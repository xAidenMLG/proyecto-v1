'use strict';
/* MIDI Forge - interfaz. Sin dependencias; todo el estado vive en `project` (JSON canonico midi-forge/1). */
const $ = (s, r) => (r || document).querySelector(s);
const ROLE_COLOR = {pad: '#7aa2f7', strings: '#bb9af7', keys: '#ff9e64', bass: '#f7768e', arp: '#e0af68', mallet: '#73daca', lead: '#9ece6a', drums: '#7dcfff'};
const TABS = [['json', 'JSON'], ['global', 'Global'], ['tracks', 'Pistas'], ['sections', 'Secciones'], ['blocks', 'Bloques'],
  ['lead', 'Lead'], ['auto', 'Automatizaci\u00f3n'], ['report', 'Informe']];
let META = null, project = null, result = null, tab = 'json', sel = {s: 0, t: null}, hidden = {}, adapterReport = [];
let genTimer = null, dirty = false, seekBeat = 0, player = null;

// ------------------------------------------------------------------ utilidades
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') e.className = v;
    else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, '');
    else if (v !== false && v != null) e.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
}
const clone = (o) => JSON.parse(JSON.stringify(o));
function getP(o, path) { return path.split('.').reduce((a, k) => (a == null ? undefined : a[k]), o); }
function setP(o, path, v) {
  const ks = path.split('.'); let c = o;
  for (let i = 0; i < ks.length - 1; i++) { if (typeof c[ks[i]] !== 'object' || c[ks[i]] === null) c[ks[i]] = {}; c = c[ks[i]]; }
  c[ks[ks.length - 1]] = v;
}
function delP(o, path) {
  const ks = path.split('.'); const chain = [o]; let c = o;
  for (let i = 0; i < ks.length - 1; i++) { c = c && c[ks[i]]; if (c == null) return; chain.push(c); }
  delete c[ks[ks.length - 1]];
  for (let i = chain.length - 1; i > 0; i--) if (Object.keys(chain[i]).length === 0) delete chain[i - 1][ks[i - 1]];
}
async function API(path, body) {
  const r = await fetch(path, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
  const ct = r.headers.get('Content-Type') || '';
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).error || m; } catch (e) {} throw new Error(m); }
  return ct.includes('json') ? r.json() : r;
}
async function getText(path) { const r = await fetch(path); if (!r.ok) throw new Error(r.statusText); return r.text(); }
function setStatus(msg, cls) { const s = $('#status'); s.textContent = msg; s.className = 'status ' + (cls || ''); }
function download(name, data, type) {
  const blob = data instanceof Blob ? data : new Blob([data], {type: type || 'application/octet-stream'});
  const a = h('a', {href: URL.createObjectURL(blob), download: name}); document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
const slug = (s) => (s || 'proyecto').normalize('NFKD').replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '_').toLowerCase() || 'proyecto';
function changed() {
  dirty = true; $('#btnMid').disabled = true;
  if ($('#autoGen').checked) { clearTimeout(genTimer); genTimer = setTimeout(generate, 600); } else setStatus('Hay cambios sin generar (Ctrl+Enter).', 'warn');
}

// ------------------------------------------------------------------ controles enlazados
function field(label, ctrl, cls) { return h('label', {class: 'f ' + (cls || '')}, h('span', {}, label), ctrl); }
function numIn(obj, path, o) {
  o = o || {};
  const cur = getP(obj, path);
  const e = h('input', {type: 'number', step: o.step || (o.int ? 1 : 'any'), min: o.min, max: o.max, placeholder: o.ph || ''});
  e.value = cur == null ? '' : cur;
  e.addEventListener('input', () => {
    if (e.value === '') { if (o.optional) delP(obj, path); else return; } else setP(obj, path, o.int ? Math.round(+e.value) : +e.value);
    (o.on || changed)();
  });
  return e;
}
function txtIn(obj, path, o) {
  o = o || {};
  const e = h('input', {type: 'text', spellcheck: 'false', placeholder: o.ph || ''}); e.value = getP(obj, path) == null ? '' : getP(obj, path);
  e.style.width = o.w || '100%';
  e.addEventListener('input', () => { setP(obj, path, e.value); (o.on || changed)(); });
  return e;
}
function chkIn(obj, path, label, on, dflt) {
  const e = h('input', {type: 'checkbox'}); const v = getP(obj, path); e.checked = v == null ? !!dflt : !!v;
  e.addEventListener('change', () => { setP(obj, path, e.checked); (on || changed)(); });
  return h('label', {class: 'f inline'}, e, h('span', {}, label));
}
function selIn(obj, path, options, o) {
  o = o || {};
  const e = h('select', {});
  for (const op of options) { const v = typeof op === 'object' ? op.v : op, l = typeof op === 'object' ? op.l : op; e.append(h('option', {value: v}, l)); }
  const cur = getP(obj, path); e.value = cur == null ? (o.empty ? '' : (typeof options[0] === 'object' ? options[0].v : options[0])) : cur;
  e.addEventListener('change', () => { if (e.value === '' && o.optional) delP(obj, path); else setP(obj, path, o.num ? +e.value : e.value); (o.on || changed)(); });
  return e;
}
function jsonArea(obj, path, o) {
  o = o || {};
  const v = getP(obj, path);
  const ta = h('textarea', {rows: o.rows || 3, spellcheck: 'false'}); ta.value = v == null ? '' : JSON.stringify(v);
  ta.addEventListener('input', () => {
    if (ta.value.trim() === '') { delP(obj, path); ta.classList.remove('bad'); (o.on || changed)(); return; }
    try { setP(obj, path, JSON.parse(ta.value)); ta.classList.remove('bad'); (o.on || changed)(); } catch (e) { ta.classList.add('bad'); }
  });
  return ta;
}
function rangeIn(obj, path, o) {
  const v = getP(obj, path) || [];
  const a = h('input', {type: 'number', step: 1, placeholder: 'min'}), b = h('input', {type: 'number', step: 1, placeholder: 'max'});
  a.value = v[0] == null ? '' : v[0]; b.value = v[1] == null ? '' : v[1];
  const upd = () => { if (a.value === '' || b.value === '') delP(obj, path); else setP(obj, path, [+a.value, +b.value]); ((o && o.on) || changed)(); };
  a.addEventListener('input', upd); b.addEventListener('input', upd);
  return h('span', {class: 'row', style: 'margin:0;gap:4px'}, a, '\u2013', b);
}
function listIn(obj, path, o) {
  const v = getP(obj, path);
  const e = h('input', {type: 'text', spellcheck: 'false', placeholder: 'a,b,c'}); e.value = Array.isArray(v) ? v.join(',') : '';
  e.addEventListener('input', () => {
    const t = e.value.split(',').map((x) => x.trim()).filter((x) => x !== '');
    if (!t.length) delP(obj, path); else setP(obj, path, t.every((x) => !isNaN(+x)) ? t.map(Number) : t);
    ((o && o.on) || changed)();
  });
  return e;
}
function paramField(params, f, on) {
  let c;
  const t = f.type;
  const wrap = (el) => field(f.label, el);
  if (t === 'bool') { c = chkIn(params, f.key, f.label, on, f.default); return h('div', {title: f.help || ''}, c); }
  if (t === 'number') c = numIn(params, f.key, {optional: true, ph: f.default == null ? '' : String(f.default), on});
  else if (t === 'int') c = numIn(params, f.key, {int: true, optional: true, ph: f.default == null ? '' : String(f.default), on});
  else if (t === 'select') c = selIn(params, f.key, ['', ...f.options], {optional: true, empty: true, on});
  else if (t === 'range') c = rangeIn(params, f.key, {on});
  else if (t === 'list') c = listIn(params, f.key, {on});
  else if (t === 'json') { c = jsonArea(params, f.key, {rows: 2, on}); const d = h('div', {title: f.help || '', style: 'flex-basis:100%'}, field(f.label, c)); if (f.help) d.append(h('div', {class: 'hint'}, f.help)); return d; }
  else c = txtIn(params, f.key, {on});
  const el = wrap(c); if (f.help) el.title = f.help; return el;
}

