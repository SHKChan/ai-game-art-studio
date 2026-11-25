---
name: sprite-sheet-processing
description: Turn an external sprite sheet into a clean, aligned animation (Engine C).
---

# Sprite Sheet Processing

Turn an external sprite sheet into a clean, aligned animation (Engine C).

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Procedural pixels come from Engine A (`procedural` provider, docs/engine-a-guide.md) — never paste pixels in with ad-hoc image code.

## Required inputs
Sheet PNG; grid (cols×rows/cell size) or auto-detect; background type; art mode; anchor policy.

## Recommended workflow
1. Inspect the sheet: transparent? solid/checker background? baked labels?
2. `import sheet.png --opts '{"slicing":{"method":"grid","cols":4,"rows":2},"background":{"method":"auto"},"mode":"pixel","normalize":{"anchor":"source"}}'` (or method auto with merge_px for detached weapons).
3. If it is upscaled 'fake pixel art', add `depixelate_block: "auto"`.
4. Compare before/after; fix order with `frames move`; QA; export.

## Tool-selection rules
Import & Processing Studio; processing.frames (slice_grid/slice_auto/remove_background/normalize_group).

## Prompt templates
n/a (deterministic). Record the source and licence in the asset name/tags.

## Quality criteria
Correct frame count/order; transparent; consistent scale; motion preserved; no cropping.

## Common failure modes
Grid misaligned with uneven sheets; checkerboard baked into pixels; auto-slice splitting a weapon from its body.

## Recovery strategies
Use cell/margin/spacing; background method checker; increase merge_px; switch to manual grid.

## Output specification
Animation asset with source rects, preserved source frames (`frames_src/`), processed frames, processing record.
