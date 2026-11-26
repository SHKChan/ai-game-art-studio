# Third-party notices / 第三方声明

This repository no longer contains other projects' git checkouts. Code and data derived from them are kept
with their original MIT copyright notices, as the licence requires.

## Atelier — https://github.com/marmikshah/atelier (commit 8ac6adfc784d1e3127060e4f5b58cde1e6c9bf85)
```
MIT License — Copyright (c) 2026 Marmik Shah
```
- **Not included as code.** Pixel Forge (`artstudio/engine`) is an independent Python implementation of a subset of
  Atelier's *tool-call format* (tool and argument names, document/recipe layout) so Atelier recipes replay; primitive
  semantics (rect, ellipse inflation, paint_grid) follow Atelier's documented behaviour.
- `tests/fixtures/showcase/{potion,slash,torch,cat,explosion}.gif`, `{potion,slash}.recipe` — showcase art, MIT.
- Drawing guidance adapted into `skills/` and `docs/pixel-forge-guide.md`.

## Pixel Atelier — https://github.com/jinxingtaire/pixel-atelier (commit 15d199f68e6657af0873b3c950525c4bf28eed6f)
```
MIT License — Copyright (c) 2026 Pixel Character Pipeline contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and
this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```
Derived files (modified; header in each file):
- `artstudio/pipeline/spritepipe.py` ← `spritepipe/core.py` (UTF-8, numpy pixel access)
- `artstudio/prompts_zh_sheet.py` ← `bridge/production.py` (STEPS, generation_prompt, verbatim)
- `artstudio/providers/codex_rpc.py` ← `bridge/rpc.py` (UTF-8 pipes)
- `tests/test_spritepipe.py` ← `tests/test_pipeline.py`
- `samples/knight/` ← `examples/knight` (sample art: demonstration/reproduction only — see `samples/knight/NOTICE.md`)

## Python packages
Pillow (MIT-CMU), NumPy (BSD-3-Clause); Playwright (Apache-2.0, optional, tests only).

## Formats / APIs referenced (no code copied)
ComfyUI server API (the GPL-3.0 ComfyUI code is not included), TexturePacker JSON-hash and cocos2d plist formats.
