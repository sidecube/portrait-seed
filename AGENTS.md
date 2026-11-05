# Instructions for an AI agent receiving this repository

This is a standalone camera-to-portrait core. Read README.md, docs/SETUP.md and
docs/PRIVACY.md first. Keep the project generic. Do not add the exhibition UI,
audio, dashboards, trackers, facial embeddings or background startup services.

## Help the user run it

1. Identify the OS, Python version, available disk/RAM and camera needs. Explain
   that local vision inference may be slow. Do not promise a frame rate.
2. Create an isolated virtual environment. Install this project and run
   `python -m unittest discover -s tests -v` before any real input.
3. Ask the user before downloading multi-GB weights; use official Qwen/model
   and llama.cpp sources in docs/SETUP.md. Verify their actual current filenames.
   Model weights and the matching vision projector are not bundled.
4. Start the model service bound only to 127.0.0.1:8795. Disable its web UI and
   prompt cache. Explain that its process memory is outside this package.
5. Use `doctor`; this does not access the camera or OpenAI.
6. Obtain participant permission before `describe --consent`. This opens the
   camera once and stores a description; no visitor photo file is created.
7. Ask the user to enter their own API key in a local terminal/environment.
   Never request, print, copy into chat or commit it. Do not read existing .env
   files or unrelated app credentials to find a key.
8. Explain that an OpenAI request is paid, and a lost response may be charged
   again on retry (three total attempts maximum). Obtain approval for the paid
   run before using `--allow-paid`. Use the job ID within ten minutes of capture.
9. Check the saved PNG/sidecar, without copying either into the public repo.
   Explain that generated images and descriptions remain in private-data.
10. If something fails, follow docs/TROUBLESHOOTING.md. Report the safe error code;
    never dump request/response bodies. Do not send the visitor photo to a cloud
    model as a fallback or widen the local endpoint to a remote host.

## Invariants when modifying code

- The cloud boundary must never accept a camera frame/file/URL as a reference.
- Keep validation before cloud dispatch. Text observations are untrusted data.
- Do not add implicit SDK retries, reset durable attempts, or extend deadlines.
- An output save failure must not cause an automatic fresh paid generation.
- Never claim "fully offline", "anonymous", "zero retention" or legal compliance.
- The installation and this public extraction differ; docs/PROVENANCE.md says how.
- Test without a real camera or paid API calls unless the user authorizes them.
- This ZIP does not grant permission to read or publish private-data or secrets.

## Help the author publish it

Follow PUBLISH.md. Check the package manifest, run tests and the release audit,
then use the account/repository name supplied by the user. Do not invent an owner,
publish the parent directory or include a private data directory. The package
contains no git history or repository remote. Preserve MIT attribution.

