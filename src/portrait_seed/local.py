"""The only network destination that is allowed to receive a camera image."""
import json
import httpx
from .errors import PipelineError
from .prompts import analysis_payload, validate_description

LOCAL_URL = "http://127.0.0.1:8795/v1/chat/completions"
MAX_LOCAL_RESPONSE = 256 * 1024


def describe(capture, traits, *, transport=None):
    payload, _ = analysis_payload(capture, traits)
    try:
        # No environment proxy, configurable hostname, redirect or cloud fallback.
        with httpx.Client(trust_env=False, follow_redirects=False, timeout=240,
                          transport=transport) as client:
            with client.stream("POST", LOCAL_URL, json=payload) as response:
                if response.status_code != 200:
                    raise PipelineError("local_service_unavailable")
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_LOCAL_RESPONSE:
                        raise PipelineError("local_response_too_large")
        result = json.loads(body)
        choice = result["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise PipelineError("local_description_incomplete")
        return validate_description(json.loads(choice["message"]["content"]), traits)
    except PipelineError:
        raise
    except Exception:
        raise PipelineError("local_analysis_failed") from None

