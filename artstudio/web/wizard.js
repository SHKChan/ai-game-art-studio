// Guided flow: animate a character (Motion Studio).
// 1 Character (reference image) → 2 Actions → 3 Prompts (Codex or template, editable) → 4 Generate (Codex / ComfyUI) → 5 Review & export.
import { t } from './i18n.js';
import { S, api, el, toast, guard, emit, fileUrl, charUrl, exportUrl, badge, fixtureBadge, readFile, select, field, waitJob, refreshProject } from './core.js';

const STEPS = ['Character', 'Actions', 'Prompts', 'Generate', 'Review & export'];
export const W = { step: 0, cid: null, char: null, plan: null, provider: null, workflow: '', checkpoint: '', denoise: 0.62, presets: null };

const proj = () => `/api/projects/${S.project}`;
const provider = (id) => S.providers.find(p => p.id === id);
const avail = (id) => !!provider(id)?.status.available;

async function loadChar() {
  if (!W.cid) { W.char = null; W.plan = null; return; }
  W.char = await api(`${proj()}/characters/${W.cid}`);
  W.plan = await api(`${proj()}/characters/${W.cid}/plan`);
}
async function savePlan() { W.plan = await api(`${proj()}/characters/${W.cid}/plan`, { body: W.plan }); }
function master(c) { const m = c?.masters || {}; return m.right || m.east || m.south || m.primary || Object.values(m)[0]; }

export async function renderWizard(root, opts = {}) {
  if (!S.project) { root.innerHTML = ''; root.append(el('div', { class: 'card' }, el('p', {}, 'Create or select a project first.'))); return; }
  if (opts.cid !== undefined) { W.cid = opts.cid; W.char = null; W.step = opts.step ?? (opts.cid ? 1 : 0); }
  if (!W.presets) W.presets = await api('/api/action-presets');
  if (W.cid && !S.data.characters.some(c => c.id === W.cid)) { W.cid = null; W.char = null; W.step = 0; }
  if (W.cid && (!W.char || W.char.id !== W.cid)) await loadChar();
  if (!W.cid) W.step = 0;
  root.innerHTML = '';
  const can = (i) => i === 0 || (W.char && master(W.char) && (i < 2 || W.plan?.actions.length));
  const stepper = el('div', { class: 'stepper' }, ...STEPS.map((s, i) => el('button', {
    class: 'step' + (i === W.step ? ' cur' : '') + (i < W.step ? ' done' : ''), disabled: !can(i),
    onclick: () => { W.step = i; renderWizard(root); } }, el('span', { class: 'num' }, String(i + 1)), s)));
  const head = el('div', { class: 'row' }, el('h2', { class: 'wtitle' }, 'Motion Studio'), el('span', { class: 'muted' }, 'Animate a character'),
    W.char ? el('span', { class: 'muted', 'data-no-i18n': '' }, '· ' + W.char.name) : null);
  const body = el('div', { class: 'wbody' });
  root.append(head, stepper, body);
  const go = (i) => { W.step = i; renderWizard(root); window.scrollTo(0, 0); };
  await guard(() => [stepCharacter, stepActions, stepPrompts, stepGenerate, stepReview][W.step](body, go, root));
}

function nav(go, back, next, nextLabel = 'Next →', nextDisabled = false) {
  return el('div', { class: 'row wnav' }, back !== null ? el('button', { onclick: () => go(back) }, '← Back') : null, el('span', { class: 'spacer' }),
    next !== null ? el('button', { class: 'primary', disabled: nextDisabled, onclick: () => (typeof next === 'function' ? guard(next) : go(next)) }, nextLabel) : null);
}

// ------------------------------------------------------------------ 1 character + reference
function dropZone(onFile, label) {
  const input = el('input', { type: 'file', accept: 'image/png,image/webp,image/jpeg' });
  const z = el('div', { class: 'drop' }, el('div', {}, label), input);
  input.onchange = (e) => e.target.files[0] && onFile(e.target.files[0]);
  z.ondragover = (e) => { e.preventDefault(); z.classList.add('hover'); }; z.ondragleave = () => z.classList.remove('hover');
  z.ondrop = (e) => { e.preventDefault(); z.classList.remove('hover'); e.dataTransfer.files[0] && onFile(e.dataTransfer.files[0]); };
  return z;
}

