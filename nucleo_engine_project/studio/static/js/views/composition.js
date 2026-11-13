// Vista COMPOSITION — editor visual del documento dark-director/1.
// Solo toca campos conocidos del contrato; cualquier campo x_* o desconocido
// válido permanece intacto en state.doc (nunca se elimina silenciosamente).
import { state, setDoc, markDirty, globalDoc, directionDoc, sections,
         instrumentsDoc, totalBars } from '../state.js';
import { el, $, select, slider, chipsMulti, toast, toastOk } from '../ui.js';

const C = () => state.caps.catalogos;
const FS = () => state.caps.field_specs;

const TYPE_COLORS = {
  intro: '#4f6d8f', verse: '#5b7a5e', pre_chorus: '#8f7a4f', chorus: '#a56a4a',
  bridge: '#7a5b8f', break: '#8f4f5f', outro: '#4f5a6d',
};

export async function render(host) {
  host.innerHTML = '';
  host.append(el('h1', {}, 'Composition'),
    el('p', { class: 'sub' },
      'Documento dark-director/1 rev ' + state.caps.contrato.contract_rev +
      ' · identidad ' + (C().identities.length) + '× accesibilidad ' + (C().accessibilities.length) +
      '× lenguaje ' + (C().languages.length) + ' = ' + C().combinaciones_validas + ' combinaciones válidas'));

  host.append(identidadCard(), globalCard(), timelineCard(), estructuraCard(), instrumentosCard());
}

/* ---------------------------------------------------------------- identidad */
function identidadCard() {
  const d = directionDoc();
  const meta = state.doc.meta = state.doc.meta || {};
  const identity = el('select', { onchange: () => { d.identity = identity.value; touch(); } },
    C().identities.map(i => el('option', { value: i, selected: i === d.identity }, i)));
  const access = el('select', { onchange: () => { d.accessibility = access.value; touch(); } },
    C().accessibilities.map(i => el('option', { value: i, selected: i === d.accessibility }, i)));
  const title = el('input', { type: 'text', value: meta.title || '',
    oninput: () => { meta.title = title.value; state.project.name = title.value || state.project.name; touch(true); } });
  const notes = el('textarea', { rows: 2, placeholder: 'notas de la composición (opcional)',
    oninput: () => { meta.notes = notes.value; touch(true); } });
  notes.value = meta.notes || '';
  return el('div', { class: 'card' }, el('h2', {}, 'Identidad'),
    el('div', { class: 'grid-2' },
      el('div', {}, el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Título'), title)),
      el('div', { class: 'row', style: 'align-items:flex-end' },
        el('label', { class: 'fld', style: 'flex:1' }, el('span', { class: 'lbl' }, 'Identidad (direction.identity)'), identity),
        el('label', { class: 'fld', style: 'flex:1' }, el('span', { class: 'lbl' }, 'Accesibilidad'), access))),
    el('label', { class: 'fld', style: 'margin-top:10px' }, el('span', { class: 'lbl' }, 'Notas'), notes),
    el('div', { class: 'tiny', style: 'margin-top:8px' },
      'Set base de ', el('span', { class: 'mono' }, d.identity || '—'), ': ',
      el('span', { class: 'mono' }, (C().base_sets[d.identity] || []).join(', ')),
      ' — habilitar instrumentos fuera del set puede bloquear la compilación (E114).'));
}

/* ------------------------------------------------------------------ global */
function globalCard() {
  const g = globalDoc();
  const bpm = el('input', { type: 'number', min: FS().bpm.min, max: FS().bpm.max,
    value: g.bpm ?? 86, oninput: () => { g.bpm = parseInt(bpm.value) || 0; touch(); } });
  const seed = el('input', { type: 'number', step: 1, placeholder: 'p. ej. 2026',
    value: g.seed ?? '', oninput: () => { g.seed = seed.value === '' ? undefined : parseInt(seed.value); touch(true); } });
  const humanize = el('input', { type: 'number', min: 0, max: 1, step: 0.05,
    value: g.humanize ?? '', placeholder: '—',
    oninput: () => { g.humanize = humanize.value === '' ? undefined : parseFloat(humanize.value); touch(true); } });
  const vcap = el('input', { type: 'number', min: 1, max: 127,
    value: g.velocity_cap ?? '', placeholder: '—',
    oninput: () => { g.velocity_cap = vcap.value === '' ? undefined : parseInt(vcap.value); touch(true); } });
  return el('div', { class: 'card' }, el('h2', {}, 'Global'),
    el('div', { class: 'grid-3' },
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, `BPM (${FS().bpm.min}–${FS().bpm.max})`), bpm),
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Seed (global.seed)'), seed),
      el('div', { class: 'row', style: 'align-items:flex-end' },
        el('label', { class: 'fld', style: 'flex:1' }, el('span', { class: 'lbl' }, 'Humanize 0–1 (opcional)'), humanize),
        el('label', { class: 'fld', style: 'flex:1' }, el('span', { class: 'lbl' }, 'Velocity cap (opcional)'), vcap))),
    el('div', { class: 'tiny', style: 'margin-top:8px' },
      'Duración total: ', el('span', { class: 'mono', id: 'total-bars' }, String(totalBars())),
      ' compases · la seed vacía usa la que indique Generation.'));
}

