// Character, Procedural, Import & Processing, Generation and Export studios.
import { S, api, el, toast, guard, emit, fileUrl, charUrl, exportUrl, badge, fixtureBadge, refreshProject, select, readFile, waitJob, assetsOfProject, field, DIRS } from './core.js';

const lines = (v) => (v || '').split('\n').map(s => s.trim()).filter(Boolean);
const needProject = (root) => { if (!S.project) { root.innerHTML = '<p class="muted">Create or select a project first.</p>'; return true; } return false; };
const providerSelect = (ids, value) => select(S.providers.filter(p => ids.includes(p.id)).map(p => [p.id, `${p.name}${p.status.available ? '' : ' — unavailable'}`]), value);

// ------------------------------------------------------------------ Character Studio
export async function renderCharacter(root) {
  if (needProject(root)) return;
  root.innerHTML = '';
  const chars = S.data.characters;
  const pick = select([['', '— new character —'], ...chars.map(c => [c.id, c.name])], S.character || '');
  pick.onchange = () => { S.character = pick.value || null; renderCharacter(root); };
  root.append(el('div', { class: 'row' }, el('b', {}, 'Character'), pick));
  if (!S.character) return root.append(newCharacterForm(root));
  const c = await api(`/api/projects/${S.project}/characters/${S.character}`);
  const ta = (v) => el('textarea', {}, (v || []).join('\n'));
  const desc = el('textarea', {}, c.description), style = el('input', { value: c.visual_style }), cam = select(['side', 'top_down', 'three_quarter', 'isometric', 'front'], c.camera);
  const clothing = ta(c.clothing), acc = ta(c.accessories), cons = ta(c.constraints), neg = ta(c.negative_constraints);
  const weapon = el('textarea', { class: 'mono' }, JSON.stringify(c.weapon || {}, null, 1)), props = el('textarea', { class: 'mono' }, JSON.stringify(c.proportions || {}, null, 1));
  const palette = el('input', { value: (c.palette || []).join(' '), placeholder: '#rrggbb #rrggbb …' });
  const mirror = el('input', { type: 'checkbox', checked: c.mirroring.enabled });
  const save = el('button', { class: 'primary', onclick: () => guard(async () => {
    const pairs = mirror.checked ? Object.fromEntries(Object.entries({ left: 'right', west: 'east', north_west: 'north_east', south_west: 'south_east' }).filter(([k]) => c.directions.includes(k))) : {};
    await api(`/api/projects/${S.project}/characters/${c.id}/update`, { body: { description: desc.value, visual_style: style.value, camera: cam.value,
      clothing: lines(clothing.value), accessories: lines(acc.value), constraints: lines(cons.value), negative_constraints: lines(neg.value),
      weapon: JSON.parse(weapon.value || '{}'), proportions: JSON.parse(props.value || '{}'), palette: palette.value.split(/\s+/).filter(Boolean),
      mirroring: { enabled: mirror.checked, pairs } } });
    toast('Character saved'); await refreshProject(); renderCharacter(root);
  }) }, 'Save identity');
  // directional masters
  const reason = el('input', { placeholder: 'reason (required to unlock/replace a locked master)', style: 'width:100%' });
  const needReason = () => { if (!reason.value.trim()) throw new Error('Enter a reason to change a locked master'); return reason.value.trim(); };
  const dirs = el('div', { class: 'dirs' });
  for (const d of ['primary', ...c.directions]) {
    const m = c.masters[d];
    const mirrored = c.mirroring.enabled && c.mirroring.pairs[d] && c.masters[c.mirroring.pairs[d]];
    dirs.append(el('div', { class: 'dir' }, el('div', { class: 'small' }, el('b', {}, d), ' ', m ? badge(m.locked ? 'locked' : 'unlocked', m.locked ? 'locked' : 'warn') : null, m?.is_test_fixture ? badge('TEST FIXTURE', 'fixture') : null),
      m ? el('div', { class: 'checker' }, el('img', { src: charUrl(c, m.file) })) : el('div', { class: 'muted small' }, mirrored ? `mirrored from ${c.mirroring.pairs[d]} (optional)` : 'no approved master'),
      m && m.locked ? el('button', { class: 'small', onclick: () => guard(async () => { const r = needReason();
        await api(`/api/projects/${S.project}/characters/${c.id}/masters/${d}/unlock`, { body: { reason: r } }); renderCharacter(root); }) }, 'unlock') : null));
  }
  // candidates
  const cands = el('div', { class: 'assets' });
  for (const k of [...c.candidates].reverse()) {
    cands.append(el('div', { class: 'asset' }, el('div', { class: 'thumb checker' }, el('img', { src: charUrl(c, k.file) })),
      el('div', { class: 'row small' }, badge(k.status), badge(k.direction, ''), k.is_test_fixture ? badge('TEST FIXTURE', 'fixture') : null),
      k.status === 'candidate' ? el('div', { class: 'row' },
        el('button', { class: 'small', onclick: () => guard(async () => { await api(`/api/projects/${S.project}/characters/${c.id}/candidates/${k.id}/review`, { body: { decision: 'approved' } }); toast('Approved & locked'); renderCharacter(root); }) }, 'Approve'),
        el('button', { class: 'small danger', onclick: () => guard(async () => { await api(`/api/projects/${S.project}/characters/${c.id}/candidates/${k.id}/review`, { body: { decision: 'rejected' } }); renderCharacter(root); }) }, 'Reject'),
        c.masters[k.direction]?.locked ? el('button', { class: 'small', onclick: () => guard(async () => { const r = needReason();
          await api(`/api/projects/${S.project}/characters/${c.id}/masters/${k.direction}/replace`, { body: { candidate_id: k.id, reason: r } }); renderCharacter(root); }) }, 'Replace master') : null) : null));
  }
  const upDir = select(['primary', ...c.directions], 'primary'), upKind = select(['candidate', 'concept'], 'candidate');
  const up = el('input', { type: 'file', accept: 'image/*' });
  up.onchange = () => guard(async () => { const data = await readFile(up.files[0]);
    await api(`/api/projects/${S.project}/characters/${c.id}/images`, { body: { filename: up.files[0].name, data, kind: upKind.value, direction: upDir.value } }); toast('Added'); renderCharacter(root); });
  const gProv = providerSelect(['comfyui', 'mock', 'codex'], S.providers.find(p => p.id === 'comfyui' && p.status.available) ? 'comfyui' : 'mock');
  const gWf = select([['', '— workflow —'], ...(S.workflows = S.workflows.length ? S.workflows : await api('/api/workflows')).map(w => [w.id, `${w.id} [${w.category}, ${w.verification}]`])], 'sd-character-reference');
  const gDir = select(c.directions, c.directions[0]);
  const gParams = el('textarea', { class: 'mono' }, '{}');
  const preview = el('pre', { class: 'mono small', style: 'white-space:pre-wrap' });
  const report = el('div', {});
  root.append(el('div', { class: 'grid cols3' },
    el('div', { class: 'card' }, el('h3', {}, c.name), el('div', { class: 'row small' }, badge(c.direction_mode, ''), badge(c.art_style, ''), el('span', { class: 'muted' }, c.id)),
      el('div', { class: 'form' }, ...field('Description', desc), ...field('Visual style', style), ...field('Camera', cam), ...field('Clothing (1/line)', clothing),
        ...field('Accessories', acc), ...field('Weapon (JSON)', weapon), ...field('Proportions (JSON)', props), ...field('Palette', palette),
        ...field('Must keep (1/line)', cons), ...field('Negative (1/line)', neg), ...field('Optional mirroring', mirror)),
      el('p', { class: 'small muted' }, 'Mirroring is off by default: asymmetric weapons/costumes need independently generated directions.'), save),
    el('div', { class: 'card' }, el('h3', {}, 'Directional masters'), c.missing_directions.length ? el('div', { class: 'small', style: 'color:var(--warn)' }, 'Missing: ' + c.missing_directions.join(', ')) : el('div', { class: 'small', style: 'color:var(--ok)' }, 'All directions have masters'),
      dirs, reason, el('h4', {}, 'Candidates (approve → becomes locked master)'), el('div', { class: 'row' }, upKind, upDir, up), cands,
      el('h4', {}, 'Concept art'), el('div', { class: 'assets' }, ...c.concept_art.map(f => el('div', { class: 'asset' }, el('div', { class: 'thumb checker' }, el('img', { src: charUrl(c, f) }))))),
      el('h4', {}, 'Animations'), el('div', {}, ...c.assets.map(x => el('div', { class: 'row small' }, el('a', { href: '#', onclick: (e) => { e.preventDefault(); emit('open-asset', x.id); } }, x.name), badge(x.status), `${x.anim}/${x.direction}`)))),
    el('div', { class: 'card' }, el('h3', {}, 'Generate master candidate'),
      el('div', { class: 'form' }, ...field('Provider', gProv), ...field('Workflow', gWf), ...field('Direction', gDir), ...field('Params JSON', gParams)),
      el('div', { class: 'row' }, el('button', { onclick: () => guard(async () => { preview.textContent = JSON.stringify(await api('/api/prompt-preview', { body: { project_id: S.project, character_id: c.id, kind: 'master_candidate', direction: gDir.value } }), null, 1); }) }, 'Preview prompt'),
        el('button', { class: 'primary', onclick: () => guard(async () => {
          const job = await api(`/api/projects/${S.project}/generate`, { body: { provider_id: gProv.value, kind: 'master_candidate', character_id: c.id, direction: gDir.value, workflow_id: gWf.value || null, params: JSON.parse(gParams.value || '{}') } });
          toast('Generation queued'); await waitJob(job, () => renderCharacter(root)); }) }, 'Generate')),
      preview,
      el('h4', {}, 'Direction matrix check'),
      el('button', { onclick: () => guard(async () => { const r = await api(`/api/projects/${S.project}/characters/${c.id}/report`, { body: { animations: ['idle', 'walk', 'attack'] } });
        report.innerHTML = ''; report.append(...[...r.masters, ...r.animations].map(i => el('div', { class: 'issue ' + i.severity }, i.message))); if (!r.masters.length && !r.animations.length) report.textContent = 'Complete'; }) }, 'Check idle/walk/attack × directions'), report,
      el('h4', {}, 'History'), el('div', { class: 'issues small mono' }, ...[...c.history].reverse().slice(0, 40).map(h => el('div', {}, new Date(h.at * 1000).toLocaleString() + ' ' + h.event + (h.direction ? ' ' + h.direction : '') + (h.reason ? ' — ' + h.reason : '')))))));
}

