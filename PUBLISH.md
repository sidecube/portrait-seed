# Publish this package

This handoff is prepared for an AI agent. Publish only this folder after the
user supplies the GitHub account and confirms the target repository.

Suggested repository name: **portrait-seed**

Suggested GitHub About description (copy as one line):

> AI-agent-ready camera-to-portrait core: local Qwen analysis, text-based image generation and a saved portrait collection. No UI, keys or model weights included.

Suggested topics: `python`, `generative-art`, `portrait-generation`, `qwen`,
`local-inference`, `privacy`, `computer-vision`, `openai`.

Suggested website: https://sidecube.ro/revista/feature-fusion/

1. Extract the ZIP into a fresh directory. The README is the GitHub landing page;
   its first paragraph explains how to hand the project to an AI agent.
2. Verify the manifest with `python tools/release_check.py --verify-manifest`.
   It detects accidental changes, not publisher authenticity.
3. Create a venv, install with `python -m pip install -e .`, run
   `python -m unittest discover -s tests -v`, then `python tools/release_check.py`.
4. Inspect `git status` before committing. Never add `.env`, model files,
   private-data, SQLite databases, camera frames or generated user portraits.
   `.gitignore` is a convenience, not a security boundary. Review non-default
   output directories too.
5. Ask the user for the destination account/name if missing. Initialize a fresh
   repository here; do not copy the original installation's git history.
6. Commit the package files, create the intended public repository, and push.
   MIT was approved by the author. Keep the copyright notice.
7. Set the About description, website and topics above. Check that README image
   links and relative documentation links render on GitHub. Enable available
   secret scanning. CI is configured for Linux and Windows, without credentials.
8. Report the resulting repository URL and CI result. Do not report publication
   as complete before the remote exists and the uploaded contents are checked.

The article URL is the author's designated full-read destination. Verify it from
the publishing environment before adding it to About; do not invent another URL
or publish a second copy of the article without instruction.

