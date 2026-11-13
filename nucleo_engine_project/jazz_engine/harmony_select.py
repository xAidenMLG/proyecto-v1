"""Harmonic Selection Engine — FASE 7.

Búsqueda y selección de progresiones de la biblioteca de familiaridad:

  1. Recibe una activación (keyword | id | pins por tipo de sección).
  2. Filtra candidatos por clase modal de la composición y tipo de sección.
  3. Puntúa cada candidato: afinidad estructural, de tensión (recorrido
     emocional real de DMD), de resolución, familiaridad según keyword,
     variedad entre tipos y transición desde la sección anterior.
  4. Elige UNA progresión por TIPO de sección (verse/chorus/...): la
     recurrencia por tipo es exactamente lo que el oído reconoce como
     «familiar» en una canción real.

Determinista: candidatos siempre en orden de id; el azar se reduce a un
desempate minúsculo sembrado con ``random.Random(seed)``. Puro: no muta
entradas y no toca proyectos.
"""
import random

from . import harmony_adapt as HA
from . import harmony_library as HL
from .harmony_adapt import _parsear_grado as _pg   # uso interno del paquete
from .harmony_adapt import _raiz as _raiz_de        # uso interno del paquete

#: Keywords oficiales de activación (misión FASE 7 §6). Cada keyword define
#: una ESTRATEGIA de búsqueda (familias preferidas, pesos), no una progresión.
KEYWORDS = {
    "familiar_pop":        {"familias": ("familiaridad_pop",), "peso_fam": 1.4},
    "melancholic":         {"familias": ("melancolia_nostalgia",)},
    "nostalgic":           {"familias": ("melancolia_nostalgia", "familiaridad_pop"),
                            "peso_fam": 1.2, "sesgo_tension": -0.08},
    "dark_cinematic":      {"familias": ("oscuridad_cinematografica",)},
    "dream_pop":           {"familias": ("dream_pop_alternative",)},
    "alternative":         {"familias": ("dream_pop_alternative", "familiaridad_pop")},
    "soulful":             {"familias": ("soul_rnb",)},
    "emotional_resolution": {"min_resolucion": 0.65,
                             "resolucion_premio": ("chorus", "bridge", "outro")},
    "tension_release":     {"estrategia": "tension_release"},
    "familiarity_auto":    {},
}
KEYWORD_DEFAULT = "familiarity_auto"

#: Objetivo de tensión por tipo (prior dramático) — se mezcla 50/50 con la
#: tensión REAL que DMD declaró para las secciones de ese tipo.
_TENSION_TIPO = {"intro": 0.30, "verse": 0.40, "pre_chorus": 0.55, "chorus": 0.50,
                 "bridge": 0.55, "break": 0.70, "outro": 0.30}
_RES_PREMIO_TIPOS = ("chorus", "outro")


def clases_modal_validas():
    return tuple(sorted(HA.MODO_CLASE.keys()))


def _keywords_validos():
    return tuple(KEYWORDS)