async function stepCharacter(body, go, root) {
  const chars = S.data.characters;
  const pick = el('div', { class: 'cards' }, ...chars.map(c => {
    const m = master(c);
    return el('div', { class: 'pick' + (c.id === W.cid ? ' sel' : ''), onclick: () => guard(async () => { W.cid = c.id; await loadChar(); renderWizard(root); }) },
      el('div', { class: 'thumb checker' }, m ? el('img', { src: charUrl(c, m.file), alt: c.name }) : el('span', { class: 'muted small' }, 'no reference')),
      el('div', { class: 'name', 'data-no-i18n': '' }, c.name), el('div', { class: 'small muted' }, c.art_style, ' · ', c.direction_mode === 'side2' ? 'side' : 'top_down'));
  }), el('div', { class: 'pick new' + (!W.cid ? ' sel' : ''), onclick: () => { W.cid = null; W.char = null; renderWizard(root); } }, el('div', { class: 'thumb plus' }, '+'), el('div', { class: 'name' }, 'New character')));

  let file = null;
  const preview = el('div', { class: 'refbox checker' });
  const showFile = (f) => { file = f; preview.innerHTML = ''; preview.append(el('img', { src: URL.createObjectURL(f) })); };
  if (!W.char) {
    const name = el('input', { placeholder: 'e.g. Fire Knight', 'aria-label': 'Character name' });
    const style = select([['pixel', 'Pixel art'], ['hd', 'HD illustration']], S.data.project.default_style || 'pixel');
    const view = select([['side', 'Side view (platformer / side-scroller)'], ['top_down', 'Top-down / RPG (4 directions)']], 'side');
    const notes = el('input', { placeholder: 'optional: anything the image does not show (e.g. carries a shield on the back)' });
    body.append(el('div', { class: 'card' }, el('h3', {}, 'Your characters'), pick),
      el('div', { class: 'grid cols2' },
        el('div', { class: 'card' }, el('h3', {}, 'New character'),
          el('div', { class: 'form' }, ...field('Name', name), ...field('Art style', style), ...field('View', view), ...field('Notes', notes)),
          el('p', { class: 'small muted' }, 'The reference image is the single source of truth: every action is generated to match it. Use a clean full-body image, ideally on a transparent or plain background.')),
        el('div', { class: 'card' }, el('h3', {}, 'Reference image'), dropZone(showFile, 'Drop the character image here, or choose a file'), preview)),
      nav(go, null, async () => {
        if (!name.value.trim()) throw new Error('Enter a character name');
        if (!file) throw new Error('Add a reference image');
        const c = await api(`${proj()}/characters/from-reference`, { body: { name: name.value.trim(), art_style: style.value, view: view.value, description: notes.value, filename: file.name, data: await readFile(file) } });
        W.cid = c.id; await refreshProject(); await loadChar(); toast('Character created'); go(1);
      }, 'Create & continue →'));
    return;
  }
  const m = master(W.char);
  preview.append(m ? el('img', { src: charUrl(W.char, m.file) }) : el('span', { class: 'muted' }, 'no reference'));
  body.append(el('div', { class: 'card' }, el('h3', {}, 'Your characters'), pick),
    el('div', { class: 'grid cols2' },
      el('div', { class: 'card' }, el('h3', {}, 'Reference image'), preview),
      el('div', { class: 'card' }, el('h3', {}, 'Replace reference'), dropZone(f => guard(async () => {
        await api(`${proj()}/characters/${W.cid}/reference`, { body: { filename: f.name, data: await readFile(f) } });
        await loadChar(); await refreshProject(); toast('Reference updated'); renderWizard(root);
      }), 'Drop a new reference image here'), el('p', { class: 'small muted' }, 'Replacing keeps the old image in the character history.'))),
    nav(go, null, 1, 'Next →', !m));
}

