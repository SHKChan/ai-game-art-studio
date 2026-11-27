// UI localisation: English (source strings) and Simplified Chinese.
// Text nodes and placeholder/title/aria-label attributes whose exact text is a dictionary key are
// translated automatically (MutationObserver), so UI code keeps plain English literals.
// Elements marked data-no-i18n (and textarea/pre/.mono) are never translated: user data stays as typed.

export const LANGS = { en: 'English', 'zh-CN': '简体中文' };

const ZH = {
  // navigation / shell
  'AI Game Art Studio': 'AI 游戏美术工作室', 'Project': '项目', '+ Project': '+ 项目', 'Library': '资源库',
  'Character Studio': '角色工作室', 'Animation Studio': '动画工作室', 'Procedural Studio': '程序化绘制',
  'Import & Processing': '导入与处理', 'Generation': 'AI 生成', 'Export Studio': '导出', 'Jobs': '任务',
  'No jobs yet.': '暂无任务。', 'Cancel': '取消', 'Retry': '重试', 'Open': '打开', 
  'Language': '语言', 'done': '完成', 'running': '运行中',
  'Pixel engine (Pixel Forge)': '像素引擎（像素工坊）', 'ComfyUI': 'ComfyUI', 'External assets (import)': '外部素材（导入）',
  'Codex image bridge (optional)': 'Codex 图像桥接（可选）', 'Mock generation (test fixtures)': '模拟生成（测试样本）',
  'Round-bottom fantasy potion flask (health red by default) with layered glass, liquid, cork and highlights.': '圆底奇幻药水瓶（默认红色生命药水），玻璃、液体、瓶塞和高光分层绘制。',
  'Wooden treasure chest with iron trim and a gold lock (closed).': '带铁包边和金锁的木制宝箱（关闭状态）。',
  '8-frame treasure chest opening animation (anticipation, light leak, overshoot, settle, sparkle).': '8 帧宝箱开启动画（预备晃动、漏光、过冲、回稳、闪光）。',
  'Looping 8-frame fireball projectile (faces right) with hot core, flame tongues and trailing embers.': '8 帧循环火球弹（朝右），含炽热核心、火舌和拖尾火星。',
  'Shrine of Heroes: stone temple with a sword-raising hero statue, banners and animated braziers.': '英雄神殿：石砌神殿，英雄雕像高举长剑，配有旗帜和动态火盆。',
  'banner': '旗帜颜色',
  '8-frame crescent sword-slash effect with anticipation, sweep, impact flash and dissipation.': '8 帧新月形剑气特效：预备闪光、挥扫、命中闪光与消散。', 'Prompt language': '提示词语言', 'Saved': '已保存', '— no project —': '— 无项目 —',
  // library / project
  'New project': '新建项目', 'Name': '名称', 'Game': '游戏', 'Default style': '默认风格', 'Pixel art': '像素风',
  'HD illustration': '高清插画', 'Create project': '创建项目', 'game title (optional)': '游戏名称（可选）', 'My RPG': '我的 RPG',
  'Project name': '项目名称', 'Characters': '角色', '+ Character': '+ 角色', 'Samples': '示例', 'Import knight sample': '导入骑士示例',
  'Assets': '素材', 'search…': '搜索…', 'all': '全部', 'all characters': '全部角色',
  'No assets yet — use Procedural, Import or Generation.': '还没有素材 —— 可通过程序化绘制、导入或 AI 生成创建。',
  'Create or select a project first.': '请先创建或选择一个项目。',
  // asset types / statuses / modes
  'animation': '动画', 'character_sprite': '角色精灵', 'item': '道具', 'effect': '特效', 'icon': '图标', 'tileset': '图块集',
  'environment': '场景', 'ui': '界面', 'concept': '概念图', 'other': '其他', 'pixel': '像素', 'hd': '高清',
  'draft': '草稿', 'candidate': '候选', 'approved': '已通过', 'rejected': '已否决', 'locked': '已锁定', 'unlocked': '未锁定',
  'passed': '通过', 'warnings': '有警告', 'failed': '失败', 'not_run': '未检查', 'pending': '待定', 'queued': '排队中',
  'running': '运行中', 'succeeded': '成功', 'cancelled': '已取消', 'available': '可用', 'unavailable': '不可用',
  'TEST FIXTURE': '测试样本', 'MOCK': '模拟', 'CONTAINS TEST FIXTURES': '含测试样本', 'ok': '正常', 'warn': '警告', 'err': '错误',
  // animation templates & directions
  'idle': '待机', 'walk': '行走', 'run': '奔跑', 'attack': '攻击', 'combo_attack': '连击', 'cast': '施法', 'dodge': '闪避',
  'dash': '冲刺', 'jump': '跳跃', 'hit': '受击/命中', 'death': '死亡', 'interact': '交互',
  'none': '无', 'right': '右', 'left': '左', 'south': '南（正面）', 'north': '北（背面）', 'east': '东（右侧）', 'west': '西（左侧）',
  'south_east': '东南', 'south_west': '西南', 'north_east': '东北', 'north_west': '西北', 'primary': '主参考',
  // animation studio
  'Animation': '动画', '— choose an animation asset —': '— 选择动画素材 —',
  'Pick an animation (or open one from the Library).': '选择一个动画（或从资源库打开）。',
  '▶ Play': '▶ 播放', '❚❚ Pause': '❚❚ 暂停', 'Previous frame': '上一帧', 'Next frame': '下一帧', 'Zoom': '缩放', 'BG': '背景',
  'checker': '棋盘格', 'dark': '深色', 'white': '白色', 'green': '绿色', 'blue': '蓝色', 'black': '黑色',
  'Onion skin': '洋葱皮', 'Ground line': '地面线', 'Pivot': '锚点', 'Layers': '图层', 'Loop': '循环', 'FPS': '帧率',
  'apply to all': '应用到全部', '✛ Anchor edit': '✛ 编辑锚点', 'Click to set pivot when anchor-edit is on': '开启锚点编辑后点击画布设置锚点',
  'duration ms': '时长（毫秒）', '⇆ Frame comparison': '⇆ 帧对比', 'B = source of A (before/after)': 'B = A 的源帧（处理前/后）',
  'Asset': '素材', '✓ Approve': '✓ 通过', '✗ Reject': '✗ 否决', 'Approved': '已通过', 'Rejected': '已否决',
  'Deterministic QA': '确定性检查', 'Run checks': '运行检查', 'Visual review (probabilistic)': '视觉审核（主观/概率性）',
  'Technical checks do not prove identity, anatomy or motion quality. Record your own review:': '技术检查不能证明角色一致性、结构或动作质量，请记录人工审核：',
  'review notes (what you checked / what is wrong)': '审核备注（检查了什么 / 哪里有问题）', 'Looks consistent': '看起来一致', 'Problems found': '发现问题',
  'Reprocess (from preserved sources)': '重新处理（基于保留的源帧）', 'Mode': '模式', 'Anchor': '锚定方式', 'Scale': '缩放',
  'Target height': '目标高度', 'Palette size': '调色板颜色数', 'Keep canvas': '保留画布', 'Reprocess': '重新处理', 'Reprocessed': '已重新处理',
  'source': '源坐标', 'ground': '地面', 'support_foot': '支撑脚', 'torso': '躯干', 'colours': '颜色数', 'px': '像素',
  'Events': '事件', 'event type e.g. hit': '事件类型，如 hit', '+ at current frame': '+ 添加到当前帧',
  'Layers (hybrid)': '图层（混合动画）', 'Layer': '图层', '— effect / layer asset —': '— 特效 / 图层素材 —', 'Timing': '时间',
  'start at 0ms': '从 0 毫秒开始', 'Offset x/y': '偏移 x/y', 'Attach layer': '附加图层', 'Layer attached': '图层已附加',
  'Choose a layer asset': '请选择图层素材', 'Versions': '版本', 'restore': '恢复', 'Restored': '已恢复', 'Contact sheet': '帧总览图',
  'Open contact sheet PNG': '打开帧总览图 PNG', 'Duplicate': '复制', 'Reject': '否决', 'Restore': '恢复', 'Delete': '删除', 'Nudge': '微调',
  'airborne (exempt from ground snap)': '腾空（不吸附地面）', 'phase': '阶段', 'Set phase': '设置阶段', 'Manual replacement': '手动替换',
  'Selective regeneration': '单帧重新生成', 'Provider': '生成服务', 'Workflow': '工作流', 'Fix note': '修改说明',
  'what to fix (e.g. keep both hands on the hilt)': '需要修正的内容（如：双手握住剑柄）', 'workflow parameters (JSON)': '工作流参数（JSON）',
  'Regenerate this frame': '重新生成此帧', 'Regeneration queued': '已加入重新生成队列', 'Frame regenerated': '帧已重新生成',
  'Frame replaced (placed with group scale/anchor)': '帧已替换（沿用组缩放与锚点）', 'Use as character master candidate': '用作角色母版候选',
  'Add frame as master candidate': '将此帧加入母版候选', 'Added as candidate in Character Studio': '已加入角色工作室的候选',
  'Asset has no character': '该素材未关联角色', '— workflow (ComfyUI) —': '— 工作流（ComfyUI）—',
  'This asset contains TEST FIXTURE output from a mock provider. It is not AI-generated artwork.': '此素材包含模拟服务输出的测试样本，并非 AI 生成的美术作品。',
  // character studio
  'Character': '角色', '— new character —': '— 新建角色 —', 'New character': '新建角色', 'Directions': '朝向', 'Art style': '美术风格',
  'Description': '描述', 'Create': '创建', '4 directions': '4 方向', '8 directions': '8 方向', 'side-scroller (L/R)': '横版（左/右）',
  'Adventurer': '冒险者', 'Visual style': '视觉风格', 'Camera': '镜头', 'Clothing (1/line)': '服装（每行一项）', 'Accessories': '配饰',
  'Weapon (JSON)': '武器（JSON）', 'Proportions (JSON)': '比例（JSON）', 'Palette': '调色板', 'Must keep (1/line)': '必须保持（每行一项）',
  'Negative (1/line)': '禁止项（每行一项）', 'Optional mirroring': '可选镜像',
  'Mirroring is off by default: asymmetric weapons/costumes need independently generated directions.': '镜像默认关闭：不对称的武器或服装需要为每个朝向单独生成。',
  'Save identity': '保存角色设定', 'Character saved': '角色已保存', 'Directional masters': '各方向母版', 'All directions have masters': '所有方向均已有母版',
  'no approved master': '尚无通过的母版', 'unlock': '解锁', 'reason (required to unlock/replace a locked master)': '原因（解锁或替换已锁定母版时必填）',
  'Enter a reason to change a locked master': '修改已锁定的母版前请填写原因', 'Candidates (approve → becomes locked master)': '候选（通过后成为锁定母版）',
  'Approve': '通过', 'Replace master': '替换母版', 'Approved & locked': '已通过并锁定', 'Added': '已添加', 'Concept art': '概念图',
  'Animations': '动画', 'Generate master candidate': '生成母版候选', 'Params JSON': '参数（JSON）', 'Preview prompt': '预览提示词',
  'Generate': '生成', 'Generation queued': '已加入生成队列', 'Direction matrix check': '方向矩阵检查', 'Complete': '完整',
  'Check idle/walk/attack × directions': '检查 待机/行走/攻击 × 各方向', 'History': '历史记录', '— workflow —': '— 工作流 —',
  'side': '侧视', 'top_down': '俯视', 'three_quarter': '四分之三视角', 'isometric': '等距', 'front': '正视',
  'Chibi fantasy adventurer with a red hood, blonde hair, red cape, brown adventurer outfit, brown boots and a sword.': 'Q 版奇幻冒险者：红色兜帽、金发、红色披风、棕色冒险服、棕色靴子，持剑。',
  // procedural
  'Pixel engine recipe': '像素引擎配方', 'Builder': '生成器', 'About': '说明', 'asset name (optional)': '素材名称（可选）',
  'Run with pixel engine': '用像素引擎绘制', 'Drawn by the pixel engine': '像素引擎绘制完成', 'Replay a .recipe': '回放 .recipe 配方',
  'Procedural assets': '程序化素材', 'Document inspector': '文档检查器', 'Select a procedural asset.': '请选择一个程序化素材。',
  'Open in Animation Studio': '在动画工作室中打开', 'Replay recipe': '回放配方', 'Recipe replayed into a new asset': '配方已回放为新素材',
  'Cels (editable source)': '图格（可编辑源）', 'Tool calls': '工具调用', 'size': '尺寸', 'frames': '帧数', 'liquid': '药水颜色', 'color': '颜色',
  'red': '红', 'purple': '紫', 'azure': '天蓝', 'gold': '金', 'crimson': '深红',
  // import
  'Options': '选项', 'Slicing': '切图方式', 'single image / sequence': '单张图片 / 序列', 'sprite sheet: grid': '精灵表：网格',
  'sprite sheet: auto-detect': '精灵表：自动识别', 'Grid cols/rows/count': '网格 列/行/数量', 'Background': '背景', 'keep': '保留',
  'auto (solid/checker)': '自动（纯色/棋盘格）', 'colour key': '色键抠图', 'tol': '容差', 'Group scale': '整组缩放', 'or target height': '或目标高度',
  'Pixel palette': '像素调色板', 'De-pixelate': '还原像素', 'no': '否', 'auto-detect block': '自动识别像素块', 'Frame rate': '帧率',
  'keep': '保留', 'Video fps / max': '视频帧率 / 最大帧数', 'Template': '模板', 'Direction': '方向',
  'One scale for the whole group; anchoring never resizes frames individually; the canvas expands instead of cropping. Video import': '整组使用同一缩放；锚定不会逐帧缩放；画布会扩展而不是裁切。视频导入',
  'is available (ffmpeg found).': '可用（已找到 ffmpeg）。', 'needs ffmpeg (not found).': '需要 ffmpeg（未找到）。',
  'Import & process': '导入并处理', 'Choose a file first': '请先选择文件', 'Selected': '已选择', 'Before / after': '处理前 / 处理后',
  'source frame 0': '源帧 0', 'processed frame 0': '处理后帧 0',
  'Drop PNG / sprite sheet / PNG sequence / GIF / APNG / MP4 / WebM here, or': '将 PNG / 精灵表 / PNG 序列 / GIF / APNG / MP4 / WebM 拖到这里，或',
  // generation
  'Providers (checked at runtime — unavailable providers are never substituted)': '生成服务（运行时检测 —— 不可用的服务不会被悄悄替换）',
  'Generate animation keyframes': '生成动画关键帧', 'Action template': '动作模板', 'Sheet layout': '图表布局', 'auto-detect sprites': '自动识别精灵',
  'grid (cols×rows)': '网格（列×行）', 'Note': '备注', 'revision note': '修改说明', 'Retries': '重试次数', 'Generate (1 call)': '生成（1 次调用）',
  'Batch over directions (explicit budget required)': '按方向批量生成（必须设定预算）', 'Budget (max calls)': '预算（最大调用次数）',
  'Run batch': '运行批量任务', 'ComfyUI workflow templates': 'ComfyUI 工作流模板', 'id': 'ID', 'category': '类别', 'status': '状态',
  'required nodes': '所需节点', 'models': '模型', 'Check': '检查', 'Runnable on the connected server': '可在已连接的服务器上运行',
  'Import workflow (API format JSON or studio template)': '导入工作流（API 格式 JSON 或工作室模板）', 'Import': '导入', 'name': '名称',
  'Choose a JSON file': '请选择 JSON 文件', 'Choose a character': '请选择角色', 'Your characters': '你的角色', 'Queued': '已排队', 'Generated': '已生成',
  'Mappings for prompt, negative prompt, seed, size, reference images and model files are derived automatically from the graph and validated against /object_info before every run. No checkpoint, LoRA or custom node is hardcoded.': '提示词、反向提示词、种子、尺寸、参考图和模型文件的映射会根据节点图自动推导，并在每次运行前通过 /object_info 校验。不硬编码任何 checkpoint、LoRA 或自定义节点。',
  'text_to_image': '文生图', 'image_to_image': '图生图', 'character_reference': '角色参考', 'pose_keyframe': '姿势关键帧', 'inpainting': '局部重绘',
  'image_to_video': '图生视频', 'background_removal': '去背景', 'unverified': '未验证', 'mock-tested': '模拟测试通过', 'production-verified': '生产验证通过',
  'bundled': '内置', 'user': '用户',
  // export
  'Export': '导出', 'Formats': '格式', 'Preview scale': '预览倍率', 'Atlas padding': '图集间距', 'Trim frames': '裁剪透明边',
  '— (direction mirroring source) —': '— （方向镜像来源）—', 'Exports': '导出记录', 'download zip': '下载 ZIP', 'Export finished': '导出完成',
  'Select at least one animation': '请至少选择一个动画',
  'Cocos Creator 3.x: TexturePacker plist (format 2) + PNG → SpriteAtlas, plus .anim.json timing/pivot/events for examples/cocos-creator/DirectionalSpriteAnimator.ts. Phaser 3 / PixiJS: TexturePacker JSON-hash atlas. Godot / Unity: generic JSON.': 'Cocos Creator 3.x：TexturePacker plist（格式 2）+ PNG → SpriteAtlas，另附 .anim.json（时长/锚点/事件），配合 examples/cocos-creator/DirectionalSpriteAnimator.ts 使用。Phaser 3 / PixiJS：TexturePacker JSON-hash 图集。Godot / Unity：通用 JSON。',
  // guided flow: navigation + home
  'Home': '首页', 'Animate character': '角色动画', 'Pixel assets': '像素素材',   'More tools ▸': '更多工具 ▸', 'More tools ▾': '更多工具 ▾', 'Advanced tools': '高级工具', 'Animation editor': '动画编辑器',
  'Character details': '角色详情', 'Generation & workflows': '生成与工作流', 'Welcome': '欢迎',
  'Start by creating a project — it keeps characters, animations and exports together.': '先创建一个项目 —— 角色、动画和导出都会保存在项目里。',
  'Animate a character': '制作角色动画', 'Make pixel assets': '制作像素素材', 'Import existing art': '导入已有美术',
  'Upload one character image, list the actions you need, and let Codex or your local ComfyUI draw every frame.': '上传一张角色图片，列出需要的动作，由 Codex 或本地 ComfyUI 画出每一帧。',
  'Items, icons, skill effects, props and buildings from the built-in pixel engine. Works offline, no AI needed.': '用内置像素引擎制作道具、图标、技能特效、物件和建筑。可离线使用，不需要 AI。',
  'Sprite sheets, GIFs, videos or PNG frames: remove the background, slice and align them.': '精灵表、GIF、视频或 PNG 帧：去背景、切图并对齐。',
  'Start': '开始', 'AI generators:': 'AI 生成器：', 'Codex CLI': 'Codex CLI', 'Continue': '继续上次的工作', 'Recent assets': '最近的素材',
  'Install the Codex CLI or start ComfyUI to generate character frames.': '安装 Codex CLI 或启动 ComfyUI 后即可生成角色动作帧。',
  'details': '详情', 'no reference': '无参考图',
  // guided flow: wizard
  'Actions': '动作', 'Prompts': '提示词', 'Review & export': '检查与导出', '← Back': '← 上一步', 'Next →': '下一步 →',
  'View': '视角', 'Notes': '备注', 'Reference image': '参考图', 'Replace reference': '更换参考图',
  'e.g. Fire Knight': '例如：火焰骑士', 'Character name': '角色名称',
  'Side view (platformer / side-scroller)': '侧视（平台跳跃 / 横版）', 'Top-down / RPG (4 directions)': '俯视 / RPG（4 方向）',
  'optional: anything the image does not show (e.g. carries a shield on the back)': '可选：图片上看不到的信息（如：背上背着盾牌）',
  'The reference image is the single source of truth: every action is generated to match it. Use a clean full-body image, ideally on a transparent or plain background.': '参考图是唯一标准：所有动作都按它来生成。请使用干净的全身图，最好是透明或纯色背景。',
  'Drop the character image here, or choose a file': '把角色图片拖到这里，或选择文件', 'Create & continue →': '创建并继续 →',
  'Enter a character name': '请输入角色名称', 'Add a reference image': '请添加参考图', 'Character created': '角色已创建',
  'Drop a new reference image here': '把新的参考图拖到这里', 'Replacing keeps the old image in the character history.': '更换后旧图会保留在角色历史记录中。',
  'Reference updated': '参考图已更新', 'Which actions do you need?': '需要哪些动作？', '+ Custom action': '+ 自定义动作', 'custom': '自定义',
  'custom action': '自定义动作', 'Frames': '帧数', 'Remove': '删除', 'Action name': '动作名称', 'generated': '已生成',
  'Presets come with good frame counts and timing. For anything else, add a custom action and describe it in one line — the prompt step turns it into frame-by-frame poses.': '预设动作自带合适的帧数和节奏。其他动作请添加自定义动作并用一句话描述 —— 提示词步骤会把它拆成逐帧姿势。',
  'what happens, in one line (e.g. swings the sword overhead and slams it down)': '一句话描述动作（如：把剑举过头顶再重重劈下）',
  'No actions yet — click a preset above or add a custom action.': '还没有动作 —— 点击上方预设或添加自定义动作。', 'Add at least one action': '请至少添加一个动作',
  'Write the prompts': '编写提示词', '✨ Write with Codex (reads the reference image)': '✨ 用 Codex 编写（读取参考图）', 'Use built-in template': '使用内置模板',
  'Codex is looking at the reference image and writing prompts… (usually under a minute)': 'Codex 正在查看参考图并编写提示词…（通常不到一分钟）',
  'Prompts written': '提示词已生成', 'Character description': '角色描述',
  'Character description used in every prompt (Codex fills this from the reference).': '每条提示词都会使用的角色描述（Codex 会根据参考图填写）。',
  'Codex describes the character from the image and writes frame-by-frame poses for each action. Everything stays editable.': 'Codex 根据图片描述角色，并为每个动作写出逐帧姿势。所有内容都可以修改。',
  'Codex CLI not found — install it and run codex login to let it write prompts from the image. The built-in template works offline.': '未找到 Codex CLI —— 安装并运行 codex login 后可根据图片编写提示词。内置模板可离线使用。',
  'Frame poses (one per line)': '逐帧姿势（每行一帧）', 'Prompt': '提示词', 'Poses': '姿势', 'no prompt': '无提示词', 'codex': 'Codex', 'template': '模板', 'manual': '手动',
  'No prompt yet — use one of the buttons above, or write your own.': '还没有提示词 —— 使用上方按钮生成，或自己填写。',
  'Generator': '生成器', 'Local ComfyUI': '本地 ComfyUI', 'Test fixtures (no AI)': '测试样本（非 AI）',
  'Uses your logged-in Codex account. Best at keeping the character identical across the strip.': '使用已登录的 Codex 账号。最能保持整条精灵条中角色一致。',
  'Your own models on your GPU. The reference is repeated across the strip and redrawn per pose (img2img).': '使用你自己 GPU 上的模型。参考图会铺满整条精灵条，再按每个姿势重绘（图生图）。',
  'Returns bundled sample art labelled TEST FIXTURE — for trying the workflow only.': '返回内置示例图并标记为测试样本 —— 仅用于试用流程。',
  'default (character reference img2img)': '默认（角色参考图生图）', 'Checkpoint': '模型文件', 'Denoise': '重绘强度',
  'checkpoint file, e.g. sdxl_base.safetensors': '模型文件名，如 sdxl_base.safetensors', 'Actions to generate': '要生成的动作',
  'Each action is generated as one sprite strip, then cut into frames and aligned to one ground line and scale. You can redo single frames afterwards.': '每个动作生成为一条精灵条，再切成帧并统一地面线和缩放。之后可以单独重做某一帧。',
  '▶ Generate': '▶ 开始生成', 'Review →': '检查 →', 'Choose a generator': '请选择生成器', 'Select at least one action': '请至少选择一个动作',
  'generating': '生成中', 'prompted': '已有提示词',
  '↻ Redo action': '↻ 重做动作', 'Fine-tune…': '精细调整…', 'Click to redo this frame': '点击重做此帧',
  'Click a frame to redo just that frame.': '点击某一帧即可只重做这一帧。',
  'Frames were cut on an even grid because the generator did not return separate sprites — check the frames.': '生成结果中的角色没有分开，已按等宽网格切帧 —— 请检查各帧。',
  'Nothing generated yet.': '还没有生成内容。', 'For': '用于', 'approved only': '仅已通过', 'Everything': '全部格式',
  'PNG frames + sheets + GIF': 'PNG 帧 + 精灵表 + GIF', '⬇ Download ZIP': '⬇ 下载 ZIP', 'Cocos Creator': 'Cocos Creator', 'Godot': 'Godot', 'Phaser / PixiJS': 'Phaser / PixiJS',
  // tools (names) + Pixel Forge editor + theme
  'Motion Studio': '动作工作室', 'Pixel Forge': '像素工坊', 'Asset Import': '素材导入', 'Pixel documents': '像素文档',
  'Animate a character: upload one image, list the actions you need, and let Codex or your local ComfyUI draw every frame.': '制作角色动画：上传一张图片，列出需要的动作，由 Codex 或本地 ComfyUI 画出每一帧。',
  'Skill effects, items, icons and scenery from the built-in pixel engine — tweak speed, colours, outline and glow live. Works offline.': '用内置像素引擎制作技能特效、道具、图标和场景 —— 实时调整速度、颜色、描边和光晕。可离线使用。',
  'Bring in sprite sheets, GIFs, videos or PNG frames: remove the background, slice and align them.': '导入精灵表、GIF、视频或 PNG 帧：去背景、切图并对齐。',
  'Pick something to make, then adjust it on the right.': '选择要制作的内容，然后在右侧调整。', 'Skills & effects': '技能与特效', 'Items & icons': '道具与图标',
  'Scenery': '场景', 'Saved in this project': '本项目已保存', 'open': '打开', 'editing a copy': '编辑副本', 'Preview': '预览', 'light': '浅色',
  'rendering…': '渲染中…', 'rendered in': '渲染耗时', 'Variant': '样式', 'Speed & loop': '速度与循环', 'Speed': '速度', 'Colours': '颜色', 'Hue': '色相',
  'Saturation': '饱和度', 'Brightness': '亮度', 'Reset colours': '重置颜色', 'Outline & glow': '描边与光晕', 'Outline': '描边', 'Glow': '光晕',
  'auto': '自动', 'Flip horizontally': '水平翻转', 'Output scale': '输出放大', 'Outline colour': '描边颜色', 'Glow colour': '光晕颜色', 'Save': '保存',
  'Asset name': '素材名称', 'Save to library': '保存到资源库', 'Save & export': '保存并导出', 'Reset all': '全部重置', 'Saved to library': '已保存到资源库',
  'Open in editor': '在编辑器中打开', 'thickness': '粗细', 'element': '元素', 
  'Theme': '主题', 'System theme': '跟随系统', 'Dark': '深色', 'Light': '浅色', 
  '8-frame healing effect: pulsing ground glow, rising light column and floating plus-shaped motes.': '8 帧治疗特效：脉动的地面光圈、上升的光柱和漂浮的十字光点。',
  '8-frame looping buff aura: rotating ring at the feet, rising energy streaks and upward chevrons.': '8 帧循环增益光环：脚下旋转的光环、上升的能量光束和向上的箭头。',
  '8-frame lightning strike: bolt from the sky, impact flash, shock ring, branches and sparks.': '8 帧落雷：闪电从天而降、命中闪光、冲击环、分叉和火花。',
  '8-frame shield barrier: hexagon bubble forms, flashes, shimmers and dissolves (see-through interior).': '8 帧护盾：六边形护罩形成、闪光、流光后消散（内部半透明）。',
  '8-frame frost nova: centre flash, outward ring of ice shards, frost ring and drifting snow.': '8 帧冰霜新星：中心闪光、向外扩散的冰刺环、霜环和飘雪。',
  '8-frame looping poison cloud: churning toxic cloud, popping bubbles and falling drips.': '8 帧循环毒云：翻滚的毒雾、破裂的气泡和滴落的毒液。',
  'yellow': '黄', 'orange': '橙', 'ice': '冰', 'arcane': '奥术', 'toxic': '剧毒', 'lightning': '雷电', 'poison': '毒',
  // v0.6 — grid skills, JRPG icons
  'Top-down lava burn for a grid: cracks glow, magma floods the tiles, burns in a loop, then cools (tags cast/burn/fade).': '俯视方格熔岩灼地：地面龟裂发光、岩浆涌出淹没格子、持续燃烧（循环），最后冷却（标签 cast/burn/fade）。',
  'Top-down meteor strike for a grid: warning ring, flaming rock falls, fire-dome explosion, smoking crater.': '俯视方格陨石坠落：警示圈、燃烧的陨石落下、火焰穹顶爆炸、冒烟的陨坑。',
  'Top-down fire pillar: rune circle flares, a churning column of fire erupts (loop), collapses to embers.': '俯视火柱：符文圈亮起，翻腾的火柱冲天而起（循环），最后塌缩成火星。',
  'Top-down earth spikes for a grid: ground cracks, rock spikes burst up on every cell, dust ring, crumble.': '俯视方格地刺：地面开裂，每格都有岩刺破土而出，扬起尘环，随后崩碎。',
  'Top-down whirlpool for a grid: spiralling vortex with foam crests, dark eye and rim splashes (8-frame loop).': '俯视方格漩涡：螺旋水流、泡沫浪峰、漩涡中心和边缘水花（8 帧循环）。',
  'Tornado on a grid cell: spinning striped funnel, ground dust ring and orbiting leaves (8-frame loop).': '格子上的龙卷风：旋转的条纹漏斗、地面尘环和环绕的落叶（8 帧循环）。',
  'Top-down ice field for a grid: frost spreads, crystal clusters grow, glints while held (loop), shatters.': '俯视方格冰封大地：寒霜蔓延、冰晶簇生长、冰面闪光（循环），最后碎裂。',
  'Top-down holy judgment for a grid: magic circle inscribes, pillar of light falls, cross flash, rising motes.': '俯视方格圣光审判：魔法阵刻画成形、光柱从天而降、十字闪光、光点升腾。',
  'Top-down dark curse field for a grid: turning rune ring, curling shadow tendrils, void core, rising motes (loop).': '俯视方格暗黑诅咒之地：旋转的符文环、卷曲的暗影触手、虚空核心、上升的暗光粒子（循环）。',
  'Life drain on a grid cell: curse sigil, essence ribbons spiral up into a pulsing orb that darts away.': '格子上的生命汲取：诅咒印记，生命精华螺旋升起汇入跳动的光球，随后飞走。',
  '16×16 status badge: stat up/down (ATK, DEF, SPD, MAG) and ailments (poison, burn, freeze, sleep, …).': '16×16 状态徽章：属性升降（攻击、防御、速度、魔力）与异常状态（中毒、灼烧、冰冻、睡眠……）。',
  'Skill icons': '技能图标', 'tiles': '格数', 'kind': '种类', 'material': '材质', 'frame': '边框', 'skill': '技能', 'silver': '银', 'fire': '火',
  'water': '水', 'wind': '风', 'holy': '圣', 'earth': '土', 'physical': '物理', 'blood': '血', 'nature': '自然', 'frost': '霜',
  'sand': '沙', 'storm': '风暴', 'crystal': '水晶', 'soul': '灵魂', 'mana': '魔力', 'moon': '月', 'sun': '日', 'void': '虚空',
  'lava': '熔岩', 'soulfire': '魂火', 'acid': '酸液', 'abyss': '深渊', 'iron': '铁', 'bronze': '青铜', 'mithril': '秘银', 'common': '普通',
  'uncommon': '优秀', 'rare': '稀有', 'epic': '史诗', 'legendary': '传说', 'burn': '灼烧', 'fade': '消退', 'sword': '剑', 'katana': '太刀',
  'dagger': '匕首', 'axe': '斧', 'spear': '枪', 'staff': '法杖', 'bow': '弓', 'hammer': '锤', 'helmet': '头盔', 'armor': '铠甲',
  'shield': '盾', 'gauntlet': '护手', 'boots': '靴子', 'cloak': '披风', 'ring': '戒指', 'amulet': '护符', 'hp_potion': 'HP 药水', 'mp_potion': 'MP 以太',
  'antidote': '解毒剂', 'elixir': '万能药', 'phoenix_feather': '凤凰之羽', 'scroll': '卷轴', 'bomb': '炸弹', 'onigiri': '饭团', 'ore': '矿石', 'ingot': '锭',
  'gem': '宝石', 'herb': '草药', 'mushroom': '蘑菇', 'key': '钥匙', 'coin_pouch': '钱袋', 'lava_burn': '熔岩灼地', 'meteor': '陨石', 'fire_pillar': '火柱',
  'earth_spike': '地刺', 'whirlpool': '漩涡', 'gale': '暴风', 'ice_field': '冰封大地', 'holy_judgment': '圣光审判', 'revive': '复活', 'dark_vortex': '暗黑漩涡', 'curse': '诅咒',
  'life_drain': '生命汲取', 'heal': '治疗', 'barrier': '结界', 'haste': '加速', 'slash': '斩击', 'thunder': '雷击', 'atk_up': '攻击↑', 'atk_down': '攻击↓',
  'def_up': '防御↑', 'def_down': '防御↓', 'spd_up': '速度↑', 'spd_down': '速度↓', 'mag_up': '魔力↑', 'mag_down': '魔力↓', 'freeze': '冰冻', 'paralysis': '麻痹',
  'sleep': '睡眠', 'petrify': '石化', 'silence': '沉默', 'blind': '失明', 'stun': '眩晕', 'regen': '再生', 'charm': '魅惑',
  // v0.6 — UI kit, icon tiers
  "JRPG weapon icon (32/48/64 px): 8 kinds × 5 tiers — each tier changes the shape (fuller, guards, runes, wings, serration).": '日式 RPG 武器图标（32/48/64 像素）：8 种武器 × 5 个档次 —— 每档造型都不同（血槽、护手、符文、翅膀、锯齿）。',
  "JRPG armour/accessory icon (32/48/64 px): 8 kinds × 5 tiers — each tier changes the design (rivets, gems, wings, horns).": '日式 RPG 防具/饰品图标（32/48/64 像素）：8 种 × 5 个档次 —— 每档设计都不同（铆钉、宝石、翅膀、尖角）。',
  "JRPG consumable icon (32/48/64 px): 8 kinds × 3 grades (minor / normal / greater) with different bottles and details.": '日式 RPG 消耗品图标（32/48/64 像素）：8 种 × 3 个品级（小/中/大），瓶型和细节各不相同。',
  "JRPG material icon (32/48/64 px): ore, ingot, gem, crystal, herb, mushroom, key, coin pouch — each colour is its own design.": '日式 RPG 素材图标（32/48/64 像素）：矿石、锭、宝石、魔晶、草药、蘑菇、钥匙、钱袋 —— 每种颜色都是独立设计。',
  "Square skill icon (32/48/64 px): lit bevelled element frame + shaded emblem for 18 skills (lava burn, meteor, holy judgment, …).": '方形技能图标（32/48/64 像素）：带光照斜面的元素边框 + 立体明暗徽记，18 个技能（熔岩灼地、陨石、圣光审判……）。',
  "JRPG UI panel: window, dialog, tooltip, title banner or tab in 4 themes (classic blue, wood & gold, stone & iron, parchment); 9-slice ready.": '日式 RPG 界面面板：窗口、对话框、提示框、标题横幅或分页标签，4 种主题（经典蓝窗、木框金边、石材铁框、羊皮纸），支持九宫格拉伸。',
  "JRPG UI button in 4 themes (rect, square or round); frames = normal / hover / pressed / disabled.": '日式 RPG 按钮，4 种主题（长条、方形或圆形）；帧 = 普通 / 悬停 / 按下 / 禁用。',
  "JRPG gauge: HP, MP, EXP, stamina or ATB bar in 4 themes; `fill` 0–1; part = bar / frame / fill.": '日式 RPG 数值条：HP、MP、EXP、体力或 ATB，4 种主题；`fill` 0–1；part = 整条 / 边框 / 填充。',
  "JRPG UI frame: portrait frame, item slot or skill slot in 4 themes; slots = normal / selected / locked.": '日式 RPG 界面框：头像框、物品格或技能格，4 种主题；格子 = 普通 / 选中 / 锁定。',
  "JRPG menu icon (32/48/64 px): bag, equipment, skills, map, quest, shop, settings, save, gold, gem, cursor … colour or white.": '日式 RPG 菜单图标（32/48/64 像素）：背包、装备、技能、地图、任务、商店、设置、存档、金币、宝石、光标……彩色或白色。',
  'UI': '界面', 'grade': '品级', 'minor': '小', 'normal': '中', 'greater': '大', 'theme': '主题', 'classic_blue': '经典蓝窗', 'wood_gold': '木框金边',
  'stone_iron': '石材铁框', 'parchment': '羊皮纸', 'width': '宽度', 'height': '高度', 'shape': '形状', 'rect': '长条', 'square': '方形', 'round': '圆形',
  'fill': '填充', 'part': '部件', 'bar': '整条', 'hp': 'HP', 'mp': 'MP', 'exp': 'EXP', 'stamina': '体力', 'atb': 'ATB',
  'window': '窗口', 'dialog': '对话框', 'tooltip': '提示框', 'title': '标题横幅', 'tab': '分页标签', 'portrait': '头像框', 'slot': '物品格', 'skill_slot': '技能格',
  'style': '样式', 'mono': '白色', 'bag': '背包', 'equipment': '装备', 'skills': '技能', 'map': '地图', 'quest': '任务', 'shop': '商店',
  'settings': '设置', 'save': '存档', 'home': '主页', 'mail': '邮件', 'battle': '战斗', 'speed': '倍速', 'confirm': '确认', 'close': '关闭',
  'back': '返回', 'cursor': '光标',
  // v0.7 character kit
  'character_kit': '角色套装', 'preset': '职业', 'base': '基底', 'male': '男', 'female': '女', 'knight': '骑士', 'mage': '法师',
  'ranger': '游侠', 'priest': '牧师', 'berserker': '狂战士', 'necromancer': '死灵法师', 'skeleton': '骷髅兵', 'facing': '朝向', 'rear': '背面', 'action': '动作',
  'Unarmed_Idle': '空手待机', 'Unarmed_Walk': '空手行走', 'Unarmed_Run': '空手奔跑', 'Unarmed_Hurt': '空手受击', 'Unarmed_Death': '空手倒地', 'Sword_Idle': '持剑待机', 'Sword_Walk': '持剑行走', 'Sword_Run': '持剑奔跑', 'Sword_Attack': '挥剑攻击', 'Sword_Walk_Attack': '边走边砍', 'Sword_Run_Attack': '边跑边砍', 'Sword_Hurt': '持剑受击', 'Sword_Death': '持剑倒地', 'Bow_Attack': '弓箭射击', 'Cast_Spell': '施法', 'Summon_Rise': '召唤破土',
  '4-direction base character (Craftpix pack) — plain or as knight / mage / ranger / priest / berserker / necromancer / skeleton; 13 actions + bow attack, spell cast, summon rise. Needs the local base pack.': '四方向基础角色（Craftpix 素材包）——原样或装扮成骑士 / 法师 / 游侠 / 牧师 / 狂战士 / 死灵法师 / 骷髅兵；13 个动作 + 弓箭射击、施法、召唤破土。需要本地基础素材包。',
  // error codes (job.error_code)
  'err:provider_unavailable': '生成服务不可用', 'err:missing_models': '服务器上缺少所需模型', 'err:missing_nodes': '服务器上缺少所需节点',
  'err:invalid_values': '工作流参数值无效', 'err:invalid_workflow': 'ComfyUI 拒绝了该工作流', 'err:execution_error': '生成执行失败',
  'err:timeout': '生成超时', 'err:unreachable': '无法连接 ComfyUI', 'err:budget_exceeded': '已超出生成预算', 'err:no_outputs': '没有可取回的输出',
  'err:sheet_rejected': '生成的图表多次检查不合格', 'err:sheet_background': '无法去除图表背景', 'err:sheet_empty': '生成的图表是空的', 'err:no_description': '请先描述角色',
  // v0.5 — start options, pipeline, sprite editor
  'I have a reference image': '我有参考图', 'Describe it — generate a reference': '用文字描述，生成参考图', 'Describe the character': '描述角色',
  'Style notes': '画风备注', 'optional style notes, e.g. 16-bit SNES look, dark outline': '可选画风备注，如 16 位 SNES 风格、深色描边',
  'e.g. chibi knight, spiky blond hair, silver armour with gold trim, red cape, holds a big two-handed sword on the shoulder': '例如：Q 版骑士，金色刺猬头，银甲金边，红披风，肩扛一把双手大剑',
  'The generator draws 4 candidates from this description. You pick one; it becomes the locked reference that every action must match.': '生成服务会按描述画 4 张候选。你挑一张，它会成为锁定的参考图，之后所有动作都以它为准。',
  'Generator': '生成服务', 'Generate 4 candidates →': '生成 4 张候选 →', 'Candidates ready — pick one': '候选已生成，挑一张吧', 'Describe the character first': '请先描述角色',
  'Choose a generator': '请选择生成服务', 'Local ComfyUI (text-to-image workflow)': '本地 ComfyUI（文生图工作流）', 'Test fixtures (no AI)': '测试样本（非 AI）',
  'Generated candidates': '生成的候选', 'No candidates yet.': '还没有候选。', 'Generate more': '再生成', 'Description': '描述', '↻ Generate 4 more': '↻ 再生成 4 张',
  'what should change? e.g. bigger sword, darker armour': '要改什么？如：剑再大一些、盔甲颜色更深', '✓ Use this': '✓ 用这张', 'reference': '参考图', 'Reference locked': '参考图已锁定',
  'no reference yet — pick a candidate below': '还没有参考图——请在下方挑选候选',
  'Core set: walk · attack · hit': '核心三件套：行走 · 攻击 · 受击', 'Grid the generator draws: columns × rows': '生成时的网格：列 × 行',
  'Processing': '本地处理', 'Character height (px)': '角色高度（像素）', 'Palette colours': '调色板颜色数', 'Automatic retries': '自动重画次数',
  'Each action comes back as ONE sheet. It is cut into frames, scaled once so the character is this tall, put on one ground line, snapped to the reference palette and cleaned (halo, stray pixels). A sheet that fails the checks (empty cell, wrong size, merged sprites) is regenerated automatically.': '每个动作生成一张图表：切成单帧，整张统一缩放到这个角色高度，对齐同一条地面线，颜色锁定到参考图调色板，并清理白边和杂点。检查不合格（空格、大小不一、角色粘连）会自动重画。',
  'Runs as a queue: every selected action is generated, checked and cut one after another. You can leave it running and review everything at the end.': '按队列运行：选中的动作依次生成、检查、切图。可以放着让它跑，最后统一审核。',
  '▶ Run pipeline': '▶ 运行流水线', '✎ Edit pixels': '✎ 编辑像素', 'Edit pixels': '编辑像素', 'Timing & events…': '节奏与事件…', 'Height': '高度', 'Re-cut': '重新切图',
  'Cut the original sheet again at another size (hand edits are kept)': '按新尺寸重新切原图（保留手改像素）', 'Re-cut from the original sheet': '已从原图重新切图',
  'hand edits need a check': '手改像素需检查', 'needs review': '需审核',
  'Sprite editor': '精灵编辑器', 'Pixel': '像素', 'Pencil': '铅笔', 'Eraser': '橡皮', 'Picker': '吸管', 'Fill': '油漆桶', 'Line': '直线', 'Rectangle': '矩形', 'Select': '框选', 'Mirror': '镜像', 'Size': '粗细',
  'Click a pixel to inspect it: change its colour, delete it, or replace that colour everywhere': '点一个像素查看：改颜色、删除，或把同色全部替换',
  'Draw with the current colour': '用当前颜色画', 'Erase to transparent': '擦成透明', 'Pick a colour from the frame': '从画面取色',
  'Fill the connected area (Alt: every pixel of that colour)': '填充相连区域（按住 Alt：填充所有同色像素）', 'Straight line': '画直线', 'Rectangle outline (Shift: filled)': '矩形边框（按住 Shift：实心）',
  'Select an area, then drag to move it (Alt-drag copies)': '框选一块区域后拖动移动（按住 Alt 拖动为复制）', 'Brush size ([ and ])': '笔刷粗细（[ 和 ]）',
  'Mirror the whole frame horizontally (H with no selection)': '整帧水平镜像（无选区时按 H）', 'Colour hex': '颜色值', 'Choose colour': '选择颜色',
  'Current colour (X swaps with the second colour)': '当前颜色（按 X 与第二颜色互换）', 'Second colour': '第二颜色', 'Palette (colours used in this animation)': '调色板（本动画用到的颜色）',
  'Pixel inspector': '像素检查器', 'Pick the Pixel tool (P) and click any pixel. You can recolour it, delete it, or replace that colour in this frame or the whole animation. Arrow keys move to the next pixel; Enter paints the current colour, Delete removes the pixel.': '选择像素工具（P）后点击任意像素：可以改色、删除，或把这个颜色在本帧或整个动画里替换。方向键移动到相邻像素，Enter 涂上当前颜色，Delete 删除该像素。',
  'transparent': '透明', 'Change this pixel to:': '把这个像素改成：', 'New colour for this pixel': '这个像素的新颜色', 'Current colour': '当前颜色', 'Delete pixel': '删除像素',
  'Use this colour': '取用这个颜色', 'Replace this colour with the current colour': '把这个颜色替换成当前颜色', 'This frame': '本帧', 'All frames': '全部帧', 'Remove this colour from the frame': '从本帧删除这个颜色',
  'Transparent pixel': '透明像素', 'Copied': '已复制', 'Selection': '选区',
  'Select tool (M): drag a box, drag inside it to move, Alt-drag to copy. Ctrl+C / Ctrl+V copy and paste (also between frames), H flips, Delete clears, Enter or Esc places it.': '框选工具（M）：拖出选框，在框内拖动移动，按住 Alt 拖动复制。Ctrl+C / Ctrl+V 复制粘贴（可跨帧），H 翻转，Delete 清除，Enter 或 Esc 放下。',
  'Copy': '复制', 'Paste': '粘贴', 'Flip': '翻转', 'Clear': '清除', 'Save': '保存', 'Grid': '网格', 'Ground': '地面线', 'Fit': '适应窗口',
  'Undo (Ctrl+Z)': '撤销（Ctrl+Z）', 'Redo (Ctrl+Shift+Z)': '重做（Ctrl+Shift+Z）', 'Save (Ctrl+S)': '保存（Ctrl+S）', 'Close (Esc)': '关闭（Esc）',
  'Show the previous / next frame faintly (O)': '半透明显示前后帧（O）', 'Pixel grid': '像素网格', 'Ground line and pivot': '地面线和锚点',
  'Zoom out (-)': '缩小（-）', 'Zoom in (+)': '放大（+）', 'Fit to window (0)': '适应窗口（0）', 'Play / pause (Shift+P)': '播放 / 暂停（Shift+P）',
  'Frame duration (ms)': '帧时长（毫秒）', 'Duration': '时长', 'Insert a copy of this frame after it': '在后面插入这一帧的副本', 'Move frame left': '帧左移', 'Move frame right': '帧右移',
  'Delete frame': '删除帧', 'Duplicate frame': '复制帧', 'Delete this frame': '删除这一帧', 'Delete this frame?': '删除这一帧？', 'Undo hand edits of this frame': '撤销本帧的手改', 'Back to the processed frame': '恢复为处理后的原帧',
  'Remove all saved hand edits of this frame?': '删除这一帧已保存的全部手改？', ', / . previous / next frame': ', / . 切换上一帧 / 下一帧',
  'Space+drag or middle mouse to pan · Ctrl+wheel to zoom': '空格+拖动或鼠标中键平移 · Ctrl+滚轮缩放', 'has hand edits': '有手改像素',
  'You have unsaved pixel edits. Close without saving?': '有未保存的像素修改，确定不保存就关闭？', 'Only animations can be edited here': '这里只能编辑动画',
  'The action was re-cut at a different size after these hand edits — check them.': '手改之后动作按不同尺寸重新切过图，请检查这些手改。', 'Enter': '回车',
  'err:bad_request': '请求无效', 'err:codex_failed': 'Codex 调用失败', 'err:no_reference': '请先添加参考图', 'err:engine_error': '像素引擎错误', 'err:error': '错误', 'err:environment': '运行环境不符合要求',
};

