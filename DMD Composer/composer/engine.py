"""Motor de composición: orquesta el flujo completo de una generación.

    decisiones + seed
        → randomizador coherente (plan resuelto + log)
        → conflictos (pre-chequeos; si hay errores duros, NO se genera)
        → documento dark-director/1 + Song Map (JSON/CSV)
        → acordes literales validados con el parser REAL (si hay DMD)
        → validación REAL (puente subprocess con el DMD descubierto)
        → generación guardada (nunca sobrescribe; SHA256 en el manifest)

La validación real es la del validador del DMD real; si no hay DMD descubierto
se registra con honestidad (misión §11: no simular funcionalidades).

v1.1: el generation_manifest clasifica CADA eje en UN único estado real
(fijada / automática / libre) sin duplicados, separa las PREFERENCIAS que
nunca llegan al doc (mood/atmosphere/groove), convierte el perfil de
producción en una INSTRUCCIÓN verificable (estado
"seleccionado_pendiente_de_aplicar": nunca se declara aplicado) y añade el
bloque "armonia" con el modo REAL del documento y la fuente armónica por
sección (coherente con el Song Map).
"""
from __future__ import annotations

import datetime
import json
import time
from typing import Any, Dict, Optional

from . import __version__, bridge, builder, model, randomizer as R, songmap, store
from . import manifest as MF
from . import structure as ST

#: Ejes cuya decisión llega (directa o indirectamente) al documento.
EJES_DOC = ("identity", "accessibility", "bpm", "key", "language", "resolution",
            "harmonic_rhythm_bars", "harmony_mode", "spaces", "protagonist",
            "ending", "seed")
#: Preferencias de Composer que NUNCA se escriben en el doc (moldean sus
#: elecciones y, en production, la instrucción para Studio/DMD).
EJES_PREFERENCIA = ("mood", "atmosphere", "groove")

EFECTO_PREFERENCIA = {
    "mood": "define las pools ponderadas (tonalidad, lenguaje, atmósfera…) con las que Composer elige",
    "atmosphere": "sesga el perfil de producción sugerido y los avisos de coherencia de espacios",
    "groove": "solo sesga la curva de BPM AUTOMÁTICO; no es un campo del contrato ni parámetro del motor",
}


def _clasificar_decisiones(project: model.ComposerProject, plan: R.ResolvedPlan) -> Dict[str, Any]:
    """Un estado REAL por eje, sin duplicados ni valores fantasma.

    * fijadas     — ejes en modo fixed que llegan al doc (valor exacto escrito).
    * automaticas — ejes en modo auto (valor elegido por Composer y escrito).
    * libres      — ejes en modo free (campo NO escrito: el motor decide).
    mood/atmosphere/groove no se clasifican aquí: nunca llegan al doc.
    """
    fijadas: Dict[str, Any] = {}
    automaticas: Dict[str, Any] = {}
    for eje in EJES_DOC:
        st = (project.decisions.get(eje) or {}).get("mode")
        if st == model.FIXED:
            if eje == "seed":
                fijadas["seed"] = plan.seed_used
            else:
                fijadas[eje] = project.fixed_value(eje)
        elif st == model.AUTO:
            if eje == "seed":
                automaticas["seed"] = plan.seed_used
            else:
                v = plan.values.get(eje)
                if v is not None:
                    automaticas[eje] = v
    # fijadas ∩ automaticas = ∅ por construcción; libres = plan.free_axes
    return {"fijadas": fijadas, "automaticas": automaticas,
            "libres": list(plan.free_axes)}


