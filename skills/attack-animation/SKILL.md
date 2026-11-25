---
name: attack-animation
description: Produce attack/combo animations with anticipation, action, impact, follow-through and recovery, plus hit events.
---

# Attack Animation

Produce attack/combo animations with anticipation, action, impact, follow-through and recovery, plus hit events.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Atelier tools are reached through the `atelier` provider — never re-implement drawing in Python image code.

## Required inputs
Locked master + weapon spec; template `attack` or `combo_attack`; 6-10 frames per direction; desired hit timing.

## Recommended workflow
1. Write the action brief (support foot, hip/shoulder drive, blade path, impact frame) — see upstream Pixel Atelier templates/action-brief.md.
2. Generate the sheet; keep wide cells so the blade and trail are never cropped.
3. Import with anchor `source` (preserve lunge) and canvas expansion; verify no `clipped_sprite`/`source_clipped`.
4. Place `hit` events at impact frames; tune durations (fast action, held impact, slower recovery).
5. Optionally attach an Atelier effect layer (`hybrid`).

## Tool-selection rules
ComfyUI pose_keyframe for single broken poses; Atelier for slash/impact effects; Animation Studio events and comparison.

## Prompt templates
Template poses: 'ready; anticipation wind-up; anticipation peak; action swing; impact; follow-through; recovery; return to ready'. Add weapon geometry and 'both hands on the same straight hilt' constraints.

## Quality criteria
Readable anticipation; impact frame held ≥60 ms; blade length constant; no cropped weapon/effect; events on the contact frame.

## Common failure modes
Weapon changes length; blade resets to shoulder between combo hits; impact hidden by blur; centred-per-frame alignment removing the lunge.

## Recovery strategies
Regenerate the specific pose with the weapon note; use inpainting workflow for the weapon region; keep anchor `source`.

## Output specification
Animation `attack`/<direction> with phases + hit events; optional effect layer metadata.
