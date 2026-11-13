"""Compilador ``dark-director/1`` → ``midi-forge/1`` (Fase 1 + Fase 2).

Instrucción 09 (Fase 1): primera receta N1 real (dark_triphop), identidad
dark_triphop, accesibilidad balanced, validador E1xx, traducción de los 7 tipos
de sección, emisión de ``meta.director``, golden test determinista y regresión.

RESPUESTA 09 (Fase 2): identidades doom_triphop y doom_dark_jazz mediante
recetas con TABLA declarativa ``BLOQUES[type][instrumento]`` (deltas C1–C5 de
§6.3, implementación localizada — dark_triphop sigue usando sus ramas por rol y
produce el MISMO proyecto golden byte a byte):
  C1  consumidor genérico de tabla de receta (estilo/params/velocity por type
      × instrumento), con las traducciones compartidas intactas (bandas de
      density §2.6.5, deltas de focus §2.6.4, cluster B3 §2.6.6, approach por
      resolution §2.4.1, escalera de drums §2.6.3);
  C2  ``from_bar``/``to_bar`` y ``seed`` de bloque desde la tabla de receta;
  C3  ``AUTOMACION`` de receta → ``project["automation"]`` (referencias de
      sección por TYPE resueltas a la primera sección de ese type; type ausente
      → entrada omitida; dark_triphop declara AUTOMACION = ausente → []);
  C4  pistas base strings/piano llegan por la tabla (las ramas de
      inicialización §2.5.1 para pistas NO base quedan intactas);
  C5  validación de coherencia de la tabla en el registro (recetas.verificar
      _tabla_bloques; ver identities/__init__.py).

Responsabilidades (una sola ruta, determinista):
  1. valida la entrada con ``validador.validar`` (E1xx/E2xx bloquean; E3xx
     bloquea solo con ``qa.strict`` y, sin strict, se omite la entrada
     no soportable reportándolo — §2.10/§2.3 excepción 6);
  2. carga la receta N1 de la identidad (fail-fast §2.6.5; sin receta →
     ``RecetaNoDefinida``: no se inventa nada);
  3. expande la escalera de precedencia §2.3 (N1 receta → N2 accesibilidad →
     N3 global → N4 harmony → N5 instruments → N6 structure → N7 dev/ending/qa);
  4. emite un proyecto ``midi-forge/1`` completo (pistas, secciones, bloques
     por pista, lead.phrases con motifs, automation de receta si la identidad
     la declara, ending, guardrails) listo para ``forge.adapter.normalize``
     → ``forge.engine.generate``.

Lo que este compilador NO hace (límites documentados):
  - phrasegen (sin generador de hooks; los hooks son frases escritas o
    generativo existente);
  - campos nuevos del contrato rev. 3.2 (todo lo nuevo vive en DATOS de receta).
"""

import copy

from . import accesibilidad, contract, inicializacion, recetas
from . import identities as _identidades
from . import validador as _validador

# ------------------------------------------------------------------ tablas §2.6
#: §2.6.2: energy → rampa de velocity [v0, v1] (única traducción de energy)
RAMPAS_ENERGY = [
    (0.25, (55, 65)),
    (0.50, (68, 80)),
    (0.75, (82, 96)),
    (float("inf"), (98, 110)),
]
#: §2.6.5: traducción de density por banda (solo parámetros reales del motor)
SAX_DENSITY = {"B1": 0.20, "B2": 0.40, "B3": 0.60}          # >0.60 se recorta a 0.60
KEYS_HOLD_RESTRIKE = {"B1": 0, "B2": 4, "B3": 2}            # hold: restrike_beats
KEYS_BROKEN_REST = {"B1": 0.45, "B2": 0.25, "B3": 0.05}     # broken: rest_prob
KEYS_TAIL_NOTAS = {"B1": 1, "B2": 2, "B3": 2}               # tail: notes_per_chord
MALLET_REPLIES = {"B1": (0.25, 1), "B2": (0.45, 2), "B3": (0.60, 2)}   # (prob, max_per_bar)
MALLET_PINGS = {"B1": 1, "B2": 2, "B3": 3}                  # pings: count
#: §2.6.6: perfil de voicing de keys por banda de tension
VOICING_POR_TENSION = {"B1": "full", "B2": "shell", "B3": "rootless"}
#: §2.6.4: deltas de focus por posición
FOCUS_DELTA_VEL = (8, 4, 2)
FOCUS_DELTA_VEL_SCALE = (0.06, 0.03, 0.015)
FOCUS_VEL_SCALE_TOPE = 1.2

