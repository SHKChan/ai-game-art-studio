---
name: walking-animation
description: Produce a walk cycle with contact, down, passing and up poses for each direction.
---

# Walking Animation

Produce a walk cycle with contact, down, passing and up poses for each direction.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Procedural pixels come from Engine A (`procedural` provider, docs/engine-a-guide.md) — never paste pixels in with ad-hoc image code.

## Required inputs
Locked direction master; 4-8 frames; template `walk`; step events.

## Recommended workflow
1. Reduced test: one direction first. Generate an 8-cell sheet (contact, down, passing, up ×2).
2. Import/auto-slice; normalise with anchor `support_foot` — keeps the planted foot fixed while the body bobs.
3. Verify phases (frame labels), footstep events at contact frames, loop.
4. Selective regeneration for broken frames (`regenerate --index i`); manual replacement if you have a fixed frame.

## Tool-selection rules
ComfyUI sheet or pose workflow; Import Studio auto-slice; Animation Studio; QA anchor_discontinuity/jitter checks.

## Prompt templates
Template poses: 'contact (right foot forward), down, passing, up, contact (left foot forward), down, passing, up'. One row, equal cells, same ground line.

## Quality criteria
Alternating legs; arms counter-swing; vertical bob 1-3 px kept; no foot sliding on grounded frames; consistent scale.

## Common failure modes
Same leg forward twice; frames forced to identical bboxes (kills bob); sheet cells in the wrong order.

## Recovery strategies
Reorder with `frames move`; mark frames via phase labels; regenerate the specific pose; never per-frame rescale.

## Output specification
Animation `walk`/<direction>, loop, footstep events.