// ------------------------------------------------------------------ 2 actions
function actionRow(a, i, dirs, changed, remove) {
  const nm = el('input', { value: a.name, 'aria-label': 'Action name', 'data-no-i18n': '' });
  const fr = el('input', { type: 'number', min: 1, max: 16, value: a.frames, 'aria-label': 'Frames' });
  const lp = el('input', { type: 'checkbox', checked: a.loop });
  const dr = select(dirs, a.direction, { 'aria-label': 'Direction' });
  const ds = el('input', { value: a.description, class: 'grow', placeholder: 'what happens, in one line (e.g. swings the sword overhead and slams it down)', 'data-no-i18n': '' });
  const upd = () => {
    if (!a.asset_id && nm.value !== a.name) { const id = nm.value.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, ''); if (id) a.id = id; }
    a.name = nm.value; a.frames = Math.max(1, Math.min(16, +fr.value || 1)); a.loop = lp.checked; a.direction = dr.value; a.description = ds.value; changed(); };
  [nm, fr, dr, ds].forEach(x => x.onchange = upd); lp.onchange = upd;
  return el('div', { class: 'arow' }, el('span', { class: 'muted small tag' }, a.preset ? a.preset : 'custom'), nm, el('label', { class: 'small' }, 'Frames', fr),
    el('label', { class: 'small' }, lp, 'Loop'), dr, ds, a.asset_id ? badge('generated', 'ok') : null,
    el('button', { class: 'small danger', title: 'Remove', onclick: remove }, '✕'));
}

async function stepActions(body, go, root) {
  const dirs = W.char.directions;
  let timer = null;
  const changed = () => { clearTimeout(timer); timer = setTimeout(() => guard(savePlan), 400); };
  const list = el('div', { class: 'alist' });
  const draw = () => {
    list.innerHTML = '';
    W.plan.actions.forEach((a, i) => list.append(actionRow(a, i, dirs, changed, () => guard(async () => { W.plan.actions.splice(i, 1); await savePlan(); draw(); }))));
    if (!W.plan.actions.length) list.append(el('p', { class: 'muted' }, 'No actions yet — click a preset above or add a custom action.'));
  };
  const add = (preset) => guard(async () => {
    const p = preset ? W.presets[preset] : null;
    W.plan.actions.push(preset ? { preset, frames: p.frames, loop: p.loop, direction: dirs[0], description: p.description }
      : { name: 'custom action', frames: 6, loop: false, direction: dirs[0], description: '' });
    await savePlan(); draw();
  });
  const chips = el('div', { class: 'chips' }, ...Object.keys(W.presets).map(k => el('button', { class: 'chip', onclick: () => add(k) }, '+ ', el('span', {}, k))),
    el('button', { class: 'chip accent', onclick: () => add(null) }, '+ Custom action'));
  draw();
  body.append(el('div', { class: 'card' }, el('h3', {}, 'Which actions do you need?'),
    el('p', { class: 'small muted' }, 'Presets come with good frame counts and timing. For anything else, add a custom action and describe it in one line — the prompt step turns it into frame-by-frame poses.'),
    chips, list), nav(go, 0, async () => { clearTimeout(timer); await savePlan(); if (!W.plan.actions.length) throw new Error('Add at least one action'); go(2); }));
}

