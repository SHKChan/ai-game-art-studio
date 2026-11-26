// Sprite editor: pixel-level editing of an animation's frames (full-screen overlay).
// Edits are saved as per-frame patches on top of the processed frames (server: animation.save_frame_edits),
// so re-processing the action keeps them.
import { t, getLang } from './i18n.js';
import { S, api, el, toast, guard, fileUrl } from './core.js';

const TOOLS = [
  ['pixel', '⌖', 'Pixel', 'P', 'Click a pixel to inspect it: change its colour, delete it, or replace that colour everywhere'],
  ['pencil', '✎', 'Pencil', 'B', 'Draw with the current colour'],
  ['eraser', '⌫', 'Eraser', 'E', 'Erase to transparent'],
  ['picker', '◉', 'Picker', 'I', 'Pick a colour from the frame'],
  ['fill', '▨', 'Fill', 'G', 'Fill the connected area (Alt: every pixel of that colour)'],
  ['line', '╱', 'Line', 'L', 'Straight line'],
  ['rect', '▭', 'Rectangle', 'R', 'Rectangle outline (Shift: filled)'],
  ['select', '⬚', 'Select', 'M', 'Select an area, then drag to move it (Alt-drag copies)'],
];
const KEYS = Object.fromEntries(TOOLS.map(x => [x[3].toLowerCase(), x[0]]));
const zh = () => getLang().startsWith('zh');
const L = (en, cn) => (zh() ? cn : en);

let E = null; // editor state (one editor at a time)

// ------------------------------------------------------------------ colour helpers
const hex2 = (n) => n.toString(16).padStart(2, '0');
const toHex = (c) => '#' + hex2(c[0]) + hex2(c[1]) + hex2(c[2]);
const fromHex = (h) => { const m = /^#?([0-9a-f]{6})$/i.exec(h.trim()); if (!m) return null; const v = parseInt(m[1], 16); return [v >> 16 & 255, v >> 8 & 255, v & 255, 255]; };
const same = (a, b) => a[0] === b[0] && a[1] === b[1] && a[2] === b[2] && a[3] === b[3];
const isClear = (c) => c[3] === 0;

function loadImg(src) { return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('image failed to load')); i.src = src + '?v=' + Date.now(); }); }

// ------------------------------------------------------------------ frame data
function frameData(img, w, h) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d'); x.drawImage(img, 0, 0);
  return x.getImageData(0, 0, w, h);
}
function getPx(d, x, y) { const i = (y * d.width + x) * 4; return [d.data[i], d.data[i + 1], d.data[i + 2], d.data[i + 3]]; }
function setPx(d, x, y, c) { if (x < 0 || y < 0 || x >= d.width || y >= d.height) return; const i = (y * d.width + x) * 4; d.data[i] = c[0]; d.data[i + 1] = c[1]; d.data[i + 2] = c[2]; d.data[i + 3] = c[3]; }
function cloneData(d) { return new ImageData(new Uint8ClampedArray(d.data), d.width, d.height); }
function countColour(d, c) { let n = 0; for (let i = 0; i < d.data.length; i += 4) if (d.data[i] === c[0] && d.data[i + 1] === c[1] && d.data[i + 2] === c[2] && d.data[i + 3] === c[3]) n++; return n; }
function toDataURL(d) { const c = document.createElement('canvas'); c.width = d.width; c.height = d.height; c.getContext('2d').putImageData(d, 0, 0); return c.toDataURL('image/png'); }

function paletteOf(frames) {
  const m = new Map();
  for (const d of frames) for (let i = 0; i < d.data.length; i += 4) {
    if (d.data[i + 3] === 0) continue;
    const k = (d.data[i] << 16) | (d.data[i + 1] << 8) | d.data[i + 2];
    m.set(k, (m.get(k) || 0) + 1);
  }
  return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 64).map(([k]) => [k >> 16 & 255, k >> 8 & 255, k & 255, 255]);
}

// ------------------------------------------------------------------ history (per frame snapshots)
function begin() { E.pending = { idx: E.cur, before: cloneData(E.frames[E.cur]) }; }
function commit(label) {
  if (!E.pending) return;
  const p = E.pending; E.pending = null;
  const after = E.frames[p.idx];
  if (p.before.data.every((v, i) => v === after.data[i])) return;
  E.undo.push({ idx: p.idx, before: p.before, after: cloneData(after), label });
  if (E.undo.length > 200) E.undo.shift();
  E.redo = [];
  E.dirty.add(p.idx);
  refreshAll();
}
function undo() { const h = E.undo.pop(); if (!h) return; E.frames[h.idx] = cloneData(h.before); E.redo.push(h); E.dirty.add(h.idx); E.cur = h.idx; refreshAll(); }
function redo() { const h = E.redo.pop(); if (!h) return; E.frames[h.idx] = cloneData(h.after); E.undo.push(h); E.dirty.add(h.idx); E.cur = h.idx; refreshAll(); }
function edit(label, fn) { begin(); fn(E.frames[E.cur]); commit(label); }

