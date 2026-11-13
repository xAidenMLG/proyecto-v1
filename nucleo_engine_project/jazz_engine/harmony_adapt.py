"""Harmonic Adaptation Engine — FASE 7.

Traduce una progresión en GRADOS de la biblioteca a la tonalidad/modo REALES
de la composición y aplica variaciones controladas (extensiones, sabor sus,
inversiones, sustituciones diatónicas, intercambio modal, resolución
deceptiva, colas de aproximación entre secciones). Puro y determinista:
mismo (entrada, tonalidad, sección, variación, seed) → mismos símbolos.

Reglas de familiaridad (misión FASE 7 §5 — «variación sin destruir familiaridad»):
  - El primer acorde del ciclo (ancla) solo puede recibir extensiones, y solo
    a partir de medium.
  - Presupuesto de transformaciones estructurales por nivel: subtle 0 /
    medium 2 / rich 3; las extensiones tienen presupuesto propio.
  - La huella del arquetipo (movimiento de raíces) se mide al final y se
    registra en la evidencia con aviso si cae bajo el umbral del nivel.
  - La cadencia del ciclo nunca se trunca a ciegas: si el ciclo no encaja en
    la sección se compacta (conservando ancla+cadencia) o se completa con giro
    (turnaround), y la sección SIEMPRE termina en acorde de cadencia.

Sin duplicar MIDI Forge: los símbolos usan EXACTAMENTE el vocabulario de
``forge.theory.parse_chord`` (m7, maj9, sus4, add9, dim7, bajos "/", 7sus4...)
y se verifican parseando con esa misma función antes de devolverlos.
"""
from forge import theory as T

from . import harmony_library as HL

#: Clase modal de composición (nombres de modo de forge.theory → clase de la
#: biblioteca). Dorio/frigio/menor armónica cuentan como clase MENOR.
MODO_CLASE = {"ionian": "mayor", "lydian": "mayor", "mixolydian": "mayor",
              "aeolian": "menor", "dorian": "menor", "phrygian": "menor",
              "harmonic_minor": "menor", "locrian": "menor"}

_NITIDOS = (1, 3, 6, 8, 10)          # tonics que se escriben con sostenidos
_SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

#: Presupuestos por nivel de variación.
PRESUPUESTO = {"none": {"estructura": 0, "extensiones": 0},
               "subtle": {"estructura": 0, "extensiones": 2},
               "medium": {"estructura": 2, "extensiones": 3},
               "rich": {"estructura": 3, "extensiones": 4}}
UMBRAL_HUELLA = {"none": 1.0, "subtle": 0.95, "medium": 0.6, "rich": 0.5}

#: Extensiones por (clase de acorde, familia). Tupla vacía = triada limpia.
_EXT_CANDIDATOS = {
    "maj": {"familiaridad_pop": ("6", "add9"),
            "melancolia_nostalgia": ("add9", "maj7"),
            "oscuridad_cinematografica": (),
            "dream_pop_alternative": ("add2", "maj7"),
            "soul_rnb": ("maj7", "maj9"),
            "balada_cinematica": ("maj7", "add9")},
    "min": {"familiaridad_pop": ("7",),
            "melancolia_nostalgia": ("7", "9"),
            "oscuridad_cinematografica": ("7", "9"),
            "dream_pop_alternative": ("7", "9"),
            "soul_rnb": ("7", "9"),
            "balada_cinematica": ("7", "9")},
    "dom": {"familiaridad_pop": ("9",),
            "melancolia_nostalgia": ("7",),
            "oscuridad_cinematografica": ("7", "9"),
            "dream_pop_alternative": ("7sus4",),
            "soul_rnb": ("9", "13"),
            "balada_cinematica": ("7", "9")},
}

#: Sustituciones diatónicas por familia funcional (valor de numeral → valor).
_SUSTITUCIONES = {1: 6, 6: 1, 3: 1, 4: 2, 2: 4, 5: 7, 7: 5}
#: Grados que son tríadas mayores según clase modal (índices 0-based).
_MAYORES = {"mayor": {0, 3, 4}, "menor": {0, 2, 3, 6}}
#: Sufijos neutrales que sobreviven a una sustitución sin recalcular calidad.
_SUF_NEUTRO = ("7", "9", "11", "13", "sus4", "sus2", "add9", "add2", "5",
               "7sus4")


def _pasos_de(modo):
    return T.MODES.get(modo, T.MODES["ionian"])


