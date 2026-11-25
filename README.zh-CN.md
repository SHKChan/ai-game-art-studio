# AI 游戏美术工作室

[English](README.md) · 版本 **0.2.0**（[更新日志](CHANGELOG.md)）· MIT 许可

**本地优先的 2D 游戏美术制作工具**：支持像素风和高清插画，从单个图标到角色动画精灵，都能直接导出到游戏引擎。
纯 Python 应用（Pillow + numpy），网页界面支持中英文，不需要云服务、数据库或付费 API。

![宝箱打开](deliverables/poc/contact_sheets/A_chest_open.png)

## 能做什么

| 引擎 | 适合制作 | 方式 |
|---|---|---|
| **A — 像素引擎** | 道具、图标、技能特效、图块、场景物件、建筑、小型动画精灵 | 分层、确定性、可回放的绘制。使用内置生成器或 Agent 编写的调用列表，可离线运行。 |
| **B — AI 生成** | 精细角色：角色母版、多方向视图、动作关键帧 | 通过 **ComfyUI**（你自己的模型和工作流）以参考图驱动生成。Codex 为可选项。 |
| **C — 外部素材** | 已有的美术资源 | 导入 PNG / 序列帧 / 精灵表 / GIF / APNG / MP4 / WebM，然后清理和对齐。 |

三个引擎产出**同一种素材格式**，以下功能对所有素材通用：

- **角色**：角色设定、横版 / 4 / 8 方向、候选 → 通过后**锁定**母版、历史记录。
- **动画编辑**：播放、帧率、逐帧时长、洋葱皮、锚点、排序 / 复制 / 替换帧、单帧重新生成、事件、特效图层、版本快照。
- **处理**：去背景、切图、还原像素、整组对齐（整组统一缩放、地面锚点、保留腾空帧、扩展画布而不裁掉武器）。
- **检查**：确定性检查（尺寸、裁切、背景、抖动）与视觉审核分开记录。
- **导出**：PNG 帧、精灵表、打包图集、GIF / APNG、JSON、**Cocos Creator** plist、Phaser / PixiJS JSON、Godot 辅助脚本、ZIP。

### 内置像素生成器（引擎 A）

| 生成器 | 产出 | 参数 |
|---|---|---|
| `potion` | 奇幻药水瓶（道具） | `size`、`frames`、`liquid` 红/蓝/绿/紫 |
| `chest` / `chest_open` | 宝箱；8 帧开箱动画 | `size` |
| `fireball` | 循环火球特效 | `size`、`frames` |
| `sword_slash` | 8 帧剑气特效 | `size`、`color` azure/gold/crimson |
| `ice_spear` | 圆形技能图标 | `size`、`element` ice/lightning/poison |
| `hero_shrine` | 96×96 英雄神殿，火盆带动画 | `frames`、`banner` red/blue/green |

新素材不一定要写代码：Agent 可以写一个调用列表，用 `artstudio draw` 运行。见
[docs/engine-a-guide.md](docs/engine-a-guide.md)（英文，供 Agent 使用）。

## 快速开始

需要 **Python 3.10+**。可选：**ffmpeg**（视频导入）、**ComfyUI**（AI 生成）。

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File .\start.ps1      # 自动创建 .venv、安装依赖并打开 http://127.0.0.1:8870
```
```bash
# Linux / macOS
./start.sh
```

## 使用方法

### 网页工作室（http://127.0.0.1:8870）

1. **资源库**：新建项目，选择提示词语言（默认英文，也可选中文）。
2. 用任一引擎制作：
   - **程序化绘制**：选生成器、设参数、运行；或回放 `.recipe`。
   - **AI 生成**：连接 ComfyUI，导入或检查工作流，创建角色母版，然后生成关键帧。
   - **导入与处理**：拖入文件，切图、去背景、整组对齐。
3. **动画工作室**：检查帧、调整时长和锚点、运行检查、审核通过。
4. **导出**：选择格式（如 Cocos 图集 + GIF），下载 ZIP。

- **界面语言**：顶栏切换 English / 简体中文（记住选择；首次按浏览器语言）。
- **中文/GBK 系统**：所有读写均为 UTF-8，GBK/cp936/cp1252 系统下不会出现编码错误。

### 命令行（JSON 输出，便于脚本和 Agent 调用）

```bash
python -m artstudio --lang zh-CN project create "我的 RPG" --id my-rpg
python -m artstudio builders                                       # 列出生成器和动画模板
python -m artstudio procedural hero_shrine --project my-rpg --params '{"banner":"blue"}'
python -m artstudio draw my_gem.jsonl --project my-rpg --name "红宝石" --type icon
python -m artstudio generate --project my-rpg --provider comfyui --workflow sd-image-to-image --character hero --template walk --direction east --prompt-language zh-CN --params '{"checkpoint":"<文件>.safetensors"}'
python -m artstudio export --project my-rpg --assets <素材ID…> --formats atlas cocos gif json zip
```

- 命令行提示语言：`--lang zh-CN` 或环境变量 `ARTSTUDIO_LANG=zh-CN`。
- 配置：`studio.config.example.json`、`.env.example`。
- Windows 与 ComfyUI 部署：[docs/deployment-windows.zh-CN.md](docs/deployment-windows.zh-CN.md)。

### 内置 ComfyUI 工作流模板

`workflows/comfyui/`：文生图、图生图、角色参考、姿势关键帧、局部重绘、SVD 图生视频、去背景（rembg）。
在真实 ComfyUI 上测试前（阶段 B）均为**未验证**。也可以在界面或命令行导入自己的工作流。

## 基于哪些项目

本仓库是独立的，不包含其他项目的 git 仓库。它基于两个 MIT 项目：

| 上游项目 | 采用的内容 | 现在的位置 |
|---|---|---|
| **[Atelier](https://github.com/marmikshah/atelier)**（Marmik Shah），提交 `8ac6adf` | 工具调用格式、文档 / recipe 结构、绘制规则 | `artstudio/engine`：自研 Python 实现（不需要 Rust），Atelier 的 recipe 回放结果**逐像素一致**。 |
| **[Pixel Atelier](https://github.com/jinxingtaire/pixel-atelier)**（Pixel Character Pipeline contributors），提交 `15d199f` | 精灵处理流程、中文精灵表提示词、Codex 客户端、骑士示例 | `artstudio/pipeline/spritepipe.py`、`artstudio/prompts_zh_sheet.py`、`artstudio/providers/codex_rpc.py`、`samples/knight/`，已改写为 UTF-8，兼容 GBK/cp936 系统。 |

AI 生成通过 **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** 的服务器接口完成，不包含 ComfyUI 代码。
许可与派生文件清单：[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 验证状态

- ✅ **离线验收（阶段 A）**：65 项自动化测试、Playwright 中英文界面测试、概念验证素材，见 [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md)。
- 🧪 **AI 生成目前只经过模拟服务测试**。模拟输出标记为 TEST FIXTURE，不是 AI 作品。
- ⛔ **阶段 B（真实 ComfyUI 推理）尚未运行**。请在 ComfyUI 电脑上运行 `scripts/production_smoke_test.py`。

## 参与开发

- 规则与注意事项：[AGENTS.md](AGENTS.md)；需求：[SPECIFICATION.md](SPECIFICATION.md)。
- 运行测试：`python scripts/run_tests.py`。
- 版本历史：[CHANGELOG.md](CHANGELOG.md)；当前版本：[VERSION](VERSION)。