def _instruccion_produccion(project: model.ComposerProject, plan: R.ResolvedPlan,
                            gen_dir: Optional[str]) -> Dict[str, Any]:
    """Instrucción VERIFICABLE para aplicar el perfil de producción.

    Composer no produce MIDI (D2) y el perfil no es un campo del contrato:
    nunca se declara "aplicado", solo "seleccionado_pendiente_de_aplicar".
    """
    perfil = plan.values.get("production")
    dec = project.decisions.get("production") or {}
    origen = "usuario" if (dec.get("mode") == model.FIXED and perfil) else \
             ("composer" if perfil else "sin_preferencia")
    prod = project.production or {}
    f7 = prod.get("f7_keyword")
    f7_var = prod.get("f7_variation")
    seed = plan.seed_used
    cli = "python scripts/produce.py doc.json" + (f" --production {perfil}" if perfil else "")
    cli += f" --seed {seed}" if seed is not None else "  # sin --seed usa global.seed del doc"
    if f7:
        cli += f" --harmony {f7}"
        if f7_var:
            cli += f" --harmony-variacion {f7_var}"
    cli += " --out <carpeta_de_salida>"
    return {
        "perfil": perfil,
        "origen": origen,
        "estado": "seleccionado_pendiente_de_aplicar" if perfil else "sin_perfil",
        "llega_al_doc": False,
        "nota": ("El perfil NO es un campo del contrato y Composer no genera MIDI: "
                 "esta selección solo se hace real al producir el MIDI en el pipeline "
                 "de DMD. Nunca se declara aplicada por el hecho de estar registrada."),
        "instruccion": {
            "studio": (f"Importa el doc.json de esta generación en DMD Studio y genera con "
                       f"Producción='{perfil or 'full (default)'}' y seed={seed} "
                       "(o vacío: el doc ya lleva global.seed)") + (f" · F7 keyword: {f7}" if f7 else ""),
            "cli": cli,
            "verificacion": "el SHA256 del MIDI resultante queda en la evidencia de Studio/produce.py",
            "carpeta_doc": gen_dir,
        },
        "f7_keyword": f7,
        "f7_variation": f7_var,
    }


def registrar_produccion(pid: str, gen_id: str, r_produce: Dict[str, Any], *,
                         perfil: str, seed: Optional[int], harmony: Optional[dict],
                         nombre: str) -> Dict[str, Any]:
    """Cierra el ciclo de producción de UNA generación (misión de integración).

    Registra el bloque "midi" del generation_manifest y avanza el estado del
    perfil de producción a "aplicado" — SOLO si el archivo real pasa la
    verificación de integridad en disco (existe, MThd, SHA256 == registrado).
    La UI nunca da por buena una producción sin esta evidencia.

    Nunca toca doc.json / song_map.* (generaciones inmutables); el bloque
    "midi" es el añadido planificado (roadmap v1.2 §2.2).

    ``r_produce`` es el dict del núcleo real (producir_cancion vía puente).
    Lanza StoreError si la integridad falla (el job lo registra como error).
    """
    if not r_produce.get("ok") or not r_produce.get("sha256"):
        raise store.StoreError("resultado de producción sin sha256: no se registra nada")
    d = store.gen_dir(pid, gen_id)
    out_dir = str(d / "midi" / nombre)
    regenerar = (f"python scripts/produce.py doc.json --production {perfil}"
                 + (f" --seed {int(seed)}" if seed is not None else "")
                 + f" --out {out_dir} --verify {r_produce['sha256']}")
    block = {
        "estado": "aplicado",
        "perfil": perfil,
        "seed": seed,
        "harmony": harmony,
        "generado_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "duracion_s": r_produce.get("duracion_s"),
        "bpm": r_produce.get("bpm"),
        "compases": r_produce.get("compases"),
        "nombre": nombre,
        "sha256": r_produce["sha256"],
        "rutas": {
            "midi": r_produce.get("midi"),
            "evidencia": r_produce.get("evidencia"),
            "config_efectiva": str(d / "midi" / nombre / "config_efectiva.json"),
            "events": r_produce.get("events"),
        },
        "verificado": True,
        "compliance_fails": r_produce.get("compliance_fails") or [],
        "compliance_warns": r_produce.get("compliance_warns") or [],
        "eventos": {"regenerar": regenerar},
    }
    # 1) bloque midi del manifest (atómico; write_midi_block rechaza reescritura)
    store.write_midi_block(pid, gen_id, block)
    # 2) integridad REAL en disco — sin esto NO se declara aplicado jamás
    integ = store.midi_integrity(pid, gen_id)
    if integ["estado"] != "ok":
        raise store.StoreError(f"integridad del MIDI producido falló: {integ['detalle']}")
    # 3) avance honesto del bloque produccion del manifest
    f = d / "generation_manifest.json"
    m = json.loads(f.read_text(encoding="utf-8"))
    prod = m.get("produccion")
    if isinstance(prod, dict):
        prod["estado"] = "aplicado"
        prod["midi_sha256"] = block["sha256"]
        prod["aplicado_utc"] = block["generado_utc"]
        store.atomic_write_json(f, m)
    return block


