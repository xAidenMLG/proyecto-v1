// Vista PRODUCTION — los 7 perfiles reales + seed/WAV por defecto del proyecto.
import { state, production, markDirty } from '../state.js';
import { el, $, select, toastOk, toastErr } from '../ui.js';
import { API } from '../api.js';

export async function render(host) {
  host.innerHTML = '';
  host.append(el('h1', {}, 'Production'),
    el('p', { class: 'sub' }, 'Perfiles de producción oficiales (identificadores internos exactos del backend). Ningún perfil nuevo: son las configuraciones aprobadas y congeladas de los motores.'));

  host.append(perfilesCard(), defaultsCard(), audioCard());
}

function perfilesCard() {
  const p = production();
  const grid = el('div', { class: 'profile-grid' });
  for (const prof of state.caps.perfiles) {
    const card = el('div', { class: 'profile-card' + (p.profile === prof.id ? ' sel' : '') },
      el('div', { class: 'pid' }, prof.id + (prof.es_default ? ' · default' : '')),
      el('h3', {}, prof.label),
      el('div', { class: 'engine-dots' },
        Object.entries(prof.engines || {}).map(([k, v]) =>
          el('span', { class: 'eng ' + (v === true ? 'on' : v === false ? 'off' : '') },
            v === true ? `${k} ✓` : v === false ? `${k} ·` : `${k} —`)),
        prof.variation ? el('span', { class: 'eng on' }, 'variación: ' + prof.variation) : null));
    card.onclick = () => {
      p.profile = prof.id;
      markDirty(true);
      $$('.profile-card', grid).forEach(c => c.classList.remove('sel'));
      card.classList.add('sel');
      toastOk('Perfil de producción: ' + prof.id);
    };
    grid.append(card);
  }
  return el('div', { class: 'card' }, el('h2', {}, 'Perfil de producción'), grid,
    el('div', { class: 'tiny', style: 'margin-top:10px' },
      'original = camino ORIGINAL (delegación byte a byte a MIDI Forge, sin jazz_engine). El resto son presets de motores sobre la arquitectura existente.'));
}

function defaultsCard() {
  const p = production();
  const seed = el('input', { type: 'number', value: p.seed ?? '', placeholder: 'usa global.seed',
    oninput: () => { p.seed = seed.value === '' ? null : parseInt(seed.value) || 0; markDirty(true); } });
  const outName = el('input', { type: 'text', value: p.out_name || '', placeholder: 'slug del título',
    oninput: () => { p.out_name = outName.value.trim(); markDirty(true); } });
  const wav = el('input', { type: 'checkbox', checked: !!p.render_wav,
    onchange: () => { p.render_wav = wav.checked; markDirty(true); } });
  return el('div', { class: 'card' }, el('h2', {}, 'Defaults del proyecto (Production)'),
    el('div', { class: 'grid-3' },
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Seed por defecto'), seed),
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Nombre de salida'), outName),
      el('label', { class: 'fld' }, el('span', { class: 'lbl' }, 'Renderizar WAV'),
        el('label', { class: 'row', style: 'gap:8px' }, wav, el('span', { class: 'tiny' }, 'requiere FluidSynth + .sf2')))));
}

async function audioCard() {
  const card = el('div', { class: 'card' }, el('h2', {}, 'Audio (WAV)'));
  let a = state.caps.audio || {};
  const info = el('div', { class: 'tiny muted' });
  const render = () => {
    info.innerHTML = '';
    info.append(el('div', {}, 'FluidSynth: ', a.fluidsynth ? el('span', { class: 'mono', style: 'color:var(--ok)' }, a.fluidsynth) : el('span', { style: 'color:var(--err)' }, 'no encontrado')),
      el('div', {}, 'Soundfont: ', a.soundfont_encontrado ? el('span', { class: 'mono', style: 'color:var(--ok)' }, a.soundfont_encontrado) : el('span', { style: 'color:var(--warn)' }, 'no encontrado')),
      el('div', { style: 'margin-top:6px' }, a.wav_posible
        ? el('span', { class: 'badge ok' }, 'WAV DISPONIBLE')
        : el('span', { class: 'badge warn' }, 'SOLO MIDI (instala FluidSynth + soundfont para WAV)')));
  };
  render();

  const sfPath = el('input', { type: 'text', placeholder: 'ruta al .sf2 (vacío = autodetección)', style: 'flex:2' });
  const fsPath = el('input', { type: 'text', placeholder: 'ruta a fluidsynth(.exe) (opcional)', style: 'flex:2' });
  try {
    const s = await API.getSettings();
    sfPath.value = s.soundfont_path || '';
    fsPath.value = s.fluidsynth_path || '';
  } catch { /* no bloquear */ }

  const saveBtn = el('button', { class: 'btn sm', onclick: async () => {
    try {
      await API.putSettings({ soundfont_path: sfPath.value.trim(), fluidsynth_path: fsPath.value.trim() });
      state.caps = await API.capabilities();
      a = state.caps.audio;
      render();
      toastOk('Ajustes de audio guardados');
    } catch (e) { toastErr(e); }
  } }, 'Guardar rutas');

  card.append(el('div', { class: 'row', style: 'align-items:flex-end; margin-top:8px' },
    el('label', { class: 'fld', style: 'flex:2' }, el('span', { class: 'lbl' }, 'Soundfont (.sf2)'), sfPath),
    el('label', { class: 'fld', style: 'flex:2' }, el('span', { class: 'lbl' }, 'Ejecutable FluidSynth'), fsPath),
    saveBtn), el('div', { style: 'margin-top:10px' }, info));
  return card;
}
