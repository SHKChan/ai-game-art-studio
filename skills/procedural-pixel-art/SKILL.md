---
name: procedural-pixel-art
description: Draw a layered, replayable pixel-art sprite or prop with Engine A through a builder or raw tool calls.
---

# Procedural Pixel Art

Draw a layered, replayable pixel-art sprite or prop with Engine A through a builder or raw tool calls.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Procedural pixels come from Engine A (`procedural` provider, docs/engine-a-guide.md) — never paste pixels in with ad-hoc image code.

## Required inputs
Subject brief; canvas size (e.g. 32/48/64 px); palette or colour intent; layer plan (parts that move or recolour); frame count if animated.

## Recommended workflow
1. Check `python -m artstudio status` → provider `procedural` is built in (always available).
2. If a builder fits (`python -m artstudio builders`), run `python -m artstudio procedural <builder> --project P --params '{...}'`.
3. Otherwise write calls (list of {name, arguments} with "$DOC") following docs/engine-a-guide.md: doc_new → lock palette (doc_palette op=set) → one layer per moving/recolourable part → silhouette → block masses → details → audit.
   Save the calls as JSONL and run `python -m artstudio draw calls.jsonl --project P --name "..." --type icon|item|effect|tileset` to bring the drawing into the studio (Atelier-format recipes also replay: `python -m artstudio replay x.recipe`).
4. Inspect: `contact-sheet`, Procedural Studio inspector (layers, cels, palette), `qa`.
5. Fix the failing REGION on its layer (doc_dump_region, one doc_draw) — never redraw the frame.
6. Approve with `decide approved`; keep `source/doc.recipe` (replayable).

## Tool-selection rules
Engine A (`procedural` provider) for every pixel; builders compute instructions deterministically and the engine paints them (doc_paint_grid with palette indices). Use `replay` to prove reproducibility. Do NOT use the image-generation providers for icons/props that Atelier can draw.

## Prompt templates
Builder params are the prompt. For new builders write a one-paragraph brief in this style: 'Effect — a particle explosion: bright core flashes, debris arcs outward... 10 frames, 1 s at 10 FPS, 32x32, 6 colours, transparent background.'

## Quality criteria
Reads at 1x in pure silhouette; locked palette (doc_palette op=report clean); ≥2 layers; transparent background; no pixels on the canvas edge; deterministic QA `passed`; recipe replay pixel-identical.

## Common failure modes
Detailing before the silhouette reads; one flat layer; anti-aliased strokes on a locked palette (off-palette pixels); motion driven by alpha (dies in GIF); pencil used for lines (dots).

## Recovery strategies
doc_checkpoint before risky ops; doc_dump_region then a single targeted op; split layers with doc_layer duplicate+erase; for GIF fades change pixels not alpha.

## Output specification
Animation asset (type item/effect/icon) with `procedural.doc_id`, `source/doc.recipe`, frames in `frames/`, deterministic QA result; editable document in `<project>/atelier/documents/<doc_id>`.
