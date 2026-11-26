import { initI18n, setLang, LANGS, getLang, tError } from './i18n.js';
import { S, api, el, toast, guard, on, emit, fileUrl, badge, fixtureBadge, refreshProject, select } from './core.js';
import { renderAnimation, openAsset } from './anim.js';
import { renderCharacter, renderProcedural, renderImport, renderGenerate, renderExport } from './studios.js';
import { renderWizard } from './wizard.js';
import { renderHome } from './home.js';

const RENDER = { home: (r) => renderHome(r, { show: showTab, projectForm }), wizard: renderWizard, library: renderLibrary, character: renderCharacter,
  animation: renderAnimation, procedural: renderProcedural, import: renderImport, generate: renderGenerate, export: renderExport };
const ADVANCED = ['animation', 'character', 'generate'];
let current = 'home';

function setMore(open) {
  document.querySelector('.tabs').classList.toggle('show-adv', open);
  const b = document.getElementById('moreBtn');
  b.setAttribute('aria-expanded', String(open)); b.textContent = open ? 'More tools ▾' : 'More tools ▸';
}

export function showTab(name, opts) {
  current = name;
  if (ADVANCED.includes(name)) setMore(true);
  document.querySelectorAll('.tabs button[data-tab]').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.id === 'tab-' + name));
  guard(() => RENDER[name](document.getElementById('tab-' + name), opts));
}
window.studioShowTab = showTab;
on('open-asset', (id) => { S.asset = id; showTab('animation'); });

async function loadProjects(selectId) {
  const projects = await api('/api/projects');
  const sel = document.getElementById('projectSelect');
  sel.innerHTML = '';
  for (const p of projects) sel.append(el('option', { value: p.id }, `${p.name} (${p.counts.assets})`));
  if (!projects.length) { S.project = null; sel.append(el('option', { value: '' }, '— no project —')); }
  else { S.project = selectId || S.project || projects[0].id; sel.value = S.project; }
  await refreshProject();
}

async function loadProviders() {
  S.providers = await api('/api/providers');
  const box = document.getElementById('providerPills');
  box.innerHTML = '';
  for (const p of S.providers) box.append(el('span', { class: 'pill ' + (p.status.available ? 'on' : 'off'),
    title: p.status.available ? JSON.stringify(p.status.details) : p.status.reason }, (p.status.available ? '● ' : '○ ') + p.id +
    (p.status.details?.is_mock ? ' (MOCK)' : '')));
}

function renderLibrary(root) {
  root.innerHTML = '';
  if (!S.project || S.creating) { root.append(projectForm()); return; }
  const d = S.data;
  const typeSel = select(['all', 'animation', 'character_sprite', 'item', 'effect', 'icon', 'tileset', 'environment', 'ui', 'concept', 'other'], 'all');
  const charSel = select([['', 'all characters'], ...d.characters.map(c => [c.id, c.name])], '');
  const q = el('input', { placeholder: 'search…' });
  const grid = el('div', { class: 'assets' });
  const draw = () => {
    grid.innerHTML = '';
    const list = d.assets.filter(a => (typeSel.value === 'all' || a.type === typeSel.value) && (!charSel.value || a.character_id === charSel.value)
      && (!q.value || (a.name + a.id + (a.tags || []).join(' ')).toLowerCase().includes(q.value.toLowerCase())));
    for (const a of list) {
      const f = a.animation?.frames?.find(x => x.status !== 'rejected');
      grid.append(el('div', { class: 'asset', onclick: () => emit('open-asset', a.id) },
        el('div', { class: 'thumb checker' }, f ? el('img', { src: fileUrl(a, f.file), alt: a.name, loading: 'lazy' }) : '—'),
        el('div', { class: 'name', title: a.name }, a.name),
        el('div', { class: 'row small' }, badge(a.type, ''), badge(a.art_style, ''), badge(a.status), fixtureBadge(a),
          a.animation ? el('span', { class: 'muted' }, `${a.animation.frames.length}f ${a.animation.direction !== 'none' ? a.animation.direction : ''}`) : null)));
    }
    if (!list.length) grid.append(el('p', { class: 'muted' }, 'No assets yet — use Procedural, Import or Generation.'));
  };
  [typeSel, charSel].forEach(s => s.onchange = draw); q.oninput = draw;
  const chars = el('div', {}, ...d.characters.map(c => el('div', { class: 'row' },
    el('a', { href: '#', 'data-no-i18n': '', onclick: (e) => { e.preventDefault(); showTab('wizard', { cid: c.id, step: 1 }); } }, c.name),
    el('a', { href: '#', class: 'small', onclick: (e) => { e.preventDefault(); S.character = c.id; showTab('character'); } }, 'details'),
    badge(c.direction_mode, ''), badge(c.art_style, ''), el('span', { class: 'muted small' }, `${Object.keys(c.masters).length}/${c.directions.length} masters`))));
  root.append(el('div', { class: 'grid cols2' },
    el('div', { class: 'card' }, el('h3', { 'data-no-i18n': '' }, d.project.name), el('p', { class: 'muted small', 'data-no-i18n': '' }, `${d.project.game || ''} · ${d.project.default_style} · id ${d.project.id}`),
      el('div', { class: 'row' }, el('label', {}, 'Prompt language', (() => { const s = select([['en', 'English'], ['zh-CN', '中文']], d.project.prompt_language || 'en');
        s.onchange = () => guard(async () => { await api(`/api/projects/${S.project}/settings`, { body: { prompt_language: s.value } }); toast('Saved'); await refreshProject(); }); return s; })())),
      el('h4', {}, 'Characters'), chars,
      el('button', { onclick: () => showTab('wizard', { cid: null }) }, '+ Character'),
      el('h4', {}, 'Samples'),
      el('button', { onclick: () => guard(async () => { const r = await api(`/api/projects/${S.project}/knight-sample`, { body: {} }); toast(`Imported ${r.assets.length} knight animations`); await refreshProject(); renderLibrary(root); }) },
        'Import knight sample')),
    el('div', { class: 'card' }, el('div', { class: 'row' }, el('h3', {}, 'Assets'), typeSel, charSel, q), grid)));
  draw();
}

