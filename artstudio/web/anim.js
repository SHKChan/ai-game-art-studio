// Animation Studio: playback, timeline editing, onion skin, anchor editing, comparison, events, layers, QA.
import { S, api, el, toast, guard, emit, fileUrl, badge, fixtureBadge, refreshProject, select, readFile, waitJob, assetsOfProject } from './core.js';

const V = { asset: null, imgs: [], srcImgs: [], cur: 0, playing: false, zoom: 4, bg: 'checker', onion: false, ground: true, pivot: true,
  anchorEdit: false, compare: false, cmpA: 0, cmpB: 1, cmpSource: false, layerImgs: {}, t0: 0, raf: 0, showLayers: true };

export function openAsset(id) { S.asset = id; }

function loadImg(src) { return new Promise((res) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = src + '?v=' + Date.now(); }); }

async function loadAsset(id) {
  const a = await api(`/api/projects/${S.project}/assets/${id}`);
  V.asset = a;
  V.imgs = await Promise.all(a.animation.frames.map(f => loadImg(fileUrl(a, f.file))));
  V.srcImgs = [];
  V.layerImgs = {};
  for (const l of a.animation.layers || []) {
    const la = await api(`/api/projects/${S.project}/assets/${l.asset_id}`).catch(() => null);
    if (la) V.layerImgs[l.asset_id] = { asset: la, layer: l, imgs: await Promise.all(la.animation.frames.map(f => loadImg(fileUrl(la, f.file)))) };
  }
  if (V.lastId !== id) { V.zoom = Math.max(1, Math.min(12, Math.floor(480 / Math.max(...a.animation.canvas)))); V.cur = 0; V.lastId = id; }
  V.cur = Math.min(V.cur, a.animation.frames.length - 1);
}

function frames() { return V.asset.animation.frames; }
function activeIdx() { return frames().map((f, i) => [f, i]).filter(([f]) => f.status !== 'rejected').map(([, i]) => i); }

function drawBg(ctx, w, h) {
  if (V.bg === 'checker') {
    const s = 8;
    for (let y = 0; y < h; y += s) for (let x = 0; x < w; x += s) { ctx.fillStyle = ((x + y) / s) % 2 ? '#9aa0ad' : '#7a7f8c'; ctx.fillRect(x, y, s, s); }
  } else { ctx.fillStyle = V.bg; ctx.fillRect(0, 0, w, h); }
}

function layerFrameAt(L, tMs) {
  const fr = L.asset.animation.frames; const total = fr.reduce((s, f) => s + f.duration_ms, 0);
  let t = tMs - (L.layer.start_ms || 0);
  if (t < 0) return -1;
  if (L.asset.animation.loop.enabled) t = t % total; else if (t >= total) return -1;
  let acc = 0;
  for (let i = 0; i < fr.length; i++) { acc += fr[i].duration_ms; if (t < acc) return i; }
  return -1;
}

function frameStart(i) { return frames().slice(0, i).reduce((s, f) => s + f.duration_ms, 0); }

