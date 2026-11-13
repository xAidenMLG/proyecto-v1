/* DMD COMPOSER — capa de acceso a la API local (solo localhost). */
"use strict";

const API = {
  async req(method, url, body) {
    const opt = { method, headers: {} };
    if (body !== undefined) {
      opt.headers["Content-Type"] = "application/json";
      opt.body = JSON.stringify(body);
    }
    const r = await fetch(url, opt);
    let data = null;
    try { data = await r.json(); } catch (e) { /* respuesta no-JSON */ }
    if (!r.ok) {
      const msg = (data && (data.error || data.detail)) || `HTTP ${r.status}`;
      throw new Error(msg);
    }
    return data;
  },
  get(url) { return this.req("GET", url); },
  post(url, body) { return this.req("POST", url, body || {}); },
  put(url, body) { return this.req("PUT", url, body || {}); },
  del(url) { return this.req("DELETE", url); },

  /* ---------- MIDI por generación (vista Output) ---------- */
  generarMidi(pid, genId, events = true) {
    return this.post(`/api/projects/${pid}/generations/${genId}/midi`, { events });
  },
  estadoMidi(pid, genId) {
    return this.get(`/api/projects/${pid}/generations/${genId}/midi`);
  },
  cancelarMidi(pid, genId) {
    return this.post(`/api/projects/${pid}/generations/${genId}/midi/cancel`, {});
  },
  async descargarMidi(pid, genId) {
    // descarga del .mid vía blob + anchor (nombre del bloque midi: nombre)
    let nombre = null;
    try { const st = await this.estadoMidi(pid, genId); if (st && st.midi && st.midi.nombre) nombre = st.midi.nombre; }
    catch (e) { /* sin estado: seguimos con un nombre por defecto */ }
    const r = await fetch(`/api/projects/${pid}/generations/${genId}/midi/download`);
    if (!r.ok) {
      let d = null;
      try { d = await r.json(); } catch (e) { /* respuesta no-JSON */ }
      throw new Error((d && (d.detail || d.error)) || `HTTP ${r.status}`);
    }
    const blob = await r.blob();
    const base = String(nombre || genId).replace(/[\\/:*?"<>|]+/g, "_").trim() || genId;
    const fname = base.toLowerCase().endsWith(".mid") ? base : `${base}.mid`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = fname;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    return fname;
  },
  eventosGen(pid, genId) {
    return this.get(`/api/projects/${pid}/generations/${genId}/events`);
  },
  artefactoMidi(pid, genId, fname) {
    return this.get(`/api/projects/${pid}/generations/${genId}/midi/artifacts/${fname}`);
  },
};
