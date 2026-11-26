# AGENTS.md — persistent instructions for agents working on AI Game Art Studio

Read this first, then `SPECIFICATION.md` (authoritative requirements) and `DEVELOPMENT_PROGRESS.md` (current state).

## Project facts

- **What it is:** local-first 2D game art studio. Engine A = own pixel engine; Engine B = character animation (AI:
  Codex CLI or ComfyUI); Engine C = import.
  User-facing overview: `README.md` / `README.zh-CN.md`.
- **Version:** `VERSION` (currently 0.3.0). History: `CHANGELOG.md`.
- **Based on (MIT):** Atelier (marmikshah/atelier @ 8ac6adf) — call format re-implemented in `artstudio/engine`;
  Pixel Atelier (jinxingtaire/pixel-atelier @ 15d199f) — code moved into `artstudio/pipeline`, `prompts_zh_sheet.py`,
  `providers/codex_rpc.py`, `samples/knight`. Neither is a dependency any more; do not re-add them as checkouts.
- **Status:** Stage A (offline) done, 78 tests. Stage B (real ComfyUI) **not run** — never claim it passed.
- **Owner policy:** the owner allows rewriting and reorganising any code. Translation scope is UI, CLI/API messages,
  prompts, README and deployment guide only.

## Ground rules

1. **Never fabricate.** Do not invent API capabilities, generated artwork, test results or integrations. A test is
   "passed" only if it was executed in this session and the output was read. Record what you ran.
2. **Mock ≠ real.** Anything produced by `MockGenerationProvider` or `mock_comfyui/` is a TEST FIXTURE. It must carry
   `provider.is_test_fixture = true` and must never be described as AI-generated art. Stage B (real ComfyUI) is not
   passed until `scripts/production_smoke_test.py` passes on a real server *and* a human reviews the art.
3. **No placeholder art to hide failures.** If a provider is unavailable, report it as unavailable; never substitute
   another technology silently.
4. **Self-contained repo.** No vendored git checkouts. Code derived from Atelier/Pixel Atelier keeps its MIT notice
   (file header + THIRD_PARTY_NOTICES.md). Keep `samples/knight` (demo-only art) and `tests/fixtures` attributed.
5. **Do not modify unrelated projects** (e.g. sibling `vibe-game/`).
6. **Generated assets stay out of the source tree** (workspace dir; `deliverables/` holds curated POC outputs only).
7. **Paid / remote generation needs an explicit budget** for unattended batches (`budget=N`). Prefer reduced tests
   (one direction, one action) before batches.

## Architecture in one paragraph

Engine A is `artstudio/engine` (own pixel engine, Atelier-compatible call format; builders in `artstudio/procedural`).
`artstudio.service.Studio` is the single entry point used by the HTTP server (`artstudio/server/app.py`), the CLI
(`artstudio/cli.py`) and job handlers (`artstudio/jobs.py`). Providers (`artstudio/providers/`) report runtime
availability. All image assets are manifests (`artstudio/schema/asset.schema.json`) with an `animation` block;
source frames are preserved (`frames_src/`), processed frames (`frames/`) are reproducible from
`processing.normalize`. Processing lives in `artstudio/processing/frames.py` (shared by pixel and HD modes), QA in
`artstudio/qa/`, exports in `artstudio/export/`. UI: `artstudio/web/` (vanilla ES modules, no build step, strict CSP).

## Engine B — character animation (guided flow)

- Flow: reference image (locked master) → action plan → prompts → **one sprite strip per action** → slice + align →
  animation asset → review (redo single frames) → export. UI: `artstudio/web/wizard.js`; home: `home.js`.
- Plan: `artstudio/actions.py`, stored at `characters/<cid>/action_plan.json`. Action ids are `[a-z0-9_]` (non-ASCII
  names fall back to `action`, `action_2`). Presets come from `animation.TEMPLATES`.
- Prompts: `write_prompts(method="codex")` runs `codex exec` read-only with the reference image and expects JSON
  (`codex_cli.extract_json`); `method="template"` is the offline fallback. Never silently swap one for the other.
- Generation: `Studio.generate_action`. Codex → `codex app-server` image bridge (`providers/codex_rpc.py`); ComfyUI →
  `strip_reference` (reference repeated per cell) + img2img; mock → labelled fixtures. `strip_layout` uses auto
  slicing and falls back to an even grid with a visible warning.
- Codex is located by `codex_cli.resolve` (`codex_bin` / `ARTSTUDIO_CODEX` / PATH, incl. `codex.cmd`). The prompt goes
  on **stdin**, never argv (Windows quoting + Chinese text). Tests use `tests/fake_codex.py` via
  `ARTSTUDIO_CODEX="<python> tests/fake_codex.py"`; that double is not art and must never ship as output.
- Batch generation is job kind `batch_actions` and always has a budget (default = number of actions).

## UI structure

- Main nav: Home · Animate character · Pixel assets · Import · Library · Export. Expert tabs (Animation editor,
  Character details, Generation & workflows) sit under **More tools** and open automatically when linked to.
- Keep new user-facing features inside the guided flow first; add expert controls to the advanced tabs.
- The jobs dock auto-folds when idle; don't place primary buttons where it would cover them while jobs run.

## Development standards

- Python ≥ 3.10, dependencies limited to Pillow + numpy (stdlib for HTTP/WebSocket/JSON). Add a dependency only
  with a strong reason and update `requirements.txt` + `pyproject.toml`.
- Type hints on public functions; validate inputs at boundaries (schemas, `StudioError` for user errors).
- Paths from users/UI go through `util.safe_join`; IDs through `check_id`. Subprocesses: fixed argument lists, never
  `shell=True`, never a UI-supplied executable.