function draw(canvas) {
  const a = V.asset; if (!a) return;
  const [cw, ch] = a.animation.canvas; const z = V.zoom;
  canvas.width = cw * z; canvas.height = ch * z;
  const ctx = canvas.getContext('2d'); ctx.imageSmoothingEnabled = a.art_style !== 'pixel';
  drawBg(ctx, canvas.width, canvas.height);
  const idx = V.cur; const act = activeIdx();
  if (V.onion && !V.playing) {
    const pos = act.indexOf(idx);
    for (const [off, tint] of [[-1, 'rgba(255,80,80,.35)'], [1, 'rgba(80,160,255,.35)']]) {
      const j = act[(pos + off + act.length) % act.length];
      if (j === undefined || j === idx || !V.imgs[j]) continue;
      ctx.globalAlpha = 0.35; ctx.drawImage(V.imgs[j], 0, 0, cw * z, ch * z); ctx.globalAlpha = 1;
    }
  }
  const tMs = frameStart(idx) + (V.playing ? V.subMs || 0 : 0);
  const layers = V.showLayers ? Object.values(V.layerImgs).sort((x, y) => x.layer.z - y.layer.z) : [];
  for (const L of layers.filter(L => L.layer.z < 0)) drawLayer(ctx, L, tMs, z);
  if (V.imgs[idx]) ctx.drawImage(V.imgs[idx], 0, 0, cw * z, ch * z);
  for (const L of layers.filter(L => L.layer.z >= 0)) drawLayer(ctx, L, tMs, z);
  const [px, py] = a.animation.pivot;
  if (V.ground) { ctx.strokeStyle = 'rgba(65,199,138,.9)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(0, py * z + .5); ctx.lineTo(cw * z, py * z + .5); ctx.stroke(); }
  if (V.pivot) { ctx.strokeStyle = '#ff5fa2'; ctx.beginPath(); ctx.moveTo(px * z - 6, py * z); ctx.lineTo(px * z + 6, py * z); ctx.moveTo(px * z, py * z - 6); ctx.lineTo(px * z, py * z + 6); ctx.stroke(); }
}

function drawLayer(ctx, L, tMs, z) {
  const i = layerFrameAt(L, tMs); if (i < 0 || !L.imgs[i]) return;
  const a = V.asset; const [px, py] = a.animation.pivot; const [lx, ly] = L.asset.animation.pivot; const [ox, oy] = L.layer.offset || [0, 0];
  const [lw, lh] = L.asset.animation.canvas;
  ctx.drawImage(L.imgs[i], (px - lx + ox) * z, (py - ly + oy) * z, lw * z, lh * z);
}

function play(canvas, info) {
  cancelAnimationFrame(V.raf);
  let last = performance.now(); V.subMs = 0;
  const tick = (now) => {
    if (!V.playing) return;
    V.subMs += now - last; last = now;
    const act = activeIdx(); if (!act.length) return;
    let d = frames()[V.cur].duration_ms;
    while (V.subMs >= d) {
      V.subMs -= d;
      const pos = act.indexOf(V.cur);
      if (pos === act.length - 1 && !V.asset.animation.loop.enabled) { V.playing = false; V.subMs = 0; info(); draw(canvas); return; }
      V.cur = act[(pos + 1) % act.length]; d = frames()[V.cur].duration_ms;
    }
    draw(canvas); info();
    V.raf = requestAnimationFrame(tick);
  };
  V.raf = requestAnimationFrame(tick);
}

async function frameOp(op, extra = {}) {
  const a = await api(`/api/projects/${S.project}/assets/${V.asset.id}/frames`, { body: { op, ...extra } });
  V.asset = a; await loadAsset(a.id); await refreshProject();
}

export async function renderAnimation(root) {
  root.innerHTML = '';
  const anims = assetsOfProject(a => a.animation);
  const pick = select([['', '— choose an animation asset —'], ...anims.map(a => [a.id, `${a.name} · ${a.animation.name}/${a.animation.direction} · ${a.animation.frames.length}f`])], S.asset || '');
  pick.onchange = () => { S.asset = pick.value; renderAnimation(root); };
  root.append(el('div', { class: 'row' }, el('b', {}, 'Animation'), pick));
  if (!S.asset) { root.append(el('p', { class: 'muted' }, 'Pick an animation (or open one from the Library).')); return; }
  await loadAsset(S.asset);
  const a = V.asset; const A = a.animation;
  const canvas = el('canvas', { title: 'Click to set pivot when anchor-edit is on' });
  const info = el('div', { class: 'row small mono' });
  const updInfo = () => {
    const f = frames()[V.cur];
    info.textContent = `frame ${V.cur + 1}/${frames().length} · ${f.duration_ms}ms · offset ${f.offset} · phase ${f.phase || '-'} · origin ${f.origin}${f.airborne ? ' · airborne' : ''} · canvas ${A.canvas} · pivot ${A.pivot}`;
    tl.querySelectorAll('.tframe').forEach((t, i) => t.classList.toggle('cur', i === V.cur));
  };
  canvas.onclick = (e) => {
    if (!V.anchorEdit) return;
    const r = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - r.left) * canvas.width / r.width / V.zoom), y = Math.floor((e.clientY - r.top) * canvas.height / r.height / V.zoom);
    guard(async () => { await frameOp('pivot', { x, y }); toast(`Pivot set to ${x},${y}`); renderAnimation(root); });
  };
  const stage = el('div', { class: 'stage' }, canvas);
  // controls
  const playBtn = el('button', { class: 'primary', onclick: () => { V.playing = !V.playing; playBtn.textContent = V.playing ? '❚❚ Pause' : '▶ Play'; if (V.playing) play(canvas, updInfo); else draw(canvas); } }, '▶ Play');
  const step = (d) => { V.playing = false; playBtn.textContent = '▶ Play'; V.cur = (V.cur + d + frames().length) % frames().length; draw(canvas); updInfo(); };
  const zoom = select([...new Set([1, 2, 3, 4, 6, 8, 12, V.zoom])].sort((x, y) => x - y), V.zoom, { title: 'Zoom' }); zoom.onchange = () => { V.zoom = +zoom.value; draw(canvas); };
  const bg = select([['checker', 'checker'], ['#14161c', 'dark'], ['#ffffff', 'white'], ['#3fbf5f', 'green'], ['#6b8cff', 'blue'], ['#000000', 'black']], V.bg);
  bg.onchange = () => { V.bg = bg.value; draw(canvas); };
  const tog = (key, label) => { const c = el('input', { type: 'checkbox', checked: V[key] }); c.onchange = () => { V[key] = c.checked; draw(canvas); }; return el('label', {}, c, label); };
  const fps = el('input', { type: 'number', min: 1, max: 60, value: Math.round(1000 / (A.frames[0]?.duration_ms || 100)) });
  const anchorBtn = el('button', { onclick: () => { V.anchorEdit = !V.anchorEdit; anchorBtn.classList.toggle('primary', V.anchorEdit); } }, '✛ Anchor edit');
  const controls = el('div', { class: 'row' }, playBtn, el('button', { onclick: () => step(-1), title: 'Previous frame' }, '◀'), el('button', { onclick: () => step(1), title: 'Next frame' }, '▶'),
    el('label', {}, 'Zoom', zoom), el('label', {}, 'BG', bg), tog('onion', 'Onion skin'), tog('ground', 'Ground line'), tog('pivot', 'Pivot'),
    Object.keys(V.layerImgs).length ? tog('showLayers', 'Layers') : null,
    el('label', {}, el('input', { type: 'checkbox', checked: A.loop.enabled, onchange: (e) => guard(() => frameOp('loop', { enabled: e.target.checked })) }), 'Loop'),
    el('label', {}, 'FPS', fps, el('button', { class: 'small', onclick: () => guard(async () => { await frameOp('fps', { fps: +fps.value }); renderAnimation(root); }) }, 'apply to all')),
    anchorBtn);
  // timeline
  const tl = el('div', { class: 'timeline' });
  let dragFrom = null;
  frames().forEach((f, i) => {
    const evs = (A.events || []).filter(e => e.frame === i).map(e => e.type).join(',');
    const t = el('div', { class: 'tframe' + (f.status === 'rejected' ? ' rej' : '') + (i === V.cur ? ' cur' : ''), draggable: 'true',
      onclick: () => { V.cur = i; V.playing = false; playBtn.textContent = '▶ Play'; draw(canvas); updInfo(); renderSide(); },
      ondragstart: () => (dragFrom = i), ondragover: (e) => { e.preventDefault(); t.classList.add('dragover'); }, ondragleave: () => t.classList.remove('dragover'),
      ondrop: (e) => { e.preventDefault(); if (dragFrom !== null && dragFrom !== i) guard(async () => { await frameOp('move', { index: dragFrom, to: i }); renderAnimation(root); }); } },
      el('img', { src: fileUrl(a, f.file) + '?v=' + Date.now(), alt: 'frame ' + i, class: V.bg === 'checker' ? 'checker' : '' }),
      el('div', {}, `#${i} · `, el('input', { type: 'number', value: f.duration_ms, style: 'width:52px;padding:1px', title: 'duration ms', onclick: (e) => e.stopPropagation(),
        onchange: (e) => guard(() => frameOp('duration', { index: i, duration_ms: +e.target.value })) })),
      evs ? el('div', { class: 'ev' }, '⚑ ' + evs) : null, f.phase ? el('div', { class: 'muted' }, f.phase) : null);
    tl.append(t);
  });
  const side = el('div', { class: 'card' });
  const renderSide = () => { side.innerHTML = ''; side.append(...frameTools(root, canvas)); };
  const head = el('div', { class: 'row' }, el('h3', {}, a.name), badge(a.status), badge(a.art_style, ''), fixtureBadge(a), el('span', { class: 'muted small' }, `${A.name} · ${A.direction} · provider ${a.provider.id}`));
  const fixtureWarn = a.provider.is_test_fixture ? el('div', { class: 'warnbox' }, 'This asset contains TEST FIXTURE output from a mock provider. It is not AI-generated artwork.') : null;
  root.append(el('div', { class: 'grid cols3' },
    el('div', { class: 'card' }, ...assetPanel(root)),
    el('div', { class: 'card' }, head, fixtureWarn, controls, stage, info, tl, compareView()),
    side));
  renderSide(); draw(canvas); updInfo();
}

