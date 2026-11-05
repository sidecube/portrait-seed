"""Offline boundary/failure tests. No real camera, credentials, weights or paid calls."""
import base64
import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest
import contextlib
from unittest.mock import patch
import httpx
from PIL import Image
from portrait_seed.capture import capture_description
from portrait_seed.cloud import ImageGenerator
from portrait_seed.errors import CloudError, PipelineError
from portrait_seed.images import normalize_generated
from portrait_seed.local import describe, LOCAL_URL
from portrait_seed.pipeline import run_job
from portrait_seed.prompts import validate_description, portrait_prompt
from portrait_seed.reference import GeneratedReference
from portrait_seed.store import Store

TRAITS=[{'key':'eyes'},{'key':'hair'}]
TEXT={'eyes':{'description':'Round eyes with visible dark irises.','visibility':'clear'},
      'hair':{'description':'Short wavy dark hair.','visibility':'clear'}}


def png(color='blue'):
    buffer=io.BytesIO()
    Image.new('RGB',(64,64),color).save(buffer,format='PNG')
    return buffer.getvalue()


def success_response(request):
    return httpx.Response(200,json={'created':0,'data':[{'b64_json':base64.b64encode(png()).decode()}]})


def hanging_worker(connection, device, traits):
    time.sleep(60)


def safe_worker(connection, device, traits):
    connection.send((True,time.time(),TEXT))
    connection.close()


