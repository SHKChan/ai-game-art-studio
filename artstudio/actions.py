"""Motion Studio action plans: the sequential action frames of one character.

A plan lives in `characters/<cid>/action_plan.json`:

    {"character_id", "identity", "identity_source", "language", "actions": [action...], "updated_at"}
    action = {"id", "name", "preset", "description", "frames", "loop", "direction", "poses", "prompt",
              "negative", "prompt_source", "asset_id", "attempts", "status"}

Each action is generated as ONE horizontal sprite strip (all frames in one image, same character as the
reference), then sliced, aligned and stored as an animation asset. Prompts are written by Codex from the
reference image (`write_prompts(method="codex")`) or from templates; both are editable before generation.
"""
from __future__ import annotations

import copy
import re

from .animation import TEMPLATES
from .codex_cli import CodexError, exec_text, extract_json
from .prompts import (BASE_NEGATIVE, BASE_NEGATIVE_ZH, CAMERA_ZH, DIRECTION_TEXT, DIRECTION_TEXT_ZH, POSES_ZH, STYLE_TEXT,
                      STYLE_TEXT_ZH, character_block, character_block_zh)
from .util import StudioError, now, read_json, write_json

PLAN_FILE = "action_plan.json"
MAX_FRAMES = 16
STATUSES = ("draft", "prompted", "generating", "generated", "approved", "failed")
CAMERA_EN = {"side": "side view", "top_down": "top-down RPG three-quarter view", "three_quarter": "three-quarter RPG view",
             "isometric": "isometric view", "front": "front view"}
PRESET_DESCRIPTIONS = {
    "idle": "breathing in place, relaxed", "walk": "walking forward at a steady pace", "run": "running fast",
    "attack": "one strong weapon attack", "combo_attack": "two-hit combo attack", "cast": "casting a spell with both hands",
    "dodge": "quick evasive roll", "dash": "short burst dash forward", "jump": "jump up and land",
    "hit": "getting hit and recoiling", "death": "collapsing to the ground", "interact": "reaching out to use an object",
}


def _is_zh(lang) -> bool:
    return str(lang or "").lower().startswith("zh")


def generic_poses(n: int, loop: bool, lang: str = "en") -> list[str]:
    """Neutral per-frame beats for a custom action (the description says what happens)."""
    if loop:
        return [(f"循环第 {i + 1}/{n} 拍（最后一帧能接回第一帧）" if _is_zh(lang) else f"cycle beat {i + 1}/{n} (last frame flows back into frame 1)")
                for i in range(n)]
    beats = (["准备", "蓄势", "动作", "顶点/命中", "随势", "恢复"] if _is_zh(lang)
             else ["ready", "anticipation", "action", "peak / impact", "follow-through", "recovery"])
    if n == 1:
        return [beats[3]]
    return [beats[round(i * (len(beats) - 1) / (n - 1))] for i in range(n)]


def new_action(preset: str | None = None, *, name: str | None = None, description: str = "", frames: int | None = None,
               loop: bool | None = None, direction: str = "right", lang: str = "en") -> dict:
    tpl = TEMPLATES.get(preset or "")
    if preset and not tpl:
        raise StudioError(f"Unknown action preset {preset}. Available: {sorted(TEMPLATES)}")
    n = int(frames or (tpl["frames"] if tpl else 6))
    lp = bool(tpl.get("loop", False)) if loop is None and tpl else bool(loop)
    sid = re.sub(r"[^a-z0-9]+", "_", str(name or preset or "").lower()).strip("_")[:40]
    a = {"id": sid or "action", "name": name or (preset or "action").replace("_", " "),
         "preset": preset if tpl else None, "description": description or (PRESET_DESCRIPTIONS.get(preset, "") if tpl else ""),
         "frames": n, "loop": lp, "direction": direction, "poses": [], "prompt": "", "negative": "", "prompt_source": "",
         "asset_id": None, "attempts": [], "status": "draft"}
    a["poses"] = default_poses(a, lang)
    return a


