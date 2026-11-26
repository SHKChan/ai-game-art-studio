# Agent skills

Reusable production skills for agents (Claude Code, Codex, any CLI-capable agent). Each folder holds a
`SKILL.md` with YAML front matter (name, description) and the sections: required inputs, workflow,
tool-selection rules, prompt templates, quality criteria, failure modes, recovery, output spec.

They adapt the drawing guides of the Atelier editor (layer discipline, silhouette first, region fixes, review lenses)
and Pixel Atelier's character workflow (master locking, whole-character poses, semantic alignment, separate
technical/visual/engine verification) to this studio's CLI and UI. New Pixel Forge assets: see
`procedural-builder-authoring` and `docs/pixel-forge-guide.md`.

Install for Claude Code: copy the folders into `.claude/skills/` of a project (or `~/.claude/skills/`).