function newProject() {
  S.creating = true; showTab('home');
}

function projectForm() {
  const name = el('input', { value: 'My RPG', 'aria-label': 'Project name' }), game = el('input', { placeholder: 'game title (optional)' });
  const style = select([['pixel', 'Pixel art'], ['hd', 'HD illustration']], 'pixel');
  return el('div', { class: 'card', id: 'projectForm' }, el('h3', {}, 'New project'),
    el('div', { class: 'form' }, el('label', {}, 'Name'), name, el('label', {}, 'Game'), game, el('label', {}, 'Default style'), style),
    el('div', { class: 'row' }, el('button', { class: 'primary', onclick: () => guard(async () => {
      const p = await api('/api/projects', { body: { name: name.value, game: game.value, default_style: style.value } });
      S.creating = false; await loadProjects(p.id); showTab('home'); }) }, 'Create project'),
      S.project ? el('button', { onclick: () => { S.creating = false; showTab('home'); } }, 'Cancel') : null));
}

async function renderJobs() {
  if (!S.project) return;
  const jobs = await api('/api/jobs?limit=30&project=' + S.project);
  const box = document.getElementById('jobsList');
  box.innerHTML = '';
  for (const j of jobs) {
    const live = ['queued', 'running'].includes(j.status);
    box.append(el('div', { class: 'job' },
      el('div', { class: 'row' }, badge(j.status), el('b', {}, j.label), el('span', { class: 'spacer' }),
        live ? el('button', { class: 'small', onclick: () => guard(() => api(`/api/jobs/${j.id}/cancel`, { body: {} })) }, 'Cancel') : null,
        ['failed', 'cancelled'].includes(j.status) ? el('button', { class: 'small', onclick: () => guard(() => api(`/api/jobs/${j.id}/retry`, { body: {} })) }, 'Retry') : null,
        j.result?.asset_id ? el('button', { class: 'small', onclick: () => emit('open-asset', j.result.asset_id) }, 'Open') : null),
      el('div', { class: 'bar' }, el('i', { style: `width:${Math.round((j.progress || 0) * 100)}%` })),
      el('div', { class: 'muted' }, j.error ? '⚠ ' + tError(j.error_code, j.error) : j.message, j.budget != null ? ` · budget ${j.budget_used}/${j.budget}` : '')));
  }
  if (!jobs.length) box.append(el('div', { class: 'job muted' }, 'No jobs yet.'));
  const anyLive = jobs.some(j => ['queued', 'running'].includes(j.status));
  const dock = document.getElementById('jobsDock');
  const live = jobs.filter(j => ['queued', 'running'].includes(j.status)).length;
  document.getElementById('jobsCount').textContent = live ? `(${live})` : '';
  if (!dock.dataset.pinned) {  // auto: open while something runs, fold away afterwards so it never covers buttons
    clearTimeout(renderJobs._fold);
    if (anyLive) dock.classList.remove('collapsed');
    else renderJobs._fold = setTimeout(() => dock.classList.add('collapsed'), 2500);
  }
  if (anyLive) { clearTimeout(renderJobs._t); renderJobs._t = setTimeout(renderJobs, 700); }
  else if (renderJobs._wasLive) { await refreshProject(); }
  renderJobs._wasLive = anyLive;
}
on('jobs', () => { clearTimeout(renderJobs._t); renderJobs(); });

async function boot() {
  initI18n();
  const ls = document.getElementById('langSelect');
  for (const [k, v] of Object.entries(LANGS)) ls.append(el('option', { value: k }, v));
  ls.value = getLang();
  ls.onchange = () => setLang(ls.value);
  document.querySelectorAll('.tabs button[data-tab]').forEach(b => b.onclick = () => showTab(b.dataset.tab));
  document.getElementById('moreBtn').onclick = () => setMore(!document.querySelector('.tabs').classList.contains('show-adv'));
  document.getElementById('projectSelect').onchange = async (e) => { S.project = e.target.value; S.asset = null; await refreshProject(); showTab(current); renderJobs(); };
  document.getElementById('newProjectBtn').onclick = newProject;
  document.getElementById('themeBtn').onclick = () => { const h = document.documentElement; h.dataset.theme = h.dataset.theme === 'dark' ? 'light' : 'dark'; };
  document.getElementById('jobsToggle').onclick = () => { const d = document.getElementById('jobsDock'); d.classList.toggle('collapsed');
    if (d.classList.contains('collapsed')) delete d.dataset.pinned; else d.dataset.pinned = '1'; };
  S.templates = await api('/api/templates');
  await Promise.all([loadProviders(), loadProjects()]);
  showTab('home');
  renderJobs();
  setInterval(loadProviders, 15000);
}
on('project', () => { if (current === 'library') renderLibrary(document.getElementById('tab-library')); });
window.studioShowTab = showTab;
boot().catch(e => toast(e.message, true));
export { openAsset };