def compose(project: model.ComposerProject, dmd_path: Optional[str],
            manifest_full: Dict[str, Any], seed_override: Optional[int] = None,
            save: bool = True, validate: bool = True) -> Dict[str, Any]:
    """Flujo completo. Devuelve un dict con el resultado y sus artefactos."""
    out: Dict[str, Any] = {"ok": False, "errores": [], "avisos": [], "sugerencias": [],
                           "log": [], "warnings_pipeline": []}
    cat = MF.catalog(manifest_full)

    # 1) estructura fija del usuario → normalizar (E106/E105 anticipados).
    #    Sin secciones aún NO es error: puede venir la estructura automática.
    #    Los TypeError/ValueError de datos mal coercioandos se convierten en
    #    error limpio (auditoría M7: nada de 500 con stack).
    if project.sections:
        try:
            project.sections = ST.normalize_sections(project.sections, manifest_full)
        except ST.StructureError as e:
            out["errores"].append({"code": "E106", "where": "structure", "message": str(e),
                                   "fix": "corrige la estructura en el editor"})
            return out
        except (TypeError, ValueError) as e:
            out["errores"].append({"code": "datos", "where": "structure",
                                   "message": f"datos de sección no válidos: {e}",
                                   "fix": "revisa números y campos de las secciones"})
            return out

    # 2) plan del randomizador (misma semilla → mismo plan)
    try:
        plan = R.resolve(project, manifest_full, seed_override=seed_override)
    except Exception as e:
        out["errores"].append({"code": "plan", "where": "randomizer",
                               "message": f"plan no resoluble: {e}", "fix": "revisa las decisiones fijadas"})
        return out
    # estructura automática (si el usuario no construyó ninguna)
    import random as _r
    project.sections = R.resolve_auto_structure(project, plan, rng=_r.Random(plan.seed_used))
    try:
        project.sections = ST.normalize_sections(project.sections, manifest_full)
    except ST.StructureError as e:
        out["errores"].append({"code": "E106", "where": "structure", "message": str(e),
                               "fix": "ajusta la plantilla automática"})
        return out
    out["log"] = plan.log
    out["seed_used"] = plan.seed_used
    out["free_axes"] = plan.free_axes

    # 3) conflictos pre-validador
    conf = builder.conflicts(project, plan, manifest_full)
    out["errores"] += conf["errores"]
    out["avisos"] += conf["avisos"]
    out["sugerencias"] += conf["sugerencias"]
    if conf["errores"]:
        out["error"] = "restricciones incompatibles: corrige lo indicado antes de generar"
        return out

    # 4) documento + song map
    try:
        doc, build_info = builder.build(project, plan, manifest_full)
    except Exception as e:
        out["errores"].append({"code": "build", "where": "builder",
                               "message": f"no se pudo construir el documento: {e}",
                               "fix": "revisa tonalidad y progresiones"})
        return out
    try:
        sm = songmap.build_song_map(doc, project, manifest_full)
        csv_text = songmap.song_map_csv(sm)
    except Exception as e:
        out["errores"].append({"code": "songmap", "where": "song map",
                               "message": f"no se pudo construir el Song Map: {e}", "fix": "reporta el caso"})
        return out
    out["doc"] = doc
    out["song_map"] = sm
    out["song_map_csv"] = csv_text
    out["build"] = build_info

    # 4.b) acordes LITERALES → parser REAL del motor (un solo motor armónico).
    chords_doc = [c for s in doc.get("structure", []) for c in (s.get("chords") or [])]
    if chords_doc and dmd_path:
        pc = bridge.parse_chords(dmd_path, chords_doc)
        if pc.get("ok"):
            for r in pc.get("resultados", []):
                if not r.get("ok"):
                    out["errores"].append(
                        {"code": "E113", "where": "acordes literales",
                         "message": f"'{r['simbolo']}': {r.get('error')}",
                         "fix": "corrige el símbolo (gramática real de forge/theory) o quítalo"})
                    out["error"] = "el parser REAL rechaza un acorde literal"
        else:
            out["warnings_pipeline"].append(
                "acordes literales no prevalidados: " + str(pc.get("error")))
    elif chords_doc:
        out["warnings_pipeline"].append(
            "acordes literales SIN prevalidar (no hay DMD descubierto): el validador "
            "real los juzgará al importar el doc en Studio")
    if out.get("error"):
        return out

    # 5) validación REAL (puente)
    if validate and dmd_path:
        v = bridge.validate_doc(dmd_path, doc)
        if v.get("ok"):
            val = v["validacion"]
            out["validacion"] = {"ok": not val["errores"], **val}
            for code, msg in val["errores"]:
                out["errores"].append({"code": code, "where": "validador real", "message": msg,
                                       "fix": "corrige según el código del contrato"})
            for code, msg in val["avisos"]:
                out["avisos"].append({"code": code, "where": "validador real", "message": msg,
                                      "fix": "aviso W4xx: nunca bloquea"})
            if val["errores"]:
                out["error"] = "el validador REAL rechaza el documento"
                return out
        else:
            out["validacion"] = {"ok": None, "error": v.get("error")}
            out["warnings_pipeline"].append(
                "validación real no disponible: " + str(v.get("error")))

    # 6) compilación real de control (opcional, si hay DMD)
    if validate and dmd_path and not out["errores"]:
        c = bridge.compile_preview(dmd_path, doc)
        if c.get("ok"):
            out["compila"] = True
            out["compilado"] = {"total_bars": c.get("total_bars"),
                                "secciones": c.get("secciones"),
                                "target_schema": c.get("target_schema")}
        else:
            out["compila"] = False
            out["errores"].append({"code": "compilador", "where": "compilador real",
                                   "message": str(c.get("error")), "fix": "revisa el documento"})
            out["error"] = "el compilador real rechaza el documento"
            return out

    out["ok"] = True

    # 7) bloques de fidelidad para UI y manifest
    armonia_block = {
        "modo_global": build_info.get("harmony_mode"),
        "modo_real_del_doc": build_info.get("modo_real_del_doc"),
        "secciones_guiadas": build_info.get("progressions_secciones", []),
        "secciones_con_acordes_literales": build_info.get("chords_literales", []),
        "secciones_nativas": build_info.get("secciones_nativas", []),
        "secciones_sin_decision": build_info.get("secciones_sin_decision", []),
        "fuente_por_seccion": {row["id"]: row["fuente_armonia"] for row in sm.get("secciones", [])},
        "f7": {"activo_en_doc": False,
               "nota": "F7 (Familiarity Engine) es OPCIONAL y de Studio: el doc NUNCA la "
                       "contiene; se pasa como keyword al producir (nunca se mezcla sola)"},
    }
    prot = plan.values.get("protagonist")
    prot_block = {
        "id": prot,
        "propuesta": (project.protagonist_proposal or {"estado": "no_generada"}),
        "efecto_doc": {
            "enabled_true": sorted(iid for iid, e in (doc.get("instruments") or {}).items()
                                   if e.get("enabled") is True),
            "focus_con_protagonista": [s["id"] for s in doc.get("structure", [])
                                       if prot and prot in (s.get("focus") or [])],
        } if prot else None,
    }
    produccion_block = _instruccion_produccion(project, plan, None)
    out["armonia"] = armonia_block
    out["protagonista"] = prot_block
    out["produccion"] = produccion_block
    decisiones = _clasificar_decisiones(project, plan)
    preferencias = {"nota": "NO llegan al doc.json: condicionan cómo elige Composer",
                    "diversity": {"valor": project.diversity,
                                  "efecto": "aplana o endurece las pools (restrained → adventurous)"}}
    for eje in EJES_PREFERENCIA:
        st = (project.decisions.get(eje) or {}).get("mode")
        preferencias[eje] = {"estado": st or model.FREE,
                             "valor": plan.values.get(eje),
                             "efecto": EFECTO_PREFERENCIA[eje]}
    out["decisiones"] = decisiones
    out["preferencias_composer"] = preferencias

    # 8) persistencia
    if save:
        manifest_gen = {
            "formato": "generation-manifest/1",
            "composer_version": __version__,
            "timestamp": time.time(),
            "obra": project.name,
            "pid": project.pid,
            "seed_used": plan.seed_used,
            "decisiones": decisiones,
            "preferencias_composer": preferencias,
            "armonia": armonia_block,
            "protagonista": prot_block,
            "produccion": produccion_block,
            "log_explicabilidad": plan.log,
            "build": build_info,
            "doc_sha256": store.sha256_obj(doc),
            "contrato": cat.get("fingerprint"),
            "album": project.album,
            "validacion": {"ok": bool(out.get("validacion", {}).get("ok")),
                           "errores": len(out.get("validacion", {}).get("errores", []) or []),
                           "avisos": len(out.get("validacion", {}).get("avisos", []) or []),
                           "compila": bool(out.get("compila"))}
            if dmd_path else {"ok": None, "nota": "sin DMD descubierto: no se validó en vivo"},
        }
        saved = store.save_generation(project.pid or "sin_proyecto", doc, sm, csv_text, manifest_gen)
        # la instrucción de producción referencia la carpeta real ya creada
        if saved.get("gen_id"):
            out["produccion"]["instruccion"]["carpeta_doc"] = \
                str(store.OUTPUT_DIR / (project.pid or "sin_proyecto") / saved["gen_id"])
        out["generation"] = saved
    return out
