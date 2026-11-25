# Limitations

## Engine A (own pixel engine, Atelier-compatible)

| Limitation | Handling |
|---|---|
| Implements the studio subset of Atelier's 27 tools (new, info, layer, frame, palette set/report, paint_grid, draw, fx outline/flip/shift/replace_color, region, rescale, add_tag, seam_report, look, export, list, delete). Analysis tools (critique, components, anim_audit, frame_diff, dump_region, ref, checkpoint, font) are not implemented. | Unknown tools fail loudly. Atelier recipes using only the subset replay pixel-identical (tested on showcase potion/slash). Studio QA, contact sheets and versions cover inspection. |
| Draw primitives `stroke aa`, `curve`, `stamp`, `gradient`, `noise`, `scatter`, `text`, palette `generate/snap/swap` are absent | Builders compute such effects in Python (`raster.vnoise`, `ramp_pick`) and paint them |
| Assets made by the earlier Rust-Atelier integration keep their frames, but their documents were in Atelier's own store | Replay `source/doc.recipe` to rebuild an editable Engine A document |

## Character pipeline / Engine B

| Limitation | Handling |
|---|---|
| No GPU/ComfyUI/Codex on the development computer | ComfyUI path mock-tested only; Stage B guide + smoke test |
| Knight sample art is demonstration-only | `samples/knight/NOTICE.md`; never ship it |
| `spritepipe` needs ≤255 colours, binary alpha, poses not touching cell edges | Offered for pixel-mode assets only; studio QA covers HD |
| Plain img2img identity preservation is limited | Import IPAdapter/reference workflows (Generation → Import) |

## Environment

- Windows launch scripts were written but not executed here (no Windows host).
- Cocos Creator / Godot / Phaser runtimes not available: export files validated structurally; Cocos TS compiled with `tsc --strict` against an API stub only.
- Bundled ComfyUI workflows are `unverified`; `svd-image-to-video` and `rembg-inspyrenet` need nodes absent from the mock.
