// Vista RESULTS — historial de generaciones, artefactos, hashes, audio y descargas.
import { state } from '../state.js';
import { el, $, fmtBytes, fmtDate, fmtDur, copyText, download, toastErr } from '../ui.js';
import { API } from '../api.js';

let highlightGen = null;
export function pulse(genId) { highlightGen = genId; }

export async function render(host) {
  host.innerHTML = '';
  host.append(el('h1', {}, 'Results'),
    el('p', { class: 'sub' }, 'Artefactos reales del pipeline: doc.json, config_efectiva.json, MIDI, evidencia.json y WAV. Cada archivo con su SHA256.'));

  // el historial puede haber cambiado (nueva generación): re-obtener el proyecto
  try { state.project = await API.project(state.project.id); }
  catch (e) { host.append(el('div', { class: 'empty' }, 'Error: ' + (e.error || e))); return; }

  const p = state.project;
  if (!p.history || !p.history.length) {
    host.append(el('div', { class: 'empty' },
      'Este proyecto aún no tiene generaciones. Ve a Generation y pulsa «Generar MIDI».'));
    return;
  }

  const jobs = await API.jobs(p.id).catch(() => []);
  const jobByGen = Object.fromEntries(jobs.map(j => [j.gen_id, j]));

  for (const h of p.history) {
    host.append(genCard(h, jobByGen[h.gen_id]));
  }
}

