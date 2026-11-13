"""Harmonic Familiarity Engine — etapa de integración (FASE 7).

Punto ÚNICO de integración de la biblioteca de familiaridad armónica en el
pipeline: reescribe ``sections[].chords`` del proyecto YA COMPILADO
(vocabulario nativo midi-forge/1) ANTES del enriquecimiento. Así sax, Rhodes,
vibes, bajos, pad y comping heredan la nueva armonía por el camino normal:
``render.generate`` llama a ``aplicar`` justo tras normalizar la config y
antes de ``enhance``.

Garantías:
  - Sin clave ``harmony`` en la config → el proyecto no se toca (ni una
    copia) y el comportamiento es byte a byte el de FASE 6.
  - ``production='original'`` + ``harmony`` → ValueError (el camino ORIGINAL
    nunca se modifica).
  - Secciones con material del COMPOSITOR (lead.phrases del compilado)
    conservan su armonía original (el material protegido jamás se arriesga);
    se registran en la evidencia.
  - La adaptación de secciones es en orden INVERSO del timeline para que las
    colas de aproximación (FASE 7 §5) apunten al primer acorde REAL de la
    sección siguiente ya adaptada.
  - Determinista: toda decisión pasa por ``random.Random(seed)`` con orden
    estable de candidatos.
"""
import copy
import random

from forge import theory as T

from . import harmony_adapt as AD
from . import harmony_library as HL
from . import harmony_select as SEL

#: Claves del activador (documentadas en docs/HARMONIA_BIBLIOTECA.md).
VARIACION_DEFAULT = "subtle"

#: API estable del paquete: la validación de la activación vive en el motor de
#: selección, pero el punto de entrada público es este módulo.
normalizar_activacion = SEL.normalizar_activacion


def _tipo_y_drama(project):
    """(tonico, modo, [{id, tipo, tension, final, material, chord_bars}])."""
    g = project.get("global") or {}
    tonico, modo = T.parse_key(g.get("key") or "C major")
    original = ((project.get("meta") or {}).get("director") or {}).get("original") or {}
    orig_by_id, orig_by_type = {}, {}
    for s in original.get("structure") or []:
        orig_by_id[s.get("id")] = s
        orig_by_type.setdefault(s.get("type"), s)
    material = set((project.get("lead") or {}).get("phrases", {}).keys())
    secciones = []
    for sec in project.get("sections") or []:
        oe = orig_by_id.get(sec["id"], orig_by_type.get(sec.get("kind")))
        oe = oe or {}
        tipo = oe.get("type", sec.get("kind", "verse"))
        if tipo == "pre":
            tipo = "pre_chorus"
        secciones.append({
            "id": sec["id"], "tipo": tipo,
            "tension": (float(oe["tension"]) if oe.get("tension") is not None else None),
            "final": bool(sec.get("final")),
            "material": sec["id"] in material,
            "chord_bars": float(sec.get("chord_bars", 1) or 1),
            "bars": int(sec["bars"]),
        })
    return tonico, modo, secciones


def aplicar(project, act):
    """Aplica la activación al proyecto compilado. Devuelve (proyecto2, ev).

    No muta la entrada. ``act`` ya normalizada por ``normalizar_activacion``.
    """
    lib = HL.biblioteca()
    tonico, modo, info = _tipo_y_drama(project)
    eleccion, ev_sel = SEL.seleccionar(lib, info, tonico, modo, act, seed=act["seed"])
    rng = random.Random(int(act["seed"]) ^ 0x5EED7)
    proj = copy.deepcopy(project)
    by_id = {s["id"]: s for s in proj.get("sections") or []}

    ev = dict(ev_sel)
    ev["variacion"] = act["variacion"]
    ev["seed"] = act["seed"]
    ev["tonalidad"] = {"tonico": tonico, "modo": modo}
    ev["respetar_material"] = act["respetar_material"]
    ev["secciones"] = {}
    ev["respetadas_material"] = []
    ev["resumen"] = {"reescritas": 0, "respetadas": 0}

    simbolo_sig = None                     # primer acorde REAL de la sección siguiente
    orden = list(reversed(list(project.get("sections") or [])))
    adaptadas = {}
    for sec in orden:
        sid = sec["id"]
        meta = next(m for m in info if m["id"] == sid)
        if meta["material"] and act["respetar_material"]:
            ev["respetadas_material"].append(sid)
            ev["resumen"]["respetadas"] += 1
            adaptadas[sid] = None
            continue
        ele = eleccion.get(meta["tipo"])
        if not ele:
            adaptadas[sid] = None
            continue
        entry = HL.por_id(lib, ele["id"])
        seccion = {"id": sid, "bars": meta["bars"], "chord_bars": meta["chord_bars"],
                   "type": meta["tipo"], "final": meta["final"]}
        simbolos, log = AD.adaptar(entry, tonico, modo, seccion, act["variacion"],
                                   rng, primer_simbolo_siguiente=simbolo_sig)
        adaptadas[sid] = simbolos
        simbolo_sig = AD.primer_raiz(simbolos, tonico)
        ev["secciones"][sid] = {
            "tipo": meta["tipo"], "entrada": ele["id"], "nombre": ele["nombre"],
            "score": ele["score"], "simbolos": simbolos, "log": log,
        }
        ev["resumen"]["reescritas"] += 1

    # escritura (en orden natural; los dicts de sección ya son copia profunda)
    for sid, simbolos in adaptadas.items():
        if simbolos is None:
            continue
        sec = by_id[sid]
        sec["chords"] = copy.deepcopy(simbolos)
        for clave in ("chord_overrides", "cycle_bars"):
            if clave in sec:                     # restos de la armonía original
                del sec[clave]
                ev["secciones"][sid].setdefault("limpieza", []).append(clave)
    return proj, ev