function compareView() {
  const box = el('div', {});
  const btn = el('button', { onclick: () => { V.compare = !V.compare; fill(); } }, '⇆ Frame comparison');
  const fill = () => {
    box.querySelector('.compare')?.remove();
    if (!V.compare) return;
    const a = V.asset; const n = frames().length;
    const sa = select([...Array(n).keys()], V.cmpA), sb = select([...Array(n).keys()], V.cmpB);
    const src = el('input', { type: 'checkbox', checked: V.cmpSource });
    const imgA = el('img'), imgB = el('img');
    const upd = () => {
      V.cmpA = +sa.value; V.cmpB = +sb.value; V.cmpSource = src.checked;
      imgA.src = fileUrl(a, frames()[V.cmpA].file);
      imgB.src = V.cmpSource ? fileUrl(a, frames()[V.cmpA].source_file || frames()[V.cmpA].file) : fileUrl(a, frames()[V.cmpB].file);
    };
    [sa, sb, src].forEach(x => x.onchange = upd);
    box.append(el('div', { class: 'compare' },
      el('div', {}, el('div', { class: 'row' }, 'A', sa), el('div', { class: 'checker' }, imgA)),
      el('div', {}, el('div', { class: 'row' }, el('label', {}, src, 'B = source of A (before/after)'), 'B', sb), el('div', { class: 'checker' }, imgB))));
    upd();
  };
  box.append(btn); return box;
}

