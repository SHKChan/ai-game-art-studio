# Engine A guide — making new procedural assets

For agents and developers. Engine A is the studio's own layered pixel engine (`artstudio/engine`). Its call format
is compatible with the Atelier editor — `{"name": <tool>, "arguments": {...}}`, one call per step — so recipes
recorded by Atelier replay unchanged (tested pixel-identical on Atelier's showcase recipes).

## 1. Pick a route

| Situation | Route | Command |
|---|---|---|
| One asset, drawn once | **Call list** (JSONL) | `python -m artstudio draw my.jsonl --project P --name "Gem" --type icon` |
| A family of assets with variants (colours, sizes, elements) | **Builder** (Python module) | `python -m artstudio procedural <builder> --project P --params '{...}'` |
| Re-create an existing drawing | **Replay** a `.recipe` | `python -m artstudio replay doc.recipe --project P` |

Rule of thumb: if you will make it a second time with different settings, write a builder.

## 2. Tools (`artstudio/engine/tools.py`)

| Tool | Main arguments |
|---|---|
| `doc_new` | `name, width, height` (first call; later calls use `"doc_id": "$DOC"`) |
| `doc_palette` | `op: set, colors: ["#rrggbb", …]` · `op: report` |
| `doc_layer` | `op: add|rename|set|delete|duplicate|move, index, name, visible, opacity, to_index` |
| `doc_frame` | `op: add|duration|delete|insert|duplicate|move, frame, count, duration_ms, copy_from, to_index` |
| `doc_paint_grid` | `layer, frame, frame_to, x, y, legend {char: palette index or colour}, rows [...], replace` |
| `doc_draw` | `op: pencil|line|rect|ellipse|polyline|polygon|stroke|fill|fill_cel|clear_cel`, coordinates, `color`, `fill`, `erase`, `frame_to` |
| `doc_fx` | `op: outline|flip|shift|replace_color` |
| `doc_region` | `op: clear|move, rect [x0,y0,x1,y1] (inclusive), offset [dx,dy]` |
| `doc_rescale` | `factor` (integer, nearest) |
| `doc_add_tag` | `name, from, to` |
| `doc_look`, `doc_export`, `doc_info`, `list_docs`, `delete_doc` | inspection / export |

Colours may be palette indices (preferred: keeps the palette locked), `#rrggbb(aa)` or `[r,g,b,a]`.
Unknown tools/arguments fail loudly — fix the call, do not work around it.

## 3. Call list example (one-off icon)

```jsonl
{"name":"doc_new","arguments":{"name":"red-gem","width":16,"height":16}}
{"name":"doc_palette","arguments":{"doc_id":"$DOC","op":"set","colors":["#1a1020","#7a1028","#d02a40","#ff8090","#ffffff"]}}
{"name":"doc_layer","arguments":{"doc_id":"$DOC","op":"rename","index":0,"name":"gem"}}
{"name":"doc_paint_grid","arguments":{"doc_id":"$DOC","layer":0,"frame":0,"x":4,"y":3,"legend":{"o":0,"d":1,"m":2,"l":3,"w":4},
 "rows":["..oooo..",".olwmmo.","olwmmmdo","ommmmddo",".ommddo.","..oddo..","...oo..."]}}
```

## 4. Builder recipe (repeatable assets)

Create `artstudio/procedural/<name>.py`:

```python
from .raster import DocBuilder, Grid, ramp_pick

DESCRIPTION = "One sentence shown in the UI."          # add a Chinese line to artstudio/web/i18n.js too
ASSET_TYPE = "icon"                                    # item | icon | effect | tileset | environment | ui | animation
PARAMS = {"size": {"type": "int", "default": 32}, "element": {"type": "string", "default": "ice", "enum": ["ice", "fire"]}}

def build(size=32, element="ice", **_):
    d = DocBuilder("my-asset", size, size)
    d.palette([...])                  # 1. lock the palette first; refer to colours by index
    body = d.layer("body")            # 2. one layer per part that moves, glows or may be recoloured
    g = Grid(size, size)              # 3. compute pixels in Python (shapes, shading, noise)…
    g.ellipse(16, 16, 10, 10, 2)
    d.paint(g, body, 0)               # 4. …and let the engine paint them (doc_paint_grid)
    return d.calls
```

Then add the name to `_NAMES` in `artstudio/procedural/__init__.py`.

`Grid` helpers: `rect, line, polygon, ellipse, field(fn), outline(colour), merge, copy`.
Shading: `ramp_pick(t, ramp, x, y, dither)` maps 0..1 to a dark→light ramp with ordered dithering.
Noise: `vnoise(x, y, seed)`, `hash01(...)` — deterministic, so the same params give the same pixels.
Animation: `d.add_frames(n - 1, ms)`, paint each frame, `d.duration(i, ms)`, `d.tag(name, 0, n - 1)`.

**Worked example:** `artstudio/procedural/ice_spear.py` (skill icon, 3 element variants):
frame layer (rim lit top-left, dark outline) → spear layer (shaft + pointed head shaded across its width,
contour only against the background) → glow layer (sparkle pixels, not alpha).

## 5. Art rules (from the Atelier and Pixel Atelier guides)

- **Silhouette first.** It must read in one flat colour at 1×. Detail last, only on the focal area.
- **Light from one direction** (top-left by convention) across a whole asset set.
- **Layers per part.** Body, moving part, glow/effects separately — fixes stay local.
- **Fix the region, never the frame.** Change the one wrong area; don't redraw everything.
- **Motion with pixels, not alpha.** GIF has 1-bit alpha; fades must shrink/recolour.
- **Leave a 1–2 px margin.** QA flags pixels touching the canvas edge.
- **Effects:** strong anticipation frame, fast action, held impact, then dissipation.
- **Characters:** don't hand-draw complex characters here — use Engine B (ComfyUI) or C (import).

## 6. Verify before you hand over

1. `python -m artstudio procedural <name> --project P` → note the asset id.
2. `python -m artstudio contact-sheet --project P --asset <id> --out sheet.png --scale 6` — **look at it.**
3. `python -m artstudio qa --project P --asset <id>` → deterministic status `passed`
   (pixel-mode animations: add `--spritepipe` → `TECHNICAL_VERIFIED`).
4. Determinism: `python -m artstudio replay <asset>/source/doc.recipe --project P` must give identical pixels.
5. Add the builder to `tests/test_integration.py` (`EngineATests.test_builders_produce_editable_documents`).
6. Record a visual review (UI → Animation Studio) — technical checks never prove the art is good.
