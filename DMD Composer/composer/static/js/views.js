/* DMD COMPOSER — vistas (módulos A–E + salida).
   Regla de la UI: todo lo que se muestra viene de /api/system (catálogos
   REALES del DMD) o del proyecto. Nada inventado en el cliente. */
"use strict";

/* ---------------------------------------------------------------- helpers */
function el(tag, attrs = {}, ...children) {
  const n = document.createElement(tag);
  const deferred = [];
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k === "value" || k === "selected" || k === "checked" || k === "disabled") deferred.push([k, v]);
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) n.setAttribute(k, v);
  }
  for (const c of children) {
    if (c === null || c === undefined) continue;
    n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  // las propiedades de estado se aplican DESPUÉS de insertar los hijos
  for (const [k, v] of deferred) {
    if (v === null || v === undefined) continue;
    if (k === "value") n.value = v;
    else n[k] = !!v;
  }
  return n;
}

function panel(title, ...children) {
  const p = el("div", { class: "panel" }, el("h2", { text: title }));
  children.forEach(c => p.appendChild(c));
  return p;
}

function status(msg, kind) {
  const s = document.getElementById("status-msg");
  s.textContent = msg;
  s.style.color = kind === "err" ? "var(--err)" : kind === "ok" ? "var(--ok)" : "var(--tx-2)";
}

async function guard(fn, okMsg) {
  try {
    await fn();
    if (okMsg) status(okMsg, "ok");
  } catch (e) {
    status(`Error: ${e.message}`, "err");
  }
}

function modeTag(mode) {
  const t = { fixed: ["Fijada", "pill-fija"], auto: ["Automática", "pill-auto"],
              free: ["Libre", "pill-libre"] }[mode] || [mode, ""];
  return el("span", { class: `mode-tag ${t[1]}`, text: t[0] });
}

/* Fila de decisión: [label] [modo] [input de valor si fijada] */
function decisionRow(eje, opts = {}) {
  const st = State.decision(eje);
  const wrap = el("div", { class: "row" });
  wrap.appendChild(el("label", { text: State.decLabel(eje) }));
  const modoOpts = [el("option", { value: "fixed", text: "Fijada (la exijo)" }),
                    el("option", { value: "auto", text: "Automática (Composer elige)" })];
  if (!opts.required) modoOpts.push(el("option", { value: "free", text: "Libre (decide el motor)" }));
  else modoOpts.push(el("option", { value: "free", disabled: true,
    text: "Libre — no disponible: el contrato exige este campo" }));
  const modeSel = el("select", {}, ...modoOpts);
  modeSel.value = st.mode;
  const valueBox = el("span", { class: "row" });
  const rebuildValue = () => {
    valueBox.innerHTML = "";
    if (modeSel.value !== "fixed") { valueBox.appendChild(modeTag(modeSel.value)); return; }
    valueBox.appendChild(opts.valueInput ? opts.valueInput(st.value) : el("input", { type: "text" }));
    valueBox.appendChild(modeTag("fixed"));
  };
  modeSel.addEventListener("change", () => {
    const v = modeSel.value === "fixed" ? (opts.defaultFixed !== undefined ? opts.defaultFixed : "") : null;
    State.setDecision(eje, modeSel.value, v);
    rebuildValue();
    saveQuiet();
  });
  valueBox.addEventListener("change", () => {
    const inp = valueBox.querySelector("input,select");
    if (inp && modeSel.value === "fixed") {
      State.setDecision(eje, "fixed", opts.parse ? opts.parse(inp.value) : inp.value);
      saveQuiet();
    }
  });
  rebuildValue();
  wrap.appendChild(modeSel);
  wrap.appendChild(valueBox);
  if (opts.hint) wrap.appendChild(el("span", { class: "dim", text: opts.hint }));
  return wrap;
}

function saveQuiet() {
  guard(async () => { await State.saveProject(); App.refreshSidebar(); }, null);
}

