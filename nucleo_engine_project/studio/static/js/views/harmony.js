// Vista HARMONY — los dos modos reales + biblioteca Fase 7 (opcional).
//
//  · NATIVE HARMONY: sin progresiones explícitas → la receta N1 de la
//    identidad decide (precedencia del motor, no se toca nada).
//  · GUIDED HARMONY: harmony.progressions (clave = id o type de sección) y/o
//    chords por sección. El compilador resuelve id > type.
//  · Fase 7 (familiaridad): va en la CONFIG DE PRODUCCIÓN (como --harmony del
//    CLI), es opcional y nunca activa por defecto.
import { state, setDoc, harmonyDoc, sections, harmonyMode, production, markDirty } from '../state.js';
import { el, $, select, toast, toastErr, toastOk, confirmDialog } from '../ui.js';
import { API } from '../api.js';

const C = () => state.caps.catalogos;
const FS = () => state.caps.field_specs;

export async function render(host) {
  host.innerHTML = '';
  host.append(el('h1', {}, 'Harmony'),
    el('p', { class: 'sub' }, 'Modo nativo (receta N1) o guiado (progresiones explícitas). La biblioteca de familiaridad Fase 7 es una opción adicional, nunca un valor predeterminado.'));

  host.append(modeCard());
  host.append(baseCard());

  if (harmonyMode() === 'guided') host.append(progressionsCard());
  host.append(fase7Card());
}

/* -------------------------------------------------------------------- modo */
function modeCard() {
  const mode = harmonyMode();
  const wrap = el('div', { class: 'harmony-mode' });
  const native = el('div', { class: 'mode-card' + (mode === 'native' ? ' sel' : '') },
    el('h3', {}, 'NATIVE HARMONY'),
    el('p', {}, 'El sistema usa su receta armónica nativa N1 de la identidad. No se insertan progresiones artificiales: las decide el motor.'));
  const guided = el('div', { class: 'mode-card' + (mode === 'guided' ? ' sel' : '') },
    el('h3', {}, 'GUIDED HARMONY'),
    el('p', {}, 'Introduces progresiones y las asignas a secciones (harmony.progressions con clave id o type, y/o chords por sección). Precedencia real: chords > progressions.id > progressions.type.'));

  native.onclick = async () => {
    if (harmonyMode() === 'native') return;
    const ok = await confirmDialog('Volver a NATIVE HARMONY',
      'Se eliminarán las progresiones explícitas (harmony.progressions y chords por sección). ¿Continuar?', 'Volver a nativo', true);
    if (!ok) return;
    delete state.doc.harmony.progressions;
    sections().forEach(s => { delete s.chords; });
    markDirty(true);
    render($('#view'));
    toastOk('Modo nativo: la receta N1 decide la armonía');
  };
  guided.onclick = () => {
    if (harmonyMode() === 'guided') return;
    harmonyDoc().progressions = harmonyDoc().progressions || {};
    markDirty(true);
    render($('#view'));
  };
  wrap.append(native, guided);
  return el('div', { class: 'card' }, el('h2', {}, 'Modo armónico'), wrap);
}

/* ------------------------------------------------------------------- base */
function baseCard() {
  const h = harmonyDoc();
  const key = el('input', { type: 'text', value: h.key || '', placeholder: 'p. ej. D minor',
    oninput: () => { h.key = key.value; markDirty(true); } });
  const lang = select(h.language || '', C().languages, { onchange: () => { h.language = lang.value; markDirty(true); } });
  const res = select(h.resolution || '', [{ v: '', label: 'default del lenguaje' }, ...C().resolutions],
    { onchange: () => { h.resolution = res.value || undefined; markDirty(true); } });
  const hrb = el('input', { type: 'number', min: FS().harmonic_rhythm_bars.min, max: FS().harmonic_rhythm_bars.max,
    value: h.harmonic_rhythm_bars ?? 1,
    oninput: () => { h.harmonic_rhythm_bars = parseInt(hrb.value) || 1; markDirty(true); } });
  const defRes = { pop_dream_pop: 'tonal', hybrid: 'modal', experimental: 'chromatic' }[h.language] || '—';
  return el('div', { class: 'card' }, el('h2', {}, 'Parámetros armónicos (ambos modos)'),
    el('div', { class: 'grid-3' },
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Tonalidad (harmony.key) *'), key),
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Lenguaje armónico *'), lang),
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, `Resolución (default: ${defRes})`), res)),
    el('div', { style: 'margin-top:10px; max-width:260px' },
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Ritmo armónico (1–8 compases)'), hrb)),
    el('div', { class: 'tiny', style: 'margin-top:8px' },
      '* campos requeridos por el contrato (E103). Acordes fuera del vocabulario del lenguaje se respetan con aviso W414.'));
}

