"""Planificador de álbum — FASE 8.

Convierte un spec ``dmd-album/1`` validado en un PLAN ejecutable y
determinista (``dmd-album-plan/1``). Para cada pista:

  1. Resuelve y verifica el documento dark-director/1 (existencia, esquema,
     identidad del álbum) y lo COMPILA en seco (dry-run) para detectar
     documentos inválidos ANTES de producir nada.
  2. Extrae un digest técnico (BPM, tonalidad, compases, secciones,
     energías) que alimenta el control de diversidad.
  3. Asigna perfil de producción y seed cuando el spec no los declara:
     - semilla derivada:  ``seed = semilla_album + 101 * (indice + 1)``
       (fórmula documentada y estable; una semilla explícita siempre gana).
     - perfil: greedy determinista bajo las restricciones del spec
       (fracción máxima por perfil, respiro cada N pistas, variedad en
       consecutivas). Las decisiones explícitas del compositor SIEMPRE
       ganan sobre la asignación (si violan restricciones → aviso, no error).
  4. Analiza diversidad PRE y anexa avisos.

El plan se escribe como ``plan.json`` en la carpeta de salida y es el
contrato de ejecución del orquestador: reproducible y auditable.
"""
import copy
import datetime
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):  # ejecución directa del módulo
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from . import esquema as ES
from . import diversidad as DV

_SECCIONES_BASICO = {"id", "type", "bars", "energy", "tension", "density",
                     "focus", "active", "drums", "final", "chord_bars",
                     "materials", "materials_ref", "lead", "melody", "harmony_overrides"}


