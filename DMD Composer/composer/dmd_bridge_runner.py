"""Runner del puente Composer → DMD REAL (proceso hijo aislado).

Ejecutado por ``composer.bridge`` con el intérprete actual y UN argumento
fijo (``--spec``). Nunca recibe código ni comandos del usuario: solo rutas y
un JSON validado. Añade la ruta del DMD descubierto a ``sys.path`` y usa los
módulos REALES (contrato, recetas, validador, compilador, producción, F7) —

  * introspect     → manifiesto de capacidades reales (catálogos + recetas).
  * validate       → validador REAL (E1xx/E2xx/E3xx + W4xx).
  * compile_preview→ compilador REAL sin renderizar (estructura + acordes).
  * parse_chords   → forge.theory.parse_chord REAL sobre símbolos literales
                     (editor de acordes por sección; v1.1). Un solo motor
                     armónico: el del DMD real.
  * produce        → núcleo de producción REAL (scripts/produce.py::
                     producir_cancion, cargado por RUTA igual que
                     studio/runner.py). Escribe en ``out_dir`` el MIDI,
                     evidencia.json, config_efectiva.json y (opcional,
                     Opción A) events.json. Único productor de MIDI.
  * capabilities   → versión del studio/motores para el fingerprint.

Escribe el resultado como JSON en el archivo ``--out``; el estado de error
viaja en ``{"ok": false, "error": ...}``. Nada se imprime a stdout salvo el
marcador final (patrón studio.runner).
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path


def _import_dmd(dmd_path: str):
    """Importa los módulos del DMD REAL desde su carpeta (solo lectura)."""
    root = Path(dmd_path).resolve()
    if not (root / "dark_director" / "contract.py").is_file():
        raise FileNotFoundError(
            f"'{root}' no parece un DMD (falta dark_director/contract.py)")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    dd = importlib.import_module("dark_director")
    contract = importlib.import_module("dark_director.contract")
    validador = importlib.import_module("dark_director.validador")
    compilador = importlib.import_module("dark_director.compilador")
    identities = importlib.import_module("dark_director.identities")
    je = importlib.import_module("jazz_engine")
    production = importlib.import_module("jazz_engine.production")
    hlib = importlib.import_module("jazz_engine.harmony_library")
    return contract, validador, compilador, identities, je, production, hlib


def _safe_export(v):
    """Solo tipos JSON (títulos/sets → listas)."""
    if isinstance(v, dict):
        return {str(k): _safe_export(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_safe_export(x) for x in v]
    if isinstance(v, (int, float, bool)) or v is None:
        return v
    return str(v)


def task_introspect(mods) -> dict:
    contract, validador, compilador, identities, je, production, hlib = mods
    recetas = {}
    con_receta = tuple(getattr(identities, "CON_RECETA", ()))
    identidad_activa = getattr(identities, "IDENTIDAD_ACTIVA", None)
    archivadas = tuple(getattr(identities, "IDENTIDADES_ARCHIVADAS", ()))
    for identity in contract.IDENTITIES:
        mod = getattr(identities, identity, None)
        if mod is None or identity not in con_receta:
            continue
        progs = {}
        for lang, tabla in getattr(mod, "PROGRESIONES", {}).items():
            progs[lang] = {t: [list(p) for p in pairs] for t, pairs in tabla.items()}
        recetas[identity] = {
            "set_base": list(getattr(mod, "SET_BASE", ())),
            "lead": getattr(mod, "LEAD", "sax_tenor"),
            "bpm_default": getattr(mod, "BPM_DEFAULT", None),
            "bpm_rango": list(getattr(mod, "BPM_RANGO_TIPICO", (70, 96))),
            "harmonic_rhythm_bars": getattr(mod, "HARMONIC_RHYTHM_BARS", 1),
            "register_default": _safe_export(getattr(mod, "REGISTER_DEFAULT", {})),
            "d_receta": _safe_export(getattr(mod, "D_RECETA", {})),
            "energy_base": _safe_export(getattr(mod, "ENERGY_BASE", {})),
            "tension_base": _safe_export(getattr(mod, "TENSION_BASE", {})),
            "drums_nivel": _safe_export(getattr(mod, "DRUMS_NIVEL", {})),
            "focus_default": _safe_export(getattr(mod, "FOCUS_DEFAULT", {})),
            "progresiones": progs,
        }
    tiers = {}
    for nombre in ("_POP", "_HYBRID"):
        tiers[nombre[1:]] = sorted(getattr(validador, nombre, set()))
    try:
        f7 = [{"id": e.get("id"), "nombre": e.get("nombre"),
               "keywords": list(e.get("keywords") or [])}
              for e in (hlib.biblioteca() or {}).values()]
    except Exception:
        f7 = []
    return {
        "ok": True,
        "fingerprint": {
            "contract": contract.CONTRACT_ID,
            "contract_rev": contract.CONTRACT_REV,
            "compiler_version": contract.COMPILER_VERSION,
            "compiler_stage": contract.COMPILER_STAGE,
            "target_schema": contract.TARGET_SCHEMA,
            "jazz_engine_version": getattr(je, "__version__", None),
            "identidad_activa": identidad_activa,
            "identidades_archivadas": list(archivadas),
        },
        "catalogos": {
            "instruments": list(contract.INSTRUMENT_IDS),
            "section_types": list(contract.SECTION_TYPES),
            "drums_ladder": list(contract.DRUMS_LADDER),
            "identities": list(contract.IDENTITIES),
            "accessibilities": list(contract.ACCESSIBILITIES),
            "languages": list(contract.LANGUAGES),
            "resolutions": list(contract.RESOLUTIONS),
        },
        "recetas": recetas,
        "perfiles": {
            "nombres": list(production.nombres()),
            "default": production.DEFAULT_PROFILE,
        },
        "harmony_keywords": list(getattr(hlib, "KEYWORDS", []) or
                                 ["familiar_pop", "melancholic", "nostalgic", "dark_cinematic",
                                  "dream_pop", "alternative", "soulful", "emotional_resolution",
                                  "tension_release", "familiarity_auto"]),
        "niveles_variacion": list(getattr(hlib, "NIVELES_VARIACION", ())),
        "biblioteca_fase7": f7,
        "vocabulario_tiers": tiers,
        "ew_codes": {k: {"familia": v[0], "resumen": v[1]}
                     for k, v in getattr(contract, "EW_CODES", {}).items()},
    }


def task_validate(mods, doc: dict) -> dict:
    validador = mods[1]
    r = validador.validar(doc)
    return {"ok": True, "validacion": {
        "errores": [list(x) for x in r.get("errores", [])],
        "e3xx": [list(x) for x in r.get("e3xx", [])],
        "avisos": [list(x) for x in r.get("avisos", [])],
        "no_verificados": list(r.get("no_verificados", [])),
    }}


def task_compile_preview(mods, doc: dict) -> dict:
    compilador = mods[2]
    r = compilador.compilar(doc)
    proj = r.get("proyecto") or {}
    secs = proj.get("sections") or proj.get("structure") or []
    resumen_secs = []
    for s in secs:
        resumen_secs.append({
            "id": s.get("id"), "name": s.get("name"), "kind": s.get("kind"),
            "bars": s.get("bars"), "chords": s.get("chords"),
            "chord_bars": s.get("chord_bars"),
            "final": bool(s.get("final")),
        })
    tracks = [{"id": t.get("id"), "role": t.get("role"), "enabled": bool(t.get("enabled")),
               "program": t.get("program")} for t in (proj.get("tracks") or [])]
    return {"ok": True, "compila": True,
            "avisos_compilador": [str(a) for a in r.get("avisos", [])],
            "secciones": resumen_secs,
            "tracks": tracks,
            "target_schema": proj.get("schema"),
            "total_bars": sum(int(s.get("bars") or 0) for s in secs)}


def task_parse_chords(mods, symbols: list) -> dict:
    """Valida símbolos literales con el parser REAL del motor (forge/theory).

    El sufijo ``:bars`` ('Dm9:2') NO es parte del acorde: el compilador lo
    separa antes de parsear (misma partición aquí). Devuelve por símbolo:
    ok, error, raíz, bajo, notas del acorde y compases declarados.
    El árbitro es EXACTAMENTE la gramática que aplicará el validador E113.
    """
    theory = importlib.import_module("forge.theory")
    resultados = []
    for sym in symbols:
        head, _, bars_part = str(sym).partition(":")
        r = {"simbolo": sym, "ok": False}
        try:
            bars = float(bars_part) if bars_part else None
            if bars_part and (bars != int(bars) or not (1 <= bars <= 64)):
                raise ValueError(f"compases por acorde inválido: {bars_part!r} "
                                 "(entero 1–64, sintaxis 'Acorde:compases')")
            r["compases"] = int(bars) if bars is not None else None
            c = theory.parse_chord(head)
            r["ok"] = True
            r["acorde"] = head
            r["raiz"] = theory.FLAT_NAMES[int(c.root) % 12]
            r["bajo"] = theory.FLAT_NAMES[int(c.bass) % 12] if getattr(c, "bass", None) is not None else None
            r["notas"] = [theory.FLAT_NAMES[(int(c.root) + st) % 12]
                          for _, st in sorted(c.deg.items(), key=lambda kv: kv[1])]
        except Exception as e:
            r["error"] = f"{type(e).__name__}: {e}"
        resultados.append(r)
    return {"ok": True, "resultados": resultados,
            "validos": all(r["ok"] for r in resultados)}


def _load_produce_module(dmd_path: str):
    """Carga ``scripts/produce.py`` del DMD REAL por RUTA (patrón
    studio/runner.py::_load_produce_module): sin paquete, sin copias.
    El módulo inserta la raíz del DMD en sys.path al importarse."""
    root = Path(dmd_path).resolve()
    p = root / "scripts" / "produce.py"
    if not p.is_file():
        raise FileNotFoundError(f"no se encontró el núcleo de producción: {p}")
    spec = importlib.util.spec_from_file_location("produce", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["produce"] = mod
    spec.loader.exec_module(mod)
    return mod


def task_produce(spec: dict) -> dict:
    """Ejecuta producir_cancion en ESTE proceso hijo aislado.

    Composer nunca importa el DMD: este runner es el ÚNICO punto donde el
    núcleo de producción real se ejecuta. ``verify`` NO se usa (el servidor
    verifica en disco con sha256 + cabecera MThd). Devuelve el dict del
    núcleo + ``ok``; los errores reales del motor viajan con su traceback.
    """
    mod = _load_produce_module(spec["dmd_path"])
    r = mod.producir_cancion(
        spec["doc"],
        production=str(spec.get("production") or "full"),
        seed=spec.get("seed"),
        harmony=spec.get("harmony"),
        out_dir=str(spec["out_dir"]),
        events=bool(spec.get("events", False)),
    )
    r = _safe_export(r)
    r["ok"] = True
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    try:
        mods = _import_dmd(spec["dmd_path"])
        task = spec.get("task")
        if task == "introspect":
            result = task_introspect(mods)
        elif task == "validate":
            result = task_validate(mods, spec["doc"])
        elif task == "compile_preview":
            result = task_compile_preview(mods, spec["doc"])
        elif task == "parse_chords":
            result = task_parse_chords(mods, spec.get("simbolos") or [])
        elif task == "produce":
            result = task_produce(spec)
        else:
            result = {"ok": False, "error": f"tarea desconocida: {task!r}"}
    except Exception as e:
        result = {"ok": False, "error": f"{type(e).__name__}: {e}",
                  "traceback": traceback.format_exc(limit=8)}
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print("## BRIDGE " + ("OK" if result.get("ok") else "ERROR"), flush=True)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