// ------------------------------------------------------------------ drawing ops
function brush(d, x, y, c) { const s = E.size, o = Math.floor((s - 1) / 2); for (let j = 0; j < s; j++) for (let i = 0; i < s; i++) setPx(d, x - o + i, y - o + j, c); }
function linePts(x0, y0, x1, y1) {
  const pts = []; const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1; let err = dx + dy;
  for (;;) { pts.push([x0, y0]); if (x0 === x1 && y0 === y1) break; const e2 = 2 * err; if (e2 >= dy) { err += dy; x0 += sx; } if (e2 <= dx) { err += dx; y0 += sy; } }
  return pts;
}
function rectPts(x0, y0, x1, y1, filled) {
  const pts = []; const [l, r] = [Math.min(x0, x1), Math.max(x0, x1)], [tp, b] = [Math.min(y0, y1), Math.max(y0, y1)];
  for (let y = tp; y <= b; y++) for (let x = l; x <= r; x++) if (filled || x === l || x === r || y === tp || y === b) pts.push([x, y]);
  return pts;
}
function flood(d, x, y, c, global) {
  const target = getPx(d, x, y); if (same(target, c)) return 0;
  let n = 0;
  if (global) { for (let yy = 0; yy < d.height; yy++) for (let xx = 0; xx < d.width; xx++) if (same(getPx(d, xx, yy), target)) { setPx(d, xx, yy, c); n++; } return n; }
  const st = [[x, y]];
  while (st.length) {
    const [px, py] = st.pop();
    if (px < 0 || py < 0 || px >= d.width || py >= d.height || !same(getPx(d, px, py), target)) continue;
    setPx(d, px, py, c); n++;
    st.push([px + 1, py], [px - 1, py], [px, py + 1], [px, py - 1]);
  }
  return n;
}
function replaceColour(d, from, to) { let n = 0; for (let i = 0; i < d.data.length; i += 4) if (d.data[i] === from[0] && d.data[i + 1] === from[1] && d.data[i + 2] === from[2] && d.data[i + 3] === from[3]) { d.data[i] = to[0]; d.data[i + 1] = to[1]; d.data[i + 2] = to[2]; d.data[i + 3] = to[3]; n++; } return n; }

// ------------------------------------------------------------------ selection (marquee + floating pixels)
function selNorm(s) { return { x: Math.min(s.x0, s.x1), y: Math.min(s.y0, s.y1), w: Math.abs(s.x1 - s.x0) + 1, h: Math.abs(s.y1 - s.y0) + 1 }; }
function liftSelection(copy) {
  const r = selNorm(E.sel), d = E.frames[E.cur];
  const buf = new ImageData(r.w, r.h);
  begin();
  for (let y = 0; y < r.h; y++) for (let x = 0; x < r.w; x++) {
    const c = getPx(d, r.x + x, r.y + y); setPx(buf, x, y, c);
    if (!copy) setPx(d, r.x + x, r.y + y, [0, 0, 0, 0]);
  }
  E.float = { buf, x: r.x, y: r.y };
}
function dropFloat() {
  if (!E.float) return;
  const { buf, x, y } = E.float, d = E.frames[E.cur];
  for (let j = 0; j < buf.height; j++) for (let i = 0; i < buf.width; i++) { const c = getPx(buf, i, j); if (c[3]) setPx(d, x + i, y + j, c); }
  E.sel = { x0: x, y0: y, x1: x + buf.width - 1, y1: y + buf.height - 1 };
  E.float = null;
  commit('move selection');
}
function flipSel() {
  if (E.float) { const b = E.float.buf, n = new ImageData(b.width, b.height); for (let y = 0; y < b.height; y++) for (let x = 0; x < b.width; x++) setPx(n, b.width - 1 - x, y, getPx(b, x, y)); E.float.buf = n; draw(); return; }
  if (!E.sel) return flipFrame();
  const r = selNorm(E.sel);
  edit('flip selection', (d) => { const tmp = []; for (let y = 0; y < r.h; y++) for (let x = 0; x < r.w; x++) tmp.push(getPx(d, r.x + x, r.y + y)); for (let y = 0; y < r.h; y++) for (let x = 0; x < r.w; x++) setPx(d, r.x + r.w - 1 - x, r.y + y, tmp[y * r.w + x]); });
}
function flipFrame() {
  const px = E.asset.animation.pivot[0];
  edit('mirror frame', (d) => { const src = cloneData(d); for (let y = 0; y < d.height; y++) for (let x = 0; x < d.width; x++) setPx(d, x, y, [0, 0, 0, 0]); for (let y = 0; y < d.height; y++) for (let x = 0; x < d.width; x++) { const c = getPx(src, x, y); if (c[3]) setPx(d, 2 * px - 1 - x, y, c); } });
}
function deleteSel() {
  if (E.float) { E.float = null; commit('delete selection'); return; }
  if (!E.sel) return;
  const r = selNorm(E.sel);
  edit('delete selection', (d) => { for (let y = 0; y < r.h; y++) for (let x = 0; x < r.w; x++) setPx(d, r.x + x, r.y + y, [0, 0, 0, 0]); });
}
function copySel() { if (!E.sel) return; const r = selNorm(E.sel), d = E.frames[E.cur], b = new ImageData(r.w, r.h); for (let y = 0; y < r.h; y++) for (let x = 0; x < r.w; x++) setPx(b, x, y, getPx(d, r.x + x, r.y + y)); E.clip = { buf: b, x: r.x, y: r.y }; toast(L('Copied', '已复制')); }
function pasteClip() { if (!E.clip) return; if (E.float) dropFloat(); begin(); E.float = { buf: cloneData(E.clip.buf), x: E.clip.x, y: E.clip.y }; setTool('select'); draw(); }

// ------------------------------------------------------------------ rendering
function checker(ctx, w, h, s) {
  const dark = document.documentElement.dataset.theme !== 'light';
  const [a, b] = dark ? ['#3b404c', '#33373f'] : ['#e4e6eb', '#d3d6dd'];
  ctx.fillStyle = a; ctx.fillRect(0, 0, w, h); ctx.fillStyle = b;
  for (let y = 0; y < h; y += s) for (let x = ((y / s) % 2) * s; x < w; x += 2 * s) ctx.fillRect(x, y, s, s);
}
function off(d) { const c = document.createElement('canvas'); c.width = d.width; c.height = d.height; c.getContext('2d').putImageData(d, 0, 0); return c; }

