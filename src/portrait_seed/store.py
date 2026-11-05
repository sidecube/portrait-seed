"""Persist descriptions and GENERATED images only, with a durable attempt budget."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
from .errors import PipelineError
from .images import normalize_generated
from .reference import GeneratedReference


class Store:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = (self.root / ".lock").open("a+b")
        self.lock.seek(0)
        self.lock.write(b"0")
        self.lock.flush()
        self.lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock.close()
            raise PipelineError("data_directory_in_use") from None
        try:
            self.db = sqlite3.connect(self.root / "portraits.sqlite3")
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute('''CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, captured_at REAL NOT NULL, deadline REAL NOT NULL,
                traits TEXT NOT NULL, description TEXT NOT NULL, parent TEXT,
                status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                error TEXT, image BLOB, sha256 TEXT, completed_at REAL)''')
            self.db.commit()
            with self.db:
                self.db.execute("UPDATE jobs SET status='cancelled', error='capture_expired' "
                                "WHERE deadline<=? AND status!='completed'", (time.time(),))
        except Exception:
            self.lock.close()
            raise

    def close(self):
        self.db.close()
        self.lock.close()

    def create(self, captured_at, description, traits):
        now = time.time()
        if not isinstance(captured_at, (float, int)) or not now-600 < captured_at <= now:
            raise PipelineError("capture_expired")
        from .prompts import validate_description
        clean = validate_description(description, traits)
        parent = self.db.execute("SELECT id FROM jobs WHERE status='completed' ORDER BY completed_at DESC LIMIT 1").fetchone()
        ident = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO jobs (id,captured_at,deadline,traits,description,parent,status) VALUES (?,?,?,?,?,?,?)",
                            (ident, captured_at, captured_at+600, json.dumps(traits), json.dumps(clean), parent[0] if parent else None, "ready"))
        return ident

    def get(self, ident):
        row = self.db.execute("SELECT * FROM jobs WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise PipelineError("job_not_found")
        return dict(row)

    def reference(self, parent):
        if parent is None:
            return None
        row = self.get(parent)
        image = row["image"]
        if row["status"] != "completed" or not image or hashlib.sha256(image).hexdigest() != row["sha256"]:
            raise PipelineError("invalid_generated_reference")
        normalize_generated(image)
        return GeneratedReference(row['id'], image, row['sha256'])

    def begin_attempt(self, ident):
        # Persist before network I/O. A crash still consumes this attempt.
        with self.db:
            result = self.db.execute("UPDATE jobs SET status='submitting', attempts=attempts+1, error=NULL "
                "WHERE id=? AND status IN ('ready','retryable','submitting') AND attempts<3 AND deadline>?",
                (ident, time.time()))
        if result.rowcount != 1:
            row = self.get(ident)
            if row['deadline'] <= time.time() and row['status'] != 'completed':
                self.fail(ident, 'capture_expired', 'cancelled')
                raise PipelineError('capture_expired')
            raise PipelineError('job_not_eligible_or_attempt_limit')

    def fail(self, ident, code, status):
        with self.db:
            self.db.execute("UPDATE jobs SET error=?,status=? WHERE id=? AND status!='completed'", (code, status, ident))

    def complete(self, ident, image):
        image = normalize_generated(image)
        with self.db:
            self.db.execute("UPDATE jobs SET status='completed',image=?,sha256=?,completed_at=?,error=NULL WHERE id=?",
                            (image, hashlib.sha256(image).hexdigest(), time.time(), ident))
        return self.export(ident)

    def export(self, ident):
        row = self.get(ident)
        image = self.reference(ident).checked_bytes()
        # Database-generated UUID, never a caller-provided filename.
        filename = uuid.UUID(row['id']).hex
        directory = self.root / 'portraits'
        directory.mkdir(exist_ok=True, mode=0o700)
        if directory.is_symlink():
            raise PipelineError('invalid_output_directory')
        target = directory / (filename+'.png')
        temporary = directory / (uuid.uuid4().hex+'.tmp')
        try:
            with temporary.open('xb') as stream:
                stream.write(image)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        # No visitor image, identity embedding or API response body in metadata.
        metadata = {key:row[key] for key in ('id','parent','captured_at','completed_at','attempts','sha256')}
        metadata['traits'] = json.loads(row['description'])
        metadata['model'] = 'gpt-image-1-mini'
        metadata['visitor_image_sent_to_openai'] = False
        sidecar = directory / (filename+'.json')
        if sidecar.is_symlink():
            raise PipelineError('invalid_output_metadata')
        sidecar.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
        return target