#: roles/programas del catálogo §2.5 (fuente: inicializacion.INIT_CATALOG)
ROL_DE = {iid: spec["rol"] for iid, spec in inicializacion.INIT_CATALOG.items()}
PROGRAMA_DE = {"sax_tenor": 66, "rhodes": 4, "vibraphone": 11, "piano": 0,
               "pad": 91, "strings": 50, "bass": None, "drums": None}

_ESCALERA_DRUMS = ("off", "air", "light", "groove", "heavy")

_NOMBRES_NOTA = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")

_E3X_OMISIBLES = {"E301", "E302", "E303"}


class DirectorInvalido(ValueError):
    """La entrada viola el contrato (códigos E bloqueantes)."""

    def __init__(self, resultado):
        self.resultado = resultado
        codigos = [c for c, _m in resultado.get("errores", [])]
        super().__init__("entrada inválida según dark-director/1: " + "; ".join(
            f"{c}: {m}" for c, m in resultado.get("errores", [])))


class StrictBloqueante(ValueError):
    """E3xx presente con ``qa.strict=true`` (§2.10: bloquea solo entonces)."""

    def __init__(self, resultado):
        self.resultado = resultado
        super().__init__("qa.strict=true: capacidades no soportadas (E3xx): "
                         + "; ".join(f"{c}: {m}" for c, m in resultado.get("e3xx", [])))


# ------------------------------------------------------------------ helpers
def _doc_a_dict(doc):
    import json
    if isinstance(doc, (str, bytes)):
        try:
            doc = json.loads(doc)
        except ValueError as e:
            res = _validador.validar(None)
            res["errores"] = [("E101", f"JSON malformado: {e}")]
            raise DirectorInvalido(res)
    return doc


def _rampa_energy(energy):
    for tope, rampa in RAMPAS_ENERGY:
        if energy <= tope:
            return list(rampa)
    return [98, 110]


def _banda_densidad(inst, seccion, d_receta, insts):
    """density efectiva §2.6.5 de un instrumento en una sección (con clamp)."""
    d_inst = (insts.get(inst) or {}).get("density")
    d_secc = seccion.get("density")
    return contract.density_band(contract.density_efectiva(d_inst, d_secc, d_receta))


def _instanciar_simbolo(tonic_pc, offset, calidad):
    """(tónica, offset en semitonos, calidad) → símbolo 'Root' + calidad."""
    return _NOMBRES_NOTA[(tonic_pc + offset) % 12] + calidad


def _nivel_drums_menos_uno(nivel):
    i = _ESCALERA_DRUMS.index(nivel)
    return _ESCALERA_DRUMS[max(0, i - 1)]


def _vel_con_delta(vel, delta, cap):
    if vel is None:
        return None
    if isinstance(vel, list):
        return [max(1, min(cap, v + delta)) for v in vel]
    return max(1, min(cap, vel + delta))


def _resolver_seccion_ref(ref, secs_in):
    """C3: resuelve una referencia de sección de la AUTOMACION de receta.
    Si ``section`` coincide con un TYPE del contrato y no con un id real, se
    sustituye por el id de la PRIMERA sección de ese type; si el type no existe
    en la estructura, devuelve None (la entrada se omite: nunca se inventa una
    sección). Las referencias válidas del motor (id real, 'start'/'end'/'last',
    índice int) pasan sin cambios."""
    if not isinstance(ref, dict):
        return ref
    sid = ref.get("section")
    if sid is None or sid in ("start", "end", "last") or isinstance(sid, int):
        return ref
    if any(s["id"] == sid for s in secs_in):
        return ref
    if sid in contract.SECTION_TYPES:
        for s in secs_in:
            if s["type"] == sid:
                return dict(ref, section=s["id"])
        return None
    return None


def _bloque_de_tabla(receta, entrada, *, delta, cap, banda_tension, resp_decl):
    """C1: materializa un bloque de la tabla ``BLOQUES[type][instrumento]`` de
    la receta en el formato de bloque del motor. Claves de receta que se
    consumen y retiran aquí: ``clusters_b3`` (clusters que se añaden a
    ``params.tension`` SOLO si la banda de tension de la sección es B3 — §2.6.6,
    la tensión sigue siendo del compositor; mecanismo real pad/strings/keys
    ``tension`` de gen_chordal). ``lead_auto`` la procesa el caller (necesita
    contexto de frases/improvisación)."""
    b = copy.deepcopy(entrada)
    clusters = b.pop("clusters_b3", None)
    params = dict(b.get("params") or {})
    if clusters and banda_tension == "B3":
        params["tension"] = list(params.get("tension") or []) + copy.deepcopy(clusters)
    b["params"] = params
    # mallet replies: respond_to es SIEMPRE el lead real (E302 ya filtrado;
    # mismo criterio que las ramas por rol)
    if b.get("style") == "replies":
        params.setdefault("respond_to", resp_decl.get("responds_to", receta.LEAD))
    # deltas de focus §2.6.4 sobre la velocity declarada (misma regla que las
    # ramas por rol; drums no declara velocity en las tablas)
    vel = b.get("velocity")
    if vel is not None:
        b["velocity"] = _vel_con_delta(vel, delta, cap)
    b.setdefault("enabled", True)
    b.setdefault("from_bar", 0)
    b.setdefault("to_bar", None)
    return b


