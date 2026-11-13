// Vista GENERATION — validación previa, generación con pipeline real,
// progreso en vivo, log, cancelación y configuración efectiva visible.
import { state, markDirty, production } from '../state.js';
import { el, $, toast, toastErr, toastOk, confirmDialog } from '../ui.js';
import { API } from '../api.js';
import { saveProject } from '../app.js';

let pollTimer = null;

export async function render(host) {
  host.innerHTML = '';
  stopPoll();
  host.append(el('h1', {}, 'Generation'),
    el('p', { class: 'sub' }, 'Ejecuta el pipeline REAL: dark-director/1 → compilador → jazz_engine → MIDI Forge. La interfaz nunca duplica esta lógica: solo la orquesta.'));

  host.append(configCard(), runCard(), logCard());

  // si venimos de un trabajo reciente, mostrarlo
  try {
    const jobs = await API.jobs(state.project.id);
    if (jobs.length) showJob(jobs[0].jid, { silent: true });
  } catch { /* primera ejecución */ }
}

function effConfig() {
  const p = production();
  const seedEff = $('#g-seed')?.value !== '' && $('#g-seed')?.value != null
    ? parseInt($('#g-seed').value)
    : p.seed;
  const parts = [
    'perfil=' + (p.profile || 'full'),
    'seed=' + (seedEff ?? '(global.seed)'),
  ];
  const har = p.harmony;
  if (har && typeof har === 'object') {
    if (har.keyword) parts.push('harmony.keyword=' + har.keyword);
    if (har.id) parts.push('harmony.id=' + har.id);
    if (har.variacion) parts.push('harmony.variacion=' + har.variacion);
    if (har.seed != null) parts.push('harmony.seed=' + har.seed);
  }
  if ($('#g-wav')?.checked) parts.push('wav=1');
  return parts.join('  ');
}

function cliEquiv() {
  const p = production();
  const har = p.harmony && typeof p.harmony === 'object' ? p.harmony : null;
  const flags = [`--production ${p.profile || 'full'}`];
  const seed = $('#g-seed')?.value;
  if (seed !== '' && seed != null) flags.push(`--seed ${seed}`);
  else if (p.seed != null) flags.push(`--seed ${p.seed}`);
  if (har) {
    if (har.keyword) flags.push(`--harmony ${har.keyword}`);
    if (har.id) flags.push(`--harmony-id ${har.id}`);
    if (har.variacion) flags.push(`--harmony-variacion ${har.variacion}`);
    if (har.seed != null) flags.push(`--harmony-seed ${har.seed}`);
  }
  return `python scripts/produce.py doc.json ${flags.join(' ')} --out <carpeta>`;
}

function configCard() {
  const p = production();
  const seed = el('input', { type: 'number', id: 'g-seed', value: '', placeholder: 'default del proyecto: ' + (p.seed ?? 'global.seed') });
  seed.addEventListener('input', () => { $('#g-eff').textContent = effConfig(); $('#g-cli').textContent = cliEquiv(); });
  const outName = el('input', { type: 'text', id: 'g-out', placeholder: 'nombre de la carpeta/MIDI (vacío = título)' });
  const valFirst = el('input', { type: 'checkbox', id: 'g-valf', checked: true });
  const wav = el('input', { type: 'checkbox', id: 'g-wav', checked: !!p.render_wav });
  wav.addEventListener('change', () => { $('#g-eff').textContent = effConfig(); });
  return el('div', { class: 'card' }, el('h2', {}, 'Configuración de esta generación'),
    el('div', { class: 'grid-3' },
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Seed reproducible (opcional)'), seed),
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Nombre de salida (opcional)'), outName),
      el('div', { class: 'row', style: 'align-items:flex-end; gap:18px' },
        el('label', { class: 'row', style: 'gap:8px' }, valFirst, el('span', { class: 'tiny' }, 'Validación previa (contrato + compilador)')),
        el('label', { class: 'row', style: 'gap:8px' }, wav, el('span', { class: 'tiny' }, 'Renderizar WAV')))),
    el('div', { style: 'margin-top:14px; border-top:1px solid var(--line); padding-top:12px' },
      el('span', { class: 'lbl' }, 'Configuración efectiva'),
      el('div', { class: 'mono', id: 'g-eff', style: 'color:var(--acc)' }, effConfig()),
      el('span', { class: 'lbl', style: 'margin-top:10px' }, 'Comando CLI equivalente (para reproducir fuera del estudio)'),
      el('div', { class: 'mono muted', id: 'g-cli' }, cliEquiv())));
}

