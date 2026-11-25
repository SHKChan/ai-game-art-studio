# AI 游戏美术工作室

[English](README.md)

本地优先的 2D 游戏美术制作工具，支持像素风和高清插画。纯 Python 应用（Pillow + numpy），界面支持中英文，
不需要云服务、数据库或付费 API。

| 引擎 | 作用 |
|---|---|
| **A — 像素引擎** | 分层、可回放的程序化像素画：道具、图标、特效、图块。自研引擎，调用格式兼容 Atelier。 |
| **B — AI 生成** | 通过 **ComfyUI** 以参考图驱动生成角色关键帧（可导入任意模型和工作流）。Codex 为可选项。 |
| **C — 外部素材** | 导入 PNG / 序列帧 / 精灵表 / GIF / APNG / MP4 / WebM；抠背景、切图、对齐。 |

## 安装与启动

需要 **Python 3.10+**。可选：**ffmpeg**（视频导入）、**ComfyUI**（AI 生成）。

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File .\start.ps1      # 自动创建 .venv、安装依赖并打开 http://127.0.0.1:8870
```
```bash
# Linux / macOS
./start.sh
```

- **界面语言**：顶栏切换 English / 简体中文（记住选择；首次按浏览器语言）。
- **命令行/接口提示语言**：`--lang zh-CN` 或环境变量 `ARTSTUDIO_LANG=zh-CN`。
- **提示词语言**：资源库中按项目设置（默认英文，多数 ComfyUI 模型对英文更稳定）。
- **中文/GBK 系统**：所有读写均为 UTF-8，GBK/cp936/cp1252 系统下不会再出现编码错误。
- 配置：`studio.config.example.json`、`.env.example`；Windows 与 ComfyUI 部署：[docs/deployment-windows.zh-CN.md](docs/deployment-windows.zh-CN.md)。

## 工作区

| 工作区 | 功能 |
|---|---|
| 资源库 | 项目、角色、素材、筛选、提示词语言、骑士示例 |
| 角色工作室 | 角色设定、横版/4/8 方向、候选 → 通过后**锁定**母版、需填写原因才能替换/解锁、可选镜像、历史 |
| 动画工作室 | 播放、帧率、逐帧时长、循环、洋葱皮、地面线、锚点编辑、帧对比、排序/复制/删除、替换、单帧重新生成、事件、特效图层、检查、审核、版本 |
| 程序化绘制 | 运行生成器、回放 `.recipe`、查看文档（调色板、图层、图格、调用） |
| 导入与处理 | 拖放导入、切图、去背景、还原像素、整组对齐、处理前后对比 |
| AI 生成 | 服务状态、ComfyUI 工作流导入与检查、关键帧生成、提示词预览、带预算的批量生成 |
| 导出 | PNG 帧、精灵表、打包图集、GIF/APNG、JSON、Cocos Creator plist、Phaser/PixiJS JSON、Godot 辅助脚本、ZIP |

## 命令行（JSON 输出，便于 Agent 调用）

```bash
python -m artstudio --lang zh-CN project create "我的 RPG" --id my-rpg
python -m artstudio procedural ice_spear --project my-rpg --params '{"element":"lightning"}'
python -m artstudio draw my_gem.jsonl --project my-rpg --name "红宝石" --type icon
python -m artstudio generate --project my-rpg --provider comfyui --workflow sd-image-to-image --character hero --template walk --direction east --prompt-language zh-CN --params '{"checkpoint":"<文件>.safetensors"}'
python -m artstudio export --project my-rpg --assets <素材ID…> --formats atlas cocos gif json zip
```

新增程序化素材的方法：[docs/engine-a-guide.md](docs/engine-a-guide.md)（英文，供 Agent 使用）。

## 验证状态

- ✅ 离线验收（阶段 A）：63 项自动化测试、Playwright 中英文界面测试、概念验证素材 —— 见 [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md)。
- 🧪 AI 生成目前**只经过模拟服务测试**。⛔ **阶段 B（真实 ComfyUI 推理）尚未运行。**

许可：MIT。派生代码与示例数据保留原版权声明，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