// ------------------------------------------------------------------ pesta\u00f1as
function renderTabs() {
  const t = $('#tabs'); t.innerHTML = '';
  for (const [id, label] of TABS) t.append(h('button', {class: id === tab ? 'on' : '', onclick: () => { tab = id; renderTabs(); renderPanel(); }}, label));
}
function renderPanel() {
  const p = $('#panel'); p.innerHTML = '';
  if (!project && tab !== 'json') { p.append(h('p', {class: 'hint'}, 'Carga un JSON primero.')); return; }
  ({json: tabJson, global: tabGlobal, tracks: tabTracks, sections: tabSections, blocks: tabBlocks, lead: tabLead, auto: tabAuto, report: tabReport})[tab](p);
}
function reportList(rep) { return h('div', {}, rep.map((r) => h('div', {class: 'rep ' + r.level}, (r.level === 'warn' ? '\u26a0 ' : r.level === 'error' ? '\u2716 ' : '\u00b7 ') + r.msg))); }

async function loadJson(text) {
  let obj;
  try { obj = JSON.parse(text); } catch (e) { setStatus('JSON inv\u00e1lido: ' + e.message, 'err'); return; }
  try {
    const pre = $('#presetSel') ? $('#presetSel').value : '';
    const r = await API('/api/normalize', {json: obj, preset: pre || undefined});
    project = r.project; adapterReport = r.report; result = null; sel = {s: 0, t: project.tracks[0] && project.tracks[0].id};
    $('#projName').value = (project.meta && project.meta.name) || '';
    const warn = r.report.filter((x) => x.level !== 'info').length;
    setStatus('Proyecto cargado: ' + project.sections.length + ' secciones, ' + project.tracks.length + ' pistas' + (warn ? ' (' + warn + ' avisos)' : '') + '.', warn ? 'warn' : 'ok');
    renderPanel(); drawRoll();
  } catch (e) { setStatus('No se pudo normalizar: ' + e.message, 'err'); }
}
function tabJson(p) {
  const ta = h('textarea', {id: 'jsonIn', rows: 16, spellcheck: 'false', placeholder: 'Pega aqu\u00ed tu JSON: spec descriptivo (Neon Rain v2, Shadow Corner), proyecto midi-forge/1 o eventos.'});
  const file = h('input', {type: 'file', accept: '.json,application/json', style: 'display:none', onchange: async (e) => { const f = e.target.files[0]; if (f) { ta.value = await f.text(); loadJson(ta.value); } }});
  const exSel = h('select', {id: 'exSel'}); const preSel = h('select', {id: 'presetSel'}, h('option', {value: ''}, 'auto'), META.presets.map((x) => h('option', {value: x}, x)));
  API('/api/examples').then((ex) => ex.forEach((x) => exSel.append(h('option', {value: x.file}, x.name))));
  p.append(h('h3', {}, 'Pegar o cargar JSON'), ta,
    h('div', {class: 'row'},
      h('button', {class: 'primary', onclick: () => loadJson(ta.value)}, 'Cargar y normalizar'),
      h('button', {onclick: () => file.click()}, 'Abrir archivo\u2026'), file,
      h('button', {onclick: () => { if (project) ta.value = JSON.stringify(project, null, 1); }}, 'Ver proyecto normalizado'),
      field('G\u00e9nero (si el JSON no lo dice)', preSel, 'inline')),
    h('div', {class: 'row'}, field('Ejemplos', exSel, 'inline'),
      h('button', {onclick: async () => { ta.value = await getText('/api/example?name=' + encodeURIComponent(exSel.value)); loadJson(ta.value); }}, 'Cargar ejemplo')),
    h('p', {class: 'hint'}, 'Formatos aceptados: (1) spec descriptivo como neon_rain_v2_spec.json / shadow_corner.json; (2) proyecto can\u00f3nico "midi-forge/1" (lo que exporta el bot\u00f3n Proyecto); (3) JSON de eventos con notas (se reproduce tal cual).'),
    h('h3', {}, 'Lo que se interpret\u00f3'), reportList(adapterReport));
}
function tabGlobal(p) {
  const g = project.global, e = project.ending, redo = renderPanel;
  const ts = g.time_signature;
  p.append(h('h3', {}, 'Proyecto'), h('div', {class: 'row'}, field('Descripci\u00f3n', txtIn(project, 'meta.description', {w: '420px'}))),
    h('h3', {}, 'Tiempo y tonalidad'),
    h('div', {class: 'row'}, field('BPM', numIn(g, 'bpm', {step: 1, min: 20, max: 300})),
      field('Comp\u00e1s', h('span', {class: 'row', style: 'margin:0;gap:4px'}, numIn(ts, '0', {int: true, min: 1, max: 32}), '/', numIn(ts, '1', {int: true, min: 1, max: 32}))),
      field('Tonalidad (p.ej. "D minor", "F# dorian")', txtIn(g, 'key', {w: '190px'})),
      field('Ticks por negra', numIn(g, 'ticks_per_beat', {int: true, min: 96, max: 960}))),
    h('h3', {}, 'Semilla y humanizaci\u00f3n'),
    h('div', {class: 'row'}, field('Semilla', h('span', {class: 'row', style: 'margin:0;gap:4px'}, numIn(g, 'seed', {int: true}),
        h('button', {class: 'small', title: 'Nueva semilla', onclick: () => { g.seed = Math.floor(Math.random() * 99999); renderPanel(); changed(); }}, '\ud83c\udfb2'))),
      field('Humanizaci\u00f3n (0-2)', numIn(g, 'humanize', {step: 0.1, min: 0, max: 3})), field('Tope de velocidad', numIn(g, 'velocity_cap', {int: true, min: 40, max: 127})),
      field('Rango pitch-bend (st)', numIn(g, 'pitch_bend_range', {int: true, min: 1, max: 24})),
      chkIn(g, 'repair_clashes', 'Reparar choques de semitono', changed, true)),
    h('h3', {}, 'G\u00e9nero / preset de bloques'),
    h('div', {class: 'row'}, field('Preset', selIn(g, 'preset', META.presets)),
      h('button', {onclick: async () => {
        if (!confirm('Esto reemplaza TODOS los bloques por los valores por defecto del preset "' + g.preset + '". \u00bfContinuar?')) return;
        const r = await API('/api/apply_preset', {project, preset: g.preset}); project = r.project; renderPanel(); changed();
      }}, 'Aplicar a todos los bloques')),
    h('h3', {}, 'Render FX (MP3 / WAV)'), renderFxUI(),
    h('h3', {}, 'Final'),
    h('div', {class: 'row'}, chkIn(e.fade_out, 'enabled', 'Fade out (CC11) en el outro'), field('Exponente', numIn(e.fade_out, 'exponent', {step: 0.1}))),
    h('div', {class: 'row'}, chkIn(e.tape_stop, 'enabled', 'Tape-stop (cinta que se apaga)'), field('Compases', numIn(e.tape_stop, 'bars', {step: 0.5, min: 0.5})),
      field('Semitonos', numIn(e.tape_stop, 'semitones', {step: 0.1})), field('Exponente', numIn(e.tape_stop, 'exponent', {step: 0.1}))));
}

