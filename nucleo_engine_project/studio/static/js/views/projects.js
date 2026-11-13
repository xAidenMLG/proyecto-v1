// Vista PROJECTS — crear, abrir, duplicar, eliminar, exportar.
import { API } from '../api.js';
import { state } from '../state.js';
import { el, $, toast, toastErr, toastOk, confirmDialog, modal, fmtDate, fmtDur, download } from '../ui.js';
import { openProject, saveProject } from '../app.js';

export async function render(host) {
  host.innerHTML = '<div class="loading">CARGANDO PROYECTOS…</div>';
  let list = [];
  try { list = await API.projects(); state.projects = list; }
  catch (e) { host.innerHTML = ''; host.append(el('div', { class: 'empty' }, 'Error: ' + (e.error || e))); return; }

  host.innerHTML = '';
  host.append(
    el('h1', {}, 'Projects'),
    el('p', { class: 'sub' },
      'Cada proyecto conserva el documento dark-director/1, la configuración de producción, la seed y el historial de generaciones.'),
    el('div', { class: 'spread', style: 'margin-bottom:14px' },
      el('div', { class: 'muted tiny' }, `${list.length} proyecto(s)`),
      el('button', { class: 'btn primary', onclick: () => createProjectModal(() => render(host)) }, '+ Nuevo proyecto')),
  );

  if (!list.length) {
    host.append(el('div', { class: 'empty' },
      'Aún no hay proyectos. Crea el primero para diseñar una composición sin escribir JSON.'));
    return;
  }

  const tbl = el('table', { class: 'tbl' },
    el('thead', {}, el('tr', {},
      el('th', {}, 'Proyecto'), el('th', {}, 'Identidad'), el('th', {}, 'BPM'),
      el('th', {}, 'Generaciones'), el('th', {}, 'Actualizado'), el('th', { style: 'width:220px' }, ''))),
    el('tbody', {}, list.map(p => el('tr', {},
      el('td', {}, el('div', { style: 'font-weight:600' }, p.name),
        el('div', { class: 'tiny mono' }, p.id)),
      el('td', { class: 'mono tiny' }, p.identity || '—'),
      el('td', { class: 'mono' }, p.bpm ?? '—'),
      el('td', { class: 'mono' }, p.generaciones),
      el('td', { class: 'tiny muted' }, fmtDate(p.updated_utc)),
      el('td', {},
        el('div', { class: 'row', style: 'gap:6px; flex-wrap:nowrap' },
          el('button', { class: 'btn sm primary', onclick: () => openProject(p.id) }, 'Abrir'),
          el('button', { class: 'btn sm ghost', title: 'Duplicar', onclick: async () => {
            try { const np = await API.duplicateProject(p.id); toastOk('Duplicado: ' + np.name); render(host); }
            catch (e) { toastErr(e); }
          } }, '⧉'),
          el('button', { class: 'btn sm ghost', title: 'Exportar JSON del documento',
            onclick: () => download(API.exportUrl(p.id), p.id + '.doc.json') }, '↓'),
          el('button', { class: 'btn sm danger', title: 'Eliminar', onclick: async () => {
            const ok = await confirmDialog('Eliminar proyecto',
              `Se eliminará «${p.name}» con sus generaciones. Esta acción no se puede deshacer.`, 'Eliminar', true);
            if (!ok) return;
            try { await API.deleteProject(p.id); toastOk('Proyecto eliminado'); render(host); }
            catch (e) { toastErr(e); }
          } }, '✕')))))),
    );
  host.append(el('div', { class: 'card' }, tbl));
}

export function createProjectModal(ondone) {
  const name = el('input', { type: 'text', placeholder: 'p. ej. Noches Largas', maxlength: '60' });
  const desc = el('input', { type: 'text', placeholder: 'descripción breve (opcional)', maxlength: '200' });
  const form = el('div', {},
    el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Nombre'), name),
    el('label', { class: 'fld', style: 'margin-top:10px' }, el('span', { class: 'lbl' }, 'Descripción'), desc),
    el('p', { class: 'tiny', style: 'margin-top:12px' },
      'Se crea con un documento mínimo válido (dark_triphop × balanced, 2 secciones) que puedes editar en Composition o en JSON.'),
  );
  modal(form, {
    title: 'Nuevo proyecto',
    actions: [
      { label: 'Cancelar', kind: 'ghost', onclick: () => {} },
      { label: 'Crear y abrir', kind: 'primary', onclick: async () => {
        if (!name.value.trim()) { toast('El proyecto necesita un nombre', 'err'); return false; }
        try {
          const p = await API.createProject({ name: name.value.trim(), description: desc.value.trim() });
          toastOk('Proyecto creado');
          ondone?.();
          openProject(p.id);
        } catch (e) { toastErr(e); return false; }
      } },
    ],
  });
  setTimeout(() => name.focus(), 50);
}