function newCharacterForm(root) {
  const name = el('input', { value: 'Adventurer' }), mode = select([['four', '4 directions'], ['eight', '8 directions'], ['side2', 'side-scroller (L/R)']], 'four');
  const style = select(['pixel', 'hd'], S.data.project.default_style), desc = el('textarea', {}, 'Chibi fantasy adventurer with a red hood, blonde hair, red cape, brown adventurer outfit, brown boots and a sword.');
  return el('div', { class: 'card' }, el('h3', {}, 'New character'), el('div', { class: 'form' }, ...field('Name', name), ...field('Directions', mode), ...field('Art style', style), ...field('Description', desc)),
    el('button', { class: 'primary', onclick: () => guard(async () => {
      const c = await api(`/api/projects/${S.project}/characters`, { body: { name: name.value, direction_mode: mode.value, art_style: style.value, description: desc.value } });
      S.character = c.id; await refreshProject(); renderCharacter(root); }) }, 'Create'));
}

// ------------------------------------------------------------------ Procedural Studio
export async function renderProcedural(root) {
  if (needProject(root)) return;
  root.innerHTML = '';
  const atl = S.providers.find(p => p.id === 'atelier');
  const builders = S.templates.builders;
  const bsel = select(Object.keys(builders), Object.keys(builders)[0]);
  const form = el('div', { class: 'form' });
  const inputs = {};
  const drawForm = () => {
    form.innerHTML = ''; for (const k in inputs) delete inputs[k];
    const b = builders[bsel.value];
    form.append(el('label', {}, 'About'), el('div', { class: 'small muted' }, b.description));
    for (const [k, spec] of Object.entries(b.params)) {
      inputs[k] = spec.enum ? select(spec.enum, spec.default) : el('input', { value: spec.default, type: spec.type === 'int' ? 'number' : 'text' });
      form.append(el('label', {}, k), inputs[k]);
    }
  };
  bsel.onchange = drawForm; drawForm();
  const name = el('input', { placeholder: 'asset name (optional)' });
  const procAssets = assetsOfProject(a => a.procedural);
  const list = el('div', { class: 'assets' }, ...procAssets.map(a => el('div', { class: 'asset' + (S.procAsset === a.id ? ' sel' : ''), onclick: () => { S.procAsset = a.id; renderProcedural(root); } },
    el('div', { class: 'thumb checker' }, el('img', { src: fileUrl(a, a.animation.frames[0].file) })), el('div', { class: 'name' }, a.name), el('div', { class: 'small muted' }, `${a.procedural.builder} · ${a.animation.frames.length}f`))));
  const inspector = el('div', { class: 'card' }, el('h3', {}, 'Document inspector'), el('p', { class: 'muted' }, 'Select a procedural asset.'));
  root.append(el('div', { class: 'grid cols3' },
    el('div', { class: 'card' }, el('h3', {}, 'Atelier recipe'), !atl?.status.available ? el('div', { class: 'warnbox' }, 'Atelier unavailable: ' + atl?.status.reason) : el('div', { class: 'small muted' }, atl.status.details.version),
      el('div', { class: 'form' }, el('label', {}, 'Builder'), bsel), form, el('div', { class: 'form' }, el('label', {}, 'Name'), name),
      el('button', { class: 'primary', disabled: !atl?.status.available, onclick: () => guard(async () => {
        const params = {}; for (const [k, i] of Object.entries(inputs)) params[k] = i.type === 'number' ? +i.value : i.value;
        const job = await api(`/api/projects/${S.project}/procedural`, { body: { builder: bsel.value, params, name: name.value || null } });
        await waitJob(job, async (j) => { toast('Drawn by Atelier'); S.procAsset = j.result.asset_id; await refreshProject(); renderProcedural(root); }); }) }, 'Run with Atelier'),
      el('h4', {}, 'Replay an Atelier .recipe'), (() => { const f = el('input', { type: 'file', accept: '.recipe' }); f.onchange = () => guard(async () => {
        const job = await api(`/api/projects/${S.project}/import`, { body: { filename: f.files[0].name, data: await readFile(f.files[0]), name: f.files[0].name } });
        await waitJob(job, async (j) => { S.procAsset = j.result.asset_id; await refreshProject(); renderProcedural(root); }); }); return f; })()),
    el('div', { class: 'card' }, el('h3', {}, 'Procedural assets'), list), inspector));
  if (S.procAsset) {
    const a = await api(`/api/projects/${S.project}/assets/${S.procAsset}`).catch(() => null);
    if (!a) return;
    const info = await api(`/api/projects/${S.project}/assets/${a.id}/atelier`).catch(e => ({ error: e.message }));
    inspector.innerHTML = '';
    inspector.append(el('h3', {}, a.name), el('div', { class: 'row' }, el('button', { onclick: () => emit('open-asset', a.id) }, 'Open in Animation Studio'),
      el('button', { onclick: () => guard(async () => { const job = await api(`/api/projects/${S.project}/assets/${a.id}/replay`, { body: {} });
        await waitJob(job, async (j) => { toast('Recipe replayed into a new asset'); await refreshProject(); S.procAsset = j.result.asset_id; renderProcedural(root); }); }) }, 'Replay recipe'),
      el('a', { href: fileUrl(a, a.procedural.recipe), target: '_blank' }, 'doc.recipe')));
    if (info.error) { inspector.append(el('div', { class: 'warnbox' }, info.error)); return; }
    const doc = info.doc;
    inspector.append(el('div', { class: 'small muted' }, `doc ${info.doc_id} · ${doc.w}×${doc.h} · revision ${doc.revision} · ${info.recipe_lines} recipe calls`),
      el('h4', {}, 'Palette'), el('div', {}, ...(doc.palette || []).map(c => el('span', { class: 'swatch', title: JSON.stringify(c), style: `background:${Array.isArray(c) ? `rgba(${c[0]},${c[1]},${c[2]},${(c[3] ?? 255) / 255})` : c}` }))),
      el('h4', {}, 'Layers'), el('div', {}, ...doc.layers.map((l, li) => el('div', { class: 'small' }, `L${li} ${l.name} · ${l.blend} · opacity ${l.opacity}${l.visible ? '' : ' · hidden'}`))),
      el('h4', {}, `Frames (${doc.frames.length})`), el('div', { class: 'small mono' }, doc.frames.map(f => f.duration_ms + 'ms').join(' · ')),
      el('h4', {}, 'Cels (editable source)'), el('div', { class: 'cels' }, ...info.cels.slice(0, 120).map(n => el('figure', { class: '' }, el('img', { class: 'checker', src: `/files/${S.project}/atelier/${info.doc_id}/cels/${n}` }), el('figcaption', {}, n.replace('.png', ''))))),
      el('h4', {}, 'Tool calls'), el('div', { class: 'small mono issues' }, Object.entries(info.recipe_head.reduce((m, n) => (m[n] = (m[n] || 0) + 1, m), {})).map(([k, v]) => `${k} ×${v}`).join('  ')));
  }
}

