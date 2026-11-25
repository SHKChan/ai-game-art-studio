# Upstream limitations and how the studio handles them

## Atelier

| Limitation (verified) | Impact | Handling |
|---|---|---|
| No published Windows binary; releases are macOS/Linux; toolchain pinned to Rust 1.98 | Windows users must build from source | `scripts/build-atelier.ps1`; studio auto-detects `upstream/atelier/target/release/atelier.exe`; Atelier shown *unavailable* if missing |
| Pinned 1.98 toolchain could not be downloaded here | Build used rustc 1.97 with `--ignore-rust-version` | All 378 Rust tests + 100/100 showcase replays pass with that build; documented |
| Recipes have no version; tool behaviour changes break replay | Recipes are tied to the upstream commit | Upstream commit recorded; asset stores the recipe and the processed frames (pixels never depend on replay) |
| Tool names/arguments may change between commits | Builders could break on upgrade | Builders only use stable core tools (doc_new/layer/palette/frame/paint_grid/add_tag); integration tests catch drift |
| GIF export is 1-bit alpha; opacity-driven motion dies in GIF | Effects must move pixels | Builders draw fades with pixels; studio GIF writer thresholds alpha and also writes APNG |
| No pose interpolation / no character AI | Complex characters are impractical to draw by tool calls | Characters go through Engine B/C; Atelier is used for props, icons, tiles and effects |
| `tools/tests` showcase-tooling tests fail in this sandbox (fake binary wrapper) | none for the studio | Recorded; Rust tests and real showcase verification pass |

## Pixel Atelier

| Limitation (verified) | Impact | Handling |
|---|---|---|
| Generation only through a logged-in `codex app-server` with built-in imagegen | Not available offline; not portable to other generators | ComfyUI is the primary provider; Codex kept as optional provider |
| Side-view, right-facing, single direction; mirroring by engine flip | No 4/8-direction support | New character master system with independent directions; mirroring optional and explicit |
| Fixed 8-action order (idle→…→knockdown), 4×2 sheets, 8 poses each | Rigid for other games | 12 configurable templates, any frame count, user-defined names |
| Project JSON stores images as base64; canvases limited to 128–320 px; ≤16 actions | Large files, size limits | Files on disk + manifests with hashes; no size caps beyond sanity limits |
| Pixel-only pipeline (forced palette mapping, alpha threshold 220) | No HD illustration support | Separate HD mode (soft alpha, Lanczos, no quantization) sharing alignment/QA/export |
| UI and docs in Chinese; workbench tied to the knight sample | Harder for international users | New English UI; upstream prompts reused verbatim where useful (`pixel_atelier_prompt`) |
| `requirements.txt` pins `Pillow<12` | Conflicts with current Pillow | Upstream tests pass with Pillow 12.3; studio allows `<13`; upstream file untouched |
| No automated test of real generation; one-character case study ("no multi-character pass-rate data") | Quality claims limited | Studio separates technical, visual and engine verification; Stage B smoke test |
| `spritepipe` requires ≤255 colours, binary alpha, poses not touching cell edges | Cannot verify HD output | `qa --spritepipe` only offered for pixel-mode assets; studio QA covers HD |

## Environment limits on the development computer (this run)

- No GitHub access, no GPU, no ComfyUI, no Codex CLI → all AI generation is **mock-tested only** (Stage A).
- Device VM (user's computer) has Python 3.10 + Pillow + numpy + ffmpeg but **no Rust toolchain**: Atelier was built and
  exercised in the cloud build environment (Linux). Windows build must be done on the target machine.
- No Cocos Creator / Godot / Phaser runtime → engine examples are written against documented APIs but not executed.
