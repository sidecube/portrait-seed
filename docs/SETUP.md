# Setup, one stage at a time

## 1. Python environment

Use Python 3.11 or newer. Extract the repository somewhere writable. Examples
assume your terminal is in that directory. Use a private local output directory;
avoid automatically synced or shared folders for personal descriptions/results.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Use that venv's Python for all later commands. Do not install both GUI and
headless OpenCV variants into it. The package uses headless OpenCV only.

## 2. Local model, installed separately

Obtain a llama.cpp build with Qwen3-VL multimodal support, and a matched pair of
model and projector GGUF files. A starting point is Qwen3-VL-4B-Instruct Q4_K_M.

- [Official Qwen GGUF model card and files](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF)
- [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases)
- [llama.cpp multimodal documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)
- [llama-server reference](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)

These are separate multi-GB downloads, under their own licenses. Review the
actual files and checksums supplied by the publisher. No weights, projector,
binary runtime or face-detector model are included in this repository.

Run the following on ONE line, substituting the real executable/model paths:

```text
llama-server -m /path/to/model.gguf --mmproj /path/to/matching-mmproj.gguf --host 127.0.0.1 --port 8795 --no-webui --cache-ram 0 --reasoning off -c 4096 -np 1 -t 4 -tb 4 -ngl 0 --no-mmproj-offload
```

On Windows use `llama-server.exe` and quoted Windows paths; on Linux an absolute
path or `./llama-server` may be required. Check `llama-server --help` for the chosen
build. The example is CPU-only and starts with four threads; it is not a universal
hardware optimum. More RAM and appropriate acceleration can help. If analysis
cannot finish within ten minutes, use a suitable local model/runtime or hardware;
do not disable the privacy deadline or send the photograph to a hosted service.

Keep this server on the **same computer**, bound to loopback. Do not substitute a
hosted OpenAI-compatible endpoint. The package itself fixes the analysis URL to
`http://127.0.0.1:8795/v1/chat/completions` and bypasses environment proxies.

```sh
python -m portrait_seed doctor
```

`doctor` checks only the health response; it does not prove the loaded model can
understand images. The next step checks the actual camera-to-description path.

## 3. Camera and local description

Only open the camera after participants agree. Keep one consenting participant
in frame; the local prompt asks for the largest foreground person. There is no
automatic face enrollment or visitor tracking in this project.

```sh
python -m portrait_seed describe --camera 0 --consent
```

The command prints a job ID. The frame is processed in an isolated worker and is
not saved as a file. The validated description is retained in private-data.
No image-generation request is sent at this stage. If the device index is wrong,
choose another local index. No network camera URL or input-photo path is accepted.

Default categories: eyes, nose, lips, head shape, hair, eyewear and facial hair.
To choose others, supply comma-separated names:

```sh
python -m portrait_seed describe --camera 0 --traits eyes,hair,eyewear --consent
```

All supported names are in `prompts.py`. The prompt forbids identity, ethnicity,
gender, health, age and other hidden-attribute inferences. This is an instruction
to a fallible model, not a proof that every description will obey it.

## 4. Supply your own API access

The default image endpoint uses `gpt-image-1-mini`; check access and billing in
your own OpenAI account. The program reads only
`OPENAI_API_KEY` from the process environment, never automatically from `.env`.

For a private prompt without shell history containing the key, run Python from
the venv and enter these lines:

```python
import getpass, os, subprocess, sys
os.environ['OPENAI_API_KEY'] = getpass.getpass('OpenAI API key: ')
subprocess.run([sys.executable, '-m', 'portrait_seed', 'resume', 'JOB_ID', '--allow-paid'])
os.environ.pop('OPENAI_API_KEY', None)
```

Replace `JOB_ID` with the ID from step 3. Do not type the key as a literal in a
script, shell command, chat or screenshot. Exit the Python session when done.

Submit within ten minutes of capture. `--allow-paid` permits up to three total
attempts, including potentially billed repeats after a timeout. The SDK's own
automatic retries are disabled. Invalid credentials and most 4xx errors stop
immediately. A completed job can be exported without a new cloud request.

## 5. Inspect your saved portrait

Successful output is saved as a generated image in SQLite, then exported as
`private-data/portraits/<job-id>.png` with a JSON sidecar. Open the PNG in your
normal image viewer. The project itself has no preview interface.

Repeat `generate --camera 0 --consent --allow-paid` in an environment containing
your key to continue from the latest completed portrait. No real visitor image
can be selected as a cloud reference through the command line.

## Official API references

- [GPT Image 1 Mini](https://developers.openai.com/api/docs/models/gpt-image-1-mini)
- [Image editing endpoint](https://developers.openai.com/api/reference/resources/images/methods/edit)
- [Python SDK](https://github.com/openai/openai-python)

The configured provider is not interchangeable with the local analysis service.
Changing it requires reviewing the code and the data boundary tests.