function renderFxUI() {
  if (!project.render) {
    return h('div', {class: 'row'}, h('button', {onclick: () => {
      project.render = {enabled: true, lowpass_hz: 9000, loudness_lufs: -16, fade_out_seconds: 12, fade_curve: 'exp',
        noise: {hiss: {level: 0.0012, profile: {intro: 1, outro: 1, default: 0.25}}, crackle: {per_second: 3, level: 0.03, profile: {intro: 1, outro: 1, default: 0.25}}}};
      renderPanel(); changed();
    }}, 'Activar Render FX'), h('span', {class: 'hint'}, 'Lowpass, hiss, crackle, loudness (LUFS) y fade al exportar audio.'));
  }
  const r = project.render, n = r.noise = r.noise || {}, hiss = n.hiss = n.hiss || {level: 0.0012, profile: {default: 1}}, cr = n.crackle = n.crackle || {per_second: 3, level: 0.03, profile: {default: 1}};
  const prof = (o) => h('span', {class: 'row', style: 'margin:0;gap:4px'}, ['intro', 'outro', 'default'].map((k) => h('span', {class: 'hint'}, k + ' \u00d7', numIn(o, 'profile.' + k, {step: 0.05, min: 0}))));
  return h('div', {}, h('div', {class: 'row'}, chkIn(r, 'enabled', 'Aplicar al exportar', changed, true),
      field('Lowpass (Hz, vac\u00edo = no)', numIn(r, 'lowpass_hz', {int: true, optional: true, min: 200})), field('Loudness LUFS (vac\u00edo = no)', numIn(r, 'loudness_lufs', {optional: true, step: 0.5})),
      field('Fade out (s)', numIn(r, 'fade_out_seconds', {optional: true, min: 0})), field('Curva', selIn(r, 'fade_curve', ['exp', 'tri']))),
    h('div', {class: 'row'}, field('Hiss (nivel 0-1)', numIn(hiss, 'level', {step: 0.0005, min: 0})), prof(hiss)),
    h('div', {class: 'row'}, field('Crackle (clicks/s)', numIn(cr, 'per_second', {step: 0.5, min: 0})), field('Nivel', numIn(cr, 'level', {step: 0.005, min: 0})), prof(cr)),
    h('div', {class: 'hint'}, 'Servidor con FFmpeg: todo (loudnorm en 2 pasadas). MP3 del navegador: lowpass, ruido, fade y normalizaci\u00f3n de pico.'),
    h('div', {class: 'row'}, h('button', {class: 'small danger', onclick: () => { delete project.render; renderPanel(); changed(); }}, 'Quitar Render FX')));
}
function tabTracks(p) {
  project.tracks.forEach((t, i) => {
    const prog = t.role === 'drums' ? h('span', {class: 'pill'}, 'Canal 10 (GM drums)') :
      field('Instrumento GM', selIn(t, 'program', META.gm_names.map((n, k) => ({v: k, l: k + ' \u00b7 ' + n})), {num: true}));
    p.append(h('div', {class: 'card'},
      h('div', {class: 'row', style: 'margin-top:0'}, h('b', {style: 'color:' + ROLE_COLOR[t.role]}, t.id), field('Nombre', txtIn(t, 'name', {w: '200px'})),
        h('span', {class: 'pill'}, t.role), chkIn(t, 'enabled', 'activa', changed, true), chkIn(t, 'mute', 'mute'), chkIn(t, 'solo', 'solo'),
        h('span', {class: 'spacer'}), h('button', {class: 'small danger', onclick: () => { if (!confirm('Eliminar pista ' + t.id + '?')) return; project.tracks.splice(i, 1); project.sections.forEach((s) => delete s.blocks[t.id]); renderPanel(); changed(); }}, 'Eliminar')),
      h('div', {class: 'row'}, prog, t.role === 'drums' ? null : field('Canal', numIn(t, 'channel', {int: true, min: 1, max: 16})),
        field('Volumen', numIn(t, 'volume', {int: true, min: 0, max: 127})), field('Pan', numIn(t, 'pan', {int: true, min: 0, max: 127})),
        field('Reverb', numIn(t, 'reverb', {int: true, min: 0, max: 127})), field('Chorus', numIn(t, 'chorus', {int: true, min: 0, max: 127}))),
      h('div', {class: 'row'}, field('Desafinaci\u00f3n (bend)', numIn(t, 'detune', {int: true})), field('Offset (ticks)', numIn(t, 'offset_ticks', {int: true})),
        field('Jitter (ticks)', numIn(t, 'jitter_ticks', {int: true, min: 0})), field('Jitter vel.', numIn(t, 'vel_jitter', {int: true, min: 0})),
        field('Rango MIDI', rangeIn(t, 'range')), t.role === 'bass' || t.role === 'lead' ? chkIn(t, 'mono', 'mon\u00f3fono', changed, true) : null)));
  });
  const roleSel = h('select', {}, META.roles.map((r) => h('option', {value: r}, r)));
  p.append(h('div', {class: 'row'}, roleSel, h('button', {onclick: async () => {
    const role = roleSel.value; let id = role, n = 2; while (project.tracks.some((t) => t.id === id)) id = role + '_' + n++;
    const used = new Set(project.tracks.filter((t) => t.role !== 'drums').map((t) => t.channel)); let ch = 1; while (used.has(ch) || ch === 10) ch++;
    project.tracks.push(Object.assign({}, clone(META.role_defaults[role]), {id, name: id, role, channel: role === 'drums' ? 10 : ch, enabled: true, mute: false, solo: false}));
    const r = await API('/api/normalize', {json: project}); project = r.project; renderPanel(); changed();
  }}, '+ A\u00f1adir pista')));
}
function tabSections(p) {
  const total = project.sections.reduce((a, s) => a + s.bars, 0), bb = project.global.time_signature[0] * 4 / project.global.time_signature[1];
  p.append(h('div', {class: 'hint'}, total + ' compases \u00b7 ' + Math.floor(total * bb * 60 / project.global.bpm / 60) + ':' + String(Math.round(total * bb * 60 / project.global.bpm) % 60).padStart(2, '0')));
  project.sections.forEach((s, i) => {
    const chordsTxt = h('input', {type: 'text', spellcheck: 'false', style: 'width:100%'}); chordsTxt.value = s.chords.map((c) => (typeof c === 'object' ? c.chord + ':' + (c.bars || '') : c)).join(' ');
    chordsTxt.addEventListener('input', () => { s.chords = chordsTxt.value.split(/[\s,]+/).filter(Boolean); changed(); });
    const vel = s.velocity || [];
    const move = (d) => { const j = i + d; if (j < 0 || j >= project.sections.length) return; [project.sections[i], project.sections[j]] = [project.sections[j], project.sections[i]]; renderPanel(); changed(); };
    p.append(h('div', {class: 'card'},
      h('div', {class: 'row', style: 'margin-top:0'}, h('b', {}, (i + 1) + '.'), field('Nombre', txtIn(s, 'name', {w: '160px'})), field('Tipo', selIn(s, 'kind', META.kinds)),
        field('Compases', numIn(s, 'bars', {int: true, min: 1})), field('Comp./acorde', numIn(s, 'chord_bars', {step: 0.5, min: 0.25})), chkIn(s, 'final', 'final'),
        h('span', {class: 'spacer'}), h('button', {class: 'small', onclick: () => move(-1)}, '\u2191'), h('button', {class: 'small', onclick: () => move(1)}, '\u2193'),
        h('button', {class: 'small', onclick: async () => { const c = clone(s); c.id = s.id + '_copia'; c.name = s.name + ' (copia)'; project.sections.splice(i + 1, 0, c); const r = await API('/api/normalize', {json: project}); project = r.project; renderPanel(); changed(); }}, 'Duplicar'),
        h('button', {class: 'small danger', onclick: () => { if (project.sections.length < 2) return; project.sections.splice(i, 1); renderPanel(); changed(); }}, '\u2715')),
      field('Acordes (separados por espacio; "Dm:2" = 2 compases)', chordsTxt),
      h('div', {class: 'row'}, field('Velocidad base (ini\u2013fin, vac\u00edo = por bloque)', rangeIn(s, 'velocity')),
        field('Compases por ciclo (opcional)', numIn(s, 'cycle_bars', {int: true, optional: true, min: 1}))),
      h('details', {}, h('summary', {class: 'hint'}, 'Cambios de acorde por compas (sus4, splits) \u2013 JSON'),
        h('div', {class: 'hint'}, 'Ej: [{"when":{"bar_mod":[4,3],"cycle_parity":"odd"},"split":[[0,2,"Csus4"],[2,4,"C"]]}]'), jsonArea(s, 'chord_overrides', {rows: 3}))));
  });
  p.append(h('button', {onclick: async () => {
    const n = project.sections.length + 1; project.sections.push({id: 'seccion_' + n, name: 'Secci\u00f3n ' + n, kind: 'verse', bars: 8, chords: ['Dm', 'Bb', 'F', 'C'], chord_bars: 1, blocks: {}});
    const r = await API('/api/normalize', {json: project}); project = r.project; renderPanel(); changed();
  }}, '+ A\u00f1adir secci\u00f3n'));
}

