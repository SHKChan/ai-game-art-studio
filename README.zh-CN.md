# AI 游戏美术工作室

[English](README.md) · 版本 **0.4.0**（[更新日志](CHANGELOG.md)）· MIT 许可

**本地优先的 2D 游戏美术制作工具**：支持像素风和高清插画，从单个图标到角色动画精灵，都能直接导出到游戏引擎。
纯 Python 应用（Pillow + numpy），网页界面支持中英文，不需要云服务、数据库或付费 API。

![宝箱打开](deliverables/poc/contact_sheets/A_chest_open.png)

## 能做什么

工作室有三个工具，产出**同一种素材格式**，编辑、检查和导出对所有素材通用。

| 工具 | 适合制作 | 方式 |
|---|---|---|
| **🔥 像素工坊（Pixel Forge）** | 技能特效、道具、图标、物件、场景 | 内置像素生成器 + **实时编辑器**：样式、尺寸、速度、颜色、描边、光晕、翻转、放大。分层、可回放，离线可用，不需要 AI。 |
| **🎬 动作工作室（Motion Studio）** | 角色的动作帧：待机、行走、攻击、自定义动作 | 一张参考图 → 动作 → 提示词 → 每个动作一条精灵条，由 **Codex CLI** 或本地 **ComfyUI** 绘制。 |
| **📥 素材导入（Asset Import）** | 已有的美术资源 | PNG / 序列帧 / 精灵表 / GIF / APNG / MP4 / WebM：去背景、切图、对齐。 |

通用功能：

- **角色**：角色设定、横版 / 4 / 8 方向、候选 → 通过后**锁定**母版、历史记录。
- **动画编辑**：播放、帧率、逐帧时长、洋葱皮、锚点、排序 / 复制 / 替换帧、单帧重新生成、事件、特效图层、版本快照。
- **处理**：去背景、切图、还原像素、整组对齐（整组统一缩放、地面锚点、保留腾空帧、扩展画布而不裁掉武器）。
- **检查**：确定性检查（尺寸、裁切、背景、抖动）与视觉审核分开记录。
- **导出**：PNG 帧、精灵表、打包图集、GIF / APNG、JSON、**Cocos Creator** plist、Phaser / PixiJS JSON、Godot 辅助脚本、ZIP。
- **外观**：English / 中文，以及 跟随系统 / 深色 / 浅色 主题（顶栏）。

### 像素工坊内置生成器

| 生成器 | 产出 | 选项（编辑器另有速度 / 颜色 / 描边 / 光晕 / 翻转 / 放大） |
|---|---|---|
| `heal` | 治疗：地面光圈、光柱、上升的十字光点（循环） | `color` green/blue/gold、`frames` |
| `buff_aura` | 增益光环：脚下旋转光环、上升光束和箭头（循环） | `color` gold/red/purple、`frames` |
| `lightning_strike` | 落雷：闪电劈下、命中闪光、冲击环、火花 | `color` blue/purple/yellow、`thickness` 1–3 |
| `shield_barrier` | 护盾：六边形护罩形成、流光、消散（半透明） | `color` azure/gold/green |
| `frost_nova` | 冰霜新星：中心闪光、向外扩散的冰刺环、雪花 | `color` ice/arcane/toxic |
| `poison_cloud` | 毒云：翻滚的毒雾、冒泡和滴落（循环） | `color` green/purple/orange、`frames` |
| `fireball` | 循环火球 | `size`、`frames` |
| `sword_slash` | 8 帧剑气 | `color` azure/gold/crimson、`thickness` 0.5–1.6 |
| `ice_spear` | 圆形技能图标 | `size`、`element` ice/lightning/poison |
| `potion` | 奇幻药水瓶（道具） | `size`、`frames`、`liquid` 红/蓝/绿/紫 |
| `chest` / `chest_open` | 宝箱；8 帧开箱动画 | `size` |
| `hero_shrine` | 96×96 英雄神殿，火盆带动画 | `frames`、`banner` red/blue/green |

新素材不一定要写代码：Agent 可以写一个调用列表，用 `artstudio draw` 运行。见
[docs/pixel-forge-guide.md](docs/pixel-forge-guide.md)（英文，供 Agent 使用）。

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

首页有三个入口，对应三个工具。

**🎬 动作工作室** —— 五步制作角色动画：

1. **角色**：名称、美术风格、侧视或俯视，以及 **一张参考图**（会锁定为母版）。
2. **动作**：点击预设（待机、行走、奔跑、攻击、施法、跳跃、受击、死亡……），或添加 **自定义动作** 并用一句话描述，
   例如「把剑举过头顶再重重劈下」。设置帧数、是否循环和朝向。