def _sha_texto(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _responder_orden_canonico():
    import jazz_engine as je
    return list(je.production.nombres())


def _orden_preferencia(candidatos, *, usos, perfil_previo, necesita_respiro):
    """Orden determinista de candidatos para la pista actual.

    Criterios en orden: (1) respiro obligado por la ventana, (2) no repetir
    perfil consecutivo, (3) menor uso hasta ahora, (4) orden canónico.
    """
    canonico = _responder_orden_canonico()

    def clave(p):
        es_respiro = p in ES.PERFILES_RESPIRO
        return (0 if (necesita_respiro and es_respiro) else 1,
                1 if p == perfil_previo else 0,
                usos.get(p, 0),
                canonico.index(p))
    return sorted(candidatos, key=clave)


def _asignar_perfiles(pistas, restricciones, n):
    """Completa los perfiles no declarados (determinista; deja los explícitos)."""
    usos = {}
    for p in pistas:
        if p["perfil"] is not None:
            usos[p["perfil"]] = usos.get(p["perfil"], 0) + 1
    candidatos = _responder_orden_canonico()
    previo = next((p["perfil"] for p in reversed(pistas) if p["perfil"]), None)
    respiro_cada = int(restricciones.get("respiro_cada", 5))
    frac_max = float(restricciones.get("perfil_frac_max", 0.4))

    for i, p in enumerate(pistas):
        if p.get("error_plan"):
            continue  # pistas con documento inválido: no se asigna nada
        if p["perfil"] is not None:
            previo = p["perfil"]
            continue
        # ventana que TERMINA en i: si las últimas respiro_cada-1 pistas ya
        # decididas no contienen respiro, esta pista DEBE serlo para cerrar
        # una ventana completa con respiro.
        previas = [q["perfil"] for q in pistas[max(0, i - respiro_cada + 1):i]
                   if q["perfil"] is not None]
        necesita_respiro = (i >= respiro_cada - 1 and len(previas) == respiro_cada - 1
                            and all(x not in ES.PERFILES_RESPIRO for x in previas))
        orden = _orden_preferencia(
            candidatos, usos=usos, perfil_previo=previo,
            necesita_respiro=necesita_respiro)
        elegido = None
        for c in orden:
            if usos.get(c, 0) + 1 > frac_max * n + 1e-9:
                continue
            elegido = c
            break
        if elegido is None:  # restricciones imposibles: relaja fracción
            elegido = orden[0]
        p["perfil"] = elegido
        p["_perfil_asignado"] = True
        usos[elegido] = usos.get(elegido, 0) + 1
        previo = elegido
    return pistas


def _digest_doc(doc, proyecto):
    """Digest técnico de un documento compilado (para diversidad/coherencia)."""
    secs = doc.get("structure") or []
    h = doc.get("harmony") or {}
    g = doc.get("global") or {}
    energias = [float(s.get("energy", 0.0)) for s in secs]
    tensiones = [float(s.get("tension", 0.0)) for s in secs]
    densidades = [float(s.get("density", 0.0)) for s in secs]
    material = [s.get("id") for s in secs
                if ("lead" in s or "melody" in s or "materials" in s
                    or "materials_ref" in s)]
    tipos = [s.get("type") for s in secs]
    return {
        "titulo": (doc.get("meta") or {}).get("title"),
        "bpm": int(g.get("bpm", 0)),
        "seed_global": int(g.get("seed", 0)),
        "tonalidad": h.get("key"),
        "lenguaje": h.get("language"),
        "resolucion": h.get("resolution"),
        "compases": int(proyecto.get("meta", {}).get("bars", 0) or
                        sum(int(s.get("bars", 0)) for s in secs)),
        "n_secciones": len(secs),
        "tipos_seccion": tipos,
        "energia_media": round(sum(energias) / len(energias), 3) if energias else 0.0,
        "energia_max": round(max(energias), 3) if energias else 0.0,
        "tension_media": round(sum(tensiones) / len(tensiones), 3) if tensiones else 0.0,
        "densidad_media": round(sum(densidades) / len(densidades), 3) if densidades else 0.0,
        "secciones_con_material_escrito": material,
        "ending": sorted((doc.get("ending") or {}).keys()),
    }


def planificar(spec, raiz):
    """Planifica el álbum. ``spec`` validado; ``raiz`` = Path del album.json.

    Devuelve (plan, avisos). Los documentos individuales que fallan NO
    abortan el álbum (misión §8 — fallos parciales sin perder pistas
    válidas): quedan en ``plan['errores_documentos']`` y en la pista como
    ``error_plan``; el orquestador los registra como fallo y produce el
    resto. Solo abortan los problemas estructurales del spec (ya validados).
    """
    raiz = Path(raiz).resolve()
    pistas_spec = spec["pistas"]
    restricciones = dict(ES.DEFAULTS_RESTRICCIONES)
    restricciones.update(copy.deepcopy(spec.get("restricciones") or {}))
    semilla_album = int(spec["semilla_album"])
    identidad = spec.get("identidad", ES.IDENTIDAD_ALBUM)
    errores_docs = []
    avisos = list()

    pistas = []
    for i, p in enumerate(pistas_spec):
        ref = p["doc"]
        ruta = Path(ref)
        if not ruta.is_absolute():
            ruta = raiz / ruta
        ruta = ruta.resolve()
        pref = "pistas[%d] (%s)" % (i + 1, p.get("id", "?"))
        if not ruta.is_file():
            errores_docs.append("A201: %s — no existe el documento: %s" % (pref, ruta))
            pistas.append({"indice": i + 1, "id": p["id"], "error_plan": errores_docs[-1],
                           "digest": None, "perfil": p.get("perfil"), "seed": None,
                           "origen_seed": "n/d", "harmony": None, "doc": ref,
                           "doc_resuelto": str(ruta), "sha256_doc": None,
                           "titulo": p.get("titulo") or p["id"], "rol": p.get("rol")})
            continue
        try:
            doc = json.loads(ruta.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            errores_docs.append("A202: %s — JSON inválido: %s" % (pref, e))
            pistas.append({"indice": i + 1, "id": p["id"], "error_plan": errores_docs[-1],
                           "digest": None, "perfil": p.get("perfil"), "seed": None,
                           "origen_seed": "n/d", "harmony": None, "doc": ref,
                           "doc_resuelto": str(ruta), "sha256_doc": None,
                           "titulo": p.get("titulo") or p["id"], "rol": p.get("rol")})
            continue
        if doc.get("schema") != "dark-director/1":
            errores_docs.append("A203: %s — schema %r != 'dark-director/1'"
                                % (pref, doc.get("schema")))
            pistas.append({"indice": i + 1, "id": p["id"], "error_plan": errores_docs[-1],
                           "digest": None, "perfil": p.get("perfil"), "seed": None,
                           "origen_seed": "n/d", "harmony": None, "doc": ref,
                           "doc_resuelto": str(ruta), "sha256_doc": None,
                           "titulo": p.get("titulo") or p["id"], "rol": p.get("rol")})
            continue
        dir_identity = (doc.get("direction") or {}).get("identity")
        if dir_identity != identidad:
            errores_docs.append("A204: %s — identidad del documento %r != identidad del "
                                "álbum %r (un álbum es un solo universo musical)"
                                % (pref, dir_identity, identidad))
            pistas.append({"indice": i + 1, "id": p["id"], "error_plan": errores_docs[-1],
                           "digest": None, "perfil": p.get("perfil"), "seed": None,
                           "origen_seed": "n/d", "harmony": None, "doc": ref,
                           "doc_resuelto": str(ruta), "sha256_doc": None,
                           "titulo": p.get("titulo") or p["id"], "rol": p.get("rol")})
            continue
        from dark_director import compilador as CD
        try:
            r = CD.compilar(copy.deepcopy(doc))
        except CD.DirectorInvalido as e:
            det = getattr(e, "args", [None])[0]
            resumen = det if isinstance(det, str) else getattr(det, "errores", None) or det
            errores_docs.append("A205: %s — el documento no compila: %s" % (pref, resumen))
            pistas.append({"indice": i + 1, "id": p["id"], "error_plan": errores_docs[-1],
                           "digest": None, "perfil": p.get("perfil"), "seed": None,
                           "origen_seed": "n/d", "harmony": None, "doc": ref,
                           "doc_resuelto": str(ruta), "sha256_doc": None,
                           "titulo": p.get("titulo") or p["id"], "rol": p.get("rol")})
            continue
        except CD.StrictBloqueante as e:
            errores_docs.append("A205: %s — bloqueado por strict: %s" % (pref, e))
            pistas.append({"indice": i + 1, "id": p["id"], "error_plan": errores_docs[-1],
                           "digest": None, "perfil": p.get("perfil"), "seed": None,
                           "origen_seed": "n/d", "harmony": None, "doc": ref,
                           "doc_resuelto": str(ruta), "sha256_doc": None,
                           "titulo": p.get("titulo") or p["id"], "rol": p.get("rol")})
            continue

        seed = p.get("seed")
        origen_seed = "especificado"
        if seed is None:
            seed = semilla_album + 101 * (i + 1)
            origen_seed = "derivada"
        pistas.append({
            "indice": i + 1,
            "id": p["id"],
            "titulo": p.get("titulo") or (doc.get("meta") or {}).get("title") or p["id"],
            "rol": p.get("rol"),
            "doc": ref,
            "doc_resuelto": str(ruta),
            "sha256_doc": _sha_texto(json.dumps(doc, ensure_ascii=False, sort_keys=True)),
            "perfil": p.get("perfil"),
            "seed": int(seed),
            "origen_seed": origen_seed,
            "harmony": copy.deepcopy(p.get("harmony")),
            "_perfil_asignado": p.get("perfil") is None,
            "digest": _digest_doc(doc, r["proyecto"]),
        })

    n = len(pistas)
    _asignar_perfiles(pistas, restricciones, n)

    # armonía de la pista: jamás inyectada; solo eco del spec (o None).
    for p in pistas:
        asignado = p.pop("_perfil_asignado", False)
        p["perfil_origen"] = "asignado" if asignado else "especificado"
        if p["harmony"] is not None and p["harmony"].get("keyword") == "familiarity_auto":
            avisos.append("W-A3: la pista '%s' usa familiarity_auto declarada "
                          "EXPLÍCITAMENTE en el spec (el sistema nunca la activa solo)"
                          % p["id"])

    analisis_pre = DV.analizar_pre(pistas, restricciones)
    frac_max = float(restricciones.get("perfil_frac_max", 0.4))
    for ex in analisis_pre["exceso_perfil"]:
        explic = next((q for q in pistas if q["perfil"] == ex["perfil"]), None)
        explicitas = sum(1 for q in pistas_spec
                         if q.get("perfil") == ex["perfil"])
        avisos.append("W-A4: el perfil '%s' cubre %d/%d pistas (> %.0f%%)%s"
                      % (ex["perfil"], ex["cuenta"], n, 100 * frac_max,
                         " — perfiles explícitos del compositor: se respetan"
                         if explicitas else ""))
    for v in analisis_pre["ventanas_sin_respiro"]:
        avisos.append("W-A5: ventana %s–%s sin pista de respiro (%s)"
                      % (v[0], v[1], "/".join(ES.PERFILES_RESPIRO)))
    for c in analisis_pre["consecutivos_iguales"]:
        avisos.append("W-A6: consecutivas sospechosas %s (%s)"
                      % ("<->".join(c["pistas"]), c["motivo"]))
    for t in analisis_pre["bpm_fuera_de_rango"]:
        avisos.append("W-A7: '%s' con BPM %d fuera del rango de referencia %d–%d "
                      "(Dark Trip Hop)" % (t["pista"], t["bpm"], *DV.BPM_SANO))

    curva = spec.get("curva_energia")
    real = DV.curva_energia_real(pistas)
    desv = DV.desviacion_curva(curva, real)
    if curva:
        for i, d in enumerate(desv):
            if d > 0.15:
                avisos.append("W-A8: '%s' energía media %.2f vs objetivo %.2f "
                              "(desviación %.2f > 0.15)" % (pistas[i]["id"], real[i],
                                                            curva[i], d))

    import jazz_engine as je
    from dark_director import contract as CT
    plan = {
        "schema": ES.SCHEMA_PLAN,
        "album": spec.get("album"),
        "identidad": identidad,
        "semilla_album": semilla_album,
        "restricciones": restricciones,
        "raiz": str(raiz),
        "creado_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "versiones": {"album": __import__("album").__version__,
                      "jazz_engine": je.__version__,
                      "contrato": CT.contract_info()},
        "pistas": pistas,
        "errores_documentos": errores_docs,
        "analisis": {
            "diversidad_pre": analisis_pre,
            "curva_energia": {
                "objetivo": curva,
                "real": real,
                "desviacion": desv if curva else None,
            },
            "avisos": avisos,
        },
    }
    return plan, avisos


def escribir_plan(plan, ruta_salida):
    """Escribe plan.json (UTF-8, determinista salvo creado_utc)."""
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
    import json
    Path(ruta_salida).write_text(json.dumps(plan, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    return Path(ruta_salida)