// ------------------------------------------------------------------ bloques
function blockLabel(b, role) {
  if (!b || !b.enabled || b.style === 'none') return 'off';
  const sch = META.style_schema[role] || {}; const st = sch[b.style];
  return st ? st.label.split(' ')[0] : b.style;
}
function tabBlocks(p) {
  if (project.raw) { p.append(h('p', {class: 'hint'}, 'Este proyecto viene de un JSON de eventos: no tiene bloques generativos. Usa la pesta\u00f1a Pistas (mute/solo/mezcla).')); return; }
  const tbl = h('table', {class: 'mx'});
  const head = h('tr', {}, h('th', {}, ''), project.sections.map((s, i) => h('th', {title: s.name}, h('div', {}, s.name.length > 11 ? s.name.slice(0, 10) + '\u2026' : s.name), h('small', {class: 'hint'}, s.bars + ' c. '),
    h('button', {class: 'small', title: 'Activar/desactivar toda la secci\u00f3n', onclick: () => { const on = !project.tracks.some((t) => s.blocks[t.id].enabled); project.tracks.forEach((t) => { s.blocks[t.id].enabled = on; }); renderPanel(); changed(); }}, '\u25d0'))));
  tbl.append(head);
  project.tracks.forEach((t) => {
    tbl.append(h('tr', {}, h('th', {style: 'color:' + ROLE_COLOR[t.role]}, t.id, h('br'),
      h('button', {class: 'small', title: 'Activar/desactivar toda la pista', onclick: () => { const on = !project.sections.some((s) => s.blocks[t.id].enabled); project.sections.forEach((s) => { s.blocks[t.id].enabled = on; }); renderPanel(); changed(); }}, '\u25d0')),
      project.sections.map((s, si) => {
        const b = s.blocks[t.id]; const on = b && b.enabled && b.style !== 'none';
        const range = b && (b.from_bar || b.to_bar != null) ? ' ' + (b.from_bar || 0) + '\u2013' + (b.to_bar == null ? s.bars : b.to_bar) : '';
        return h('td', {class: 'cell' + (on ? '' : ' off') + (sel.s === si && sel.t === t.id ? ' sel' : ''), onclick: () => { sel = {s: si, t: t.id}; renderPanel(); }}, blockLabel(b, t.role), h('small', {}, range));
      })));
  });
  p.append(tbl, h('p', {class: 'hint'}, 'Clic en una celda para editar ese bloque (secci\u00f3n \u00d7 pista).'));
  const sec = project.sections[sel.s], tr = project.tracks.find((t) => t.id === sel.t);
  if (!sec || !tr) return;
  const b = sec.blocks[tr.id], sch = META.style_schema[tr.role];
  const adv = h('textarea', {rows: 6, spellcheck: 'false'}); const syncAdv = () => { adv.value = JSON.stringify(b.params || {}, null, 1); adv.classList.remove('bad'); };
  const onP = () => { syncAdv(); changed(); };
  syncAdv();
  adv.addEventListener('change', () => { try { b.params = JSON.parse(adv.value); adv.classList.remove('bad'); renderPanel(); changed(); } catch (e) { adv.classList.add('bad'); } });
  const velMode = b.velocity == null ? 'inherit' : (Array.isArray(b.velocity) ? 'ramp' : 'fixed');
  const velBox = h('span', {class: 'row', style: 'margin:0'});
  const drawVel = () => {
    velBox.innerHTML = '';
    if (velMode === 'fixed') velBox.append(numIn(b, 'velocity', {int: true, min: 1, max: 127}));
    if (velMode === 'ramp') velBox.append(rangeIn(b, 'velocity'));
  };
  const velSel = h('select', {onchange: () => {
    const m = velSel.value;
    if (m === 'inherit') delete b.velocity; else if (m === 'fixed') b.velocity = 80; else b.velocity = [60, 100];
    renderPanel(); changed();
  }}, [['inherit', 'heredar de la secci\u00f3n'], ['fixed', 'fija'], ['ramp', 'rampa ini\u2192fin']].map(([v, l]) => h('option', {value: v}, l)));
  velSel.value = velMode; drawVel();
  const seedIn = numIn(b, 'seed', {int: true, optional: true, ph: '0'});
  const form = h('div', {class: 'row'}, (sch[b.style] && sch[b.style].fields || []).map((f) => paramField(b.params, f, onP)));
  if (tr.role === 'drums' && b.style === 'pattern') {
    form.append(h('button', {class: 'small', onclick: () => {
      const pr = META.drum_presets[(b.params && b.params.preset) || 'synth_verse'];
      b.params.layers = clone(pr.layers); b.params.fills = clone(pr.fills); renderPanel(); changed();
    }}, 'Copiar capas del preset para editarlas'));
  }
  p.append(h('div', {class: 'card sel'},
    h('div', {class: 'row', style: 'margin-top:0'}, h('b', {style: 'color:' + ROLE_COLOR[tr.role]}, tr.name), h('span', {class: 'pill'}, sec.name + ' \u00b7 ' + sec.bars + ' compases \u00b7 ' + sec.kind)),
    h('div', {class: 'row'}, chkIn(b, 'enabled', 'bloque activo', () => { renderPanel(); changed(); }, true),
      field('Estilo', selIn(b, 'style', Object.keys(sch).map((k) => ({v: k, l: sch[k].label})), {on: () => { b.params = {}; renderPanel(); changed(); }})),
      field('Desde compás', numIn(b, 'from_bar', {int: true, min: 0, max: sec.bars})), field('Hasta (excl.)', numIn(b, 'to_bar', {int: true, optional: true, min: 0, max: sec.bars, ph: String(sec.bars)}))),
    h('div', {class: 'row'}, field('Velocidad', velSel), velBox,
      field('Semilla del bloque', h('span', {class: 'row', style: 'margin:0;gap:4px'}, seedIn,
        h('button', {class: 'small', title: 'Variar este bloque', onclick: () => { b.seed = Math.floor(Math.random() * 9999); renderPanel(); changed(); }}, '\ud83c\udfb2')))),
    h('h3', {}, 'Par\u00e1metros del estilo'), form,
    h('details', {}, h('summary', {class: 'hint'}, 'Par\u00e1metros avanzados (JSON)'), adv),
    h('div', {class: 'row'},
      h('button', {onclick: async () => {
        const nb = await API('/api/default_block', {preset: project.global.preset, role: tr.role, kind: sec.kind, bars: sec.bars, section: {final: sec.final, occurrence: sec.occurrence}});
        sec.blocks[tr.id] = nb; renderPanel(); changed();
      }}, 'Restaurar por defecto'),
      h('button', {onclick: () => { project.sections.forEach((s) => { if (s.kind === sec.kind && s !== sec) s.blocks[tr.id] = clone(b); }); renderPanel(); changed(); }}, 'Copiar a secciones del mismo tipo'),
      h('button', {onclick: () => { project.sections.forEach((s) => { if (s !== sec) s.blocks[tr.id] = clone(b); }); renderPanel(); changed(); }}, 'Copiar a todas las secciones'))));
}