/* ---------------------------------------------------------------- timeline */
function timelineCard() {
  const card = el('div', { class: 'card' }, el('h2', {}, 'Línea temporal'),
    el('div', { class: 'tiny muted', style: 'margin-bottom:10px' },
      'Ancho proporcional a los compases de cada sección. Pulsa una sección para editarla abajo.'));
  const tl = el('div', { class: 'timeline', id: 'tl' });
  card.append(tl);
  card.refresh = () => {
    tl.innerHTML = '';
    const secs = sections();
    const total = Math.max(totalBars(), 1);
    for (const s of secs) {
      const bars = parseInt(s.bars) || 0;
      const seg = el('div', {
        class: 'tl-seg' + (s.final ? ' tl-final' : ''),
        style: `flex:${bars}; background:${TYPE_COLORS[s.type] || '#55606e'}`,
        title: `${s.id} · ${s.type} · ${bars} compases · drums ${s.drums || 'default'}`
          + (s.final ? ' · FINAL' : ''),
        onclick: () => {
          const node = $(`[data-sec="${s.id}"]`);
          if (node) { node.classList.add('open'); node.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
        },
      }, el('div', { class: 'tl-id' }, s.id || '·'),
         el('div', { class: 'tl-bars' }, `${s.type} · ${bars}b`));
      tl.append(seg);
    }
  };
  card.refresh();
  return card;
}

export function refreshTimeline() {
  const tl = $('#tl')?.closest('.card');
  if (tl && tl.refresh) tl.refresh();
  const tb = $('#total-bars');
  if (tb) tb.textContent = String(totalBars());
}

/* --------------------------------------------------------------- estructura */
function estructuraCard() {
  const card = el('div', { class: 'card' },
    el('div', { class: 'spread' }, el('h2', {}, 'Structure (mínimo 2 secciones, ids únicos)'),
      el('button', { class: 'btn sm', onclick: () => { addSection(); } }, '+ Añadir sección')),
    el('div', { id: 'sec-list' }));
  card.refresh = () => {
    const list = $('#sec-list', card);
    list.innerHTML = '';
    const secs = sections();
    secs.forEach((s, i) => list.append(sectionItem(s, i, card)));
    if (!secs.length) list.append(el('div', { class: 'empty' }, 'Sin secciones — añade al menos dos.'));
  };
  card.refresh();
  return card;
}

function touch(refresh = false) {
  markDirty(true);
  if (refresh) refreshTimeline();
}

function addSection(afterIdx = null) {
  const secs = sections();
  const usedTypes = new Set(secs.map(s => s.type));
  const type = C().section_types.find(t => !usedTypes.has(t)) || 'verse';
  let base = type, n = 1;
  const usedIds = new Set(secs.map(s => s.id));
  while (usedIds.has(`${base}_${n}`)) n++;
  const s = { id: `${base}_${n}`, type, bars: 8, energy: 0.5, tension: 0.4, density: 0.5,
              focus: [], drums: 'groove' };
  const idx = afterIdx === null ? secs.length : afterIdx + 1;
  secs.splice(idx, 0, s);
  touch(true);
  const card = $('#sec-list').closest('.card');
  card.refresh();
}

function sectionItem(s, i, card) {
  const item = el('div', { class: 'sec-item open', 'data-sec': s.id });

  const head = el('div', { class: 'sec-head', onclick: (e) => {
    if (e.target.closest('button, input, select')) return;
    item.classList.toggle('open');
  } },
    el('span', { class: 'sec-num' }, String(i + 1).padStart(2, '0')),
    el('span', { class: 'sec-name' }, s.id || '·'),
    el('span', { class: 'sec-meta' }, `${s.type} · ${s.bars}b · drums:${s.drums || '—'}${s.final ? ' · FINAL' : ''}`),
    el('span', { class: 'sec-caret' }, '▸'));

  const body = el('div', { class: 'sec-body' });

  // fila 1: id, tipo, compases, drums, final
  const idInp = el('input', { type: 'text', value: s.id || '', oninput: () => {
    const old = s.id; s.id = idInp.value.trim(); fixRefs(old, s.id); touch(true);
    item.setAttribute('data-sec', s.id);
    $('.sec-name', item).textContent = s.id;
  } });
  const typeSel = select(s.type, C().section_types, { onchange: () => { s.type = typeSel.value; touch(true);
    $('.sec-meta', item).textContent = `${s.type} · ${s.bars}b · drums:${s.drums || '—'}${s.final ? ' · FINAL' : ''}`; } });
  const barsInp = el('input', { type: 'number', min: FS().bars.min, max: FS().bars.max, value: s.bars ?? 8,
    oninput: () => { s.bars = parseInt(barsInp.value) || 1; touch(true);
      $('.sec-meta', item).textContent = `${s.type} · ${s.bars}b · drums:${s.drums || '—'}${s.final ? ' · FINAL' : ''}`; } });
  const drumsSel = select(s.drums || '', [{ v: '', label: 'default' }, ...C().drums_ladder],
    { onchange: () => { s.drums = drumsSel.value || undefined; touch(true); } });
  const finalChk = el('input', { type: 'checkbox', checked: !!s.final,
    onchange: () => { if (finalChk.checked) sections().forEach(x => { delete x.final; });
      if (finalChk.checked) s.final = true; else delete s.final;
      markDirty(true); refreshTimeline(); card.refresh(); } });

  // sliders
  const en = slider('Energy', s.energy, { oninput: v => { s.energy = v; touch(); } });
  const te = slider('Tension', s.tension, { oninput: v => { s.tension = v; touch(); } });
  const de = slider('Density', s.density, { oninput: v => { s.density = v; touch(); } });

  // focus / active
  const focusWrap = chipsMulti(s.focus, C().instruments, v => { s.focus = v.length ? v : undefined; touch(); });
  const activeWrap = chipsMulti(s.active, C().instruments, v => { s.active = v.length ? v : undefined; touch(); });

  // avanzado: chords, chord_bars, resolution, loop_bars (campos reales del contrato)
  const chordsInp = el('input', { type: 'text', placeholder: 'p. ej. Dm9, Bbmaj7, Fmaj9 (GUIDED)',
    value: (s.chords || []).join(', '),
    oninput: () => { const v = chordsInp.value.split(',').map(x => x.trim()).filter(Boolean);
      s.chords = v.length ? v : undefined; touch(); } });
  const cbars = el('input', { type: 'number', min: 1, max: 8, value: s.chord_bars ?? '', placeholder: '—',
    oninput: () => { s.chord_bars = cbars.value === '' ? undefined : parseInt(cbars.value); touch(true); } });
  const resSel = select(s.resolution || '', [{ v: '', label: 'default' }, ...C().resolutions],
    { onchange: () => { s.resolution = resSel.value || undefined; touch(); } });
  const lbars = el('input', { type: 'number', min: 1, max: 32, value: s.loop_bars ?? '', placeholder: '—',
    oninput: () => { s.loop_bars = lbars.value === '' ? undefined : parseInt(lbars.value); touch(true); } });

  const secs = sections();
  body.append(
    el('div', { class: 'grid-3' },
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Id (único)'), idInp),
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Tipo'), typeSel),
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Compases'), barsInp)),
    el('div', { style: 'margin-top:10px' }, en, te, de),
    el('div', { style: 'margin-top:8px' },
      el('span', { class: 'lbl' }, 'Focus (instrumentos protagonistas)'),
      focusWrap),
    el('div', { style: 'margin-top:10px' },
      el('span', { class: 'lbl' }, 'Active (solo suenan estos; ignora el resto en la sección)'),
      activeWrap,
      el('div', { class: 'tiny' }, 'W406: focus/active sobre instrumentos que no suenan se ignora.')),
    el('div', { class: 'row', style: 'margin-top:12px; align-items:flex-end' },
      el('label', { class: 'fld', style: 'flex:2' }, el('span', { class: 'lbl' }, 'Drums'), drumsSel),
      el('label', { class: 'fld', style: 'flex:1' }, el('span', { class: 'lbl' }, 'Sección final'),
        el('label', { class: 'row', style: 'gap:8px' }, finalChk, el('span', { class: 'tiny' }, 'final: true')))),
    el('details', { class: 'adv' },
      el('summary', {}, 'Avanzado de la sección (acordes propios, resolución, loop)'),
      el('div', { class: 'grid-2' },
        el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Acordes (section.chords — modo GUIDED)'), chordsInp),
        el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'chord_bars 1–8'), cbars)),
      el('div', { class: 'grid-2', style: 'margin-top:8px' },
        el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Resolución'), resSel),
        el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'loop_bars 1–32'), lbars)),
      el('div', { class: 'tiny', style: 'margin-top:6px' },
        'chords aquí tienen precedencia sobre harmony.progressions (id antes que type).')),
  );

  head.append(el('div', { class: 'row', style: 'gap:4px; margin-left:auto' },
    el('button', { class: 'btn icon ghost', title: 'Subir', onclick: (e) => { e.stopPropagation();
      if (i > 0) { [secs[i - 1], secs[i]] = [secs[i], secs[i - 1]]; markDirty(true); refreshTimeline(); card.refresh(); } } }, '↑'),
    el('button', { class: 'btn icon ghost', title: 'Bajar', onclick: (e) => { e.stopPropagation();
      if (i < secs.length - 1) { [secs[i + 1], secs[i]] = [secs[i], secs[i + 1]]; markDirty(true); refreshTimeline(); card.refresh(); } } }, '↓'),
    el('button', { class: 'btn icon ghost', title: 'Duplicar sección', onclick: (e) => { e.stopPropagation();
      const copy = JSON.parse(JSON.stringify(s));
      let n = 2; const base = copy.id.replace(/_\d+$/, '');
      const usedIds = new Set(secs.map(x => x.id));
      while (usedIds.has(copy.id.replace(/_\d+$/, '') + '_' + n)) n++;
      copy.id = base + '_' + n;
      secs.splice(i + 1, 0, copy); markDirty(true); refreshTimeline(); card.refresh(); } }, '⧉'),
    el('button', { class: 'btn icon danger ghost', title: 'Eliminar sección', onclick: (e) => { e.stopPropagation();
      if (secs.length <= 1) { toast('Debe existir al menos una sección (el contrato exige ≥ 2)', 'err'); return; }
      secs.splice(i, 1); markDirty(true); refreshTimeline(); card.refresh(); } }, '✕'),
  ));

  item.append(head, body);
  return item;
}