def _nombre_pc(pc, tonico):
    return (_SHARPS if tonico in _NITIDOS else T.FLAT_NAMES)[pc % 12]


def _parsear_grado(tok):
    rom, acc, suf, sl = HL.validar_grado(str(tok))
    return {"rom": rom, "idx": HL.ROMAN_INDEX[rom.upper()] - 1,
            "acc": {"b": -1, "#": 1}.get(acc, 0), "suf": suf, "sl": sl,
            "menor": rom.islower()}


def _raiz(g, tonico, modo):
    return (tonico + _pasos_de(modo)[g["idx"]] + g["acc"]) % 12


def _calidad_base(g, modo, entry_modo=None):
    """Calidad del grado: '' (mayor) | 'm' | 'dim' | 'aug'.

    - Clase modal COINCIDENTE (entrada menor ↔ composición menor, o mayor↔
      mayor): manda el CASO del numeral — es la intención del arquetipo, y los
      desacuerdos con la escala (p. ej. VI mayor en dórico) son intercambio
      modal deliberado. Solo se clampa a diatónico si la escala pide disminuido
      (vii°).
    - Clase RELAJADA (progresión «mayor» sobre composición menor): manda la
      ESCALA, para que la adaptación siga siendo diatónica (el oído reconoce
      el movimiento de raíces, no el caso del numeral).
    """
    coincidente = entry_modo is not None and MODO_CLASE[modo] == entry_modo
    if coincidente:
        escala = _calidad_diatonica(g, modo)
        if escala == "dim":
            return "dim"
        return "m" if g["menor"] else ""
    return _calidad_diatonica(g, modo)


def _calidad_diatonica(g, modo):
    """Tríada diatónica del grado en la escala real: '' | 'm' | 'dim' | 'aug'."""
    i = g["idx"]
    pasos = _pasos_de(modo)
    ter = (pasos[(i + 2) % 7] + (12 if (i + 2) % 7 <= i else 0) - pasos[i]) % 12
    qui = (pasos[(i + 4) % 7] + (12 if (i + 4) % 7 <= i else 0) - pasos[i]) % 12
    if ter == 4 and qui == 7:
        return ""
    if ter == 3 and qui == 7:
        return "m"
    if ter == 3 and qui == 6:
        return "dim"
    if ter == 4 and qui == 8:
        return "aug"
    return "" if ter == 4 else "m"


def _forzar_mayor(g, modo):
    """Excepciones documentadas en clase menor: V y VII mayúsculas se quedan
    mayores (dominante armónica del menor y bVII de color aeolio)."""
    return (MODO_CLASE[modo] == "menor" and g["rom"].upper() in ("V", "VII")
            and not g["menor"])


def _clase_acorde(g, modo, entry_modo=None):
    """maj | min | dom | dim | aug — para extensiones."""
    suf = g["suf"]
    base = "" if _forzar_mayor(g, modo) else _calidad_base(g, modo, entry_modo)
    if suf in ("dim", "dim7", "m7b5"):
        return "dim"
    if suf == "aug":
        return "aug"
    if suf in ("7", "9", "11", "13"):
        return "min" if base == "m" else "dom"
    return {"": "maj", "m": "min", "dim": "dim", "aug": "aug"}[base]


def _simbolo(g, tonico, modo, entry_modo=None):
    """Token de grado → símbolo parseable por forge.theory. La calidad sigue la
    regla de _calidad_base (caso del arquetipo si el modo coincide, escala si
    se relajó), con la excepción documentada V/VII mayor en menor; los sufijos
    de la entrada van encima (sus sustituye la 3ª, 7sus4 es dominante
    suspendido, dim conserva su familia)."""
    nombre = _nombre_pc(_raiz(g, tonico, modo), tonico)
    suf = g["suf"]
    base = "" if _forzar_mayor(g, modo) else _calidad_base(g, modo, entry_modo)
    if suf == "":
        return nombre + base
    if suf in ("dim", "dim7", "m7b5"):
        return nombre + suf
    if suf == "7sus4":
        return nombre + "7sus4"
    if suf in ("sus4", "sus2"):
        return nombre + suf                      # la sus sustituye la 3ª
    if suf in ("add9", "add2"):
        return nombre + (("m" + suf) if base == "m" else suf)
    if suf in ("maj7", "maj9"):
        return nombre + ("mmaj7" if base == "m" else suf)
    if base == "dim":
        return nombre + ("m7b5" if suf in ("7", "9", "11", "13") else "dim")
    if base == "aug":
        return nombre + "aug" + suf
    return nombre + (("m" + suf) if base == "m" else suf)


