// Asset packs browser (Asset Import tab): installed third-party packs → filter by English tags → import into the project.
import { S, api, el, toast, guard, select, waitJob, refreshProject } from './core.js';

const P = { packs: null, pack: null, opts: {}, tags: [], q: '', picked: new Set() };

// Clickable tag chips. `active` is the list of selected tags; onToggle(tag) is called on click.
export function tagChips(counts, active, onToggle, limit = 40) {
  const box = el('div', { class: 'chips', 'data-no-i18n': '' });
  const shown = counts.slice(0, limit);
  for (const t of active) if (!shown.some(([x]) => x === t)) shown.unshift([t, 0]);
  for (const [t, n] of shown) box.append(el('button', { class: 'chip' + (active.includes(t) ? ' on' : ''), title: n ? `${n}` : '', onclick: () => onToggle(t) },
    t, n ? el('span', { class: 'n' }, n) : null));
  return box;
}

const qs = (o) => Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');

export async function renderPackBrowser(box) {
  if (!P.packs) P.packs = (await api('/api/packs')).packs;
  if (!P.pack) P.pack = (P.packs.find(p => p.available) || P.packs[0])?.id;
  const pack = P.packs.find(p => p.id === P.pack);
  box.innerHTML = '';
  const packSel = select(P.packs.map(p => [p.id, `${p.title}${p.available ? ` (${p.count})` : ' — not installed'}`]), P.pack, { 'aria-label': 'Asset pack', 'data-no-i18n': '' });
  packSel.onchange = () => { P.pack = packSel.value; P.opts = {}; P.tags = []; P.q = ''; P.picked.clear(); guard(() => renderPackBrowser(box)); };
  const head = el('div', { class: 'row' }, el('h3', {}, 'Asset packs'), packSel);
  box.append(head);
  if (!pack) return;
  box.append(el('p', { class: 'small muted', 'data-no-i18n': '' }, pack.description), el('p', { class: 'small muted' }, el('b', {}, 'Licence: '), el('span', { 'data-no-i18n': '' }, pack.license)));
  if (!pack.available) {
    box.append(el('div', { class: 'warnbox' }, 'Not installed. Put the pack ZIP on this computer and run:'),
      el('pre', { class: 'mono' }, `python scripts/setup_asset_packs.py <pack.zip>\n→ ${pack.path}`));
    return;
  }
  // pack options (tier / variants / shadows)
  const optRow = el('div', { class: 'row' });
  for (const [k, spec] of Object.entries(pack.options || {})) {
    const cur = P.opts[k] ?? spec.default;
    let input;
    if (spec.type === 'boolean') { input = el('input', { type: 'checkbox', checked: !!cur }); input.onchange = () => { P.opts[k] = input.checked; P.picked.clear(); guard(() => renderPackBrowser(box)); }; }
    else { input = select(spec.enum, cur); input.onchange = () => { P.opts[k] = input.value; guard(() => renderPackBrowser(box)); }; }
    optRow.append(el('label', {}, spec.label || k, input));
  }
  const q = el('input', { placeholder: 'search…', value: P.q, 'aria-label': 'Search pack' });
  optRow.append(q);
  box.append(optRow);
  const res = await api(`/api/packs/${P.pack}/items?` + qs({ ...P.opts, tags: P.tags.join(','), q: P.q }));
  const chipBox = el('div', {});
  chipBox.append(el('div', { class: 'small muted' }, 'Tags (click to filter, all selected tags must match):'),
    tagChips(res.tags.filter(([t]) => !['pack', P.pack, 'pixel-art'].includes(t)), P.tags, (t) => {
      P.tags = P.tags.includes(t) ? P.tags.filter(x => x !== t) : [...P.tags, t]; guard(() => renderPackBrowser(box)); }));
  q.onchange = () => { P.q = q.value; guard(() => renderPackBrowser(box)); };
  const grid = el('div', { class: 'assets packgrid' });
  const count = el('span', { class: 'muted small', 'data-no-i18n': '' });
  const upd = () => { count.textContent = `${res.count} / ${res.total} · ${P.picked.size} ✓`; };
  for (const it of res.items) {
    const cb = el('input', { type: 'checkbox', checked: P.picked.has(it.id), 'aria-label': it.name });
    cb.onchange = () => { cb.checked ? P.picked.add(it.id) : P.picked.delete(it.id); upd(); };
    grid.append(el('label', { class: 'asset packitem', title: it.tags.join(' ') + (it.description ? '\n' + it.description : '') },
      el('div', { class: 'thumb checker' }, el('img', { src: `/api/packs/${P.pack}/thumb?` + qs({ item: it.id, ...P.opts }), alt: '', loading: 'lazy' })),
      el('div', { class: 'row small' }, cb, el('span', { class: 'name', 'data-no-i18n': '' }, it.name)),
      el('div', { class: 'small muted', 'data-no-i18n': '' }, `${it.type} · ${it.frames ?? '?'}f`)));
  }
  if (!res.items.length) grid.append(el('p', { class: 'muted' }, 'Nothing matches these tags.'));
  const doImport = (ids) => guard(async () => {
    if (!S.project) throw new Error('Create or select a project first.');
    if (!ids.length) throw new Error('Nothing selected');
    const job = await api(`/api/projects/${S.project}/packs/import`, { body: { pack: P.pack, items: ids, options: P.opts } });
    toast(`Importing ${ids.length} item(s)…`);
    await waitJob(job, async (j) => {
      await refreshProject();
      toast(`Imported ${j.result.imported.length}, skipped ${j.result.skipped.length} (already in project)`);
    });
  });
  upd();
  box.append(chipBox, el('div', { class: 'row' },
    el('button', { class: 'small', onclick: () => { res.items.forEach(i => P.picked.add(i.id)); guard(() => renderPackBrowser(box)); } }, 'select shown'),
    el('button', { class: 'small', onclick: () => { P.picked.clear(); guard(() => renderPackBrowser(box)); } }, 'select none'), count,
    el('span', { class: 'spacer' }),
    el('button', { onclick: () => doImport([...P.picked]) }, 'Import selected'),
    el('button', { class: 'primary', onclick: () => doImport(res.items.map(i => i.id)) }, 'Import all shown')), grid);
}
