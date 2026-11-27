// Pixel Forge: pick a builder, tweak it live (variant, size, speed, colours, outline, glow, flip, scale), save or export.
import { t } from './i18n.js';
import { S, api, el, toast, guard, emit, exportUrl, badge, select, waitJob, refreshProject } from './core.js';

const F = { builders: null, defaults: null, builder: null, params: {}, edits: {}, prev: null, imgs: [], frame: 0, playing: true,
  zoom: 4, bg: 'checker', seq: 0, timer: null, tick: null, source: null };

const title = (k) => k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
const BG = { checker: null, dark: '#1b1e27', light: '#f2f3f7', green: '#3a9a4a' };

function paramDefaults(b) { return Object.fromEntries(Object.entries(F.builders[b].params).map(([k, p]) => [k, p.default])); }

function choose(b, params, edits, source = null) {
  F.builder = b; F.params = { ...paramDefaults(b), ...(params || {}) }; F.edits = { ...F.defaults, ...(edits || {}) }; F.source = source;
  F.frame = 0;
}

export async function renderForge(root) {
  if (!F.builders) { const r = await api('/api/forge/builders'); F.builders = r.builders; F.defaults = r.edit_defaults; }
  if (!F.builder) choose(Object.keys(F.builders).includes('fireball') ? 'fireball' : Object.keys(F.builders)[0]);
  root.innerHTML = '';
  const canvas = el('canvas', { class: 'fcanvas', 'aria-label': 'Preview' });
  const info = el('div', { class: 'small muted', 'data-no-i18n': '' });
  const strip = el('div', { class: 'fthumbs' });
  const controls = el('div', { class: 'fcontrols' });
  const gallery = galleryPanel(root);
  const stage = el('div', { class: 'card fstage' },
    el('div', { class: 'row' }, el('h3', { 'data-no-i18n': '' }, title(F.builder)), el('span', { class: 'muted small' }, F.builders[F.builder].description),
      F.source ? badge('editing a copy', 'warn') : null),
    el('div', { class: 'fview', id: 'fview' }, canvas), previewBar(canvas), info, strip);
  root.append(el('div', { class: 'forge' }, gallery, stage, controls));
  renderControls(controls, canvas, info, strip, root);
  await refresh(canvas, info, strip);
}

function galleryPanel(root) {
  const groups = {};
  // search box: every word must appear in the builder name or its (English) tags
  const words = (F.q || '').toLowerCase().split(/\s+/).filter(Boolean);
  const hit = (k) => words.every(w => (k.replace(/_/g, ' ') + ' ' + (F.builders[k].tags || []).join(' ')).toLowerCase().includes(w));
  for (const [k, b] of Object.entries(F.builders)) if (hit(k)) (groups[b.group] ||= []).push(k);
  const search = el('input', { placeholder: 'search tags… (fire, dungeon, monster)', value: F.q || '', 'aria-label': 'Search builders' });
  search.onchange = () => { F.q = search.value; renderForge(root); };
  const mine = (S.data?.assets || []).filter(a => a.procedural?.builder && F.builders[a.procedural.builder]).slice(-12).reverse();
  return el('div', { class: 'card fgallery' }, el('h3', {}, 'Pixel Forge'),
    el('p', { class: 'small muted' }, 'Pick something to make, then adjust it on the right.'), search,
    !Object.keys(groups).length ? el('p', { class: 'muted small' }, 'Nothing matches these tags.') : null,
    ...['Characters', 'Skills & effects', 'Skill icons', 'Items & icons', 'UI', 'Scenery', 'Other'].filter(g => groups[g]).map(g => el('div', {},
      el('h4', {}, g), el('div', { class: 'fgrid' }, ...groups[g].map(k => el('button', { class: 'fitem' + (k === F.builder && !F.source ? ' sel' : ''), title: F.builders[k].description + '\n#' + (F.builders[k].tags || []).join(' #'),
        onclick: () => { choose(k); renderForge(root); } }, el('img', { src: `/api/forge/thumb/${k}.png`, alt: '' }), el('span', { 'data-no-i18n': '' }, title(k))))))),
    mine.length ? el('div', {}, el('h4', {}, 'Saved in this project'), ...mine.map(a => el('div', { class: 'row small fsaved' },
      el('a', { href: '#', 'data-no-i18n': '', onclick: (e) => { e.preventDefault(); choose(a.procedural.builder, a.procedural.params, a.procedural.edits, a.id); renderForge(root); } }, a.name),
      el('a', { href: '#', class: 'muted', onclick: (e) => { e.preventDefault(); emit('open-asset', a.id); } }, 'open')))) : null);
}

