"""An explicit generated-reference type prevents accidental raw-byte uploads."""
from dataclasses import dataclass
import hashlib
from .errors import PipelineError


@dataclass(frozen=True)
class GeneratedReference:
    job_id: str
    png: bytes
    sha256: str

    def checked_bytes(self):
        if hashlib.sha256(self.png).hexdigest() != self.sha256:
            raise PipelineError('invalid_generated_reference')
        return self.png