/* ============================================================ 1 · SETUP */
function viewSetup(root) {
  const p = State.project;
  const cat = State.catalog;
  root.innerHTML = "";

  /* — módulo A: identidad — */
  const moodRow = decisionRow("mood", {
    valueInput: v => el("select", {}, ...Object.keys(State.moodLabels)
      .map(m => el("option", { value: m, text: State.moodLabels[m], selected: v === m }))),
  });
  const spacesRow = decisionRow("spaces", {
    valueInput: v => el("select", {},
      el("option", { value: "free", text: "sin preferencia" }),
      el("option", { value: "suggested", text: "sugeridos" }),
      el("option", { value: "mandatory", text: "obligatorios" })),
    hint: "espacios de aire en la composición",
  });
  const protRow = decisionRow("protagonist", {
    valueInput: v => {
      const s = el("select", {}, el("option", { value: "none", text: "— sin protagonista —" }),
        ...(cat.instruments || []).map(i => el("option", { value: i, text: State.instrumentLabels[i] || i })));
      s.value = v || "none";
      return s;
    },
    hint: "Automática = LEAD de la receta de la identidad · elige su distribución abajo (aceptar, modificar o rechazar)",
  });

  const panA = panel("A · Identidad musical",
    moodRow, spacesRow, protRow,
    el("p", { class: "hint",
      text: "El mood ajusta las preferencias ponderadas del randomizador (tonalidades, lenguaje, energía); NO va al doc. " +
            "El protagonista recibe una PROPUESTA de distribución (focus/active/enabled/density: campos reales del contrato) " +
            "que TÚ aceptas, modificas después o rechazas — nunca se aplica sola." }));

  /* — propuesta de distribución del protagonista (v1.1) — */
  const propPanel = panel("A · Distribución del protagonista (propuesta editable)");
  const propBox = el("div", {});
  const renderPropEstado = () => {
    propBox.innerHTML = "";
    const pp = (State.project.protagonist_proposal) || {};
    if (pp.estado) {
      propBox.appendChild(el("div", { class: pp.estado === "aplicada" ? "msg-ok" : "msg-tip",
        text: pp.estado === "aplicada"
          ? `Propuesta APLICADA (${pp.cambios_aplicados ?? "?"} cambios) para '${pp.protagonista}': los campos quedan editables abajo.`
          : `Propuesta RECHAZADA para '${pp.protagonista || "?"}': ningún campo fue tocado.` }));
    }
  };
  const renderProp = (prop) => {
    propBox.innerHTML = "";
    if (!prop.protagonista) {
      propBox.appendChild(el("div", { class: "msg-warn", text: (prop.notas || [""]).join(" ") || "sin protagonista" }));
      return;
    }
    propBox.appendChild(el("h2", { text: `Propuesta para ${prop.protagonista} — ${prop.cambios.length} cambio(s)` }));
    const t = el("table", {}, el("tr", {}, el("th", { text: "Donde" }), el("th", { text: "Campo" }),
      el("th", { text: "Antes" }), el("th", { text: "Después" }), el("th", { text: "Por qué" })));
    (prop.cambios || []).forEach(c => t.appendChild(el("tr", {},
      el("td", { text: c.tipo === "instruments" ? `instrumento ${c.iid}` : c.sid }),
      el("td", { text: c.campo }),
      el("td", { class: "dim mono", text: JSON.stringify(c.antes) ?? "—" }),
      el("td", { class: "mono", text: JSON.stringify(c.despues) }),
      el("td", { class: "dim", text: c.porque }))));
    propBox.appendChild(t);
    (prop.secciones_sin_cambio || []).forEach(sc => propBox.appendChild(el("div", { class: "dim",
      text: `${sc.sid}: ${sc.motivo}` })));
    (prop.notas || []).forEach(n => propBox.appendChild(el("div", { class: "msg-tip", text: n })));
    propBox.appendChild(el("div", { class: "row" },
      el("button", { class: "btn primary", text: "Aplicar propuesta", onclick: () =>
        guard(async () => {
          const r = await API.post(`/api/projects/${State.pid}/protagonist/apply`, {});
          State.project = r.proyecto;
          status(`propuesta aplicada: ${r.cambios_aplicados} cambio(s) — ya puedes editarlos`, "ok");
          App.go("setup");
        }, null) }),
      el("button", { class: "btn", text: "Rechazar (no tocar nada)", onclick: () =>
        guard(async () => {
          const r = await API.post(`/api/projects/${State.pid}/protagonist/reject`, {});
          State.project = r.proyecto;
          status("propuesta rechazada: ningún campo modificado", "ok");
          App.go("setup");
        }, null) })));
  };
  propPanel.appendChild(el("div", { class: "row" },
    el("button", { class: "btn", text: "Generar propuesta de distribución", onclick: () =>
      guard(async () => {
        await State.saveProject();
        const prop = await API.get(`/api/projects/${State.pid}/protagonist/proposal`);
        renderProp(prop);
      }, null) }),
    el("span", { class: "dim", text: "solo lectura hasta que aceptes;rechazar no modifica nada" })));
  renderPropEstado();
  propPanel.appendChild(propBox);

  /* — instrumentos (catálogo real) — */
  const instPanel = panel("A · Instrumentación (catálogo real del contrato)");
  instPanel.appendChild(el("p", { class: "hint",
    text: "Protagonista = prioridad funcional · Acompañante = presente y soporte · Off = apagado explícito · Auto = el motor decide con su receta." }));
  const instTable = el("table", {},
    el("tr", {}, el("th", { text: "Instrumento" }), el("th", { text: "Rol" }),
       el("th", { text: "Activación" }), el("th", { text: "Density (opcional)" })));
  for (const iid of cat.instruments || []) {
    const conf = p.instruments[iid] || { role: "auto" };
    const roleSel = el("select", {},
      el("option", { value: "auto", text: "Auto" }),
      el("option", { value: "protagonist", text: "Protagonista" }),
      el("option", { value: "support", text: "Acompañante" }),
      el("option", { value: "off", text: "Off" }));
    roleSel.value = conf.role || "auto";
    roleSel.addEventListener("change", () => { ensureInst(iid).role = roleSel.value; saveQuiet(); });
    const enabSel = el("select", {},
      el("option", { value: "", text: "— libre —" }),
      el("option", { value: "true", text: "enabled=true" }),
      el("option", { value: "false", text: "enabled=false" }));
    enabSel.value = conf.enabled === true ? "true" : conf.enabled === false ? "false" : "";
    enabSel.addEventListener("change", () => {
      const c = ensureInst(iid);
      c.enabled = enabSel.value === "" ? null : enabSel.value === "true";
      saveQuiet();
    });
    const densInp = el("input", { type: "number", step: "0.05", min: "0", max: "1",
      value: conf.density !== undefined && conf.density !== null ? conf.density : "" });
    densInp.addEventListener("change", () => {
      const c = ensureInst(iid);
      c.density = densInp.value === "" ? null : Math.max(0, Math.min(1, parseFloat(densInp.value)));
      saveQuiet();
    });
    instTable.appendChild(el("tr", {},
      el("td", { text: `${State.instrumentLabels[iid] || iid} ` }, el("span", { class: "dim mono", text: iid })),
      el("td", {}, roleSel), el("td", {}, enabSel), el("td", {}, densInp)));
  }
  instPanel.appendChild(instTable);

  /* — preferencias generales — */
  const pref = panel("A · Preferencias generales",
    decisionRow("identity", {
      required: true,
      valueInput: v => {
        const arch = (State.system && State.system.identidades_archivadas) || [];
        return el("select", {}, ...(cat.identities || []).map(i =>
          el("option", { value: i, text: arch.includes(i) ? `${i} — ARCHIVADA (histórica)` : i })));
      },
      hint: ((State.system && State.system.identidades_archivadas) || []).length
        ? `archivadas (solo compatibilidad histórica, se avisa al componer): ${(State.system.identidades_archivadas || []).join(", ")} · activa: ${State.system.identidad_activa || "dark_triphop"}`
        : "el contrato exige identidad; sin fijarla, Composer elige",
    }),
    decisionRow("accessibility", {
      required: true,
      valueInput: v => el("select", {}, ...(cat.accessibilities || []).map(a => el("option", { value: a, text: a }))),
    }),
    decisionRow("bpm", { valueInput: v => el("input", { type: "number", min: "20", max: "300", value: v ?? "" }),
      parse: v => { const n = parseInt(v, 10); if (isNaN(n)) throw new Error("BPM debe ser número"); return n; },
      hint: "20–300; el rango típico lo fija la receta de la identidad" }),
    decisionRow("key", {
      required: true,
      valueInput: v => el("input", { type: "text", placeholder: "D minor / C major / A dorian", value: v ?? "" }),
      hint: "el contrato exige tonalidad; sin fijarla, Composer elige por mood" }),
    decisionRow("language", {
      required: true,
      valueInput: v => el("select", {}, ...(cat.languages || []).map(l => el("option", { value: l, text: l }))),
      hint: "vocabulario de acordes: pop / híbrido / experimental" }),
    decisionRow("resolution", {
      valueInput: v => el("select", {}, ...(cat.resolutions || []).map(l => el("option", { value: l, text: l }))),
      hint: "gesto de transición entre secciones" }),
    decisionRow("harmonic_rhythm_bars", { valueInput: v => el("input", { type: "number", min: "1", max: "8", value: v ?? "" }),
      parse: v => { const n = parseInt(v, 10); if (isNaN(n)) throw new Error("ritmo armónico debe ser número"); return n; },
      hint: "1 = un acorde por compás; 2 = un acorde cada dos compases…" }),
    decisionRow("atmosphere", {
      valueInput: v => el("select", {}, ...["spacious", "medium", "dense"].map(a => el("option", { value: a, text: a }))),
      hint: "sesgo de densidad del randomizador" }),
    decisionRow("groove", {
      valueInput: v => el("select", {}, ...["laid_back", "steady", "driving"].map(a => el("option", { value: a, text: a }))),
      hint: "NO es tempo ni campo del doc: solo sesga la curva de BPM automático",
    }),
    decisionRow("ending", {
      valueInput: v => el("select", {}, ...["fade_out", "tape_stop", "none"].map(a => el("option", { value: a, text: a }))),
    }),
    decisionRow("production", {
      valueInput: v => el("select", {}, el("option", { value: "", text: "— elegir al generar —" }),
        ...(cat.perfiles || []).map(x => el("option", { value: x, text: x }))),
      hint: "se usa al generar el MIDI en Studio; NO entra en el JSON del contrato" }),
  );

  /* — diversidad + notas — */
  const divSel = el("select", {}, ...["restrained", "balanced", "adventurous"].map(d =>
    el("option", { value: d, text: { restrained: "Contenida", balanced: "Equilibrada", adventurous: "Aventurada" }[d] })));
  divSel.value = p.diversity || "balanced";
  divSel.addEventListener("change", () => { p.diversity = divSel.value; saveQuiet(); });
  const notesTa = el("textarea", { rows: "2", placeholder: "notas del proyecto (van al meta.notes del JSON)" });
  notesTa.value = p.notes || "";
  notesTa.addEventListener("change", () => { p.notes = notesTa.value; saveQuiet(); });
  const nameInp = el("input", { type: "text", value: p.name });
  nameInp.addEventListener("change", () => { p.name = nameInp.value; saveQuiet(); });

  const panD = panel("D · Randomizador: nivel de diversidad",
    el("div", { class: "row" }, el("label", { text: "Diversidad" }), divSel,
      el("span", { class: "dim", text: "contenida = gustos marcados · aventurada = más opciones no obvias (siempre coherentes)" })),
    el("div", { class: "row" }, el("label", { text: "Nombre de la obra" }), nameInp),
    el("div", { class: "row" }, el("label", { text: "Notas" }), notesTa));

  root.append(panA, propPanel, instPanel, pref, panD);
}

function ensureInst(iid) {
  const p = State.project;
  if (!p.instruments[iid]) p.instruments[iid] = { role: "auto", enabled: null, density: null };
  return p.instruments[iid];
}