class BoundaryTests(unittest.TestCase):
    def test_initial_cloud_request_is_text_only(self):
        seen=[]
        def handler(req):
            seen.append(req)
            return success_response(req)
        with patch.dict(os.environ,{'OPENAI_BASE_URL':'https://invalid.example','HTTPS_PROXY':'http://invalid.example'}):
            generator=ImageGenerator(api_key='test-only-not-a-real-key',transport=httpx.MockTransport(handler))
            try:self.assertTrue(generator.generate(TEXT,TRAITS).startswith(b'\x89PNG'))
            finally:generator.close()
        self.assertEqual(len(seen),1)
        self.assertEqual(str(seen[0].url),'https://api.openai.com/v1/images/generations')
        payload=json.loads(seen[0].content)
        self.assertNotIn('image',payload)
        self.assertNotIn('data:image',seen[0].content.decode())
        self.assertIn('Round eyes',payload['prompt'])

    def test_edits_contain_only_generated_reference(self):
        generated=png('blue'); camera=png('red'); seen=[]
        def handler(req):
            seen.append(req)
            return success_response(req)
        generator=ImageGenerator(api_key='test-only-not-a-real-key',transport=httpx.MockTransport(handler))
        try:
            generator.generate(TEXT,TRAITS,GeneratedReference('test',generated,hashlib.sha256(generated).hexdigest()))
        finally:generator.close()
        self.assertEqual(seen[0].url.path,'/v1/images/edits')
        self.assertIn(generated,seen[0].content)
        self.assertNotIn(camera,seen[0].content)
        self.assertIn(b'previous-generated-portrait.png',seen[0].content)

    def test_raw_bytes_cannot_be_cloud_reference(self):
        seen=[]
        generator=ImageGenerator(api_key='test-only-not-a-real-key',transport=httpx.MockTransport(lambda req:seen.append(req)))
        try:
            with self.assertRaises(PipelineError):generator.generate(TEXT,TRAITS,png('red'))
        finally:generator.close()
        self.assertFalse(seen)

    def test_corrupted_reference_never_sent(self):
        seen=[]
        generator=ImageGenerator(api_key='test-only-not-a-real-key',transport=httpx.MockTransport(lambda req:seen.append(req)))
        try:
            with self.assertRaises(PipelineError):
                generator.generate(TEXT,TRAITS,GeneratedReference('test',png(),'invalid'))
        finally:generator.close()
        self.assertFalse(seen)

    def test_local_receives_frame_only_on_loopback(self):
        seen=[]
        def handler(req):
            seen.append(req)
            return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(TEXT)}}]})
        with patch.dict(os.environ,{'HTTP_PROXY':'http://invalid.example'}):
            result=describe(png('red'),TRAITS,transport=httpx.MockTransport(handler))
        self.assertEqual(result,TEXT)
        self.assertEqual(str(seen[0].url),LOCAL_URL)
        self.assertIn('data:image/jpeg;base64,',seen[0].content.decode())
        self.assertFalse(json.loads(seen[0].content)['cache_prompt'])

    def test_local_redirect_fails_without_following(self):
        seen=[]
        def handler(req):
            seen.append(req)
            return httpx.Response(307,headers={'location':'https://invalid.example/upload'})
        with self.assertRaises(PipelineError):describe(png(),TRAITS,transport=httpx.MockTransport(handler))
        self.assertEqual(len(seen),1)

    def test_cloud_redirect_fails_without_following(self):
        seen=[]
        def handler(req):
            seen.append(req)
            return httpx.Response(307,headers={'location':'https://invalid.example/upload'})
        generator=ImageGenerator(api_key='test-only-not-a-real-key',transport=httpx.MockTransport(handler))
        try:
            with self.assertRaises(CloudError):generator.generate(TEXT,TRAITS)
        finally:generator.close()
        self.assertEqual(len(seen),1)

    def test_local_truncated_response_fails(self):
        transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{'content':json.dumps(TEXT)}}]}))
        with self.assertRaises(PipelineError):describe(png(),TRAITS,transport=transport)

    def test_local_oversized_response_fails(self):
        transport=httpx.MockTransport(lambda req:httpx.Response(200,content=b'x'*300_000))
        with self.assertRaises(PipelineError):describe(png(),TRAITS,transport=transport)

    def test_cloud_sdk_does_not_retry_internally(self):
        seen=[]
        def handler(req):
            seen.append(req)
            return httpx.Response(500,json={'error':{'message':'sensitive upstream body'}})
        generator=ImageGenerator(api_key='test-only-not-a-real-key',transport=httpx.MockTransport(handler))
        try:
            with self.assertRaises(CloudError) as error:generator.generate(TEXT,TRAITS)
            self.assertEqual(str(error.exception),'cloud_http_500')
        finally:generator.close()
        self.assertEqual(len(seen),1)

    def test_cloud_refusal_is_not_retried(self):
        generator=ImageGenerator(api_key='test-only-not-a-real-key',transport=httpx.MockTransport(lambda req:httpx.Response(400,json={'error':{'message':'refused'}})))
        try:
            with self.assertRaises(CloudError) as error:generator.generate(TEXT,TRAITS)
            self.assertFalse(error.exception.retryable)
        finally:generator.close()

    def test_schema_rejects_extra_keys_or_embedded_data(self):
        cases=[{**TEXT,'identity':{'description':'someone','visibility':'clear'}},
               {**TEXT,'eyes':{'description':'https://invalid.example','visibility':'clear'}},
               {**TEXT,'eyes':{'description':'DATA:image/png;base64,abc','visibility':'clear'}},
               {**TEXT,'eyes':{'description':'x'*241,'visibility':'clear'}},
               {**TEXT,'eyes':{'description':'eyes','visibility':'unknown'}}]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(PipelineError):validate_description(case,TRAITS)

    def test_hidden_feature_description_removed(self):
        result=validate_description({**TEXT,'eyes':{'description':'invented','visibility':'not_visible'}},TRAITS)
        self.assertIsNone(result['eyes']['description'])

    def test_empty_description_fails(self):
        with self.assertRaises(PipelineError):
            validate_description({key:{'description':None,'visibility':'not_visible'} for key in TEXT},TRAITS)

    def test_prompt_marks_observations_as_untrusted(self):
        result=portrait_prompt(TEXT,True)
        self.assertIn('not instructions',result)
        self.assertIn('fictional portrait',result)

    def test_invalid_generated_image_rejected(self):
        for image in (b'',b'not an image',b'x'*(32*1024*1024+1)):
            with self.assertRaises(PipelineError):normalize_generated(image)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=Store(self.temp.name)
    def tearDown(self):
        self.store.close()
        self.temp.cleanup()
    def job(self,age=0):
        return self.store.create(time.time()-age,TEXT,TRAITS)
    def test_completed_job_survives_restart_and_exports(self):
        ident=self.job();calls=[]
        class Generator:
            def generate(self,*args):calls.append(args);return png()
        path=run_job(self.store,ident,Generator())
        self.assertEqual(path.read_bytes(),png())
        self.store.close();self.store=Store(self.temp.name)
        self.assertEqual(run_job(self.store,ident,Generator()),path)
        self.assertEqual(len(calls),1)
        self.assertEqual(self.store.get(ident)['attempts'],1)
    def test_next_portrait_uses_completed_parent(self):
        first=self.job();self.store.complete(first,png())
        second=self.job();self.assertEqual(self.store.get(second)['parent'],first)
        reference=self.store.reference(first)
        self.assertIsInstance(reference,GeneratedReference)
        self.assertEqual(reference.png,png())
    def test_tampered_parent_stops_before_paid_attempt(self):
        first=self.job();self.store.complete(first,png());second=self.job()
        with self.store.db:self.store.db.execute('UPDATE jobs SET image=? WHERE id=?',(png('red'),first))
        with self.assertRaises(PipelineError):run_job(self.store,second,None)
        self.assertEqual(self.store.get(second)['attempts'],0)
    def test_expired_description_cannot_start_cloud_call(self):
        ident=self.job()
        with self.store.db:self.store.db.execute('UPDATE jobs SET deadline=? WHERE id=?',(time.time()-1,ident))
        with self.assertRaises(PipelineError):run_job(self.store,ident,None)
        self.assertEqual(self.store.get(ident)['status'],'cancelled')
        self.assertEqual(self.store.get(ident)['attempts'],0)
    def test_expiry_boundary_and_future_timestamps(self):
        now=time.time()
        with patch('portrait_seed.store.time.time',return_value=now):
            self.store.create(now-599.99,TEXT,TRAITS)
            for stamp in (now-600,now+1,float('nan')):
                with self.assertRaises(PipelineError):self.store.create(stamp,TEXT,TRAITS)
    def test_three_attempts_persist_through_restart(self):
        ident=self.job()
        self.store.begin_attempt(ident)
        self.store.close();self.store=Store(self.temp.name)
        self.store.begin_attempt(ident);self.store.begin_attempt(ident)
        with self.assertRaises(PipelineError):self.store.begin_attempt(ident)
        self.assertEqual(self.store.get(ident)['attempts'],3)
    def test_retry_success_and_bounded_failure(self):
        class Flaky:
            calls=0
            def generate(self,*args):
                self.calls+=1
                if self.calls<3:raise CloudError('cloud_connection_uncertain',True)
                return png()
        ident=self.job();generator=Flaky()
        run_job(self.store,ident,generator,sleep=lambda _:None)
        self.assertEqual(generator.calls,3)
        self.assertEqual(self.store.get(ident)['status'],'completed')
        class Broken:
            calls=0
            def generate(self,*args):
                self.calls+=1
                raise CloudError('cloud_http_503',True)
        ident=self.job();generator=Broken()
        with self.assertRaises(CloudError):run_job(self.store,ident,generator,sleep=lambda _:None)
        self.assertEqual(generator.calls,3)
        with self.assertRaises(PipelineError):run_job(self.store,ident,generator,sleep=lambda _:None)
        self.assertEqual(generator.calls,3)
    def test_expiry_during_backoff_prevents_retry(self):
        ident=self.job()
        class Broken:
            calls=0
            def generate(self,*args):self.calls+=1;raise CloudError('cloud_http_503',True)
        def wait(_):
            with self.store.db:self.store.db.execute('UPDATE jobs SET deadline=0 WHERE id=?',(ident,))
        generator=Broken()
        with self.assertRaises(PipelineError):run_job(self.store,ident,generator,sleep=wait)
        self.assertEqual(generator.calls,1)
    def test_result_can_finish_after_deadline(self):
        ident=self.job();store=self.store
        class Slow:
            def generate(self,*args):
                with store.db:store.db.execute('UPDATE jobs SET deadline=0 WHERE id=?',(ident,))
                return png()
        run_job(store,ident,Slow())
        self.assertEqual(store.get(ident)['status'],'completed')
    def test_export_failure_does_not_repeat_generation(self):
        ident=self.job();calls=[]
        class Generator:
            def generate(self,*args):calls.append(1);return png()
        with patch.object(self.store,'export',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):run_job(self.store,ident,Generator())
        run_job(self.store,ident,Generator())
        self.assertEqual(len(calls),1)
    def test_completed_png_can_be_recovered_without_cloud(self):
        ident=self.job();path=self.store.complete(ident,png());path.unlink()
        self.assertEqual(self.store.export(ident).read_bytes(),png())
    def test_data_lock_blocks_concurrent_writer(self):
        with self.assertRaises(PipelineError):Store(self.temp.name)
    def test_no_frame_or_identity_columns(self):
        columns=[row[1] for row in self.store.db.execute('PRAGMA table_info(jobs)')]
        self.assertNotIn('capture',columns);self.assertNotIn('embedding',columns)
    def test_restart_expires_pending_jobs(self):
        ident=self.job()
        with self.store.db:self.store.db.execute('UPDATE jobs SET deadline=0 WHERE id=?',(ident,))
        self.store.close();self.store=Store(self.temp.name)
        self.assertEqual(self.store.get(ident)['status'],'cancelled')
    def test_end_to_end_mocked_local_and_cloud(self):
        frame=png('red')
        local_transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(TEXT)}}]}))
        description=describe(frame,TRAITS,transport=local_transport)
        ident=self.store.create(time.time(),description,TRAITS)
        generator=ImageGenerator(api_key='test-only-not-a-real-key',transport=httpx.MockTransport(success_response))
        try:run_job(self.store,ident,generator)
        finally:generator.close()
        self.assertEqual(self.store.get(ident)['status'],'completed')
        for path in Path(self.temp.name).rglob('*'):
            if path.is_file() and path.name != '.lock':self.assertNotIn(frame,path.read_bytes())


