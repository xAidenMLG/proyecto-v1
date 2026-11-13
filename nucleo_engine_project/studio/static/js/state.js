// Estado global de la sesión de estudio + pub/sub mínimo.
// El documento dark-director/1 (state.doc) es un objeto único: las vistas
// visuales solo tocan campos conocidos, así los campos x_* y cualquier clave
// válida desconocida NUNCA se pierden al alternar entre editor visual y JSON.

export const state = {
  caps: null,          // capabilities del backend
  projects: [],        // lista
  project: null,       // proyecto activo (meta + production + history)
  doc: null,           // documento dark-director/1 del proyecto activo (editable)
  dirty: false,
  lastJob: null,       // jid del último trabajo lanzado
};

const subs = {};
export function on(evt, fn) { (subs[evt] = subs[evt] || []).push(fn); }
export function emit(evt, data) { (subs[evt] || []).forEach(fn => fn(data)); }

export function markDirty(v = true) {
  state.dirty = v;
  emit('dirty', v);
}

export function setDoc(doc, { dirty = true } = {}) {
  state.doc = doc;
  if (dirty) markDirty(true);
  emit('doc', doc);
}

// ---- helpers de documento (solo campos conocidos; nunca borran lo demás) ----

export function globalDoc() {
  state.doc.global = state.doc.global || {};
  return state.doc.global;
}
export function harmonyDoc() {
  state.doc.harmony = state.doc.harmony || {};
  return state.doc.harmony;
}
export function directionDoc() {
  state.doc.direction = state.doc.direction || {};
  return state.doc.direction;
}
export function sections() {
  if (!Array.isArray(state.doc.structure)) state.doc.structure = [];
  return state.doc.structure;
}
export function instrumentsDoc() {
  if (!state.doc.instruments || typeof state.doc.instruments !== 'object') state.doc.instruments = {};
  return state.doc.instruments;
}
export function devDoc() {
  if (!state.doc.development || typeof state.doc.development !== 'object') state.doc.development = {};
  return state.doc.development;
}
export function production() {
  if (!state.project.production || typeof state.project.production !== 'object')
    state.project.production = {};
  return state.project.production;
}

// ¿Modo armónico GUIDED? (presencia de progresiones explícitas: precedencia real)
export function harmonyMode() {
  const h = state.doc.harmony || {};
  const hasProg = h.progressions && typeof h.progressions === 'object'
    && Object.keys(h.progressions).length > 0;
  const hasChords = (state.doc.structure || []).some(s => Array.isArray(s.chords) && s.chords.length);
  return (hasProg || hasChords) ? 'guided' : 'native';
}

export function totalBars() {
  return (state.doc.structure || []).reduce((a, s) => a + (parseInt(s.bars) || 0), 0);
}

export function docTitle() {
  return (state.doc.meta && state.doc.meta.title) || state.project?.name || '—';
}
