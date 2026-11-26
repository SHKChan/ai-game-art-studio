---
name: tileset-generation
description: Create seamless terrain tiles and tilesets with Pixel Forge, verified with its seam report.
---

# Tileset Generation

Create seamless terrain tiles and tilesets with Pixel Forge, verified with its seam report.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Procedural pixels come from Pixel Forge (`procedural` provider, docs/pixel-forge-guide.md) — never paste pixels in with ad-hoc image code.

## Required inputs
Tile size (16/32); terrain types; transitions needed (edges/corners); palette; top-down vs side-view.

## Recommended workflow
1. One document per tile family; one frame per tile variant (or a sheet canvas with a grid).
2. Compute base texture in a builder (raster.vnoise + ramp_pick), paint it, then details on their own layer.
3. Check tiling with `doc_seam_report` (horizontal + vertical mismatch must be 0) and `doc_look tile=true`.
4. Build transitions (edges, inner/outer corners) as separate frames; tag them (doc_add_tag).
5. Run it with `procedural`/`draw` and export as sheet + JSON.

## Tool-selection rules
Pixel Forge (doc_seam_report, doc_look tile=true; shading with raster.ramp_pick). Studio exports with `--formats sheet json` (do not trim tiles: use `trim=false`).

## Prompt templates
'32x32 top-down grass tile, 5-colour green ramp, sparse 2-pixel flowers, seamless on all sides, no single-pixel noise.'

## Quality criteria
doc_seam_report mismatch 0 on both axes; no visible repetition in a 3x3 preview; consistent palette across the set.

## Common failure modes
Seams at edges; obvious repeating features; trimming tiles on export (breaks grid alignment).

## Recovery strategies
Edit only the edge columns/rows reported by doc_seam_report; vary features across variants; export untrimmed.

## Output specification
Tileset asset(s) + untrimmed sheet PNG + JSON with tile rects.