3. **提示词**：**✨ 用 Codex 编写** 会查看参考图，写出角色描述、逐帧姿势和每个动作的提示词；也可以使用内置模板。所有内容都可以修改。
4. **生成**：选择 **Codex CLI** 或 **本地 ComfyUI**（工作流、模型文件、重绘强度）。每个动作生成一条精灵条，再切成帧并对齐（统一缩放和地面线）。
5. **检查与导出**：预览每个动画，点击某一帧可只重做这一帧，审核通过后导出到 Cocos Creator、Godot、Phaser/PixiJS 或 PNG/GIF。

**🔥 像素工坊** —— 左侧选择生成器，中间实时预览，右侧调整：

| 区域 | 可调内容 |
|---|---|
| 样式 | 生成器自带选项（配色、尺寸、帧数、粗细……） |
| 节奏 | 速度 0.25×–3×、循环 |
| 颜色 | 单独修改调色板中的任意颜色，或整体调整色相 / 饱和度 / 亮度 |
| 描边与光晕 | 描边 0–3 像素及颜色、抖动光晕 0–4 像素及颜色、水平翻转、输出放大 1×–4× |
| 保存 | 保存到资源库，或保存并导出（PNG 帧、精灵表、GIF、JSON、Cocos、ZIP） |

所有修改都会随素材保存，并记录为像素引擎调用，因此保存的素材可以精确回放，也能在工坊中重新打开（「本项目已保存」）。

**📥 素材导入** —— 拖入文件，选择切图 / 去背景 / 对齐方式后导入。

专业工具在 **更多工具** 中：逐帧 **动画编辑器**、**角色详情**、**生成与工作流**（ComfyUI）和 **像素文档**（配方、图层、图格）。

- **界面语言**：顶栏切换 English / 简体中文（记住选择；首次按浏览器语言）。
- **中文/GBK 系统**：所有读写均为 UTF-8，GBK/cp936/cp1252 系统下不会出现编码错误。

### 命令行（JSON 输出，便于脚本和 Agent 调用）

```bash
python -m artstudio --lang zh-CN project create "我的 RPG" --id my-rpg
python -m artstudio builders                                       # 列出生成器和动画模板
python -m artstudio procedural hero_shrine --project my-rpg --params '{"banner":"blue"}'
python -m artstudio procedural heal --project my-rpg --params '{"color":"gold"}' --edits '{"speed":1.5,"outline":1,"glow":2}'
# 动作工作室（角色动画）
python -m artstudio animate new --project my-rpg --name "火焰骑士" --image knight.png --view side
python -m artstudio animate add --project my-rpg --character <角色ID> --preset attack
python -m artstudio animate add --project my-rpg --character <角色ID> --name "旋风斩" --description "伸剑原地转一圈" --frames 6
python -m artstudio animate prompts --project my-rpg --character <角色ID> --method codex --language zh-CN
python -m artstudio animate generate --project my-rpg --character <角色ID> --provider codex
python -m artstudio draw my_gem.jsonl --project my-rpg --name "红宝石" --type icon
python -m artstudio generate --project my-rpg --provider comfyui --workflow sd-image-to-image --character hero --template walk --direction east --prompt-language zh-CN --params '{"checkpoint":"<文件>.safetensors"}'
python -m artstudio export --project my-rpg --assets <素材ID…> --formats atlas cocos gif json zip
```

- 命令行提示语言：`--lang zh-CN` 或环境变量 `ARTSTUDIO_LANG=zh-CN`。
- 配置：`studio.config.example.json`、`.env.example`。Codex CLI：安装并运行 `codex login`，工作室会在 PATH 中找到它（或设置 `codex_bin`）。
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

- ✅ **离线验收（阶段 A）**：84 项自动化测试、覆盖完整引导流程的 Playwright 中英文界面测试、概念验证素材，见 [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md)。
- 🧪 **AI 生成目前只经过模拟测试**：ComfyUI 使用 `mock_comfyui/`，Codex 使用测试替身（`tests/fake_codex.py`）。模拟输出标记为 TEST FIXTURE，不是 AI 作品。真实的 Codex CLI 尚未在此运行。
- ⛔ **阶段 B（真实 ComfyUI 推理）尚未运行**。请在 ComfyUI 电脑上运行 `scripts/production_smoke_test.py`。

## 参与开发

- 规则与注意事项：[AGENTS.md](AGENTS.md)；需求：[SPECIFICATION.md](SPECIFICATION.md)。
- 运行测试：`python scripts/run_tests.py`。
- 版本历史：[CHANGELOG.md](CHANGELOG.md)；当前版本：[VERSION](VERSION)。
