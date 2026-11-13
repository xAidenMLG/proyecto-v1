// Shell + router de DMD STUDIO.
import { API } from './api.js';
import { state, on, emit, markDirty, docTitle } from './state.js';
import { el, $, $$, toast, toastErr, toastOk, confirmDialog, modal } from './ui.js';

import * as projectsView from './views/projects.js';
import * as compositionView from './views/composition.js';
import * as harmonyView from './views/harmony.js';
import * as productionView from './views/production.js';
import * as generationView from './views/generation.js';
import * as jsonView from './views/jsoneditor.js';
import * as resultsView from './views/results.js';

const VIEWS = {
  projects: projectsView,
  composition: compositionView,
  harmony: harmonyView,
  production: productionView,
  generation: generationView,
  json: jsonView,
  results: resultsView,
};

const REQUIRES_PROJECT = new Set(['composition', 'harmony', 'production', 'generation', 'json', 'results']);

function currentRoute() {
  const h = location.hash.replace(/^#\/?/, '') || 'projects';
  const [view, arg] = h.split('/');
  return { view: VIEWS[view] ? view : 'projects', arg };
}

function renderNav(view) {
  $$('#nav a').forEach(a => a.classList.toggle('active', a.dataset.view === view));
  $$('#nav a').forEach(a => {
    const needs = REQUIRES_PROJECT.has(a.dataset.view);
    a.classList.toggle('disabled', needs && !state.project);
  });
}

async function render() {
  const { view, arg } = currentRoute();
  renderNav(view);
  const host = $('#view');
  host.innerHTML = '<div class="loading">…</div>';
  try {
    await VIEWS[view].render(host, arg);
  } catch (e) {
    host.innerHTML = '';
    host.append(
      Object.assign(document.createElement('div'), {
        className: 'empty',
        textContent: 'No se pudo mostrar esta vista: ' + ((e && e.error) || e)
      }));
  }
  updateTopbar();
}

function updateTopbar() {
  $('#project-crumb').innerHTML = state.project
    ? `<b>${escapeHtml(docTitle())}</b> <span class="tiny">· ${state.project.id}</span>`
    : 'sin proyecto';
  $('#btn-save').disabled = !state.project || !state.dirty;
  $('#btn-saveas').disabled = !state.project;
  $('#dirty-dot').hidden = !state.dirty;
  $('#btn-goto-gen').disabled = !state.project;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// ------------------------------------------------------------- acciones shell
async function saveProject(silent = false) {
  if (!state.project) return;
  try {
    const p = await API.saveProject(state.project.id, {
      name: state.project.name,
      description: state.project.description,
      doc: state.doc,
      production: state.project.production,
    });
    state.project = p;
    markDirty(false);
    if (!silent) toastOk('Proyecto guardado');
    updateTopbar();
    emit('saved', p);
  } catch (e) { toastErr(e); }
}

async function openProject(pid) {
  try {
    const p = await API.project(pid);
    state.project = p;
    state.doc = p.doc;
    state.lastJob = null;
    markDirty(false);
    localStorage.setItem('dmd.project', pid);
    location.hash = '#/composition';
    await render();
    emit('project-opened', p);
  } catch (e) { toastErr(e); }
}

async function closeProject() {
  if (state.dirty) {
    const ok = await confirmDialog('Cambios sin guardar',
      'Hay cambios sin guardar. ¿Cerrar el proyecto de todos modos?', 'Cerrar', true);
    if (!ok) return;
  }
  state.project = null;
  state.doc = null;
  localStorage.removeItem('dmd.project');
  location.hash = '#/projects';
  render();
}

export { openProject, closeProject, saveProject, render };

// ----------------------------------------------------------------- arranque
async function boot() {
  try {
    state.caps = await API.capabilities();
    const a = state.caps.audio || {};
    $('#engine-status').innerHTML =
      `contrato ${state.caps.contrato.contract} rev ${state.caps.contrato.contract_rev}<br>` +
      `jazz_engine ${state.caps.jazz_engine_version} · ${state.caps.perfiles.length} perfiles<br>` +
      (a.wav_posible
        ? '<span style="color:var(--ok)">WAV disponible (FluidSynth ✓)</span>'
        : '<span style="color:var(--warn)">WAV no disponible (falta FluidSynth o soundfont)</span>');
  } catch (e) {
    $('#engine-status').textContent = 'sin conexión con el backend';
    toastErr(e);
  }

  // restaurar proyecto activo
  const last = localStorage.getItem('dmd.project');
  if (last) {
    try {
      const p = await API.project(last);
      state.project = p; state.doc = p.doc; markDirty(false);
    } catch { localStorage.removeItem('dmd.project'); }
  }

  $('#btn-save').onclick = () => saveProject();
  $('#btn-saveas').onclick = async () => {
    if (!state.project) return;
    const name = document.createElement('input');
    name.type = 'text'; name.value = state.project.name + ' (copia)'; name.maxLength = 60;
    modal(el('div', {}, el('label', { class: 'fld' }, el('span', { class: 'lbl' },
      'Nuevo nombre (se copia documento y producción, sin el historial)'), name)), {
      title: 'Guardar como',
      actions: [
        { label: 'Cancelar', kind: 'ghost' },
        { label: 'Guardar copia y abrir', kind: 'primary', onclick: async () => {
          try {
            const p = await API.duplicateProject(state.project.id, name.value.trim() || undefined);
            toastOk('Guardado como: ' + p.name);
            openProject(p.id);
          } catch (e) { toastErr(e); return false; }
        } },
      ],
    });
  };
  $('#btn-goto-gen').onclick = () => { location.hash = '#/generation'; };
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      if (state.project) saveProject();
    }
  });
  window.addEventListener('beforeunload', (e) => {
    if (state.dirty) { e.preventDefault(); e.returnValue = ''; }
  });

  window.addEventListener('hashchange', render);
  on('dirty', updateTopbar);
  on('doc', updateTopbar);
  await render();
}

boot();
