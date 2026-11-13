/* DMD COMPOSER — arranque, navegación y barra lateral. */
"use strict";

const App = {
  async init() {
    document.querySelectorAll("#nav button").forEach(b =>
      b.addEventListener("click", () => this.go(b.dataset.view)));

    document.getElementById("proj-new").addEventListener("click", () =>
      guard(async () => {
        const name = prompt("Nombre de la obra:", "Nueva composición");
        if (!name) return;
        const p = await API.post("/api/projects", { name });
        await this.loadProjects();
        await this.open(p.pid);
        this.refreshSidebar();
      }, "proyecto creado"));

    document.getElementById("proj-dup").addEventListener("click", () =>
      guard(async () => {
        if (!State.pid) return;
        const p = await API.post(`/api/projects/${State.pid}/duplicate`, {});
        await this.loadProjects();
        await this.open(p.pid);
        this.refreshSidebar();
      }, "proyecto duplicado"));

    document.getElementById("proj-del").addEventListener("click", () =>
      guard(async () => {
        if (!State.pid || !confirm("¿Borrar el proyecto y sus generaciones?")) return;
        await API.del(`/api/projects/${State.pid}`);
        State.pid = null; State.project = null;
        await this.loadProjects();
        if (State.projects.length) await this.open(State.projects[0].pid);
        this.refreshSidebar();
      }, "proyecto borrado"));

    document.getElementById("dmd-refresh").addEventListener("click", () =>
      guard(async () => {
        const fpAntes = State.system && State.system.fingerprint;
        const r = await API.post("/api/integration/refresh");
        await this.refreshSystem();
        this.go(document.querySelector("#nav button.active")?.dataset.view || "setup");
        if (!r.ok) {
          status("Verificación DMD: el DMD real no respondió (" + (r.origen || "sin manifiesto") + ")", "err");
          return;
        }
        const fpAhora = State.system.fingerprint;
        if (fpAntes && fpAhora && fpAntes !== fpAhora) {
          status(`DMD CAMBIADO: fingerprint ${fpAntes} → ${fpAhora}. Catálogos y recetas recalculados.`, "err");
        } else {
          status(`DMD verificado ahora (${r.origen}) · ${fpAhora}`, "ok");
        }
      }, null));

    await this.refreshSystem();
    await this.loadProjects();
    if (State.projects.length) await this.open(State.projects[0].pid);
    else {
      // primera ejecución: crear el proyecto de bienvenida para que la UI
      // arranque siempre con un proyecto activo
      const p = await API.post("/api/projects", { name: "Mi primera composición" });
      await this.loadProjects();
      await this.open(p.pid);
      status("Proyecto de bienvenida creado. Empieza por la vista 1 · Setup.", "ok");
    }
    this.refreshSidebar();
  },

  async refreshSystem() {
    const sys = await State.loadSystem();
    const st = document.getElementById("dmd-status");
    if (State.system.dmd_descubierto) {
      st.className = "ok";
      st.textContent = `DMD: ${State.system.dmd_descubierto.split(/[\\/]/).pop()} · ${State.system.fingerprint}`;
    } else {
      st.className = "bad";
      st.textContent = "DMD no descubierto — configura la ruta (catalogo de instantánea)";
    }
  },

  async loadProjects() { await State.loadProjects(); this.refreshProjSelect(); },

  refreshProjSelect() {
    const sel = document.getElementById("proj-select");
    sel.innerHTML = "";
    State.projects.forEach(p => {
      sel.appendChild(el("option", { value: p.pid, text: `${p.name} (${p.pid})` }));
    });
    if (State.pid) sel.value = State.pid;
    sel.onchange = () => guard(async () => { await this.open(sel.value); this.refreshSidebar(); });
  },

  async open(pid) {
    await State.openProject(pid);
    this.refreshProjSelect();
    this.go(document.querySelector("#nav button.active")?.dataset.view || "setup");
  },

  refreshSidebar() {
    const meta = document.getElementById("proj-meta");
    if (State.project) {
      meta.textContent = `${State.project.name}\nsecciones: ${State.project.sections.length}\n` +
        `modo armonía: ${State.decision("harmony_mode").value || "guided"}`;
    } else meta.textContent = "sin proyecto";
    const c = State.counts();
    document.getElementById("dec-counter").textContent =
      `fijadas: ${c.fija} · automáticas: ${c.auto} · libres: ${c.libre}\ninstrumentos configurados: ${c.insts}`;
    const seed = State.decision("seed");
    document.getElementById("status-seed").textContent =
      seed.mode === "fixed" && seed.value ? `seed fijada: ${seed.value}` : "seed automática";
  },

  go(view) {
    document.querySelectorAll("#nav button").forEach(b =>
      b.classList.toggle("active", b.dataset.view === view));
    const root = document.getElementById("view");
    const renderers = { setup: viewSetup, structure: viewStructure, harmony: viewHarmony,
                        randomizer: viewRandomizer, preview: viewPreview, output: viewOutput };
    (renderers[view] || viewSetup)(root);
    this.refreshSidebar();
  },
};

window.addEventListener("DOMContentLoaded", () =>
  App.init().catch(e => status(`Error de arranque: ${e.message}`, "err")));