function draw() {
  if (!E) return;
  const { w, h } = E, z = E.zoom, cv = E.canvas, ctx = cv.getContext('2d');
  if (cv.width !== w * z || cv.height !== h * z) { cv.width = w * z; cv.height = h * z; }
  ctx.imageSmoothingEnabled = false;
  checker(ctx, cv.width, cv.height, Math.max(8, z * 4));
  if (E.onion && E.frames.length > 1) {
    const prev = E.frames[(E.cur - 1 + E.frames.length) % E.frames.length];
    ctx.globalAlpha = 0.28; ctx.drawImage(off(prev), 0, 0, w * z, h * z);
    if (E.frames.length > 2) { ctx.globalAlpha = 0.14; ctx.drawImage(off(E.frames[(E.cur + 1) % E.frames.length]), 0, 0, w * z, h * z); }
    ctx.globalAlpha = 1;
  }
  ctx.drawImage(off(E.frames[E.cur]), 0, 0, w * z, h * z);
  if (E.float) ctx.drawImage(off(E.float.buf), E.float.x * z, E.float.y * z, E.float.buf.width * z, E.float.buf.height * z);
  if (E.preview) { ctx.fillStyle = E.tool === 'eraser' ? 'rgba(255,255,255,.5)' : toHex(E.color); for (const [x, y] of E.preview) ctx.fillRect(x * z, y * z, z, z); }
  if (E.grid && z >= 6) {
    ctx.strokeStyle = document.documentElement.dataset.theme !== 'light' ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.08)'; ctx.lineWidth = 1; ctx.beginPath();
    for (let x = 0; x <= w; x++) { ctx.moveTo(x * z + .5, 0); ctx.lineTo(x * z + .5, h * z); }
    for (let y = 0; y <= h; y++) { ctx.moveTo(0, y * z + .5); ctx.lineTo(w * z, y * z + .5); }
    ctx.stroke();
  }
  if (E.guides) {
    const [px, py] = E.asset.animation.pivot;
    ctx.strokeStyle = 'rgba(255,90,90,.85)'; ctx.setLineDash([z, z]); ctx.beginPath(); ctx.moveTo(0, py * z + .5); ctx.lineTo(w * z, py * z + .5); ctx.stroke();
    ctx.strokeStyle = 'rgba(90,170,255,.6)'; ctx.beginPath(); ctx.moveTo(px * z + .5, 0); ctx.lineTo(px * z + .5, h * z); ctx.stroke(); ctx.setLineDash([]);
  }
  const box = (x, y, ww, hh, col, dash) => { ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.setLineDash(dash ? [4, 3] : []); ctx.strokeRect(x * z + 1, y * z + 1, ww * z - 2, hh * z - 2); ctx.setLineDash([]); };
  if (E.sel && !E.float) { const r = selNorm(E.sel); box(r.x, r.y, r.w, r.h, '#fff', true); }
  if (E.float) box(E.float.x, E.float.y, E.float.buf.width, E.float.buf.height, '#ffd34d', true);
  if (E.hover && E.tool !== 'pixel') box(E.hover[0], E.hover[1], 1, 1, 'rgba(255,255,255,.7)');
  if (E.cursor) { box(E.cursor[0], E.cursor[1], 1, 1, '#000'); ctx.strokeStyle = '#ffd34d'; ctx.lineWidth = 1; ctx.strokeRect(E.cursor[0] * z - 1.5, E.cursor[1] * z - 1.5, z + 3, z + 3); }
}

function refreshAll() { draw(); renderInspector(); renderFrames(); renderTop(); }

// ------------------------------------------------------------------ pointer
function pos(ev) { const r = E.canvas.getBoundingClientRect(); return [Math.floor((ev.clientX - r.left) / E.zoom), Math.floor((ev.clientY - r.top) / E.zoom)]; }
const inside = ([x, y]) => x >= 0 && y >= 0 && x < E.w && y < E.h;

