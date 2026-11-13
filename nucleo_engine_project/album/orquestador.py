"""Orquestador del álbum — FASE 8.

Ejecuta el plan pista a pista REUTILIZANDO el núcleo de scripts/produce.py
(``producir_cancion``): nada de generación paralela, nada de render nuevo.
Cada pista vive en su carpeta ``NN_<id>/`` con los artefactos oficiales de
FASE 6 (doc.json, config_efectiva.json, <id>.mid, evidencia.json).

Estado y recuperación (misión §8):
  - ``estado.json`` registra por pista: estado (ok|fallo|pendiente), sha256,
    huella técnica, error, e identidad de la ejecución (sha256_doc + perfil +
    seed + harmony). Se actualiza tras CADA pista (crash-safe).
  - Reanudación: un ``producir`` posterior salta las pistas ok cuya
    especificación NO cambió. Si el doc/perfil/seed/harmony cambió, la pista
    se marca pendiente con razón ``cambio_especificacion`` y NO se regenera
    en silencio: hace falta ``--regen`` (resultados aceptados preservados).
  - ``--regen id1,id2`` regenera SOLO esas pistas (índice "03" o id).
  - ``--solo id1,id2`` produce solo esas pistas sin tocar el resto del
    estado (útil para producir por bloques).
  - Fallo de una pista NO aborta el álbum: se registra y se continúa; el
    código de salida es 1 si hubo algún fallo.
"""
import copy
import datetime
import hashlib
import json
import sys
import traceback
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from . import esquema as ES
from . import planificador as PL

ESTADO_OK = "ok"
ESTADO_FALLO = "fallo"
ESTADO_PENDIENTE = "pendiente"

RAZON_ESPEC_CAMBIO = "cambio_especificacion"


def _ruta_estado(out_dir):
    return Path(out_dir) / "estado.json"


def _cargar_estado(out_dir):
    p = _ruta_estado(out_dir)
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"schema": ES.SCHEMA_ALBUM, "pistas": {}}
    return {"schema": ES.SCHEMA_ALBUM, "pistas": {}}


def _guardar_estado(out_dir, estado):
    estado["actualizado_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _ruta_estado(out_dir).write_text(json.dumps(estado, ensure_ascii=False, indent=2),
                                     encoding="utf-8")


def _huella_json(huella):
    """Huella como lista compacta (para huellas.json)."""
    return list(huella or [])


def _especificacion(plan_pista):
    """Firma de la especificación efectiva de una pista (para detectar cambios)."""
    return {"sha256_doc": plan_pista["sha256_doc"],
            "perfil": plan_pista["perfil"],
            "seed": plan_pista["seed"],
            "harmony": plan_pista["harmony"]}


def _resolver_ids(plan, lista):
    """Acepta ids ('03_ritual') o índices ('3', '03'). Devuelve ids válidos."""
    por_indice = {str(t["indice"]).zfill(2): t["id"] for t in plan["pistas"]}
    ids = set()
    desconocidos = []
    for x in lista:
        x = str(x).strip()
        if x in {t["id"] for t in plan["pistas"]}:
            ids.add(x)
        elif x.zfill(2) in por_indice:
            ids.add(por_indice[x.zfill(2)])
        else:
            desconocidos.append(x)
    return ids, desconocidos