// ------------------------------------------------------------------ Import & Processing
export async function renderImport(root) {
  if (needProject(root)) return;
  root.innerHTML = '';
  let files = [];
  const drop = el('div', { class: 'drop' }, 'Drop PNG / sprite sheet / PNG sequence / GIF / APNG / MP4 / WebM here, or ', el('input', { type: 'file', multiple: true }));
  const before = el('div', { class: 'checker', style: 'min-height:160px;text-align:center' });
  const setFiles = (fl) => { files = [...fl]; before.innerHTML = ''; if (files[0] && files[0].type.startsWith('image')) before.append(el('img', { src: URL.createObjectURL(files[0]), style: 'max-width:100%;max-height:300px;image-rendering:pixelated' })); else if (files[0]) before.append(el('div', { class: 'muted' }, files[0].name)); drop.firstChild.textContent = `${files.length} file(s): ${files.map(f => f.name).join(', ')} `; };
  drop.querySelector('input').onchange = (e) => setFiles(e.target.files);
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add('hover'); }; drop.ondragleave = () => drop.classList.remove('hover');
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove('hover'); setFiles(e.dataTransfer.files); };
  const mode = select(['pixel', 'hd'], S.data.project.default_style);
  const slicing = select([['single', 'single image / sequence'], ['grid', 'sprite sheet: grid'], ['auto', 'sprite sheet: auto-detect']], 'single');
  const cols = el('input', { type: 'number', value: 4 }), rows = el('input', { type: 'number', value: 2 }), count = el('input', { type: 'number', placeholder: 'all' });
  const bgm = select([['none', 'keep'], ['auto', 'auto (solid/checker)'], ['solid', 'colour key']], 'none'), bgc = el('input', { type: 'color', value: '#00ff00' }), tol = el('input', { type: 'number', value: 28 });
  const anchor = select(['source', 'ground', 'support_foot', 'torso'], 'source'), scale = el('input', { type: 'number', step: 0.05, value: 1 }), th = el('input', { type: 'number', placeholder: 'px' });
  const depix = select([['', 'no'], ['auto', 'auto-detect block'], ['2', '2'], ['4', '4'], ['8', '8']], '');
  const fps = el('input', { type: 'number', placeholder: 'keep', step: 1 }), vfps = el('input', { type: 'number', value: 12 }), vmax = el('input', { type: 'number', value: 48 });
  const anim = el('input', { value: 'imported' }), dir = select(DIRS, 'none'), tpl = select(['', ...Object.keys(S.templates.animations)], '');
  const ch = select([['', '—'], ...S.data.characters.map(c => [c.id, c.name])], ''), palette = el('input', { type: 'number', placeholder: 'colours' });
  const result = el('div', {});
  const go = el('button', { class: 'primary', onclick: () => guard(async () => {
    if (!files.length) throw new Error('Choose a file first');
    const payload = { files: await Promise.all(files.map(async f => ({ name: f.name, data: await readFile(f) }))), mode: mode.value, anim_name: anim.value, direction: dir.value,
      template: tpl.value || null, character_id: ch.value || null, depixelate_block: depix.value || null, fps: fps.value ? +fps.value : null,
      slicing: slicing.value === 'grid' ? { method: 'grid', cols: +cols.value, rows: +rows.value, count: count.value ? +count.value : null } : { method: slicing.value },
      background: bgm.value === 'none' ? null : { method: bgm.value === 'solid' ? 'solid' : 'auto', color: bgm.value === 'solid' ? [1, 3, 5].map(i => parseInt(bgc.value.slice(i, i + 2), 16)) : null, tolerance: +tol.value },
      normalize: { anchor: anchor.value, scale: +scale.value || 1, target_height: th.value ? +th.value : null, palette_size: palette.value ? +palette.value : null },
      video: { fps: +vfps.value, max_frames: +vmax.value } };
    const job = await api(`/api/projects/${S.project}/import`, { body: payload });
    await waitJob(job, async (j) => {
      await refreshProject();
      const a = await api(`/api/projects/${S.project}/assets/${j.result.asset_id}`);
      result.innerHTML = '';
      const f0 = a.animation.frames[0];
      result.append(el('h4', {}, 'Before / after'), el('div', { class: 'compare' },
        el('div', {}, el('div', { class: 'small muted' }, 'source frame 0'), el('div', { class: 'checker' }, el('img', { src: fileUrl(a, f0.source_file) }))),
        el('div', {}, el('div', { class: 'small muted' }, 'processed frame 0'), el('div', { class: 'checker' }, el('img', { src: fileUrl(a, f0.file) })))),
        el('div', { class: 'row' }, badge(a.qa.deterministic.status), `${a.animation.frames.length} frames · canvas ${a.animation.canvas}`, el('button', { onclick: () => emit('open-asset', a.id) }, 'Open in Animation Studio')));
    });
  }) }, 'Import & process');
  const ext = S.providers.find(p => p.id === 'external');
  root.append(el('div', { class: 'grid cols2' },
    el('div', { class: 'card' }, el('h3', {}, 'Options'),
      el('div', { class: 'form' }, ...field('Mode', mode), ...field('Slicing', slicing), ...field('Grid cols/rows/count', el('div', { class: 'row' }, cols, rows, count)),
        ...field('Background', el('div', { class: 'row' }, bgm, bgc, 'tol', tol)), ...field('Anchor', anchor), ...field('Group scale', scale), ...field('or target height', th),
        ...field('Pixel palette', palette), ...field('De-pixelate', depix), ...field('Frame rate', fps), ...field('Video fps / max', el('div', { class: 'row' }, vfps, vmax)),
        ...field('Animation', anim), ...field('Direction', dir), ...field('Template', tpl), ...field('Character', ch)),
      el('p', { class: 'small muted' }, 'One scale for the whole group; anchoring never resizes frames individually; the canvas expands instead of cropping. Video import ',
        ext?.status.details.video_import ? 'is available (ffmpeg found).' : 'needs ffmpeg (not found).'), go),
    el('div', { class: 'card' }, drop, el('h4', {}, 'Selected'), before, result)));
}