function assetPanel(root) {
  const a = V.asset; const A = a.animation;
  const qa = a.qa.deterministic || {};
  const issues = el('div', { class: 'issues' }, ...(qa.issues || []).map(i => el('div', { class: 'issue ' + i.severity }, `${i.severity} · ${i.code}${i.frame !== undefined ? ' #' + i.frame : ''} — ${i.message}`)));
  const vis = a.qa.visual || {};
  const P = a.processing?.normalize?.params || {};
  const mode = select(['pixel', 'hd'], a.art_style), anchor = select(['source', 'ground', 'support_foot', 'torso'], P.anchor || 'source');
  const scale = el('input', { type: 'number', step: 0.05, value: a.processing?.normalize?.scale ?? 1 });
  const th = el('input', { type: 'number', placeholder: 'px', value: P.target_height || '' });
  const pal = el('input', { type: 'number', placeholder: 'colours', value: P.palette_size || '' });
  const keepCanvas = el('input', { type: 'checkbox' });
  const evType = el('input', { placeholder: 'event type e.g. hit', value: 'hit', style: 'width:110px' });
  const effects = assetsOfProject(x => x.animation && x.id !== a.id);
  const effSel = select([['', '— effect / layer asset —'], ...effects.map(x => [x.id, x.name])], '');
  const anchorEv = select([['', 'start at 0ms'], ...[...new Set((A.events || []).map(e => e.type))].map(t => [t, 'at event: ' + t])], 'hit');
  const offx = el('input', { type: 'number', value: 0 }), offy = el('input', { type: 'number', value: 0 });
  return [
    el('h3', {}, 'Asset'), el('div', { class: 'small muted' }, a.id),
    el('div', { class: 'row' },
      el('button', { onclick: () => guard(async () => { await api(`/api/projects/${S.project}/assets/${a.id}/decision`, { body: { decision: 'approved' } }); toast('Approved'); renderAnimation(root); }) }, '✓ Approve'),
      el('button', { class: 'danger', onclick: () => guard(async () => { await api(`/api/projects/${S.project}/assets/${a.id}/decision`, { body: { decision: 'rejected' } }); toast('Rejected'); renderAnimation(root); }) }, '✗ Reject')),
    el('h4', {}, 'Deterministic QA ', badge(qa.status || 'not_run')),
    el('button', { onclick: () => guard(async () => { await api(`/api/projects/${S.project}/assets/${a.id}/qa`, { body: {} }); renderAnimation(root); }) }, 'Run checks'),
    issues,
    el('h4', {}, 'Visual review (probabilistic) ', badge(vis.status || 'not_run')),
    el('div', { class: 'small muted' }, 'Technical checks do not prove identity, anatomy or motion quality. Record your own review:'),
    (V.vnote = el('input', { placeholder: 'review notes (what you checked / what is wrong)', value: vis.notes || '' })),
    el('div', { class: 'row' }, el('button', { class: 'small', onclick: () => visualReview(root, 'pass') }, 'Looks consistent'), el('button', { class: 'small danger', onclick: () => visualReview(root, 'fail') }, 'Problems found')),
    el('h4', {}, 'Reprocess (from preserved sources)'),
    el('div', { class: 'form' }, 'Mode', mode, 'Anchor', anchor, 'Scale', scale, 'Target height', th, 'Palette size', pal, 'Keep canvas', keepCanvas),
    el('button', { onclick: () => guard(async () => {
      const params = { mode: mode.value, anchor: anchor.value, scale: +scale.value || 1, target_height: th.value ? +th.value : null, palette_size: pal.value ? +pal.value : null };
      if (keepCanvas.checked) { params.canvas = A.canvas; params.pivot = A.pivot; } else { params.canvas = null; params.pivot = null; }
      await api(`/api/projects/${S.project}/assets/${a.id}/reprocess`, { body: { params } }); toast('Reprocessed'); renderAnimation(root);
    }) }, 'Reprocess'),
    el('h4', {}, 'Events'),
    el('div', {}, ...(A.events || []).map((e, k) => el('div', { class: 'row small' }, `#${e.frame} ${e.type}`, el('button', { class: 'small', onclick: () => guard(async () => {
      await frameOp('events', { events: A.events.filter((_, j) => j !== k) }); renderAnimation(root); }) }, '×')))),
    el('div', { class: 'row' }, evType, el('button', { class: 'small', onclick: () => guard(async () => {
      await frameOp('events', { events: [...(A.events || []), { frame: V.cur, type: evType.value.trim() }] }); renderAnimation(root); }) }, '+ at current frame')),
    el('h4', {}, 'Layers (hybrid)'),
    el('div', {}, ...(A.layers || []).map(l => el('div', { class: 'small' }, `${l.role}: ${l.name} · start ${l.start_ms}ms · offset ${l.offset}${l.anchor_to_event ? ' · @' + l.anchor_to_event : ''}`))),
    el('div', { class: 'form' }, 'Layer', effSel, 'Timing', anchorEv, 'Offset x/y', el('div', { class: 'row' }, offx, offy)),
    el('button', { onclick: () => guard(async () => { if (!effSel.value) throw new Error('Choose a layer asset');
      await api(`/api/projects/${S.project}/assets/${a.id}/layers`, { body: { effect_id: effSel.value, anchor_event: anchorEv.value, offset: [+offx.value, +offy.value] } });
      toast('Layer attached'); renderAnimation(root); }) }, 'Attach layer'),
    el('h4', {}, 'Versions'),
    el('div', { class: 'issues' }, ...[...a.versions].reverse().map(v => el('div', { class: 'row small' }, `v${v.version} · ${v.note || ''}`,
      el('button', { class: 'small', onclick: () => guard(async () => { await api(`/api/projects/${S.project}/assets/${a.id}/restore`, { body: { version: v.version } }); toast('Restored'); renderAnimation(root); }) }, 'restore')))),
    el('h4', {}, 'Contact sheet'), el('a', { href: `/api/projects/${S.project}/assets/${a.id}/contact-sheet.png`, target: '_blank' }, 'Open contact sheet PNG'),
  ];
}