/* ====================================================== 2 · ESTRUCTURA */
function viewStructure(root) {
  const p = State.project;
  const cat = State.catalog;
  root.innerHTML = "";

  const pan = panel("B · Constructor estructural libre");
  pan.appendChild(el("p", { class: "hint",
    text: "Añade, duplica, reordena y elimina secciones. El NOMBRE visible es libre (va al Song Map); " +
          "el TIPO funcional siempre es del catálogo real del contrato (7 tipos). Compases = duración de la sección." }));
  if (!p.sections.length) {
    pan.appendChild(el("div", { class: "msg-warn",
      text: "Sin secciones: al componer, el randomizador elegirá una plantilla estructural del mood. " +
            "Construye al menos 2 secciones para tener estructura propia (el contrato exige ≥ 2)." }));
  }

  const list = el("div", {});
  const render = () => {
    list.innerHTML = "";
    p.sections.forEach((s, i) => {
      const card = el("div", { class: "sec-card" });
      const labelInp = el("input", { type: "text", value: s.label, title: "nombre visible (Song Map)" });
      labelInp.addEventListener("change", () => { s.label = labelInp.value; saveQuiet(); });
      const typeSel = el("select", {}, ...(cat.section_types || []).map(t =>
        el("option", { value: t, text: State.typeLabels[t] || t })));
      typeSel.value = s.type;
      typeSel.addEventListener("change", () => { s.type = typeSel.value; saveQuiet(); refreshTimeline(); });
      const barsInp = el("input", { type: "number", min: "1", max: "512", value: s.bars });
      barsInp.addEventListener("change", () => {
        s.bars = Math.max(1, Math.min(512, parseInt(barsInp.value || "4", 10)));
        saveQuiet(); refreshTimeline();
      });
      const head = el("div", { class: "sec-head" },
        el("span", { class: "ord", text: String(i + 1).padStart(2, "0") }),
        labelInp, typeSel, barsInp,
        el("button", { class: "btn small", text: "↑", title: "subir", onclick: () => {
          if (i > 0) { [p.sections[i - 1], p.sections[i]] = [p.sections[i], p.sections[i - 1]]; saveQuiet(); render(); } } }),
        el("button", { class: "btn small", text: "↓", title: "bajar", onclick: () => {
          if (i < p.sections.length - 1) { [p.sections[i + 1], p.sections[i]] = [p.sections[i], p.sections[i + 1]]; saveQuiet(); render(); } } }),
        el("button", { class: "btn small", text: "Duplicar", onclick: () => {
          const copy = JSON.parse(JSON.stringify(s));
          copy.id = s.id + "_copy";
          let n = 2; const ids = p.sections.map(x => x.id);
          while (ids.includes(copy.id)) { copy.id = s.id + "_copy" + (n++); }
          copy.label = s.label + " (copia)";
          p.sections.splice(i + 1, 0, copy); saveQuiet(); render();
        } }),
        el("button", { class: "btn small danger", text: "✕", title: "eliminar", onclick: () => {
          p.sections.splice(i, 1); saveQuiet(); render();
        } }));
      card.appendChild(head);

      const params = el("div", { class: "sec-params" });
      const mkParam = (label, value, onchg, attrs = {}) => {
        const inp = el("input", { type: attrs.type || "number", ...attrs, value: value === null || value === undefined ? "" : value });
        inp.addEventListener("change", () => onchg(inp.value));
        return el("div", { class: "p" }, el("label", { text: label }), inp);
      };
      params.appendChild(mkParam("energy", s.energy, v => { s.energy = v === "" ? null : parseFloat(v); saveQuiet(); }, { step: "0.05", min: "0", max: "1" }));
      params.appendChild(mkParam("tension", s.tension, v => { s.tension = v === "" ? null : parseFloat(v); saveQuiet(); }, { step: "0.05", min: "0", max: "1" }));
      params.appendChild(mkParam("density", s.density, v => { s.density = v === "" ? null : parseFloat(v); saveQuiet(); }, { step: "0.05", min: "0", max: "1" }));
      const drumsSel = el("select", {}, el("option", { value: "", text: "— libre —" }),
        ...(cat.drums_ladder || ["off", "air", "light", "groove", "heavy"]).map(d => el("option", { value: d, text: d })));
      drumsSel.value = s.drums || "";
      drumsSel.addEventListener("change", () => { s.drums = drumsSel.value || null; saveQuiet(); });
      params.appendChild(el("div", { class: "p" }, el("label", { text: "drums" }), drumsSel));
      const cbInp = el("input", { type: "number", min: "1", max: "8", value: s.chord_bars || "" });
      cbInp.addEventListener("change", () => { s.chord_bars = cbInp.value ? parseInt(cbInp.value, 10) : null; saveQuiet(); });
      params.appendChild(el("div", { class: "p" }, el("label", { text: "acordes cada (compases)" }), cbInp));
      const finalChk = el("input", { type: "checkbox" });
      finalChk.checked = !!s.final;
      finalChk.addEventListener("change", () => { s.final = finalChk.checked; saveQuiet(); });
      params.appendChild(el("div", { class: "p" }, el("label", { text: "final" }), finalChk));
      card.appendChild(params);

      /* focus / active (máx 3 focus) */
      const mkMulti = (field, max, title) => {
        const box = el("div", { class: "p" }, el("label", { text: title, title }));
        (cat.instruments || []).forEach(iid => {
          const chk = el("input", { type: "checkbox" });
          chk.checked = (s[field] || []).includes(iid);
          chk.addEventListener("change", () => {
            const arr = new Set(s[field] || []);
            if (chk.checked) { arr.add(iid); if (max && arr.size > max) { chk.checked = false; arr.delete(iid); } }
            else arr.delete(iid);
            s[field] = arr.size ? [...arr] : null;
            saveQuiet();
          });
          box.appendChild(chk);
          box.appendChild(el("span", { class: "dim", text: (State.instrumentLabels[iid] || iid).split(" ")[0] }));
        });
        return box;
      };
      const adv = el("div", { class: "sec-params" }, mkMulti("focus", 3, "focus (máx 3)"), mkMulti("active", 0, "active (whitelist; vacío = todos)"));
      card.appendChild(adv);
      list.appendChild(card);
    });
  };
  render();

  const addLabel = el("input", { type: "text", placeholder: "nombre visible (Verse 1, Preludio…)" });
  const addType = el("select", {}, ...(cat.section_types || []).map(t => el("option", { value: t, text: State.typeLabels[t] || t })));
  const addBars = el("input", { type: "number", min: "1", max: "512", value: "8" });
  const addBtn = el("button", { class: "btn primary", text: "Añadir sección", onclick: () => {
    const label = addLabel.value.trim() || addType.options[addType.selectedIndex].text;
    const base = label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "sec";
    let id = base, n = 2;
    const ids = p.sections.map(x => x.id);
    while (ids.includes(id)) id = `${base}_${n++}`;
    p.sections.push({ id, label, type: addType.value, bars: Math.max(1, parseInt(addBars.value, 10) || 8) });
    addLabel.value = ""; saveQuiet(); render(); refreshTimeline();
  } });
  pan.appendChild(el("div", { class: "row" }, addLabel, addType, addBars, addBtn));
  pan.appendChild(list);

  /* timeline */
  const tlPanel = panel("Cronología (4/4; duración = compases × 4 tiempos × 60/BPM)");
  const tlStrip = el("div", { class: "tl-strip" });
  const tlInfo = el("div", { class: "dim", text: "" });
  const refreshTimeline = () => {
    tlStrip.innerHTML = "";
    const total = p.sections.reduce((a, s) => a + s.bars, 0) || 1;
    p.sections.forEach(s => {
      tlStrip.appendChild(el("div", { class: `tl-seg t-${s.type}`,
        style: `flex:${s.bars}`, title: `${s.label}: ${s.bars} compases`, text: s.bars >= 2 ? s.label : "" }));
    });
    const bpm = State.decision("bpm");
    tlInfo.textContent = `total: ${total} compases` +
      (bpm.mode === "fixed" && bpm.value ? ` · ≈ ${(total * 4 * 60 / bpm.value / 60).toFixed(2)} min a ${bpm.value} BPM` : " · BPM automático (la duración exacta se calcula al componer)");
  };
  tlPanel.append(tlStrip, tlInfo);
  refreshTimeline();
  root.append(pan, tlPanel);
}