def default_poses(a: dict, lang: str = "en") -> list[str]:
    tpl = TEMPLATES.get(a.get("preset") or "")
    n = int(a["frames"])
    if tpl and len(tpl["poses"]) == n:
        return list(POSES_ZH.get(a["preset"], tpl["poses"])) if _is_zh(lang) else list(tpl["poses"])
    return generic_poses(n, bool(a.get("loop")), lang)


# ------------------------------------------------------------------ persistence
def plan_path(ws, pid, cid):
    return ws.char_dir(pid, cid) / PLAN_FILE


def load_plan(ws, pid: str, cid: str) -> dict:
    ws.get_character(pid, cid)
    p = plan_path(ws, pid, cid)
    if p.is_file():
        return read_json(p)
    return {"character_id": cid, "identity": "", "identity_source": "", "language": "", "actions": [], "updated_at": now()}


def clean_action(a: dict, lang: str = "en") -> dict:
    nm = a.get("name") or (None if a.get("preset") else a.get("id")) or None
    out = new_action(a.get("preset") or None, name=str(nm)[:60] if nm else None,
                     description=str(a.get("description", ""))[:1000], frames=a.get("frames"), loop=a.get("loop"),
                     direction=str(a.get("direction") or "right"), lang=lang)
    if a.get("id"):
        out["id"] = re.sub(r"[^a-z0-9_]+", "_", str(a["id"]).lower()).strip("_")[:40] or out["id"]
    if not 1 <= out["frames"] <= MAX_FRAMES:
        raise StudioError(f"frames must be 1..{MAX_FRAMES}")
    poses = [str(p)[:200] for p in (a.get("poses") or [])]
    out["poses"] = poses if len(poses) == out["frames"] else default_poses(out, lang)
    for k in ("prompt", "negative"):
        out[k] = str(a.get(k) or "")[:6000]
    out["prompt_source"] = a.get("prompt_source") or ("manual" if out["prompt"] else "")
    out["asset_id"] = a.get("asset_id")
    out["attempts"] = list(a.get("attempts") or [])[-20:]
    out["status"] = a.get("status") if a.get("status") in STATUSES else ("prompted" if out["prompt"] else "draft")
    return out


def save_plan(ws, pid: str, cid: str, plan: dict) -> dict:
    c = ws.get_character(pid, cid)
    lang = plan.get("language") or "en"
    actions, seen = [], set()
    for a in plan.get("actions", []):
        a = clean_action(a, lang)
        base, i = a["id"], 2
        while a["id"] in seen:
            a["id"] = f"{base}_{i}"; i += 1
        seen.add(a["id"])
        actions.append(a)
    if len(actions) > 24:
        raise StudioError("At most 24 actions per plan")
    out = {"character_id": c["id"], "identity": str(plan.get("identity", ""))[:4000],
           "identity_source": plan.get("identity_source", ""), "language": lang, "actions": actions, "updated_at": now()}
    write_json(plan_path(ws, pid, cid), out)
    return out


def get_action(plan: dict, action_id: str) -> dict:
    a = next((x for x in plan["actions"] if x["id"] == action_id), None)
    if not a:
        raise StudioError(f"Unknown action {action_id}")
    return a


# ------------------------------------------------------------------ prompts
def identity_text(c: dict, plan: dict, lang: str) -> str:
    if plan.get("identity"):
        return (f"角色：{c['name']}。{plan['identity']}" if _is_zh(lang) else f"Character: {c['name']}. {plan['identity']}")
    return character_block_zh(c) if _is_zh(lang) else character_block(c)


