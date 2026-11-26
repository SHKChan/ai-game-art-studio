"""Prompt templates for Motion Studio (reference-driven character generation).

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


# ------------------------------------------------------------------ Chinese prompt variants (prompt_language="zh-CN")
# English stays the default: most ComfyUI checkpoints follow English prompts more reliably.
DIRECTION_TEXT_ZH = {
    "right": "朝右（侧视）", "left": "朝左（侧视，单独绘制，不是镜像）", "south": "面向镜头（正面/南）", "north": "背对镜头（背面/北）",
    "east": "朝画面右侧（东，侧面）", "west": "朝画面左侧（西，侧面，单独绘制）", "south_east": "四分之三正面朝右下（东南）",
    "south_west": "四分之三正面朝左下（西南）", "north_east": "四分之三背面朝右上（东北）", "north_west": "四分之三背面朝左上（西北）", "none": "",
}
STYLE_TEXT_ZH = {
    "pixel": "清晰硬边像素画，1 像素描边，有限调色板，无抗锯齿、无模糊",
    "hd": "高分辨率手绘 2D 游戏角色，轮廓清晰，柔和明暗，保留抗锯齿边缘",
}
CAMERA_ZH = {"side": "侧视", "top_down": "俯视 RPG 四分之三视角", "three_quarter": "四分之三 RPG 视角", "isometric": "等距视角", "front": "正视"}
POSES_ZH = {
    "idle": ["自然站姿", "吸气，胸口上抬 1 像素", "最高点", "回到自然站姿", "呼气，略微下沉", "最低点"],
    "walk": ["接触（右脚在前）", "下沉", "交叉", "上升", "接触（左脚在前）", "下沉", "交叉", "上升"],
    "run": ["着地", "蹬地", "腾空", "前伸", "着地（另一条腿）", "蹬地", "腾空", "前伸"],
    "attack": ["准备", "蓄势", "蓄势顶点", "挥击", "命中", "随挥", "回收", "回到准备姿势"],
    "combo_attack": ["准备", "第一段蓄势", "第一段挥击", "第一段命中", "第一段随挥", "重新架势", "第二段蓄势", "第二段挥击", "第二段命中", "第二段随挥", "回收", "准备"],
    "cast": ["准备", "举起法器", "聚集能量", "蓄能顶点", "释放", "随势", "平复", "准备"],
    "dodge": ["下蹲", "倾身", "翻滚/扑出", "翻滚", "落地", "恢复"],
    "dash": ["下蹲", "蹬出", "爆发", "滑行", "刹停", "恢复"],
    "jump": ["屈膝预备", "起跳", "上升", "最高点", "下落", "落地前", "落地缓冲", "恢复"],
    "hit": ["受击后仰", "踉跄", "缓冲", "恢复"],
    "death": ["受击", "失去平衡", "膝盖弯曲", "倒下", "着地", "弹起", "静止", "躺倒"],
    "interact": ["准备", "伸手", "抓取", "使用", "松开", "准备"],
}
BASE_NEGATIVE_ZH = "背景，场景，地面，地面阴影，文字，水印，网格线，边框，身体被裁切，武器被裁切，多余肢体，多余手指，重复角色，服装改变，发型改变，武器改变，模糊，压缩噪点"


def character_block_zh(c: dict) -> str:
    parts = [f"角色：{c['name']}。{c.get('description', '')}".strip()]
    if c.get("proportions"):
        parts.append("比例：" + "，".join(f"{k} {v}" for k, v in c["proportions"].items()))
    if c.get("clothing"):
        parts.append("服装：" + "、".join(c["clothing"]))
    if c.get("accessories"):
        parts.append("配饰：" + "、".join(c["accessories"]))
    if c.get("weapon"):
        parts.append("武器（保持形状与握法不变）：" + "，".join(f"{k}：{v}" for k, v in c["weapon"].items()))
    if c.get("palette"):
        parts.append("只使用以下调色板：" + " ".join(c["palette"][:32]))
    if c.get("constraints"):
        parts.append("必须保持：" + "；".join(c["constraints"]))
    return " ".join(parts)


def keyframe_prompt_zh(c: dict, template: str, direction: str, mode: str | None = None, frame_index: int | None = None, note: str = "") -> dict:
    mode = mode or c.get("art_style", "pixel")
    poses = POSES_ZH.get(template) or TEMPLATES[template]["poses"]
    style = (c.get("visual_style") or "") + "；" + STYLE_TEXT_ZH[mode]
    if frame_index is None:
        order = "；".join(f"{i + 1}：{p}" for i, p in enumerate(poses))
        layout = (f"一张透明背景 PNG 精灵图表，单行 {len(poses)} 格，等宽等高，严格从左到右：{order}。"
                  "每格只有一个完整角色，各格人物比例和地面线一致，身体、武器和特效四周留出充足空白。")
    else:
        layout = f"单个姿势：{poses[min(frame_index, len(poses) - 1)]}。一个完整角色，透明背景，四周留白。"
    pos = (f"{character_block_zh(c)} 动作：{template}。{CAMERA_ZH.get(c.get('camera', 'side'), '')}，{DIRECTION_TEXT_ZH.get(direction, direction)}。"
           f"画风：{style}。{layout}脸、发型、服装、比例和武器必须与参考图完全一致。" + (f"本轮修改：{note}" if note else ""))
    neg = BASE_NEGATIVE_ZH + ("，" + "，".join(c["negative_constraints"]) if c.get("negative_constraints") else "")
    return {"positive": pos, "negative": neg, "template": template, "direction": direction, "mode": mode, "language": "zh-CN"}


def master_prompt_zh(c: dict, direction: str = "south") -> dict:
    mode = c.get("art_style", "pixel")
    pos = (f"{character_block_zh(c)} 角色母版参考图，自然站立，全身，{DIRECTION_TEXT_ZH.get(direction, direction)}。"
           f"画风：{c.get('visual_style') or ''}；{STYLE_TEXT_ZH[mode]}。透明背景，居中，全身完整可见并留白。")
    return {"positive": pos, "negative": BASE_NEGATIVE_ZH, "direction": direction, "mode": mode, "language": "zh-CN"}


def build_keyframe_prompt(c, template, direction, mode=None, frame_index=None, note="", language="en") -> dict:
    if str(language).lower().startswith("zh"):
        return keyframe_prompt_zh(c, template, direction, mode, frame_index, note)
    return keyframe_prompt(c, template, direction, mode, frame_index, note)


def build_master_prompt(c, direction="south", language="en") -> dict:
    return master_prompt_zh(c, direction) if str(language).lower().startswith("zh") else master_prompt(c, direction)