- JSON writes are atomic (`util.write_json`). Every user-visible edit to an asset snapshots a version.
- Alignment rules (do not break): one scale per animation group; no per-frame bbox fitting or centring; keep
  intentional vertical motion (airborne frames); expand canvas instead of cropping weapons/effects.
- Pixel mode = nearest/integer/binary alpha/optional palette. HD mode = Lanczos (premultiplied), partial alpha, no
  forced quantization. Never convert HD art to pixel art unless explicitly requested.
- Deterministic QA and visual (probabilistic) review are separate fields; never mark visual consistency from
  technical checks.
- Logging: `logging.getLogger("artstudio.<area>")`, key=value style, to stderr. CLI prints JSON to stdout.
- **Encoding:** every file read/write and subprocess pipe states `encoding="utf-8"` (tests/test_encoding.py enforces it).
  Never rely on the locale (Windows GBK/cp936/cp1252).
- **Bilingual (en / zh-CN):** UI strings are English literals; add the Chinese text to `artstudio/web/i18n.js` (exact-text
  dictionary; dynamic strings via `ZH_PATTERNS`). Mark user data with `data-no-i18n`. Server/CLI errors: raise
  `StudioError(msg, code=...)` and add the code or an English-template regex + Chinese text to `artstudio/i18n.py`.
  Prompts: English default; Chinese variants in `artstudio/prompts.py` (`build_*_prompt(language=...)`).
  Agent-facing docs/skills stay English; user docs have `.zh-CN.md` versions.

## Commands

```bash
python scripts/run_tests.py                       # all tests (engine, pipeline, encoding, mock ComfyUI, server, CLI)
python -m artstudio serve --port 8870             # web studio
python tests/ui_playwright.py                     # UI test of the whole guided flow; start the studio first with an EMPTY
                                                  # workspace and ARTSTUDIO_CODEX="<python> tests/fake_codex.py"
python demo/build_poc.py                          # rebuild proof-of-concept deliverables
python mock_comfyui/server.py --port 8188 [--scenario ok|fail|timeout|disconnect|slow]
python scripts/make_workflow_templates.py         # regenerate bundled ComfyUI templates
python scripts/production_smoke_test.py --comfy URL --checkpoint FILE   # Stage B only, real server
```


## Adding things

- **Procedural asset / builder**: follow **docs/engine-a-guide.md** (call list via `artstudio draw`, or a builder module with
  `DESCRIPTION`, `PARAMS`, `ASSET_TYPE`, `build()`; register in `procedural/__init__.py`; add to tests; look at the contact
  sheet; add the Chinese description to i18n.js). Skill: `skills/procedural-builder-authoring`.
- **Engine tool**: add `t_<tool>` in `artstudio/engine/tools.py` using Atelier's argument names where one exists; test it in
  `tests/test_engine.py`; Atelier showcase recipes in `tests/fixtures/showcase` must keep replaying pixel-identical.
- **Provider**: subclass `providers.base.Provider`, implement `status/capabilities/generate`, register in
  `providers/__init__.py`, add mock-based tests. Mark results with `is_test_fixture` when not real.
- **Workflow template**: prefer importing (UI/CLI). Bundled ones are generated by `scripts/make_workflow_templates.py`
  and must stay `unverified` until Stage B evidence exists.
- **Schema change**: bump the schema version, add a migration step in `Workspace.migrate`, update `docs/asset-schema.md`.

## Versioning and changelog

- Version lives in three places that must match: `VERSION`, `pyproject.toml` (`version`), `artstudio/__init__.py`
  (`__version__`). `tests/test_core.py::VersionTests` checks this.
- Semantic versioning while < 1.0: new feature or breaking change → bump minor (0.x.0); fixes/docs only → patch.
- Every user-visible change goes under `## [Unreleased]` in `CHANGELOG.md` (Added / Changed / Removed / Fixed).
  On release, rename it to `## [x.y.z] — YYYY-MM-DD`, bump all three version strings, and commit.
- If a user-facing feature changes, update both `README.md` and `README.zh-CN.md` (feature table, builder table, CLI).

## Gotchas (learned the hard way)

- **Git:** commit locally only unless the owner asks to push. End commit messages with the attribution lines the session
  provides. When copying the repo between machines with tar, **always exclude `.git`** — an earlier transfer overwrote
  the device repo's `.git` and it had to be rebuilt.
- **Deleting files on the owner's machine** needs explicit delete permission; batch deletions into one request.
- **Tests under the C locale** must still pass (`LC_ALL=C python scripts/run_tests.py`); Chinese CLI args arrive as
  surrogates there and are fixed by `cli._fix_arg`.
- **UI is CSP-strict** (no `unsafe-eval`): Playwright `wait_for_function` fails; use `expect(locator)` instead.
- **Builder QA:** keep art 1–2 px off the canvas edge, or QA reports `source_clipped`. A transparent border is expected
  for round icons (`detect_background` handles it).
- **Engine A parity:** brushes anchor at `size // 2`; `doc_region` rects are inclusive `[x0,y0,x1,y1]`; ellipses use
  Atelier's +0.5 inflation. Changing any of these breaks `tests/fixtures/showcase` replay.
- **New builder checklist:** module in `artstudio/procedural/`, register in `_NAMES`, add `(frames, size)` to
  `EngineATests` in `tests/test_integration.py`, add the Chinese description to `artstudio/web/i18n.js`, add a row to
  both READMEs, add a CHANGELOG entry, look at the contact sheet yourself.
- **Never edit `vibe-game/`** (sibling project in the same parent folder).

## Keep DEVELOPMENT_PROGRESS.md current

After each milestone record: what was completed, what was verified (command + result), decisions, blockers, and
remaining tasks. Use the labels *implemented*, *mock-tested*, *offline-tested*, *production-verified*.
