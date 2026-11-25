# Agent skills

Reusable production skills for agents (Claude Code, Codex, any MCP/CLI agent). Each folder holds a
`SKILL.md` with YAML front matter (name, description) and the sections: required inputs, workflow,
tool-selection rules, prompt templates, quality criteria, failure modes, recovery, output spec.

They adapt the upstream guides — Atelier's `crates/atelier/skills/{sprite,scene,review}.md` (drawing
loop, layer discipline, region fixes, review lenses) and Pixel Atelier's `docs/workflow.md`,
`templates/action-brief.md`, `templates/review-checklist.md` (master locking, whole-character poses,
semantic alignment, separate technical/visual/engine verification) — to this studio's CLI and UI.

Install for Claude Code: copy the folders into `.claude/skills/` of a project (or `~/.claude/skills/`).
The upstream Atelier skills remain available via `atelier skills install`.