function previewBar(canvas) {
  const play = el('button', { class: 'small', onclick: () => { F.playing = !F.playing; play.textContent = F.playing ? '❚❚ Pause' : '▶ Play'; if (F.playing) animate(canvas); } }, F.playing ? '❚❚ Pause' : '▶ Play');
  const step = (d) => { F.playing = false; play.textContent = '▶ Play'; F.frame = (F.frame + d + F.imgs.length) % Math.max(1, F.imgs.length); draw(canvas); };
  const zoom = select([1, 2, 3, 4, 6, 8].map(z => [z, z + '×']), F.zoom, { 'aria-label': 'Zoom' });
  zoom.onchange = () => { F.zoom = +zoom.value; draw(canvas); };
  const bg = select([['checker', 'checker'], ['dark', 'dark'], ['light', 'light'], ['green', 'green']], F.bg, { 'aria-label': 'Background' });
  bg.onchange = () => { F.bg = bg.value; draw(canvas); };
  return el('div', { class: 'row' }, el('button', { class: 'small', title: 'Previous frame', onclick: () => step(-1) }, '◀'), play,
    el('button', { class: 'small', title: 'Next frame', onclick: () => step(1) }, '▶|'), el('label', {}, 'Zoom', zoom), el('label', {}, 'BG', bg));
}

function draw(canvas) {
  const im = F.imgs[F.frame];
  if (!im) return;
  const z = F.zoom, w = im.width * z, h = im.height * z;
  if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  const c = canvas.getContext('2d');
  c.imageSmoothingEnabled = false;
  if (BG[F.bg]) { c.fillStyle = BG[F.bg]; c.fillRect(0, 0, w, h); }
  else { const q = 8; for (let y = 0; y < h; y += q) for (let x = 0; x < w; x += q) { c.fillStyle = ((x + y) / q) % 2 ? '#9aa0ad' : '#7a7f8c'; c.fillRect(x, y, q, q); } }
  c.drawImage(im, 0, 0, w, h);
  document.querySelectorAll('.fthumbs img').forEach((x, i) => x.classList.toggle('cur', i === F.frame));
}

function animate(canvas) {
  clearTimeout(F.tick);
  const loop = () => {
    if (!canvas.isConnected || !F.playing || !F.imgs.length) return;
    draw(canvas);
    const d = F.prev.durations[F.frame] || 100;
    const last = F.frame === F.imgs.length - 1;
    F.tick = setTimeout(() => { F.frame = last ? (F.prev.loop ? 0 : 0) : F.frame + 1; loop(); }, last && !F.prev.loop ? Math.max(d, 600) : d);
  };
  loop();
}

async function refresh(canvas, info, strip) {
  const seq = ++F.seq;
  info.textContent = t('rendering…');
  const r = await api('/api/forge/preview', { body: { builder: F.builder, params: F.params, edits: F.edits } });
  if (seq !== F.seq) return;
  F.prev = r;
  const lb = document.getElementById('forgeLoop');
  if (lb && F.edits.loop == null) lb.checked = !!r.loop;   // per-variant default (e.g. character idle loops, attack does not)
  F.imgs = await Promise.all(r.frames.map(src => new Promise(res => { const i = new Image(); i.onload = () => res(i); i.src = src; })));
  if (F.frame >= F.imgs.length) F.frame = 0;
  const total = r.durations.reduce((a, b) => a + b, 0);
  info.textContent = `${r.size[0]}×${r.size[1]} px · ${r.frames.length} ${t('frames')} · ${total} ms · ~${Math.round(1000 * r.frames.length / total)} fps · ${t('rendered in')} ${r.ms} ms`;
  strip.innerHTML = '';
  F.imgs.forEach((im, i) => strip.append(el('img', { src: im.src, title: `${i + 1}: ${r.durations[i]} ms`, onclick: () => { F.frame = i; draw(canvas); } })));
  if (F.playing) animate(canvas); else draw(canvas);
  if (F.fillSwatches && JSON.stringify(r.base_palette || []) !== F.swatchKey && !document.activeElement?.classList.contains('swatch-in')) F.fillSwatches();
  else document.querySelectorAll('.swatch-in').forEach((inp, i) => { if (r.palette && r.palette[i] && document.activeElement !== inp) inp.value = r.palette[i]; });
}

