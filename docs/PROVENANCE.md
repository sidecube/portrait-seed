# Relationship to the original implementation

Portrait Seed is a new, independently runnable extraction of the **active
local-description generation approach** used in Feature Fusion. It is not a
copy of the whole installation and does not import it at runtime.

Three functions were adapted from `offline_studio/local_traits.py`:

- `analysis_payload`: image resize, visible-feature instruction and JSON schema;
- `validate_description`: exact-key, visibility and description validation;
- `portrait_prompt`: fictional portrait instructions and consistent studio style.

Their source-function hashes and the original module hash are in
[source-provenance.json](source-provenance.json). These identify the extraction
baseline; they do not authenticate an unpublished original repository. The
exception class and installation-specific style label were changed. The allowed
categories exclude the historical `sex_presentation` category; the remaining
14 categories describe visible appearance. Seven are selected by default.

The active `private_generation.py` flow informed the division between local
analysis and OpenAI calls. Earlier experimental photo-upload paths were not
copied. No visitor images, generated exhibition portraits, identities, databases,
configuration or secrets were used as package assets.

## Deliberate differences

| Original installation | This independent core |
| --- | --- |
| Continuous tracking and event-driven capture | One explicit camera capture per command |
| Temporary local capture files, deleted after commit/expiry | No intentional photograph files; short-lived worker memory |
| Rich queue, controls and recovery services | One private job store, exclusive writer, three-attempt budget |
| YuNet, MediaPipe and identity memory | No tracking/embedding models; Qwen describes the foreground person |
| Exhibition-selected trait probabilities | Explicit categories, with a fixed seven-category default |
| Several image model options and a special full-regeneration branch | One documented Mini configuration; generated parent is used when available |
| Translation, animated portraits, sound and visualizations | None included |
| Operator web server, feed and settings | No web server or UI |

Camera handling, process isolation, storage, CLI and provider adapters were
implemented specifically for this reduced project. SQLite retains generated PNGs
as well as export metadata so an export failure can be recovered without paying
for another image. This design is simpler than the full exhibition queue.

The publicly reviewable claim is about **this package's** data path. An installed
exhibition build must be checked separately. Full project context:
[SIDECUBE — Feature Fusion](https://sidecube.ro/revista/feature-fusion/).