function fixRefs(oldId, newId) {
  if (!oldId || !newId || oldId === newId) return;
  const h = state.doc.harmony;
  if (h && h.progressions && oldId in h.progressions) {
    h.progressions[newId] = h.progressions[oldId];
    if (newId !== oldId) delete h.progressions[oldId];
  }
  const dev = state.doc.development || {};
  if (dev.melody && dev.melody.phrases && oldId in dev.melody.phrases) {
    dev.melody.phrases[newId] = dev.melody.phrases[oldId];
    if (newId !== oldId) delete dev.melody.phrases[oldId];
  }
  markDirty(true);
}

/* ------------------------------------------------------------- instrumentos */
function instrumentosCard() {
  const inst = instrumentsDoc();
  const card = el('div', { class: 'card' }, el('h2', {}, 'Instruments'),
    el('div', { class: 'tiny muted', style: 'margin-bottom:10px' },
      'Catálogo cerrado de 8 instrumentos. Vacío = la receta N1 de la identidad decide.'));
  for (const iid of C().instruments) {
    const cfg = inst[iid] = inst[iid] && typeof inst[iid] === 'object' ? inst[iid] : {};
    const enabled = el('input', { type: 'checkbox', checked: !!cfg.enabled,
      onchange: () => { if (enabled.checked) cfg.enabled = true; else delete cfg.enabled; touch(); } });
    const reg = cfg.register || [];
    const lo = el('input', { type: 'number', value: reg[0] ?? '', placeholder: '—', style: 'width:70px',
      oninput: () => setReg() });
    const hi = el('input', { type: 'number', value: reg[1] ?? '', placeholder: '—', style: 'width:70px',
      oninput: () => setReg() });
    const setReg = () => {
      if (lo.value === '' && hi.value === '') delete cfg.register;
      else cfg.register = [parseInt(lo.value) || 0, parseInt(hi.value) || 127];
      touch();
    };
    const den = slider('Density', cfg.density, { oninput: v => { cfg.density = v; touch(); } });
    const mixv = cfg.mix || {};
    const mkMix = (k, min, max) => {
      const inp = el('input', { type: 'number', min, max, value: mixv[k] ?? '',
        placeholder: '—', style: 'width:76px' });
      inp.addEventListener('input', () => {
        cfg.mix = cfg.mix || {};
        if (inp.value === '') delete cfg.mix[k];
        else cfg.mix[k] = parseFloat(inp.value);
        if (!Object.keys(cfg.mix).length) delete cfg.mix;
        touch();
      });
      return inp;
    };
    card.append(el('div', { class: 'sec-item', style: 'padding:12px 14px; margin-bottom:8px' },
      el('div', { class: 'row' },
        el('label', { class: 'row', style: 'gap:8px; width:170px' }, enabled,
          el('span', { class: 'mono', style: 'font-size:12.5px' }, iid)),
        el('span', { class: 'lbl', style: 'margin:0' }, 'register'),
        lo, el('span', { class: 'tiny' }, '–'), hi,
        el('div', { style: 'flex:1; min-width:220px' }, den)),
      el('details', { class: 'adv' }, el('summary', {}, 'mix (volume · pan · reverb · chorus · brightness)'),
        el('div', { class: 'row' },
          mkMix('volume', 0, 127), mkMix('pan', -64, 63), mkMix('reverb', 0, 127),
          mkMix('chorus', 0, 127), mkMix('brightness', 0, 127)))));
  }
  return card;
}