def ejecutar(ruta_album, out_dir, *, regen=(), solo=None, forzar=False,
             informe=True, verbose=True):
    """Produce el álbum. Devuelve código de salida (0 OK; 1 hubo fallos).

    ``ruta_album``: ruta del album.json. ``out_dir``: carpeta de resultados
    (plan.json, estado.json, huellas.json, informe_album.*, NN_<id>/).
    """
    raiz = Path(ruta_album).resolve().parent
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    spec, avisos_esquema = ES.cargar_album(ruta_album)
    plan, avisos_plan = PL.planificar(spec, raiz)
    PL.escribir_plan(plan, out / "plan.json")

    estado = _cargar_estado(out)
    estado.setdefault("pistas", {})
    estado["album"] = plan["album"]
    estado["schema"] = ES.SCHEMA_ALBUM
    estado["semilla_album"] = plan["semilla_album"]

    regen_ids, desconocidos = _resolver_ids(plan, regen)
    if desconocidos:
        raise ValueError("--regen: ids/índices desconocidos: %s (válidos: %s)"
                         % (", ".join(desconocidos),
                            ", ".join(t["id"] for t in plan["pistas"])))
    solo_ids = None
    if solo:
        solo_ids, desconocidos = _resolver_ids(plan, solo)
        if desconocidos:
            raise ValueError("--solo: ids/índices desconocidos: %s"
                             % ", ".join(desconocidos))

    sys_path = Path(__file__).resolve().parent.parent / "scripts"
    if str(sys_path) not in sys.path:
        sys.path.insert(0, str(sys_path))
    import produce as PD  # núcleo oficial de producción (FASE 6/8)

    ruta_huellas = out / "huellas.json"
    huellas = {}
    if ruta_huellas.is_file():
        try:
            huellas = json.loads(ruta_huellas.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            huellas = {}
    fallos = 0
    for t in plan["pistas"]:
        tid = t["id"]
        carpeta = out / ("%02d_%s" % (t["indice"], tid))
        previo = (estado["pistas"].get(tid) or {})
        if solo_ids is not None and tid not in solo_ids:
            continue  # --solo: no tocar el resto del estado
        if t.get("error_plan"):
            # documento inválido detectado en planificación: registrar y seguir
            reg = {"estado": ESTADO_FALLO, "id": tid, "indice": t["indice"],
                   "perfil": t.get("perfil"), "seed": None, "harmony": None,
                   "error": t["error_plan"], "razon": "error_plan",
                   "carpeta": str(carpeta),
                   "intentos": int(previo.get("intentos", 0))}
            estado["pistas"][tid] = reg
            _guardar_estado(out, estado)
            fallos += 1
            if verbose:
                print("FALLO %s (plan): %s" % (tid, t["error_plan"].split(" — ")[0]))
            continue
        regenerar = forzar or tid in regen_ids
        if previo.get("estado") == ESTADO_OK and not regenerar:
            esp_ante = previo.get("especificacion") or {}
            esp_ahora = _especificacion(t)
            if esp_ante == esp_ahora:
                huellas.setdefault(tid, previo.get("huella_sha") or [])
                if verbose:
                    print("SALTADA %s (ya producida; sha %s…)" % (tid, previo.get("sha256_midi", "")[:16]))
                continue
            # especificación cambió: preservar el resultado aceptado y avisar
            previo["estado"] = ESTADO_PENDIENTE
            previo["razon"] = RAZON_ESPEC_CAMBIO
            estado["pistas"][tid] = previo
            _guardar_estado(out, estado)
            if verbose:
                print("PENDIENTE %s (la especificación cambió; usa --regen %s para "
                      "regenerar; el resultado anterior se conserva)" % (tid, tid))
            continue

        doc = json.loads(Path(t["doc_resuelto"]).read_text(encoding="utf-8"))
        reg = {"estado": None, "id": tid, "indice": t["indice"],
               "perfil": t["perfil"], "seed": t["seed"],
               "harmony": copy.deepcopy(t["harmony"]),
               "especificacion": _especificacion(t),
               "carpeta": str(carpeta),
               "intentos": int(previo.get("intentos", 0)) + 1}
        try:
            r = PD.producir_cancion(doc, production=t["perfil"], seed=t["seed"],
                                    harmony=t["harmony"], out_dir=carpeta,
                                    indice=False)
            reg.update({"estado": ESTADO_OK, "sha256_midi": r["sha256"],
                        "bpm": r["bpm"], "compases": r["compases"],
                        "duracion_s": r["duracion_s"],
                        "compliance_fails": r["compliance_fails"],
                        "compliance_warns": r["compliance_warns"],
                        "huella_sha": hashlib.sha256(
                            json.dumps(_huella_json(r["huella"])).encode()
                        ).hexdigest()[:16]})
            huellas[tid] = _huella_json(r["huella"])
            if verbose:
                print("OK %s (%s, seed %d) SHA %s…" % (tid, t["perfil"], t["seed"],
                                                       r["sha256"][:16]))
        except Exception as e:  # aislamiento de fallos por pista
            reg.update({"estado": ESTADO_FALLO,
                        "error": "%s: %s" % (type(e).__name__, e),
                        "traceback": traceback.format_exc(limit=8)})
            huellas.pop(tid, None)
            fallos += 1
            if verbose:
                print("FALLO %s: %s" % (tid, reg["error"]))
        estado["pistas"][tid] = reg
        _guardar_estado(out, estado)

    ruta_huellas.write_text(json.dumps(huellas), encoding="utf-8")

    if informe:
        from . import informe as INF
        INF.generar(out)
    return 1 if fallos else 0


def estado_de(out_dir):
    """Estado legible del álbum (para el CLI ``estado``)."""
    estado = _cargar_estado(out_dir)
    lineas = []
    for tid, reg in estado.get("pistas", {}).items():
        det = reg.get("sha256_midi", reg.get("error", ""))[:40]
        lineas.append("%-24s %-10s %s" % (tid, reg.get("estado"), det))
    return estado, lineas