def normalizar_activacion(raw, seed_base=0):
    """Valida la activación del side-file/CLI. Devuelve dict normalizado o
    None si ``raw`` es None (sin activación). Errores → ValueError claro:
    la activación debe ser un objeto NO vacío con 'keyword', 'id' o
    'progressions'."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("config['harmony'] debe ser un objeto "
                         "{'keyword'|'id'|'progressions', 'seed'?, 'variacion'?}")
    if not raw:
        raise ValueError("config['harmony'] vacía: declara 'keyword', 'id' o "
                         "'progressions'")
    claves = set(raw)
    desconocidas = claves - {"keyword", "id", "progressions", "seed",
                             "variacion", "respetar_material"}
    if desconocidas:
        raise ValueError("claves desconocidas en config['harmony']: %s "
                         "(válidas: keyword, id, progressions, seed, variacion, "
                         "respetar_material)" % ", ".join(sorted(desconocidas)))
    if "keyword" in claves and "id" in claves:
        raise ValueError("config['harmony']: usa 'keyword' o 'id', no ambos")
    act = {"seed": int(raw.get("seed", seed_base) or 0),
           "variacion": raw.get("variacion", "subtle"),
           "respetar_material": bool(raw.get("respetar_material", True)),
           "keyword": None, "id": None, "progressions": None}
    if act["variacion"] not in HL.NIVELES_VARIACION:
        raise ValueError("variación desconocida: %r (válidos: %s)"
                         % (act["variacion"], ", ".join(HL.NIVELES_VARIACION)))
    if "id" in raw:
        act["id"] = str(raw["id"])
    if "keyword" in raw:
        kw = str(raw["keyword"]).strip().lower()
        if kw not in KEYWORDS:
            raise ValueError("keyword armónica desconocida: %r (válidos: %s; "
                             "o usa {'id': ...} para una progresión concreta)"
                             % (raw["keyword"], ", ".join(_keywords_validos())))
        act["keyword"] = kw
    if "progressions" in raw:
        pins = raw["progressions"]
        if not isinstance(pins, dict) or not pins:
            raise ValueError("harmony.progressions debe ser un objeto "
                             "{'<tipo_sección>': '<ID>'}")
        for tipo, pid in pins.items():
            if tipo not in HL.TIPOS_ESTRUCTURA:
                raise ValueError("harmony.progressions: tipo de sección "
                                 "desconocido %r (válidos: %s)"
                                 % (tipo, ", ".join(HL.TIPOS_ESTRUCTURA)))
        act["progressions"] = {str(t): str(p) for t, p in pins.items()}
    if act["keyword"] is None and act["id"] is None and not act["progressions"]:
        raise ValueError("config['harmony'] vacía: declara 'keyword', 'id' o "
                         "'progressions'")
    return act


def _candidatos(lib, act, modo_clase):
    """Candidatos base según activación (con filtros duros de clase modal,
    con relajación documentada si el filtro deja vacío)."""
    if act["id"]:
        return [HL.por_id(lib, act["id"])], []
    pins_familias = None
    filtro = None
    if act["keyword"]:
        k = KEYWORDS[act["keyword"]]
        pins_familias = k.get("familias")
        filtro = k
    ids = sorted(lib)
    total = [lib[i] for i in ids]
    avisos = []
    if pins_familias:
        total = [e for e in total if e["familia"] in pins_familias]
        if not total:
            avisos.append("keyword sin progresiones: relajando familias")
            total = [lib[i] for i in ids]
    if filtro and filtro.get("min_resolucion"):
        estrictos = [e for e in total if e["resolucion"] >= filtro["min_resolucion"]]
        if estrictos:
            total = estrictos
        else:
            avisos.append("sin candidatos con resolución ≥ %.2f: relajando"
                          % filtro["min_resolucion"])
    compat = [e for e in total if e["modo"] == modo_clase]
    if not compat:
        avisos.append("sin progresiones de clase %s: relajando modo" % modo_clase)
        compat = total
    return compat, avisos


def _score_transicion(raiz_previa, raiz_candidata):
    """Movimiento de raíces entre secciones: 5ª/4ª > paso > mismo > tritono."""
    if raiz_previa is None or raiz_candidata is None:
        return 0.0
    iv = (raiz_candidata - raiz_previa) % 12
    if iv in (5, 7):
        return 0.6
    if iv in (1, 2, 10, 11):
        return 0.4
    if iv == 0:
        return 0.1
    if iv == 6:
        return -0.4
    return 0.0


def _objetivo_tension(tipo, tensiones_reales, act):
    base = _TENSION_TIPO.get(tipo, 0.45)
    reales = [t for t in tensiones_reales if t is not None]
    mezcla = 0.5 * base + 0.5 * (sum(reales) / len(reales) if reales else base)
    kw = KEYWORDS.get(act["keyword"] or "", {})
    sesgo = kw.get("sesgo_tension", 0.0)
    if kw.get("estrategia") == "tension_release":
        if tipo in ("pre_chorus", "bridge", "break"):
            mezcla += 0.12
        elif tipo in ("chorus", "outro"):
            mezcla -= 0.05
    return max(0.0, min(1.0, mezcla + sesgo))


def _score(entry, tipo, act, objetivo_tension, raiz_previa, primer_raiz_cand,
           usados_en_otros, cb_seccion):
    k = KEYWORDS.get(act["keyword"] or "", {})
    s = 0.0
    # familiaridad (peso según keyword)
    s += 1.6 * entry["familiaridad"] * k.get("peso_fam", 1.0)
    # afinidad de tensión con el recorrido emocional real
    s += 1.2 * (1.0 - abs(entry["tension"] - objetivo_tension))
    # resolución: premio en coros/finales; en breaks se prefiere suspender
    if tipo in _RES_PREMIO_TIPOS or tipo in k.get("resolucion_premio", ()):
        s += 0.8 * entry["resolucion"]
    if tipo in ("break", "intro") :
        s += 0.3 * (1.0 - entry["resolucion"])
    if k.get("estrategia") == "tension_release" and tipo in ("pre_chorus", "bridge", "break"):
        s -= 0.5 * entry["resolucion"]
    # variedad entre tipos: leve preferencia por arquetipos aún no usados (la
    # recurrencia real la fija la cuota CUOTA_DISTINTAS, no este término)
    s -= 0.3 * usados_en_otros
    # transición desde la sección anterior
    s += _score_transicion(raiz_previa, primer_raiz_cand)
    # ritmo armónico sugerido cercano al real de la sección
    if abs(float(entry["ritmo"]) - float(cb_seccion)) <= 0.5:
        s += 0.3
    return s


#: Cuota de progresiones DISTINTAS por canción: una canción real vive de 2-4
#: progresiones recurrentes; más variedad por sección mata la familiaridad y
#: menos mata el desarrollo. Los tipos fijados (pins/ID) nunca se reasignan.
CUOTA_DISTINTAS = 4


def _cuota_de_recurrencia(lib, eleccion, tipos_orden, act, tonico, modo,
                          tensiones_por_tipo, cb_por_tipo, avisos, rng):
    """Si la elección greedy supera la cuota de progresiones distintas, conserva
    las mejores por score agregado y reasigna el resto al mejor candidato
    conservado para cada tipo (determinista, pins respetados)."""
    pins = act.get("progressions") or {}
    if act.get("id"):
        return eleccion
    fijados = {t for t in eleccion if t in pins}
    libres = [t for t in tipos_orden if t not in fijados]
    ids_libres = {eleccion[t]["id"] for t in libres}
    if len(ids_libres) <= CUOTA_DISTINTAS:
        return eleccion
    agregado = {}
    for t in libres:
        v = eleccion[t]
        agregado[v["id"]] = agregado.get(v["id"], 0.0) + v["score"]
    conservar = {cid for cid, _ in sorted(agregado.items(),
                                          key=lambda kv: (-kv[1], kv[0]))
                 [:CUOTA_DISTINTAS]}
    reasignados = 0
    usados = {}
    for t in libres:
        if eleccion[t]["id"] in conservar:
            usados[eleccion[t]["id"]] = usados.get(eleccion[t]["id"], 0) + 1
    for t in libres:
        actual = eleccion[t]["id"]
        if actual in conservar:
            continue
        objetivo = _objetivo_tension(t, tensiones_por_tipo.get(t, []), act)
        puntuados = []
        for cid in sorted(conservar):
            e = lib[cid]
            raiz_cand = _raiz_de(_pg(e["grados"][0]), tonico, modo)
            sc = _score(e, t, act, objetivo, None, raiz_cand,
                        usados.get(cid, 0), cb_por_tipo.get(t, 1.0))
            sc += rng.random() * 1e-3
            puntuados.append((sc, cid))
        puntuados.sort(key=lambda p: (-p[0], p[1]))
        nuevo_sc, nuevo_id = puntuados[0]
        eleccion[t] = {"id": nuevo_id, "nombre": lib[nuevo_id]["nombre"],
                       "score": round(nuevo_sc, 3)}
        usados[nuevo_id] = usados.get(nuevo_id, 0) + 1
        reasignados += 1
    if reasignados:
        avisos.append("cuota de %d progresiones distintas por canción: %d tipo(s) "
                      "reasignado(s) a arquetipos conservados"
                      % (CUOTA_DISTINTAS, reasignados))
    return eleccion


def seleccionar(lib, secciones, tonico, modo, act, seed=0):
    """Selecciona una progresión por tipo de sección.

    ``secciones``: lista de dicts {id, tipo, tension, final, material,
    chord_bars} EN ORDEN del timeline. Devuelve (eleccion, evidencia):
    ``eleccion``: {tipo: {'id', 'nombre', 'score', 'desglose'}};
    ``evidencia``: dict completo para auditoría.
    """
    rng = random.Random(int(seed))
    modo_clase = HA.MODO_CLASE.get(modo, "menor")
    candidatos, avisos = _candidatos(lib, act, modo_clase)

    tipos_orden, tensiones_por_tipo, cb_por_tipo, finals = [], {}, {}, {}
    for sc in secciones:
        t = sc["tipo"]
        if t not in tipos_orden:
            tipos_orden.append(t)
            tensiones_por_tipo[t] = []
        tensiones_por_tipo[t].append(sc.get("tension"))
        cb_por_tipo.setdefault(t, float(sc.get("chord_bars", 1) or 1))
        if sc.get("final"):
            finals[t] = True

    eleccion, desgloses = {}, {}
    raiz_previa = None
    for tipo in tipos_orden:
        pid = (act.get("progressions") or {}).get(tipo) or act.get("id")
        objetivo = _objetivo_tension(tipo, tensiones_por_tipo.get(tipo, []), act)
        if pid:
            entry = HL.por_id(lib, pid)
            cand_ids = [entry["id"]]
        else:
            cand_ids = [e["id"] for e in candidatos]
        usados = {}
        for t, v in eleccion.items():
            usados[v["id"]] = usados.get(v["id"], 0) + 1
        puntuados = []
        for cid in cand_ids:
            e = lib[cid]
            if not pid and tipo not in e["estructura"]:
                continue
            # primera raíz del candidato (en la tonalidad real, sin adaptar):
            raiz_cand = _raiz_de(_pg(e["grados"][0]), tonico, modo)
            sc = _score(e, tipo, act, objetivo, raiz_previa, raiz_cand,
                        usados.get(cid, 0), cb_por_tipo.get(tipo, 1.0))
            sc += rng.random() * 1e-3              # desempate determinista
            puntuados.append((sc, cid))
        if not puntuados and not pid:
            # relajación documentada: sin candidato que declare el tipo,
            # se admite cualquiera de la pool (estructura flexible)
            for cid in cand_ids:
                e = lib[cid]
                sc = _score(e, tipo, act, objetivo, raiz_previa, None,
                            usados.get(cid, 0), cb_por_tipo.get(tipo, 1.0))
                sc += rng.random() * 1e-3
                puntuados.append((sc, cid))
            avisos.append("tipo %r sin progresiones con estructura declarada: "
                          "relajando estructura" % tipo)
        if not puntuados:
            raise ValueError("sin candidatos para el tipo %r (revisa la activación)"
                             % tipo)
        puntuados.sort(key=lambda p: (-p[0], p[1]))
        mejor_sc, mejor_id = puntuados[0]
        eleccion[tipo] = {"id": mejor_id, "nombre": lib[mejor_id]["nombre"],
                          "score": round(mejor_sc, 3)}
        desgloses[tipo] = [(round(s, 3), cid) for s, cid in puntuados[:3]]
        # raíz previa para la siguiente elección: ÚLTIMO acorde del ciclo base
        gl = _pg(lib[mejor_id]["grados"][-1])
        raiz_previa = _raiz_de(gl, tonico, modo)

    eleccion = _cuota_de_recurrencia(lib, eleccion, tipos_orden, act, tonico,
                                     modo, tensiones_por_tipo, cb_por_tipo,
                                     avisos, rng)

    evidencia = {
        "keyword": act["keyword"], "id": act["id"],
        "pins": act.get("progressions"), "modo_composicion": modo,
        "clase_modal": modo_clase, "candidatos_evaluados": len(candidatos),
        "avisos": avisos,
        "top3_por_tipo": {t: desgloses[t] for t in desgloses},
        "criterios": ("familiaridad×keyword + afinidad de tensión (recorrido DMD) "
                      "+ resolución por tipo + variedad entre tipos + transición "
                      "de raíces + ritmo armónico; desempate sembrado"),
    }
    return eleccion, evidencia
