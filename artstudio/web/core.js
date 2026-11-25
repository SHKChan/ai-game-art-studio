// Shared state + helpers for the studio UI (no framework, no build step).
import { getLang, t, tError } from './i18n.js';
export const S = { project: null, data: null, providers: [], templates: null, workflows: [], jobs: [], asset: null, listeners: {} };

export async function api(path, opts = {}) {
  const init = { method: opts.method || (opts.body ? 'POST' : 'GET'), headers: { 'X-Studio-Lang': getLang() } };
  if (opts.body !== undefined) { init.body = JSON.stringify(opts.body); init.headers['Content-Type'] = 'application/json'; }
  const r = await fetch(path, init);
  const ct = r.headers.get('content-type') || '';
  const data = ct.includes('json') ? await r.json() : await r.blob();
  if (!r.ok) throw new Error((data && data.error) || r.statusText);
  return data;
}

export function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'html') e.innerHTML = v;
    else if (k === 'value') e.value = v;
    else if (k === 'checked') e.checked = !!v;
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat()) if (k !== null && k !== undefined && k !== false) e.append(k instanceof Node ? k : document.createTextNode(String(k)));
  return e;
}

export function toast(msg, err = false) {
  const box = document.getElementById('toast');
  box.textContent = t(String(msg)); box.className = 'show' + (err ? ' err' : '');
  clearTimeout(box._h); box._h = setTimeout(() => (box.className = ''), err ? 6000 : 2500);
}

export async function guard(fn) {
  try { return await fn(); } catch (e) { toast(e.message || String(e), true); console.error(e); }
}

export const on = (ev, fn) => ((S.listeners[ev] ||= []).push(fn));
export const emit = (ev, data) => (S.listeners[ev] || []).forEach(f => f(data));

export function fileUrl(asset, rel) { return `/files/${asset.project_id}/assets/${asset.id}/${rel}`; }
export function charUrl(c, rel) { return `/files/${c.project_id}/characters/${c.id}/${rel}`; }
export function exportUrl(pid, eid, rel) { return `/files/${pid}/exports/${eid}/${rel}`; }

export function badge(text, cls) { return el('span', { class: 'badge ' + (cls || text) }, text); }
export function fixtureBadge(a) { return a?.provider?.is_test_fixture ? badge('TEST FIXTURE', 'fixture') : null; }

export function readFile(file) {
  return new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file); });
}

export function select(options, value, attrs = {}) {
  const s = el('select', attrs);
  for (const o of options) {
    const [v, label] = Array.isArray(o) ? o : [o, o];
    const opt = el('option', { value: v }, label);
    if (String(v) === String(value)) opt.selected = true;
    s.append(opt);
  }
  return s;
}

export function field(label, input) { return [el('label', {}, label), input]; }

export async function waitJob(job, onDone) {
  emit('jobs');
  for (let i = 0; i < 1200; i++) {
    const j = await api('/api/jobs/' + job.id);
    if (['succeeded', 'failed', 'cancelled'].includes(j.status)) {
      emit('jobs');
      if (j.status === 'succeeded') { onDone && onDone(j); } else toast(`${j.label}: ${t(j.status)} — ${tError(j.error_code, j.error || '')}`, true);
      return j;
    }
    await new Promise(r => setTimeout(r, 400));
  }
}

export async function refreshProject() {
  if (!S.project) return;
  S.data = await api('/api/projects/' + S.project);
  emit('project', S.data);
}

export function assetsOfProject(filter = () => true) { return (S.data?.assets || []).filter(filter); }
export const DIRS = ['none', 'right', 'left', 'south', 'east', 'north', 'west', 'south_east', 'south_west', 'north_east', 'north_west'];
