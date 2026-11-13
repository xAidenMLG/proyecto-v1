"""Validador de entrada del contrato ``dark-director/1`` (E1xx/E2xx/E3xx + W4xx).

Instrucción 09 — Fase 1 (compilador mínimo): este módulo ES el validador
E1xx exigido por la instrucción. Fuente de verdad: rev. 3 (§2.10, §3.x),
rev. 3.1 (E114, §2.5.1) y rev. 3.2 (definición cerrada de bandas de §2.6.5).

Diferencias con el QA documental de rev. 3 (``scripts/validar_respuesta_03.py``):
  - E113/E105-key usan la gramática REAL del motor (``theory.parse_chord`` /
    ``theory.parse_key`` vía ``forge_link``), no una gramática documental.
  - Implementa E203/E204/E114 (el QA no los necesitaba: ningún ejemplo los
    dispara) y el conteo completo de W407/W413 (el QA cortaba en el primero).
  - Bandas por ``contract.density_band`` (rev. 3.2), no por la espejo antigua.
  - W403/W401 requieren la receta N1 real de la identidad: sin receta, la
    comprobación se registra en ``no_verificados`` (honestidad), nunca se
    inventa un rango de BPM ni una tabla D_receta.
  - ``x_`` a secas NO es extensión (``contract.es_campo_extension``).

Semántica: E1xx/E2xx bloquean siempre; E3xx bloquea solo con ``qa.strict``
(el compilador decide); W4xx nunca bloquea ni cambia valores.
"""

import re

from . import accesibilidad, contract, inicializacion, recetas
from . import identities as _identidades

TOL = 1e-6

# ---------------------------------------------------------------- vocabulario
# Gramática de PARSEABILIDAD: la real de ``theory.parse_chord`` (E113).
# Vocabulario de TIER para W414 (§2.4): listas contractuales por language.
_POP = {"", "6", "m", "add9", "sus2", "sus4", "sus", "7sus4", "maj7", "maj9", "m7", "m9"}
_HYBRID = _POP | {"7", "9", "11", "13", "maj11", "maj13", "m11", "m13",
                  "add11", "add13", "5", "7#11", "m7b5"}

_ROOT_RE = re.compile(r"^([A-G][#b]?)(.*)$", re.S)

_LANG_TIERS = {"pop_dream_pop": ("pop",), "hybrid": ("pop", "hybrid"),
               "experimental": ("pop", "hybrid", "experimental")}


def _quality_tier(sym):
    """'pop' | 'hybrid' | 'experimental' para un símbolo YA parseable por el
    motor. Todo lo que parsea y no es pop/hybrid es experimental (§2.4)."""
    m = _ROOT_RE.match(str(sym).strip())
    if not m:
        return "experimental"
    rest = m.group(2)
    bass_ok = True
    if "/" in rest:
        rest, bass = rest.split("/", 1)
        bass_ok = bool(re.fullmatch(r"[A-G][#b]?", bass or ""))
    if not bass_ok:
        return "experimental"
    if rest in _POP:
        return "pop"
    if rest in _HYBRID:
        return "hybrid"
    return "experimental"


def parse_pitch(p):
    """MIDI 0–127 o nombre 'C4'; None si no parsea (E111)."""
    if isinstance(p, bool):
        return None
    if isinstance(p, int) and 0 <= p <= 127:
        return p
    if isinstance(p, str):
        m = re.match(r"^([A-G])(#|b)?(-?\d+)$", p.strip())
        if not m:
            return None
        base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[m.group(1)]
        acc = 1 if m.group(2) == "#" else -1 if m.group(2) == "b" else 0
        val = (int(m.group(3)) + 1) * 12 + base + acc
        return val if 0 <= val <= 127 else None
    return None


# ---------------------------------------------------------------- campos conocidos
KNOWN_ROOT = {"schema", "meta", "direction", "global", "harmony", "instruments",
              "structure", "development", "ending", "qa"}
KNOWN_META = {"title", "notes"}
KNOWN_DIRECTION = {"identity", "accessibility"}
KNOWN_GLOBAL = {"bpm", "seed", "humanize", "velocity_cap"}
KNOWN_HARMONY = {"key", "language", "resolution", "harmonic_rhythm_bars", "progressions"}
KNOWN_INST = {"enabled", "register", "density", "mix", "type"}
KNOWN_MIX = {"volume", "pan", "reverb", "chorus", "brightness"}
KNOWN_SECTION = {"id", "type", "bars", "energy", "tension", "density", "focus", "active",
                 "drums", "chords", "chord_bars", "resolution", "final", "loop_bars"}
KNOWN_DEV = {"melody", "motifs", "responses", "improvisation"}
KNOWN_MELODY = {"phrases"}
KNOWN_NOTE = {"bar", "beat", "pitch", "dur", "vel"}
KNOWN_MOTIF = {"from_section", "sections", "loop_bars", "transpose_st"}
KNOWN_RESPONSE = {"responds_to", "prob", "max_per_bar"}
KNOWN_IMPROV = {"section", "instrument"}
KNOWN_ENDING = {"fade_out", "tape_stop"}
KNOWN_ENDING_OBJ = {"enabled", "bars", "exponent", "semitones"}
KNOWN_QA = {"strict", "guardrails"}