// ------------------------------------------------------------------ lead
const pitchName = (n) => (typeof n === 'number' ? ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'][n % 12] + (Math.floor(n / 12) - 1) : n);
const phrasesToText = (arr) => (arr || []).map((n) => [n.bar, n.beat, pitchName(n.pitch), n.dur].concat(n.vel != null ? [n.vel] : []).join(' ')).join('\n');
function textToPhrases(t) {
  const out = [];
  for (const line of t.split('\n')) {
    const w = line.trim().split(/[\s,;]+/); if (w.length < 4 || w[0].startsWith('#')) continue;
    const n = {bar: parseInt(w[0], 10), beat: parseFloat(w[1]), pitch: isNaN(+w[2]) ? w[2] : +w[2], dur: parseFloat(w[3])};
    if (w[4] != null && w[4] !== '') n.vel = parseInt(w[4], 10);
    if (isNaN(n.bar) || isNaN(n.beat) || isNaN(n.dur)) throw new Error('L\u00ednea inv\u00e1lida: ' + line);
    out.push(n);
  }
  return out;
}
function tabLead(p) {
  p.append(h('p', {class: 'hint'}, 'Una nota por l\u00ednea: "compas beat nota duraci\u00f3n [velocidad]" (compas desde 0, relativo a la secci\u00f3n). Ej: 0 0.5 F5 2.5. Si una secci\u00f3n no tiene frases, el bloque Lead "auto" genera una.'));
  project.sections.forEach((s) => {
    const ta = h('textarea', {rows: 5, spellcheck: 'false'}); ta.value = phrasesToText(project.lead.phrases[s.id]);
    const seed = h('input', {type: 'number', value: '1', style: 'width:60px'}), dens = h('input', {type: 'number', step: '0.05', value: '0.35', style: 'width:64px'});
    const cont = h('select', {}, ['arch', 'rising', 'falling', 'flat'].map((x) => h('option', {value: x}, x)));
    const msg = h('span', {class: 'hint'});
    p.append(h('div', {class: 'card'}, h('div', {class: 'row', style: 'margin-top:0'}, h('b', {}, s.name), h('span', {class: 'pill'}, (project.lead.phrases[s.id] || []).length + ' notas'), msg), ta,
      h('div', {class: 'row'}, h('button', {class: 'small primary', onclick: () => {
        try { const arr = textToPhrases(ta.value); if (arr.length) project.lead.phrases[s.id] = arr; else delete project.lead.phrases[s.id]; msg.textContent = 'Aplicado (' + arr.length + ' notas)'; changed(); } catch (e) { msg.textContent = e.message; }
      }}, 'Aplicar'),
      h('button', {class: 'small', onclick: () => { delete project.lead.phrases[s.id]; ta.value = ''; msg.textContent = 'Borrado'; changed(); }}, 'Borrar'),
      field('semilla', seed, 'inline'), field('densidad', dens, 'inline'), field('', cont, 'inline'),
      h('button', {class: 'small', onclick: async () => {
        try { const r = await API('/api/suggest_lead', {project, section_id: s.id, seed: +seed.value, params: {density: +dens.value, contour: cont.value}}); ta.value = phrasesToText(r.notes); msg.textContent = 'Sugerencia lista: pulsa Aplicar'; } catch (e) { msg.textContent = e.message; }
      }}, 'Sugerir frase'))));
  });
}
function tabAuto(p) {
  const ta = h('textarea', {rows: 14, spellcheck: 'false'}); ta.value = JSON.stringify(project.automation || [], null, 1);
  const msg = h('span', {class: 'hint'});
  const tpl = (o) => { const a = JSON.parse(ta.value || '[]'); a.push(o); ta.value = JSON.stringify(a, null, 1); };
  const sid = project.sections[0].id;
  p.append(h('h3', {}, 'Automatizaci\u00f3n de CC (rampas)'), h('p', {class: 'hint'}, 'Cada entrada: pista (id, rol, "pitched" o "all"), cc, desde/hasta {section, bar}, v0\u2192v1, curve. CC11 = expresi\u00f3n; CC7 = volumen; CC1 = modulaci\u00f3n.'), ta,
    h('div', {class: 'row'}, h('button', {class: 'primary', onclick: () => { try { project.automation = JSON.parse(ta.value); ta.classList.remove('bad'); msg.textContent = 'Aplicado'; changed(); } catch (e) { ta.classList.add('bad'); msg.textContent = e.message; } }}, 'Aplicar'),
      h('button', {onclick: () => tpl({track: 'pad', cc: 11, from: {section: sid, bar: 0}, to: {section: sid, bar: 4}, v0: 35, v1: 127})}, '+ fade-in'),
      h('button', {onclick: () => tpl({track: 'strings', cc: 11, from: {section: sid, bar: 0}, to: {section: sid, bar: 8}, v0: 88, v1: 127, curve: 1})}, '+ swell'),
      h('button', {onclick: () => tpl({track: 'all', cc: 7, from: {section: sid, bar: 0}, to: {section: sid, bar: 2}, v0: 60, v1: 100})}, '+ rampa de volumen'), msg));
}
function tabReport(p) {
  p.append(h('h3', {}, 'Interpretaci\u00f3n del JSON'), reportList(adapterReport));
  if (!result) { p.append(h('p', {class: 'hint'}, 'Genera para ver la validaci\u00f3n.')); return; }
  const v = result.validation;
  const kv = h('div', {class: 'kv'});
  const add = (k, val, cls) => { kv.append(h('div', {}, k), h('div', {class: cls || ''}, val)); };
  add('Compases / duraci\u00f3n', v.bars + ' \u00b7 ' + Math.floor(v.duration_seconds / 60) + ':' + String(Math.round(v.duration_seconds % 60)).padStart(2, '0'));
  add('Choques de semitono (no intencionales)', v.semitone_clashes_unintended, v.semitone_clashes_unintended ? 'err' : 'ok');
  add('Reparaciones autom\u00e1ticas', v.repairs.moved + ' movidas \u00b7 ' + v.repairs.removed + ' quitadas');
  add('Notas disonantes intencionales', v.intentional_dissonant_notes);
  if (v.max_pitched_polyphony && v.max_pitched_polyphony.raw) add('Polifon\u00eda m\u00e1x.', v.max_pitched_polyphony.raw + ' (' + v.max_pitched_polyphony.ignoring_legato_overlap + ' sin solape legato)');
  if (v.snare_avg_delay_ms != null) add('Retraso medio del snare', v.snare_avg_delay_ms + ' ms');
  for (const [tid, o] of Object.entries(v.voice_leading || {})) add('Voice leading \u00b7 ' + tid, 'mov. medio ' + o.avg_movement + ' st, m\u00e1x ' + o.max_movement + ', gaps ' + (o.gaps || []).join('\u2013') + ', sin 3\u00aa ' + o.chords_without_third);
  add('Secciones vac\u00edas', v.empty_sections.length ? v.empty_sections.join(', ') : 'ninguna', v.empty_sections.length ? 'warnc' : 'ok');
  add('Notas por pista', Object.entries(v.note_counts).map(([k, n]) => k + ': ' + n).join(' \u00b7 '));
  p.append(h('h3', {}, 'Validaci\u00f3n'), kv);
  if (v.compliance && v.compliance.length) {
    const icon = {pass: '\u2714', fail: '\u2716', warn: '\u26a0', info: '\u2139'}, cls = {pass: 'ok', fail: 'err', warn: 'warnc', info: ''};
    p.append(h('h3', {}, 'Cumplimiento del brief (autom\u00e1tico)'), h('div', {}, v.compliance.map((c) => h('div', {class: 'rep'},
      h('span', {class: cls[c.status]}, icon[c.status] + ' '), h('b', {}, c.label + (c.requested ? ' *' : '')), h('div', {class: 'hint', style: 'margin-left:18px'}, c.detail)))),
      h('div', {class: 'hint'}, '* = pedido expl\u00edcitamente en el JSON.'));
  }
  if (v.warnings.length) p.append(h('h3', {}, 'Avisos del motor'), reportList(v.warnings.map((m) => ({level: 'warn', msg: m}))));
  p.append(h('h3', {}, 'Velocidades por secci\u00f3n [min, m\u00e1x, n]'), h('pre', {}, JSON.stringify(v.velocity_by_section, null, 1)));
}

// ------------------------------------------------------------------ piano roll
function drawRoll() {
  const cv = $('#roll'), wrap = $('#rollWrap'); const ctx = cv.getContext && cv.getContext('2d'); if (!ctx) return;
  const lg = $('#legend'); lg.innerHTML = '';
  if (!result) { cv.width = wrap.clientWidth || 600; cv.height = 120; ctx.fillStyle = '#0b0d13'; ctx.fillRect(0, 0, cv.width, cv.height); ctx.fillStyle = '#8a91a8'; ctx.fillText('Genera para ver el piano roll.', 12, 24); return; }
  const ev = result.events, ppb = +$('#zoom').value, W = Math.ceil(ev.total_beats * ppb) + 40, top = 18, drumH = 64, H = 330;
  cv.width = W; cv.height = H;
  ctx.fillStyle = '#0b0d13'; ctx.fillRect(0, 0, W, H);
  let lo = 127, hi = 0;
  ev.tracks.forEach((t) => { if (t.role !== 'drums') t.notes.forEach((n) => { lo = Math.min(lo, n[2]); hi = Math.max(hi, n[2]); }); });
  if (lo > hi) { lo = 48; hi = 84; } lo -= 2; hi += 2;
  const ph = (H - top - drumH - 6) / (hi - lo + 1);
  ev.sections.forEach((s, i) => {
    ctx.fillStyle = i % 2 ? 'rgba(255,255,255,.025)' : 'rgba(255,255,255,0)'; ctx.fillRect(s.t0 * ppb, top, (s.t1 - s.t0) * ppb, H - top);
    ctx.fillStyle = '#8a91a8'; ctx.font = '11px sans-serif'; ctx.fillText(s.name, s.t0 * ppb + 4, 12);
    ctx.strokeStyle = '#2a2f42'; ctx.beginPath(); ctx.moveTo(s.t0 * ppb, 0); ctx.lineTo(s.t0 * ppb, H); ctx.stroke();
  });
  ctx.strokeStyle = 'rgba(255,255,255,.05)';
  for (let b = 0; b < ev.total_beats; b += ev.bar_beats) { ctx.beginPath(); ctx.moveTo(b * ppb, top); ctx.lineTo(b * ppb, H); ctx.stroke(); }
  const dnotes = [...new Set(ev.tracks.filter((t) => t.role === 'drums').flatMap((t) => t.notes.map((n) => n[2])))].sort((a, b) => a - b);
  ev.tracks.forEach((t) => {
    const lab = h('label', {}, h('input', {type: 'checkbox', checked: !hidden[t.id], onchange: (e) => { hidden[t.id] = !e.target.checked; drawRoll(); }}), h('i', {style: 'background:' + ROLE_COLOR[t.role]}), t.id);
    lg.append(lab);
    if (hidden[t.id]) return;
    ctx.fillStyle = ROLE_COLOR[t.role];
    t.notes.forEach((n) => {
      const x = n[0] * ppb, w = Math.max(2, n[1] * ppb - 1), a = 0.35 + 0.65 * (n[3] / 127);
      ctx.globalAlpha = a;
      if (t.role === 'drums') { const k = dnotes.indexOf(n[2]); const y = H - drumH + (k / Math.max(1, dnotes.length)) * drumH; ctx.fillRect(x, y, Math.max(2, 3), drumH / Math.max(4, dnotes.length) - 1); }
      else ctx.fillRect(x, top + (hi - n[2]) * ph, w, Math.max(2, ph - 1));
    });
    ctx.globalAlpha = 1;
  });
  $('#playhead').style.left = seekBeat * ppb + 'px';
}
function fmtClock(sec) { sec = Math.max(0, sec); return Math.floor(sec / 60) + ':' + String(Math.floor(sec % 60)).padStart(2, '0'); }

// ------------------------------------------------------------------ vista previa (WebAudio)
class Player {
  constructor(ev) { this.ev = ev; this.ac = null; this.timer = null; this.raf = null; this.t0 = 0; this.startBeat = 0; this.playing = false; }
  noise(ac) { if (!this._nb) { const b = ac.createBuffer(1, ac.sampleRate, ac.sampleRate), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; this._nb = b; } return this._nb; }
  build(ac, startBeat, t0, fx) {
    const ev = this.ev; this.ac = ac; this.spb = 60 / ev.bpm; this.startBeat = startBeat; this.t0 = t0;
    const comp = ac.createDynamicsCompressor(); comp.threshold.value = -14; comp.ratio.value = 6;
    const master = ac.createGain(); master.gain.value = 0.8; comp.connect(master); this.master = master;
    let outNode = ac.destination;
    if (fx && fx.lowpass_hz) { const lp = ac.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = fx.lowpass_hz; lp.connect(ac.destination); outNode = lp; }
    master.connect(outNode); this.outNode = outNode;
    this.tg = {};
    ev.tracks.forEach((t) => {
      const g = ac.createGain(), pan = ac.createStereoPanner ? ac.createStereoPanner() : null;
      g.gain.value = Math.pow((t.volume || 100) / 127, 1.5) * 0.9 * (t.gain == null ? 1 : t.gain);
      if (pan) { pan.pan.value = ((t.pan == null ? 64 : t.pan) - 64) / 64; g.connect(pan); pan.connect(comp); } else g.connect(comp);
      const ex = ac.createGain(); ex.connect(g); this.tg[t.id] = ex;
      (t.expr || []).forEach(([b, v]) => { const tt = this.t0 + (b - startBeat) * this.spb; ex.gain.setValueAtTime(Math.pow(v / 127, 2), Math.max(tt, this.t0)); });
      if (!(t.expr || []).length) ex.gain.value = 1;
    });
  }
  start(startBeat) {
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) throw new Error('Este navegador no soporta WebAudio.');
    const ac = new AC(), ev = this.ev;
    this.build(ac, startBeat, ac.currentTime + 0.15);
    this.list = [];
    ev.tracks.forEach((t) => { if (hidden[t.id]) return; t.notes.forEach((n) => { if (n[0] + n[1] >= startBeat) this.list.push({t, n}); }); });
    this.list.sort((a, b) => a.n[0] - b.n[0]); this.idx = 0; this.playing = true;
    this.timer = setInterval(() => this.pump(), 120); this.pump();
    const loop = () => { if (!this.playing) return; const beat = this.startBeat + (ac.currentTime - this.t0) / this.spb; this.onTick(beat); if (beat > ev.total_beats + 3) { this.stop(); this.onEnd && this.onEnd(); return; } this.raf = requestAnimationFrame(loop); };
    loop();
  }
  onTick() {}
  pump() {
    const ac = this.ac; if (!ac) return; const horizon = ac.currentTime + 1.2;
    while (this.idx < this.list.length) {
      const {t, n} = this.list[this.idx]; const when = this.t0 + (n[0] - this.startBeat) * this.spb;
      if (when > horizon) break; this.idx++;
      try { this.voice(t, n, Math.max(when, ac.currentTime)); } catch (e) { /* una nota fallida no detiene la reproduccion */ }
    }
  }
  bendAt(t, beat) { const b = t.bends || []; let v = 0; for (let i = 0; i < b.length; i++) { if (b[i][0] <= beat + 1e-6) v = b[i][1]; else break; } return v; }
  voice(t, n, when) {
    const ac = this.ac, dest = this.tg[t.id], spb = this.spb, dur = Math.max(0.05, n[1] * spb), vel = n[3] / 127, pitch = n[2];
    if (t.role === 'drums') return this.drum(dest, pitch, when, vel);
    const f = 440 * Math.pow(2, (pitch - 69) / 12), amp = Math.pow(vel, 1.4);
    const cfg = {pad: [['sawtooth', -7], ['sawtooth', 7]], strings: [['sawtooth', -5], ['sawtooth', 5]], bass: [['sawtooth', 0], ['sine', 0, 0.5]], lead: [['sawtooth', 0], ['square', 6]], arp: [['sine', 0], ['triangle', 0, 2]]}[t.role] || [['sine', 0]];
    const par = {pad: {lp: 1100, a: 0.5, r: 1.0, g: 0.11}, strings: {lp: 2400, a: 0.12, r: 0.5, g: 0.1}, bass: {lp: 600, a: 0.005, r: 0.1, g: 0.3}, lead: {lp: 4200, a: 0.02, r: 0.25, g: 0.12}, arp: {lp: 5000, a: 0.003, r: 0.3, g: 0.22}}[t.role];
    const flt = ac.createBiquadFilter(); flt.type = 'lowpass'; flt.frequency.value = par.lp; const env = ac.createGain();
    flt.connect(env); env.connect(dest);
    const end = when + dur;
    if (t.role === 'arp') { env.gain.setValueAtTime(0.0001, when); env.gain.linearRampToValueAtTime(par.g * amp, when + par.a); env.gain.exponentialRampToValueAtTime(0.0002, when + Math.max(0.5, dur * 1.6)); }
    else { env.gain.setValueAtTime(0.0001, when); env.gain.linearRampToValueAtTime(par.g * amp, when + par.a); env.gain.setValueAtTime(par.g * amp, Math.max(when + par.a, end)); env.gain.linearRampToValueAtTime(0.0001, end + par.r); }
    const stop = (t.role === 'arp' ? when + Math.max(0.5, dur * 1.6) : end + par.r) + 0.05;
    const b0 = n[0], b1 = n[0] + n[1] + par.r / spb;
    cfg.forEach(([type, det, mult]) => {
      const o = ac.createOscillator(); o.type = type; o.frequency.value = f * (mult || 1); o.detune.value = det + this.bendAt(t, b0);
      (t.bends || []).forEach(([bb, c]) => { if (bb > b0 && bb < b1) o.detune.setValueAtTime(det + c, when + (bb - b0) * spb); });
      o.connect(flt); o.start(when); o.stop(stop);
    });
  }
  drum(dest, note, when, vel) {
    const ac = this.ac, nz = () => { const s = ac.createBufferSource(); s.buffer = this.noise(ac); return s; };
    const env = (g, a, d) => { g.gain.setValueAtTime(a, when); g.gain.exponentialRampToValueAtTime(0.0005, when + d); };
    const sweep = (f0, f1, d, a) => { const o = ac.createOscillator(), g = ac.createGain(); o.frequency.setValueAtTime(f0, when); o.frequency.exponentialRampToValueAtTime(f1, when + d * 0.6); env(g, a * vel, d); o.connect(g); g.connect(dest); o.start(when); o.stop(when + d + 0.05); };
    const nburst = (type, freq, d, a, off) => { const s = nz(), fl = ac.createBiquadFilter(), g = ac.createGain(); fl.type = type; fl.frequency.value = freq; const w = when + (off || 0); g.gain.setValueAtTime(a * vel, w); g.gain.exponentialRampToValueAtTime(0.0005, w + d); s.connect(fl); fl.connect(g); g.connect(dest); s.start(w); s.stop(w + d + 0.05); };
    if (note === 35 || note === 36) sweep(130, 42, 0.38, 0.95);
    else if (note === 38 || note === 40) { nburst('bandpass', 1900, 0.2, 0.55); sweep(220, 130, 0.12, 0.4); }
    else if (note === 39) [0, 0.012, 0.026].forEach((o) => nburst('bandpass', 1300, 0.09, 0.45, o));
    else if (note === 37) { nburst('highpass', 3000, 0.03, 0.3); sweep(900, 700, 0.05, 0.25); }
    else if (note === 42 || note === 44) nburst('highpass', 7500, 0.05, 0.28);
    else if (note === 46) nburst('highpass', 7000, 0.32, 0.28);
    else if ([41, 43, 45, 47, 48, 50].includes(note)) { const f = 70 * Math.pow(2, (note - 41) / 12 * 1.1); sweep(f * 1.8, f, 0.3, 0.7); }
    else if (note === 49 || note === 57 || note === 55) nburst('highpass', 5200, 1.5, 0.35);
    else if (note === 51 || note === 53) { nburst('highpass', 6500, 0.5, 0.2); sweep(3100, 3000, 0.4, 0.12); }
    else nburst('highpass', 4000, 0.1, 0.25);
  }
  stop() {
    this.playing = false; clearInterval(this.timer); cancelAnimationFrame(this.raf);
    if (this.ac) { try { this.ac.close(); } catch (e) {} this.ac = null; }
  }
}
function togglePlay() {
  const btn = $('#btnPlay');
  if (player && player.playing) { player.stop(); btn.innerHTML = '&#9654; Escuchar'; return; }
  if (!result) { setStatus('Genera primero (Ctrl+Enter).', 'warn'); return; }
  try {
    player = new Player(result.events);
    player.onTick = (beat) => { seekBeat = beat; const ppb = +$('#zoom').value; $('#playhead').style.left = beat * ppb + 'px'; $('#clock').textContent = fmtClock(beat * 60 / result.events.bpm);
      const w = $('#rollWrap'); const x = beat * ppb; if (x > w.scrollLeft + w.clientWidth * 0.85 || x < w.scrollLeft) w.scrollLeft = Math.max(0, x - 80); };
    player.onEnd = () => { btn.innerHTML = '&#9654; Escuchar'; seekBeat = 0; };
    player.start(seekBeat >= result.events.total_beats ? 0 : seekBeat); btn.innerHTML = '&#9632; Parar';
  } catch (e) { setStatus(e.message, 'err'); }
}