// builder params whose raw name would clash with the editor's own sections
const PARAM_LABELS = { color: 'Colour scheme' };

function renderControls(box, canvas, info, strip, root) {
  const update = () => { clearTimeout(F.timer); F.timer = setTimeout(() => guard(() => refresh(canvas, info, strip)), 180); };
  const b = F.builders[F.builder];
  const sec = (name, ...kids) => el('div', { class: 'fsec' }, el('h4', {}, name), ...kids);
  // variant params
  const pkids = Object.entries(b.params).map(([k, p]) => {
    if (p.enum) return el('div', { class: 'frow' + (p.enum.length > 4 ? ' stack' : '') }, el('label', {}, PARAM_LABELS[k] || k), el('div', { class: 'chips' }, ...p.enum.map(v => el('button', { class: 'chip' + (F.params[k] === v ? ' on' : ''),
      onclick: (e) => { F.params[k] = v; e.target.closest('.chips').querySelectorAll('.chip').forEach(c => c.classList.toggle('on', c === e.currentTarget)); update(); } }, v))));
    const isSize = k === 'size';
    const lo = p.min ?? (isSize ? 16 : (k === 'frames' ? 2 : 1)), hi = p.max ?? (isSize ? 128 : 16), st = p.step ?? (isSize ? 8 : (p.type === 'float' ? 0.1 : 1));
    return slider(k, F.params[k], lo, hi, st, (v) => { F.params[k] = p.type === 'float' ? v : Math.round(v); update(); }, (v) => (isSize ? `${v} px` : String(v)));
  });
  // timing
  const loopBox = el('input', { type: 'checkbox', id: 'forgeLoop', checked: F.edits.loop ?? b.loop });
  loopBox.onchange = () => { F.edits.loop = loopBox.checked; update(); };
  const timing = sec('Speed & loop', slider('Speed', F.edits.speed, 0.25, 3, 0.05, (v) => { F.edits.speed = v; update(); }, (v) => `${(+v).toFixed(2)}×`),
    el('label', { class: 'frow' }, loopBox, 'Loop'));
  // colours
  const base = F.prev?.base_palette;
  const sw = el('div', { class: 'swatches' });
  const fillSwatches = () => {
    sw.innerHTML = '';
    const map = F.edits.palette_map || {};
    (F.prev?.base_palette || []).forEach((c, i) => {
      const inp = el('input', { type: 'color', class: 'swatch-in', value: map[c] || (F.prev.palette || [])[i] || c, title: c });
      inp.oninput = () => { F.edits.palette_map = { ...(F.edits.palette_map || {}), [c]: inp.value }; F.edits.palette = null; update(); };
      sw.append(inp);
    });
    F.swatchKey = JSON.stringify(F.prev?.base_palette || []);
  };
  F.fillSwatches = fillSwatches;
  const colours = sec('Palette tweaks', el('p', { class: 'small muted' }, 'Fine-tune the finished picture: each swatch is a colour it uses — change one to replace it everywhere. Applied on top of the colour scheme above, and kept when you switch schemes (only colours the new scheme also uses).'), sw,
    slider('Hue', F.edits.hue, -180, 180, 5, (v) => { F.edits.hue = v; update(); }, (v) => `${v}°`),
    slider('Saturation', F.edits.saturation, 0, 2, 0.05, (v) => { F.edits.saturation = v; update(); }, (v) => `${Math.round(v * 100)}%`),
    slider('Brightness', F.edits.brightness, 0.5, 1.5, 0.05, (v) => { F.edits.brightness = v; update(); }, (v) => `${Math.round(v * 100)}%`),
    el('button', { class: 'small', onclick: () => { Object.assign(F.edits, { palette: null, palette_map: null, hue: 0, saturation: 1, brightness: 1 }); renderForge(root); } }, 'Reset colours'));
  // shape
  const oc = el('input', { type: 'color', value: F.edits.outline_color || '#14101e', 'aria-label': 'Outline colour' });
  oc.oninput = () => { F.edits.outline_color = oc.value; update(); };
  const gc = el('input', { type: 'color', value: F.edits.glow_color || '#ffffff', 'aria-label': 'Glow colour' });
  const gAuto = el('input', { type: 'checkbox', checked: !F.edits.glow_color });
  gc.oninput = () => { F.edits.glow_color = gc.value; gAuto.checked = false; update(); };
  gAuto.onchange = () => { F.edits.glow_color = gAuto.checked ? null : gc.value; update(); };
  const flip = el('input', { type: 'checkbox', checked: F.edits.flip });
  flip.onchange = () => { F.edits.flip = flip.checked; update(); };
  const scale = select([1, 2, 3, 4].map(z => [z, z + '×']), F.edits.scale, { 'aria-label': 'Output scale' });
  scale.onchange = () => { F.edits.scale = +scale.value; update(); };
  const shape = sec('Outline & glow',
    slider('Outline', F.edits.outline, 0, 3, 1, (v) => { F.edits.outline = v; update(); }, (v) => `${v} px`),
    el('div', { class: 'frow' }, el('label', {}, 'Outline colour'), oc),
    slider('Glow', F.edits.glow, 0, 4, 1, (v) => { F.edits.glow = v; update(); }, (v) => `${v} px`),
    el('div', { class: 'frow' }, el('label', {}, 'Glow colour'), gc, el('label', { class: 'small' }, gAuto, 'auto')),
    el('label', { class: 'frow' }, flip, 'Flip horizontally'), el('div', { class: 'frow' }, el('label', {}, 'Output scale'), scale));
  // save
  const name = el('input', { value: F.source ? title(F.builder) + ' (edited)' : title(F.builder), 'aria-label': 'Asset name', 'data-no-i18n': '' });
  const out = el('div', {});
  const save = async (andExport) => {
    const job = await api(`/api/projects/${S.project}/procedural`, { body: { builder: F.builder, params: F.params, edits: F.edits, name: name.value } });
    await waitJob(job, async (j) => {
      await refreshProject(); toast('Saved to library');
      root.querySelector('.fgallery')?.replaceWith(galleryPanel(root));
      const aid = j.result.asset_id;
      out.innerHTML = '';
      out.append(el('div', { class: 'row' }, badge('Saved', 'ok'), el('button', { class: 'small', onclick: () => emit('open-asset', aid) }, 'Open in editor')));
      if (andExport) {
        const ej = await api(`/api/projects/${S.project}/export`, { body: { asset_ids: [aid], name: name.value.replace(/[^A-Za-z0-9_-]+/g, '_').toLowerCase() || F.builder, formats: ['frames', 'sheet', 'gif', 'json', 'cocos', 'zip'] } });
        await waitJob(ej, async (x) => {
          const list = await api(`/api/projects/${S.project}/exports`); const e = list.find(z => z.export_id === x.result.export_id) || list[0];
          if (e?.zip) out.append(el('a', { class: 'btn primary', href: exportUrl(S.project, e.export_id, e.zip) }, '⬇ Download ZIP'));
        });
      }
    });
  };
  const saveSec = sec('Save', el('div', { class: 'frow' }, el('label', {}, 'Name'), name),
    S.project ? el('div', { class: 'row' }, el('button', { class: 'primary', onclick: () => guard(() => save(false)) }, 'Save to library'),
      el('button', { onclick: () => guard(() => save(true)) }, 'Save & export')) : el('p', { class: 'small muted' }, 'Create or select a project first.'),
    el('button', { class: 'small ghost', onclick: () => { choose(F.builder); renderForge(root); } }, 'Reset all'), out);
  box.append(el('div', { class: 'card' }, sec('Variant', ...pkids), timing, colours, shape, saveSec));
  // swatches need the first preview
  const wait = setInterval(() => { if (F.prev && F.prev.base_palette) { clearInterval(wait); if (!sw.children.length) fillSwatches(); } if (!box.isConnected) clearInterval(wait); }, 100);
}

function slider(label, value, lo, hi, step, onchange, fmt) {
  const r = el('input', { type: 'range', min: lo, max: hi, step, value, 'aria-label': label });
  const v = el('span', { class: 'fval', 'data-no-i18n': '' }, fmt(value));
  r.oninput = () => { v.textContent = fmt(+r.value); onchange(+r.value); };
  return el('div', { class: 'frow' }, el('label', {}, label), r, v);
}