/* ----------------------------------------------------------- progressions */
function progressionsCard() {
  const h = harmonyDoc();
  h.progressions = h.progressions && typeof h.progressions === 'object' ? h.progressions : {};
  const card = el('div', { class: 'card' }, el('h2', {}, 'Progresiones guiadas'),
    el('div', { class: 'tiny muted', style: 'margin-bottom:10px' },
      'Clave = id de sección (más específico) o type de sección. Ejemplo del golden: verse → Dm9, Bbmaj7, Fmaj9, C7sus4.'));

  const list = el('div');
  const rebuild = () => {
    list.innerHTML = '';
    const keys = Object.keys(h.progressions);
    if (!keys.length) list.append(el('div', { class: 'empty' },
      'Sin progresiones. Añade una clave (id o type) y sus acordes.'));
    const opts = [
      ...C().section_types.map(t => ({ v: t, label: 'type: ' + t })),
      ...sections().map(s => ({ v: s.id, label: 'id: ' + s.id })),
    ].filter(o => !keys.includes(o.v));
    for (const k of keys) {
      const chordsInp = el('input', { type: 'text', value: (h.progressions[k] || []).join(', '),
        oninput: () => {
          h.progressions[k] = chordsInp.value.split(',').map(x => x.trim()).filter(Boolean);
          markDirty(true);
        } });
      list.append(el('div', { class: 'row', style: 'align-items:flex-end; margin-bottom:8px' },
        el('div', { style: 'width:220px' }, el('span', { class: 'lbl' }, 'Clave'), el('div', { class: 'chip on' }, k)),
        el('label', { class: 'fld', style: 'flex:1' }, el('span', { class: 'lbl' }, 'Acordes (separados por coma)'), chordsInp),
        el('button', { class: 'btn sm danger ghost', onclick: () => {
          delete h.progressions[k]; markDirty(true); rebuild();
        } }, '✕')));
    }
    const addKey = select('', [{ v: '', label: '— añadir clave —' }, ...opts],
      { onchange: () => {
        if (!addKey.value) return;
        h.progressions[addKey.value] = h.progressions[addKey.value] || [];
        markDirty(true); rebuild();
      } });
    if (opts.length) list.append(el('div', { style: 'max-width:300px; margin-top:6px' }, addKey));
  };
  rebuild();
  card.append(list);
  return card;
}

/* -------------------------------------------------------------- fase 7 */
function fase7Card() {
  const p = production();
  const har = p.harmony && typeof p.harmony === 'object' ? p.harmony : null;
  const on = !!har;

  const sw = el('input', { type: 'checkbox', checked: on, onchange: () => {
    p.harmony = sw.checked ? { keyword: 'familiarity_auto' } : null;
    markDirty(true);
    render($('#view'));
  } });

  const card = el('div', { class: 'card' },
    el('div', { class: 'spread' },
      el('div', {},
        el('h2', {}, 'Biblioteca de familiaridad (Fase 7) — opcional'),
        el('div', { class: 'tiny muted' },
          'Se aplica en la generación (equivalente a --harmony/--harmony-id del CLI). La precedencia entre receta N1, progresiones guiadas y biblioteca la decide el motor, nunca esta interfaz.')),
      el('label', { class: 'row', style: 'gap:8px' }, sw,
        el('span', { class: 'badge' + (on ? ' acc' : '') }, on ? 'ACTIVA' : 'INACTIVA'))));

  if (!on) return card;

  const lib = state.caps.biblioteca_fase7 || [];
  const mode = har.keyword ? 'keyword' : 'id';
  const modeSel = select(mode, [{ v: 'keyword', label: 'Por keyword' }, { v: 'id', label: 'Progresión concreta (id)' }],
    { onchange: () => {
      if (modeSel.value === 'keyword') p.harmony = { keyword: 'familiarity_auto' };
      else p.harmony = { id: (lib[0] && lib[0].id) || '' };
      markDirty(true); render($('#view'));
    } });

  let picker;
  if (mode === 'keyword') {
    picker = select(har.keyword, state.caps.harmony_keywords, { onchange: () => {
      p.harmony = { keyword: picker.value, ...(har.variacion ? { variacion: har.variacion } : {}),
        ...(har.seed != null ? { seed: har.seed } : {}) };
      markDirty(true);
      info.textContent = describeKeyword(picker.value);
    } });
  } else {
    picker = select(har.id, lib.map(e => ({ v: e.id, label: `${e.id} — ${e.nombre}` })),
      { onchange: () => {
        p.harmony = { id: picker.value, ...(har.variacion ? { variacion: har.variacion } : {}),
          ...(har.seed != null ? { seed: har.seed } : {}) };
        markDirty(true);
        const e = lib.find(x => x.id === picker.value);
        info.textContent = e ? `${e.funcion} · keywords: ${e.keywords.join(', ')}` : '';
      } });
  }

  const vari = select(har.variacion || 'subtle',
    [{ v: '', label: 'default (subtle)' }, ...FS().harmony_variaciones.map(v => ({ v, label: v }))],
    { onchange: () => { if (vari.value) p.harmony.variacion = vari.value; else delete p.harmony.variacion; markDirty(true); } });
  const hseed = el('input', { type: 'number', value: har.seed ?? '', placeholder: 'la seed principal',
    oninput: () => { if (hseed.value === '') delete p.harmony.seed; else p.harmony.seed = parseInt(hseed.value) || 0; markDirty(true); } });

  const info = el('div', { class: 'tiny muted', style: 'margin-top:8px' },
    mode === 'keyword' ? describeKeyword(har.keyword) : '');

  card.append(el('div', { class: 'grid-2', style: 'margin-top:12px' },
    el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Selección'), modeSel),
    el('label', { class: 'fld' }, el('span', { class: 'lbl' }, mode === 'keyword' ? 'Keyword' : 'Progresión'), picker)),
    el('div', { class: 'grid-2', style: 'margin-top:10px' },
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Nivel de transformación'), vari),
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Semilla propia (harmony-seed)'), hseed)),
    info,
    el('div', { class: 'tiny', style: 'margin-top:10px' },
      'Niveles admitidos: ', el('span', { class: 'mono' }, FS().harmony_variaciones.join(' · ')),
      '. "familiarity_auto" deja que la biblioteca elija.'));
  return card;
}

function describeKeyword(kw) {
  const lib = state.caps.biblioteca_fase7 || [];
  const matches = lib.filter(e => (e.keywords || []).includes(kw));
  if (!matches.length) return 'sin descripción local';
  return `${matches.length} progresión(es) declaran este keyword · familias: ${[...new Set(matches.map(m => m.familia))].join(', ')}`;
}