class WorkerTests(unittest.TestCase):
    def test_real_worker_releases_camera_and_sends_text_only(self):
        from portrait_seed.capture import _worker
        import cv2
        import numpy as np
        frame=np.zeros((64,64,3),dtype=np.uint8)
        class Camera:
            released=False
            def isOpened(self):return True
            def read(self):return True,frame
            def release(self):self.released=True
        class Connection:
            value=None
            closed=False
            def send(self,value):self.value=value
            def close(self):self.closed=True
        camera=Camera();connection=Connection()
        with patch.object(cv2,'VideoCapture',return_value=camera), patch('portrait_seed.local.describe',return_value=TEXT) as analyze:
            _worker(connection,0,TRAITS)
        self.assertTrue(camera.released and connection.closed)
        self.assertEqual(connection.value[2],TEXT)
        self.assertTrue(connection.value[0])
        self.assertIsInstance(analyze.call_args.args[0],bytes)
        self.assertFalse(any(isinstance(value,bytes) for value in connection.value))

    def test_cli_requires_consent_without_creating_data(self):
        from portrait_seed.cli import main
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'must-not-exist'
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['--data',str(target),'describe']),1)
            self.assertFalse(target.exists())

    def test_cli_requires_paid_permission_before_any_capture(self):
        from portrait_seed.cli import main
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'must-not-exist'
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['--data',str(target),'generate','--consent']),1)
            self.assertFalse(target.exists())

    def test_worker_returns_only_validated_text(self):
        stamp,result=capture_description(0,TRAITS,timeout=10,worker=safe_worker)
        self.assertEqual(result,TEXT)
        self.assertLess(time.time()-stamp,10)
    def test_hanging_worker_is_terminated(self):
        before={p.pid for p in multiprocessing.active_children()}
        started=time.monotonic()
        with self.assertRaises(PipelineError):capture_description(0,TRAITS,timeout=.2,worker=hanging_worker)
        self.assertLess(time.monotonic()-started,8)
        self.assertEqual({p.pid for p in multiprocessing.active_children()},before)
    def test_network_camera_and_unbounded_timeout_rejected(self):
        for device,timeout in [('https://invalid.example',10),(0,601),(-1,10)]:
            with self.assertRaises(PipelineError):capture_description(device,TRAITS,timeout=timeout)


if __name__=='__main__':unittest.main()