async function visualReview(root, verdict) {
  const notes = V.vnote?.value || (verdict === 'fail' ? 'problems found' : 'reviewed: consistent');
  const findings = { character_identity_drift: verdict, art_style_drift: verdict, unnatural_motion: verdict };
  await guard(() => api(`/api/projects/${S.project}/assets/${V.asset.id}/visual-review`, { body: { findings, notes, reviewer: 'user' } }));
  renderAnimation(root);
}

function frameTools(root, canvas) {
  const a = V.asset; const f = frames()[V.cur]; const i = V.cur;
  const provs = S.providers.filter(p => ['comfyui', 'mock', 'codex'].includes(p.id));
  const prov = select(provs.map(p => [p.id, `${p.id}${p.status.available ? '' : ' (unavailable)'}`]), provs.find(p => p.status.available)?.id);
  const wf = select([['', '— workflow (ComfyUI) —'], ...S.workflows.map(w => [w.id, `${w.id} [${w.verification}]`])], 'sd-pose-keyframe');
  const params = el('textarea', { class: 'mono', placeholder: '{"checkpoint": "...", "steps": 24}' }, '{}');
  const note = el('input', { placeholder: 'what to fix (e.g. keep both hands on the hilt)' });
  const phase = el('input', { value: f.phase || '', placeholder: 'phase', style: 'width:120px' });
  const fileIn = el('input', { type: 'file', accept: 'image/png,image/webp,image/jpeg' });
  fileIn.onchange = () => guard(async () => {
    const data = await readFile(fileIn.files[0]);
    await api(`/api/projects/${S.project}/assets/${a.id}/replace`, { body: { index: i, image: data } }); toast('Frame replaced (placed with group scale/anchor)'); renderAnimation(root);
  });
  if (!S.workflows.length) api('/api/workflows').then(w => { S.workflows = w; });
  return [
    el('h3', {}, `Frame #${i}`),
    el('div', { class: 'checker', style: 'text-align:center' }, el('img', { src: fileUrl(a, f.file) + '?v=' + Date.now(), style: 'max-width:100%;image-rendering:pixelated;max-height:180px' })),
    el('div', { class: 'small muted' }, `source rect ${f.source_rect || '-'} · source size ${f.source_size} · trimmed ${f.trimmed_rect}`),
    f.generation ? el('div', { class: 'small muted' }, 'generation: ' + JSON.stringify({ provider: f.generation.provider, workflow: f.generation.workflow_id, fixture: f.generation.is_test_fixture })) : null,
    el('div', { class: 'row' },
      el('button', { onclick: () => guard(async () => { await frameOp('duplicate', { index: i }); renderAnimation(root); }) }, 'Duplicate'),
      el('button', { onclick: () => guard(async () => { await frameOp(f.status === 'rejected' ? 'restore' : 'reject', { index: i }); renderAnimation(root); }) }, f.status === 'rejected' ? 'Restore' : 'Reject'),
      el('button', { class: 'danger', onclick: () => guard(async () => { await frameOp('delete', { index: i }); V.cur = Math.max(0, i - 1); renderAnimation(root); }) }, 'Delete')),
    el('div', { class: 'row' }, 'Nudge',
      ...[['←', -1, 0], ['→', 1, 0], ['↑', 0, -1], ['↓', 0, 1]].map(([t, dx, dy]) => el('button', { class: 'small', onclick: () => guard(async () => { await frameOp('nudge', { index: i, dx, dy }); renderAnimation(root); }) }, t))),
    el('div', { class: 'row' }, el('label', {}, el('input', { type: 'checkbox', checked: f.airborne, onchange: (e) => guard(() => frameOp('airborne', { index: i, value: e.target.checked })) }), 'airborne (exempt from ground snap)')),
    el('div', { class: 'row' }, phase, el('button', { class: 'small', onclick: () => guard(async () => { await frameOp('phase', { index: i, phase: phase.value }); renderAnimation(root); }) }, 'Set phase')),
    el('h4', {}, 'Manual replacement'), fileIn,
    el('h4', {}, 'Selective regeneration'),
    el('div', { class: 'form' }, 'Provider', prov, 'Workflow', wf, 'Fix note', note),
    el('details', {}, el('summary', { class: 'small muted' }, 'workflow parameters (JSON)'), params),
    el('button', { class: 'primary', onclick: () => guard(async () => {
      const p = S.providers.find(x => x.id === prov.value);
      if (!p?.status.available) throw new Error(`${prov.value} is unavailable: ${p?.status.reason}`);
      const job = await api(`/api/projects/${S.project}/assets/${a.id}/regenerate`, { body: { index: i, provider_id: prov.value, workflow_id: wf.value || null, params: JSON.parse(params.value || '{}'), note: note.value } });
      toast('Regeneration queued'); await waitJob(job, () => { toast('Frame regenerated'); renderAnimation(root); });
    }) }, 'Regenerate this frame'),
    el('h4', {}, 'Use as character master candidate'),
    el('button', { onclick: () => guard(async () => {
      if (!a.character_id) throw new Error('Asset has no character');
      await api(`/api/projects/${S.project}/characters/${a.character_id}/frame-as-candidate`, { body: { asset_id: a.id, index: i, direction: a.animation.direction === 'none' ? 'primary' : a.animation.direction } });
      toast('Added as candidate in Character Studio');
    }) }, 'Add frame as master candidate'),
  ];
}
