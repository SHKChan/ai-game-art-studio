@tool
extends EditorScript
## Godot 4 — builds a SpriteFrames resource from an AI Game Art Studio export (<name>.anim.json + atlas PNG).
## Edit the three paths below, then File > Run in the Script editor.
## Each frame becomes an AtlasTexture region; per-frame durations are exact because the animation
## speed is set to 1000 FPS and each frame's relative duration equals its milliseconds.
## Trimmed frames: AtlasTexture.margin restores the original frame size/offset so the pivot stays put.
## Status: written against the Godot 4 API, not executed on the development machine (no Godot installed).

const MANIFEST := "res://art/game_assets.anim.json"
const ATLAS := "res://art/game_assets_atlas.png"
const OUTPUT := "res://art/game_assets_frames.tres"

func _run() -> void:
	var data = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
	var tex: Texture2D = load(ATLAS)
	var sf := SpriteFrames.new()
	sf.remove_animation("default")
	for anim in data["animations"]:
		var key: String = anim["key"]
		sf.add_animation(key)
		sf.set_animation_loop(key, anim["loop"]["enabled"])
		sf.set_animation_speed(key, 1000.0)
		for f in anim["frames"]:
			var at := AtlasTexture.new()
			at.atlas = tex
			var r = f["atlas"]
			at.region = Rect2(r["x"], r["y"], r["w"], r["h"])
			var src = f["source_size"]
			var off = f["trim_offset"]
			at.margin = Rect2(off[0], off[1], src[0] - r["w"], src[1] - r["h"])
			sf.add_frame(key, at, float(f["duration_ms"]))
	ResourceSaver.save(sf, OUTPUT)
	print("Saved ", OUTPUT, ". Set AnimatedSprite2D.offset = -pivot_px + size/2 (centered) to put the root at the node origin.")
