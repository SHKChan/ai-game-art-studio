---
name: eight-directional-character
description: Extend a four-direction character to eight directions (adds diagonals) without rotation hacks.
---

# Eight Directional Character

Extend a four-direction character to eight directions (adds diagonals) without rotation hacks.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Atelier tools are reached through the `atelier` provider — never re-implement drawing in Python image code.

## Required inputs
Approved four-direction masters; direction_mode=eight; budget for 4 extra masters + animations.

## Recommended workflow
1. Generate diagonal masters (south_east, south_west, north_east, north_west) referencing the two neighbouring cardinal masters.
2. Approve individually; check proportions against cardinals with the contact sheet.
3. Produce animations per diagonal with an explicit batch budget; consider mirroring only for symmetric designs.
4. Export with `--character C` so the direction_map includes flip_x only where mirroring is enabled.

## Tool-selection rules
ComfyUI reference workflows; Character Studio; export direction_map; Cocos TopDownCharacterController (directions=8).

## Prompt templates
'three-quarter front facing down-right (south-east)'; include both neighbour masters as references when the workflow supports multiple images.

## Quality criteria
Smooth facing transitions when rotating through all 8; equal on-screen height; consistent pivot.

## Common failure modes
Diagonals drift in style; mixed camera angles; diagonal frames scaled differently.

## Recovery strategies
Regenerate with stronger reference weighting/lower denoise; normalise with the same target_height as cardinals (one group scale).

## Output specification
8 masters, 8× animation assets per action, complete direction_map.
