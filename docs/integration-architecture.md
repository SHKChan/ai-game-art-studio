# Architecture

```
            ┌──────────── Web UI (artstudio/web, vanilla ES modules, en / zh-CN) ────────────┐
            │ Library · Character · Animation · Procedural · Import · Generation · Export     │
            └───────────────▲─────────────────────────────────────────────────────────────┘
                            │ JSON over loopback HTTP (cookie token, Host/Origin checks, X-Studio-Lang)
 Agent CLI ──► artstudio.service.Studio ◄── artstudio.server.app (stdlib ThreadingHTTPServer)
 (JSON out)        │        └── JobQueue (threads, persisted jobs, budget, cancel/retry/resume)
   ┌───────────────┼────────────────────────────────────┬─────────────────────────────────┐
   │ Providers (runtime-checked)                        │ Processing / QA / Export         │
   │  ProceduralProvider ──► artstudio.engine (Engine A) │  processing/frames.py (pixel+HD) │
   │      builders: artstudio.procedural                │  pipeline/spritepipe.py (checker)│
   │  ComfyUIProvider ──► ComfyUI HTTP + /ws            │  qa/ (deterministic + visual)    │
   │  ExternalAssetProvider (+ ffmpeg)                  │  export/ (atlas, plist, JSON…)   │
   │  MockGenerationProvider (fixtures)                 │  i18n.py (server/CLI messages)   │
   │  CodexImageProvider ──► providers/codex_rpc.py     │                                  │
   └────────────────────────────────────────────────────┴─────────────────────────────────┘
                   │
         Workspace (local files, versioned JSON schemas, UTF-8 everywhere)
```

## Decisions

1. **Self-contained Python codebase.** The repository started by driving two external projects (Atelier's Rust binary,
   Pixel Atelier's Python modules). With the owner's approval it was reorganised: Engine A was re-implemented in Python
   and the Pixel Atelier code actually used was moved into `artstudio/` (MIT notices kept). Benefits: no Rust toolchain
   or external binary on Windows, one dependency set (Pillow + numpy), and full control over encoding and i18n.
2. **Engine A keeps Atelier's call format.** Tools and argument names follow Atelier (`doc_new`, `doc_paint_grid`,
   `doc_draw` …), documents keep `doc.json + cels/ + doc.recipe`. Compatibility is tested: Atelier showcase recipes
   (potion, slash) replay pixel-identical to Atelier's own GIFs, and all builders render identically to the earlier
   Atelier-rendered proof-of-concept frames. Unsupported Atelier tools fail with a clear error.
3. **Builders = deterministic instruction generators** (`artstudio/procedural`): compute pixels with `raster.Grid`,
   emit `doc_paint_grid` calls on separate layers/frames; the engine paints, stores and records the recipe.
4. **One asset model.** Every image asset has an `animation` block; source frames are preserved, processed frames are
   reproducible from the recorded normalisation; edits snapshot versions.
5. **Group alignment** (`normalize_group`): one scale per group, explicit anchors, airborne exemption, canvas expansion.
6. **Providers never substitute each other**; mock output is flagged `is_test_fixture` everywhere.
7. **ComfyUI is model-agnostic**: imported API-format workflows, mappings derived and validated against `/object_info`.
8. **Encoding:** all text I/O is explicit UTF-8 (enforced by a test); POSIX argv recovery for non-UTF-8 locales; the
   launcher also enables Python UTF-8 mode as a safety net.
9. **Bilingual:** UI via exact-text dictionary + MutationObserver (`web/i18n.js`); server/CLI errors via codes and
   English-template patterns (`artstudio/i18n.py`); generation prompts in English (default) or Chinese per project.
10. **Security:** loopback by default, session cookie, Host allow-list, Origin check, size limits, `safe_join`, no shell.
11. **Standard export formats only:** TexturePacker JSON-hash, cocos2d plist format 2, documented generic JSON.

## Extension interfaces

`Provider` (`providers/base.py`): `status()`, `capabilities()`, `generate()`, `cancel()`; register in
`providers/Registry`. Engine tools: `artstudio/engine/tools.py` (`t_<name>`). Builders: `docs/engine-a-guide.md`.
