/* DMD COMPOSER — estado global de la UI (proyecto activo + catálogos). */
"use strict";

const State = {
  catalog: null,          // catálogos reales (del manifiesto DMD)
  system: null,           // estado de integración
  projects: [],           // lista de proyectos
  pid: null,              // proyecto activo
  project: null,          // proyecto cargado (dict)
  lastCompose: null,      // último resultado de compose

  instrumentLabels: {
    sax_tenor: "Sax tenor", rhodes: "Rhodes", vibraphone: "Vibraphone",
    bass: "Bass", drums: "Drums", piano: "Piano", pad: "Pad", strings: "Strings",
  },
  typeLabels: {
    intro: "Intro", verse: "Verse", pre_chorus: "Pre-Chorus", chorus: "Chorus",
    bridge: "Bridge", break: "Break / Interlude / Solo", outro: "Outro / Coda",
  },
  moodLabels: { melancholic: "Melancólico", dark: "Oscuro", hopeful: "Esperanzador",
                tense: "Tenso", neutral: "Neutro" },

  decLabel(eje) {
    return {
      identity: "Identidad musical", accessibility: "Accesibilidad", bpm: "BPM",
      key: "Tonalidad", language: "Lenguaje armónico", resolution: "Resolución",
      harmonic_rhythm_bars: "Ritmo armónico (compases/acorde)",
      harmony_mode: "Modo de armonía", mood: "Mood (preferencias ponderadas)",
      atmosphere: "Atmósfera", groove: "Groove", spaces: "Espacios musicales",
      protagonist: "Instrumento protagonista", production: "Perfil de producción",
      ending: "Cierre (ending)", seed: "Semilla del randomizador",
    }[eje] || eje;
  },

  async loadSystem() {
    this.system = await API.get("/api/system");
    this.catalog = this.system.catalogos;
    return this.system;
  },

  async loadProjects() {
    this.projects = await API.get("/api/projects");
    return this.projects;
  },

  async openProject(pid) {
    this.pid = pid;
    this.project = await API.get(`/api/projects/${pid}`);
    return this.project;
  },

  async saveProject() {
    if (!this.project) return;
    this.project = await API.put(`/api/projects/${this.pid}`, {
      name: this.project.name,
      notes: this.project.notes,
      diversity: this.project.diversity,
      decisions: this.project.decisions,
      instruments: this.project.instruments,
      sections: this.project.sections,
      harmony_sections: this.project.harmony_sections,
      production: this.project.production,
    });
    return this.project;
  },

  decision(eje) {
    const d = (this.project.decisions || {})[eje];
    return d || { mode: "free", value: null };
  },

  setDecision(eje, mode, value) {
    if (mode === "free") this.project.decisions[eje] = { mode: "free", value: null };
    else if (mode === "auto") this.project.decisions[eje] = { mode: "auto", value: null };
    else this.project.decisions[eje] = { mode: "fixed", value };
  },

  counts() {
    const d = (this.project && this.project.decisions) || {};
    let fija = 0, auto = 0, libre = 0;
    for (const k of Object.keys(d)) {
      if (d[k].mode === "fixed") fija++;
      else if (d[k].mode === "auto") auto++;
      else libre++;
    }
    const insts = Object.keys((this.project && this.project.instruments) || {}).length;
    return { fija, auto, libre, insts };
  },
};
