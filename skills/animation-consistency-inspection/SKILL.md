---
name: animation-consistency-inspection
description: Inspect animations: deterministic QA plus a separate, explicitly probabilistic visual review.
---

# Animation Consistency Inspection

Inspect animations: deterministic QA plus a separate, explicitly probabilistic visual review.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Procedural pixels come from Pixel Forge (`procedural` provider, docs/pixel-forge-guide.md) — never paste pixels in with ad-hoc image code.

## Required inputs
Animation asset(s); character master; expected directions/animations.

## Recommended workflow
1. `qa --project P --asset A` (empty/opaque/background/clipping/canvas/duplicates/scale/anchor/jitter/durations/events).
2. Pixel-art: optionally `qa --spritepipe` to run the whole-character spritepipe TECHNICAL_VERIFIED checker.
3. `contact-sheet` + Animation Studio at game scale, then half speed; onion skin; compare against the master.
4. Record visual findings (identity drift, clothing, weapon deformation, limbs, proportions, style, motion, transitions) as a visual review — never infer them from deterministic results.
5. `character report` for missing directions; approve/reject.

## Tool-selection rules
artstudio.qa (deterministic), qa.visual (probabilistic record; no model bundled), artstudio.pipeline.spritepipe.

## Prompt templates
Visual review checklist (whole-character review checklist): identity, proportions, weapon length/grip, support foot, phases, loop seam, effects not duplicated.

## Quality criteria
Deterministic `passed` AND a recorded visual review; technical pass alone is never reported as visual consistency.

## Common failure modes
Treating TECHNICAL_VERIFIED as approval; chasing one jitter metric while gait breaks.

## Recovery strategies
Fix the root cause (regenerate pose, re-anchor) instead of tuning thresholds; document known issues on the asset.

## Output specification
qa.deterministic + qa.visual + qa.manual on the asset manifest.