def strip_prompt(c: dict, plan: dict, a: dict, mode: str, lang: str = "en") -> dict:
    """Prompt for ONE horizontal sprite strip containing every frame of the action."""
    n = int(a["frames"])
    poses = a["poses"] if len(a["poses"]) == n else default_poses(a, lang)
    style_extra = c.get("visual_style") or ""
    style_en = "; ".join(x for x in (style_extra, STYLE_TEXT[mode]) if x)
    style_zh = "；".join(x for x in (style_extra, STYLE_TEXT_ZH[mode]) if x)
    if _is_zh(lang):
        order = "；".join(f"{i + 1}：{p}" for i, p in enumerate(poses))
        pos = (f"{identity_text(c, plan, lang)} 动作：{a['name']}——{a['description']}。"
               f"{CAMERA_ZH.get(c.get('camera', 'side'), '')}，{DIRECTION_TEXT_ZH.get(a['direction'], a['direction'])}。"
               f"画风：{style_zh}。"
               f"一张透明背景 PNG 精灵条：单行恰好 {n} 格，等宽等高，从左到右依次为：{order}。"
               f"{'动作循环：最后一帧可以自然接回第一帧。' if a['loop'] else ''}"
               "每格只有一个完整角色，各格人物大小、比例和地面线一致，身体、武器和特效四周留出充足空白；不要格子边框、不要文字。"
               "脸、发型、服装、配色、比例和武器必须与参考图完全一致。")
        neg = BASE_NEGATIVE_ZH
    else:
        order = "; ".join(f"{i + 1}: {p}" for i, p in enumerate(poses))
        pos = (f"{identity_text(c, plan, lang)} Action: {a['name']} — {a['description']}. "
               f"{CAMERA_EN.get(c.get('camera', 'side'), '')}, {DIRECTION_TEXT.get(a['direction'], a['direction'])}. "
               f"Style: {style_en}. "
               f"One transparent PNG sprite strip: exactly {n} equal cells in a single row, left to right: {order}. "
               + ("Looping action: the last frame flows back into the first. " if a["loop"] else "")
               + "Exactly one complete character per cell, same size, proportions and ground line in every cell, generous empty "
               "margin around body, weapon and effects; no cell borders, no text. Identical face, hair, outfit, colours, "
               "proportions and weapon to the reference image.")
        neg = BASE_NEGATIVE
    if c.get("negative_constraints"):
        neg += ("，" if _is_zh(lang) else ", ") + ("，" if _is_zh(lang) else ", ").join(c["negative_constraints"])
    return {"positive": pos, "negative": neg}


def frame_prompt(c: dict, plan: dict, a: dict, index: int, mode: str, lang: str = "en") -> dict:
    """Single-frame prompt (selective regeneration of one bad frame)."""
    pose = a["poses"][min(index, len(a["poses"]) - 1)] if a.get("poses") else ""
    if _is_zh(lang):
        pos = (f"{identity_text(c, plan, lang)} 动作：{a['name']}——{a['description']}，第 {index + 1}/{a['frames']} 帧：{pose}。"
               f"{DIRECTION_TEXT_ZH.get(a['direction'], a['direction'])}。画风：{STYLE_TEXT_ZH[mode]}。"
               "一个完整角色，透明背景，四周留白；与参考图同一角色。")
        return {"positive": pos, "negative": BASE_NEGATIVE_ZH}
    pos = (f"{identity_text(c, plan, lang)} Action: {a['name']} — {a['description']}, frame {index + 1}/{a['frames']}: {pose}. "
           f"{DIRECTION_TEXT.get(a['direction'], a['direction'])}. Style: {STYLE_TEXT[mode]}. "
           "One complete character, transparent background, empty margin on all sides; same character as the reference.")
    return {"positive": pos, "negative": BASE_NEGATIVE}


CODEX_INSTRUCTIONS = """You are the art director for a 2D game. The attached image is the reference for ONE game character.
Write image-generation prompts for sprite animation strips of this exact character.

Return ONLY one JSON object, no prose, in this shape:
{"identity": "<one paragraph: body type and proportions, face, hair, outfit pieces and colours, accessories, weapon/props and how they are held, art style and outline/shading>",
 "actions": [{"id": "<action id>", "poses": ["<frame 1 pose>", "..."], "prompt": "<full prompt>"}]}

Rules:
- Write identity, poses and prompts in {language}.
- One entry per action below, same ids, and EXACTLY the given number of poses (one per frame, in time order).
  Poses must read as a smooth, believable motion that matches the user's description; respect "loop".
- Each prompt asks for ONE transparent PNG sprite strip: exactly N equal cells in a single row, left to right in pose order,
  one complete character per cell, identical scale and ground line in every cell, empty margin around body/weapon/effects,
  no borders, no text. It must restate the identity details so the character stays identical to the reference.
- Art style: {style}. Camera: {camera}. Facing: as given per action.

Actions:
{actions}
"""


