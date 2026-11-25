---
name: four-directional-character
description: Produce independent south/east/north/west masters and animations for a top-down RPG character.
---

# Four Directional Character

Produce independent south/east/north/west masters and animations for a top-down RPG character.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Atelier tools are reached through the `atelier` provider — never re-implement drawing in Python image code.

## Required inputs
Locked primary master; direction_mode=four; mirroring decision (default off); per-direction notes for asymmetric gear.

## Recommended workflow
1. Generate one master candidate per direction from the locked primary (`sd-character-reference` workflow, `--direction east` etc.). Never rotate a front image.
2. Approve each direction separately; leave mirroring OFF unless gear is symmetric (then enable it explicitly; west may map to flipped east).
3. Reduced test first: walk east + attack east. Only after they pass QA and visual review, batch the remaining directions with an explicit budget: `generate ... --batch-directions south north west --budget 3`.
4. `character report` must show no missing directions.

## Tool-selection rules
ComfyUI pose/reference workflows; Character Studio direction grid; QA `check_animation_set`.

## Prompt templates
keyframe_prompt(c, template, direction): adds 'three-quarter RPG view, facing screen-right (east, side profile)', identity block, sheet layout (one row, N cells, same scale and ground line).

## Quality criteria
Same proportions/height across directions (compare masters); weapon in the correct hand per direction; no missing direction; consistent ground line.

## Common failure modes
Back view (north) loses identity cues; weapon hand swaps between east/west; mirrored asymmetric gear.

## Recovery strategies
Add explicit per-direction constraints (e.g. 'sword in right hand, visible on screen-left when facing west'); regenerate only that direction; disable mirroring.

## Output specification
masters for 4 directions; animations named <anim> with direction metadata; direction_map in exports.
