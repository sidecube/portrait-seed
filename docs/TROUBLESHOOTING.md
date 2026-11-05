# Failure paths

No program can guarantee that cameras, disks or paid services never fail. This
core stops at an unsafe boundary instead of switching to a photo-upload fallback.

| Symptom / safe error | Action |
| --- | --- |
| `participant_consent_required` | Obtain agreement, then explicitly pass `--consent`. |
| `paid_permission_required` | Explain possible charges and pass `--allow-paid` only when approved. |
| `missing_openai_api_key` | Set your own key locally; never paste it in an issue or chat. |
| `capture_or_local_analysis_failed` | Check device index, camera permission, another program using it, and local model readiness. Test with one participant in clear light. No cloud fallback is attempted. |
| `capture_deadline_expired` | The worker exceeded ten minutes and was stopped. Check hardware/model speed before a fresh consented capture. |
| `local_service_unavailable` / `local_analysis_failed` | Start the local server with the correct vision model/projector. Ensure it serves the documented schema. The public CLI deliberately groups worker errors to avoid leaking image/prompt bodies. |
| `local_description_incomplete` | The model did not finish its response. Check context capacity and model compatibility; do not submit partial JSON. |
| `capture_expired` | The text job's ten-minute submission window ended. Start a fresh capture; do not extend the stored deadline. |
| `cloud_http_400`, `_401`, `_403`, `_404` | Check prompt support, credentials, account access or model availability. These stop without automatic retry. |
| `cloud_http_408`, `_409`, `_429` or `_5xx` | Up to three total attempts, with a short bounded backoff and an expiry check before every dispatch. Persistent failures stop. |
| `cloud_connection_uncertain` | The provider may have received/billed the request. Automatic retries remain within the approved total of three. |
| `cloud_invalid_image` | Missing/malformed image response; counted as a consumed attempt. No remote result URL is followed. |
| `job_not_eligible_or_attempt_limit` | Already failed/cancelled, or all three attempts consumed. `list` shows the state. No force/reset command is supplied. |
| `invalid_generated_reference` | Stored reference fails validation/checksum. Stop and investigate; never substitute a visitor photo. |
| `data_directory_in_use` | Another command is operating on this collection. Wait for it to finish. The OS releases the lock if it crashes. |
| `local_or_dependency_error` | Check disk space, private-directory permissions, installed versions and paths. Do not enable HTTP body logging. |

## Interrupted cloud request

The attempt count is durable before sending. A restart can therefore leave a job
in `submitting`, even if the provider completed it. `resume JOB_ID --allow-paid`
can use only the remaining attempts and only before expiry; a repeated request
may be charged again. There is no claim of exactly-once delivery or billing.

## Image received, but saving failed

Saving occurs outside the retry loop. If the SQLite transaction completed but
the PNG export failed, `export JOB_ID` recreates it with no paid request. If the
database commit failed too, the response may be unrecoverable. Fix the disk first;
an explicit resume can consume a remaining paid attempt. A local failure never
silently triggers another paid request in the same run.

## Process hangs

Camera and local-analysis work have a parent-side deadline and worker termination.
HTTP clients have finite I/O timeouts. These do not bound every possible OS failure
or a malicious peer that sends bytes indefinitely. This repository does not ship
a supervisor or claim the full installation's recovery behavior.