function genCard(h, job) {
  const genId = h.gen_id;
  const outName = h.out_name || 'salida';
  const open = highlightGen === genId;

  const head = el('div', { class: 'spread', style: 'cursor:pointer' },
    el('div', {},
      el('div', { class: 'row', style: 'gap:10px' },
        el('b', {}, genId),
        el('span', { class: 'badge acc' }, h.perfil || '—'),
        el('span', { class: 'mono tiny' }, 'seed ' + (h.seed ?? '—')),
        el('span', { class: 'mono tiny' }, fmtDur(h.duracion_s)),
        el('span', { class: 'tiny muted' }, fmtDate(h.fecha_utc)),
        (h.compliance_fails || []).length ? el('span', { class: 'badge err' }, 'compliance FAIL') : el('span', { class: 'badge ok' }, 'compliance OK'),
        h.wav ? (h.wav.ok ? el('span', { class: 'badge ok' }, 'WAV') : el('span', { class: 'badge warn' }, 'WAV no')) : null),
      el('div', { class: 'mono tiny muted', style: 'margin-top:5px' },
        'sha256 ', (h.sha256_midi || '').slice(0, 24), '…',
        el('button', { class: 'btn icon ghost', title: 'copiar sha256', onclick: (e) => {
          e.stopPropagation(); copyText(h.sha256_midi || '');
        } }, '⧉'))),
    el('span', { class: 'sec-caret' }, '▸'));

  const body = el('div', { class: 'sec-body' });
  const card = el('div', { class: 'sec-item' + (open ? ' open' : ''), style: open ? '' : '' },
    head, body);
  if (!open) body.style.display = 'none';
  head.onclick = () => {
    const vis = body.style.display !== 'none';
    body.style.display = vis ? 'none' : '';
    card.classList.toggle('open', !vis);
  };

  // ---- audio + descargas (la carpeta real la lista el backend) ----
  const audioBox = el('div');
  const dlBox = el('div', { class: 'row', style: 'margin-top:10px' });
  API.generation(state.project.id, genId).then(g => {
    for (const [key, meta] of Object.entries(g.archivos || {})) {
      if (!key.includes('/')) continue;          // solo artefactos de la carpeta de salida
      const slash = key.indexOf('/');
      const folder = key.slice(0, slash), fname = key.slice(slash + 1);
      const url = API.audioUrl(state.project.id, genId, folder, fname);
      if (/\.(wav|mp3)$/.test(fname)) {
        audioBox.append(
          el('div', { style: 'margin-top:8px' },
            el('span', { class: 'lbl' }, 'Escucha (' + fname + ' · ' + fmtBytes(meta.bytes) + ')'),
            el('audio', { controls: true, src: url, preload: 'none' })));
      }
      if (/\.(mid|wav|mp3|json)$/.test(fname) && fname !== 'doc.json') {
        dlBox.append(el('button', { class: 'btn sm ghost',
          onclick: () => download(url, fname) }, '↓ ' + fname));
      }
    }
    for (const key of Object.keys(g.archivos || {})) {
      if (key.endsWith('/doc.json')) {
        const folder = key.slice(0, key.indexOf('/'));
        dlBox.append(el('button', { class: 'btn sm ghost',
          onclick: () => download(API.audioUrl(state.project.id, genId, folder, 'doc.json'), 'doc.json') }, '↓ doc.json'));
        break;
      }
    }
    if (!dlBox.children.length) dlBox.append(el('span', { class: 'tiny' }, 'artefactos no encontrados'));
    dlBox.append(el('button', { class: 'btn sm ghost', onclick: () =>
      download(API.genLogUrl(state.project.id, genId), genId + '.log') }, '↓ job.log'));
  }).catch(e => { dlBox.append(el('span', { class: 'err-text' }, String(e.error || e))); });

  // ---- evidencia + log ----
  const evidBox = el('div', { class: 'tiny muted' });
  API.generation(state.project.id, genId).then(g => {
    const evKey = Object.keys(g.archivos || {}).find(k => k.endsWith('/evidencia.json'));
    const ev = evKey ? g.archivos[evKey] : null;
    if (!ev) return;
    const lines = [];
    lines.push(`bpm ${ev.bpm} · ${ev.compases} compases · ${ev.duracion_s}s · notas/pista: ` +
      Object.entries(ev.notas_por_pista || {}).map(([k, v]) => `${k}:${v}`).join(' '));
    if (ev.compliance_warns?.length) lines.push('avisos compliance: ' + ev.compliance_warns.join(', '));
    if (ev.avisos_compilador?.length) lines.push('avisos compilador: ' + ev.avisos_compilador.join(', '));
    if (ev.harmonia) lines.push('familiaridad F7: ' + JSON.stringify(ev.harmonia.activacion));
    if (ev.reproduccion?.regenerar) {
      lines.push('');
      const regen = el('div', { class: 'mono', style: 'color:var(--acc); word-break:break-all' },
        ev.reproduccion.regenerar);
      const copy = el('button', { class: 'btn icon ghost', title: 'copiar comando',
        onclick: () => copyText(ev.reproduccion.regenerar) }, '⧉');
      lines.push('');
      evidBox.append(el('div', { style: 'margin-top:8px' },
        el('span', { class: 'lbl' }, 'Reproducción exacta (CLI)'), el('div', { class: 'row' }, regen, copy)));
    }
    for (const l of lines) if (l) evidBox.prepend(el('div', {}, l));
    if (ev.reproduccion?.fluidsynth_windows) {
      evidBox.append(el('div', { style: 'margin-top:8px' },
        el('span', { class: 'lbl' }, 'WAV en Windows (FluidSynth)'),
        el('div', { class: 'mono muted', style: 'word-break:break-all' }, ev.reproduccion.fluidsynth_windows)));
    }
  }).catch(() => {});

  const logTerm = el('div', { class: 'term', style: 'max-height:220px; margin-top:10px' }, '…');
  if (job) {
    logTerm.innerHTML = '';
    for (const l of (job.log_tail || [])) logTerm.append(el('div', {}, l || ' '));
  } else {
    fetch(API.genLogUrl(state.project.id, genId)).then(r => r.ok ? r.text() : '').then(t => {
      logTerm.innerHTML = '';
      (t || 'log no disponible').split('\n').slice(-60).forEach(l => logTerm.append(el('div', {}, l)));
    }).catch(() => {});
  }

  body.append(
    el('div', { class: 'grid-2' },
      el('div', {}, el('span', { class: 'lbl' }, 'Evidencia'), evidBox),
      el('div', {}, el('span', { class: 'lbl' }, 'Audio'), audioBox)),
    el('div', { style: 'margin-top:8px' }, dlBox),
    logTerm);
  return card;
}
