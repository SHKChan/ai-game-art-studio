"""Prompt templates for Engine B (reference-driven character generation).

Prompts carry explicit identity constraints (proportions, clothing, hair, weapon geometry, palette,
camera direction) taken from the locked character master, following Pixel Atelier's workflow rules:
one action per sheet, fixed grid order, whole character per cell, transparent background, safe margins.
"""
from __future__ import annotations

from .animation import TEMPLATES

DIRECTION_TEXT = {
    "right": "facing right (side view)", "left": "facing left (side view; drawn independently, not mirrored)",
    "south": "facing the camera (front / south)", "north": "facing away from the camera (back / north)",
    "east": "facing screen-right (east, side profile)", "west": "facing screen-left (west, side profile, drawn independently)",
    "south_east": "three-quarter front facing down-right (south-east)", "south_west": "three-quarter front facing down-left (south-west)",
    "north_east": "three-quarter back facing up-right (north-east)", "north_west": "three-quarter back facing up-left (north-west)",
    "none": "",
}
STYLE_TEXT = {
    "pixel": "crisp pixel art, hard 1px outline, limited palette, no anti-aliasing, no blur",
    "hd": "high-resolution hand-painted 2D game sprite, clean silhouette, soft shading, anti-aliased edges",
}
BASE_NEGATIVE = ("background, scenery, floor, ground shadow, text, watermark, grid lines, frame borders, cropped body, "
                 "cut-off weapon, extra limbs, extra fingers, duplicate character, different outfit, different hairstyle, "
                 "different weapon, blurry, jpeg artifacts")


def character_block(c: dict) -> str:
    parts = [f"Character: {c['name']}. {c.get('description', '')}".strip()]
    if c.get("proportions"):
        parts.append("Proportions: " + ", ".join(f"{k} {v}" for k, v in c["proportions"].items()))
    if c.get("clothing"):
        parts.append("Clothing: " + ", ".join(c["clothing"]))
    if c.get("accessories"):
        parts.append("Accessories: " + ", ".join(c["accessories"]))
    if c.get("weapon"):
        parts.append("Weapon (keep exact geometry and grip): " + ", ".join(f"{k}: {v}" for k, v in c["weapon"].items()))
    if c.get("palette"):
        parts.append("Use only this palette: " + " ".join(c["palette"][:32]))
    if c.get("constraints"):
        parts.append("Must keep: " + "; ".join(c["constraints"]))
    return " ".join(parts)


def keyframe_prompt(c: dict, template: str, direction: str, mode: str | None = None, frame_index: int | None = None,
                    note: str = "") -> dict:
    t = TEMPLATES[template]
    mode = mode or c.get("art_style", "pixel")
    style = (c.get("visual_style") or "") + "; " + STYLE_TEXT[mode]
    camera = {"side": "side view", "top_down": "top-down RPG three-quarter view", "three_quarter": "three-quarter RPG view",
              "isometric": "isometric view", "front": "front view"}.get(c.get("camera", "side"), "")
    if frame_index is None:
        poses = "; ".join(f"{i + 1}: {p}" for i, p in enumerate(t["poses"]))
        layout = (f"One transparent PNG sprite sheet, {len(t['poses'])} cells in a single row, equal cell size, left to right in this order: {poses}. "
                  "Exactly one complete character per cell, same scale and ground line in every cell, generous empty margin around body, weapon and effects.")
    else:
        layout = f"Single pose: {t['poses'][frame_index]}. One complete character, transparent background, empty margin on all sides."
    pos = (f"{character_block(c)} Action: {template.replace('_', ' ')}. {camera}, {DIRECTION_TEXT.get(direction, direction)}. "
           f"Style: {style}. {layout} Identical face, hair, outfit, proportions and weapon to the reference image."
           + (f" Revision: {note}" if note else ""))
    neg = BASE_NEGATIVE + (", " + ", ".join(c["negative_constraints"]) if c.get("negative_constraints") else "")
    return {"positive": pos, "negative": neg, "template": template, "direction": direction, "mode": mode}


def master_prompt(c: dict, direction: str = "south") -> dict:
    mode = c.get("art_style", "pixel")
    pos = (f"{character_block(c)} Character master reference, neutral standing pose, full body, "
           f"{DIRECTION_TEXT.get(direction, direction)}. Style: {(c.get('visual_style') or '')}; {STYLE_TEXT[mode]}. "
           "Transparent background, centred, full body visible with margin.")
    return {"positive": pos, "negative": BASE_NEGATIVE, "direction": direction, "mode": mode}