def _con_inversion(sym, grado_sl, tonico):
    """Añade bajo /3 /5 /7 si la nota existe (sin duplicar teoría de forge)."""
    ch, _err = T.safe_chord(sym, tonico)
    d = {"3": 3, "5": 5, "7": 7}.get(str(grado_sl))
    if d is None or (d == 3 and not ch.true_third):
        return sym
    pc = ch.tone(d)
    return sym if pc is None else "%s/%s" % (sym, _nombre_pc(pc, tonico))


def _slots_de(seccion):
    cb = float(seccion.get("chord_bars", 1) or 1)
    return max(1, int(round(float(seccion["bars"]) / max(0.25, cb)))), cb


def _menoridad(grados_tokens):
    """Caso mayoritario de los grados base (para giros de turnaround)."""
    minusculas = sum(1 for t in grados_tokens if t[0].islower())
    return minusculas * 2 >= len(grados_tokens)


def _expande(grados, n):
    """Rellena ``n`` slots: ciclo repetido, versión compacta (n < len) o ciclo
    + giro de turnaround (n % len ≠ 0). Devuelve (tokens, ajuste|None)."""
    L = len(grados)
    if n % L == 0:
        return list(grados) * (n // L), None
    if n < L:
        if n == 2:
            idx = [0, L - 1]
        else:
            idx = [0] + [1 + int(round(j / float(n - 1) * (L - 3)))
                         for j in range(1, n - 1)] + [L - 1]
        return [grados[i] for i in idx[:n]], "compacta_%d_en_%d" % (L, n)
    k, m = n // L, n % L
    out = list(grados) * k
    if _menoridad(grados):
        out.extend(["iv", "V7"][:m])
    else:
        out.extend(["IV", "V7"][:m])
    return out[:n], "giro_%d" % m


def _intervalo(raiz_a, raiz_b):
    return (raiz_b - raiz_a) % 12


def _romano(valor, menor):
    r = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}[valor]
    return r.lower() if menor else r


