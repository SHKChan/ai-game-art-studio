"""Server/CLI message localisation (en, zh-CN).

Errors carry a stable `code` (StudioError.code / GenerationError.code). Messages without an explicit code
are matched against known English templates below, so existing raise sites are translated too.
Unknown messages fall back to English. Original English detail is appended for support/debugging.
"""
from __future__ import annotations

import re

SUPPORTED = ("en", "zh-CN")

CODES = {
    "provider_unavailable": "生成服务不可用", "missing_models": "服务器上缺少所需模型", "missing_nodes": "服务器上缺少所需节点",
    "invalid_values": "工作流参数值无效", "invalid_workflow": "ComfyUI 拒绝了该工作流", "execution_error": "生成执行失败",
    "timeout": "生成超时", "unreachable": "无法连接 ComfyUI", "budget_exceeded": "已超出生成预算", "no_outputs": "没有可取回的输出",
    "bad_request": "请求无效", "engine_error": "像素引擎错误", "environment": "运行环境不符合要求", "sample_missing": "缺少示例素材",
    "not_procedural": "不是程序化素材", "charkit_base_missing": "缺少 Craftpix 基础角色素材包（需本地解压到 assets_local/craftpix-base，不随仓库分发）", "document_missing": "找不到引擎文档（可回放配方重建）", "conflict": "数据已被其他操作修改，请刷新后重试",
}

# (regex on the English message, Chinese template using regex groups)
PATTERNS = [
    (r"^Unknown project (.+)$", "项目不存在：{0}"), (r"^Unknown asset (.+)$", "素材不存在：{0}"),
    (r"^Unknown character (.+)$", "角色不存在：{0}"), (r"^Unknown job$", "任务不存在"), (r"^Unknown version$", "版本不存在"),
    (r"^Unknown builder (.+?)\.", "未知的生成器：{0}"), (r"^Unknown workflow (.+)$", "未知的工作流：{0}"),
    (r"^Unknown provider (.+)$", "未知的生成服务：{0}"), (r"^Unknown frame op (.+)$", "未知的帧操作：{0}"),
    (r"^Project name must be 1-120 characters$", "项目名称须为 1 至 120 个字符"), (r"^Project already exists$", "项目已存在"),
    (r"^Frame index out of range$", "帧序号超出范围"), (r"^An animation needs at least one frame$", "动画至少需要一帧"),
    (r"^duration_ms must be 1..60000$", "帧时长须在 1 至 60000 毫秒之间"), (r"^pivot must lie inside the canvas$", "锚点必须位于画布内"),
    (r"^Master '(.+)' is locked.*$", "“{0}”方向的母版已锁定，请使用“替换母版”并填写原因"),
    (r"^Replacing a locked master requires a reason$", "替换已锁定的母版需要填写原因"), (r"^Unlocking requires a reason$", "解锁需要填写原因"),
    (r"^Direction (.+) not in (.+)$", "方向 {0} 不在 {1} 中"), (r"^No frames$", "没有帧"), (r"^Empty frames: (.+)$", "存在空白帧：{0}"),
    (r"^File not found: (.+)$", "文件不存在：{0}"), (r"^Unsupported file type (.+)$", "不支持的文件类型：{0}"),
    (r"^Upload too large$", "上传文件过大"), (r"^Empty upload$", "上传内容为空"), (r"^Unreadable image: (.+)$", "无法读取图片：{0}"),
    (r"^ffmpeg is not installed.*$", "未安装或未配置 ffmpeg，无法导入视频"), (r"^ffmpeg failed: (.+)$", "ffmpeg 处理失败：{0}"),
    (r"^Background is not a solid colour or checkerboard.*$", "背景不是纯色或棋盘格；请指定颜色或使用外部抠图工具"),
    (r"^Sheet has no visible pixels.*$", "精灵表没有可见像素（背景是否透明？）"), (r"^No sprites found$", "未找到精灵"),
    (r"^Batch jobs require an explicit generation budget.*$", "批量任务必须设定生成预算（budget=N）"),
    (r"^Generation budget exhausted \((\d+)/(\d+)\).*$", "生成预算已用完（{0}/{1}）"),
    (r"^Only failed or cancelled jobs can be retried$", "只能重试失败或已取消的任务"),
    (r"^Not an API-format workflow.*$", "不是 API 格式的工作流。请在 ComfyUI 中使用“导出（API）”"),
    (r"^No output node found.*$", "工作流中没有输出节点（SaveImage/PreviewImage 等）"),
    (r"^Workflow input '(.+)' requires an image$", "工作流输入“{0}”需要图片"), (r"^Missing required workflow input '(.+)'$", "缺少必填的工作流输入“{0}”"),
    (r"^Provider '(.+)' unavailable: (.+)$", "生成服务“{0}”不可用：{1}"), (r"^ComfyUI unreachable at (\S+?): .*$", "无法连接 {0} 上的 ComfyUI"),
    (r"^Timed out after (\d+)s$", "{0} 秒后超时"), (r"^Select one or more animation assets$", "请选择一个或多个动画素材"),
    (r"^Atlas would be (\d+)x(\d+); exceeds max (\d+).*$", "图集尺寸 {0}x{1} 超过上限 {2}，请拆分导出或减少帧数"),
    (r"^unknown tool '(.+)'.*$", "未知的引擎工具：{0}"), (r"^row (\d+) col (\d+): character '(.+)' is not in the legend$", "第 {0} 行第 {1} 列：字符“{2}”不在图例中"),
    (r"^Open the studio at / first.*$", "请先从首页打开工作室（缺少会话 Cookie）"), (r"^missing field (.+)$", "缺少字段：{0}"),
]
_COMPILED = [(re.compile(p), z) for p, z in PATTERNS]


def normalize(lang: str | None) -> str:
    if not lang:
        return "en"
    lang = lang.split(",")[0].strip()
    return "zh-CN" if lang.lower().startswith("zh") else "en"


def localize(message: str, code: str | None = None, lang: str = "en") -> str:
    if normalize(lang) == "en":
        return message
    for rx, zh in _COMPILED:
        m = rx.match(message)
        if m:
            return zh.format(*m.groups())
    if code and code in CODES:
        return f"{CODES[code]}（{message}）"
    return message


def localize_exc(exc: Exception, lang: str = "en") -> str:
    return localize(str(exc), getattr(exc, "code", None), lang)
