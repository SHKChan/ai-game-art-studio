---
name: character-master-creation
description: Establish a locked character identity (master reference) before producing any animation.
---

# Character Master Creation

Establish a locked character identity (master reference) before producing any animation.

CLI: `python -m artstudio <command>` (JSON on stdout). Web: http://127.0.0.1:8870. Procedural pixels come from Engine A (`procedural` provider, docs/engine-a-guide.md) — never paste pixels in with ad-hoc image code.

## Required inputs
Concept or reference image(s); name/description; proportions (head:body, height px); clothing, accessories, weapon geometry and grip; palette; camera; art style (pixel/hd); negative constraints.

## Recommended workflow
1. `character create --project P --name ... --directions four|eight|side2 --style pixel|hd --patch '{...identity fields...}'`.
2. Add concept art (`add-image --kind concept`).
3. Generate candidates: `generate --kind master_candidate --provider comfyui --workflow sd-text-to-image|sd-character-reference --character C --direction south` (or upload candidates).
4. Review candidates side by side; `character review --decision approved|rejected` with a reason. Approval copies the image to masters/ and LOCKS it.
5. Freeze palette (update `palette`, `palette_frozen: true`).
6. Only an explicit `replace-master --reason` changes a locked master; history records it.

## Tool-selection rules
ComfyUI (primary) or Codex (optional) for candidates; Character Studio for review; never approve TEST FIXTURE candidates for production.

## Prompt templates
Built by `artstudio.prompts.master_prompt`: character block (description, proportions, clothing, weapon, palette, must-keep) + 'Character master reference, neutral standing pose, full body, facing the camera (front / south). Style: ... Transparent background, centred, full body visible with margin.' Negative: background, text, cropped body, extra limbs, different outfit/hair/weapon...

## Quality criteria
Full body visible with margin; transparent background; matches every identity field; weapon geometry measurable; one candidate explicitly approved and locked.

## Common failure modes
Approving before the weapon/proportions are settled; changing a locked master silently; mixing candidates of different art styles.

## Recovery strategies
Reject and regenerate with a revision note; if a later action reveals a master problem, replace the master with a reason and re-audit all actions that used the old one.

## Output specification
character.json (schema character/1) with locked `masters.primary` (and directional masters), candidates with status, history.