// ------------------------------------------------------------------ Generation
export async function renderGenerate(root) {
  if (needProject(root)) return;
  root.innerHTML = '';
  S.workflows = await api('/api/workflows');
  const provCards = el('div', { class: 'grid', style: 'grid-template-columns:repeat(auto-fill,minmax(250px,1fr))' }, ...S.providers.map(p => el('div', { class: 'card' },
    el('div', { class: 'row' }, el('b', {}, p.name), badge(p.status.available ? 'available' : 'unavailable', p.status.available ? 'ok' : 'err'), p.status.details?.is_mock ? badge('MOCK', 'fixture') : null),
    el('div', { class: 'small muted' }, p.status.available ? JSON.stringify(p.status.details).slice(0, 220) : p.status.reason))));
  const wfTable = el('table', {}, el('tr', {}, ...['id', 'category', 'status', 'required nodes', 'models', ''].map(h => el('th', {}, h))),
    ...S.workflows.map(w => el('tr', {}, el('td', {}, w.id, el('div', { class: 'muted' }, w.source)), el('td', {}, w.category), el('td', {}, badge(w.verification, w.verification === 'production-verified' ? 'ok' : 'warn')),
      el('td', { class: 'mono' }, (w.required_nodes || []).join(', ')), el('td', { class: 'mono' }, (w.required_models || []).map(m => m.param || m.input).join(', ')),
      el('td', {}, el('button', { class: 'small', onclick: () => guard(async () => { const r = await api(`/api/workflows/${w.id}/check`, { body: {} });
        toast(r.ok ? 'Runnable on the connected server' : `Not runnable: ${[...r.missing_nodes, ...r.missing_models.map(m => m.value)].join(', ') || 'invalid values'}`, !r.ok); }) }, 'Check'),
        w.source === 'user' ? el('button', { class: 'small danger', onclick: () => guard(async () => { await api('/api/workflows/' + w.id, { method: 'DELETE' }); renderGenerate(root); }) }, '×') : null))));
  const wfFile = el('input', { type: 'file', accept: '.json' }), wfName = el('input', { placeholder: 'name' }), wfCat = select(['text_to_image', 'image_to_image', 'character_reference', 'pose_keyframe', 'inpainting', 'image_to_video', 'background_removal'], 'image_to_image');
  const prov = providerSelect(['comfyui', 'mock', 'codex'], S.providers.find(p => p.id === 'comfyui')?.status.available ? 'comfyui' : 'mock');
  const wf = select([['', '— workflow —'], ...S.workflows.map(w => [w.id, `${w.id} [${w.verification}]`])], 'sd-image-to-image');
  const ch = select([['', '—'], ...S.data.characters.map(c => [c.id, c.name])], S.character || '');
  const tpl = select(Object.keys(S.templates.animations), 'walk'), dir = select(DIRS, 'east'), mode = select(['', 'pixel', 'hd'], '');
  const layout = select([['auto', 'auto-detect sprites'], ['grid', 'grid (cols×rows)']], 'auto'), cols = el('input', { type: 'number', value: 8 }), rows = el('input', { type: 'number', value: 1 });
  const params = el('textarea', { class: 'mono' }, '{"steps": 24}'), note = el('input', { placeholder: 'revision note' }), retries = el('input', { type: 'number', value: 1, min: 1, max: 5 });
  const budget = el('input', { type: 'number', value: 2, min: 0 }), dirsBatch = el('input', { value: 'south east north west' });
  const preview = el('pre', { class: 'mono small', style: 'white-space:pre-wrap' });
  const body = () => ({ provider_id: prov.value, workflow_id: wf.value || null, character_id: ch.value || null, template: tpl.value, direction: dir.value, mode: mode.value || null,
    kind: 'keyframes', params: JSON.parse(params.value || '{}'), note: note.value, max_attempts: +retries.value,
    layout: layout.value === 'grid' ? { method: 'grid', cols: +cols.value, rows: +rows.value } : { method: 'auto' } });
  root.append(el('div', { class: 'card' }, el('h3', {}, 'Providers (checked at runtime — unavailable providers are never substituted)'), provCards),
    el('div', { class: 'grid cols2', style: 'margin-top:12px' },
      el('div', { class: 'card' }, el('h3', {}, 'Generate animation keyframes'),
        el('div', { class: 'form' }, ...field('Provider', prov), ...field('Workflow', wf), ...field('Character', ch), ...field('Action template', tpl), ...field('Direction', dir), ...field('Mode', mode),
          ...field('Sheet layout', el('div', { class: 'row' }, layout, cols, rows)), ...field('Params JSON', params), ...field('Note', note), ...field('Retries', retries)),
        el('div', { class: 'row' }, el('button', { onclick: () => guard(async () => { if (!ch.value) throw new Error('Choose a character'); preview.textContent = JSON.stringify(await api('/api/prompt-preview', { body: { project_id: S.project, character_id: ch.value, template: tpl.value, direction: dir.value } }), null, 1); }) }, 'Preview prompt'),
          el('button', { class: 'primary', onclick: () => guard(async () => { const p = S.providers.find(x => x.id === prov.value); if (!p.status.available) throw new Error(`${p.id} unavailable: ${p.status.reason}`);
            const job = await api(`/api/projects/${S.project}/generate`, { body: body() }); toast('Queued'); await waitJob(job, (j) => { toast('Generated'); refreshProject(); }); }) }, 'Generate (1 call)')),
        el('h4', {}, 'Batch over directions (explicit budget required)'),
        el('div', { class: 'form' }, ...field('Directions', dirsBatch), ...field('Budget (max calls)', budget)),
        el('button', { onclick: () => guard(async () => { const b = body(); const items = dirsBatch.value.split(/\s+/).filter(Boolean).map(d => ({ ...b, direction: d }));
          items.forEach(i => { delete i.max_attempts; });
          const job = await api(`/api/projects/${S.project}/batch`, { body: { items, budget: +budget.value } }); toast(`Batch queued (budget ${budget.value})`); await waitJob(job, () => refreshProject()); }) }, 'Run batch'),
        preview),
      el('div', { class: 'card' }, el('h3', {}, 'ComfyUI workflow templates'), wfTable,
        el('h4', {}, 'Import workflow (API format JSON or studio template)'), el('div', { class: 'row' }, wfFile, wfName, wfCat,
          el('button', { onclick: () => guard(async () => { if (!wfFile.files[0]) throw new Error('Choose a JSON file');
            const t = await api('/api/workflows/import', { body: { workflow: await wfFile.files[0].text(), name: wfName.value || wfFile.files[0].name.replace('.json', ''), category: wfCat.value } });
            toast(`Imported ${t.id} (unverified)`); renderGenerate(root); }) }, 'Import')),
        el('p', { class: 'small muted' }, 'Mappings for prompt, negative prompt, seed, size, reference images and model files are derived automatically from the graph and validated against /object_info before every run. No checkpoint, LoRA or custom node is hardcoded.'))));
}

