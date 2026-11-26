# Asset, character and workflow schemas (version 1)

Machine-readable schemas (JSON Schema 2020-12 subset) live in `artstudio/schema/`:

- `asset.schema.json` — one asset (`asset.json`)
- `character.schema.json` — one character master record (`character.json`)
- `workflow.schema.json` — one ComfyUI workflow template

They are enforced on every save (`artstudio.schema.require_valid`), so a workspace can be validated by any
external JSON-Schema tool as well.

## Workspace layout

```
<workspace>/studio.json                      {"format","schema_version":1,"app_version","created_at"}
<workspace>/projects/<pid>/project.json
<workspace>/projects/<pid>/characters/<cid>/character.json   masters/ candidates/ concept/
<workspace>/projects/<pid>/assets/<aid>/asset.json           source/ frames_src/ frames/ versions/vN/
<workspace>/projects/<pid>/exports/<eid>/export_manifest.json + files
<workspace>/projects/<pid>/engine/documents/<doc-uuid>/      Pixel Forge editable documents (doc.json, cels/, doc.recipe)
<workspace>/jobs/<jid>.json
<workspace>/comfyui/workflows/<wid>.json                     user-imported templates
```

## Asset (key fields)

| field | meaning |
|---|---|
| `schema_version` | 1 |
| `id`, `type`, `name`, `project_id`, `character_id` | identity; type ∈ character_sprite, animation, icon, item, tileset, effect, environment, ui, concept, reference, other |
| `art_style` | `pixel` or `hd` (processing mode) |
| `provider` | `{id, kind, is_test_fixture, details}` — who produced it; fixtures are always flagged |
| `prompt`, `reference_images` | generation prompt (positive/negative/template) and references used |
| `source_files`, `processed_files` | `{path, sha256, role, origin, width, height}` |
| `processing` | `normalize` record (params, scale, canvas, pivot, per-frame offsets) + `import` record |
| `procedural` | `{engine: artstudio-pixel (or atelier for legacy assets), doc_id, recipe, builder, params}` |
| `versions` | `[{version, created_at, note, snapshot: "versions/vN"}]` |
| `status` | draft / candidate / approved / rejected / locked |
| `qa.deterministic` | `{status, issues[], counts, checked_at}` |
| `qa.visual` | `{status, kind: "probabilistic", findings, notes, reviewer}` (never auto-filled from deterministic QA) |
| `qa.manual` | `{decision, note, at}` |
| `exports` | `[{id, format, path, created_at}]` |

### `animation`

| field | meaning |
|---|---|
| `name`, `template`, `direction`, `mirror_of` | e.g. `walk`, template `walk`, `east` |
| `canvas` `[w,h]`, `pivot` `[x,y]` | full-frame canvas and logical root (pixels, y down) |
| `anchor` | `{kind: source|ground|support_foot|torso|custom, ground_y}` |
| `loop` | `{enabled, ping_pong, hold_last}` |
| `frames[]` | `{id, file, source_file, duration_ms, offset, source_rect, source_size, trimmed_rect, origin, status, phase, airborne, generation}` |
| `events[]` | `{frame, type, name?, data?}` (e.g. hit, footstep, release) |
| `layers[]` | `{name, asset_id, role, offset, z, start_ms, anchor_to_event, event_offset_ms}` — independently timed overlays |
| `phases[]` | `{name, from, to}` (anticipation, action, impact, follow_through, recovery / contact, down, passing, up) |

`offset` is where the (scaled) source frame's top-left lands on the canvas — together with
`processing.normalize.scale` it reproduces every processed frame from `frames_src/`.

## Export manifest (`<name>.anim.json`, schema `artstudio.export/1`)

```json
{"animations": [{"key": "walk_east", "name": "walk", "direction": "east", "loop": {"enabled": true},
   "canvas": [64, 64], "pivot_px": [32, 60], "duration_ms": 800,
   "frames": [{"name": "walk_east_00", "duration_ms": 100, "start_ms": 0,
               "atlas": {"x": 2, "y": 2, "w": 22, "h": 40, "page": 0},
               "trim_offset": [21, 20], "trimmed_size": [22, 40], "source_size": [64, 64],
               "pivot_px": [32, 60], "pivot_norm": [0.5, 0.0625], "pivot_norm_trimmed": [0.5, 0.0]}],
   "events": [{"frame": 0, "type": "footstep", "time_ms": 0}], "layers": [], "previews": {"gif": "previews/walk_east.gif"}}],
 "direction_map": {"walk": {"east": {"key": "walk_east", "flip_x": false}, "west": {"key": "walk_east", "flip_x": true}}},
 "contains_test_fixtures": false}
```

`pivot_norm` uses the y-up anchor convention of Cocos Creator / Unity; pixel fields use y-down.

## Migration & backup

`studio.json.schema_version` is checked on open. Older workspaces are migrated in `Workspace.migrate()` (chain of
version steps); newer ones are refused rather than silently rewritten. `python -m artstudio backup out.zip` writes a
complete archive (optionally without exports); `restore` refuses archives with path traversal and only restores into
an empty folder.
