# Windows 部署与阶段 B（生产环境）验收

阶段 A（离线工程验收）已在开发电脑上完成。**阶段 B 尚未运行**，必须在装有可用 ComfyUI 的 Windows 电脑上进行。

## 1. 安装

1. 安装 **Python 3.10+**（python.org，勾选 *Add python.exe to PATH*）。可选：**ffmpeg**（视频导入），放入 PATH 或设置 `ARTSTUDIO_FFMPEG`。
2. 将 `ai-game-art-studio` 文件夹复制（或 `git clone`）到目标电脑。无需其他组件 —— 像素引擎已内置（不需要 Rust 或外部程序）。
3. 启动：`powershell -ExecutionPolicy Bypass -File .\start.ps1`（首次运行会创建 `.venv` 并安装依赖，然后打开 http://127.0.0.1:8870/）。
   参数：`-Port 8870 -Workspace D:\Art\studio-ws -ComfyUrl http://127.0.0.1:8188 -NoBrowser`。

**离线安装依赖**：在联网电脑执行 `pip download -r requirements.txt -d wheels --platform win_amd64 --python-version 3.12 --only-binary=:all:`，
在目标电脑执行 `.venv\Scripts\pip install --no-index --find-links wheels -r requirements.txt`。

**语言与编码**：界面在顶栏切换 English / 简体中文；命令行/接口提示用 `ARTSTUDIO_LANG=zh-CN` 或 `--lang zh-CN`；
提示词语言在资源库中按项目设置。所有文件一律以 UTF-8 读写，不受 Windows 代码页（GBK/cp936/cp1252）影响。

## 2. 配置

复制 `studio.config.example.json` → `studio.config.json`，和/或 `.env.example` → `.env`。

| 设置 | 环境变量 | 默认值 |
|---|---|---|
| workspace | `ARTSTUDIO_WORKSPACE` | `<仓库>/workspace`（正式使用请放到源码目录外，如 `D:\GameArt\ws`） |
| port | `ARTSTUDIO_PORT` | 8870 |
| comfyui.url | `COMFYUI_URL` | http://127.0.0.1:8188 |
| comfyui.job_timeout_s | `COMFYUI_TIMEOUT` | 600 |
| language | `ARTSTUDIO_LANG` | en |
| comfyui.api_key_env | — | 存放代理令牌的环境变量**名称**（令牌本身不写入配置） |

## 3. 连接 ComfyUI

- 本机：正常启动 ComfyUI（默认端口 8188）。远程：用 `--listen 0.0.0.0` 启动并填写 `http://<主机>:8188`（ComfyUI 无身份验证，仅限可信网络）。
- 工作室「AI 生成」页的 ComfyUI 卡片应显示 **可用**、版本和 GPU。显示「模拟」说明连到了测试服务器。
- 模型放在 ComfyUI 自己的目录中；工作室通过 `/object_info` 读取服务器上实际存在的模型。

## 4. 导入工作流

1. 在 ComfyUI 中搭建或载入工作流，选择 **Workflow → Export (API)**（旧版界面：启用开发者模式 → *Save (API Format)*）。
2. 工作室 →「AI 生成」→「导入工作流」：选择 JSON、名称和类别。
3. 工作室会自动推导映射（正/反向提示词、种子、尺寸、步数、CFG、重绘幅度、LoadImage → 图片输入、模型文件 → `model_<输入>_<节点>` 参数）并记录所需节点和模型。
4. 点击「检查」，对照在线服务器校验节点与模型文件名。
5. 导入的模板初始为「未验证」。生产运行成功并经人工审核后，将 `<workspace>/comfyui/workflows/<id>.json` 中的 `"verification"` 改为 `"production-verified"`。

内置模板只使用核心节点，需要提供 `{"checkpoint": "<你的文件>.safetensors"}` 等参数（姿势模板另需 `"controlnet"`，视频模板需 `"video_checkpoint"`）。
`rembg-inspyrenet` 还需要 ComfyUI-Inspyrenet-Rembg 自定义节点，尚未验证。

## 5. 阶段 B 冒烟测试

```powershell
.venv\Scripts\python.exe scripts\production_smoke_test.py --comfy http://127.0.0.1:8188 `
   --checkpoint <你的模型.safetensors> [--controlnet <openpose.safetensors>] `
   [--reference D:\refs\hero.png] --budget 4 --steps 20 --size 768
```

脚本会检查：服务器可达（拒绝模拟服务器）、节点与模型、各内置工作流兼容性、文生图、图生图 → 导入 → 检查 → 导出、
可选的姿势关键帧、取消任务、离线回退，并在 `workspace/stage-b-smoke-report/` 中输出报告和供**人工审核**的帧总览图。

之后在界面中完成规格书 §15 测试 B 的缩减版：母版（南）→ 通过 → 东向行走（4–8 帧）→ 东向攻击（6–10 帧）→ 审核 → 再设定预算批量生成其余方向。

只有当冒烟测试在真实服务器上通过、生成的图表能干净导入、人工确认角色一致性、且 GPU 耗时可接受时，阶段 B 才算通过。

## 6. 迁移与备份

- 备份：`python -m artstudio backup D:\backups\studio.zip [--no-exports]`（或在工作室停止时直接复制 workspace 文件夹）。
- 在另一台电脑恢复：`python -m artstudio restore backup.zip D:\GameArt\ws`（目标须为空），再用 `-Workspace D:\GameArt\ws` 启动。
- 升级：workspace 带有 `schema_version`，旧版本会自动迁移，更高版本会被拒绝。
- 引擎 A 的文档保存在 workspace 中（`projects/<pid>/engine`），配方是纯 JSON 行，可在任何电脑上回放。

## 7. 在目标电脑上运行测试

`.venv\Scripts\python.exe scripts\run_tests.py`。界面测试：`pip install playwright && playwright install chromium`，
用空 workspace 启动工作室后运行 `python tests\ui_playwright.py`。