// ------------------------------------------------------------------ Export Studio
export async function renderExport(root) {
  if (needProject(root)) return;
  root.innerHTML = '';
  const anims = assetsOfProject(a => a.animation);
  const checks = {};
  const list = el('div', {}, ...anims.map(a => { checks[a.id] = el('input', { type: 'checkbox' }); return el('div', { class: 'row small' }, checks[a.id], a.name, badge(a.status), fixtureBadge(a), el('span', { class: 'muted' }, `${a.animation.name}/${a.animation.direction}${a.animation.layers?.length ? ' +layers' : ''}`)); }));
  const fmts = ['frames', 'sheet', 'atlas', 'gif', 'apng', 'json', 'cocos', 'phaser', 'godot', 'zip'];
  const fchecks = Object.fromEntries(fmts.map(f => [f, el('input', { type: 'checkbox', checked: true })]));
  const name = el('input', { value: 'game_assets' }), scale = el('input', { type: 'number', value: 2 }), pad = el('input', { type: 'number', value: 2 }), trim = el('input', { type: 'checkbox', checked: true });
  const ch = select([['', '— (direction mirroring source) —'], ...S.data.characters.map(c => [c.id, c.name])], '');
  const exports = await api(`/api/projects/${S.project}/exports`);
  root.append(el('div', { class: 'grid cols2' },
    el('div', { class: 'card' }, el('h3', {}, 'Export'), el('h4', {}, 'Animations'), el('div', { class: 'row' }, el('button', { class: 'small', onclick: () => Object.values(checks).forEach(c => c.checked = true) }, 'all'), el('button', { class: 'small', onclick: () => Object.values(checks).forEach(c => c.checked = false) }, 'none')), list,
      el('h4', {}, 'Formats'), el('div', { class: 'row' }, ...fmts.map(f => el('label', {}, fchecks[f], f))),
      el('div', { class: 'form' }, ...field('Name', name), ...field('Preview scale', scale), ...field('Atlas padding', pad), ...field('Trim frames', trim), ...field('Character', ch)),
      el('p', { class: 'small muted' }, 'Cocos Creator 3.x: TexturePacker plist (format 2) + PNG → SpriteAtlas, plus .anim.json timing/pivot/events for examples/cocos-creator/DirectionalSpriteAnimator.ts. Phaser 3 / PixiJS: TexturePacker JSON-hash atlas. Godot / Unity: generic JSON.'),
      el('button', { class: 'primary', onclick: () => guard(async () => {
        const ids = Object.entries(checks).filter(([, c]) => c.checked).map(([id]) => id); if (!ids.length) throw new Error('Select at least one animation');
        const job = await api(`/api/projects/${S.project}/export`, { body: { asset_ids: ids, name: name.value, formats: fmts.filter(f => fchecks[f].checked), preview_scale: +scale.value, padding: +pad.value, trim: trim.checked, character_id: ch.value || null } });
        await waitJob(job, () => { toast('Export finished'); renderExport(root); }); }) }, 'Export')),
    el('div', { class: 'card' }, el('h3', {}, 'Exports'), ...exports.map(x => el('div', { class: 'card', style: 'margin-bottom:8px' },
      el('div', { class: 'row' }, el('b', {}, x.name), badge(x.qa), x.contains_test_fixtures ? badge('CONTAINS TEST FIXTURES', 'fixture') : null, el('span', { class: 'muted small' }, new Date(x.created_at * 1000).toLocaleString()),
        x.zip ? el('a', { href: exportUrl(S.project, x.export_id, x.zip) }, 'download zip') : null),
      el('div', { class: 'row' }, ...x.files.filter(f => f.startsWith('previews/') && f.endsWith('.gif')).slice(0, 12).map(f => el('div', { class: 'checker', style: 'padding:2px' }, el('img', { src: exportUrl(S.project, x.export_id, f), title: f, style: 'max-height:120px;image-rendering:pixelated' })))),
      el('details', {}, el('summary', { class: 'small' }, `${x.files.length} files`), el('div', { class: 'small mono' }, ...x.files.map(f => el('div', {}, el('a', { href: exportUrl(S.project, x.export_id, f), target: '_blank' }, f))))))))));
}