/* ========================================================= 3 · ARMONÍA */
function viewHarmony(root) {
  const p = State.project;
  const cat = State.catalog;
  root.innerHTML = "";

  const pan = panel("C · Harmonic Composer — progresiones por sección");
  pan.appendChild(el("p", { class: "hint" }));
  pan.children[1].innerHTML =
    "<b>Guiada</b> = tú escribes los grados romanos de cada sección y Composer los convierte a acordes reales " +
    "(misma gramática que el motor). <b>Nativa</b> = la receta N1 de la identidad crea la progresión: libertad del motor. " +
    "<b>Mezcla real:</b> global Guiada + secciones marcadas Nativa (esas secciones usan la receta N1 y queda registrado " +
    "en el Song Map). Si el modo global es Nativa, las progresiones guiadas por sección NO se escriben al doc — Composer " +
    "lo advierte al resolver el plan, nunca lo hace en silencio. Los ACORDES LITERALES (columna de la derecha) tienen la " +
    "precedencia más alta (§2.8) y viajan con cualquier modo. La escala fija la raíz y la calidad diatónica (en C major, " +
    "<span class='mono'>I - III - vi - V</span> → <span class='mono'>C - Em - Am - G</span>). En tonalidades menores, " +
    "<span class='mono'>V</span> es la dominante mayor; tokens: " +
    "<span class='mono'>7 maj7 m7 9 m9 sus4 7sus4 add9 dim aug m7b5 6 64 b/# grado:N</span>.";

  const keyRow = decisionRow("key", {
    required: true,
    valueInput: v => el("input", { type: "text", placeholder: "D minor", value: v ?? "" }),
    hint: "requerida por el contrato; si es automática el randomizador la elige por mood",
  });
  const langRow = decisionRow("language", {
    required: true,
    valueInput: v => el("select", {}, ...(cat.languages || []).map(l => el("option", { value: l, text: l }))),
    hint: "vocabulario real admitido (W414 si sales del idioma)",
  });
  const modeRow = decisionRow("harmony_mode", {
    required: true,
    valueInput: v => el("select", {},
      el("option", { value: "guided", text: "Guiada (progresiones explícitas)" }),
      el("option", { value: "native", text: "Nativa (recetas N1)" })),
    hint: "instrucción de construcción (no es campo del contrato; sin opción Libre) · F7 se elige al generar y SIEMPRE es opcional",
  });
  const hrRow = decisionRow("harmonic_rhythm_bars", {
    valueInput: v => el("input", { type: "number", min: "1", max: "8", value: v ?? "" }),
    parse: v => { const n = parseInt(v, 10); if (isNaN(n)) throw new Error("ritmo armónico debe ser número"); return n; },
    hint: "global; cada sección puede anularlo con 'acordes cada N compases'",
  });
  pan.append(keyRow, langRow, modeRow, hrRow);

  /* tabla por sección con conversión EN VIVO */
  const tbl = el("table", {});
  tbl.appendChild(el("tr", {}, el("th", { text: "Sección" }), el("th", { text: "Modo" }),
    el("th", { text: "Grados romanos (guiada)" }), el("th", { text: "→ acordes reales" }),
    el("th", { text: "Acordes literales (opcional, §2.8)" }), el("th", { text: "→ validación real" })));
  const previewChords = async (cell, sid) => {
    // lee el estado VIVO (State.project se reemplaza en cada guardado: usar la
    // constante `p` del render capturaría un objeto obsoleto tras el primer save)
    const hs = State.project.harmony_sections[sid] || {};
    cell.innerHTML = "";
    if (!hs.chords) { cell.appendChild(el("span", { class: "dim", text: "—" })); return; }
    const syms = hs.chords.split(/\s+|,|;|–|—/).filter(t => t && t !== "-");
    try {
      const r = await API.post("/api/harmony/parse_chords", { simbolos: syms });
      if (r.ok === null) { cell.appendChild(el("span", { class: "msg-warn", text: r.nota })); return; }
      for (const x of (r.resultados || [])) {
        if (x.ok) {
          cell.appendChild(el("span", { class: "chip chord-chip", text: x.simbolo,
            title: (x.notas || []).join(" · ") + (x.compases ? ` · ${x.compases} compases` : "") }));
        } else {
          cell.appendChild(el("div", { class: "msg-err", text: `${x.simbolo}: ${x.error}` }));
        }
      }
    } catch (e) {
      cell.appendChild(el("span", { class: "msg-err", text: e.message }));
    }
  };
  const previewOne = async (cell, sid) => {
    const hs = (State.project.harmony_sections[sid] || {});
    cell.innerHTML = "";
    if ((State.project.harmony_sections[sid] || {}).mode !== "guided" || !hs.numerals) {
      cell.appendChild(el("span", { class: "dim", text: "— (nativa: receta N1 o libertad) —" }));
      return;
    }
    try {
      const keyFixed = State.decision("key");
      if (keyFixed.mode !== "fixed") {
        cell.appendChild(el("span", { class: "dim", text: "fija la tonalidad para ver la conversión" }));
        return;
      }
      const r = await API.post("/api/harmony/preview", {
        key: keyFixed.value, numerals: hs.numerals, language: State.decision("language").value || null });
      if (!r.ok) { cell.appendChild(el("span", { class: "msg-err", text: r.error })); return; }
      for (const c of r.acordes) {
        cell.appendChild(el("span", { class: "chip chord-chip", text: c.symbol,
          title: `${c.roman} · calidad ${c.tier}${c.diatonico ? "" : " · no diatónico"}` }));
      }
      if (r.avisos.length) r.avisos.forEach(a => cell.appendChild(el("div", { class: "msg-warn", text: a })));
    } catch (e) {
      cell.appendChild(el("span", { class: "msg-err", text: e.message }));
    }
  };
  const rebuildTable = () => {
    tbl.innerHTML = "";
    tbl.appendChild(el("tr", {}, el("th", { text: "Sección" }), el("th", { text: "Modo" }),
      el("th", { text: "Grados romanos (guiada)" }), el("th", { text: "→ acordes reales" }),
      el("th", { text: "Acordes literales (opcional, §2.8)" }), el("th", { text: "→ validación real" })));
    const secs = p.sections.length ? p.sections : [{ id: "(sin estructura)", label: "(sin estructura)" }];
    secs.forEach(s => {
      const hs = p.harmony_sections[s.id] || { mode: "guided", numerals: "" };
      const modeSel = el("select", {},
        el("option", { value: "guided", text: "Guiada" }),
        el("option", { value: "native", text: "Nativa" }));
      modeSel.value = hs.mode || "guided";
      modeSel.addEventListener("change", () => {
        ensureHSection(s.id).mode = modeSel.value; saveQuiet(); previewOne(pvCell, s.id);
      });
      const numInp = el("input", { type: "text", style: "width:220px",
        placeholder: "I - III - vi - V", value: hs.numerals || "" });
      numInp.addEventListener("change", () => {
        ensureHSection(s.id).numerals = numInp.value.trim() || null;
        saveQuiet(); previewOne(pvCell, s.id);
      });
      const chInp = el("input", { type: "text", style: "width:200px",
        placeholder: "G/B - Dm9:2 - Fmaj7", value: hs.chords || "" });
      chInp.addEventListener("change", () => {
        ensureHSection(s.id).chords = chInp.value.trim() || null;
        saveQuiet(); previewChords(pvChCell, s.id);
      });
      const pvCell = el("td", {});
      const pvChCell = el("td", {});
      const tr = el("tr", {},
        el("td", { text: s.label }, el("div", { class: "dim", text: s.id })),
        el("td", {}, modeSel), el("td", {}, numInp), pvCell,
        el("td", {}, chInp), pvChCell);
      tbl.appendChild(tr);
      previewOne(pvCell, s.id);
      previewChords(pvChCell, s.id);
    });
  };
  rebuildTable();
  pan.appendChild(tbl);
  pan.appendChild(el("p", { class: "hint",
    text: "Los acordes literales se prevalidan con el parser REAL del DMD (forge/theory: el mismo que aplica el validador E113). " +
          "Sin DMD descubierto no se prevalidan: se escribe la advertencia y el doc lleva los símbolos tal cual. " +
          "Tienen precedencia MÁXIMA (posición 1 de §2.8) incluso en modo Nativa, y el Song Map los marca como fuente 'explicito'. " +
          "Sepáralos con espacios, comas o ' - '; el sufijo ':N' fija compases de ese acorde (p. ej. 'Dm9:2')." }));

  /* plantillas por mood */
  const applyTpl = el("button", { class: "btn", text: "Aplicar plantilla del mood a las secciones sin progresión", onclick: async () => {
    const mood = State.decision("mood").value || "neutral";
    const keyFixed = State.decision("key");
    if (keyFixed.mode !== "fixed") { status("fija la tonalidad para usar plantillas", "err"); return; }
    const r = await API.post("/api/harmony/templates", { mood, key: keyFixed.value });
    let n = 0;
    (p.sections || []).forEach(s => {
      const hs = p.harmony_sections[s.id];
      if ((!hs || !hs.numerals) && r.por_tipo[s.type]) {
        ensureHSection(s.id).mode = "guided";
        p.harmony_sections[s.id].numerals = r.por_tipo[s.type]; n++;
      }
    });
    saveQuiet(); rebuildTable();
    status(`plantillas aplicadas a ${n} sección(es) (mood ${mood})`, "ok");
  } });
  pan.appendChild(el("div", { class: "row" }, applyTpl,
    el("span", { class: "dim", text: "solo rellena secciones guiadas sin progresión; no toca lo que tú ya escribiste" })));

  /* ritmo armónico por acorde (distribución definida) */
  const distPanel = panel("Ritmo armónico avanzado (opcional)");
  distPanel.appendChild(el("p", { class: "hint" }));
  distPanel.children[0].innerHTML =
    "Una progresión de 4 acordes NO significa 4 compases. El ritmo lo dan: (1) <b>acordes cada N compases</b> " +
    "por sección (módulo B), (2) el <b>ritmo armónico global</b>, y (3) la distribución POR ACORDE con la sintaxis " +
    "<span class='mono'>grado:N</span> — p. ej. <span class='mono'>I:2 - V:1 - vi:1</span> (el acorde I dura 2 compases). " +
    "La progresión repite en ciclo hasta llenar la sección (comportamiento real del motor). " +
    "Limitación honesta: dos acordes DENTRO de un mismo compás no existe en este contrato (el mínimo es 1 compás por acorde).";
  root.append(pan, distPanel);
}

function ensureHSection(sid) {
  const p = State.project;
  if (!p.harmony_sections[sid]) p.harmony_sections[sid] = { mode: "guided", numerals: null, chord_bars: null, resolution: null };
  return p.harmony_sections[sid];
}

