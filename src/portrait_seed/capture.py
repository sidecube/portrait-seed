"""No preview, recorder, image file, remote camera URL or face identity database."""
import multiprocessing as mp
import time
from .errors import PipelineError
from .prompts import validate_description

CAPTURE_TTL = 600


def _worker(connection, device, traits):
    try:
        import cv2
        from .local import describe
        camera = cv2.VideoCapture(device)
        try:
            if not camera.isOpened():
                raise PipelineError("camera_unavailable")
            # Discard initial buffered frames. The parent also bounds blocking drivers.
            frame = None
            for _ in range(8):
                ok, candidate = camera.read()
                if ok:
                    frame = candidate
            if frame is None:
                raise PipelineError("camera_frame_unavailable")
            captured_at = time.time()
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                raise PipelineError("camera_encoding_failed")
        finally:
            camera.release()
        description = describe(encoded.tobytes(), traits)
        # Only validated TEXT leaves this short-lived process via IPC.
        connection.send((True, captured_at, description))
    except Exception:
        connection.send((False, "capture_or_local_analysis_failed", None))
    finally:
        connection.close()


def capture_description(device, traits, *, timeout=CAPTURE_TTL, worker=_worker):
    if type(device) is not int or device < 0:
        raise PipelineError("camera_must_be_local_device_index")
    if not 0 < timeout <= CAPTURE_TTL:
        raise PipelineError("invalid_capture_timeout")
    context = mp.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(sender, device, traits), daemon=True)
    started = time.monotonic()
    process.start()
    sender.close()
    try:
        if not receiver.poll(timeout):
            raise PipelineError("capture_deadline_expired")
        try:
            result = receiver.recv()
        except EOFError:
            raise PipelineError("capture_worker_failed") from None
        if not result[0]:
            raise PipelineError("capture_or_local_analysis_failed")
        if time.monotonic() - started >= timeout:
            raise PipelineError("capture_deadline_expired")
        return result[1], validate_description(result[2], traits)
    finally:
        receiver.close()
        # End this process even on success: discard its camera/encoded buffers.
        if process.is_alive():
            process.terminate()
        process.join(3)
        if process.is_alive():
            process.kill()
            process.join(3)
        process.close()