// ------------------------------------------------------------------ 3 prompts
async function stepPrompts(body, go, root) {
  const codexOk = avail('codex');
  const status = el('span', { class: 'small muted' });
  const write = (method) => guard(async () => {
    await savePlan();
    if (method === 'template') {
      const r = await api(`${proj()}/characters/${W.cid}/plan/prompts`, { body: { method } });
      W.plan = r.plan; toast('Prompts written'); renderWizard(root); return;
    }
    status.textContent = 'Codex is looking at the reference image and writing prompts… (usually under a minute)';
    const job = await api(`${proj()}/characters/${W.cid}/plan/prompts`, { body: { method } });
    await waitJob(job, async () => { await loadChar(); toast('Prompts written'); renderWizard(root); });
    status.textContent = '';
  });
  const identity = el('textarea', { rows: 3, placeholder: 'Character description used in every prompt (Codex fills this from the reference).' }, W.plan.identity || '');
  identity.onchange = () => guard(async () => { W.plan.identity = identity.value; W.plan.identity_source = 'manual'; await savePlan(); });
  const cards = W.plan.actions.map(a => {
    const poses = el('textarea', { rows: Math.min(8, a.frames), 'aria-label': 'Poses' }, a.poses.join('\n'));
    const prompt = el('textarea', { rows: 6, 'aria-label': 'Prompt', placeholder: 'No prompt yet — use one of the buttons above, or write your own.' }, a.prompt || '');
    poses.onchange = () => guard(async () => { a.poses = poses.value.split('\n').map(x => x.trim()).filter(Boolean); if (a.poses.length !== a.frames) toast(`Poses: ${a.poses.length}, frames: ${a.frames}`, true); await savePlan(); });
    prompt.onchange = () => guard(async () => { a.prompt = prompt.value; a.prompt_source = 'manual'; await savePlan(); });
    return el('div', { class: 'card' }, el('div', { class: 'row' }, el('b', { 'data-no-i18n': '' }, a.name), el('span', { class: 'muted small' }, `${a.frames} frames`),
      a.loop ? badge('Loop', '') : null, a.prompt_source ? badge(a.prompt_source, a.prompt_source === 'codex' ? 'ok' : '') : badge('no prompt', 'warn')),
      el('div', { class: 'small muted', 'data-no-i18n': '' }, a.description),
      el('div', { class: 'grid pgrid' }, el('div', {}, el('h4', {}, 'Frame poses (one per line)'), poses), el('div', {}, el('h4', {}, 'Prompt'), prompt)));
  });
  body.append(el('div', { class: 'card' }, el('h3', {}, 'Write the prompts'),
      el('div', { class: 'row' },
        el('button', { class: 'primary', disabled: !codexOk, title: codexOk ? '' : (provider('codex')?.status.reason || 'codex CLI not found'), onclick: () => write('codex') }, '✨ Write with Codex (reads the reference image)'),
        el('button', { onclick: () => write('template') }, 'Use built-in template'), status),
      el('p', { class: 'small muted' }, codexOk ? 'Codex describes the character from the image and writes frame-by-frame poses for each action. Everything stays editable.'
        : 'Codex CLI not found — install it and run codex login to let it write prompts from the image. The built-in template works offline.'),
      el('h4', {}, 'Character description'), identity),
    ...cards, nav(go, 1, async () => {
      await savePlan();
      const missing = W.plan.actions.filter(a => !a.prompt).map(a => a.id);
      if (missing.length) { const r = await api(`${proj()}/characters/${W.cid}/plan/prompts`, { body: { method: 'template', action_ids: missing } }); W.plan = r.plan; }
      go(3);
    }));
}

// ------------------------------------------------------------------ 4 generate
function providerCard(id, title, desc, extra) {
  const p = provider(id);
  const ok = !!p?.status.available;
  const radio = el('input', { type: 'radio', name: 'prov', value: id, checked: W.provider === id, disabled: !ok });
  radio.onchange = () => { W.provider = id; document.querySelectorAll('.prov').forEach(x => x.classList.toggle('sel', x.dataset.id === id)); };
  return el('label', { class: 'prov' + (W.provider === id ? ' sel' : '') + (ok ? '' : ' off'), 'data-id': id },
    el('div', { class: 'row' }, radio, el('b', {}, title), badge(ok ? 'available' : 'unavailable', ok ? 'ok' : 'err'), p?.status.details?.is_mock ? badge('MOCK', 'fixture') : null),
    el('div', { class: 'small muted' }, desc), ok ? null : el('div', { class: 'small errtext' }, p?.status.reason || ''), extra || null);
}

function genParams() { return W.provider === 'comfyui' ? { ...(W.checkpoint ? { checkpoint: W.checkpoint } : {}), denoise: W.denoise } : {}; }

