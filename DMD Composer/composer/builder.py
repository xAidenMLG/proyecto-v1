"""Constructor del documento ``dark-director/1`` (rev 3.2) + conflictos.

Traduce el proyecto de Composer (decisiones fijadas/automáticas/libres + plan
resuelto del randomizador) a un documento EXACTO del contrato:

  * Solo campos que el validador REAL admite (E109 = 0 siempre: nada se
    inventa). Los nombres visibles de sección NO van al doc (van al Song Map).
  * ``fixed`` → se escribe tal cual. ``auto`` → se escribe el valor del plan.
    ``free`` → el campo NO se escribe: la receta N1 y los motores deciden.
  * Guided Harmony → ``harmony.progressions`` indexado por id de sección
    (precedencia §2.8 del compilador: id > type > receta N1).
  * Native Harmony → sin ``progressions``: libertad total del motor.

Los conflictos son PRE-chequeos para el usuario (misión §3): si dos
restricciones fijadas son incompatibles, se informa y se explica QUÉ decisión
cambiar. Los W4xx se espejan con la MISMA semántica del validador real
(`suena()` = base ∪ enabled − disabled − active, TENSION_BASE como fallback)
para que el usuario no reciba sorpresas. El árbitro final SIEMPRE es el
validador real del DMD descubierto.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from . import model, structure as ST, harmony as H, randomizer as R

BAND_B3_MIN = 0.67
DRUMS_LADDER = ("off", "air", "light", "groove", "heavy")


def _split_literal_chords(text: str) -> List[str]:
    """Separa acordes literales ('G/B - Dm9:2 Fmaj7' o 'G/B, Dm9:2').

    Separadores: espacios, comas, punto y coma y guiones largos (– —).
    Un guión corto aislado entre espacios también separa; un guión DENTRO del
    símbolo se conserva (es un token real del parser del motor: 'D-9' = Dm9).
    """
    toks = [t for t in re.split(r"\s+|,|;|\u2013|\u2014", (text or "").strip()) if t]
    return [t for t in toks if t != "-"]


def conflicts(project: model.ComposerProject, plan: R.ResolvedPlan,
              manifest: Optional[dict] = None) -> Dict[str, List[dict]]:
    """Pre-chequeos de coherencia: {errores, avisos, sugerencias}.

    errore  → bloquearía la compilación (E-codes) o contradice una decisión fijada.
    aviso   → el documento compila pero el validador real emitirá W4xx.
    sugerencia → mejora musical opcional / información.
    """
    errors: List[dict] = []
    warns: List[dict] = []
    tips: List[dict] = []
    dec = project.decisions
    identity = plan.values.get("identity") or project.fixed_value("identity")
    receta = ((manifest or {}).get("recetas") or {}).get(identity) or {}
    base_set = set(receta.get("set_base") or [])
    catalogs = (manifest or {}).get("catalogos") or {}
    inst_catalog = catalogs.get("instruments") or \
        ["sax_tenor", "rhodes", "vibraphone", "bass", "drums", "piano", "pad", "strings"]

    def suena(iid: str, sec: model.Section) -> bool:
        """Espejo EXACTO de validador.suena(): base ∪ enabled=true − enabled=false
        − exclusiones de active de la sección."""
        if iid not in inst_catalog:
            return False
        conf = project.instruments.get(iid) or model.InstrumentDecision()
        if conf.enabled is False:
            return False
        existe = iid in base_set or conf.enabled is True
        return existe and (sec.active is None or iid in sec.active)

    def dispositivo_pad_strings(sec: model.Section) -> bool:
        return suena("pad", sec) or suena("strings", sec)

    # ---- estructura -----------------------------------------------------------
    secs = project.sections
    if len(secs) < 2:
        errors.append({"code": "E106", "where": "structure",
                       "message": f"la estructura tiene {len(secs)} sección(es); el contrato exige ≥ 2",
                       "fix": "añade otra sección en el editor de estructura"})
    ids = [s.id for s in secs]
    if len(set(ids)) != len(ids):
        dups = sorted({i for i in ids if ids.count(i) > 1})
        errors.append({"code": "E106", "where": "structure",
                       "message": f"ids de sección duplicados: {dups}",
                       "fix": "renombra las secciones duplicadas"})
    hr_efectivo_global = plan.values.get("harmonic_rhythm_bars") or project.fixed_value("harmonic_rhythm_bars")
    for s in secs:
        if s.focus and len(s.focus) > 3:
            errors.append({"code": "E105", "where": f"sección {s.id}",
                           "message": "focus admite máximo 3 instrumentos",
                           "fix": "deja solo los 3 más importantes"})
        cb = s.chord_bars or hr_efectivo_global
        if cb and s.bars % cb != 0:
            warns.append({"code": "W417", "where": f"sección {s.id}",
                          "message": f"{cb} compases por acorde no dividen los {s.bars} compases: "
                                     "el último acorde se recorta (W417 del validador real)",
                          "fix": f"ajusta los compases a un múltiplo de {cb} o cambia el ritmo armónico"})
        # W406 — focus/active de instrumentos que no suenan en esa sección
        for ref in list(s.focus or []) + list(s.active or []):
            if ref in inst_catalog and not suena(ref, s):
                warns.append({"code": "W406", "where": f"sección {s.id}",
                              "message": f"'{ref}' está en focus/active pero no suena ahí "
                                         "(fuera del set base y sin enabled=true, o desactivado): "
                                         "su entrada se ignorará (W406 del validador real)",
                              "fix": f"activa '{ref}' en instrumentos o quítalo de focus/active"})
        # W412 — resolution declarada en la ÚLTIMA sección (gesto omitido)
        if s is secs[-1] and s.resolution is not None:
            warns.append({"code": "W412", "where": f"sección {s.id}",
                          "message": "resolution en la última sección: el gesto de transición "
                                     "se omite y el acorde final suena entero (W412)",
                          "fix": "quítala o déjala si quieres el acorde entero"})

    # ---- identidad / BPM --------------------------------------------------------
    bpm = plan.values.get("bpm") or project.fixed_value("bpm")
    # identidad ARCHIVADA (v1.1, D-03 del manual): permitida por compatibilidad
    # histórica, pero SIEMPRE con advertencia explícita.
    archivadas = ((manifest or {}).get("fingerprint") or {}).get("identidades_archivadas") or []
    if identity and identity in archivadas:
        activa = ((manifest or {}).get("fingerprint") or {}).get("identidad_activa") or "dark_triphop"
        warns.append({"code": "identidad-archivada", "where": "direction.identity",
                      "message": f"'{identity}' es una identidad ARCHIVADA (solo compatibilidad "
                                 f"histórica); la identidad activa del ecosistema es '{activa}'",
                      "fix": "elige la identidad activa salvo que necesites reproducir material antiguo"})
    if identity and receta:
        lo, hi = receta.get("bpm_rango", (70, 96))
        if bpm and not (lo <= bpm <= hi):
            warns.append({"code": "W401", "where": "global.bpm",
                          "message": f"BPM {bpm} fuera del rango típico de {identity} [{lo}, {hi}] "
                                     "(se compila igual; puede sonar fuera del estilo)",
                          "fix": f"deja el BPM automático o muévelo a {lo}–{hi}"})
        # W402 — ritmo armónico DECLARADO menor que el default de la receta
        # (fuera del gate guided: aplica también en native; espejo de validador)
        hr_decl = project.fixed_value("harmonic_rhythm_bars") or \
            (plan.values.get("harmonic_rhythm_bars")
             if (dec.get("harmonic_rhythm_bars") or {}).get("mode") == model.AUTO else None)
        hr_receta = receta.get("harmonic_rhythm_bars", 1)
        if hr_decl is not None and hr_decl < hr_receta:
            warns.append({"code": "W402", "where": "harmony.harmonic_rhythm_bars",
                          "message": f"ritmo armónico {hr_decl} menor que el default de la receta "
                                     f"de {identity} ({hr_receta} compases): peso armónico reducido (W402)",
                          "fix": f"usa {hr_receta} o más"})

    # ---- protagonist: id válido y coherente --------------------------------------
    prot = plan.values.get("protagonist")
    inst_dec = project.instruments
    if prot not in (None, "", "none"):
        if prot not in inst_catalog:
            errors.append({"code": "E110", "where": "protagonist",
                           "message": f"protagonista '{prot}' no está en el catálogo real de 8 instrumentos",
                           "fix": "elige uno del catálogo: " + ", ".join(inst_catalog)})
        elif prot in inst_dec and inst_dec[prot].role == model.ROLE_OFF:
            errors.append({"code": "conflicto", "where": f"instruments.{prot}",
                           "message": f"el protagonista '{prot}' tiene role=off en la tabla de instrumentos",
                           "fix": f"cambia el rol de '{prot}' o elige otro protagonista"})
        elif not suena(prot, model.Section(id="x", label="x", type="verse", bars=4)):
            if prot in base_set:
                pass        # en el set base y sin off: suena
            else:
                conf = inst_dec.get(prot)
                if conf is None or conf.enabled is not True:
                    warns.append({"code": "E114-riesgo", "where": f"instruments.{prot}",
                                  "message": f"protagonista '{prot}' está fuera del set base de {identity}: "
                                             "Composer escribirá enabled=true para que suene; el "
                                             "validador real puede emitir E114 si no puede inicializarse "
                                             "con seguridad",
                                  "fix": f"revisa la tabla de instrumentos si el validador se queja"})
    # rol 'protagonista' en la tabla sin eje protagonista activo: el rol NO
    # llega al doc por sí solo (es informativo) — aviso honesto.
    hay_rol_protagonista = any(c.role == model.ROLE_PROTAGONIST for c in inst_dec.values())
    if hay_rol_protagonista and not prot:
        warns.append({"code": "conflicto-suave", "where": "instruments",
                      "message": "hay rol 'protagonista' en la tabla pero el eje protagonista no "
                                 "está fijado ni automático: el rol solo es informativo y NO llega al doc",
                      "fix": "fija el eje protagonista (módulo A) o aplica la propuesta de distribución"})
    for iid, conf in inst_dec.items():
        if iid not in inst_catalog:
            errors.append({"code": "E110", "where": f"instruments.{iid}",
                           "message": f"'{iid}' no está en el catálogo real de 8 instrumentos",
                           "fix": "usa el catálogo: " + ", ".join(inst_catalog)})
        if conf.role == model.ROLE_OFF and conf.enabled:
            errors.append({"code": "conflicto", "where": f"instruments.{iid}",
                           "message": f"'{iid}' está desactivado (role=off) pero enabled=true fijado",
                           "fix": "elige uno: role=off o enabled=true"})
        if conf.role == model.ROLE_PROTAGONIST and prot and prot != iid:
            errors.append({"code": "conflicto", "where": f"instruments.{iid}",
                           "message": f"hay dos protagonistas fijados: '{prot}' y '{iid}'",
                           "fix": "deja UN protagonista (prioridad funcional) y al resto como acompañantes"})
        if conf.density is not None and iid in ("bass", "drums", "pad", "strings"):
            warns.append({"code": "W410", "where": f"instruments.{iid}.density",
                          "message": f"density de '{iid}' no tiene traducción en v1 (el validador lo avisará)",
                          "fix": "quita la density de este instrumento o ignora el aviso"})

    # ---- tonalidad / progresiones guiadas ---------------------------------------------
    # SEMÁNTICA DEFINITIVA Native/Guided (v1.1):
    #   * global NATIVA  → NO se escriben progressions[id]; las secciones con
    #     grados guiados NO viajan (advertencia EXPLÍCITA, nunca silencio).
    #     Los acordes literales SÍ viajan siempre (precedencia §2.8, posición 1).
    #   * global GUIADA  → cada sección con decisión guiada DEBE tener grados o
    #     acordes literales; una sección SIN decisión armónica se resuelve con
    #     la receta N1 del motor (advertencia explícita con la acción necesaria).
    #     Una sección marcada Nativa dentro de una composición guiada SÍ usa N1
    #     (capacidad soportada por la cadena de precedencia del compilador).
    language = plan.values.get("language") or project.fixed_value("language")
    key_lbl = plan.values.get("key") or project.fixed_value("key")
    harmony_mode = plan.values.get("harmony_mode") or "guided"
    if harmony_mode == "guided":
        if not key_lbl:
            errors.append({"code": "E103", "where": "harmony.key",
                           "message": "armonía guiada sin tonalidad: fíjala o deja el modo nativo",
                           "fix": "fija la tonalidad en el Módulo C"})
        else:
            try:
                keyinfo = H.parse_key(str(key_lbl))
            except H.HarmonyError as e:
                errors.append({"code": "E105", "where": "harmony.key",
                               "message": str(e), "fix": "usa 'C major', 'D minor'..."})
                keyinfo = None
            if keyinfo is not None:
                if not language:
                    errors.append({"code": "E103", "where": "harmony.language",
                                   "message": "falta el lenguaje armónico (requerido por el contrato)",
                                   "fix": "deja el lenguaje automático o fija uno"})
                secciones_sin_decision: List[str] = []
                for s in secs:
                    hs = project.harmony_sections.get(s.id)
                    if hs is None:
                        secciones_sin_decision.append(s.id)
                        continue
                    if hs.mode == "guided":
                        if not hs.numerals and not hs.chords:
                            errors.append({"code": "progresion", "where": f"sección {s.id}",
                                           "message": "sección guiada sin progresión ni acordes literales",
                                           "fix": f"escribe grados romanos (p. ej. 'I - III - vi - V'), acordes "
                                                  f"literales ('G/B - Dm9:2'), o cámbiala a Nativa"})
                        else:
                            if hs.numerals:
                                try:
                                    ch = H.resolve_progression(hs.numerals, keyinfo)
                                    if language:
                                        for w in H.tier_warnings(ch, language):
                                            warns.append({"code": "W414", "where": f"sección {s.id}",
                                                          "message": w, "fix": "usa calidades del vocabulario del lenguaje"})
                                    for w in H.diatonic_warnings(ch):
                                        tips.append({"code": "info", "where": f"sección {s.id}",
                                                     "message": w, "fix": "ok si es intencional (bVI, dominantes...)"})
                                except H.HarmonyError as e:
                                    errors.append({"code": "E113", "where": f"sección {s.id}",
                                                   "message": f"progresión: {e}",
                                                   "fix": "corrige el grado señalado"})
                            if hs.chords and not _split_literal_chords(hs.chords):
                                errors.append({"code": "E113", "where": f"sección {s.id}",
                                               "message": "acordes literales vacíos",
                                               "fix": "escribe símbolos reales separados por espacios ('G/B Dm9:2')"})
                if secciones_sin_decision:
                    warns.append({"code": "armonia-implicita", "where": "módulo C",
                                  "message": "modo GUIADO con secciones sin decisión armónica: "
                                             f"{', '.join(secciones_sin_decision)}. El motor usará su receta N1 "
                                             "para ellas (queda registrado en el Song Map como 'receta_n1'); "
                                             "NO es una conversión silenciosa",
                                  "fix": "escribe progresiones o acordes en esas secciones, aplica la plantilla "
                                         "del mood, o márcalas como Nativa si es intencional"})
    else:  # native
        guiadas_con_numeros = [s.id for s in secs
                               if (project.harmony_sections.get(s.id) or model.HarmonySection()).mode == "guided"
                               and (project.harmony_sections.get(s.id) or model.HarmonySection()).numerals]
        if guiadas_con_numeros:
            warns.append({"code": "guiada-ignorada", "where": "módulo C",
                          "message": "modo global NATIVA: las progresiones guiadas de "
                                     f"{', '.join(guiadas_con_numeros)} NO se escribirán al documento "
                                     "(el motor usará sus recetas N1 para esas secciones)",
                          "fix": "cambia el modo global a Guiada para que viajen, o marca esas "
                                 "secciones como Nativa si es intencional"})

    # ---- accesibilidad commercial sin hook (espejo EXACTO del validador) ---------------
    # El validador cuenta hook = chorus con phrases/motif/loop_bars. Composer no
    # escribe phrases/motifs → el único hook posible aquí es loop_bars.
    access = plan.values.get("accessibility") or project.fixed_value("accessibility")
    if access == "commercial":
        hooks = [s for s in secs if s.type == "chorus" and s.loop_bars]
        if secs and not hooks:
            warns.append({"code": "W404", "where": "qa/structure",
                          "message": "commercial sin material de hook en ningún chorus "
                                     "(ni phrases, ni motif, ni loop_bars) — W404 del validador real",
                          "fix": "activa el hook (loop_bars) en un chorus o acepta el aviso"})

    # ---- tensión B3 sin pad/strings (W409; con suena() real por sección) ---------------
    tiene_dispositivo_global = bool({"pad", "strings"} & base_set) or \
        any(c.enabled for iid, c in inst_dec.items() if iid in ("pad", "strings"))
    for s in secs:
        t = s.tension
        if t is None and receta:
            t = (receta.get("tension_base") or {}).get(s.type)
        if t is not None and t >= BAND_B3_MIN and not dispositivo_pad_strings(s):
            # si el dispositivo existe en el set base pero active lo excluye, avisa igual
            if tiene_dispositivo_global:
                warns.append({"code": "W409", "where": f"sección {s.id}",
                              "message": f"tension {t} (banda B3) pero ni pad ni strings SUENAN en "
                                         f"'{s.id}' (active los excluye o están desactivados): "
                                         "dispositivos limitados a voicings — W409 del validador real",
                              "fix": "incluye pad/strings en active de esa sección o baja la tensión"})
            else:
                warns.append({"code": "W409", "where": f"sección {s.id}",
                              "message": f"tension {t} (banda B3) sin pad ni strings activos: "
                                         "los dispositivos de tensión quedan limitados a voicings — W409",
                              "fix": "activa pad o strings, o baja la tensión"})
            break

    # ---- espacios obligatorios con estructura propia del usuario (M6) -------------------
    spaces = plan.values.get("spaces")
    atm = plan.values.get("atmosphere")
    if spaces == "mandatory" and secs:
        hay_aire = any(s.type == "break" or (s.drums or "") in ("", "air", "light")
                       for s in secs)
        if not hay_aire:
            warns.append({"code": "conflicto-suave", "where": "módulo A/B",
                          "message": "espacios OBLIGATORIOS fijados pero tu estructura no tiene "
                                     "ninguna sección de aire (sin break y todo con drums groove/heavy)",
                          "fix": "añade un break con drums light, o baja spaces a 'sugeridos'"})
    if spaces == "mandatory" and atm == "dense":
        warns.append({"code": "conflicto-suave", "where": "módulo A",
                      "message": "espacios OBLIGATORIOS + atmósfera densa son intenciones opuestas: "
                                 "el resultado será más denso de lo que piden los espacios",
                      "fix": "elige atmósfera spacious/medium o baja spaces a 'sugeridos'"})

    # ---- final múltiple ---------------------------------------------------------------------
    finales = [s.id for s in secs if s.final]
    if len(finales) > 1:
        warns.append({"code": "W415", "where": "structure",
                      "message": f"final=true en {len(finales)} secciones {finales} (gana la última en orden) — W415",
                      "fix": "deja final solo en la sección que cierra"})

    # ---- drums off + improvisación no aplica (Composer no escribe improvisación) --------------
    for s in secs:
        if s.drums == "off":
            tips.append({"code": "info", "where": f"sección {s.id}",
                         "message": "drums off: sección sin batería; si el motor improvisara aquí "
                                    "no habría nivel que bajar (W418)", "fix": "ok para breaks totales"})

    return {"errores": errors, "avisos": warns, "sugerencias": tips}


def _section_fields(s: model.Section, hs: Optional[model.HarmonySection]) -> dict:
    """Campos reales de una sección del contrato (solo lo declarado).

    ``hs`` (decisión armónica de la sección) puede aportar:
      * acordes LITERALES (``chords``): posición 1 de la precedencia §2.8 —
        se escriben como ``structure[].chords`` SIEMPRE, con cualquier modo global;
      * chord_bars y resolution por sección (M1: se PROPAGAN, no se pierden).
    """
    out: Dict[str, Any] = {"id": s.id, "type": s.type, "bars": int(s.bars)}
    for campo in ("energy", "tension", "density"):
        v = getattr(s, campo)
        if v is not None:
            out[campo] = round(float(v), 4)
    if s.drums is not None:
        out["drums"] = s.drums
    if s.focus:
        out["focus"] = list(s.focus)[:3]
    if s.active is not None:
        out["active"] = list(s.active)
    if hs is not None and hs.chords:
        toks = _split_literal_chords(hs.chords)
        if toks:
            out["chords"] = toks
    if s.chord_bars is not None:
        out["chord_bars"] = int(s.chord_bars)
    elif hs is not None and hs.chord_bars is not None:
        out["chord_bars"] = int(hs.chord_bars)
    if s.resolution is not None:
        out["resolution"] = s.resolution
    elif hs is not None and hs.resolution is not None:
        out["resolution"] = hs.resolution
    if s.loop_bars is not None:
        out["loop_bars"] = int(s.loop_bars)
    if s.final:
        out["final"] = True
    return out


def build(project: model.ComposerProject, plan: R.ResolvedPlan,
          manifest: Optional[dict] = None) -> Tuple[dict, dict]:
    """Proyecto + plan → (documento dark-director/1, info de construcción).

    Devuelve el doc SOLO si no hay conflictos duros; los errores se reportan
    por separado (el llamador decide). Nunca escribe campos desconocidos.
    """
    secs = ST.normalize_sections(project.sections, manifest)
    dec = project.decisions

    def fixed(eje: str) -> Any:
        return project.fixed_value(eje)

    auto = plan.values
    identity = auto.get("identity") or fixed("identity")
    receta = ((manifest or {}).get("recetas") or {}).get(identity) or {}
    base_set = set(receta.get("set_base") or [])
    access = auto.get("accessibility") if (dec.get("accessibility") or {}).get("mode") == model.AUTO \
        else fixed("accessibility")
    language = auto.get("language") if (dec.get("language") or {}).get("mode") == model.AUTO \
        else fixed("language")
    key_lbl = auto.get("key") if (dec.get("key") or {}).get("mode") in (model.AUTO, model.FREE) \
        else fixed("key")
    resolution = auto.get("resolution") if (dec.get("resolution") or {}).get("mode") == model.AUTO \
        else fixed("resolution")
    hr = auto.get("harmonic_rhythm_bars") if (dec.get("harmonic_rhythm_bars") or {}).get("mode") == model.AUTO \
        else fixed("harmonic_rhythm_bars")

    doc: Dict[str, Any] = {"schema": "dark-director/1"}
    doc["meta"] = {"title": project.name}
    if project.notes:
        doc["meta"]["notes"] = project.notes[:300]
    doc["direction"] = {"identity": identity}
    if access:
        doc["direction"]["accessibility"] = access
    glob: Dict[str, Any] = {}
    if auto.get("bpm") is not None or fixed("bpm") is not None:
        glob["bpm"] = int(auto.get("bpm") or fixed("bpm"))
    # seed Libre = el doc NO lleva global.seed (el motor usa la suya); Fixed/Auto sí.
    if (dec.get("seed") or {}).get("mode") != model.FREE and plan.seed_used is not None:
        glob["seed"] = int(plan.seed_used)
    if glob:
        doc["global"] = glob

    # ---- harmony -----------------------------------------------------------------
    h: Dict[str, Any] = {}
    keyinfo = None
    if key_lbl:
        keyinfo = H.parse_key(str(key_lbl))
        h["key"] = keyinfo.label
    if language:
        h["language"] = language
    if resolution:
        h["resolution"] = resolution
    if hr is not None:
        h["harmonic_rhythm_bars"] = int(hr)
    harmony_mode = plan.values.get("harmony_mode") or "guided"
    progressions: Dict[str, List[str]] = {}
    if harmony_mode == "guided" and keyinfo is not None:
        for s in secs:
            hs = project.harmony_sections.get(s.id)
            if hs and hs.mode == "guided" and hs.numerals:
                ch = H.resolve_progression(hs.numerals, keyinfo)
                progressions[s.id] = [c.symbol for c in ch]
    if progressions:
        h["progressions"] = progressions
    doc["harmony"] = h

    # ---- instruments ----------------------------------------------------------------
    insts: Dict[str, Any] = {}
    prot = plan.values.get("protagonist")
    for iid, conf in project.instruments.items():
        entry: Dict[str, Any] = {}
        if conf.role == model.ROLE_OFF:
            entry["enabled"] = False
        elif conf.enabled is True:
            entry["enabled"] = True
        if conf.density is not None:
            entry["density"] = round(float(conf.density), 4)
        if entry:
            insts[iid] = entry
    # protagonista fuera del set base → enabled=true explícito (única forma de que suene)
    if prot and base_set and prot not in base_set:
        entry = insts.setdefault(prot, {})
        if entry.get("enabled") is not False:
            entry["enabled"] = True
    if insts:
        doc["instruments"] = insts

    # ---- structure ------------------------------------------------------------------
    doc["structure"] = [_section_fields(s, project.harmony_sections.get(s.id)) for s in secs]

    # ---- ending -----------------------------------------------------------------------
    ending_kind = plan.values.get("ending")
    if ending_kind and ending_kind != "none" and secs:
        last_bars = secs[-1].bars
        if ending_kind == "fade_out":
            doc["ending"] = {"fade_out": {"enabled": True, "bars": min(4, last_bars)}}
        elif ending_kind == "tape_stop":
            doc["ending"] = {"tape_stop": {"enabled": True, "bars": min(2, last_bars)}}

    # ---- info de construcción (fuente de verdad para manifest y Song Map) -------------
    chords_literales = sorted(
        s.id for s in secs
        if (project.harmony_sections.get(s.id) or model.HarmonySection()).chords)
    secciones_nativas = sorted(
        s.id for s in secs
        if (project.harmony_sections.get(s.id) or model.HarmonySection()).mode == "native")
    secciones_sin_decision = sorted(s.id for s in secs if s.id not in project.harmony_sections)
    tiene_chords = any(s.get("chords") for s in doc["structure"])
    modo_real = "guided" if (progressions or tiene_chords) else "native"
    info = {"harmony_mode": harmony_mode, "language": language, "key": key_lbl,
            "progressions_secciones": sorted(progressions.keys()),
            "chords_literales": chords_literales,
            "secciones_nativas": secciones_nativas,
            "secciones_sin_decision": secciones_sin_decision,
            "modo_real_del_doc": modo_real,
            "identity": identity, "accessibility": access,
            "nativas_n1": not progressions and not tiene_chords}
    return doc, info