LEAD = "sax_tenor"
VIBES = "vibraphone"
BASS = "bass"
SPLIT_STRATS = {"tonal", "deceptive"}
BASS_GESTURE = {"tonal", "chromatic"}
LANG_DEFAULT_RES = {"pop_dream_pop": "tonal", "hybrid": "modal", "experimental": "chromatic"}
ATYPICAL_PAIRS = {("doom_dark_jazz", "commercial"),
                  ("commercial", "experimental"),
                  ("experimental", "pop_dream_pop"),
                  ("doom_dark_jazz", "pop_dream_pop")}


def _es_x(k):
    return contract.es_campo_extension(k)


def _num_in(v, lo, hi):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and lo - TOL <= v <= hi + TOL


def _simbolos(lista):
    out = []
    for ch in (lista or []):
        if isinstance(ch, dict):
            out.append(ch.get("chord"))
        elif isinstance(ch, str):
            s = ch.strip()
            if ":" in s:
                cabeza, cola = s.rsplit(":", 1)
                try:
                    float(cola)
                    out.append(cabeza)
                    continue
                except ValueError:
                    pass
            out.append(s)
    return out


# ---------------------------------------------------------------- validador
def validar(ex):
    """Valida un documento ``dark-director/1`` (dict ya parseado).

    Devuelve un dict:
      errores        : [(codigo, mensaje)]  — E1xx/E2xx (bloquean siempre)
      e3xx           : [(codigo, mensaje)]  — capacidad no soportada (E301–E303)
      avisos         : [(codigo, mensaje)]  — W4xx (nunca bloquea)
      no_verificados : [mensaje]            — checks que requieren receta N1 no registrada
    """
    E, W, X3, NV = [], [], [], []

    def err(code, msg): E.append((code, msg))
    def warn(code, msg): W.append((code, msg))
    def e3(code, msg): X3.append((code, msg))

    if not isinstance(ex, dict):
        err("E101", "raíz no-objeto (JSON malformado se detecta al parsear)")
        return _salir(E, W, X3, NV)
    if ex.get("schema") != contract.CONTRACT_ID:
        err("E102", f"schema ausente o != '{contract.CONTRACT_ID}'")
    for k in ex:
        if k not in KNOWN_ROOT and not _es_x(k):
            err("E109", f"campo desconocido '{k}' en la raíz")

    g = ex.get("global") or {}
    if not isinstance(g, dict):
        err("E104", "global debe ser objeto")
    else:
        for k in g:
            if k not in KNOWN_GLOBAL and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en global")
        if "bpm" in g and not _num_in(g["bpm"], 20, 300):
            err("E105", f"bpm fuera de 20–300: {g['bpm']!r}")
        if "seed" in g and (not isinstance(g["seed"], int) or g["seed"] < 0):
            err("E105", f"seed debe ser entero ≥ 0: {g['seed']!r}")
        if "humanize" in g and not _num_in(g["humanize"], 0.0, 2.0):
            err("E105", f"humanize fuera de 0–2: {g['humanize']!r}")
        if "velocity_cap" in g and (not isinstance(g["velocity_cap"], int)
                                    or not 40 <= g["velocity_cap"] <= 127):
            err("E105", f"velocity_cap fuera de 40–127: {g['velocity_cap']!r}")

    direction = ex.get("direction")
    identity = access = None
    if not isinstance(direction, dict):
        if "direction" in ex:
            err("E104", "direction debe ser objeto")
        err("E103", "direction ausente (identity/accessibility requeridos)")
    else:
        for k in direction:
            if k not in KNOWN_DIRECTION and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en direction")
        if "identity" not in direction:
            err("E103", "direction.identity requerido")
        elif direction["identity"] not in contract.IDENTITIES:
            err("E105", f"identity fuera del enum: {direction['identity']!r}")
        else:
            identity = direction["identity"]
        if "accessibility" not in direction:
            err("E103", "direction.accessibility requerido")
        elif direction["accessibility"] not in contract.ACCESSIBILITIES:
            err("E105", f"accessibility fuera del enum: {direction['accessibility']!r}")
        else:
            access = direction["accessibility"]

    meta = ex.get("meta")
    if meta is not None and not isinstance(meta, dict):
        err("E104", "meta debe ser objeto")
    elif isinstance(meta, dict):
        for k in meta:
            if k not in KNOWN_META and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en meta")

    # harmony -------------------------------------------------------------
    h = ex.get("harmony") or {}
    language = None
    if not isinstance(h, dict):
        if "harmony" in ex:
            err("E104", "harmony debe ser objeto")
        err("E103", "harmony ausente (key/language requeridos)")
        h = {}
    else:
        for k in h:
            if k not in KNOWN_HARMONY and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en harmony")
        if "language" not in h:
            err("E103", "harmony.language requerido")
        elif h["language"] not in contract.LANGUAGES:
            err("E105", f"language fuera del enum: {h['language']!r}")
        else:
            language = h["language"]
        if "key" not in h:
            err("E103", "harmony.key requerido")
        elif not isinstance(h["key"], str) or not _parsea_key(h["key"]):
            err("E105", f"harmony.key no parseable por theory.parse_key: {h.get('key')!r}")
        if "resolution" in h and h["resolution"] not in contract.RESOLUTIONS:
            err("E105", f"resolution fuera del enum: {h['resolution']!r}")
        if "harmonic_rhythm_bars" in h and (not isinstance(h["harmonic_rhythm_bars"], int)
                                            or not 1 <= h["harmonic_rhythm_bars"] <= 8):
            err("E105", f"harmonic_rhythm_bars fuera de 1–8: {h['harmonic_rhythm_bars']!r}")

    # instruments ---------------------------------------------------------
    insts = ex.get("instruments") or {}
    if not isinstance(insts, dict):
        if "instruments" in ex:
            err("E104", "instruments debe ser objeto")
        insts = {}
    for iid, conf in insts.items():
        if iid not in contract.INSTRUMENT_IDS:
            err("E110", f"id de instrumento fuera del catálogo de 8: {iid!r}")
            continue
        if not isinstance(conf, dict):
            err("E104", f"instruments.{iid} debe ser objeto")
            continue
        for k in conf:
            if k not in KNOWN_INST and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en instruments.{iid}")
        if "enabled" in conf and not isinstance(conf["enabled"], bool):
            err("E104", f"instruments.{iid}.enabled debe ser bool")
        if "register" in conf:
            r = conf["register"]
            if (not isinstance(r, list) or len(r) != 2
                    or not all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 127 for x in r)
                    or r[0] >= r[1]):
                err("E105", f"register de {iid} debe ser [low, high] con 0–127 y low < high")
        if "density" in conf and not _num_in(conf["density"], 0.0, 1.0):
            err("E105", f"density de {iid} fuera de 0–1: {conf['density']!r}")
        if "type" in conf and (iid != BASS or conf["type"] not in ("finger", "upright")):
            err("E105", f"type de {iid} inválido (solo bass: finger|upright)")
        mix = conf.get("mix")
        if mix is not None:
            if not isinstance(mix, dict):
                err("E104", f"mix de {iid} debe ser objeto")
            else:
                for k in mix:
                    if k not in KNOWN_MIX and not _es_x(k):
                        err("E109", f"campo desconocido '{k}' en mix de {iid}")
                for k, v in mix.items():
                    if k in KNOWN_MIX and (not isinstance(v, int) or isinstance(v, bool)
                                           or not 0 <= v <= 127):
                        err("E105", f"mix.{k} de {iid} fuera de 0–127: {v!r}")

    # structure -----------------------------------------------------------
    secs = ex.get("structure")
    sec_by_id, ids = {}, []
    estructura_ok = False
    if not isinstance(secs, list):
        if "structure" in ex:
            err("E104", "structure debe ser lista")
        err("E103", "structure requerida (≥ 2 secciones)")
        secs = []
    elif len(secs) < 2:
        err("E106", f"structure con menos de 2 secciones ({len(secs)})")
    else:
        estructura_ok = True
    for s in secs:
        if not isinstance(s, dict):
            err("E104", "cada sección debe ser objeto")
            continue
        sid, stype = s.get("id"), s.get("type")
        for k in s:
            if k not in KNOWN_SECTION and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en sección {sid!r}")
        if not isinstance(sid, str) or not sid:
            err("E103", "sección sin id")
            continue
        if stype not in contract.SECTION_TYPES:
            err("E105", f"type de sección fuera del catálogo de 7: {stype!r} ({sid})")
        if not isinstance(s.get("bars"), int) or isinstance(s.get("bars"), bool) or s.get("bars", 0) < 1:
            err("E105", f"bars de {sid} debe ser entero ≥ 1: {s.get('bars')!r}")
        if sid in sec_by_id:
            err("E106", f"id de sección duplicado: {sid!r}")
        sec_by_id[sid] = s
        ids.append(sid)
        for k in ("energy", "tension", "density"):
            if k in s and not _num_in(s[k], 0.0, 1.0):
                err("E105", f"{k} de {sid} fuera de 0–1: {s[k]!r}")
        if "drums" in s and s["drums"] not in contract.DRUMS_LADDER:
            err("E105", f"drums de {sid} fuera de la escalera §2.6.3: {s['drums']!r}")
        if "resolution" in s and s["resolution"] not in contract.RESOLUTIONS:
            err("E105", f"resolution de {sid} fuera del enum: {s['resolution']!r}")
        if "chord_bars" in s and (not isinstance(s["chord_bars"], int) or isinstance(s["chord_bars"], bool)
                                  or not 1 <= s["chord_bars"] <= 8):
            err("E105", f"chord_bars de {sid} fuera de 1–8: {s['chord_bars']!r}")
        if "loop_bars" in s and (not isinstance(s["loop_bars"], int) or isinstance(s["loop_bars"], bool)
                                 or not 1 <= s["loop_bars"] <= 32):
            err("E105", f"loop_bars de {sid} fuera de 1–32: {s['loop_bars']!r}")
        if "final" in s and not isinstance(s["final"], bool):
            err("E104", f"final de {sid} debe ser bool")
        focus = s.get("focus")
        if focus is not None:
            if not isinstance(focus, list):
                err("E104", f"focus de {sid} debe ser lista")
            else:
                if len(focus) > 3:
                    err("E105", f"focus de {sid} con más de 3 instrumentos")
                for ref in focus:
                    if ref not in contract.INSTRUMENT_IDS:
                        err("E110", f"focus de {sid} referencia id fuera del catálogo: {ref!r}")
        active = s.get("active")
        if active is not None:
            if not isinstance(active, list):
                err("E104", f"active de {sid} debe ser lista")
            else:
                for ref in active:
                    if ref not in contract.INSTRUMENT_IDS:
                        err("E110", f"active de {sid} referencia id fuera del catálogo: {ref!r}")
        for sym in _simbolos(s.get("chords")):
            if not _parsea_acorde(sym):
                err("E113", f"símbolo de acorde no parseable por theory.parse_chord: {sym!r} ({sid})")

    # progressions --------------------------------------------------------
    for key, prog in (h.get("progressions") or {}).items():
        if key not in sec_by_id and key not in contract.SECTION_TYPES:
            err("E107", f"clave de progressions no es id ni type de sección: {key!r}")
        if not isinstance(prog, list) or not prog:
            err("E105", f"progression '{key}' vacía o no-lista")
            continue
        for sym in _simbolos(prog):
            if not _parsea_acorde(sym):
                err("E113", f"símbolo de acorde no parseable por theory.parse_chord: {sym!r} (progressions.{key})")

    # development ---------------------------------------------------------
    dev = ex.get("development") or {}
    if not isinstance(dev, dict):
        if "development" in ex:
            err("E104", "development debe ser objeto")
        dev = {}
    for k in dev:
        if k not in KNOWN_DEV and not _es_x(k):
            err("E109", f"campo desconocido '{k}' en development")
    melody = dev.get("melody") or {}
    if not isinstance(melody, dict):
        err("E104", "development.melody debe ser objeto")
        melody = {}
    for k in melody:
        if k not in KNOWN_MELODY and not _es_x(k):
            err("E109", f"campo desconocido '{k}' en development.melody")
    phrases = melody.get("phrases") or {}
    if not isinstance(phrases, dict):
        err("E104", "development.melody.phrases debe ser objeto")
        phrases = {}
    for sid, notas in phrases.items():
        if sid not in sec_by_id:
            err("E107", f"phrases de sección inexistente: {sid!r}")
            continue
        bars = sec_by_id[sid].get("bars", 0)
        if not isinstance(notas, list):
            err("E104", f"phrases de {sid} debe ser lista de notas")
            continue
        for n in notas:
            if not isinstance(n, dict):
                err("E104", f"nota de {sid} debe ser objeto")
                continue
            for k in n:
                if k not in KNOWN_NOTE and not _es_x(k):
                    err("E109", f"campo desconocido '{k}' en nota de {sid}")
            bar, beat, dur = n.get("bar"), n.get("beat", 0.0), n.get("dur", 1.0)
            if not isinstance(bar, int) or isinstance(bar, bool) or not 0 <= bar <= bars - 1:
                err("E111", f"bar de nota fuera de 0..{bars - 1} en {sid}: {bar!r}")
            elif not _num_in(beat, 0.0, 4.0) or beat >= 4.0 - TOL:
                err("E111", f"beat de nota fuera de [0, 4) en {sid}: {beat!r}")
            elif bar * 4 + beat + dur > bars * 4 + TOL:
                err("E111", f"la nota sobrepasa el final de {sid} (bar·4+beat+dur > bars·4)")
            if parse_pitch(n.get("pitch")) is None:
                err("E111", f"pitch de nota no parsea en {sid}: {n.get('pitch')!r}")
            if (not isinstance(dur, (int, float)) or isinstance(dur, bool)
                    or dur <= 0 or dur > 16 + TOL):
                err("E111", f"dur de nota fuera de (0, 16] en {sid}: {dur!r}")
            if "vel" in n and (not isinstance(n["vel"], int) or isinstance(n["vel"], bool)
                               or not 1 <= n["vel"] <= 127):
                err("E111", f"vel de nota fuera de 1–127 en {sid}: {n['vel']!r}")

    motifs = dev.get("motifs") or {}
    if not isinstance(motifs, dict):
        err("E104", "development.motifs debe ser objeto")
        motifs = {}
    for nombre, mo in motifs.items():
        if not isinstance(mo, dict):
            err("E104", f"motif {nombre} debe ser objeto")
            continue
        for k in mo:
            if k not in KNOWN_MOTIF and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en motif {nombre}")
        src = mo.get("from_section")
        if src not in sec_by_id:
            err("E107", f"motif {nombre}: from_section inexistente: {src!r}")
        elif not phrases.get(src):
            err("E108", f"motif {nombre}: fuente '{src}' sin frases (v1 sin phrasegen)")
        dsts = mo.get("sections")
        if dsts is not None:
            if not isinstance(dsts, list) or not dsts:
                err("E105", f"motif {nombre}: sections vacía o no-lista")
            else:
                for d in dsts:
                    if d not in sec_by_id:
                        err("E107", f"motif {nombre}: destino inexistente: {d!r}")
        if "loop_bars" in mo and (not isinstance(mo["loop_bars"], int) or isinstance(mo["loop_bars"], bool)
                                  or not 1 <= mo["loop_bars"] <= 32):
            err("E105", f"motif {nombre}: loop_bars fuera de 1–32: {mo['loop_bars']!r}")
        if "transpose_st" in mo and (not isinstance(mo["transpose_st"], int)
                                     or isinstance(mo["transpose_st"], bool)
                                     or abs(mo["transpose_st"]) > 24):
            err("E105", f"motif {nombre}: transpose_st fuera de ±24: {mo['transpose_st']!r}")

    for iid, resp in (dev.get("responses") or {}).items():
        if iid not in contract.INSTRUMENT_IDS:
            err("E110", f"responses sobre id fuera del catálogo: {iid!r}")
            continue
        if iid != VIBES:
            e3("E303", f"responses declarado sobre '{iid}': sin mecanismo replies fuera de mallet")
        if not isinstance(resp, dict):
            err("E104", f"responses.{iid} debe ser objeto")
            continue
        for k in resp:
            if k not in KNOWN_RESPONSE and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en responses.{iid}")
        rt = resp.get("responds_to", LEAD)
        if rt not in contract.INSTRUMENT_IDS:
            err("E110", f"responds_to fuera del catálogo: {rt!r}")
        elif rt != LEAD:
            e3("E302", f"responses.{iid}.responds_to apunta a '{rt}', que no es el lead")
        if "prob" in resp and not _num_in(resp["prob"], 0.0, 1.0):
            err("E105", f"responses.{iid}.prob fuera de 0–1: {resp['prob']!r}")
        if "max_per_bar" in resp and (not isinstance(resp["max_per_bar"], int)
                                      or isinstance(resp["max_per_bar"], bool)
                                      or not 1 <= resp["max_per_bar"] <= 4):
            err("E105", f"responses.{iid}.max_per_bar fuera de 1–4: {resp['max_per_bar']!r}")

    improv = dev.get("improvisation") or []
    if not isinstance(improv, list):
        err("E104", "development.improvisation debe ser lista")
        improv = []
    for imp in improv:
        if not isinstance(imp, dict):
            err("E104", "cada entrada de improvisation debe ser objeto")
            continue
        for k in imp:
            if k not in KNOWN_IMPROV and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en improvisation")
        sec_imp = imp.get("section")
        if sec_imp not in sec_by_id:
            err("E107", f"improvisation.section inexistente: {sec_imp!r}")
        elif imp.get("instrument") not in (None, LEAD):
            e3("E301", f"improvisación en '{imp.get('instrument')}': el generativo solo existe en el lead (sax_tenor)")

    # ending / qa ---------------------------------------------------------
    ending = ex.get("ending") or {}
    if not isinstance(ending, dict):
        if "ending" in ex:
            err("E104", "ending debe ser objeto")
        ending = {}
    for k in ending:
        if k not in KNOWN_ENDING and not _es_x(k):
            err("E109", f"campo desconocido '{k}' en ending")
    ultima_bars = secs[-1].get("bars", 0) if isinstance(secs, list) and secs and isinstance(secs[-1], dict) else 0
    for kind in ("fade_out", "tape_stop"):
        v = ending.get(kind)
        if v is True:
            v = {"enabled": True}
        if v is None or v is False:
            continue
        if not isinstance(v, dict):
            err("E104", f"ending.{kind} debe ser objeto o true/false")
            continue
        for k in v:
            if k not in KNOWN_ENDING_OBJ and not _es_x(k):
                err("E109", f"campo desconocido '{k}' en ending.{kind}")
        bars = v.get("bars", 4 if kind == "fade_out" else 2)
        if not isinstance(bars, int) or isinstance(bars, bool) or bars < 1 or bars > ultima_bars:
            err("E112", f"ending.{kind}.bars inválido o mayor que la última sección: {bars!r}")
        if "exponent" in v and not _num_in(v["exponent"], 1.0, 4.0):
            err("E105", f"ending.{kind}.exponent fuera de 1.0–4.0: {v['exponent']!r}")
        if kind == "tape_stop" and "semitones" in v and (not isinstance(v["semitones"], int)
                                                         or isinstance(v["semitones"], bool)
                                                         or not 1 <= v["semitones"] <= 12):
            err("E105", f"ending.tape_stop.semitones fuera de 1–12: {v['semitones']!r}")
        if "enabled" in v and not isinstance(v["enabled"], bool):
            err("E104", f"ending.{kind}.enabled debe ser bool")

    qa = ex.get("qa") or {}
    if not isinstance(qa, dict):
        if "qa" in ex:
            err("E104", "qa debe ser objeto")
        qa = {}
    for k in qa:
        if k not in KNOWN_QA and not _es_x(k):
            err("E109", f"campo desconocido '{k}' en qa")
    if "strict" in qa and not isinstance(qa["strict"], bool):
        err("E104", "qa.strict debe ser bool")
    guardrails_decl = qa.get("guardrails") or {}
    if not isinstance(guardrails_decl, dict):
        err("E104", "qa.guardrails debe ser objeto")
        guardrails_decl = {}
    for nombre in guardrails_decl:
        if nombre not in accesibilidad.GUARDRAILS_SIEMPRE_ON + ("motif_repeat", "lead_coverage"):
            err("E109", f"guardrail desconocido (solo los 8 reales): {nombre!r}")

    # E114 — inicialización insegura de enabled=true fuera del set base (rev. 3.1 §2.5.1)
    # Fase 2: cualquier identidad CON receta registrada usa su receta real;
    # sin receta, cae al supuesto provisional §5.0.1 (dato de contrato).
    receta = (getattr(_identidades, identity) if identity in _identidades.CON_RECETA else None)
    if identity is not None:
        if receta is not None:
            base = tuple(receta.SET_BASE)
        else:
            base = contract.BASE_SETS_SUPUESTO_PROVISIONAL[identity]  # dato de contrato §5.0.1
        for iid, conf in insts.items():
            if iid not in contract.INSTRUMENT_IDS or not isinstance(conf, dict):
                continue
            if conf.get("enabled") is not True:
                continue
            if iid in base:
                continue  # ok-base: sin efecto adicional
            existe_lead = (LEAD in base or (insts.get(LEAD) or {}).get("enabled") is True)
            estado, _detalle = inicializacion.estado_inicializacion(
                iid, en_base=False, existe_lead=existe_lead, receta_da_datos=receta is not None)
            if estado == "E114":
                err("E114", _detalle)

    # E203 / E204 — contradicciones explícitas (rev. 3 §2.10)
    def suena(iid, sec):
        if iid not in contract.INSTRUMENT_IDS:
            return False
        if (insts.get(iid) or {}).get("enabled") is False:
            return False
        existe = iid in base or (insts.get(iid) or {}).get("enabled") is True
        act = sec.get("active")
        return existe and (act is None or iid in act)

    if identity is not None:
        for imp in improv:
            sec_imp = sec_by_id.get(imp.get("section"))
            iid = imp.get("instrument", LEAD)
            if not isinstance(sec_imp, dict) or iid not in contract.INSTRUMENT_IDS:
                continue
            act = sec_imp.get("active")
            if act is not None and iid not in act:
                err("E203", f"improvisación de '{iid}' en '{sec_imp.get('id')}' con active que lo excluye")
            if (insts.get(iid) or {}).get("enabled") is False:
                err("E204", f"improvisación de '{iid}' con la pista deshabilitada globalmente")
        escrito = set(phrases) | {d for mo in motifs.values() if isinstance(mo, dict)
                                  for d in (mo.get("sections") or [])}
        for sid in escrito:
            sec = sec_by_id.get(sid)
            if isinstance(sec, dict) and not suena(LEAD, sec):
                err("E204", f"material escrito (frases/motif) en '{sid}' donde el lead no suena")
        if VIBES in (dev.get("responses") or {}) and (insts.get(VIBES) or {}).get("enabled") is False:
            err("E204", "responses.vibraphone con la pista del vibráfono deshabilitada")

    # ------------------------------------------------------------------ W4xx
    if identity is None or access is None or language is None or not estructura_ok or not sec_by_id:
        # sin contexto completo no se recomputan avisos (honestidad; los errores
        # estructurales ya bloquean la compilación)
        return _salir(E, W, X3, NV)

    guardrails = accesibilidad.guardrails_default(access)
    guardrails.update({k: v for k, v in guardrails_decl.items() if isinstance(v, bool)})

    # W411
    pares = {(identity, access), (access, language), (identity, language)}
    if pares & ATYPICAL_PAIRS:
        warn("W411", f"combinación identidad×accessibility×language poco convencional (9/27): {identity}/{access}/{language}")
    # W401 — solo con receta real (sin receta: no_verificado, sin rangos inventados)
    bpm = (ex.get("global") or {}).get("bpm")
    if receta is not None and bpm is not None:
        lo, hi = receta.BPM_RANGO_TIPICO
        if not lo <= bpm <= hi:
            warn("W401", f"bpm {bpm} fuera del rango típico de {identity} [{lo}, {hi}] (se compila igual)")
    if receta is None and bpm is not None:
        NV.append(f"W401 no verificable sin receta N1 de '{identity}' (bpm {bpm})")
    # W402 — ritmo armónico menor que el default de receta de la identidad
    # (generalizado en Fase 2: antes solo doom_dark_jazz==1; dark_triphop con
    # default 1 no puede dispararlo — 1 < 1 es falso — y doom_triphop/doom_dark_jazz
    # tienen default 2 → 1:1 avisa, como documentaba RESPUESTA 09 T5).
    if receta is not None:
        hr_decl = h.get("harmonic_rhythm_bars")
        if hr_decl is not None and hr_decl < receta.HARMONIC_RHYTHM_BARS:
            warn("W402", f"ritmo armónico {hr_decl} menor que el default de receta "
                         f"de {identity} ({receta.HARMONIC_RHYTHM_BARS} compases); "
                         "peso armónico reducido")
    # W404
    if access == "commercial":
        hooks = any(s.get("type") == "chorus" and (s.get("id") in escrito or "loop_bars" in s)
                    for s in secs if isinstance(s, dict))
        if not hooks:
            warn("W404", "commercial sin material de hook en ningún chorus (ni phrases, ni motif, ni loop_bars)")
    # W405
    cap = (ex.get("global") or {}).get("velocity_cap")
    if cap is not None and cap > 110 and identity.startswith("doom"):
        warn("W405", f"velocity_cap {cap} > 110 en identidad doom")
    # W408 (§2.11: declarado vs derivado)
    mr_efectivo = guardrails["motif_repeat"]
    mr_declarado = "motif_repeat" in guardrails_decl
    if mr_efectivo and any(isinstance(mo, dict) and mo.get("loop_bars", 8) != 8 for mo in motifs.values()):
        causa = "declarado ON por el compositor (falsos positivos posibles)" if mr_declarado \
            else "derivado del perfil de accesibilidad → el compilador emite motif_repeat OFF"
        warn("W408", f"motif_repeat con motifs de loop_bars ≠ 8 (ventana fija de 8): {causa}")
    # W410 — density sin traducción
    for iid, conf in insts.items():
        if not isinstance(conf, dict) or "density" not in conf:
            continue
        if iid in ("bass", "drums", "pad", "strings"):
            warn("W410", f"instruments.{iid}.density sin traducción v1 (1 aviso por declaración; ignorada)")
    escrito_sin_improv = escrito - {i.get("section") for i in improv if isinstance(i, dict)}
    if LEAD in {k for k, c in insts.items() if isinstance(c, dict) and "density" in c}:
        for s in secs:
            if isinstance(s, dict) and s.get("id") in escrito_sin_improv and suena(LEAD, s):
                warn("W410", f"density del sax no aplicable en '{s['id']}' (bloque efectivo de material escrito)")
    # W403 / W409 — bandas rev. 3.2
    d_inst_vibes = (insts.get(VIBES) or {}).get("density")
    for s in secs:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        d_receta_type = receta.D_RECETA[s["type"]] if receta is not None else None
        if receta is not None:
            d_eff = contract.density_efectiva((insts.get(VIBES) or {}).get("density"),
                                              s.get("density"), d_receta_type)
        elif d_inst_vibes is None and "density" in s:
            # cancelación exacta (propiedades 1 y 6 de §2.6.5): la banda es la de
            # la density de sección SEA CUAL SEA la tabla D_receta → verificable sin receta
            d_eff = s["density"]
        elif d_inst_vibes is None:
            # la efectiva sería D_receta(type): sin receta N1 no es computable
            NV.append(f"W403 no computable en '{sid}' sin receta N1 de '{identity}' "
                      "(density heredada de la receta)")
            d_eff = None
        else:
            NV.append(f"W403 no verificable en '{sid}' sin receta N1 de '{identity}' "
                      f"(vibraphone declara density propia {d_inst_vibes})")
            d_eff = None
        if d_eff is not None and contract.density_band(d_eff) == "B3" and suena(VIBES, s) \
                and guardrails.get("mallet_sparse", True):
            warn("W403", f"vibraphone con density efectiva {d_eff} en banda B3 y mallet_sparse ON ('{sid}')")
        tens = s.get("tension")
        if tens is None and receta is not None:
            tens = receta.TENSION_BASE[s["type"]]
        if tens is not None and contract.density_band(tens) == "B3" \
                and not (suena("pad", s) or suena("strings", s)):
            warn("W409", f"tension en banda B3 sin pad ni strings activos ('{sid}'): dispositivos limitados a voicings")
    # W413 — transpose_st fuera de registro
    reg = (insts.get(LEAD) or {}).get("register")
    if reg:
        lo_r, hi_r = reg
        for nombre, mo in motifs.items():
            if not isinstance(mo, dict):
                continue
            t = mo.get("transpose_st", 0) or 0
            descartadas = sum(1 for n in phrases.get(mo.get("from_section"), []) or []
                              if isinstance(n, dict)
                              and parse_pitch(n.get("pitch")) is not None
                              and not lo_r <= parse_pitch(n.get("pitch")) + t <= hi_r)
            if descartadas:
                warn("W413", f"motif {nombre}: {descartadas} nota(s) fuera del registro del lead tras transpose_st (descartadas)")
    # W414 — vocabulario por language
    for key, prog in (h.get("progressions") or {}).items():
        for sym in _simbolos(prog):
            if _parsea_acorde(sym) and _quality_tier(sym) not in _LANG_TIERS[language]:
                warn("W414", f"acorde '{sym}' fuera del vocabulario '{language}' (progressions.{key}); se respeta por precedencia")
    for s in secs:
        if not isinstance(s, dict):
            continue
        for sym in _simbolos(s.get("chords")):
            if _parsea_acorde(sym) and _quality_tier(sym) not in _LANG_TIERS[language]:
                warn("W414", f"acorde '{sym}' fuera del vocabulario '{language}' ('{s.get('id')}'); se respeta por precedencia")
    # W415 / W416
    finales = [s.get("id") for s in secs if isinstance(s, dict) and s.get("final")]
    if len(finales) > 1:
        warn("W415", f"final: true en {len(finales)} secciones {finales} (gana la última en orden)")
    def _ending_on(kind):
        v = ending.get(kind)
        return bool(v.get("enabled")) if isinstance(v, dict) else bool(v)
    if _ending_on("fade_out") and _ending_on("tape_stop"):
        warn("W416", "fade_out y tape_stop ambos activos (se aplican ambos; se sugiere elegir uno)")
    # W417
    for s in secs:
        if not isinstance(s, dict):
            continue
        cb = s.get("chord_bars", h.get("harmonic_rhythm_bars"))
        if cb and s.get("bars", 0) % cb != 0:
            warn("W417", f"chord_bars/harmonic_rhythm_bars ({cb}) no divide los {s.get('bars')} compases de '{s.get('id')}' (último acorde recortado)")
    # W418
    for imp in improv:
        if not isinstance(imp, dict):
            continue
        sec_imp = sec_by_id.get(imp.get("section"))
        if not isinstance(sec_imp, dict):
            continue
        nivel = sec_imp.get("drums")
        if nivel is None and receta is not None:
            nivel = receta.DRUMS_NIVEL[sec_imp["type"]]
        elif nivel is None:
            nivel = "groove"  # provisional sin receta (solo 'off' dispara)
        if nivel == "off":
            warn("W418", f"improvisación en '{sec_imp.get('id')}' con drums: off (no hay nivel que bajar)")
    # W407 / W419 — truncado y loop
    for nombre, mo in motifs.items():
        if not isinstance(mo, dict):
            continue
        src = mo.get("from_section")
        notas_src = phrases.get(src) or []
        loop = mo.get("loop_bars")
        for d in (mo.get("sections") or []):
            sec_d = sec_by_id.get(d)
            if not isinstance(sec_d, dict):
                continue
            dbars = sec_d.get("bars", 0)
            truncadas = sum(1 for n in notas_src if isinstance(n, dict) and n.get("bar", 0) >= dbars)
            if truncadas:
                warn("W407", f"motif {nombre}: {truncadas} nota(s) truncadas en '{d}' (material más largo que la sección)")
            if loop is not None and loop > dbars:
                warn("W419", f"motif {nombre}: loop_bars {loop} > compases del destino '{d}' (suena una vez y se corta)")
    # W412 / W420 / W421 — transiciones (§2.4.2)
    orden = [s for s in secs if isinstance(s, dict)]
    for i, s in enumerate(orden):
        es_ultima = (i == len(orden) - 1)
        res = s.get("resolution") or h.get("resolution") or LANG_DEFAULT_RES[language]
        if es_ultima:
            if "resolution" in s:
                warn("W412", f"resolution explícita en la última sección ('{s.get('id')}'): gesto omitido, acorde final entero")
            continue
        if s.get("bars", 0) < 2 and res in SPLIT_STRATS:
            warn("W420", f"transición desde '{s.get('id')}' con < 2 compases: split omitido (acorde entero)")
        if res in BASS_GESTURE and not suena(BASS, s):
            que = "approach omitido; el split sí se aplica" if res == "tonal" \
                else "gesto cromático omitido (la estrategia no incluye split)"
            warn("W421", f"transición '{s.get('id')}' → '{orden[i + 1].get('id')}': bass inactivo en el origen, {que}")
    # W406 — active/focus referencia instrumentos que no suenan
    for s in secs:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        for ref in list(s.get("focus") or []) + list(s.get("active") or []):
            if ref not in contract.INSTRUMENT_IDS:
                continue
            if not suena(ref, s):
                warn("W406", f"'{ref}' no suena en '{sid}' → entrada de active/focus ignorada")

    return _salir(E, W, X3, NV)


def _salir(E, W, X3, NV):
    return {"errores": E, "e3xx": X3, "avisos": W, "no_verificados": NV}


_Theory = None


def _theory():
    global _Theory
    if _Theory is None:
        from . import forge_link
        _Theory = forge_link.import_forge().theory
    return _Theory


def _parsea_acorde(sym):
    try:
        _theory().parse_chord(sym)
        return True
    except ValueError:
        return False
    # otras excepciones (p. ej. ForgeNoEncontrado) NO se tragan: sin la gramática
    # real del motor no se puede decidir E113, y fallar en silencio la corruptiría


def _parsea_key(texto):
    try:
        _theory().parse_key(texto)
        return True
    except ValueError:
        return False
