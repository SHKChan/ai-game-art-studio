# Deployment on Windows + Stage B (production) acceptance

Stage A (offline engineering acceptance) was completed on the development computer.
**Stage B has NOT been run.** It must be performed on a Windows computer with a working ComfyUI.

## 1. Install

1. Install **Python 3.10+** (python.org, tick *Add python.exe to PATH*). Optional: **ffmpeg** (video import) —
   put `ffmpeg.exe` on PATH or set `ARTSTUDIO_FFMPEG`.
2. Copy (or `git clone`) the `ai-game-art-studio` folder to the target computer. Nothing else is needed —
   the pixel engine is built in (no Rust, no external binaries).
3. Start: `powershell -ExecutionPolicy Bypass -File .\start.ps1` (first run creates `.venv` and installs
   `requirements.txt`; opens http://127.0.0.1:8870/).
   Options: `-Port 8870 -Workspace D:\Art\studio-ws -ComfyUrl http://127.0.0.1:8188 -NoBrowser`.

**Offline dependency install.** On a connected machine: `pip download -r requirements.txt -d wheels --platform win_amd64
--python-version 3.12 --only-binary=:all:`; on the target: `.venv\Scripts\pip install --no-index --find-links wheels -r requirements.txt`.

**Language & encoding.** UI language: top-bar switch (English / 简体中文). CLI/API messages: `ARTSTUDIO_LANG=zh-CN`
or `--lang zh-CN`. All files are read/written as UTF-8 regardless of the Windows code page (GBK/cp936/cp1252), and the
launcher additionally enables Python UTF-8 mode.

## 2. Configure

Copy `studio.config.example.json` → `studio.config.json` and/or `.env.example` → `.env`.

| setting | env | default |
|---|---|---|
| workspace | `ARTSTUDIO_WORKSPACE` | `<repo>/workspace` (keep it outside the source tree for production, e.g. `D:\GameArt\ws`) |
| port | `ARTSTUDIO_PORT` | 8870 |
| comfyui.url | `COMFYUI_URL` | http://127.0.0.1:8188 |
| comfyui.job_timeout_s | `COMFYUI_TIMEOUT` | 600 |
| language | `ARTSTUDIO_LANG` | en (`zh-CN` for Chinese CLI/API messages) |
| prompt_language | — | en (per-project override in the Library) |
| comfyui.api_key_env | — | name of an env var holding a bearer token for an authenticating proxy (never the token itself) |

## 3. Connect ComfyUI

- Local: start ComfyUI normally (`python main.py`, default port 8188). Remote: start it with `--listen 0.0.0.0` and
  use `http://<host>:8188` — only on a trusted network (ComfyUI has no authentication).
- In the studio *Generation* tab the ComfyUI card must show **available** with your version and GPU. If it shows
  "(MOCK)" you are connected to the test server.
- Install the models you intend to use in ComfyUI's own folders; the studio reads what exists from `/object_info`.
- In *Animate character → Generate* choose **Local ComfyUI**, enter the checkpoint file name, keep denoise around 0.55–0.7.
  The reference is repeated across a strip (one cell per frame) and redrawn per pose with img2img.

## 3b. Connect the Codex CLI (optional, recommended for character animation)

- Install and log in once: `npm install -g @openai/codex`, then `codex login`. No API key is stored by the studio.
- The studio finds `codex` / `codex.cmd` on PATH. If it lives elsewhere set `codex_bin` in `studio.config.json`
  (or `ARTSTUDIO_CODEX`), e.g. `"codex_bin": "C:\\Users\\you\\AppData\\Roaming\\npm\\codex.cmd"`.
- Codex is used twice in *Animate character*: **Write with Codex** (`codex exec` reads the reference image and writes
  the character description + frame-by-frame poses) and **Generate → Codex CLI** (built-in image generation through
  `codex app-server`). The home page shows "Codex CLI ●" when it is found; login is checked at the first call.

## 4. Import workflows

1. In ComfyUI build/load a workflow, then **Workflow → Export (API)** (older UI: enable Dev mode → *Save (API Format)*).
2. Studio → *Generation* → *Import workflow*: choose the JSON, a name and a category
   (text_to_image, image_to_image, character_reference, pose_keyframe, inpainting, image_to_video, background_removal).
3. The studio derives mappings (positive/negative prompt from the sampler's links, seed, size, steps, cfg, denoise,
   LoadImage → image inputs, model files → `model_<input>_<node>` parameters) and records required nodes/models.
   Review them (`python -m artstudio workflows show --id <id>`); adjust by re-importing a template JSON with an edited
   `mappings` block if needed. CLI: `python -m artstudio workflows import --file wf.json --name "My pose" --category pose_keyframe`.
4. Press **Check** — it validates nodes and model filenames against the live server.
5. Imported templates start as `unverified`. After a successful production run and human review, mark them verified
   (edit `"verification": "production-verified"` in `<workspace>/comfyui/workflows/<id>.json`).

Bundled templates (`workflows/comfyui/*.json`) use core nodes only and need parameters such as
`{"checkpoint": "<your file>.safetensors"}` (pose: also `"controlnet"`; video: `"video_checkpoint"`).
`rembg-inspyrenet` additionally needs the ComfyUI-Inspyrenet-Rembg custom node and is unverified.

## 5. Stage B — production smoke test

```powershell
.venv\Scripts\python.exe scripts\production_smoke_test.py --comfy http://127.0.0.1:8188 `
   --checkpoint <your_checkpoint.safetensors> [--controlnet <openpose.safetensors>] `
   [--reference D:\refs\hero.png] --budget 4 --steps 20 --size 768
```

It checks reachability (refuses the mock), node/model discovery, every bundled workflow's compatibility,
text-to-image, image-to-image → import → QA → export, optional pose keyframe, cancellation and offline fallback, and
writes `workspace/stage-b-smoke-report/smoke_report.{json,md}` plus contact sheets **for human review**.

Then run the reduced production test of SPECIFICATION §15 Test B in the UI:
master (south) → approve → walk east (4–8 frames) → attack east (6–10 frames) → review → only then batch the other
directions with an explicit budget. Record results in `DEVELOPMENT_PROGRESS.md` under Stage B.

Stage B is passed only when: the smoke test passes on the real server, generated sheets import cleanly, a human has
reviewed identity/proportion consistency, and GPU time per job is acceptable.

## 6. Migration and backup

- Backup: `python -m artstudio backup D:\backups\studio-2026-11-25.zip [--no-exports]` (or copy the workspace folder
  while the studio is stopped).
- Restore on another PC: `python -m artstudio restore backup.zip D:\GameArt\ws` (target must be empty), then start with
  `-Workspace D:\GameArt\ws`.
- Upgrading the app: workspaces carry `schema_version`; the app migrates older ones on open and refuses newer ones.
- Engine A documents travel inside the workspace (`projects/<pid>/engine`); recipes are plain JSON lines and replay on
  any machine. Workspaces created before the engine switch keep their rendered frames; replay their recipe to rebuild
  the editable document.

## 7. Running the offline test-suite on the target

`.venv\Scripts\python.exe scripts\run_tests.py` (mock ComfyUI is started in-process; all 63 tests run without external tools). UI test: `pip install playwright && playwright install chromium`, start the studio
with an empty workspace and run `python tests\ui_playwright.py`.