function onDown(ev) {
  if (ev.button === 1 || (ev.button === 0 && E.space)) { E.pan = { x: ev.clientX, y: ev.clientY, sl: E.stage.scrollLeft, st: E.stage.scrollTop }; return; }
  if (ev.button !== 0) return;
  const p = pos(ev); E.canvas.setPointerCapture(ev.pointerId);
  const d = E.frames[E.cur];
  E.drag = { start: p, last: p, alt: ev.altKey, shift: ev.shiftKey };
  switch (E.tool) {
    case 'pixel': if (inside(p)) { E.cursor = p; renderInspector(); draw(); } E.drag = null; break;
    case 'picker': if (inside(p)) { const c = getPx(d, ...p); if (c[3]) setColor(c); else toast(L('Transparent pixel', '透明像素')); } E.drag = null; break;
    case 'fill': if (inside(p)) edit('fill', (dd) => flood(dd, p[0], p[1], E.color, ev.altKey)); E.drag = null; break;
    case 'pencil': case 'eraser': begin(); brush(d, p[0], p[1], E.tool === 'eraser' ? [0, 0, 0, 0] : E.color); draw(); break;
    case 'line': case 'rect': E.preview = [p]; draw(); break;
    case 'select':
      if (E.float && hit(p, E.float.x, E.float.y, E.float.buf.width, E.float.buf.height)) { E.drag.move = { fx: E.float.x, fy: E.float.y }; break; }
      if (E.float) dropFloat();
      if (E.sel && hit(p, ...Object.values(selNorm(E.sel)))) { liftSelection(ev.altKey); E.drag.move = { fx: E.float.x, fy: E.float.y }; draw(); break; }
      E.sel = { x0: p[0], y0: p[1], x1: p[0], y1: p[1] }; draw(); break;
  }
}
function hit(p, x, y, w, h) { return p[0] >= x && p[1] >= y && p[0] < x + w && p[1] < y + h; }
function onMove(ev) {
  if (E.pan) { E.stage.scrollLeft = E.pan.sl - (ev.clientX - E.pan.x); E.stage.scrollTop = E.pan.st - (ev.clientY - E.pan.y); return; }
  const p = pos(ev);
  E.hover = inside(p) ? p : null;
  renderStatus();
  if (!E.drag) { if (E.tool !== 'pixel') draw(); return; }
  const { start, last } = E.drag;
  const d = E.frames[E.cur];
  if (E.tool === 'pencil' || E.tool === 'eraser') { for (const [x, y] of linePts(last[0], last[1], p[0], p[1])) brush(d, x, y, E.tool === 'eraser' ? [0, 0, 0, 0] : E.color); }
  else if (E.tool === 'line') E.preview = linePts(start[0], start[1], p[0], p[1]);
  else if (E.tool === 'rect') E.preview = rectPts(start[0], start[1], p[0], p[1], ev.shiftKey);
  else if (E.tool === 'select') {
    if (E.drag.move && E.float) { E.float.x = E.drag.move.fx + p[0] - start[0]; E.float.y = E.drag.move.fy + p[1] - start[1]; }
    else if (E.sel) { E.sel.x1 = Math.max(0, Math.min(E.w - 1, p[0])); E.sel.y1 = Math.max(0, Math.min(E.h - 1, p[1])); }
  }
  E.drag.last = p;
  draw();
}
function onUp() {
  if (E.pan) { E.pan = null; return; }
  if (!E.drag) return;
  const tool = E.tool;
  if (tool === 'pencil' || tool === 'eraser') commit(tool);
  else if ((tool === 'line' || tool === 'rect') && E.preview) { const pts = E.preview; E.preview = null; edit(tool, (d) => pts.forEach(([x, y]) => brush(d, x, y, E.color))); }
  else if (tool === 'select' && E.sel && !E.float) { const r = selNorm(E.sel); if (r.w * r.h <= 1 && !E.drag.move) E.sel = null; }
  E.drag = null;
  draw(); renderInspector();
}
function onWheel(ev) {
  if (!ev.ctrlKey && !ev.metaKey && !ev.altKey && Math.abs(ev.deltaY) < 40 && E.stage.scrollHeight > E.stage.clientHeight) return; // normal scroll
  ev.preventDefault();
  setZoom(E.zoom * (ev.deltaY < 0 ? 1.25 : 0.8), ev);
}
function setZoom(z, ev) {
  const old = E.zoom; z = Math.max(1, Math.min(48, Math.round(z)));
  if (z === old) return;
  const st = E.stage, r = st.getBoundingClientRect();
  const cx = ev ? ev.clientX - r.left : st.clientWidth / 2, cy = ev ? ev.clientY - r.top : st.clientHeight / 2;
  const ix = (st.scrollLeft + cx - E.canvas.offsetLeft) / old, iy = (st.scrollTop + cy - E.canvas.offsetTop) / old;
  E.zoom = z; draw();
  st.scrollLeft = ix * z + E.canvas.offsetLeft - cx; st.scrollTop = iy * z + E.canvas.offsetTop - cy;
  E.ui.zoom.textContent = z + '×';
}
function fitZoom() {
  const st = E.stage; const z = Math.max(1, Math.floor(Math.min((st.clientWidth - 40) / E.w, (st.clientHeight - 40) / E.h)));
  E.zoom = 0; setZoom(z);
}