async function stepGenerate(body, go, root) {
  if (!W.provider || !avail(W.provider)) W.provider = ['codex', 'comfyui'].find(avail) || null;
  S.workflows = await api('/api/workflows');
  const wfs = S.workflows.filter(w => ['character_reference', 'image_to_image'].includes(w.category));
  const wf = select([['', 'default (character reference img2img)'], ...wfs.map(w => [w.id, `${w.name} (${w.verification})`])], W.workflow);
  const ckpt = el('input', { value: W.checkpoint, placeholder: 'checkpoint file, e.g. sdxl_base.safetensors' });
  const den = el('input', { type: 'number', step: 0.05, min: 0.2, max: 1, value: W.denoise });
  wf.onchange = () => (W.workflow = wf.value); ckpt.onchange = () => (W.checkpoint = ckpt.value); den.onchange = () => (W.denoise = +den.value);
  const comfyExtra = el('div', { class: 'form small' }, ...field('Workflow', wf), ...field('Checkpoint', ckpt), ...field('Denoise', den));
  const checks = {};
  const rows = W.plan.actions.map(a => { checks[a.id] = el('input', { type: 'checkbox', checked: !a.asset_id || a.status === 'failed' });
    return el('label', { class: 'row' }, checks[a.id], el('span', { 'data-no-i18n': '' }, a.name), el('span', { class: 'muted small' }, `${a.frames} frames`), badge(a.status)); });
  const cost = el('span', { class: 'muted small' });
  const upd = () => { const n = Object.values(checks).filter(c => c.checked).length; cost.textContent = `${n} generation call(s) — one image per action`; };
  Object.values(checks).forEach(c => c.onchange = upd); upd();
  const prog = el('div', {});
  const run = () => guard(async () => {
    const ids = Object.entries(checks).filter(([, c]) => c.checked).map(([id]) => id);
    if (!ids.length) throw new Error('Select at least one action');
    if (!W.provider) throw new Error('Choose a generator');
    const job = await api(`${proj()}/characters/${W.cid}/plan/generate`, { body: { provider_id: W.provider, workflow_id: W.workflow || null, params: genParams(), action_ids: ids } });
    prog.innerHTML = '';
    const bar = el('i', { style: 'width:2%' }), msg = el('div', { class: 'small muted', 'data-no-i18n': '' }, 'queued');
    prog.append(el('div', { class: 'bar big' }, bar), msg);
    const poll = setInterval(async () => { try { const j = await api('/api/jobs/' + job.id); bar.style.width = Math.max(2, Math.round((j.progress || 0) * 100)) + '%'; msg.textContent = j.message; } catch (e) { /* ignore */ } }, 600);
    const j = await waitJob(job, async () => {});
    clearInterval(poll);
    await refreshProject(); await loadChar();
    if (j?.status === 'succeeded') { const f = Object.keys(j.result.failed || {}); if (f.length) toast(`Failed: ${f.join(', ')}`, true); go(4); }
    else renderWizard(root);
  });
  body.append(el('div', { class: 'grid cols2' },
    el('div', { class: 'card' }, el('h3', {}, 'Generator'),
      providerCard('codex', 'Codex CLI', 'Uses your logged-in Codex account. Best at keeping the character identical across the strip.'),
      providerCard('comfyui', 'Local ComfyUI', 'Your own models on your GPU. The reference is repeated across the strip and redrawn per pose (img2img).', comfyExtra),
      S.providers.some(p => p.id === 'mock') ? providerCard('mock', 'Test fixtures (no AI)', 'Returns bundled sample art labelled TEST FIXTURE — for trying the workflow only.') : null),
    el('div', { class: 'card' }, el('h3', {}, 'Actions to generate'), ...rows, el('p', {}, cost),
      el('p', { class: 'small muted' }, 'Each action is generated as one sprite strip, then cut into frames and aligned to one ground line and scale. You can redo single frames afterwards.'),
      el('button', { class: 'primary big', onclick: run }, '▶ Generate'), prog)),
    nav(go, 2, W.plan.actions.some(a => a.asset_id) ? 4 : null, 'Review →'));
}

// ------------------------------------------------------------------ 5 review + export
function player(a) {
  const fr = a.animation.frames.filter(f => f.status !== 'rejected');
  const img = el('img', { alt: a.name });
  let i = 0;
  const tick = () => { if (i > 0 && !img.isConnected) return; const f = fr[i % fr.length]; img.src = fileUrl(a, f.file); i++; setTimeout(tick, Math.max(40, f.duration_ms)); };
  if (fr.length) tick();
  return el('div', { class: 'player checker' }, img);
}