// ------------------------------------------------------------------ MP3
// Render offline con el mismo sintetizador de la vista previa + codificacion con lamejs (incluido en lame.min.js).
async function renderOffline(ev, fx) {
  const OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext; if (!OAC) throw new Error('Este navegador no soporta OfflineAudioContext.');
  const sr = 44100, music = ev.total_beats * 60 / ev.bpm, secs = music + 3;
  const ac = new OAC(2, Math.ceil(secs * sr), sr);
  fx = fx && fx.enabled !== false ? fx : null;
  const p = new Player(ev); p.build(ac, 0, 0, fx);
  ev.tracks.forEach((t) => { if (hidden[t.id]) return; t.notes.forEach((n) => { try { p.voice(t, n, n[0] * p.spb); } catch (e) { /* nota fallida: se omite */ } }); });
  const spb = 60 / ev.bpm, prof = (pf, kind) => (pf && (pf[kind] != null ? pf[kind] : (pf.default != null ? pf.default : 1)));
  const noise = fx && fx.noise;
  if (noise && noise.hiss) {   // hiss: ruido blanco con ganancia por seccion
    const nb = ac.createBuffer(1, sr * 2, sr), d = nb.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const src = ac.createBufferSource(); src.buffer = nb; src.loop = true; const g = ac.createGain(); const base = noise.hiss.level || 0.0012;
    ev.sections.forEach((sec) => g.gain.setValueAtTime(base * prof(noise.hiss.profile, sec.kind), sec.t0 * spb));
    src.connect(g); g.connect(p.outNode); src.start(0);
  }
  if (noise && noise.crackle) {   // crackle: clicks aleatorios con envolvente por seccion
    const cb = ac.createBuffer(1, Math.ceil(secs * sr), sr), d = cb.getChannelData(0), c = noise.crackle;
    for (let k = 0, n = Math.floor(music * (c.per_second || 3)); k < n; k++) {
      const t = Math.random() * (music - 0.2), sec = ev.sections.find((x) => t >= x.t0 * spb && t < x.t1 * spb);
      const amp = (c.level || 0.03) * prof(c.profile, sec ? sec.kind : 'default') * (0.25 + 0.75 * Math.random()) * (Math.random() < 0.5 ? -1 : 1), pos = Math.floor(t * sr);
      for (let i = 0, len = 14 + Math.floor(Math.random() * 34); i < len; i++) d[pos + i] += amp * Math.pow(0.82, i) * (i % 2 ? -0.6 : 1);
    }
    const src = ac.createBufferSource(); src.buffer = cb; src.connect(p.outNode); src.start(0);
  }
  if (fx && fx.fade_out_seconds && music > fx.fade_out_seconds) {
    p.master.gain.setValueAtTime(0.8, music - fx.fade_out_seconds);
    if (fx.fade_curve === 'exp') p.master.gain.exponentialRampToValueAtTime(0.0005, music); else p.master.gain.linearRampToValueAtTime(0, music);
  }
  return ac.startRendering();
}
async function encodeMp3(buf, kbps, onProgress) {
  if (typeof lamejs === 'undefined') throw new Error('No se cargo lame.min.js (encoder MP3).');
  const L = buf.getChannelData(0), R = buf.numberOfChannels > 1 ? buf.getChannelData(1) : L, n = L.length;
  let peak = 0; for (let i = 0; i < n; i += 7) { const a = Math.abs(L[i]), b = Math.abs(R[i]); if (a > peak) peak = a; if (b > peak) peak = b; }
  const k = peak > 0.001 ? 0.9 / peak : 1, enc = new lamejs.Mp3Encoder(2, buf.sampleRate, kbps), bs = 1152 * 8, out = [];
  const i16 = (x) => Math.max(-32768, Math.min(32767, Math.round(x * k * 32767)));
  for (let i = 0, c = 0; i < n; i += bs, c++) {
    const m = Math.min(bs, n - i), l = new Int16Array(m), r = new Int16Array(m);
    for (let j = 0; j < m; j++) { l[j] = i16(L[i + j]); r[j] = i16(R[i + j]); }
    const d = enc.encodeBuffer(l, r); if (d.length) out.push(new Uint8Array(d));
    if (c % 30 === 0) { if (onProgress) onProgress(Math.round(100 * i / n)); await new Promise((res) => setTimeout(res, 0)); }
  }
  const end = enc.flush(); if (end.length) out.push(new Uint8Array(end));
  return new Blob(out, {type: 'audio/mpeg'});
}
async function downloadMp3() {
  if (!project) return;
  const btn = $('#btnMp3'), name = slug(project.meta.name) + '.mp3';
  btn.disabled = true;
  try {
    if (!result || dirty) await generate();
    if (!result) return;
    if ($('#mp3Mode').value === 'auto' && META.mp3) {
      setStatus('Renderizando MP3 con FluidSynth (instrumentos reales)\u2026');
      try { const r = await API('/api/mp3', {project}); const fxh = r.headers.get('X-Forge-FX'); download(name, await r.blob()); setStatus('MP3 listo (FluidSynth). FX: ' + (fxh || 'ninguno') + '.', 'ok'); return; }
      catch (e) { setStatus('El servidor no pudo crear el MP3 (' + e.message + '); se usa el navegador\u2026', 'warn'); }
    }
    setStatus('Renderizando audio en el navegador\u2026');
    await new Promise((res) => setTimeout(res, 30));
    const t0 = Date.now(), tick = setInterval(() => setStatus('Renderizando audio en el navegador\u2026 ' + Math.round((Date.now() - t0) / 1000) + ' s (puede tardar; el resto de la p\u00e1gina sigue activa)'), 500);
    let buf; try { buf = await renderOffline(result.events, project.render); } finally { clearInterval(tick); }
    const blob = await encodeMp3(buf, 192, (pc) => setStatus('Codificando MP3\u2026 ' + pc + '%'));
    download(name, blob); setStatus('MP3 listo (' + (blob.size / 1048576).toFixed(1) + ' MB, sintetizador del navegador).', 'ok');
  } catch (e) { setStatus('MP3: ' + e.message, 'err'); }
  finally { btn.disabled = false; }
}