def adaptar(entry, tonico, modo, seccion, variacion="subtle", rng=None,
            primer_simbolo_siguiente=None):
    """Adapta ``entry`` a la sección real (tonalidad/modo/longitud).

    Devuelve (simbolos, log). ``simbolos``: lista de str (un acorde por slot)
    o dict {"chord", "bars"} para colas de aproximación a medio slot.
    """
    if variacion not in HL.NIVELES_VARIACION:
        raise ValueError("nivel de variación desconocido: %r (válidos: %s)"
                         % (variacion, ", ".join(HL.NIVELES_VARIACION)))
    import random
    rng = rng or random.Random(0)
    disp = set(entry["variaciones"])
    n_slots, cb = _slots_de(seccion)
    log = {"slots": n_slots, "chord_bars": cb, "transformaciones": [], "avisos": []}

    tokens, ajuste = _expande([str(t) for t in entry["grados"]], n_slots)
    if ajuste:
        log["transformaciones"].append({"tipo": "ajuste_estructura", "detalle": ajuste})
    gs = [_parsear_grado(t) for t in tokens]
    base_raices = [_raiz(g, tonico, modo) for g in gs]
    bud = PRESUPUESTO[variacion]
    usados = {"estructura": 0, "extensiones": 0}

    def _presupuesto(clave):
        if usados[clave] < bud[clave]:
            usados[clave] += 1
            return True
        return False

    # --- resolucion_deceptiva: SOLO sección final y solo V del último slot
    if ("resolucion_deceptiva" in disp and variacion in ("medium", "rich")
            and seccion.get("final") and gs):
        ult = gs[-1]
        menor_clase = MODO_CLASE[modo] == "menor"
        if ult["rom"].upper() == "V" and not ult["menor"] and ult["suf"] in ("", "7"):
            if _presupuesto("estructura"):
                nuevo = {"rom": "VI" if menor_clase else "vi", "idx": 5, "acc": 0,
                         "suf": "", "sl": None, "menor": not menor_clase}
                gs[-1] = nuevo
                log["transformaciones"].append(
                    {"tipo": "resolucion_deceptiva", "slot": len(gs) - 1,
                     "detalle": "V→%s" % nuevo["rom"]})

    # --- sustitucion_diatonica: un máximo, slot interno, misma función
    if ("sustitucion_diatonica" in disp and variacion in ("medium", "rich")
            and len(gs) >= 3 and rng.random() < 0.5):
        eligibles = [k for k in range(1, len(gs) - 1)
                     if (gs[k]["idx"] + 1) in _SUSTITUCIONES and not gs[k]["sl"]]
        if eligibles and _presupuesto("estructura"):
            k = rng.choice(eligibles)
            nuevo_valor = _SUSTITUCIONES[gs[k]["idx"] + 1]
            es_menor = (nuevo_valor - 1) not in _MAYORES[MODO_CLASE[modo]]
            neu = gs[k]["suf"] in _SUF_NEUTRO
            viejo = gs[k]["rom"] + gs[k]["suf"]
            gs[k] = {"rom": _romano(nuevo_valor, es_menor), "idx": nuevo_valor - 1,
                     "acc": 0, "suf": gs[k]["suf"] if neu else "", "sl": None,
                     "menor": es_menor}
            log["transformaciones"].append(
                {"tipo": "sustitucion_diatonica", "slot": k,
                 "detalle": "%s→%s" % (viejo, gs[k]["rom"] + gs[k]["suf"])})

    # --- intercambio_modal: un máximo; préstamo fijo (iv7 en mayor, IVmaj7 en menor)
    if "intercambio_modal" in disp and variacion in ("medium", "rich") and len(gs) >= 3:
        if rng.random() < (0.3 if variacion == "medium" else 0.6):
            mayor_clase = MODO_CLASE[modo] == "mayor"
            if mayor_clase:
                elig = [k for k in range(1, len(gs) - 1) if gs[k]["idx"] == 3
                        and not gs[k]["menor"] and gs[k]["suf"] in ("", "7")]
                nuevo = {"rom": "iv", "idx": 3, "acc": 0, "suf": "7", "sl": None,
                         "menor": True}
            else:
                elig = [k for k in range(1, len(gs) - 1) if gs[k]["idx"] == 3
                        and gs[k]["menor"] and gs[k]["suf"] in ("", "7")]
                nuevo = {"rom": "IV", "idx": 3, "acc": 0, "suf": "maj7", "sl": None,
                         "menor": False}
            if elig and _presupuesto("estructura"):
                k = elig[-1]
                viejo = gs[k]["rom"] + gs[k]["suf"]
                gs[k] = nuevo
                log["transformaciones"].append(
                    {"tipo": "intercambio_modal", "slot": k,
                     "detalle": "%s→%s" % (viejo, nuevo["rom"] + nuevo["suf"])})

    # --- sus_flavor: solo dominantes funcionales, un máximo (nivel color)
    if "sus_flavor" in disp and variacion in ("medium", "rich"):
        elig = [k for k in range(len(gs)) if gs[k]["rom"].upper() == "V"
                and not gs[k]["menor"] and gs[k]["suf"] in ("", "7")]
        if elig and rng.random() < (0.5 if variacion == "medium" else 0.7):
            k = elig[-1]
            viejo = gs[k]["suf"]
            gs[k] = dict(gs[k], suf="sus4" if viejo == "" else "7sus4")
            log["transformaciones"].append(
                {"tipo": "sus_flavor", "slot": k,
                 "detalle": "V%s→V%s" % (viejo, gs[k]["suf"])})

    # --- inversion_paso: un máximo, bajo escalerado hacia el acorde siguiente
    if ("inversion_paso" in disp and variacion in ("medium", "rich")
            and len(gs) >= 3):
        cand = [k for k in range(len(gs) - 1)
                if _intervalo(base_raices[k], base_raices[k + 1]) in (1, 2, 11, 10)
                and gs[k]["suf"] in ("", "7", "9", "sus4") and not gs[k]["sl"]]
        if cand and rng.random() < 0.6 and _presupuesto("estructura"):
            k = rng.choice(cand)
            gs[k]["sl"] = "3"
            log["transformaciones"].append(
                {"tipo": "inversion_paso", "slot": k,
                 "detalle": "bajo en 3ª (paso hacia %s)"
                            % _nombre_pc(base_raices[k + 1], tonico)})

    # --- extensiones (color según familia; nunca cambian la función ni la raíz)
    if "extensiones" in disp and bud["extensiones"] > 0:
        p = {"subtle": 0.35, "medium": 0.5, "rich": 0.6}.get(variacion, 0.0)
        for k, g in enumerate(gs):
            if usados["extensiones"] >= bud["extensiones"]:
                break
            if k == 0 and variacion == "subtle":
                continue
            if g["suf"] != "" or g["sl"]:
                continue
            cands = _EXT_CANDIDATOS.get(_clase_acorde(g, modo, entry["modo"]), {}).get(entry["familia"], ())
            if cands and rng.random() < p:
                if rng.random() < (p * 0.5 if k == 0 else 1.0):
                    g["suf"] = rng.choice(list(cands))
                    usados["extensiones"] += 1
                    log["transformaciones"].append(
                        {"tipo": "extension", "slot": k,
                         "detalle": "%s%s" % (g["rom"], g["suf"])})

    # --- símbolos finales + colas de aproximación (transición entre secciones)
    simbolos = []
    for g in gs:
        s = _simbolo(g, tonico, modo, entry["modo"])
        if g["sl"]:
            s = _con_inversion(s, g["sl"], tonico)
        simbolos.append(s)

    if variacion == "rich" and cb >= 1.0 and primer_simbolo_siguiente is not None:
        sabores = [s for s in ("dominante_secundaria", "acorde_paso") if s in disp]
        if sabores and rng.random() < 0.5:
            sabor = sabores[0] if len(sabores) == 1 else rng.choice(sabores)
            ch_next, _e = T.safe_chord(primer_simbolo_siguiente, tonico)
            r_next, r_ult = ch_next.root, base_raices[-1]
            if r_next != r_ult:
                if sabor == "dominante_secundaria":
                    sym = _nombre_pc((r_next + 7) % 12, tonico) + "7"
                    detalle = "V7 de %s" % primer_simbolo_siguiente
                else:
                    pasos = _pasos_de(modo)
                    abajo = (r_next - 1) % 12 if (r_next - 1) % 12 in pasos \
                        else (r_next + 1) % 12
                    idx = pasos.index(abajo)
                    es_men = idx not in _MAYORES[MODO_CLASE[modo]]
                    sym = _nombre_pc(abajo, tonico) + ("m" if es_men and idx else "")
                    detalle = "paso diatónico hacia %s" % primer_simbolo_siguiente
                ch, err = T.safe_chord(sym, tonico)
                if err is None:
                    mitad = max(0.5, cb / 2.0)
                    ultimo = simbolos[-1]
                    simbolos[-1] = {"chord": ultimo if isinstance(ultimo, str)
                                    else ultimo["chord"], "bars": mitad}
                    simbolos.append({"chord": sym, "bars": mitad})
                    log["transformaciones"].append(
                        {"tipo": "cola_aproximacion", "sabor": sabor,
                         "detalle": detalle})

    # --- validación de símbolos + huella del arquetipo
    for s in simbolos:
        cs = s["chord"] if isinstance(s, dict) else s
        _ch, err = T.safe_chord(cs, tonico)
        if err is not None:
            raise ValueError("símbolo adaptado no parseable: %r (%s)" % (cs, entry["id"]))
    huella = _huella(base_raices, simbolos, tonico)
    log["huella_arquetipo"] = round(huella, 3)
    if huella < UMBRAL_HUELLA[variacion]:
        log["avisos"].append("huella del arquetipo %.2f bajo el umbral %.2f"
                             % (huella, UMBRAL_HUELLA[variacion]))
    return simbolos, log


def _huella(base_raices, simbolos, tonico):
    """Fracción de intervalos de raíz del arquetipo que sobreviven (0..1)."""
    finals = []
    for s in simbolos:
        cs = s["chord"] if isinstance(s, dict) else s
        ch, _e = T.safe_chord(cs, tonico)
        finals.append(ch.root)
    n = min(len(base_raices), len(finals))
    if n < 2:
        return 1.0
    ok = total = 0
    for k in range(n - 1):
        total += 1
        if _intervalo(base_raices[k], base_raices[k + 1]) == \
                _intervalo(finals[k], finals[k + 1]):
            ok += 1
    return ok / float(total) if total else 1.0


def primer_raiz(simbolos, tonico=0):
    """Raíz (pc) del primer símbolo (para transiciones); None si vacío."""
    if not simbolos:
        return None
    s = simbolos[0]
    ch, _e = T.safe_chord(s["chord"] if isinstance(s, dict) else s, tonico)
    return ch.root
