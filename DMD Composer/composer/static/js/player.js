/* DMD COMPOSER — reproductor WebAudio de vista previa (MIDI por generación).
   Fuente: nucleo_engine_project/web/app.js, líneas 442-522 (class Player) y
   patrón togglePlay de las líneas 523-534.
   copia literal; único cambio: hidden por opts (constructor (ev, opts = {}) y
   this.hidden en vez de la global hidden del Forge).
   NOTA de producto (D22): esta escucha es una VISTA PREVIA WebAudio y NO
   equivale al render con el soundfont externo; aquí no hay UI de
   render/conversión de audio (sin WAV/MP3/soundfonts). */
"use strict";

/* ------------------------------------------------- Player (copia literal) */
class Player {
  constructor(ev, opts = {}) { this.ev = ev; this.hidden = (opts && opts.hidden) || {}; this.ac = null; this.timer = null; this.raf = null; this.t0 = 0; this.startBeat = 0; this.playing = false; }
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
    ev.tracks.forEach((t) => { if (this.hidden[t.id]) return; t.notes.forEach((n) => { if (n[0] + n[1] >= startBeat) this.list.push({t, n}); }); });
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

/* ---------------------- wrapper de sesión única (patrón togglePlay) ------ */
const ComposerPlayback = {
  player: null,
  ev: null,
  hidden: {},

  /* valida la forma de events.json ANTES de arrancar; lanza si no es válido */
  load(ev, opts = {}) {
    const ok = ev && typeof ev.bpm === "number" && Array.isArray(ev.tracks) &&
      ev.tracks.every(t => Array.isArray(t.notes));
    if (!ok) throw new Error("events.json no válido");
    this.ev = ev;
    this.hidden = (opts && opts.hidden) || {};   // por generación: {} = todas las pistas visibles
    return this;
  },

  playing() { return !!(this.player && this.player.playing); },

  /* cierra la sesión actual sin fugas de timers ni AudioContexts */
  stop() {
    if (this.player) { try { this.player.stop(); } catch (e) { /* ya parado */ } this.player = null; }
  },

  /* anti-solape: una sola sesión; stop() antes de un nuevo play() */
  play(startBeat, onTick, onEnd) {
    this.stop();
    if (!this.ev) throw new Error("no hay events.json cargado (usa load)");
    const p = new Player(this.ev, { hidden: this.hidden });
    this.player = p;
    p.onTick = (beat) => { if (onTick) onTick(beat); };
    p.onEnd = () => { this.player = null; if (onEnd) onEnd(); };
    try { p.start(startBeat || 0); }
    catch (e) { this.player = null; throw e; }   // p.ej. 'Este navegador no soporta WebAudio.'
  },
};

window.Player = Player;
window.ComposerPlayback = ComposerPlayback;