// ------------------------------------------------------------------ generar / descargar
async function generate() {
  if (!project) return;
  clearTimeout(genTimer); const t0 = performance.now(); setStatus('Generando\u2026');
  try {
    if (player && player.playing) togglePlay();
    const r = await API('/api/generate', {project});
    result = r; dirty = false;
    ['#btnMid', '#btnEvents', '#btnSave'].forEach((s) => { $(s).disabled = false; });
    const v = r.validation, bad = v.semitone_clashes_unintended;
    setStatus('Listo: ' + v.bars + ' compases \u00b7 ' + fmtClock(v.duration_seconds) + ' \u00b7 ' + Object.values(v.note_counts).reduce((a, b) => a + b, 0) + ' notas \u00b7 choques: ' + bad + ' \u00b7 ' + Math.round(performance.now() - t0) + ' ms', bad || v.warnings.length ? 'warn' : 'ok');
    drawRoll(); if (tab === 'report') renderPanel();
  } catch (e) { setStatus('Error al generar: ' + e.message, 'err'); }
}
function b64ToBlob(b64) { const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return new Blob([u], {type: 'audio/midi'}); }
function bindHeader() {
  $('#btnGen').onclick = generate; $('#btnPlay').onclick = togglePlay;
  $('#btnMid').onclick = () => { if (result) download(slug(project.meta.name) + '.mid', b64ToBlob(result.midi_b64)); };
  $('#btnProj').onclick = () => { if (project) download(slug(project.meta.name) + '.project.json', JSON.stringify(project, null, 1), 'application/json'); };
  $('#btnEvents').onclick = async () => { try { const e = await API('/api/events', {project}); download(slug(project.meta.name) + '.events.json', JSON.stringify(e), 'application/json'); } catch (er) { setStatus(er.message, 'err'); } };
  $('#btnMp3').onclick = downloadMp3;
  $('#btnWav').onclick = async () => {
    setStatus('Renderizando WAV con FluidSynth\u2026');
    try { const r = await API('/api/wav', {project}); download(slug(project.meta.name) + '.wav', await r.blob()); setStatus('WAV listo.', 'ok'); } catch (e) { setStatus('WAV: ' + e.message, 'err'); }
  };
  $('#btnSave').onclick = async () => { try { const r = await API('/api/save', {project}); setStatus('Guardado: ' + r.saved.join(' , '), 'ok'); } catch (e) { setStatus(e.message, 'err'); } };
  $('#projName').addEventListener('input', (e) => { if (project) { project.meta.name = e.target.value; } });
  $('#zoom').addEventListener('input', drawRoll);
  $('#rollWrap').addEventListener('click', (e) => { if (!result) return; const wrap = $('#rollWrap'); const x = e.clientX - wrap.getBoundingClientRect().left + wrap.scrollLeft; seekBeat = Math.max(0, x / +$('#zoom').value); $('#playhead').style.left = x + 'px'; $('#clock').textContent = fmtClock(seekBeat * 60 / result.events.bpm); });
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); generate(); }
    else if (e.code === 'Space' && !/INPUT|TEXTAREA|SELECT|BUTTON/.test(document.activeElement.tagName)) { e.preventDefault(); togglePlay(); }
  });
}

async function init() {
  bindHeader(); renderTabs();
  try {
    META = await API('/api/meta'); $('#ver').textContent = 'v' + META.version;
    $('#btnMp3').disabled = false; $('#btnMp3').title = META.mp3 ? 'MP3 con FluidSynth (instrumentos reales)' : 'MP3 con el sintetizador del navegador (instala FluidSynth + ffmpeg para instrumentos reales)';
    $('#btnWav').disabled = !META.wav.available; if (!META.wav.available) $('#btnWav').title = 'WAV no disponible: instala FluidSynth y copia un .sf2 a soundfonts/ (ver README)';
    const ex = await API('/api/examples');
    if (ex.length) { const txt = await getText('/api/example?name=' + encodeURIComponent(ex[0].file)); await loadJson(txt); tab = 'blocks'; renderTabs(); renderPanel(); await generate(); }
    else { setStatus('Listo. Pega un JSON en la pesta\u00f1a JSON.', 'ok'); renderPanel(); }
  } catch (e) { setStatus('No se pudo iniciar: ' + e.message, 'err'); }
}
window.addEventListener('DOMContentLoaded', init);
if (typeof window !== 'undefined') window.__forge = {renderOffline, encodeMp3, downloadMp3};
