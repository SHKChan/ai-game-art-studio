# Third-party notices

## Atelier — `upstream/atelier`
Source: https://github.com/marmikshah/atelier, commit 8ac6adfc784d1e3127060e4f5b58cde1e6c9bf85 (supplied locally).
Used unmodified as an external engine (CLI/MCP). Showcase GIFs/recipes are used as test inputs.

```
MIT License
Copyright (c) 2026 Marmik Shah
```
Full text: `upstream/atelier/LICENSE`. Rust crate dependencies are listed in `upstream/atelier/Cargo.lock` under their own licences.

## Pixel Atelier — `upstream/pixel-atelier`
Source: https://github.com/jinxingtaire/pixel-atelier, commit 15d199f68e6657af0873b3c950525c4bf28eed6f (supplied locally).
Imported unmodified as a library (`spritepipe`, `bridge/production.py`, `bridge/rpc.py`); its knight example art is used
as genuine sample input and as mock-server fixtures (always labelled).

```
MIT License
Copyright (c) 2026 Pixel Character Pipeline contributors
```
Full text: `upstream/pixel-atelier/LICENSE`.

## Python packages
- Pillow (MIT-CMU / HPND) — image I/O and processing.
- NumPy (BSD-3-Clause) — array processing.
- Playwright (Apache-2.0) — optional, UI tests only.

## Concepts / formats referenced (no code copied)
- ComfyUI server API (GPL-3.0 project; only its documented HTTP/WebSocket API is used; no ComfyUI code is included).
- TexturePacker JSON-hash and cocos2d plist (format 2) atlas formats.