function runCard() {
  const btn = el('button', { class: 'btn primary', id: 'g-run', onclick: () => run(btn) }, '▶ Generar MIDI');
  const cancel = el('button', { class: 'btn danger', id: 'g-cancel', hidden: true, onclick: () => doCancel() }, '✕ Cancelar');
  const status = el('span', { id: 'g-status', class: 'mono tiny muted' }, 'inactivo');
  const bar = el('div', { class: 'progress-track', style: 'margin-top:12px' },
    el('div', { class: 'progress-bar', id: 'g-bar' }));
  return el('div', { class: 'card' }, el('h2', {}, 'Ejecución'),
    el('div', { class: 'row' }, btn, cancel, el('span', { class: 'right' }), status), bar);
}

function logCard() {
  return el('div', { class: 'card' }, el('h2', {}, 'Registro de ejecución'),
    el('div', { class: 'term', id: 'g-log' }, 'Sin actividad todavía.'));
}

/* ------------------------------------------------------------- ejecución */
async function run(btn) {
  btn.disabled = true;
  try {
    if (state.dirty) {
      const ok = await confirmDialog('Cambios sin guardar',
        'Generar usa el documento GUARDADO. ¿Guardar ahora y generar con los cambios actuales?',
        'Guardar y generar');
      if (!ok) { btn.disabled = false; return; }
      await saveProject(true);
    }
    const body = {
      production: production().profile || undefined,
      seed: $('#g-seed').value === '' ? undefined : parseInt($('#g-seed').value),
      wav: $('#g-wav').checked,
      out_name: $('#g-out').value.trim() || undefined,
      validate_first: $('#g-valf').checked,
    };
    const job = await API.generate(state.project.id, body);
    state.lastJob = job.jid;
    showJob(job.jid);
  } catch (e) {
    if (e && e.validacion) showValidation(e.validacion, e.error);
    else toastErr(e);
    btn.disabled = false;
  }
}

function showValidation(v, headline) {
  const log = $('#g-log');
  const lines = [headline || 'Validación previa fallida (validador real dark-director/1):', ''];
  for (const [code, msg] of (v.errores || [])) lines.push(`E   ${code}  ${msg}`);
  for (const [code, msg] of (v.e3xx || [])) lines.push(`E3  ${code}  ${msg}`);
  for (const [code, msg] of (v.avisos || [])) lines.push(`W   ${code}  ${msg}`);
  log.innerHTML = '';
  log.append(lines.map(l => el('div', { class: l.startsWith('E') ? 't-err' : '' }, l)));
}

function showJob(jid, { silent = false } = {}) {
  $('#g-cancel').hidden = false;
  $('#g-status').textContent = 'consultando…';
  pollJob(jid, silent);
}

function pollJob(jid, silent = false) {
  stopPoll();
  const tick = async () => {
    let j;
    try { j = await API.job(jid); }
    catch { stopPoll(); return; }
    paintJob(j);
    if (['running', 'queued'].includes(j.state)) {
      pollTimer = setTimeout(tick, 700);
    } else {
      stopPoll();
      $('#g-cancel').hidden = true;
      $('#g-run').disabled = false;
      if (j.state === 'done' && !silent) toastOk('Generación completada — mira Results');
      if (j.state === 'done') {
        import('./results.js').then(m => m.pulse(j.gen_id)).catch(() => {});
      }
    }
  };
  tick();
}

function paintJob(j) {
  const log = $('#g-log');
  log.innerHTML = '';
  for (const line of (j.log_tail || [])) {
    log.append(el('div', {
      class: line.startsWith('## ') ? 't-step' : (line.includes('Traceback') || line.includes('Error') ? 't-err' : '')
    }, line || ' '));
  }
  log.scrollTop = log.scrollHeight;
  $('#g-status').textContent = `${j.state} · ${j.step || ''} · jid ${j.jid}`;
  const bar = $('#g-bar');
  if (j.state === 'running') { bar.className = 'progress-bar indet'; }
  else { bar.className = 'progress-bar'; bar.style.width = j.state === 'done' ? '100%' : '0%'; }
  if (j.state === 'done') {
    const r = j.result?.produccion;
    if (r) $('#g-status').textContent =
      `completado · ${r.perfil} · seed ${r.seed} · ${r.duracion_s}s · sha ${String(r.sha256).slice(0, 12)}…`;
  }
  if (j.state === 'error' && j.result?.error) {
    $('#g-status').innerHTML = `<span style="color:var(--err)">error: ${escapeH(j.result.error)}</span>`;
  }
}

function escapeH(s) { return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

async function doCancel() {
  const jid = state.lastJob;
  if (!jid) return;
  try {
    await API.cancelJob(jid);
    toast('Cancelando…', 'info', 2500);
  } catch (e) { toastErr(e); }
}

function stopPoll() { if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; } }