/* ==================================================== 4 · RANDOMIZADOR */
function viewRandomizer(root) {
  const p = State.project;
  const cat = State.catalog;
  root.innerHTML = "";

  const seedRow = decisionRow("seed", {
    valueInput: v => el("input", { type: "number", min: "0", value: v ?? "" }),
    parse: v => { const n = parseInt(v, 10); if (isNaN(n) || n < 0) throw new Error("seed debe ser entero ≥ 0"); return n; },
    hint: "misma seed + mismas decisiones = misma composición, bit a bit",
  });
  const pan = panel("D · Randomizador coherente",
    seedRow,
    el("p", { class: "hint",
      text: "El randomizador solo decide los ejes EN AUTOMÁTICO, condicionado por reglas de compatibilidad " +
            "(rango BPM de la identidad, dominante en menor, doom con ritmo armónico ≥ 2, protagonista sonando…) " +
            "y preferencias ponderadas por mood. Las decisiones FIJADAS se respetan siempre; las LIBRES no se escriben en el JSON." }));

  const genBtn = el("button", { class: "btn primary", text: "Resolver plan y mostrar conflictos (sin guardar)", onclick: () =>
    guard(async () => {
      await State.saveProject();
      const r = await API.post(`/api/projects/${State.pid}/compose`, { save: false });
      State.lastCompose = r;
      renderPlan(r);
      status(r.ok ? "plan resuelto y sin errores duros" : "hay conflictos: revisa la lista", r.ok ? "ok" : "err");
    }, null) });
  pan.appendChild(genBtn);

  const planBox = el("div", {});
  pan.appendChild(planBox);
  const renderPlan = (r) => {
    planBox.innerHTML = "";
    if (!r.ok && r.errores && r.errores.length) {
      r.errores.forEach(e => planBox.appendChild(el("div", { class: "msg-err",
        text: `[${e.code}] ${e.where}: ${e.message} → ${e.fix || ""}` })));
    }
    (r.avisos || []).forEach(a => planBox.appendChild(el("div", { class: "msg-warn",
      text: `[${a.code}] ${a.where}: ${a.message}` })));
    (r.sugerencias || []).forEach(s => planBox.appendChild(el("div", { class: "msg-tip", text: s.message })));
    if (r.seed_used !== undefined) {
      planBox.appendChild(el("div", { class: "row" },
        el("label", { text: "Semilla usada" }), el("span", { class: "mono", text: r.seed_used })));
      planBox.appendChild(el("h2", { text: "Decisiones del plan" }));
      const t = el("table", {}, el("tr", {}, el("th", { text: "Eje" }), el("th", { text: "Estado" }),
        el("th", { text: "Valor" }), el("th", { text: "Por qué" })));
      (r.log || []).forEach(l => t.appendChild(el("tr", {},
        el("td", { text: State.decLabel(l.axis) || l.axis }),
        el("td", {}, modeTag(l.estado)),
        el("td", { class: "mono", text: Array.isArray(l.valor) ? l.valor.join(", ") : (l.valor ?? "—") }),
        el("td", { class: "dim", text: l.razon }))));
      planBox.appendChild(t);
      planBox.appendChild(el("p", { class: "hint",
        text: "Libres (no se escriben; el motor decide): " + ((r.free_axes || []).join(", ") || "ninguno") }));
    }
  };
  if (State.lastCompose) renderPlan(State.lastCompose);
  root.append(pan);
}

/* ======================================================== 5 · PREVIEW */
function viewPreview(root) {
  const p = State.project;
  root.innerHTML = "";
  const pan = panel("Vista de estructura");
  if (!p.sections.length) {
    pan.appendChild(el("span", { class: "dim", text: "estructura automática (el randomizador elegirá plantilla del mood al componer)" }));
  } else {
    const t = el("table", {}, el("tr", {}, el("th", { text: "#" }), el("th", { text: "Sección" }),
      el("th", { text: "Tipo" }), el("th", { text: "Compases" }), el("th", { text: "Params fijados" })));
    p.sections.forEach((s, i) => {
      const params = [];
      ["energy", "tension", "density", "drums", "focus", "active", "chord_bars", "loop_bars", "final"]
        .forEach(k => { if (s[k] !== null && s[k] !== undefined && s[k] !== false) params.push(`${k}=${JSON.stringify(s[k])}`); });
      t.appendChild(el("tr", {}, el("td", { text: i + 1 }), el("td", { text: s.label }),
        el("td", { text: s.type }), el("td", { class: "num", text: s.bars }),
        el("td", { class: "dim", text: params.join(" · ") || "todo libre" })));
    });
    pan.appendChild(t);
  }
  const panH = panel("Vista armónica");
  const keyD = State.decision("key");
  panH.appendChild(el("div", { class: "row" }, el("label", { text: "Tonalidad" }),
    el("span", { class: "mono", text: keyD.mode === "fixed" ? keyD.value : "automática (por mood)" }),
    modeTag(keyD.mode)));
  const t2 = el("table", {}, el("tr", {}, el("th", { text: "Sección" }), el("th", { text: "Modo" }),
    el("th", { text: "Progresión" })));
  p.sections.forEach(s => {
    const hs = p.harmony_sections[s.id];
    t2.appendChild(el("tr", {}, el("td", { text: s.label }),
      el("td", { text: hs && hs.mode === "guided" ? "guiada" : "nativa" }),
      el("td", { class: "mono", text: (hs && hs.numerals) || "— receta N1 —" })));
  });
  panH.appendChild(t2);
  const panC = panel("Conflictos y advertencias",
    el("span", { class: "dim", text: "se calculan al resolver el plan (vista 4) y al componer (vista 6)" }));
  const panL = panel("Decisiones del randomizador (explicabilidad)",
    el("span", { class: "dim", text: "el log completo se guarda en generation_manifest.json de cada generación" }));
  if (State.lastCompose && State.lastCompose.log) {
    const t3 = el("table", {}, el("tr", {}, el("th", { text: "Eje" }), el("th", { text: "Estado" }),
      el("th", { text: "Valor" }), el("th", { text: "Razón" }), el("th", { text: "Descartadas" })));
    State.lastCompose.log.forEach(l => t3.appendChild(el("tr", {},
      el("td", { text: State.decLabel(l.axis) || l.axis }), el("td", {}, modeTag(l.estado)),
      el("td", { class: "mono", text: Array.isArray(l.valor) ? l.valor.join(", ") : (l.valor ?? "—") }),
      el("td", { class: "dim", text: l.razon }),
      el("td", { class: "dim", text: (l.descartadas || []).join(", ") }))));
    panL.appendChild(t3);
  }
  root.append(pan, panH, panC, panL);
}

/* =========================================== 6 · OUTPUT — panel MIDI ===== */
/* Estados del backend (contrato): sin_midi | en_cola | generando | ok |
   error | cancelado | timeout | interrumpido | integridad_error. */
const MIDI_ESTADOS = {
  sin_midi:         ["Sin MIDI", ""],
  en_cola:          ["En cola", "warn"],
  generando:        ["Generando…", "warn"],
  ok:               ["MIDI listo", "ok"],
  error:            ["Error", "err"],
  cancelado:        ["Cancelado", "err"],
  timeout:          ["Timeout", "err"],
  interrumpido:     ["Interrumpido", "err"],
  integridad_error: ["Error de integridad", "err"],
};
const MIDI_TERMINALES = ["ok", "error", "cancelado", "timeout", "interrumpido", "sin_midi", "integridad_error"];
const MIDI_GENERABLE = ["sin_midi", "error", "cancelado", "timeout", "interrumpido", "integridad_error"];
const MIDI_ERROR_FAMILIA = ["error", "cancelado", "timeout", "interrumpido", "integridad_error"];

function midiChip(estado) {
  const [txt, kind] = MIDI_ESTADOS[estado] || [estado || "—", ""];
  return el("span", { class: `badge${kind ? " " + kind : ""}`, title: `estado MIDI: ${estado || "desconocido"}`, text: txt });
}

function midiClockTxt(beat, bpm) {
  const s = Math.max(0, beat * 60 / (bpm || 1));
  return Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0");
}

function copyText(txt, okMsg) {
  const done = () => status(okMsg, "ok");
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(txt).then(done, () => status("No se pudo copiar al portapapeles", "err"));
  } else {
    const ta = document.createElement("textarea");
    ta.value = txt; document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); done(); } catch (e) { status("No se pudo copiar al portapapeles", "err"); }
    ta.remove();
  }
}

/* Registro de pollers activos (1 por generación, sin solapes) y teardown al
   salir de la vista Output: los pollers se autodetienen si su nodo deja de
   estar en el DOM, y App.go (envuelto abajo) para todo de inmediato. */
const MidiUI = {
  pollers: {},      // gen_id -> {timer, anchor, alive, busy}
  playingGen: null, // gen cuyo audio suena ahora
  playingBtn: null, // botón ▶/■ de esa gen
  stopPoller(genId) {
    const p = this.pollers[genId];
    if (p) { p.alive = false; clearInterval(p.timer); delete this.pollers[genId]; }
  },
  startPolling(pid, genId, anchor, apply) {
    this.stopPoller(genId); // guardia anti-pollers concurrentes por gen
    const poller = { timer: null, anchor, alive: true, busy: false };
    this.pollers[genId] = poller;
    poller.timer = setInterval(async () => {
      if (!poller.alive || !poller.anchor || !document.contains(poller.anchor)) { this.stopPoller(genId); return; }
      if (poller.busy) return;
      poller.busy = true;
      try {
        const st = await API.estadoMidi(pid, genId);
        if (!poller.alive || !document.contains(poller.anchor)) { this.stopPoller(genId); return; }
        if (MIDI_TERMINALES.includes(st.state)) this.stopPoller(genId);
        apply(st);
        if (!this.pollers[genId] && MIDI_TERMINALES.includes(st.state)) {
          status(st.state === "ok" ? `MIDI listo para ${genId}` : `MIDI de ${genId}: ${st.state}`,
                 st.state === "ok" ? "ok" : "err");
        }
      } catch (e) { /* fallo transitorio de red: se sigue sondeando */ }
      finally { poller.busy = false; }
    }, 1000);
    return poller;
  },
  resetPlayBtn() {
    if (this.playingBtn) this.playingBtn.textContent = "▶ Escuchar";
    this.playingGen = null; this.playingBtn = null;
  },
  stopAll() {
    Object.keys(this.pollers).forEach(k => this.stopPoller(k));
    if (window.ComposerPlayback) ComposerPlayback.stop();
    this.resetPlayBtn();
  },
};

