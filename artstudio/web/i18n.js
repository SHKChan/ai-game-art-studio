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
  'No jobs yet.': '暂无任务。', 'Cancel': '取消', 'Retry': '重试', 'Open': '打开', 'Toggle light/dark': '切换明暗主题',
  'Language': '语言', 'done': '完成', 'running': '运行中',
  'Pixel engine (Engine A)': '像素引擎（引擎 A）', 'ComfyUI': 'ComfyUI', 'External assets (import)': '外部素材（导入）',
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
  'Choose a JSON file': '请选择 JSON 文件', 'Choose a character': '请选择角色', 'Queued': '已排队', 'Generated': '已生成',
  'Mappings for prompt, negative prompt, seed, size, reference images and model files are derived automatically from the graph and validated against /object_info before every run. No checkpoint, LoRA or custom node is hardcoded.': '提示词、反向提示词、种子、尺寸、参考图和模型文件的映射会根据节点图自动推导，并在每次运行前通过 /object_info 校验。不硬编码任何 checkpoint、LoRA 或自定义节点。',
  'text_to_image': '文生图', 'image_to_image': '图生图', 'character_reference': '角色参考', 'pose_keyframe': '姿势关键帧', 'inpainting': '局部重绘',
  'image_to_video': '图生视频', 'background_removal': '去背景', 'unverified': '未验证', 'mock-tested': '模拟测试通过', 'production-verified': '生产验证通过',
  'bundled': '内置', 'user': '用户',
  // export
  'Export': '导出', 'Formats': '格式', 'Preview scale': '预览倍率', 'Atlas padding': '图集间距', 'Trim frames': '裁剪透明边',
  '— (direction mirroring source) —': '— （方向镜像来源）—', 'Exports': '导出记录', 'download zip': '下载 ZIP', 'Export finished': '导出完成',
  'Select at least one animation': '请至少选择一个动画',
  'Cocos Creator 3.x: TexturePacker plist (format 2) + PNG → SpriteAtlas, plus .anim.json timing/pivot/events for examples/cocos-creator/DirectionalSpriteAnimator.ts. Phaser 3 / PixiJS: TexturePacker JSON-hash atlas. Godot / Unity: generic JSON.': 'Cocos Creator 3.x：TexturePacker plist（格式 2）+ PNG → SpriteAtlas，另附 .anim.json（时长/锚点/事件），配合 examples/cocos-creator/DirectionalSpriteAnimator.ts 使用。Phaser 3 / PixiJS：TexturePacker JSON-hash 图集。Godot / Unity：通用 JSON。',
  // error codes (job.error_code)
  'err:provider_unavailable': '生成服务不可用', 'err:missing_models': '服务器上缺少所需模型', 'err:missing_nodes': '服务器上缺少所需节点',
  'err:invalid_values': '工作流参数值无效', 'err:invalid_workflow': 'ComfyUI 拒绝了该工作流', 'err:execution_error': '生成执行失败',
  'err:timeout': '生成超时', 'err:unreachable': '无法连接 ComfyUI', 'err:budget_exceeded': '已超出生成预算', 'err:no_outputs': '没有可取回的输出',
  'err:bad_request': '请求无效', 'err:engine_error': '像素引擎错误', 'err:error': '错误', 'err:environment': '运行环境不符合要求',
};

// Dynamic strings: [regex, replacement]
const ZH_PATTERNS = [
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