// ------------------------------------------------------------------ keyboard
function onKey(ev) {
  if (!E) return;
  const tag = (ev.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') { if (ev.key === 'Escape') ev.target.blur(); return; }
  const k = ev.key.toLowerCase(), mod = ev.ctrlKey || ev.metaKey;
  if (mod && k === 'z') { ev.preventDefault(); ev.shiftKey ? redo() : undo(); return; }
  if (mod && k === 'y') { ev.preventDefault(); redo(); return; }
  if (mod && k === 's') { ev.preventDefault(); guard(save); return; }
  if (mod && k === 'c') { ev.preventDefault(); copySel(); return; }
  if (mod && k === 'v') { ev.preventDefault(); pasteClip(); return; }
  if (mod && k === 'a') { ev.preventDefault(); setTool('select'); E.sel = { x0: 0, y0: 0, x1: E.w - 1, y1: E.h - 1 }; draw(); return; }
  if (mod) return;
  if (ev.key === ' ') { ev.preventDefault(); if (!ev.repeat) E.space = true; return; }
  const arrows = { arrowleft: [-1, 0], arrowright: [1, 0], arrowup: [0, -1], arrowdown: [0, 1] };
  if (arrows[k]) {
    ev.preventDefault();
    const [dx, dy] = arrows[k].map(v => v * (ev.shiftKey ? 8 : 1));
    if (E.tool === 'select' && (E.float || E.sel)) { if (!E.float) liftSelection(false); E.float.x += dx; E.float.y += dy; draw(); }
    else { const c = E.cursor || [Math.floor(E.w / 2), Math.floor(E.h / 2)]; E.cursor = [Math.max(0, Math.min(E.w - 1, c[0] + dx)), Math.max(0, Math.min(E.h - 1, c[1] + dy))]; if (E.tool !== 'pixel') setTool('pixel'); draw(); renderInspector(); }
    return;
  }
  if (k === 'delete' || k === 'backspace') { ev.preventDefault(); if (E.tool === 'select' && (E.sel || E.float)) deleteSel(); else if (E.cursor) erasePixel(); return; }
  if (k === 'enter') { if (E.float) dropFloat(); else if (E.cursor) paintPixel(E.color); return; }
  if (k === 'escape') {
    if (E.float) dropFloat();
    else if (E.sel || E.preview) { E.sel = null; E.preview = null; }
    else if (E.cursor) { E.cursor = null; renderInspector(); }
    else closeEditor();
    draw(); return;
  }
  if (KEYS[k]) { setTool(KEYS[k]); return; }
  if (k === 'h') { flipSel(); return; }
  if (k === 'o') { E.onion = !E.onion; renderTop(); draw(); return; }
  if (k === 'x') { const c = E.color; setColor(E.color2); E.color2 = c; return; }
  if (k === ',' || k === 'a') { goFrame(E.cur - 1); return; }
  if (k === '.' || k === 'd') { goFrame(E.cur + 1); return; }
  if (k === '+' || k === '=') { setZoom(E.zoom * 1.25); return; }
  if (k === '-') { setZoom(E.zoom * 0.8); return; }
  if (k === '0') { fitZoom(); return; }
  if (k === '[') { E.size = Math.max(1, E.size - 1); renderTools(); return; }
  if (k === ']') { E.size = Math.min(8, E.size + 1); renderTools(); return; }
  if (k === 'p' && ev.shiftKey) { togglePlay(); }
}
function onKeyUp(ev) { if (ev.key === ' ') E.space = false; }

// ------------------------------------------------------------------ single-pixel actions
function paintPixel(c) { const [x, y] = E.cursor; edit('recolour pixel', (d) => setPx(d, x, y, c)); }
function erasePixel() { const [x, y] = E.cursor; edit('delete pixel', (d) => setPx(d, x, y, [0, 0, 0, 0])); }
function replaceAll(from, to, all) {
  if (!all) { edit('replace colour', (d) => replaceColour(d, from, to)); return; }
  let n = 0;
  E.frames.forEach((d, i) => { const before = cloneData(d); const k = replaceColour(d, from, to); if (k) { n += k; E.undo.push({ idx: i, before, after: cloneData(d), label: 'replace colour (all frames)' }); E.dirty.add(i); } });
  E.redo = []; toast(L(`${n} pixels replaced`, `已替换 ${n} 个像素`)); refreshAll();
}

// ------------------------------------------------------------------ panels
function setTool(id) { if (E.float && id !== 'select') dropFloat(); E.tool = id; E.preview = null; renderTools(); draw(); E.canvas.style.cursor = id === 'pixel' ? 'cell' : id === 'select' ? 'crosshair' : 'crosshair'; }
function setColor(c) { E.color = [c[0], c[1], c[2], 255]; renderColour(); renderInspector(); }

function renderTools() {
  const box = E.ui.tools; box.innerHTML = '';
  for (const [id, icon, name, key, tip] of TOOLS) box.append(el('button', { class: 'sed-tool' + (E.tool === id ? ' on' : ''), title: `${t(name)} (${key}) — ${t(tip)}`, 'aria-label': name, onclick: () => setTool(id) },
    el('span', { class: 'ico' }, icon), el('span', { class: 'lbl' }, name)));
  box.append(el('div', { class: 'sed-sep' }),
    el('div', { class: 'sed-size', title: t('Brush size ([ and ])') }, el('span', { class: 'small muted' }, 'Size'),
      ...[1, 2, 3].map(n => el('button', { class: E.size === n ? 'on' : '', onclick: () => { E.size = n; renderTools(); } }, String(n)))),
    el('button', { class: 'sed-tool', title: t('Mirror the whole frame horizontally (H with no selection)'), onclick: flipFrame }, el('span', { class: 'ico' }, '⇋'), el('span', { class: 'lbl' }, 'Mirror')));
}

function renderColour() {
  const box = E.ui.colour; box.innerHTML = '';
  const hexIn = el('input', { value: toHex(E.color), class: 'mono', 'aria-label': 'Colour hex', size: 8, 'data-no-i18n': '' });
  hexIn.onchange = () => { const c = fromHex(hexIn.value); if (c) setColor(c); else hexIn.value = toHex(E.color); };
  const pick = el('input', { type: 'color', value: toHex(E.color), 'aria-label': 'Choose colour' });
  pick.oninput = () => setColor(fromHex(pick.value));
  box.append(el('div', { class: 'sed-cur' },
    el('div', { class: 'sed-sw big', style: `background:${toHex(E.color)}`, title: t('Current colour (X swaps with the second colour)') }),
    el('div', { class: 'sed-sw small2', style: `background:${toHex(E.color2)}`, title: t('Second colour'), onclick: () => { const c = E.color; setColor(E.color2); E.color2 = c; renderColour(); } }),
    pick, hexIn));
  const pal = el('div', { class: 'sed-pal' });
  for (const c of E.palette) pal.append(el('button', { class: 'sed-sw' + (same(c, E.color) ? ' on' : ''), style: `background:${toHex(c)}`, title: toHex(c), 'data-no-i18n': '',
    onclick: () => setColor(c), oncontextmenu: (e) => { e.preventDefault(); E.color2 = c; renderColour(); } }));
  box.append(el('div', { class: 'small muted' }, 'Palette (colours used in this animation)'), pal);
}

function renderInspector() {
  const box = E.ui.inspect; box.innerHTML = '';
  const d = E.frames[E.cur];
  if (!E.cursor) {
    box.append(el('div', { class: 'sed-hint' }, el('b', {}, 'Pixel inspector'), el('p', { class: 'small muted' },
      'Pick the Pixel tool (P) and click any pixel. You can recolour it, delete it, or replace that colour in this frame or the whole animation. Arrow keys move to the next pixel; Enter paints the current colour, Delete removes the pixel.')));
    return;
  }
  const [x, y] = E.cursor, c = getPx(d, x, y), clear = isClear(c);
  const n = clear ? 0 : countColour(d, c);
  const nAll = clear ? 0 : E.frames.reduce((s, f) => s + countColour(f, c), 0);
  box.append(el('div', { class: 'sed-pxhead' },
    el('div', { class: 'sed-sw huge' + (clear ? ' clear' : ''), style: clear ? '' : `background:${toHex(c)}` }),
    el('div', {}, el('div', { class: 'mono', 'data-no-i18n': '' }, `x ${x}, y ${y}`),
      el('div', { class: 'mono big', 'data-no-i18n': '' }, clear ? t('transparent') : toHex(c).toUpperCase()),
      ...(clear ? [] : [el('div', { class: 'small muted', 'data-no-i18n': '' }, L(`${n} px in this frame · ${nAll} in all frames`, `本帧 ${n} 个 · 全部帧 ${nAll} 个`))]))));
  const quick = el('div', { class: 'sed-pal mini' });
  for (const pc of E.palette.slice(0, 24)) quick.append(el('button', { class: 'sed-sw', style: `background:${toHex(pc)}`, title: toHex(pc), 'data-no-i18n': '', onclick: () => { setColor(pc); paintPixel(pc); } }));
  const cpick = el('input', { type: 'color', value: clear ? toHex(E.color) : toHex(c), 'aria-label': 'New colour for this pixel' });
  cpick.onchange = () => { const nc = fromHex(cpick.value); setColor(nc); paintPixel(nc); };
  box.append(
    el('div', { class: 'small muted' }, 'Change this pixel to:'), el('div', { class: 'row' }, cpick, el('button', { onclick: () => paintPixel(E.color), title: t('Enter') }, '■ ', el('span', {}, 'Current colour'))), quick,
    el('div', { class: 'row' }, el('button', { class: 'danger', disabled: clear, onclick: erasePixel, title: 'Delete' }, '✕ ', el('span', {}, 'Delete pixel')),
      el('button', { disabled: clear, onclick: () => setColor(c) }, '◉ ', el('span', {}, 'Use this colour'))),
    ...(clear ? [] : [el('div', { class: 'sed-replace' }, el('div', { class: 'small muted' }, 'Replace this colour with the current colour'),
      el('div', { class: 'row' }, el('span', { class: 'sed-sw', style: `background:${toHex(c)}` }), '→', el('span', { class: 'sed-sw', style: `background:${toHex(E.color)}` }),
        el('button', { class: 'small', disabled: same(c, E.color), onclick: () => replaceAll(c, E.color, false) }, 'This frame'),
        el('button', { class: 'small', disabled: same(c, E.color), onclick: () => replaceAll(c, E.color, true) }, 'All frames')),
      el('button', { class: 'small ghost', onclick: () => replaceAll(c, [0, 0, 0, 0], false) }, 'Remove this colour from the frame'))]));
}

function renderStatus() {
  const h = E.hover; const s = E.ui.status;
  if (!h) { s.textContent = `${E.w}×${E.h}`; return; }
  const c = getPx(E.frames[E.cur], h[0], h[1]);
  s.textContent = `${h[0]}, ${h[1]}  ${isClear(c) ? t('transparent') : toHex(c).toUpperCase()}`;
}

function renderTop() {
  const u = E.ui;
  u.title.textContent = E.asset.name;
  u.undo.disabled = !E.undo.length; u.redo.disabled = !E.redo.length;
  u.save.disabled = !E.dirty.size; u.save.classList.toggle('pulse', E.dirty.size > 0);
  u.dirty.textContent = E.dirty.size ? L(`${E.dirty.size} frame(s) changed`, `${E.dirty.size} 帧有改动`) : L('All saved', '已全部保存');
  u.onion.classList.toggle('on', E.onion); u.grid.classList.toggle('on', E.grid); u.guides.classList.toggle('on', E.guides);
  u.play.textContent = E.playing ? '❚❚' : '▶';
  const stale = E.asset.animation.frames.some(f => f.patch?.stale);
  u.warn.hidden = !stale;
}

function renderFrames() {
  const box = E.ui.frames; box.innerHTML = '';
  const fr = E.asset.animation.frames;
  E.frames.forEach((d, i) => {
    const c = off(d); c.className = 'sed-thumb';
    const f = fr[i];
    box.append(el('div', { class: 'sed-frame' + (i === E.cur ? ' cur' : '') + (f?.status === 'rejected' ? ' rej' : ''), onclick: () => goFrame(i), title: L(`Frame ${i + 1}`, `第 ${i + 1} 帧`) },
      el('div', { class: 'checker sed-fbox' }, c),
      el('div', { class: 'sed-fcap', 'data-no-i18n': '' }, String(i + 1), E.dirty.has(i) ? el('i', { class: 'dot' }) : null, f?.patch ? el('span', { class: 'pt', title: t('has hand edits') }, '✎') : null,
        el('span', { class: 'muted' }, `${f?.duration_ms || 100}ms`))));
  });
  const f = fr[E.cur];
  E.ui.dur.value = f?.duration_ms || 100;
  E.ui.fcount.textContent = L(`Frame ${E.cur + 1} / ${E.frames.length}`, `第 ${E.cur + 1} / ${E.frames.length} 帧`);
  E.ui.clearPatch.disabled = !f?.patch;
}

function goFrame(i) { if (E.float) dropFloat(); E.cur = (i + E.frames.length) % E.frames.length; E.sel = null; refreshAll(); }

function togglePlay() {
  E.playing = !E.playing; renderTop();
  const step = () => { if (!E || !E.playing) return; E.cur = (E.cur + 1) % E.frames.length; draw(); renderFramesLight(); E.timer = setTimeout(step, Math.max(30, E.asset.animation.frames[E.cur]?.duration_ms || 100)); };
  clearTimeout(E.timer); if (E.playing) step(); else refreshAll();
}
function renderFramesLight() { [...E.ui.frames.children].forEach((n, i) => n.classList.toggle('cur', i === E.cur)); E.ui.fcount.textContent = L(`Frame ${E.cur + 1} / ${E.frames.length}`, `第 ${E.cur + 1} / ${E.frames.length} 帧`); }

// ------------------------------------------------------------------ server
const base = () => `/api/projects/${E.asset.project_id}/assets/${E.asset.id}`;
async function save() {
  if (E.float) dropFloat();
  if (!E.dirty.size) return;
  const edits = [...E.dirty].sort((a, b) => a - b).map(i => ({ index: i, image: toDataURL(E.frames[i]) }));
  E.ui.save.disabled = true;
  E.asset = await api(`${base()}/pixels`, { body: { edits } });
  E.dirty.clear();
  const px = E.asset.animation.frames.reduce((s, f) => s + (f.patch?.pixels || 0), 0);
  toast(L(`Saved — ${px} edited pixel(s) kept as a patch layer`, `已保存 — ${px} 个手改像素存为修补层`));
  E.onChange && E.onChange(E.asset);
  refreshAll();
}
async function structural(op, extra = {}) {
  if (E.dirty.size) await save();
  E.asset = await api(`${base()}/frames`, { body: { op, ...extra } });
  await reload(E.cur);
  E.onChange && E.onChange(E.asset);
}
async function reload(cur) {
  const a = E.asset;
  const imgs = await Promise.all(a.animation.frames.map(f => loadImg(fileUrl(a, f.file))));
  E.w = a.animation.canvas[0]; E.h = a.animation.canvas[1];
  E.frames = imgs.map(i => frameData(i, E.w, E.h));
  E.cur = Math.min(cur || 0, E.frames.length - 1);
  E.undo = []; E.redo = []; E.dirty = new Set(); E.sel = null; E.float = null; E.cursor = null;
  E.palette = paletteOf(E.frames);
  if (!E.color) E.color = E.palette[0] || [0, 0, 0, 255];
  if (!E.color2) E.color2 = E.palette[1] || [255, 255, 255, 255];
  renderColour(); refreshAll();
}

// ------------------------------------------------------------------ open / close
export async function openSpriteEditor(assetOrId, opts = {}) {
  if (E) closeEditor(true);
  const a = typeof assetOrId === 'string' ? await api(`/api/projects/${S.project}/assets/${assetOrId}`) : assetOrId;
  if (!a.animation) throw new Error('Only animations can be edited here');
  const ui = {};
  const btn = (label, title, fn, cls = '') => el('button', { class: cls, title, onclick: () => guard(fn) }, label);
  ui.title = el('b', { 'data-no-i18n': '' });
  ui.undo = btn('↶', t('Undo (Ctrl+Z)'), undo); ui.redo = btn('↷', t('Redo (Ctrl+Shift+Z)'), redo);
  ui.dirty = el('span', { class: 'small muted' });
  ui.save = el('button', { class: 'primary', title: t('Save (Ctrl+S)'), onclick: () => guard(save) }, el('span', {}, 'Save'));
  ui.warn = el('span', { class: 'badge warn', title: t('The action was re-cut at a different size after these hand edits — check them.') }, 'hand edits need a check');
  ui.onion = btn('◐ ' + t('Onion skin'), t('Show the previous / next frame faintly (O)'), () => { E.onion = !E.onion; renderTop(); draw(); }, 'chipbtn');
  ui.grid = btn('▦ ' + t('Grid'), t('Pixel grid'), () => { E.grid = !E.grid; renderTop(); draw(); }, 'chipbtn');
  ui.guides = btn('┼ ' + t('Ground'), t('Ground line and pivot'), () => { E.guides = !E.guides; renderTop(); draw(); }, 'chipbtn');
  ui.zoom = el('span', { class: 'mono small sed-zoom', 'data-no-i18n': '' });
  ui.status = el('span', { class: 'mono small muted', 'data-no-i18n': '' });
  ui.tools = el('div', { class: 'sed-tools' });
  ui.colour = el('div', { class: 'sed-card' });
  ui.inspect = el('div', { class: 'sed-card sed-inspect' });
  ui.frames = el('div', { class: 'sed-frames' });
  ui.play = btn('▶', t('Play / pause (Shift+P)'), togglePlay);
  ui.fcount = el('span', { class: 'small', 'data-no-i18n': '' });
  ui.dur = el('input', { type: 'number', min: 10, max: 5000, step: 10, 'aria-label': 'Frame duration (ms)' });
  ui.dur.onchange = () => guard(() => structural('duration', { index: E.cur, duration_ms: Math.max(10, +ui.dur.value || 100) }));
  ui.clearPatch = btn('⟲ ' + t('Undo hand edits of this frame'), t('Back to the processed frame'), async () => {
    if (!confirm(t('Remove all saved hand edits of this frame?'))) return;
    if (E.dirty.size) await save();
    E.asset = await api(`${base()}/pixels/clear`, { body: { index: E.cur } }); await reload(E.cur); E.onChange && E.onChange(E.asset);
  }, 'small ghost');
  const canvas = el('canvas', { class: 'sed-canvas' });
  const stage = el('div', { class: 'sed-stage' }, el('div', { class: 'sed-pad' }, canvas));
  const root = el('div', { class: 'sed', role: 'dialog', 'aria-label': 'Sprite editor' },
    el('div', { class: 'sed-top' }, el('span', { class: 'sed-logo' }, '✎'), el('span', {}, 'Sprite editor'), el('span', { class: 'muted' }, '·'), ui.title, ui.warn,
      el('span', { class: 'spacer' }), ui.onion, ui.grid, ui.guides, el('span', { class: 'sed-vsep' }),
      btn('−', t('Zoom out (-)'), () => setZoom(E.zoom * 0.8)), ui.zoom, btn('+', t('Zoom in (+)'), () => setZoom(E.zoom * 1.25)), btn(t('Fit'), t('Fit to window (0)'), fitZoom),
      el('span', { class: 'sed-vsep' }), ui.undo, ui.redo, ui.dirty, ui.save, btn('✕', t('Close (Esc)'), () => closeEditor(), 'ghost')),
    el('div', { class: 'sed-main' }, ui.tools, el('div', { class: 'sed-center' }, stage, el('div', { class: 'sed-status' }, ui.status, el('span', { class: 'spacer' }),
      el('span', { class: 'small muted' }, 'Space+drag or middle mouse to pan · Ctrl+wheel to zoom'))),
      el('div', { class: 'sed-side' }, ui.inspect, ui.colour,
        el('div', { class: 'sed-card' }, el('b', {}, 'Selection'), el('p', { class: 'small muted' }, 'Select tool (M): drag a box, drag inside it to move, Alt-drag to copy. Ctrl+C / Ctrl+V copy and paste (also between frames), H flips, Delete clears, Enter or Esc places it.'),
          el('div', { class: 'row' }, btn(t('Copy'), 'Ctrl+C', copySel, 'small'), btn(t('Paste'), 'Ctrl+V', pasteClip, 'small'), btn(t('Flip'), 'H', flipSel, 'small'), btn(t('Clear'), 'Delete', deleteSel, 'small'))))),
    el('div', { class: 'sed-bottom' },
      el('div', { class: 'sed-fbar' }, ui.play, ui.fcount, el('label', { class: 'small' }, 'Duration', ui.dur, 'ms'),
        btn('⧉ ' + t('Duplicate frame'), t('Insert a copy of this frame after it'), () => structural('duplicate', { index: E.cur })),
        btn('◀', t('Move frame left'), () => E.cur > 0 && structural('move', { index: E.cur, to: E.cur - 1 }).then(() => goFrame(E.cur - 1))),
        btn('▶', t('Move frame right'), () => E.cur < E.frames.length - 1 && structural('move', { index: E.cur, to: E.cur + 1 }).then(() => goFrame(E.cur + 1))),
        btn('✕ ' + t('Delete frame'), t('Delete this frame'), async () => { if (E.frames.length > 1 && confirm(t('Delete this frame?'))) await structural('delete', { index: E.cur }); }, 'danger small'),
        ui.clearPatch, el('span', { class: 'spacer' }), el('span', { class: 'small muted' }, ', / . previous / next frame')),
      ui.frames));
  E = { asset: a, ui, canvas, stage, root, tool: 'pixel', size: 1, zoom: 8, onion: false, grid: true, guides: true, playing: false,
    undo: [], redo: [], dirty: new Set(), frames: [], cur: opts.frame || 0, onChange: opts.onChange, onClose: opts.onClose, color: null, color2: null };
  canvas.addEventListener('pointerdown', onDown); canvas.addEventListener('pointermove', onMove); canvas.addEventListener('pointerup', onUp);
  canvas.addEventListener('pointerleave', () => { if (E && !E.drag) { E.hover = null; renderStatus(); draw(); } });
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  stage.addEventListener('wheel', onWheel, { passive: false });
  E.keyH = onKey; E.keyU = onKeyUp;
  window.addEventListener('keydown', onKey); window.addEventListener('keyup', onKeyUp);
  E.unload = (e) => { if (E && E.dirty.size) { e.preventDefault(); e.returnValue = ''; } };
  window.addEventListener('beforeunload', E.unload);
  document.body.append(root); document.body.classList.add('sed-open');
  renderTools();
  await reload(opts.frame || 0);
  fitZoom(); setTool('pixel');
  return E;
}

export function closeEditor(force = false) {
  if (!E) return;
  if (!force && E.dirty.size && !confirm(t('You have unsaved pixel edits. Close without saving?'))) return;
  clearTimeout(E.timer);
  window.removeEventListener('keydown', E.keyH); window.removeEventListener('keyup', E.keyU); window.removeEventListener('beforeunload', E.unload);
  E.root.remove(); document.body.classList.remove('sed-open');
  const cb = E.onClose; E = null;
  cb && cb();
}
export const editorState = () => E;
