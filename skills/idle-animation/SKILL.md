---
name: idle-animation
description: Create a looping idle (breathing) animation that keeps the feet planted.
---

# Idle Animation

Create a looping idle (breathing) animation that keeps the feet planted.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Procedural pixels come from Pixel Forge (`procedural` provider, docs/pixel-forge-guide.md) — never paste pixels in with ad-hoc image code.

## Required inputs
Locked master for the direction; frame count (4-8); timing; loop=true.

## Recommended workflow
1. Template `idle` (6 frames, 120-160 ms). Generate a sheet or import frames.
2. Normalise with anchor `ground` or `support_foot` (feet planted), one group scale.
3. Check loop seam in Animation Studio (onion skin first/last), adjust durations.
4. QA → visual review → approve. Optionally pick a frame as master candidate.

## Tool-selection rules
Generation provider or import; Animation Studio (onion skin, ground line); `frames` ops for durations.

## Prompt templates
keyframe_prompt(c, 'idle', dir): poses 'neutral stance; inhale, chest rises 1px; peak; neutral; exhale; low point'.

## Quality criteria
Feet do not slide; motion ≤ 1-3 px; seamless loop; no duplicate frames (use longer durations instead).

## Common failure modes
Whole body bobbing/jitter; breathing exaggerated; identity drift between frames.

## Recovery strategies
Re-anchor with support_foot; reject drifting frames and regenerate selectively; reduce frame count.

## Output specification
Animation asset `idle`/<direction>, loop enabled.
