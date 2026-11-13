// Vista JSON — editor directo del documento dark-director/1.
// La edición manual reemplaza el objeto completo (los campos válidos
// desconocidos para la UI se PRESERVAN: aquí no hay "campos conocidos").
// La validación es SIEMPRE la del validador real del backend.
import { state, markDirty } from '../state.js';
import { el, $, toast, toastErr, toastOk, confirmDialog, download } from '../ui.js';
import { API } from '../api.js';

let gutterSynced = false;

export async function render(host) {
  host.innerHTML = '';
  host.append(el('h1', {}, 'JSON'),
    el('p', { class: 'sub' }, 'Control avanzado: el documento completo dark-director/1. La sincronización con el editor visual conserva los campos válidos que la interfaz no conoce (incluidos x_*).'));

  const text = el('textarea', { class: 'json-area', spellcheck: 'false', rows: 26 });
  text.value = JSON.stringify(state.doc, null, 2);

  const gutter = el('div', { class: 'json-gutter' });
  const syncGutter = () => {
    const n = text.value.split('\n').length;
    gutter.textContent = Array.from({ length: n }, (_, i) => i + 1).join('\n');
    gutter.scrollTop = text.scrollTop;
  };
  text.addEventListener('scroll', () => { gutter.scrollTop = text.scrollTop; });
  syncGuttered(text, syncGutter);

  const status = el('div', { class: 'tiny muted', style: 'margin-top:8px' }, 'sin validar');

  const wrap = el('div', { class: 'json-wrap' }, gutter, text);

  const btnValidate = el('button', { class: 'btn', onclick: async () => {
    await doValidate(text, status);
  } }, '✓ Validar');
  const btnApply = el('button', { class: 'btn primary', onclick: async () => {
    if (!(await doValidate(text, status))) return;
    try {
      const parsed = JSON.parse(text.value);
      if (parsed.schema && parsed.schema !== 'dark-director/1') {
        toast(`schema "${parsed.schema}" no es dark-director/1 (E102)`, 'err');
        return;
      }
      state.doc = parsed;
      markDirty(true);
      toastOk('JSON aplicado al proyecto (recuerda Guardar)');
    } catch (e) { toast('JSON malformado: ' + e.message, 'err'); }
  } }, 'Aplicar al proyecto');
  const btnFormat = el('button', { class: 'btn ghost', onclick: () => {
    try { text.value = JSON.stringify(JSON.parse(text.value), null, 2); syncGutter(); status.textContent = 'formateado'; }
    catch (e) { toast('JSON malformado: ' + e.message, 'err'); }
  } }, 'Formatear');
  const btnDownload = el('button', { class: 'btn ghost', onclick: () => {
    const blob = new Blob([text.value], { type: 'application/json' });
    const a = el('a', { href: URL.createObjectURL(blob), download: (state.project.id || 'doc') + '.json' });
    document.body.append(a); a.click(); a.remove();
  } }, '↓ Descargar');
  const btnLoad = el('input', { type: 'file', accept: '.json,application/json', style: 'display:none' });
  btnLoad.addEventListener('change', async () => {
    const f = btnLoad.files[0];
    if (!f) return;
    const txt = await f.text();
    text.value = txt; syncGutter();
    status.textContent = `cargado ${f.name} — valida antes de aplicar`;
  });
  const btnUpload = el('button', { class: 'btn ghost', onclick: () => btnLoad.click() }, '↑ Cargar JSON externo');

  host.append(el('div', { class: 'card' },
    el('div', { class: 'row', style: 'margin-bottom:12px' },
      btnValidate, btnApply, btnFormat, btnUpload, btnDownload,
      el('span', { class: 'right tiny muted' }, 'kbd: aplicar valida siempre con el motor')),
    wrap, status));
}

function syncGuttered(text, syncGutter) {
  text.addEventListener('input', syncGutter);
  syncGutter();
}

async function doValidate(text, status) {
  let parsed;
  try { parsed = JSON.parse(text.value); }
  catch (e) {
    status.innerHTML = `<span class="err-text">JSON malformado: ${escapeH(e.message)}</span>`;
    return false;
  }
  try {
    const v = await API.validate(parsed);
    const errs = v.errores || [], e3 = v.e3xx || [], avisos = v.avisos || [];
    if (!errs.length && !e3.length) {
      status.innerHTML = `<span class="ok-text">✓ válido para dark-director/1 · ${avisos.length} aviso(s) W</span>` +
        (avisos.length ? el('div', { class: 'tiny muted', style: 'margin-top:6px' },
          avisos.map(([c, m]) => el('div', {}, `${c} · ${m}`))) : '');
      return true;
    }
    status.innerHTML = '';
    const box = el('div', { class: 'err-text' }, ...errs.concat(e3).map(([c, m]) => el('div', {}, `${c} · ${m}`)));
    status.append(box);
    return false;
  } catch (e) { toastErr(e); return false; }
}

function escapeH(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
