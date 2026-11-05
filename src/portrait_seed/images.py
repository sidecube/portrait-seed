import io
from PIL import Image
from .errors import PipelineError

MAX_IMAGE_BYTES = 32 * 1024 * 1024


def normalize_generated(data):
    """Validate and re-encode provider images; do not download provider URLs."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_IMAGE_BYTES:
        raise PipelineError("invalid_generated_image")
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.width * source.height > 16_000_000 or min(source.size) < 32:
                raise ValueError("dimensions")
            source.load()
            buffer = io.BytesIO()
            source.convert("RGB").save(buffer, format="PNG")
            return buffer.getvalue()
    except Exception:
        raise PipelineError("invalid_generated_image") from None

