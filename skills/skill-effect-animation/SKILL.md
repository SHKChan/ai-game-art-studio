---
name: skill-effect-animation
description: Create spell/skill effects (fire, ice, lightning, smoke, slashes) as Engine A animations and attach them to characters.
---

# Skill Effect Animation

Create spell/skill effects (fire, ice, lightning, smoke, slashes) as Engine A animations and attach them to characters.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Procedural pixels come from Engine A (`procedural` provider, docs/engine-a-guide.md) — never paste pixels in with ad-hoc image code.

## Required inputs
Effect type; size; frames; palette; loop vs one-shot; anchor event on the character animation.

## Recommended workflow
1. Builders `fireball`, `sword_slash` (colour variants) or new calls/builders following docs/engine-a-guide.md (carry motion in pixels not alpha).
2. Rescale by integer factor to match the character's pixel scale (`reprocess --params '{"scale":2}'`).
3. `hybrid --character-asset A --effect-asset E --event hit --offset dx dy` (plus event_offset_ms to land the effect's impact on the hit).
4. Review the composite preview GIF; effect and character keep separate frames/timing in the export.

## Tool-selection rules
Engine A; Animation Studio layers; Export composite preview.

## Prompt templates
'8-frame crescent sword slash: anticipation glint, sweep with tapered trail, bright impact flash, thinning shards; 6-colour azure ramp; transparent.'

## Quality criteria
Effect fades by shrinking/recolouring (GIF-safe); integer scale matches character; impact coincides with the hit event; no edge clipping.

## Common failure modes
Alpha-only fades disappearing in GIF; effect scale mismatched with sprite pixels; effect baked into character frames.

## Recovery strategies
Redraw fade frames with fewer pixels; integer rescale; keep as separate layer.

## Output specification
Effect asset + layer entry {asset_id, offset, z, start_ms, anchor_to_event} on the character animation.
