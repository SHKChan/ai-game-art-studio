"""Chinese whole-character sheet prompt (8 actions, 4x2 grid) and action briefs.

Derived from Pixel Atelier `bridge/production.py` (MIT © 2026 Pixel Character Pipeline contributors):
STEPS and generation_prompt are kept verbatim so prompts proven on the knight case stay identical.
"""
from __future__ import annotations

STEPS = {
    'idle': ('待机', '保持站姿和呼吸，头发衣物轻微起伏，脚底稳定，首尾接成循环。', [150,110,100,120,150,110,100,120], True),
    'run': ('奔跑', '交替蹬地、腾空和落脚，髋膝踝连续，身体前倾。角色原地跑，首尾循环。', [80]*8, True),
    'dash': ('闪身', '压低身位，后脚蹬地，前倾爆发，随后刹停并回稳；位移留给游戏。', [100,80,60,40,50,70,100,130], False),
    'light': ('连段', '根据参考装备设计两段连续攻击。近战先斜劈至低位，随即蹬腿转髋从低处上挑，再回收；远程或法术设计两段相连的释放。每段沿动作轨迹短暂显示特效。', [120,90,50,70,60,50,100,140], False),
    'heavy': ('蓄力', '稳住支撑脚、压低重心，拉开蓄力与快速释放的速度差。沿用角色原有装备，释放后有明显缓冲与收势。', [130,150,200,180,50,80,110,150], False),
    'jump': ('跳跃', '屈膝预备、蹬地、空中收腿、伸腿下落、接地缓冲、恢复。世界跳跃轨迹交给游戏。', [110,90,70,90,100,90,80,130], False),
    'hurt': ('受击', '短促冲击使肩胸后仰，屈膝缓冲，装备随手滞后，再收回重心。', [60,50,60,70,80,90,110,130], False),
    'knockdown': ('倒地', '依次失衡、侧倒、着地缓冲，保持最后的倒地姿势。', [80,60,60,70,90,110,160,260], False),
}


def generation_prompt(project: dict, action: str, note: str = "") -> str:
    label, motion, _, _ = STEPS[action]
    spec = project['spec']
    default_style = (
        '2.5至3头身Q版硬边像素风格（Chibi Pixel Art），1px清晰深色像素外轮廓，'
        '简化面部（斗笠或刘海遮眼、只露简洁下颌，不画写实五官），大块复古像素色阶（32-64色），'
        '若参考图为写实原画，必须转化为Q版像素小人比例，严禁照搬写实八头身比例与平滑插画笔触'
    )
    return (
        f"为像素角色「{project['name']}」设计并绘制一段{label}动作。"
        f"人物设定：{spec.get('identity') or project['name']}。"
        f"装备：{spec.get('weapon') or '根据参考图识别并沿用原装备，无装备就保留徒手'}。"
        f"画风：{spec.get('style') or default_style}。"
        f"制作要求：{motion}\n"
        "先根据角色比例、原装备和重心设计八个连贯关键姿势，再一次生成一张透明 PNG 图表。"
        "固定 4 列 × 2 行，等宽等高，严格从左到右、从上到下。每格只有一名完整角色，统一视角、人物比例和根节点。"
        "保持同一张脸、发型、服装、握持方式和装备结构。没有换装，不新增道具。"
        "各格四周留空，容纳人物、武器和特效。输出真实透明背景，无地面、文字、格线或背景填充。"
        + (f"\n本轮修改：{note}" if note else '')
    )


