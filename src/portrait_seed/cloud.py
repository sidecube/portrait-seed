"""Outbound boundary: accepts validated text and an already-generated portrait only."""
import base64
import io
import os
import httpx
from openai import OpenAI, APIConnectionError, APITimeoutError, APIStatusError
from .errors import CloudError, PipelineError
from .images import normalize_generated
from .prompts import validate_description, portrait_prompt
from .reference import GeneratedReference

MODEL = "gpt-image-1-mini"
BASE_URL = "https://api.openai.com/v1/"


class ImageGenerator:
    def __init__(self, *, api_key=None, transport=None):
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise PipelineError("missing_openai_api_key")
        self.http = httpx.Client(trust_env=False, follow_redirects=False,
                                 transport=transport, timeout=180)
        self.client = OpenAI(api_key=key, base_url=BASE_URL, http_client=self.http,
                             max_retries=0, timeout=180)

    def close(self):
        self.client.close()

    def generate(self, description, traits, reference=None):
        clean = validate_description(description, traits)
        if reference is not None and not isinstance(reference, GeneratedReference):
            raise PipelineError('reference_must_be_generated_record')
        request = dict(model=MODEL, quality="low", size="1024x1536", n=1,
                       output_format="png", prompt=portrait_prompt(clean, reference is not None))
        try:
            if reference is None:
                result = self.client.images.generate(**request)
            else:
                # Reference bytes come only from Store.reference(), never from the camera.
                image = io.BytesIO(normalize_generated(reference.checked_bytes()))
                image.name = "previous-generated-portrait.png"
                result = self.client.images.edit(image=[image], **request)
            raw = base64.b64decode(result.data[0].b64_json, validate=True)
            return normalize_generated(raw)
        except (APIConnectionError, APITimeoutError):
            raise CloudError("cloud_connection_uncertain", retryable=True) from None
        except APIStatusError as error:
            code = error.status_code
            raise CloudError(f"cloud_http_{code}", retryable=code in (408, 409, 429) or code >= 500) from None
        except (PipelineError, ValueError, TypeError, IndexError, AttributeError):
            raise CloudError("cloud_invalid_image", retryable=True) from None