/* Tarjeta MIDI de UNA generación: chip de estado, generar/cancelar/reintentar,
   detalles cuando ok (SHA256, perfil, seed, duración, bpm, compases,
   compliance), descarga y artefactos, y escucha WebAudio de vista previa. */
function midiCard(pid, genId) {
  const card = el("div", { class: "midi-card" });
  let lastState = null;
  let clockEl = null, artBox = null, listenBtn = null;

  const apply = (st) => {
    if (!document.contains(card)) return;
    if (st.state !== lastState) { lastState = st.state; render(st); }
  };

  const generar = () => guard(async () => {
    const r = await API.generarMidi(pid, genId, true);
    if (r && r.state === "ok") {
      // 200 idempotente: ya existía un MIDI íntegro → mostrarlo directamente
      const st = await API.estadoMidi(pid, genId);
      lastState = st.state; render(st);
      status(`MIDI ya generado (idempotente) para ${genId}: mostrando el resultado`, "ok");
    } else {
      // 202 {jid, state:"queued"} → sondear cada 1 s hasta estado terminal
      lastState = "en_cola"; render({ state: "en_cola", midi: null, job: null });
      MidiUI.startPolling(pid, genId, card, apply);
      status(`MIDI en cola (job ${r.jid}) para ${genId}`, "ok");
    }
  }, null); // un 409/4xx llega aquí: guard muestra el detail del servidor

  const renderOk = (m) => {
    const fails = Number(m.compliance_fails || 0), warns = Number(m.compliance_warns || 0);
    const t = el("table", {},
      el("tr", {}, el("th", { text: "perfil" }), el("th", { text: "seed" }),
        el("th", { text: "duración" }), el("th", { text: "bpm" }),
        el("th", { text: "compases" }), el("th", { text: "compliance" }),
        el("th", { text: "generado (UTC)" })));
    t.appendChild(el("tr", {},
      el("td", { text: m.perfil || "—" }),
      el("td", { class: "mono", text: m.seed ?? "—" }),
      el("td", { class: "num", text: m.duracion_s != null ? `${Number(m.duracion_s).toFixed(1)} s` : "—" }),
      el("td", { class: "num", text: m.bpm ?? "—" }),
      el("td", { class: "num", text: m.compases ?? "—" }),
      el("td", {},
        el("span", { class: `badge${fails ? " err" : " ok"}`, title: "compliance_fails", text: `${fails} fallo(s)` }),
        el("span", { class: `badge${warns ? " warn" : ""}`, title: "compliance_warns", text: ` ${warns} aviso(s)` })),
      el("td", { class: "dim", text: m.generado_utc || "—" })));
    card.appendChild(t);

    const shaEl = el("span", { class: "mono midi-sha", title: "clic para copiar el SHA256 completo", text: m.sha256 || "—" });
    shaEl.addEventListener("click", () => copyText(m.sha256 || "", "SHA256 del MIDI copiado al portapapeles"));
    card.appendChild(el("div", { class: "row" },
      el("span", { class: "dim", text: "nombre:" }), el("span", { class: "mono", text: m.nombre || "—" }),
      el("span", { class: "dim", text: "· SHA256 (clic = copiar):" }), shaEl,
      m.verificado === false ? el("span", { class: "badge warn", text: "sin verificación" }) : null));

    clockEl = el("span", { class: "midi-clock", text: "0:00" });
    listenBtn = el("button", { class: "btn small primary", text: "▶ Escuchar", onclick: toggleListen });
    artBox = el("div", {});
    card.appendChild(el("div", { class: "midi-actions" },
      el("button", { class: "btn small", text: "⬇ .mid", title: "descargar el archivo .mid", onclick: () =>
        guard(async () => { const f = await API.descargarMidi(pid, genId); status(`descargado: ${f}`, "ok"); }, null) }),
      el("button", { class: "btn small", text: "evidencia", onclick: () => toggleArtefacto("evidencia.json") }),
      el("button", { class: "btn small", text: "config_efectiva", onclick: () => toggleArtefacto("config_efectiva.json") }),
      listenBtn, clockEl,
      el("span", { class: "dim midi-note", text: "Vista previa WebAudio — no equivale al render con tu soundfont externo" })));
    card.appendChild(artBox);
  };

  const toggleArtefacto = (fname) => guard(async () => {
    if (artBox.dataset.f === fname) { artBox.innerHTML = ""; delete artBox.dataset.f; return; }
    const data = await API.artefactoMidi(pid, genId, fname);
    artBox.dataset.f = fname;
    artBox.innerHTML = "";
    artBox.appendChild(el("div", { class: "row" },
      el("strong", { text: fname }),
      el("button", { class: "btn small", text: "✕", title: "cerrar", onclick: () => { artBox.innerHTML = ""; delete artBox.dataset.f; } })));
    const pre = el("pre", { class: "json" });
    pre.textContent = JSON.stringify(data, null, 2);
    artBox.appendChild(pre);
  }, null);

  const toggleListen = () => {
    if (MidiUI.playingGen === genId) { ComposerPlayback.stop(); MidiUI.resetPlayBtn(); return; }
    guard(async () => {
      ComposerPlayback.stop();          // anti-solape: una sola sesión
      MidiUI.resetPlayBtn();            // por si otra tarjeta quedó marcada
      const ev = await API.eventosGen(pid, genId);
      ComposerPlayback.load(ev);        // lanza 'events.json no válido' si la forma es incorrecta
      ComposerPlayback.play(0, (beat) => {
        if (!document.contains(clockEl)) { ComposerPlayback.stop(); MidiUI.resetPlayBtn(); return; }
        clockEl.textContent = midiClockTxt(beat, ev.bpm);
      }, () => MidiUI.resetPlayBtn());
      MidiUI.playingGen = genId; MidiUI.playingBtn = listenBtn;
      listenBtn.textContent = "■ Parar";
    }, null); // 404 de events.json / WebAudio ausente / forma inválida → status del servidor
  };

  const render = (st) => {
    card.innerHTML = "";
    card.appendChild(el("div", { class: "row" },
      el("span", { class: "mono", text: genId }),
      midiChip(st.state)));
    const actions = el("div", { class: "midi-actions" });
    if (MIDI_GENERABLE.includes(st.state)) {
      actions.appendChild(el("button", { class: "btn small primary",
        text: st.state === "sin_midi" ? "Generar MIDI" : "Reintentar", onclick: generar }));
    }
    if (st.state === "en_cola" || st.state === "generando") {
      actions.appendChild(el("button", { class: "btn small", text: "Cancelar", onclick: () =>
        guard(async () => { await API.cancelarMidi(pid, genId); status(`cancelación solicitada para ${genId}`, "ok"); }, null) }));
    }
    if (actions.children.length) card.appendChild(actions);
    // detalle REAL del fallo (job.error del servidor), nunca un 'Error' genérico
    if (MIDI_ERROR_FAMILIA.includes(st.state)) {
      const det = (st.job && (st.job.error || st.job.result)) || "(el servidor no dio detalle)";
      card.appendChild(el("div", { class: "msg-err midi-err-trunc", title: det, text: det }));
    }
    if (st.state === "ok" && st.midi) renderOk(st.midi);
    else if (st.state === "ok") card.appendChild(el("div", { class: "msg-warn", text: "estado ok sin bloque midi (integridad_error del servidor)" }));
  };

  /* arranque: estado actual; si hay job en vuelo, retomar el sondeo */
  guard(async () => {
    const st = await API.estadoMidi(pid, genId);
    if (!document.contains(card)) return;
    lastState = st.state;
    render(st);
    if (st.state === "en_cola" || st.state === "generando") MidiUI.startPolling(pid, genId, card, apply);
  }, null).catch(() => {}).then(() => {
    if (!card.childElementCount) {
      card.appendChild(el("div", { class: "row" },
        el("span", { class: "mono", text: genId }),
        el("span", { class: "badge err", text: "sin estado MIDI" })));
      card.appendChild(el("div", { class: "msg-err",
        text: "No se pudo consultar el estado MIDI de esta generación (¿backend sin las rutas /midi?). El detalle está en la barra de estado." }));
    }
  });
  return card;
}

