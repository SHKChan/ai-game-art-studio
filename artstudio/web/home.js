// Home: three entry points + continue where you left off. Keeps the first screen simple.
import { S, api, el, guard, emit, fileUrl, charUrl, badge } from './core.js';

function master(c) { const m = c?.masters || {}; return m.right || m.east || m.south || m.primary || Object.values(m)[0]; }

export async function renderHome(root, { show, projectForm }) {
  root.innerHTML = '';
  if (!S.project || S.creating) {
    root.append(el('div', { class: 'hero' }, el('h2', {}, 'Welcome'), el('p', { class: 'muted' }, 'Start by creating a project — it keeps characters, animations and exports together.')), projectForm());
    return;
  }
  const entry = (icon, title, text, tab, cta) => el('div', { class: 'entry', onclick: () => show(tab) },
    el('div', { class: 'icon' }, icon), el('h3', {}, title), el('p', { class: 'muted' }, text), el('button', { class: 'primary' }, cta));
  const prov = (id) => S.providers.find(p => p.id === id);
  const gen = el('div', { class: 'row small' }, el('span', { class: 'muted' }, 'AI generators:'),
    ...['codex', 'comfyui'].map(id => { const p = prov(id); const ok = !!p?.status.available;
      return el('span', { class: 'pill ' + (ok ? 'on' : 'off'), title: ok ? '' : (p?.status.reason || '') }, (ok ? '● ' : '○ ') + (id === 'codex' ? 'Codex CLI' : 'ComfyUI') + (p?.status.details?.is_mock ? ' (MOCK)' : '')); }),
    ['codex', 'comfyui'].some(id => prov(id)?.status.available) ? null : el('span', { class: 'muted' }, 'Install the Codex CLI or start ComfyUI to generate character frames.'));
  root.append(el('div', { class: 'entries' },
    entry('🎬', 'Motion Studio', 'Animate a character: upload one image, list the actions you need, and let Codex or your local ComfyUI draw every frame.', 'wizard', 'Start'),
    entry('🔥', 'Pixel Forge', 'Skill effects, items, icons and scenery from the built-in pixel engine — tweak speed, colours, outline and glow live. Works offline.', 'forge', 'Open'),
    entry('📥', 'Asset Import', 'Bring in sprite sheets, GIFs, videos or PNG frames: remove the background, slice and align them.', 'import', 'Open')), gen);
  const chars = S.data.characters;
  if (chars.length) {
    const plans = await Promise.all(chars.slice(0, 12).map(c => api(`/api/projects/${S.project}/characters/${c.id}/plan`).catch(() => null)));
    root.append(el('h3', { class: 'section' }, 'Continue'), el('div', { class: 'cards' }, ...chars.slice(0, 12).map((c, i) => {
      const p = plans[i]; const n = p?.actions.length || 0; const g = p ? p.actions.filter(a => a.asset_id).length : 0; const m = master(c);
      return el('div', { class: 'pick', onclick: () => show('wizard', { cid: c.id, step: !n ? 1 : (g ? 4 : 2) }) },
        el('div', { class: 'thumb checker' }, m ? el('img', { src: charUrl(c, m.file), alt: c.name }) : el('span', { class: 'muted small' }, 'no reference')),
        el('div', { class: 'name', 'data-no-i18n': '' }, c.name), el('div', { class: 'small muted' }, `${g}/${n} actions generated`));
    })));
  }
  const recent = [...S.data.assets].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0)).slice(0, 8);
  if (recent.length) {
    root.append(el('h3', { class: 'section' }, 'Recent assets'), el('div', { class: 'assets' }, ...recent.map(a => {
      const f = a.animation?.frames?.find(x => x.status !== 'rejected');
      return el('div', { class: 'asset', onclick: () => emit('open-asset', a.id) },
        el('div', { class: 'thumb checker' }, f ? el('img', { src: fileUrl(a, f.file), alt: a.name, loading: 'lazy' }) : '—'),
        el('div', { class: 'name', title: a.name, 'data-no-i18n': '' }, a.name), el('div', { class: 'row small' }, badge(a.type, ''), badge(a.status)));
    })));
  }
}