def write_prompts(ws, pid: str, cid: str, method: str = "template", *, action_ids: list[str] | None = None,
                  reference=None, mode: str = "pixel", lang: str = "en", codex_bin: str = "", timeout: int = 300,
                  cancel_check=None) -> dict:
    """Fill identity + per-action poses/prompts. method: codex (reads the reference image) | template."""
    c = ws.get_character(pid, cid)
    plan = load_plan(ws, pid, cid)
    plan["language"] = lang
    targets = [a for a in plan["actions"] if not action_ids or a["id"] in action_ids]
    if not targets:
        raise StudioError("No actions in the plan; add at least one action first")
    if method == "codex":
        if reference is None:
            raise StudioError("Codex prompt writing needs a reference image (approve a character master first)")
        listing = "\n".join(
            f"- id={a['id']}; name={a['name']}; frames={a['frames']}; loop={str(a['loop']).lower()}; "
            f"facing={DIRECTION_TEXT.get(a['direction'], a['direction'])}; user description: {a['description'] or '(none)'}; "
            f"suggested beats: {' | '.join(default_poses(a, lang))}" for a in targets)
        instr = (CODEX_INSTRUCTIONS.replace("{language}", "Simplified Chinese" if _is_zh(lang) else "English")
                 .replace("{style}", (c.get("visual_style") or "") + " " + STYLE_TEXT[mode])
                 .replace("{camera}", CAMERA_EN.get(c.get("camera", "side"), "side view")).replace("{actions}", listing))
        try:
            data = extract_json(exec_text(instr, [reference], codex_bin=codex_bin, timeout=timeout, cancel_check=cancel_check))
        except CodexError as e:
            raise StudioError(f"Codex prompt writing failed: {e}", code="codex_failed") from e
        if isinstance(data.get("identity"), str) and data["identity"].strip():
            plan["identity"], plan["identity_source"] = data["identity"].strip()[:4000], "codex"
        by_id = {str(x.get("id")): x for x in data.get("actions", []) if isinstance(x, dict)}
        for a in targets:
            got = by_id.get(a["id"], {})
            poses = [str(p) for p in got.get("poses", []) if str(p).strip()]
            if len(poses) == a["frames"]:
                a["poses"] = poses
            fallback = strip_prompt(c, plan, a, mode, lang)
            a["prompt"] = str(got.get("prompt") or "").strip() or fallback["positive"]
            a["negative"] = fallback["negative"]
            a["prompt_source"] = "codex" if got.get("prompt") else "template"
            a["status"] = "prompted" if a["status"] in ("draft", "prompted", "failed") else a["status"]
    elif method == "template":
        for a in targets:
            if len(a["poses"]) != a["frames"]:
                a["poses"] = default_poses(a, lang)
            pr = strip_prompt(c, plan, a, mode, lang)
            a["prompt"], a["negative"], a["prompt_source"] = pr["positive"], pr["negative"], "template"
            a["status"] = "prompted" if a["status"] in ("draft", "prompted", "failed") else a["status"]
    else:
        raise StudioError("method must be codex or template")
    return save_plan(ws, pid, cid, plan)


def presets() -> dict:
    return {k: {"frames": v["frames"], "loop": v.get("loop", False), "poses": v["poses"], "poses_zh": POSES_ZH.get(k, v["poses"]),
                "description": PRESET_DESCRIPTIONS.get(k, "")} for k, v in copy.deepcopy(TEMPLATES).items()}