/* ========================================================== 6 · OUTPUT */
function viewOutput(root) {
  root.innerHTML = "";
  MidiUI.stopAll(); // teardown del panel MIDI de la render anterior
  const pan = panel("Componer, validar y exportar");
  pan.appendChild(el("p", { class: "hint",
    text: "Composer produce el documento dark-director/1 + Song Map y los valida con el " +
          "validador REAL del DMD descubierto. El MIDI se genera aquí mismo, por generación (panel de abajo); " +
          "la escucha es una vista previa WebAudio que NO equivale al render con tu soundfont externo." }));

  const seedInp = el("input", { type: "number", min: "0", placeholder: "vacío = automática" });
  const btnCompose = el("button", { class: "btn primary", text: "Componer y validar", onclick: () =>
    guard(async () => {
      await State.saveProject();
      const seed = seedInp.value === "" ? null : parseInt(seedInp.value, 10);
      const r = await API.post(`/api/projects/${State.pid}/compose`, { seed, save: true });
      State.lastCompose = r;
      renderResult(r);
      App.loadProjects().then(App.refreshSidebar);
      refreshHistorial(); // la nueva generación aparece al instante con su tarjeta MIDI
      status(r.ok ? `composición generada (${r.generation ? r.generation.gen_id : "sin guardar"})` :
        "composición rechazada: revisa los conflictos", r.ok ? "ok" : "err");
    }, null) });
  pan.appendChild(el("div", { class: "row" }, btnCompose, el("label", { text: "seed" }), seedInp));

  const out = el("div", {});
  pan.appendChild(out);
  const renderResult = (r) => {
    out.innerHTML = "";
    if (r.errores && r.errores.length) {
      r.errores.forEach(e => out.appendChild(el("div", { class: "msg-err",
        text: `[${e.code}] ${e.where}: ${e.message} → ${e.fix || ""}` })));
    }
    if (r.avisos && r.avisos.length) {
      r.avisos.forEach(a => out.appendChild(el("div", { class: "msg-warn",
        text: `[${a.code}] ${a.where}: ${a.message}` })));
    }
    if (!r.ok) return;
    out.appendChild(el("div", { class: "msg-ok",
      text: `Documento válido para dark-director/1 · seed ${r.seed_used} · compilado por el compilador real (${r.compilado.total_bars} compases, ${r.compilado.target_schema})` }));
    if (r.armonia) {
      const a = r.armonia;
      const partes = [];
      if ((a.secciones_guiadas || []).length) partes.push(`progresiones guiadas en ${a.secciones_guiadas.join(", ")}`);
      if ((a.secciones_con_acordes_literales || []).length) partes.push(`acordes literales en ${a.secciones_con_acordes_literales.join(", ")}`);
      if ((a.secciones_nativas || []).length) partes.push(`nativas (receta N1): ${a.secciones_nativas.join(", ")}`);
      out.appendChild(el("div", { class: "msg-tip",
        text: `Modo global: ${a.modo_global} · modo REAL del doc: ${a.modo_real_del_doc} · fuente por sección en el Song Map (columna Fuente)${partes.length ? " · " + partes.join(" · ") : ""}` }));
    }
    if (r.produccion) {
      const pr = r.produccion;
      out.appendChild(el("h2", { text: "Perfil de producción — SELECCIONADO, NO APLICADO" }));
      out.appendChild(el("div", { class: pr.perfil ? "msg-warn" : "msg-tip",
        text: pr.perfil
          ? `Perfil '${pr.perfil}' (elegido por ${pr.origen === "usuario" ? "TI" : "Composer"}) · estado: ${pr.estado}. El perfil NO va en el doc: solo se hace real al producir el MIDI.`
          : `Sin perfil: Studio aplicará su default (full). Estado: ${pr.estado}.` }));
      if (pr.instruccion) {
        out.appendChild(el("pre", { class: "json",
          text: `Studio: ${pr.instruccion.studio}\nCLI:    ${pr.instruccion.cli}` +
                (pr.f7_keyword ? `\nF7:     keyword '${pr.f7_keyword}'${pr.f7_variation ? " · variación " + pr.f7_variation : ""} (opcional)` : "") }));
      }
    }
    if (r.generation) {
      out.appendChild(el("div", { class: "row" },
        el("span", { text: `Generación ${r.generation.gen_id} · SHA256 doc: ` }),
        el("span", { class: "mono dim", text: r.generation.sha256_doc })));
      for (const f of ["doc.json", "song_map.json", "song_map.csv", "generation_manifest.json"]) {
        out.appendChild(el("a", { class: "btn small", href: `/api/projects/${State.pid}/generations/${r.generation.gen_id}/files/${f}`, text: "⬇ " + f, style: "margin-right:6px" }));
      }
    }
    /* song map */
    if (r.song_map) {
      out.appendChild(el("h2", { text: "Song Map" }));
      const t = el("table", {}, el("tr", {}, el("th", { text: "#" }), el("th", { text: "Sección" }),
        el("th", { text: "Tipo" }), el("th", { text: "Compases" }), el("th", { text: "Barra inicio-fin" }),
        el("th", { text: "Progresión" }), el("th", { text: "Fuente" })));
      r.song_map.secciones.forEach(row => {
        t.appendChild(el("tr", {}, el("td", { text: row.orden }), el("td", { text: row.nombre_visible }),
          el("td", { text: row.tipo_funcional }), el("td", { class: "num", text: row.compases }),
          el("td", { class: "num", text: `${row.compas_inicial}–${row.compas_final}` }),
          el("td", {}, ...row.progresion.map(c => el("span", { class: "chip chord-chip", text: c }))),
          el("td", { class: "dim", text: row.fuente_armonia })));
      });
      out.appendChild(t);
      out.appendChild(el("h2", { text: "Para escribir la letra" }));
      const pre = el("pre", { class: "json" });
      pre.textContent = (r.song_map.notas_para_letras || []).join("\n");
      out.appendChild(pre);
      out.appendChild(el("h2", { text: "doc.json (dark-director/1 rev 3.2)" }));
      const docPre = el("pre", { class: "json" });
      docPre.textContent = JSON.stringify(r.doc, null, 2);
      out.appendChild(docPre);
    }
  };
  if (State.lastCompose) renderResult(State.lastCompose);
  root.append(pan);

  /* historial (con chip de estado MIDI + tarjeta MIDI por generación) */
  const panHist = panel("Historial de generaciones");
  const histBox = el("div", { class: "dim", text: "cargando…" });
  panHist.appendChild(histBox);
  const refreshHistorial = () => guard(async () => {
    const gens = await API.get(`/api/projects/${State.pid}/generations`);
    histBox.innerHTML = "";
    if (!gens.length) { histBox.textContent = "aún no hay generaciones"; return; }
    gens.forEach(g => {
      histBox.appendChild(el("div", { class: "row" },
        el("span", { class: "mono", text: g.gen_id }),
        el("span", { class: "dim", text: g.title || "" }),
        el("span", { class: "dim", text: `seed ${g.seed}` }),
        el("span", { class: `badge ${g.validacion_ok ? "ok" : "warn"}`,
          text: g.validacion_ok ? "válido" : "sin validación" }),
        midiChip(g.midi_estado),
        el("a", { class: "btn small", href: `/api/projects/${State.pid}/generations/${g.gen_id}/files/doc.json`, text: "⬇ doc.json" })));
      histBox.appendChild(midiCard(State.pid, g.gen_id));
    });
  }, null);
  refreshHistorial();
  root.append(panHist);

  /* álbum */
  const panAlb = panel("Modo álbum (planificador con diversidad controlada)");
  panAlb.appendChild(el("p", { class: "hint",
    text: "Crea un plan de N pistas con identidad y restricciones compartidas; cada pista recibe seed, tonalidad, " +
          "estructura y groove DIVERSIFICADOS con registro de huellas (sin duplicados exactos). Genera las pistas pendientes " +
          "en lote (reanudable) y consulta el informe de diversidad. El MIDI de cada pista se produce con el pipeline de DMD " +
          "(Studio / produce.py / modo álbum de DMD): Composer entrega los DOCUMENTOS, no el audio." }));
  const albName = el("input", { type: "text", placeholder: "VIBRAPHONE AFTER MIDNIGHT" });
  const albN = el("input", { type: "number", min: "2", max: "64", value: "13" });
  const albBtn = el("button", { class: "btn", text: "Crear álbum desde este proyecto", onclick: () =>
    guard(async () => {
      await State.saveProject();
      const a = await API.post("/api/albums", { name: albName.value, tracks: parseInt(albN.value, 10) || 2, pid: State.pid });
      status(`álbum creado: ${a.album_id}`, "ok");
      renderAlbum(a.album_id);
    }, null) });
  panAlb.appendChild(el("div", { class: "row" }, albName, albN, albBtn));
  const albBox = el("div", {});
  panAlb.appendChild(albBox);
  const informeBox = el("div", {});
  let midiCellsByTrack = {};   // n → {midiCell, actionsCell} para el refresco de producción
  let albProdBox = el("div", {});

  /* pinta la columna MIDI de cada pista a partir de /production (orquestador) */
  const renderProduccion = async (aid2) => {
    const est = await API.get(`/api/albums/${aid2}/production`);
    albProdBox.innerHTML = "";
    const chip = midiChip(est.state === "generando" ? "generando" :
      est.state === "ok" ? "ok" : est.state === "parcial" ? "warn" : "sin_midi");
    chip.textContent = `MIDI: ${est.ok}/${est.total}` + (est.state === "generando" ? " (produciendo…)" : "");
    albProdBox.appendChild(el("div", { class: "row" }, chip,
      el("button", { class: "btn small", text: "Producir MIDI de TODAS las pistas", onclick: () =>
        guard(async () => {
          const r = await API.post(`/api/albums/${aid2}/produce_all`, {});
          status(`lote del orquestador en cola (${r.jid})`, "ok");
          pollProduccion(aid2, r.jid);
        }, null) }),
      el("button", { class: "btn small danger", text: "Cancelar producción", onclick: () =>
        guard(async () => {
          const r = await API.post(`/api/albums/${aid2}/cancel`, {});
          status(r.ok ? "producción cancelada (las pistas ya hechas conservan su MIDI)" : r.nota || "nada activo", r.ok ? "warn" : "dim");
        }, null) })));
    (est.pistas || []).forEach(p => {
      const cells = midiCellsByTrack[p.n];
      if (!cells) return;
      const { midiCell, actionsCell } = cells;
      midiCell.innerHTML = ""; actionsCell.innerHTML = "";
      const chipP = midiChip(p.estado_midi === "ok" ? "ok" :
        p.estado_midi === "fallo" ? "error" : "sin_midi");
      chipP.textContent = p.estado_midi === "ok" ? "MIDI listo" : p.estado_midi === "fallo" ? "fallo" : "pendiente";
      if (p.error) chipP.title = p.error;
      midiCell.appendChild(chipP);
      if (p.estado_midi === "ok") {
        midiCell.appendChild(el("div", { class: "mono dim", style: "font-size:11px",
          text: (p.sha256_midi || "").slice(0, 10) + "…", title: p.sha256_midi || "" }));
        const a1 = el("a", { class: "btn small", href: `/api/albums/${aid2}/tracks/${p.n}/download`, text: "⬇ .mid" });
        const b1 = el("button", { class: "btn small", text: "▶ Escuchar", onclick: () =>
          guard(async () => {
            if (window.ComposerPlayback && ComposerPlayback.playing()) { ComposerPlayback.stop(); b1.textContent = "▶ Escuchar"; return; }
            b1.textContent = "cargando…";
            const ev = await API.get(`/api/albums/${aid2}/tracks/${p.n}/events`);
            ComposerPlayback.load(ev).play(0, null, () => { b1.textContent = "▶ Escuchar"; });
            b1.textContent = "■ Parar";
          }, (e) => { b1.textContent = "▶ Escuchar"; }) });
        actionsCell.appendChild(a1); actionsCell.appendChild(b1);
      }
      const b2 = el("button", { class: "btn small", text: p.estado_midi === "fallo" ? "reintentar" : "regenerar MIDI", onclick: () =>
        guard(async () => {
          const r = await API.post(`/api/albums/${aid2}/tracks/${p.n}/midi`, {});
          status(`regeneración de la pista ${p.n} en cola (${r.jid})`, "ok");
          pollProduccion(aid2, r.jid);
        }, null) });
      actionsCell.appendChild(b2);
    });
    albProdBox.appendChild(el("div", { class: "midi-note",
      text: "El lote lo ejecuta el ORQUESTADOR EXISTENTE del DMD (album/orquestador.py) en un proceso aislado: reanuda sin regenerar lo válido, reintentos por pista, estado crash-safe por pista y evidencia (SHA256) en produccion/estado.json." }));
  };
  const pollTimers = {};
  const pollProduccion = (aid2, jid) => {
    if (pollTimers[jid]) clearInterval(pollTimers[jid]);
    pollTimers[jid] = setInterval(async () => {
      if (!document.contains(albProdBox)) { clearInterval(pollTimers[jid]); delete pollTimers[jid]; return; }
      try {
        const j = await API.get(`/api/jobs/${jid}`);
        if (!j || !("state" in j)) return;
        if (j.state === "running" && j.result && typeof j.result.ok === "number") {
          status(`lote del álbum: ${j.result.ok}/${j.result.total} pistas ok`, "ok");
        }
        if (!["queued", "running"].includes(j.state)) {
          clearInterval(pollTimers[jid]); delete pollTimers[jid];
          status(j.state === "ok" ? "lote del álbum terminado" : `lote del álbum: ${j.state} ${(j.error || "").slice(0, 140)}`,
                 j.state === "ok" ? "ok" : "err");
        }
        renderProduccion(aid2);
      } catch (e) { /* red transitoria */ }
    }, 1500);
  };

  const renderAlbum = async (aid) => {
    const a = await API.get(`/api/albums/${aid}`);
    albBox.innerHTML = "";
    midiCellsByTrack = {};   // las filas se re-registran abajo (reset ANTES, no después)
    albBox.appendChild(el("div", { class: "row" },
      el("strong", { text: a.name }), el("span", { class: "dim",
        text: `· ${a.compartido.identity} · ${a.compartido.mood} · ${a.compartido.harmony_mode} · ${a.tracks_total} pistas` })));
    const t = el("table", {}, el("tr", {}, el("th", { text: "#" }), el("th", { text: "Estado" }),
      el("th", { text: "Seed" }), el("th", { text: "Tonalidad" }), el("th", { text: "BPM" }),
      el("th", { text: "Lenguaje" }), el("th", { text: "Doc" }), el("th", { text: "MIDI" }), el("th", { text: "" })));
    a.pistas.forEach(tr => {
      const genBtnT = el("button", { class: "btn small", text: tr.estado === "lista" ? "regenerar" : "generar", onclick: () =>
        guard(async () => {
          const r = await API.post(`/api/albums/${aid}/tracks/${tr.n}/generate`);
          if (r.ok) { status(`pista ${tr.n} generada`, "ok"); renderAlbum(aid); }
          else status(`pista ${tr.n}: ${r.error}`, "err");
        }, null) });
      const midiCell = el("td", { class: "dim", text: "…" });
      const actionsCell = el("td", {}, genBtnT);
      midiCellsByTrack[tr.n] = { midiCell, actionsCell };
      t.appendChild(el("tr", {}, el("td", { text: tr.n }),
        el("td", { text: tr.estado === "lista" ? "lista ✓" : "pendiente" }),
        el("td", { class: "mono", text: tr.seed ?? "—" }),
        el("td", { text: tr.key ?? "—" }), el("td", { class: "num", text: tr.bpm ?? "—" }),
        el("td", { text: tr.language ?? "—" }),
        el("td", { class: "mono dim", text: tr.doc_sha256 ? tr.doc_sha256.slice(0, 10) + "…" : "—" }),
        midiCell, actionsCell));
    });
    albBox.appendChild(t);
    albBox.appendChild(albProdBox);
    albBox.appendChild(el("div", { class: "row" },
      el("button", { class: "btn", text: "Generar TODAS las pendientes (reanudable)", onclick: () =>
        guard(async () => {
          const r = await API.post(`/api/albums/${aid}/generate_all`, {});
          const listas = (r.pistas || []).filter(x => (x.estado || "").startsWith("lista")).length;
          status(r.ok ? `álbum completo: ${listas} pista(s) lista(s)` : "algunas pistas con errores: revisa la salida", r.ok ? "ok" : "err");
          renderAlbum(aid);
        }, null) }),
      el("button", { class: "btn", text: "Informe de diversidad", onclick: () =>
        guard(async () => {
          const inf = await API.get(`/api/albums/${aid}/informe`);
          renderInforme(inf);
        }, null) })));
    albBox.appendChild(informeBox);
    renderProduccion(aid).catch(() => {});
  };
  const renderInforme = (inf) => {
    informeBox.innerHTML = "";
    informeBox.appendChild(el("h2", { text: `Informe de diversidad (${inf.pistas_listas}/${inf.pistas_total} pistas listas)` }));
    const t = el("table", {}, el("tr", {}, el("th", { text: "#" }), el("th", { text: "Tonalidad" }),
      el("th", { text: "BPM" }), el("th", { text: "Doc (SHA256)" })));
    Object.entries(inf.docs || {}).forEach(([n, sha]) => t.appendChild(el("tr", {},
      el("td", { text: n }), el("td", { class: "dim", text: "—" }), el("td", { class: "dim", text: "—" }),
      el("td", { class: "mono dim", text: sha ? sha.slice(0, 12) + "…" : "—" }))));
    informeBox.appendChild(t);
    informeBox.appendChild(el("div", { class: "msg-tip",
      text: `tonalidades distintas: ${inf.tonalidades_distintas} · distancias tonales consecutivas (círculo de quintas): ${(inf.distancia_tonal_consecutivas || []).join(", ") || "—"} · ` +
            `BPM: ${(inf.bpm_rango || ["?"])[0]}–${(inf.bpm_rango || ["?", "?"])[1]} · lenguajes: ${(inf.lenguajes || []).join(", ") || "—"} · ` +
            `grooves: ${(inf.grooves || []).join(", ") || "—"} · combinaciones duplicadas: ${inf.combinaciones_duplicadas} (huellas: ${inf.huellas_registradas})` }));
    informeBox.appendChild(el("p", { class: "hint",
      text: "El informe refleja lo que el plan garantiza (huellas), no calidad musical. La producción MIDI de cada pista y su evidencia están en el panel de producción (orquestador del DMD)." }));
  };
}

/* ---------------------------------------------- teardown del panel MIDI -- */
/* Al cambiar de vista se paran TODOS los pollers y el audio en curso.
   Se envuelve App.go (definido en app.js, que carga después de views.js)
   sin modificarlo; los pollers además se autodetienen si su nodo ancla
   deja de estar en el DOM (red de seguridad). */
window.addEventListener("DOMContentLoaded", () => {
  if (typeof App !== "undefined" && App && typeof App.go === "function") {
    const origGo = App.go.bind(App);
    App.go = (view) => { MidiUI.stopAll(); return origGo(view); };
  }
});