async function stepReview(body, go, root) {
  const done = W.plan.actions.filter(a => a.asset_id);
  const assets = {};
  await Promise.all(done.map(async a => { try { assets[a.id] = await api(`${proj()}/assets/${a.asset_id}`); } catch (e) { /* deleted */ } }));
  const redoFrame = (pa, a, i) => guard(async () => {
    const note = prompt(t(`${pa.name} — frame ${i + 1}: what should change? (leave empty to just redo it)`), '');
    if (note === null) return;
    if (!W.provider || !avail(W.provider)) W.provider = ['codex', 'comfyui'].find(avail) || 'mock';
    const job = await api(`${proj()}/assets/${a.id}/regenerate`, { body: { index: i, provider_id: W.provider, workflow_id: W.workflow || null, note, params: genParams() } });
    toast('Regeneration queued');
    await waitJob(job, async () => { toast('Frame regenerated'); renderWizard(root); });
  });
  const cards = done.filter(a => assets[a.id]).map(pa => {
    const a = assets[pa.id];
    const approved = a.qa?.manual?.decision === 'approved';
    const strip = el('div', { class: 'fstrip' }, ...a.animation.frames.map((f, i) => el('figure', { class: f.status === 'rejected' ? 'rej' : '', title: 'Click to redo this frame',
      onclick: () => redoFrame(pa, a, i) }, el('img', { src: fileUrl(a, f.file) }), el('figcaption', {}, String(i + 1)))));
    return el('div', { class: 'card rcard' },
      el('div', { class: 'row' }, el('b', { 'data-no-i18n': '' }, pa.name), badge(approved ? 'approved' : a.status), badge(a.qa.deterministic.status), fixtureBadge(a),
        el('span', { class: 'muted small' }, `${a.animation.frames.length} frames · ${a.provider.id}`), el('span', { class: 'spacer' }),
        approved ? null : el('button', { class: 'small primary', onclick: () => guard(async () => { await api(`${proj()}/assets/${a.id}/decision`, { body: { decision: 'approved' } }); toast('Approved'); renderWizard(root); }) }, '✓ Approve'),
        el('button', { class: 'small', onclick: () => { W.step = 3; renderWizard(root); } }, '↻ Redo action'),
        el('button', { class: 'small ghost', onclick: () => emit('open-asset', a.id) }, 'Fine-tune…')),
      (a.action?.layout || '').startsWith('grid') ? el('div', { class: 'warnbox' }, 'Frames were cut on an even grid because the generator did not return separate sprites — check the frames.') : null,
      el('div', { class: 'rgrid' }, player(a), el('div', {}, el('div', { class: 'small muted' }, 'Click a frame to redo just that frame.'), strip)));
  });
  const targets = { cocos: ['atlas', 'cocos', 'gif', 'json', 'zip'], godot: ['frames', 'sheet', 'godot', 'json', 'zip'], phaser: ['atlas', 'phaser', 'json', 'zip'],
    png: ['frames', 'sheet', 'gif', 'zip'], all: ['frames', 'sheet', 'atlas', 'gif', 'apng', 'json', 'cocos', 'phaser', 'godot', 'zip'] };
  const tgt = select([['cocos', 'Cocos Creator'], ['godot', 'Godot'], ['phaser', 'Phaser / PixiJS'], ['png', 'PNG frames + sheets + GIF'], ['all', 'Everything']], 'cocos');
  const onlyApproved = el('input', { type: 'checkbox' });
  const out = el('div', {});
  const exp = () => guard(async () => {
    const ids = done.map(a => assets[a.id]).filter(Boolean).filter(a => !onlyApproved.checked || a.qa?.manual?.decision === 'approved').map(a => a.id);
    if (!ids.length) throw new Error('Select at least one animation');
    const fname = (W.char.name || '').replace(/[^A-Za-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '').toLowerCase() || W.cid;
    const job = await api(`${proj()}/export`, { body: { asset_ids: ids, name: fname, formats: targets[tgt.value], character_id: W.cid } });
    await waitJob(job, async (j) => {
      const list = await api(`${proj()}/exports`); const x = list.find(e => e.export_id === j.result.export_id) || list[0];
      out.innerHTML = '';
      out.append(el('div', { class: 'row' }, badge('Export finished', 'ok'), x?.zip ? el('a', { class: 'btn primary', href: exportUrl(S.project, x.export_id, x.zip) }, '⬇ Download ZIP') : null,
        x?.contains_test_fixtures ? badge('CONTAINS TEST FIXTURES', 'fixture') : null));
    });
  });
  body.append(...(cards.length ? cards : [el('div', { class: 'card muted' }, 'Nothing generated yet.')]),
    el('div', { class: 'card' }, el('h3', {}, 'Export'), el('div', { class: 'row' }, el('label', {}, 'For', tgt), el('label', {}, onlyApproved, 'approved only'),
      el('button', { class: 'primary', onclick: exp }, 'Export')), out),
    nav(go, 3, null));
}