def _recoger_x_fields(doc, conocidos_por_nivel):
    """Recoge TODOS los campos x_* del documento (cualquier nivel) para
    incrustarlos en meta.director. Los de la raíz conservan su nombre; los
    anidados llevan el prefijo de ruta 'nivel.x_nombre' (formato de emisión
    del compilador; el contrato exige conservarlos, no fija su aplanado)."""
    extras = {}

    def recorrer(obj, ruta):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if contract.es_campo_extension(k):
                    extras[f"{ruta}.{k}" if ruta else k] = copy.deepcopy(v)
                elif isinstance(v, dict) and k in conocidos_por_nivel:
                    recorrer(v, f"{ruta}.{k}" if ruta else k)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            recorrer(item, f"{ruta}.{k}" if ruta else k)
    recorrer(doc, "")
    return extras


# ------------------------------------------------------------------ compilador
def compilar(doc):
    """Compila un documento ``dark-director/1`` (dict o string JSON) a un
    proyecto ``midi-forge/1``. Devuelve un dict con el proyecto y el informe.
    Lanza DirectorInvalido (E1xx/E2xx) o StrictBloqueante (E3xx con strict)."""
    doc = _doc_a_dict(doc)
    resultado = _validador.validar(doc)
    if resultado["errores"]:
        raise DirectorInvalido(resultado)

    qa = doc.get("qa") or {}
    strict = bool(qa.get("strict"))
    e3xx = [x for x in resultado["e3xx"] if x[0] in _E3X_OMISIBLES]
    if strict and e3xx:
        raise StrictBloqueante(resultado)
    omitidos = [f"{c}: {m}" for c, m in e3xx]

    identity = doc["direction"]["identity"]
    if identity not in _identidades.CON_RECETA:
        raise recetas.RecetaNoDefinida(
            f"la receta N1 de '{identity}' no está registrada todavía "
            f"(recetas registradas: {', '.join(_identidades.CON_RECETA)}")
    receta = getattr(_identidades, identity)
    # C1: recetas con tabla declarativa (Fase 2). dark_triphop no declara
    # BLOQUES → None → rutas por rol originales (salida golden idéntica).
    tabla_bloques = getattr(receta, "BLOQUES", None)

    access = doc["direction"]["accessibility"]
    g = doc.get("global") or {}
    h = doc.get("harmony") or {}
    insts = doc.get("instruments") or {}
    dev = doc.get("development") or {}
    ending = doc.get("ending") or {}
    language = h["language"]
    secs_in = doc["structure"]

    # C3: AUTOMACION de receta → automation del proyecto (referencias por TYPE
    # resueltas contra la estructura real; type ausente → entrada omitida).
    automacion_receta = []
    if tabla_bloques is not None:
        for entrada in copy.deepcopy(getattr(receta, "AUTOMACION", [])):
            f = _resolver_seccion_ref(entrada.get("from"), secs_in)
            t = _resolver_seccion_ref(entrada.get("to"), secs_in)
            if f is None or t is None:
                continue        # la receta referencia un type sin sección aquí
            automacion_receta.append(dict(entrada, **{"from": f, "to": t}))

    tonic_pc, _modo = _theory().parse_key(h["key"])
    langs_prog = receta.PROGRESIONES[language]
    improv_secs = [i for i in (dev.get("improvisation") or []) if i.get("instrument") == _validador.LEAD]
    improv_ids = {i["section"] for i in improv_secs}
    phrases = copy.deepcopy((dev.get("melody") or {}).get("phrases") or {})
    motifs = dev.get("motifs") or {}

    # --- pistas ---------------------------------------------------------------
    base = tuple(receta.SET_BASE)
    tracks = []
    for iid in contract.INSTRUMENT_IDS:
        conf = insts.get(iid) or {}
        en_base = iid in base
        enabled_flag = conf.get("enabled")
        if enabled_flag is False:
            continue
        if not en_base and enabled_flag is not True:
            continue
        # E114 defensivo (el validador ya lo bloquea; aquí no se emite pista parcial)
        existe_lead = (receta.LEAD in base or (insts.get(receta.LEAD) or {}).get("enabled") is True)
        estado, detalle = inicializacion.estado_inicializacion(
            iid, en_base=en_base, existe_lead=existe_lead, receta_da_datos=True)
        if estado == "E114":
            res = {"errores": [("E114", detalle)], "e3xx": [], "avisos": [], "no_verificados": []}
            raise DirectorInvalido(res)
        if estado != "ok" and estado != "ok-base":
            continue
        track = {"id": iid, "role": ROL_DE[iid], "enabled": True}
        prog = PROGRAMA_DE[iid]
        if iid == "bass":
            prog = 32 if conf.get("type") == "upright" else 38
        if prog is not None:
            track["program"] = prog
        rango = conf.get("register") or receta.REGISTER_DEFAULT.get(iid)
        if rango is not None:
            track["range"] = list(rango)
        tracks.append(track)
    track_ids = [t["id"] for t in tracks]

    # ---ENDING----------------------------------------------------------------
    last = secs_in[-1]
    proj_ending = {}
    fade = ending.get("fade_out")
    if isinstance(fade, dict) and fade.get("enabled"):
        n = fade.get("bars", 4)
        start = {"section": last["id"], "bar": max(0, last.get("bars", 0) - n)}
        f = {"enabled": True, "cc": 11, "start": start}
        if "exponent" in fade:
            f["exponent"] = fade["exponent"]
        proj_ending["fade_out"] = f
    elif fade is True:
        n = 4
        proj_ending["fade_out"] = {"enabled": True, "cc": 11,
                                   "start": {"section": last["id"], "bar": max(0, last.get("bars", 0) - n)}}
    tape = ending.get("tape_stop")
    if isinstance(tape, dict) and tape.get("enabled"):
        t = {"enabled": True, "bars": tape.get("bars", 2)}
        if "semitones" in tape:
            t["semitones"] = tape["semitones"]
        if "exponent" in tape:
            t["exponent"] = tape["exponent"]
        proj_ending["tape_stop"] = t
    elif tape is True:
        proj_ending["tape_stop"] = {"enabled": True, "bars": 2}

    # --- guardrails (N2 accesibilidad + N7 qa, con regla motif_repeat §2.11) --
    guardrails_decl = (qa.get("guardrails") or {})
    guardrails = accesibilidad.guardrails_default(access)
    guardrails.update({k: v for k, v in guardrails_decl.items() if isinstance(v, bool)})
    mr_declarado = "motif_repeat" in guardrails_decl
    hay_loop_nochocho = any(mo.get("loop_bars", 8) != 8 for mo in motifs.values())
    if guardrails["motif_repeat"] and hay_loop_nochocho and not mr_declarado:
        guardrails["motif_repeat"] = False   # §2.11: derivado → OFF + W408 (ya avisado)

    # --- responses del vibráfono (declaración explícita prevalece, §2.5.1).
    # E302 (responds_to ≠ lead) ya fue reportado: esa clave se IGNORA y se usa
    # el lead real — las estrategias no propagan entradas no soportables.
    resp_decl = (dev.get("responses") or {}).get("vibraphone") or {}
    resp_decl = {k: v for k, v in resp_decl.items() if not (k == "responds_to" and v != _validador.LEAD)}

    # --- copia de motifs (§2.7.1) --------------------------------------------
    motif_loop_por_seccion = {}
    for nombre, mo in motifs.items():
        src = mo.get("from_section")
        t = mo.get("transpose_st", 0) or 0
        lo_r, hi_r = (insts.get(receta.LEAD) or {}).get("register") or receta.REGISTER_DEFAULT[receta.LEAD]
        for dst in (mo.get("sections") or []):
            sec_d = next(s for s in secs_in if s["id"] == dst)
            notas = []
            for n in phrases.get(src, []) or []:
                if n.get("bar", 0) >= sec_d.get("bars", 0):
                    continue                        # truncado (W407 ya avisado)
                p = _validador.parse_pitch(n.get("pitch"))
                if p is None:
                    continue
                pt = p + t
                if not (lo_r <= pt <= hi_r):
                    continue                        # descartada (W413 ya avisado)
                nn = dict(n)
                nn["pitch"] = pt
                notas.append(nn)
            if "loop_bars" in mo:
                motif_loop_por_seccion[dst] = mo["loop_bars"]
            phrases.setdefault(dst, [])
            phrases[dst] = list(phrases[dst]) + notas

    # --- secciones y bloques ---------------------------------------------------
    proj_secs = []
    orden = secs_in
    for idx, s in enumerate(orden):
        sid, stype, bars = s["id"], s["type"], s["bars"]
        es_ultima = (idx == len(orden) - 1)
        kind = "pre" if stype == "pre_chorus" else stype
        # acordes: precedencia §2.8
        if s.get("chords") is not None:
            acordes = copy.deepcopy(s["chords"])
            fuente_acordes = "explicito"
        elif (h.get("progressions") or {}).get(sid) is not None:
            acordes = copy.deepcopy(h["progressions"][sid])
            fuente_acordes = "progressions_id"
        elif (h.get("progressions") or {}).get(stype) is not None:
            acordes = copy.deepcopy(h["progressions"][stype])
            fuente_acordes = "progressions_type"
        else:
            acordes = [_instanciar_simbolo(tonic_pc, off, cal) for off, cal in langs_prog[stype]]
            fuente_acordes = "receta_n1"
        chord_bars = s.get("chord_bars") or h.get("harmonic_rhythm_bars") or receta.HARMONIC_RHYTHM_BARS
        energy = s.get("energy", receta.ENERGY_BASE[stype])
        tension = s.get("tension", receta.TENSION_BASE[stype])
        nivel_drums = s.get("drums") or receta.DRUMS_NIVEL[stype]
        if sid in improv_ids:
            nivel_drums = _nivel_drums_menos_uno(nivel_drums)

        active = s.get("active")
        focus = list(s.get("focus") if s.get("focus") is not None else receta.FOCUS_DEFAULT[stype])
        # focus filtrado §2.6.4 (solo suenan; W406 ya avisado por el validador)
        focus_suenan = []
        for f in focus[:3]:
            if _suena(f, base, insts, active):
                focus_suenan.append(f)

        def suena(iid):
            return _suena(iid, base, insts, active)

        material_escrito = (sid in phrases) or (sid in motif_loop_por_seccion)

        sec_out = {"id": sid, "name": sid, "kind": kind, "bars": bars,
                   "final": bool(s.get("final")), "chords": acordes,
                   "chord_bars": chord_bars, "velocity": _rampa_energy(energy),
                   "blocks": {}}

        # resolución efectiva de la transición (§2.4): cadena exclusiva
        res_efectiva = s.get("resolution") or h.get("resolution") or _validador.LANG_DEFAULT_RES[language]
        aplicar_resolucion = (not es_ultima) and bars >= 2

        banda_tension = contract.density_band(tension)
        bloque_pad_tension = (banda_tension == "B3")

        for t in tracks:
            iid = t["id"]
            if not suena(iid):
                sec_out["blocks"][iid] = {"enabled": False, "style": "none", "params": {},
                                          "from_bar": 0, "to_bar": None}
                continue
            pos_f = focus_suenan.index(iid) if iid in focus_suenan else None
            delta = FOCUS_DELTA_VEL[pos_f] if (pos_f is not None and iid != "drums") else 0
            rol = t["role"]

            # --- pista enabled=true FUERA del set base: bloque inicializado
            # determinista de §2.5.1 (rol/bloque del catálogo; velocity = rampa de
            # energy + ROLE_VEL_OFFSET, sin clave velocity: la aplica el motor).
            # Se evalúa ANTES de las ramas de receta (que gobiernan solo pistas base).
            if iid not in base:
                spec = inicializacion.INIT_CATALOG[iid]
                estilo = spec["bloque"]
                params = {}
                if estilo == "hold":          # keys inicializadas (piano): §2.5.1
                    params["voicing"] = {"profile": "full"}
                    banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                    params["restrike_beats"] = KEYS_HOLD_RESTRIKE[banda]
                elif estilo == "sustain":     # pad/strings inicializadas
                    params["voicing"] = {"profile": "full"}
                    if estilo == "sustain" and rol == "pad" and bloque_pad_tension:
                        # §2.5.1: sin tension[] propio; los clusters llegan SOLO por
                        # la traducción de structure[].tension (§2.6.6)
                        params["tension"] = [copy.deepcopy(receta.PAD_TENSION_CLUSTER)]
                elif estilo == "generative":  # sax inicializado (rama futura)
                    banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                    params = {"density": min(SAX_DENSITY[banda], 0.60),
                              "range": list(t.get("range") or receta.REGISTER_DEFAULT.get(iid, [62, 88]))}
                elif estilo == "replies":     # vibráfono inicializado (rama futura)
                    banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                    prob, mpb = MALLET_REPLIES[banda]
                    params = {"respond_to": resp_decl.get("responds_to", receta.LEAD),
                              "prob": resp_decl.get("prob", prob),
                              "max_per_bar": resp_decl.get("max_per_bar", mpb)}
                sec_out["blocks"][iid] = {"enabled": True, "style": estilo, "params": params,
                                          "from_bar": 0, "to_bar": None}
                continue

            # --- C1/Fase 2: recetas con tabla declarativa BLOQUES[type][iid] ---
            # (doom_triphop / doom_dark_jazz). dark_triphop no declara tabla y
            # nunca entra aquí (salida golden idéntica). La tabla es el DEFAULT
            # del type; para drums, si el compositor fuerza otro nivel o la
            # improvisación baja un nivel, se usa la escalera genérica §2.6.3.
            if tabla_bloques is not None:
                fila_tipo = tabla_bloques.get(stype)
                if not isinstance(fila_tipo, dict) or iid not in fila_tipo:
                    raise recetas.RecetaError(
                        f"receta '{receta.IDENTITY}': tabla BLOQUES incompleta "
                        f"(type '{stype}', instrumento '{iid}'); C5 debió bloquear el registro")
                es_tabla = True
                if rol == "drums" and nivel_drums != receta.DRUMS_NIVEL[stype]:
                    es_tabla = False       # override del compositor o improv → escalera
                if es_tabla:
                    blk = _bloque_de_tabla(receta, fila_tipo[iid], delta=delta,
                                           cap=g.get("velocity_cap", 110),
                                           banda_tension=banda_tension,
                                           resp_decl=resp_decl)
                    params = blk["params"]
                    if rol == "drums" and pos_f is not None:
                        vs = params.get("vel_scale")
                        if vs is not None:
                            params["vel_scale"] = round(min(FOCUS_VEL_SCALE_TOPE,
                                                            vs + FOCUS_DELTA_VEL_SCALE[pos_f]), 4)
                    if (rol == "bass" and blk.get("style") == "pattern"
                            and blk.get("enabled", True)):
                        # §2.4.1/D-03: el gesto cromático solo con resolution
                        # tonal/chromatic (idéntico criterio que dark_triphop)
                        if aplicar_resolucion and res_efectiva in ("tonal", "chromatic"):
                            params["approach"] = {"enabled": True, "every": 2,
                                                  "offset": (bars - 1) % 2}
                        else:
                            params["approach"] = {"enabled": False}
                    if (rol == "lead" and blk.get("enabled", True)
                            and fila_tipo[iid].get("lead_auto")):
                        # §2.7 (precedencia N6 > N1): la improvisación explícita
                        # del compositor gana TAMBIÉN sobre filas hold (el sax pasa
                        # a generativo con density por banda). El resto de la
                        # lógica §2.7.1 aplica solo a filas auto/generative:
                        # material escrito → auto (+ loop_bars del motif); si no →
                        # generativo/auto con density por banda §2.6.5. Los defaults
                        # generativos de la receta (LEAD_GENERATIVO) se fusionan
                        # como BASE: los params de la tabla prevalecen (la receta
                        # puede afinar long_prob / contour por tipo).
                        gen_defaults = copy.deepcopy(receta.LEAD_GENERATIVO)
                        if sid in improv_ids and improv_secs:
                            blk["style"] = "generative"
                            params["range"] = list(t.get("range") or receta.REGISTER_DEFAULT[iid])
                            banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                            params["density"] = min(SAX_DENSITY[banda], 0.60)
                            gen_defaults.update(params)
                            params.clear()
                            params.update(gen_defaults)
                        elif blk.get("style") in ("auto", "generative"):
                            if material_escrito:
                                blk["style"] = "auto"   # density no aplica (W410)
                                if sid in motif_loop_por_seccion:
                                    params["loop_bars"] = motif_loop_por_seccion[sid]
                            else:
                                banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                                params["density"] = min(SAX_DENSITY[banda], 0.60)
                                gen_defaults.update(params)
                                params.clear()
                                params.update(gen_defaults)
                            params["range"] = list(t.get("range") or receta.REGISTER_DEFAULT[iid])
                        elif material_escrito:
                            # filas hold con material escrito: el motor ya toca las
                            # frases en hold; solo se propaga loop_bars si existe
                            if sid in motif_loop_por_seccion:
                                params["loop_bars"] = motif_loop_por_seccion[sid]
                    sec_out["blocks"][iid] = blk
                    continue

            if rol == "drums":
                if nivel_drums == "off":
                    sec_out["blocks"][iid] = {"enabled": False, "style": "none", "params": {},
                                              "from_bar": 0, "to_bar": None}
                    continue
                params = {"preset": receta.DRUMS_PRESET_POR_NIVEL[nivel_drums],
                          "vel_scale": receta.DRUMS_VEL_SCALE_POR_NIVEL[nivel_drums]}
                if pos_f is not None:
                    params["vel_scale"] = round(min(FOCUS_VEL_SCALE_TOPE,
                                                    params["vel_scale"] + FOCUS_DELTA_VEL_SCALE[pos_f]), 4)
                if nivel_drums == "heavy" and receta.DRUMS_FILLS_HEAVY:
                    params["fills"] = copy.deepcopy(receta.DRUMS_FILLS_HEAVY)
                sec_out["blocks"][iid] = {"enabled": True, "style": "pattern", "params": params,
                                          "from_bar": 0, "to_bar": None}
                continue

            if rol == "bass":
                patrones = receta.BASS_PATRONES[stype]
                if patrones is None:
                    sec_out["blocks"][iid] = {"enabled": False, "style": "none", "params": {},
                                              "from_bar": 0, "to_bar": None}
                    continue
                params = {"patterns": copy.deepcopy(patrones)}
                if aplicar_resolucion and res_efectiva in ("tonal", "chromatic"):
                    params["approach"] = {"enabled": True, "every": 2, "offset": (bars - 1) % 2}
                else:
                    # modal/deceptive/open: la estrategia no añade approach (§2.4.1)
                    params["approach"] = {"enabled": False}
                params["slide_in"] = {"every": 8}    # constante de receta (voz del bajo trip-hop)
                params["slide_out"] = True
                vel = _vel_con_delta(receta.BASS_VELOCITY[stype], delta, g.get("velocity_cap", 110))
                sec_out["blocks"][iid] = {"enabled": True, "style": "pattern", "params": params,
                                          "velocity": vel, "from_bar": 0, "to_bar": None}
                continue

            if rol == "keys":
                estilo = receta.KEYS_ESTILO[stype]
                banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                params = {"voicing": {"profile": VOICING_POR_TENSION[banda_tension]}}
                if estilo == "hold":
                    params["restrike_beats"] = KEYS_HOLD_RESTRIKE[banda]
                elif estilo == "broken":
                    params["rest_prob"] = KEYS_BROKEN_REST[banda]
                elif estilo == "tail":
                    params["notes_per_chord"] = KEYS_TAIL_NOTAS[banda]
                vel = _vel_con_delta(receta.KEYS_VELOCITY[stype], delta, g.get("velocity_cap", 110))
                sec_out["blocks"][iid] = {"enabled": True, "style": estilo, "params": params,
                                          "velocity": vel, "from_bar": 0, "to_bar": None}
                continue

            if rol == "mallet":
                estilo = receta.MALLET_ESTILO[stype]
                banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                params = {}
                if estilo == "replies":
                    prob, mpb = MALLET_REPLIES[banda]
                    params["respond_to"] = resp_decl.get("responds_to", receta.LEAD)
                    params["prob"] = resp_decl.get("prob", prob)
                    params["max_per_bar"] = resp_decl.get("max_per_bar", mpb)
                else:  # pings
                    params["count"] = MALLET_PINGS[banda]
                vel = _vel_con_delta(receta.MALLET_VELOCITY[stype], delta, g.get("velocity_cap", 110))
                sec_out["blocks"][iid] = {"enabled": True, "style": estilo, "params": params,
                                          "velocity": vel, "from_bar": 0, "to_bar": None}
                continue

            if rol == "pad":
                params = {"voicing": {"profile": "rootfifth"}}
                if bloque_pad_tension:
                    params["tension"] = [copy.deepcopy(receta.PAD_TENSION_CLUSTER)]
                vel = _vel_con_delta(receta.PAD_VELOCITY[stype], delta, g.get("velocity_cap", 110))
                sec_out["blocks"][iid] = {"enabled": True, "style": "sustain", "params": params,
                                          "velocity": vel, "from_bar": 0, "to_bar": None}
                continue

            if rol == "lead":
                iid_lead = iid
                if stype == "intro":
                    sec_out["blocks"][iid] = {"enabled": False, "style": "none", "params": {},
                                              "from_bar": 0, "to_bar": None}
                    continue
                if stype == "outro" and not material_escrito:
                    vel = _vel_con_delta(receta.LEAD_VELOCITY[stype], delta, g.get("velocity_cap", 110))
                    sec_out["blocks"][iid] = {"enabled": True, "style": "hold",
                                              "params": {"legato": 1.0}, "velocity": vel,
                                              "from_bar": 0, "to_bar": None}
                    continue
                params = {"range": list(t.get("range") or receta.REGISTER_DEFAULT[iid_lead])}
                if sid in improv_ids and improv_secs:
                    # improvisación: bloque generativo explícito (§2.7)
                    banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                    params["density"] = min(SAX_DENSITY[banda], 0.60)
                    params.update(copy.deepcopy(receta.LEAD_GENERATIVO))
                    estilo = "generative"
                elif material_escrito:
                    estilo = "auto"     # frases propias o copiadas; density no aplica (W410)
                    if sid in motif_loop_por_seccion:
                        params["loop_bars"] = motif_loop_por_seccion[sid]
                else:
                    banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                    params["density"] = min(SAX_DENSITY[banda], 0.60)
                    params.update(copy.deepcopy(receta.LEAD_GENERATIVO))
                    estilo = "auto"
                vel = _vel_con_delta(receta.LEAD_VELOCITY[stype], delta, g.get("velocity_cap", 110))
                sec_out["blocks"][iid] = {"enabled": True, "style": estilo, "params": params,
                                          "velocity": vel, "from_bar": 0, "to_bar": None}
                continue

            # ramas restantes: únicamente pistas BASE gobernadas por la receta N1
            # (las inicializadas ya salieron por la rama §2.5.1 de arriba)
            spec = inicializacion.INIT_CATALOG.get(iid)
            params = {}
            estilo = spec["bloque"] if spec else "none"
            if estilo == "hold":
                params["voicing"] = {"profile": "full"}
                banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                params["restrike_beats"] = KEYS_HOLD_RESTRIKE[banda]
            elif estilo == "sustain":
                params["voicing"] = {"profile": "full"}
            elif estilo == "generative":
                banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                params = {"density": min(SAX_DENSITY[banda], 0.60)}
            elif estilo == "replies":
                banda = _banda_densidad(iid, s, receta.D_RECETA[stype], insts)
                prob, mpb = MALLET_REPLIES[banda]
                params = {"respond_to": resp_decl.get("responds_to", receta.LEAD),
                          "prob": resp_decl.get("prob", prob),
                          "max_per_bar": resp_decl.get("max_per_bar", mpb)}
            sec_out["blocks"][iid] = {"enabled": True, "style": estilo, "params": params,
                                      "from_bar": 0, "to_bar": None}

        proj_secs.append(sec_out)

    # --- meta.director ----------------------------------------------------------
    conocidos = {"meta", "direction", "global", "harmony", "instruments", "development", "ending", "qa"}
    x_fields = _recoger_x_fields(doc, conocidos)
    # x_* de la raíz → claves planas (mecanismo Fase 0, build_director_meta);
    # x_* ANIDADOS → sub-clave 'anidados' con su ruta (formato de emisión del
    # compilador: el contrato exige conservarlos, no fija su aplanado).
    x_raiz = {k: v for k, v in x_fields.items() if "." not in k}
    x_anidados = {k: v for k, v in x_fields.items() if "." in k}
    director_meta = contract.build_director_meta(x_fields=x_raiz)
    if x_anidados:
        director_meta["anidados"] = x_anidados
    director_meta["source_schema"] = contract.CONTRACT_ID
    director_meta["original"] = copy.deepcopy(doc)

    proyecto = {
        "schema": contract.TARGET_SCHEMA,
        "meta": {
            "name": (doc.get("meta") or {}).get("title", ""),
            "description": (doc.get("meta") or {}).get("notes", ""),
            "director": director_meta,
        },
        "global": {
            "bpm": g.get("bpm", receta.BPM_DEFAULT),
            "time_signature": [4, 4],
            "key": h["key"],
            "ticks_per_beat": 480,
            "seed": g.get("seed", 0),
            "humanize": g.get("humanize", 1.0),
            "velocity_cap": g.get("velocity_cap", 110),
            "preset": "triphop",          # presets existentes del motor; el contrato no añade
            "repair_clashes": True,
        },
        "tracks": tracks,
        "sections": proj_secs,
        "lead": {"phrases": phrases},
        "automation": automacion_receta,   # C3: datos de receta (dark_triphop → [])
        "ending": proj_ending,
        "guardrails": guardrails,
    }

    return {
        "proyecto": proyecto,
        "avisos": [f"{c}: {m}" for c, m in resultado["avisos"]],
        "e3xx_omitidos": omitidos,
        "no_verificados": list(resultado["no_verificados"]),
        "versiones": contract.contract_info(),
    }


def _suena(iid, base, insts, active):
    """¿Suena `iid` en la sección? (existencia + enabled + whitelist §2.6.1)."""
    if iid not in contract.INSTRUMENT_IDS:
        return False
    if (insts.get(iid) or {}).get("enabled") is False:
        return False
    existe = iid in base or (insts.get(iid) or {}).get("enabled") is True
    return existe and (active is None or iid in active)


_Theory = None


def _theory():
    global _Theory
    if _Theory is None:
        from . import forge_link
        _Theory = forge_link.import_forge().theory
    return _Theory
