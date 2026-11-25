# Integration architecture

```
            ┌──────────────── Web UI (artstudio/web, no build step) ───────────────┐
            │ Library · Character · Animation · Procedural · Import · Generation · Export │
            └───────────────▲───────────────────────────────────────────────────────┘
                            │ JSON over loopback HTTP (cookie token, Host/Origin checks)
 Agent CLI ──► artstudio.service.Studio ◄── artstudio.server.app (stdlib ThreadingHTTPServer)
 (JSON out)        │        │                                   │
                   │        └── JobQueue (threads, persisted jobs, budget, cancel/retry/resume)
                   │
   ┌───────────────┼──────────────────────────────┬──────────────────────────────┐
   │ Providers (runtime-checked)                  │ Processing / QA / Export      │
   │  AtelierProceduralProvider ──► atelier (MCP stdio | CLI) [upstream, unmodified]
   │  ComfyUIProvider ──► ComfyUI HTTP + /ws      │  processing/frames.py (both modes)
   │  ExternalAssetProvider (+ ffmpeg)            │  qa/ (deterministic) + qa/visual (probabilistic)
   │  MockGenerationProvider (fixtures)           │  export/ (atlas, Cocos plist, TP JSON, GIF/APNG)
   │  CodexImageProvider ──► pixel-atelier/bridge/rpc.py [optional]
   └──────────────────────────────────────────────┴──────────────────────────────┘
                   │
         Workspace (local files, versioned JSON schemas)  ◄── adapters.py ──► pixel-atelier spritepipe / production / knight
```

## Decisions

1. **Python service, not a fork of either UI.** The spec prefers Pixel Atelier's workspace "subject to
   validation". Its server and data model are hard-wired to one side-view, 8-action, Codex-only, Chinese-language
   flow (`pixel-atelier-character/1` caps canvases at 128–320 px, 16 actions, fixed action order, base64 images inside
   project JSON). Extending it to 4/8 directions, HD mode, layers, providers and engine exports would mean rewriting
   most of it. We therefore **reuse its code as libraries** (spritepipe, production prompts/steps, rpc client, knight
   sample) and **keep its workbench runnable unchanged** (`python upstream/pixel-atelier/bridge/server.py`), and
   build a new UI on the same stack (stdlib HTTP + vanilla JS, no build tooling) — same technology, new data model.
2. **Atelier as an independent engine via its supported interfaces.** The Rust engine is never re-implemented.
   The provider prefers a persistent MCP stdio session (fast, one process per job) and falls back to
   `atelier call --stdin --home`. Each studio project has its own Atelier store (`<project>/atelier`).
3. **Procedural builders = deterministic instruction generators.** Builders compute pixel grids (3D-projected chest,
   sphere-shaded potion, noise-driven fire, crescent slash) and emit `doc_paint_grid` calls with palette-index legends
   on separate layers/frames. Atelier performs the drawing, owns the document and records the recipe; the result is
   editable with any Atelier tool and replays byte-for-byte.
4. **One asset model for everything.** Every image asset carries an `animation` block (a static icon is a 1-frame
   animation). Source frames (`frames_src/`) are preserved; processed frames (`frames/`) are re-derivable from the
   recorded normalisation parameters; each edit snapshots `versions/vN`.
5. **Alignment is a group operation.** `normalize_group` applies one scale to all frames, maps a reference point
   (source-relative common point, ground row, support-foot centroid or torso band) to the pivot, exempts airborne frames,
   adds manual integer offsets, and grows the canvas instead of cropping.
6. **Providers never substitute each other.** Generation requests name a provider; unavailable providers fail with
   `provider_unavailable`. Mock output is flagged (`is_test_fixture`) on frames, assets, character candidates and
   exports, and shown with a pink TEST FIXTURE badge.
7. **ComfyUI is model-agnostic.** Workflows are user-supplied API-format graphs wrapped in a template that declares
   inputs, mappings, outputs, required nodes and models. Before each run the bound graph is validated against
   `/object_info` (node classes and COMBO values such as checkpoint names). Bundled templates use only core nodes and
   carry `SET_*_PARAMETER` placeholders that must be bound to the user's model files.
8. **Security.** Loopback by default; session cookie (HttpOnly, SameSite=Strict); Host allow-list; Origin check on
   writes; 200 MB request cap; `safe_join` on every path; zip restore refuses traversal; subprocesses use fixed
   argument lists (Atelier, ffmpeg) — no shell, no UI-controlled executable paths; no secrets in config (an optional
   ComfyUI bearer token is read from an environment variable named in config).
9. **Engine export formats are standard ones.** TexturePacker JSON-hash (Phaser 3 / PixiJS), TexturePacker cocos2d
   plist format 2 (Cocos Creator 3.x SpriteAtlas import) and a documented generic JSON for timing/pivots/events/
   direction maps. Nothing engine-proprietary is invented.

## Extension interfaces

`Provider` (`providers/base.py`): `status()`, `capabilities()`, `generate(GenerationRequest, JobContext)`,
`cancel()`. New providers register in `providers/Registry`. Planned slots (not implemented — no verifiable API
available offline): external image APIs, image-to-video services, skeletal animation tools (e.g. Spine/DragonBones
exporters), additional MCP art tools (an MCP client like `AtelierClient` generalises to any stdio MCP server).

## Data layout

See `docs/asset-schema.md` and `artstudio/workspace.py`.
