# Verification status

Prepared 5 November 2026. Tests run in a freshly created Windows Python 3.11
virtual environment with only the package and its dependencies installed.
Direct dependency versions are recorded in ../requirements-tested.txt.

**37 offline tests passed on Windows and 37 on Linux.** The Linux run used Python
3.11.14, OpenAI SDK 2.40.0 and HTTPX 0.28.1 in an isolated temporary source
directory with an existing Python environment; no installed application files
or services were changed. The Windows run used a fresh environment with the
versions in requirements-tested.txt. These tests exercise synthetic images and
intercepted HTTP through the real SDK adapter; no real camera input, live model
inference or paid image-generation request was used for the verification.

Coverage includes:

- fixed local/cloud URLs, no proxy inheritance and no followed redirects;
- frame present only in the local request, text-only initial cloud generation;
- generated-reference type/checksum and no raw-byte reference accepted;
- JSON validation, incomplete/oversized local responses and invalid images;
- no hidden SDK retry, retryable status handling and non-retryable refusals;
- durable three-attempt budget across restarts and expiry during backoff;
- startup expiry, corrupt references and blocked concurrent writers;
- result committed before export, retry-free export recovery;
- worker termination on a hang, text-only worker result, no remote camera URL;
- mock end-to-end local description, cloud generation and saved output.

GitHub Actions is configured for Windows/Linux with Python 3.11/3.12. A
configuration is not a completed CI run; the publisher must inspect its result
after upload. Hardware compatibility and actual visual quality depend on the
user's camera, local model runtime, hardware and provider account.

The release check verifies an explicit file inventory, local documentation links,
common credential patterns and private-machine details. It is a precaution, not
a guarantee that every possible secret format can be recognized. Review files
before publishing. No third-party security audit is claimed.
