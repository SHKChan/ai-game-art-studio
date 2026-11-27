import { initI18n, setLang, LANGS, getLang, tError } from './i18n.js';
import { S, api, el, toast, guard, on, emit, fileUrl, badge, fixtureBadge, refreshProject, select } from './core.js';
import { renderAnimation, openAsset } from './anim.js';
import { renderCharacter, renderProcedural, renderImport, renderGenerate, renderExport } from './studios.js';
import { renderWizard } from './wizard.js';
import { renderHome } from './home.js';
import { renderForge } from './forge.js';
import { openSpriteEditor } from './sprite.js';
import { tagChips } from './packs.js';

const RENDER = { home: (r) => renderHome(r, { show: showTab, projectForm }), wizard: renderWizard, forge: renderForge, library: renderLibrary, character: renderCharacter,
  animation: renderAnimation, procedural: renderProcedural, import: renderImport, generate: renderGenerate, export: renderExport };
const ADVANCED = ['animation', 'character', 'generate', 'procedural'];
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
  if (S.libChar && !d.characters.some(c => c.id === S.libChar)) S.libChar = '';
  const charSel = select([['', 'all characters'], ...d.characters.map(c => [c.id, c.name])], S.libChar || '');
  const q = el('input', { placeholder: 'search…' });
  const grid = el('div', { class: 'assets' });
  const chipBox = el('div', {});
  S.libTags = (S.libTags || []).filter(t => d.assets.some(a => (a.tags || []).includes(t)));
  const drawChips = () => {
    const c = {};
    for (const a of d.assets) for (const t of a.tags || []) if (!['pack', 'procedural', 'pixel-art'].includes(t)) c[t] = (c[t] || 0) + 1;
    chipBox.innerHTML = '';
    chipBox.append(tagChips(Object.entries(c).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])), S.libTags,
      (t) => { S.libTags = S.libTags.includes(t) ? S.libTags.filter(x => x !== t) : [...S.libTags, t]; drawChips(); draw(); }, 36));
  };
  const draw = () => {
    grid.innerHTML = '';
    // search words match name / id / tags; selected tag chips must all be present
    const words = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    const list = d.assets.filter(a => (typeSel.value === 'all' || a.type === typeSel.value) && (!charSel.value || a.character_id === charSel.value)
      && S.libTags.every(t => (a.tags || []).includes(t))
      && words.every(w => (a.name + ' ' + a.id + ' ' + (a.tags || []).join(' ')).toLowerCase().includes(w)));
    for (const a of list) {
      const f = a.animation?.frames?.find(x => x.status !== 'rejected');
      grid.append(el('div', { class: 'asset', title: (a.tags || []).join(' '), onclick: () => emit('open-asset', a.id) },
        el('div', { class: 'thumb checker' }, f ? el('img', { src: fileUrl(a, f.file), alt: a.name, loading: 'lazy' }) : '—'),
        el('div', { class: 'name', title: a.name }, a.name),
        el('div', { class: 'row small' }, badge(a.type, ''), badge(a.art_style, ''), badge(a.status), fixtureBadge(a),
          a.animation ? el('span', { class: 'muted' }, `${a.animation.frames.length}f ${a.animation.direction !== 'none' ? a.animation.direction : ''}`) : null,
          a.animation ? el('button', { class: 'small asset-edit', title: 'Edit pixels', onclick: (e) => { e.stopPropagation(); guard(() => openSpriteEditor(a.id, { onClose: () => guard(refreshProject).then(() => renderLibrary(root)) })); } }, '✎') : null)));
    }
    if (!list.length) grid.append(el('p', { class: 'muted' }, 'No assets yet — use Procedural, Import or Generation.'));
  };
  typeSel.onchange = draw; charSel.onchange = () => { S.libChar = charSel.value; draw(); }; q.oninput = draw;
  const imported = (c) => !Object.keys(c.masters || {}).length && d.assets.some(a => a.character_id === c.id && a.animation);
  const chars = el('div', {}, ...d.characters.map(c => imported(c) ? el('div', { class: 'row' },
    // pack / imported characters: the name filters the asset list to their animations
    el('a', { href: '#', 'data-no-i18n': '', onclick: (e) => { e.preventDefault(); charSel.value = c.id; S.libChar = c.id; draw(); } }, c.name),
    badge(c.direction_mode, ''), el('span', { class: 'muted small' }, `${d.assets.filter(a => a.character_id === c.id).length} animations imported`)) : el('div', { class: 'row' },
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
        'Import knight sample'),
      deleteProjectBox(d.project)),
    el('div', { class: 'card' }, el('div', { class: 'row' }, el('h3', {}, 'Assets'), typeSel, charSel, q), chipBox, grid)));
  drawChips(); draw();
}

// Delete = move to <workspace>/_trash/ (recoverable). Typing the name confirms, so one stray click cannot delete.
function deleteProjectBox(project) {
  const box = el('div', { class: 'danger-zone' });
  const open = el('button', { class: 'danger small', onclick: () => {
    box.innerHTML = '';
    const name = el('input', { placeholder: project.name, 'aria-label': 'Type the project name to confirm', 'data-no-i18n': '' });
    const go = el('button', { class: 'danger', disabled: true, onclick: () => guard(async () => {
      const r = await api(`/api/projects/${project.id}`, { method: 'DELETE', body: { confirm: name.value } });
      toast('Project moved to the trash folder');
      console.info('project trash:', r.trash);
      S.project = null; S.asset = null; S.libChar = ''; S.libTags = [];
      await loadProjects(); showTab('home');
    }) }, 'Delete');
    name.oninput = () => { go.disabled = name.value.trim() !== project.name; };
    box.append(el('p', { class: 'small' }, 'Type the project name to confirm. The folder is moved to workspace/_trash and can be restored from there.'),
      el('div', { class: 'row' }, name, go, el('button', { class: 'small', onclick: () => box.replaceWith(deleteProjectBox(project)) }, 'Cancel')));
  } }, 'Delete project…');
  box.append(el('h4', {}, 'Danger zone'), open);
  return box;
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

// Theme: System (follows the OS) / Dark / Light, remembered per browser.
function applyTheme(choice) {
  const sys = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  document.documentElement.dataset.theme = choice === 'system' ? sys : choice;
}
function initTheme() {
  let choice = 'system';
  try { choice = localStorage.getItem('artstudio.theme') || 'system'; } catch (e) { /* storage unavailable */ }
  const sel = document.getElementById('themeSelect');
  for (const [v, l] of [['system', 'System theme'], ['dark', 'Dark'], ['light', 'Light']]) sel.append(el('option', { value: v }, l));
  sel.value = choice;
  applyTheme(choice);
  sel.onchange = () => { try { localStorage.setItem('artstudio.theme', sel.value); } catch (e) { /* ignore */ } applyTheme(sel.value); };
  window.matchMedia?.('(prefers-color-scheme: light)').addEventListener?.('change', () => { if (sel.value === 'system') applyTheme('system'); });
}

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
  initTheme();
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