// Dynamic strings: [regex, replacement]
const ZH_PATTERNS = [
  [/^(\d+) frames$/, '$1 帧'], [/^(\d+) generation call\(s\) — one image per action$/, '$1 次生成调用 —— 每个动作一张图'],
  [/^(\d+)\/(\d+) actions generated$/, '已生成 $1/$2 个动作'], [/^Failed: (.*)$/, '失败：$1'], [/^Poses: (\d+), frames: (\d+)$/, '姿势 $1 个，帧数 $2'],
  [/^(\d+) frames · (.*)$/, '$1 帧 · $2'], [/^(.+) — frame (\d+): what should change\? \(leave empty to just redo it\)$/, '$1 —— 第 $2 帧：需要修改什么？（留空则直接重做）'],
  [/^(\d+) file\(s\): (.*)$/, '$1 个文件：$2'], [/^Imported (\d+) knight animations$/, '已导入 $1 个骑士动画'],
  [/^Missing: (.*)$/, '缺少：$1'], [/^(\d+) files$/, '$1 个文件'], [/^(\d+) tools$/, '$1 个工具'],
  [/^Frames \((\d+)\)$/, '帧（$1）'], [/^Frame #(\d+)$/, '第 $1 帧'], [/^Pivot set to (.*)$/, '锚点已设为 $1'],
  [/^Imported (.+) \(unverified\)$/, '已导入 $1（未验证）'], [/^Batch queued \(budget (\d+)\)$/, '批量任务已排队（预算 $1）'],
  [/^(\d+)\/(\d+) masters$/, '$1/$2 个母版'], [/^Not runnable: (.*)$/, '无法运行：$1'], [/^mirrored from (\w+) \(optional\)$/, '由 $1 镜像（可选）'],
  [/^(.*) is unavailable: (.*)$/, '$1 不可用：$2'], [/^(.+) unavailable: (.*)$/, '$1 不可用：$2'],
];

let LANG = 'en';
const SKIP = 'textarea, pre, .mono, [data-no-i18n], script, style';

export function getLang() { return LANG; }

export function t(s) {
  if (LANG === 'en' || typeof s !== 'string') return s;
  const key = s.trim();
  if (Object.prototype.hasOwnProperty.call(ZH, key)) return s.replace(key, ZH[key]);
  for (const [re, rep] of ZH_PATTERNS) if (re.test(key)) return s.replace(key, key.replace(re, rep));
  return s;
}

export function tError(code, message) {
  if (LANG === 'en' || !code) return message;
  const k = 'err:' + code;
  return ZH[k] ? `${ZH[k]}${message ? '（' + message + '）' : ''}` : message;
}

function translateNode(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    const p = node.parentElement;
    if (!p || p.closest(SKIP)) return;
    const v = node.nodeValue;
    if (v && v.trim()) { const tv = t(v); if (tv !== v) node.nodeValue = tv; }
    return;
  }
  if (node.nodeType !== Node.ELEMENT_NODE || node.closest(SKIP)) return;
  for (const attr of ['placeholder', 'title', 'aria-label']) {
    const v = node.getAttribute(attr);
    if (v) { const tv = t(v); if (tv !== v) node.setAttribute(attr, tv); }
  }
  for (const c of node.childNodes) translateNode(c);
}

export function initI18n() {
  let saved = null;
  try { saved = localStorage.getItem('artstudio.lang'); } catch (e) { /* storage unavailable */ }
  LANG = saved || ((navigator.language || '').toLowerCase().startsWith('zh') ? 'zh-CN' : 'en');
  if (!LANGS[LANG]) LANG = 'en';
  document.documentElement.lang = LANG;
  if (LANG !== 'en') {
    translateNode(document.body);
    new MutationObserver((muts) => {
      for (const m of muts) {
        if (m.type === 'characterData') translateNode(m.target);
        for (const n of m.addedNodes) translateNode(n);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  }
  return LANG;
}

export function setLang(lang) {
  try { localStorage.setItem('artstudio.lang', lang); } catch (e) { /* ignore */ }
  location.reload();
}
