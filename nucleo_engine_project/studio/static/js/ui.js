// Utilidades de DOM y feedback (toasts, modales, confirmación).

export function el(tag, attrs = {}, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') n.className = v;
    else if (k === 'html') n.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') n.addEventListener(k.slice(2), v);
    else if (k === 'value') n.value = v;
    else if (k === 'checked') n.checked = !!v;
    else if (k === 'disabled') n.disabled = !!v;
    else if (k === 'selected') n.selected = !!v;
    else if (v !== null && v !== undefined && v !== false) n.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    n.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return n;
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function toast(msg, kind = 'info', ms = 4200) {
  const t = el('div', { class: 'toast ' + (kind === 'info' ? '' : kind) }, msg);
  $('#toasts').append(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 320); }, ms);
}
export const toastErr = (e) => toast((e && (e.error || e.detail)) || String(e), 'err', 6500);
export const toastOk = (m) => toast(m, 'ok');

export function modal(contentEl, { title, actions = [] } = {}) {
  const root = $('#modal-root');
  root.innerHTML = '';
  const box = el('div', { class: 'modal' },
    title ? el('h3', {}, title) : null,
    contentEl,
    actions.length ? el('div', { class: 'actions' },
      actions.map(a => el('button', {
        class: 'btn ' + (a.kind || 'ghost'),
        onclick: async () => { if (await a.onclick?.() !== false) closeModal(); }
      }, a.label))) : null);
  const ov = el('div', { class: 'overlay', onclick: (e) => { if (e.target === ov) closeModal(); } }, box);
  root.append(ov);
  return { close: closeModal, box };
}
export function closeModal() { $('#modal-root').innerHTML = ''; }

export function confirmDialog(title, msg, okLabel = 'Confirmar', danger = false) {
  return new Promise(res => {
    modal(el('p', { class: 'muted', style: 'margin:0' }, msg), {
      title,
      actions: [
        { label: 'Cancelar', kind: 'ghost', onclick: () => { res(false); } },
        { label: okLabel, kind: danger ? 'danger' : 'primary', onclick: () => { res(true); } },
      ],
    });
    // si cierra por overlay → cancelar
    const ov = $('#modal-root .overlay');
    ov.addEventListener('click', (e) => { if (e.target === ov) res(false); });
  });
}

export function fmtBytes(n) {
  if (n == null) return '—';
  if (n < 1024) return n + ' B';
  if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
  return (n / 1048576).toFixed(2) + ' MB';
}

export function fmtDate(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('es', { year: 'numeric', month: '2-digit', day: '2-digit',
                                    hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}

export function fmtDur(s) {
  if (s == null) return '—';
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return `${m}:${String(r).padStart(2, '0')}`;
}

export function copyText(txt) {
  navigator.clipboard?.writeText(txt).then(() => toastOk('Copiado al portapapeles'))
    .catch(() => toast('No se pudo copiar', 'err'));
}

export function download(url, fname) {
  const a = el('a', { href: url, download: fname || '' });
  document.body.append(a); a.click(); a.remove();
}

// select helper
export function select(value, options, attrs = {}) {
  // options: [{v, label}] o lista de strings
  const opts = options.map(o => typeof o === 'string' ? { v: o, label: o } : o);
  return el('select', attrs, opts.map(o =>
    el('option', { value: o.v, selected: String(o.v) === String(value) }, o.label)));
}

// slider con etiqueta numérica
export function slider(label, value, { min = 0, max = 1, step = 0.05, oninput } = {}) {
  const val = el('span', { class: 'val' }, Number(value ?? 0).toFixed(2));
  const inp = el('input', { type: 'range', min, max, step, value: value ?? 0,
    oninput: () => { val.textContent = Number(inp.value).toFixed(2); oninput?.(parseFloat(inp.value)); } });
  return el('div', { class: 'slider-row' },
    el('span', { class: 'lbl', style: 'margin:0' }, label), inp, val);
}

// chips multi-select (focus/active)
export function chipsMulti(selected, options, ontoggle) {
  selected = new Set(selected || []);
  const wrap = el('div', { class: 'row', style: 'gap:6px' });
  for (const o of options) {
    const c = el('span', { class: 'chip click ' + (selected.has(o) ? 'on' : '') }, o);
    c.onclick = () => {
      if (selected.has(o)) { selected.delete(o); c.classList.remove('on'); }
      else { selected.add(o); c.classList.add('on'); }
      ontoggle([...selected]);
    };
    wrap.append(c);
  }
  return wrap;
}
