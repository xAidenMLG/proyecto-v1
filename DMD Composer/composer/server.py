"""API local de DMD COMPOSER (FastAPI) — SOLO 127.0.0.1.

Seguridad (misión §11):
  * Se vincula SIEMPRE a 127.0.0.1 (nunca expuesto a red).
  * Nada del navegador ejecuta comandos: el DMD se usa vía subprocess FIJO
    (dmd_bridge_runner.py) con spec JSON validado y timeouts.
  * Ninguna ruta del cliente decide rutas de disco: ids validados con patrones
    estrictos; escritura atómica; jamás se sobrescribe una generación.
  * El JSON no se ``eval``: solo json.loads + validación con el validador REAL.
  * Límites de tamaño en todo lo que entra.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from composer import __version__
from composer import albums as ALB
from composer import bridge, engine, jobs, manifest as MF, model, store
from composer import randomizer as R
from composer import structure as ST
from composer import harmony as H

app = FastAPI(title="DMD COMPOSER", version=__version__, docs_url="/api/docs")
WEB = Path(__file__).resolve().parent / "static"

MAX_BODY = 512 * 1024   # 512 KB por petición


@app.on_event("startup")
def _startup_recover() -> None:
    """Honestidad de estado al arrancar: trabajos activos persistidos →
    'interrumpido' (el servidor se reinició durante la producción)."""
    try:
        jobs.recover_interrupted()
    except Exception:  # noqa: BLE001 — el arranque nunca depende de jobs/
        pass


def _check_size(raw_len: int):
    if raw_len > MAX_BODY:
        raise HTTPException(413, "cuerpo demasiado grande (límite 512 KB)")


def _pid(pid: str) -> str:
    try:
        return store.safe_pid(pid)
    except store.StoreError as e:
        raise HTTPException(400, str(e))


def _cfg() -> dict:
    f = store.DATA_DIR / "composer_config.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cfg(cfg: dict) -> None:
    store.atomic_write_json(store.DATA_DIR / "composer_config.json", cfg)


def _dmd_path() -> str | None:
    cfg = _cfg()
    return bridge.discover_dmd(store.DATA_DIR, cfg.get("dmd_path"))


def _manifest(refresh: bool = False) -> dict:
    return MF.get_manifest(_dmd_path(), store.DATA_DIR, refresh=refresh)


def _project(pid: str) -> model.ComposerProject:
    p = store.load_project(_pid(pid))
    if not p:
        raise HTTPException(404, "proyecto no encontrado")
    return p


# ------------------------------------------------------------------ sistema
class ConfigBody(BaseModel):
    dmd_path: str | None = None


@app.get("/api/system")
def get_system():
    cfg = _cfg()
    dmd = _dmd_path()
    m = _manifest()
    return {
        "composer_version": __version__,
        "dmd_descubierto": dmd,
        "dmd_configurado": cfg.get("dmd_path"),
        "manifiesto_origen": m.get("origen"),
        "fingerprint": MF.fingerprint_of(m),
        "identidad_activa": (m.get("fingerprint") or {}).get("identidad_activa"),
        "identidades_archivadas": (m.get("fingerprint") or {}).get("identidades_archivadas") or [],
        "catalogos": MF.catalog(m),
    }


@app.put("/api/config")
def put_config(body: ConfigBody):
    cfg = _cfg()
    if body.dmd_path is not None:
        p = Path(body.dmd_path)
        if not (p / "dark_director" / "contract.py").is_file():
            raise HTTPException(400, "la ruta configurada no contiene dark_director/contract.py")
        cfg["dmd_path"] = str(body.dmd_path)
        _save_cfg(cfg)
    return {"ok": True, "dmd_descubierto": _dmd_path(), "system": get_system()}


@app.post("/api/integration/refresh")
def post_refresh():
    m = _manifest(refresh=True)
    return {"ok": bool(m.get("ok")), "origen": m.get("origen"),
            "fingerprint": MF.fingerprint_of(m),
            "catalogos": MF.catalog(m)}


# ------------------------------------------------------------------ proyectos
class ProjectBody(BaseModel):
    name: str
    notes: str = ""


@app.get("/api/projects")
def get_projects():
    return store.list_projects()


@app.post("/api/projects")
def post_project(body: ProjectBody):
    try:
        p = store.create_project(body.name, body.notes)
        return p.to_dict()
    except store.StoreError as e:
        raise HTTPException(400, str(e))


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    return _project(pid).to_dict()


#: Ejes que el contrato EXIGE en el documento: sin modo "libre" posible.
EJES_OBLIGATORIOS = {"identity", "accessibility", "key", "language"}
#: Ejes sin "libre" por diseño de Composer (v1.1, D-07 del manual):
#: harmony_mode es una instrucción de CONSTRUCCIÓN del documento (no es un
#: campo del contrato que se pueda omitir): nativa = no escribir progressions;
#: guiada = escribirlas. "Libre" no tiene significado — antes la API lo
#: aceptaba y lo convertía en guiada de facto (conversión silenciosa).
EJES_SIN_LIBRE = EJES_OBLIGATORIOS | {"harmony_mode"}


def _validar_decision(eje: str, d: dict, cat: dict) -> dict:
    """Valida y COERCIona una decisión (misión §11: nada falla tarde).

    Devuelve la decisión canónica o lanza HTTPException con mensaje claro.
    """
    mode = d.get("mode")
    if mode not in (model.FIXED, model.AUTO, model.FREE):
        raise HTTPException(400, f"modo de decisión inválido para '{eje}': {mode!r} "
                                 "(usa fixed|auto|free)")
    value = d.get("value")

    if mode == model.FREE:
        if eje in EJES_OBLIGATORIOS:
            raise HTTPException(400, f"'{eje}' no puede ser Libre: el contrato exige "
                                     "este campo en todo documento (usa Fijada o Automática)")
        if eje in EJES_SIN_LIBRE:
            raise HTTPException(400, f"'{eje}' no puede ser Libre: es una instrucción de "
                                     "construcción del documento (elige Nativa o Guiada)")
        return model.decision(model.FREE)
    if mode == model.AUTO:
        return model.decision(model.AUTO)

    # ---- validación por eje de los valores fijados ----
    def _int(eje, v, lo, hi):
        try:
            n = int(v)
        except (TypeError, ValueError):
            raise HTTPException(400, f"{eje} fijado debe ser entero: {v!r}")
        if not (lo <= n <= hi):
            raise HTTPException(400, f"{eje} fijado fuera de rango {lo}–{hi}: {n}")
        return n

    if eje == "bpm":
        return model.decision(model.FIXED, _int("bpm", value, 20, 300))
    if eje == "seed":
        n = _int("seed", value, 0, 10 ** 9)
        return model.decision(model.FIXED, n)
    if eje == "harmonic_rhythm_bars":
        return model.decision(model.FIXED, _int("harmonic_rhythm_bars", value, 1, 8))
    if eje == "identity":
        if value not in (cat.get("identities") or []):
            raise HTTPException(400, f"identity fuera del catálogo real: {value!r}")
    elif eje == "accessibility":
        if value not in (cat.get("accessibilities") or []):
            raise HTTPException(400, f"accessibility fuera del catálogo real: {value!r}")
    elif eje == "language":
        if value not in (cat.get("languages") or []):
            raise HTTPException(400, f"language fuera del catálogo real: {value!r}")
    elif eje == "resolution":
        if value not in (cat.get("resolutions") or []):
            raise HTTPException(400, f"resolution fuera del catálogo real: {value!r}")
    elif eje == "key":
        try:
            value = H.parse_key(str(value)).label
        except H.HarmonyError as e:
            raise HTTPException(400, f"tonalidad fijada no válida: {e}")
    elif eje == "harmony_mode":
        if value not in ("native", "guided"):
            raise HTTPException(400, "harmony_mode solo admite native|guided")
    elif eje == "mood":
        if value not in R.MOODS:
            raise HTTPException(400, f"mood fuera del catálogo: {value!r}")
    elif eje == "atmosphere":
        if value not in ("spacious", "medium", "dense"):
            raise HTTPException(400, f"atmosphere no válida: {value!r}")
    elif eje == "groove":
        if value not in ("laid_back", "steady", "driving"):
            raise HTTPException(400, f"groove no válido: {value!r}")
    elif eje == "spaces":
        if value not in model.SPACES_MODES:
            raise HTTPException(400, f"spaces no válido: {value!r} (usa free|suggested|mandatory)")
    elif eje == "protagonist":
        if value not in (None, "", "none") and value not in (cat.get("instruments") or []):
            raise HTTPException(400, f"protagonista fuera del catálogo real de 8: {value!r}")
    elif eje == "production":
        if value not in (None, "") + tuple(cat.get("perfiles") or []):
            raise HTTPException(400, f"perfil de producción no válido: {value!r}")
    elif eje == "ending":
        if value not in ("fade_out", "tape_stop", "none"):
            raise HTTPException(400, f"ending no válido: {value!r}")
    return model.decision(model.FIXED, value)


@app.put("/api/projects/{pid}")
def put_project(pid: str, body: dict):
    p = _project(pid)
    _check_size(len(json.dumps(body, ensure_ascii=False)))
    try:
        if "name" in body:
            p.name = store.safe_name(str(body["name"]))
        if "notes" in body:
            p.notes = str(body["notes"] or "")[:300]
        if "diversity" in body:
            if body["diversity"] not in model.DIVERSITY_LEVELS:
                raise HTTPException(400, "nivel de diversidad no válido")
            p.diversity = body["diversity"]
        if "decisions" in body and isinstance(body["decisions"], dict):
            cat = MF.catalog(_manifest())
            for k, v in body["decisions"].items():
                if k not in model.EJES:
                    raise HTTPException(400, f"eje de decisión desconocido: {k!r}")
                p.decisions[k] = _validar_decision(k, v or {}, cat)
        if "instruments" in body and isinstance(body["instruments"], dict):
            cat = MF.catalog(_manifest())
            p.instruments = {}
            for iid, conf in body["instruments"].items():
                if iid not in cat.get("instruments", []):
                    raise HTTPException(400, f"instrumento fuera del catálogo real: {iid!r}")
                role = str(conf.get("role") or model.ROLE_AUTO)
                if role not in model.INSTRUMENT_ROLES:
                    raise HTTPException(400, f"rol no válido para {iid}: {role!r}")
                dens = conf.get("density")
                if dens is not None:
                    try:
                        dens = float(dens)
                    except (TypeError, ValueError):
                        raise HTTPException(400, f"density de {iid} debe ser número")
                    if not (0.0 <= dens <= 1.0):
                        raise HTTPException(400, f"density de {iid} fuera de 0–1: {dens}")
                if conf.get("enabled") not in (None, True, False):
                    raise HTTPException(400, f"enabled de {iid} debe ser true/false/null")
                p.instruments[str(iid)] = model.InstrumentDecision(
                    role=role, enabled=conf.get("enabled"), density=dens)
        if "sections" in body:
            p.sections = _parse_sections(body["sections"])
        if "harmony_sections" in body and isinstance(body["harmony_sections"], dict):
            p.harmony_sections = {}
            for sid, hh in body["harmony_sections"].items():
                cb = hh.get("chord_bars")
                if cb is not None:
                    try:
                        cb = int(cb)
                    except (TypeError, ValueError):
                        raise HTTPException(400, f"harmony_sections[{sid}].chord_bars debe ser entero")
                    if not (1 <= cb <= 8):
                        raise HTTPException(400, f"harmony_sections[{sid}].chord_bars fuera de 1–8: {cb}")
                res = hh.get("resolution")
                if res is not None and res not in (MF.catalog(_manifest()).get("resolutions") or []):
                    raise HTTPException(400, f"harmony_sections[{sid}].resolution fuera del catálogo real")
                chords = hh.get("chords")
                if chords is not None:
                    chords = str(chords).strip()[:200] or None
                p.harmony_sections[str(sid)] = model.HarmonySection(
                    mode="guided" if hh.get("mode") == "guided" else "native",
                    numerals=(str(hh["numerals"]).strip()[:200] if hh.get("numerals") else None),
                    chords=chords,
                    chord_bars=cb, resolution=res)
        if "production" in body and isinstance(body["production"], dict):
            prod = body["production"]
            cat = MF.catalog(_manifest())
            if prod.get("profile") not in (None,) + tuple(cat["perfiles"]):
                raise HTTPException(400, f"perfil no válido: {prod.get('profile')!r}")
            if prod.get("f7_keyword") not in (None,) + tuple(cat["harmony_keywords"]):
                raise HTTPException(400, f"keyword F7 no válida (opcional, nunca obligatoria)")
            p.production = {
                "profile": prod.get("profile"),
                "f7_keyword": prod.get("f7_keyword"),
                "f7_variation": prod.get("f7_variation"),
                "wav": bool(prod.get("wav", False)),
            }
        store.save_project(p)
        return p.to_dict()
    except store.StoreError as e:
        raise HTTPException(400, str(e))


def _parse_sections(raw) -> list:
    if not isinstance(raw, list):
        raise HTTPException(400, "sections debe ser una lista")
    cat = MF.catalog(_manifest())
    tipos = cat["section_types"]
    drums_ok = cat["drums_ladder"]
    insts = set(cat["instruments"])
    out = []
    for i, s in enumerate(raw):
        try:
            sec = model.Section(
                id=str(s.get("id") or ""), label=str(s.get("label") or s.get("id") or ""),
                type=str(s.get("type") or ""), bars=int(s.get("bars") or 0),
                energy=s.get("energy"), tension=s.get("tension"), density=s.get("density"),
                drums=s.get("drums"), focus=s.get("focus"), active=s.get("active"),
                chord_bars=s.get("chord_bars"), resolution=s.get("resolution"),
                loop_bars=s.get("loop_bars"), final=bool(s.get("final", False)))
        except (TypeError, ValueError):
            raise HTTPException(400, f"sección {i + 1}: datos inválidos")
        if sec.type not in tipos:
            raise HTTPException(400, f"sección {i + 1}: tipo '{sec.type}' fuera del catálogo real")
        for campo in ("energy", "tension", "density"):
            v = getattr(sec, campo)
            if v is not None:
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    raise HTTPException(400, f"sección '{sec.id}': {campo} debe ser número")
                if not (0.0 <= v <= 1.0):
                    raise HTTPException(400, f"sección '{sec.id}': {campo} fuera de 0–1 ({v})")
                setattr(sec, campo, round(v, 4))
        for campo in ("bars", "chord_bars", "loop_bars"):
            v = getattr(sec, campo)
            if v is not None:
                try:
                    setattr(sec, campo, int(v))
                except (TypeError, ValueError):
                    raise HTTPException(400, f"sección '{sec.id}': {campo} debe ser entero")
        if sec.focus is not None:
            if not isinstance(sec.focus, list) or len(sec.focus) > 3:
                raise HTTPException(400, f"sección '{sec.id}': focus debe ser lista de ≤3 instrumentos")
        if sec.active is not None and not isinstance(sec.active, list):
            raise HTTPException(400, f"sección '{sec.id}': active debe ser lista")
        for ref in list(sec.focus or []) + list(sec.active or []):
            if ref not in insts:
                raise HTTPException(400, f"sección '{sec.id}': '{ref}' no está en el catálogo de instrumentos")
        if sec.drums is not None and sec.drums not in drums_ok:
            raise HTTPException(400, f"sección '{sec.id}': drums fuera de la escalera real")
        if sec.resolution is not None and sec.resolution not in cat["resolutions"]:
            raise HTTPException(400, f"sección '{sec.id}': resolution fuera del catálogo real")
        out.append(sec)
    return out


@app.post("/api/projects/{pid}/duplicate")
def post_duplicate(pid: str, body: ProjectBody | None = None):
    try:
        name = body.name if (body and body.name) else None
        return store.duplicate_project(_pid(pid), name).to_dict()
    except store.StoreError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    p = _pid(pid)
    # no se puede borrar un proyecto con una producción MIDI en curso: el
    # rmtree competiría con el hijo aislado y dejaría artefactos huérfanos
    activos = [j for j in jobs.list_jobs(200)
               if j.get("state") in jobs.ACTIVE_STATES
               and str(j.get("scope", "")).startswith(f"produce:{p}:")]
    if activos:
        raise HTTPException(409, "hay una producción MIDI activa para este proyecto: "
                                 "cancélala antes de borrar (job " + activos[0]["jid"] + ")")
    if not store.delete_project(p):
        raise HTTPException(404, "proyecto no encontrado")
    return {"ok": True}


# ------------------------------------------------------------------ previews
class NumeralPreview(BaseModel):
    key: str
    numerals: str
    language: str | None = None


class ChordsBody(BaseModel):
    simbolos: list = Field(default_factory=list)


@app.post("/api/harmony/parse_chords")
def post_parse_chords(body: ChordsBody):
    """Valida acordes literales con el parser REAL del DMD (forge/theory).

    Un solo motor armónico: no hay validador paralelo en Composer. Sin DMD
    descubierto devuelve ok=None con nota honesta (no simula).
    """
    syms = [str(s)[:32] for s in (body.simbolos or []) if str(s).strip()][:64]
    if not syms:
        return {"ok": True, "resultados": [], "validos": True}
    dmd = _dmd_path()
    if not dmd:
        return {"ok": None, "nota": "sin DMD descubierto: no se puede prevalidar "
                                    "(el validador real los juzgará al importar en Studio)",
                "resultados": [], "validos": None}
    r = bridge.parse_chords(dmd, syms)
    if not r.get("ok"):
        raise HTTPException(502, f"puente con el DMD: {r.get('error')}")
    return r


@app.post("/api/harmony/preview")
def post_numeral_preview(body: NumeralPreview):
    """Conversión EN VIVO de grados romanos (módulo C)."""
    _check_size(len(body.numerals) + len(body.key))
    try:
        keyinfo = H.parse_key(body.key)
    except H.HarmonyError as e:
        raise HTTPException(400, str(e))
    try:
        chords = H.resolve_progression(body.numerals, keyinfo)
    except H.HarmonyError as e:
        return {"ok": False, "error": str(e)}
    res = {"ok": True, "key": keyinfo.label, "scale": [H.NOTE_NAMES[pc] for pc in keyinfo.scale],
           "acordes": [{"roman": c.roman, "symbol": c.symbol, "tier": c.tier,
                        "diatonico": c.diatonic, "bars": c.bars} for c in chords],
           "simbolos": [c.symbol for c in chords],
           "avisos": H.tier_warnings(chords, body.language) if body.language else [],
           "no_diatonicos": H.diatonic_warnings(chords)}
    return res


class TemplateBody(BaseModel):
    mood: str
    key: str


@app.post("/api/harmony/templates")
def post_harmony_templates(body: TemplateBody):
    """Plantillas de progresión por tipo de sección (deterministas por mood+key).

    Devuelve POR TIPO FUNCIONAL; el cliente las asigna a las secciones que
    aún no tienen progresión. Nunca inventa tipos: usa los 7 del contrato.
    """
    if body.mood not in R.MOODS:
        raise HTTPException(400, f"mood no válido: {body.mood!r}")
    try:
        H.parse_key(body.key)
    except H.HarmonyError as e:
        raise HTTPException(400, str(e))
    seed = int(hashlib.sha256(f"{body.mood}|{body.key}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    pool = R.PROG_TEMPLATES.get(body.mood, R.PROG_TEMPLATES["neutral"])
    out = {}
    for t in MF.catalog(_manifest())["section_types"]:
        opciones = pool.get(t) or pool.get("verse") or ["i - III - VII - VI"]
        out[t] = opciones[rng.randrange(len(opciones))]
    return {"ok": True, "mood": body.mood, "key": H.parse_key(body.key).label, "por_tipo": out}


class StructurePreview(BaseModel):
    sections: list = Field(default_factory=list)


@app.post("/api/structure/preview")
def post_structure_preview(body: StructurePreview):
    _check_size(len(json.dumps(body.sections, ensure_ascii=False)))
    try:
        secs = _parse_sections(body.sections)
        secs = ST.normalize_sections(secs, _manifest())
    except HTTPException:
        raise
    except (ST.StructureError, store.StoreError) as e:
        return {"ok": False, "error": str(e)}
    tl = ST.timeline(secs, None)
    return {"ok": True, **tl}


# ------------------------------------------------------------------ protagonista
@app.get("/api/projects/{pid}/protagonist/proposal")
def get_protagonist_proposal(pid: str):
    """Propuesta de distribución del protagonista (solo lectura: NO aplica)."""
    from composer import proposal as PR
    p = _project(pid)
    return PR.proponer_distribucion(p, _manifest())


@app.post("/api/projects/{pid}/protagonist/apply")
def post_protagonist_apply(pid: str):
    """Aplica la propuesta (campos reales del contrato, editables después)."""
    from composer import proposal as PR
    p = _project(pid)
    prop = PR.proponer_distribucion(p, _manifest())
    if not prop.get("protagonista"):
        raise HTTPException(400, "sin protagonista fijado (o en Automático con receta sin LEAD)")
    n = PR.aplicar_propuesta(p, prop)
    store.save_project(p)
    return {"ok": True, "cambios_aplicados": n, "estado": p.protagonist_proposal,
            "proyecto": p.to_dict()}


@app.post("/api/projects/{pid}/protagonist/reject")
def post_protagonist_reject(pid: str):
    """Registra el rechazo EXPLÍCITO de la propuesta (no toca campos)."""
    from composer import proposal as PR
    p = _project(pid)
    prop = PR.proponer_distribucion(p, _manifest())
    PR.rechazar_propuesta(p, prop)
    store.save_project(p)
    return {"ok": True, "estado": p.protagonist_proposal, "proyecto": p.to_dict()}


# ------------------------------------------------------------------ composición
class ComposeBody(BaseModel):
    seed: int | None = None
    save: bool = True


@app.post("/api/projects/{pid}/compose")
def post_compose(pid: str, body: ComposeBody):
    p = _project(pid)
    if body.seed is not None and (isinstance(body.seed, bool) or body.seed < 0):
        raise HTTPException(400, "seed debe ser entero ≥ 0")
    r = engine.compose(p, _dmd_path(), _manifest(), seed_override=body.seed, save=body.save)
    status = 200 if r["ok"] else 422
    return JSONResponse(r, status_code=status)


@app.get("/api/projects/{pid}/generations")
def get_generations(pid: str):
    return store.list_generations(_pid(pid))


@app.get("/api/projects/{pid}/generations/{gen_id}")
def get_generation(pid: str, gen_id: str):
    try:
        g = store.get_generation(pid, gen_id)
    except store.StoreError as e:
        raise HTTPException(400, str(e))
    if not g:
        raise HTTPException(404, "generación no encontrada")
    return g


@app.get("/api/projects/{pid}/generations/{gen_id}/files/{fname}")
def get_gen_file(pid: str, gen_id: str, fname: str):
    if fname not in ("doc.json", "song_map.json", "song_map.csv", "generation_manifest.json"):
        raise HTTPException(400, "archivo no permitido")
    g = store.get_generation(_pid(pid), gen_id)
    if not g or fname not in g["archivos"] or g["archivos"][fname] is None:
        raise HTTPException(404, "archivo no encontrado")
    media = "text/csv" if fname.endswith(".csv") else "application/json"
    return PlainTextResponse(g["archivos"][fname], media_type=media,
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ------------------------------------------------------- producción MIDI
#
# El MIDI lo genera el núcleo REAL del DMD (scripts/produce.py::
# producir_cancion) en un hijo AISLADO del puente; Composer solo orquesta,
# persiste y verifica. Reglas: (1) una sola producción activa por generación
# (409); (2) si ya hay MIDI íntegro → 200 idempotente, JAMÁS reescritura;
# (3) la descarga y el estado "ok" SOLO tras verificación en disco (MThd +
# SHA256); (4) nombres/rutas siempre del servidor, nunca del cliente.

class MidiBody(BaseModel):
    events: bool = True


def _gen_exists(pid: str, gen_id: str) -> Path:
    d = store.gen_dir(_pid(pid), gen_id)
    if not d.is_dir():
        raise HTTPException(404, "generación no encontrada")
    return d


def _gen_manifest(d: Path) -> dict:
    f = d / "generation_manifest.json"
    if not f.exists():
        raise HTTPException(404, "generación sin manifest")
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(500, f"manifest ilegible: {e}")


def _midi_worker(pid: str, gen_id: str, events_requested: bool):
    """Trabajador del job 'produce': puente aislado + verificación + registro."""
    def _run(ctx: dict) -> dict:
        d = store.gen_dir(pid, gen_id)
        m = _gen_manifest(d)
        doc_f = d / "doc.json"
        if not doc_f.exists():
            raise RuntimeError("la generación no tiene doc.json")
        doc = json.loads(doc_f.read_text(encoding="utf-8"))
        obra = str(m.get("obra") or pid)
        nombre = store.midi_name(pid, gen_id, obra)
        out_dir = d / "midi" / nombre
        # parámetros de producción: los que la generación DECLARÓ (perfil,
        # seed_used y F7 opcional) — el doc y la seed manda, nunca el cliente
        prod = m.get("produccion") or {}
        cat = MF.catalog(_manifest())
        perfil = prod.get("perfil") or "full"
        if perfil not in (cat.get("perfiles") or []):
            perfil = "full"
        seed = m.get("seed_used")
        harmony = None
        if prod.get("f7_keyword"):
            harmony = {"keyword": str(prod["f7_keyword"])}
            if prod.get("f7_variation"):
                harmony["variacion"] = str(prod["f7_variation"])
        ctx["log"](f"produciendo con el núcleo real: perfil={perfil} seed={seed} "
                   f"events={events_requested} → {out_dir}")
        store.prepare_midi_dir(pid, gen_id, nombre)
        proc = bridge.produce_start(_dmd_path(), doc, str(out_dir),
                                    production=perfil, seed=seed, harmony=harmony,
                                    events=events_requested)
        ctx["register_process"](proc)
        t0 = time.time()
        while proc.alive():
            if ctx["cancel_event"].is_set():
                proc.cancel()
            time.sleep(0.3)
            if time.time() - t0 > 300:
                proc.cancel()
                raise RuntimeError("timeout de producción (300s): proceso cancelado")
        r = proc.wait(timeout=30)
        if ctx["cancel_event"].is_set():
            return {"ok": False, "cancelado": True}
        if not r.get("ok"):
            tail = str(r.get("traceback") or "")[-600:]
            raise RuntimeError(f"el núcleo de producción rechazó el documento: "
                               f"{r.get('error')}" + (f" | {tail}" if tail else ""))
        ctx["progress"]({"sha256": r.get("sha256"), "perfil": perfil, "seed": seed})
        block = engine.registrar_produccion(pid, gen_id, r, perfil=perfil,
                                            seed=seed, harmony=harmony, nombre=nombre)
        ctx["log"](f"MIDI registrado y verificado: sha256={block['sha256'][:16]}…")
        return {"ok": True, "midi": block}
    return _run


def _estado_midi_payload(pid: str, gen_id: str) -> dict:
    d = store.gen_dir(pid, gen_id)
    if not d.is_dir():
        raise HTTPException(404, "generación no encontrada")
    integ = store.midi_integrity(pid, gen_id)
    job = jobs.find_by_scope(f"produce:{pid}:{gen_id}")
    state = integ["estado"]
    if job and job.get("state") in jobs.ACTIVE_STATES:
        state = "en_cola" if job.get("state") == "queued" else "generando"
    elif state == "sin_midi" and job:
        state = {"error": "error", "cancelado": "cancelado", "timeout": "timeout",
                 "interrumpido": "interrumpido"}.get(job.get("state"), state)
    return {"pid": pid, "gen_id": gen_id, "state": state,
            "detalle": integ.get("detalle"), "midi": store.read_midi_block(pid, gen_id),
            "artefactos": store.list_midi_artifacts(pid, gen_id),
            "job": job}


@app.post("/api/projects/{pid}/generations/{gen_id}/midi")
def post_gen_midi(pid: str, gen_id: str, body: MidiBody | None = None):
    pid = _pid(pid)
    _gen_exists(pid, gen_id)
    events_requested = bool(body.events) if body is not None else True
    integ = store.midi_integrity(pid, gen_id)
    if integ["estado"] == "ok":
        block = store.read_midi_block(pid, gen_id)
        return {"state": "ok", "idempotente": True, "midi": block,
                "nota": "esta generación ya tiene un MIDI verificado: no se reescribe"}
    if integ["estado"] == "integridad_error":
        raise HTTPException(409, f"el MIDI registrado no pasó la verificación de "
                                 f"integridad ({integ['detalle']}): usa una generación "
                                 "nueva en lugar de reescribir esta")
    if not _dmd_path():
        raise HTTPException(400, "sin DMD descubierto: no se puede producir MIDI "
                                 "(configura dmd_path en el sistema)")
    try:
        j = jobs.submit("produce", f"produce:{pid}:{gen_id}",
                        _midi_worker(pid, gen_id, events_requested), timeout=330)
    except jobs.JobBusy as e:
        raise HTTPException(409, f"ya hay una producción activa para esta generación ({e})")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return JSONResponse({"jid": j["jid"], "state": j["state"], "pid": pid,
                         "gen_id": gen_id, "events": events_requested}, status_code=202)


@app.get("/api/projects/{pid}/generations/{gen_id}/midi")
def get_gen_midi(pid: str, gen_id: str):
    return _estado_midi_payload(_pid(pid), gen_id)


@app.post("/api/projects/{pid}/generations/{gen_id}/midi/cancel")
def post_gen_midi_cancel(pid: str, gen_id: str):
    j = jobs.find_by_scope(f"produce:{_pid(pid)}:{gen_id}", only_active=True)
    if not j:
        return {"ok": False, "nota": "no hay producción activa para esta generación"}
    return {"ok": jobs.cancel(j["jid"])}


@app.get("/api/projects/{pid}/generations/{gen_id}/midi/download")
def get_gen_midi_download(pid: str, gen_id: str):
    pid = _pid(pid)
    integ = store.midi_integrity(pid, gen_id)
    if integ["estado"] == "sin_midi":
        raise HTTPException(404, "esta generación aún no tiene MIDI")
    if integ["estado"] != "ok":
        raise HTTPException(409, f"el MIDI no pasó la verificación ({integ['detalle']})")
    block = store.read_midi_block(pid, gen_id)
    ruta = Path((block.get("rutas") or {}).get("midi") or "")
    p = store._contained(ruta, store.gen_dir(pid, gen_id))
    if p is None or not p.is_file():
        raise HTTPException(404, "archivo MIDI no encontrado")
    nombre = block.get("nombre") or gen_id
    return FileResponse(p, media_type="audio/midi",
                        headers={"Content-Disposition":
                                 f'attachment; filename="{nombre}.mid"'})


@app.get("/api/projects/{pid}/generations/{gen_id}/events")
def get_gen_events(pid: str, gen_id: str):
    """events.json del gen (datos del Player WebAudio; NO es MIDI)."""
    pid = _pid(pid)
    block = store.read_midi_block(pid, gen_id)
    ruta = (block or {}).get("rutas", {}).get("events")
    if not ruta:
        raise HTTPException(404, "esta generación no tiene events.json (prodúcelo con events=on)")
    p = store._contained(Path(str(ruta)), store.gen_dir(pid, gen_id))
    if p is None or not p.is_file():
        raise HTTPException(404, "events.json no encontrado")
    return PlainTextResponse(p.read_text(encoding="utf-8"), media_type="application/json")


_MIDI_ARTIFACTS = ("evidencia.json", "config_efectiva.json")


@app.get("/api/projects/{pid}/generations/{gen_id}/midi/artifacts/{fname}")
def get_gen_midi_artifact(pid: str, gen_id: str, fname: str):
    pid = _pid(pid)
    if fname not in _MIDI_ARTIFACTS:
        raise HTTPException(400, "artefacto no permitido (whitelist: "
                                 + ", ".join(_MIDI_ARTIFACTS) + ")")
    block = store.read_midi_block(pid, gen_id)
    nombre = (block or {}).get("nombre")
    if not nombre:
        raise HTTPException(404, "sin producción MIDI registrada")
    p = store._contained(store.gen_dir(pid, gen_id) / "midi" / nombre / fname,
                         store.gen_dir(pid, gen_id))
    if p is None or not p.is_file():
        raise HTTPException(404, "artefacto no encontrado")
    return PlainTextResponse(p.read_text(encoding="utf-8"), media_type="application/json",
                             headers={"Content-Disposition":
                                      f'attachment; filename="{fname}"'})


@app.get("/api/jobs/{jid}")
def get_job(jid: str):
    try:
        return jobs.get(jid)
    except (jobs.JobNotFound, ValueError) as e:
        raise HTTPException(404, str(e))


@app.post("/api/jobs/{jid}/cancel")
def post_job_cancel(jid: str):
    try:
        return {"ok": jobs.cancel(jid)}
    except (jobs.JobNotFound, ValueError) as e:
        raise HTTPException(404, str(e))


@app.get("/api/jobs")
def get_jobs(limit: int = 50):
    return jobs.list_jobs(limit)


# ------------------------------------------------------------------ álbumes
class AlbumBody(BaseModel):
    name: str
    tracks: int
    pid: str


@app.get("/api/albums")
def get_albums():
    return ALB.list_albums()


@app.get("/api/albums/{album_id}")
def get_album(album_id: str):
    a = ALB.load_album(album_id)
    if not a:
        raise HTTPException(404, "álbum no encontrado")
    return a


@app.post("/api/albums")
def post_album(body: AlbumBody):
    try:
        base = _project(body.pid)
        return ALB.new_album(body.name, body.tracks, base)
    except (store.StoreError, ALB.AlbumError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/albums/{album_id}/tracks/{n}/generate")
def post_album_track(album_id: str, n: int):
    try:
        proj = ALB.track_project(album_id, n)
    except (store.StoreError, ALB.AlbumError) as e:
        raise HTTPException(400, str(e))
    r = engine.compose(proj, _dmd_path(), _manifest(), save=True)
    if r.get("ok"):
        plan = ALB.load_album(album_id)
        t = plan["pistas"][n - 1]
        t["estado"] = "lista"
        t["gen"] = r["generation"]["gen_id"]
        t["pid"] = proj.pid
        t["doc_sha256"] = r["generation"]["sha256_doc"]
        ALB.save_album(plan)
    return JSONResponse(r, status_code=200 if r["ok"] else 422)


@app.post("/api/albums/{album_id}/generate_all")
def post_album_generate_all(album_id: str):
    """Genera TODAS las pistas pendientes en orden (determinista; reanuda:
    las pistas 'lista' no se regeneran). Devuelve el resultado por pista y
    el informe de diversidad. Sin MIDI: el pipeline de DMD es el productor."""
    try:
        res = ALB.generate_all(album_id, _dmd_path(), _manifest())
    except (store.StoreError, ALB.AlbumError) as e:
        raise HTTPException(400, str(e))
    return JSONResponse(res, status_code=200 if res.get("ok") else 207)


@app.get("/api/albums/{album_id}/informe")
def get_album_informe(album_id: str):
    try:
        return ALB.informe_album(album_id)
    except (store.StoreError, ALB.AlbumError) as e:
        raise HTTPException(400, str(e))


# ------------------------------------------ producción MIDI del álbum
#
# El lote lo ejecuta el ORQUESTADOR EXISTENTE del DMD (album/orquestador.py)
# en un subprocess aislado y cancelable: Composer materializa el spec
# dmd-album/1 con los docs de cada pista y delega. Estados por pista leídos
# del estado.json crash-safe del orquestador; reintentos por pista con
# --regen; reanudación re-ejecutando (el orquestador salta las pistas ok).

def _album_worker(album_id: str, regen: Optional[list] = None):
    def _run(ctx: dict) -> dict:
        dmd = _dmd_path()
        if not dmd:
            raise RuntimeError("sin DMD descubierto: no se puede producir el álbum")
        spec = ALB.materializar_spec(album_id)
        out_dir = ALB.production_dir(album_id)
        modo = "regen " + ",".join(map(str, regen)) if regen else "lote completo"
        ctx["log"](f"orquestador del DMD sobre {spec['album']!r} ({modo}): "
                   f"{len(spec['pistas'])} pistas")
        proc = bridge.album_start(dmd, str(out_dir / "album.json"), str(out_dir),
                                  regen=regen)
        ctx["register_process"](proc)
        t0 = time.time()
        last_n = -1
        while proc.alive():
            if ctx["cancel_event"].is_set():
                proc.cancel()
                break
            try:
                est = ALB.estado_produccion(album_id)
                if est["ok"] != last_n:
                    last_n = est["ok"]
                    ctx["progress"]({"ok": est["ok"], "total": est["total"]})
                    ctx["log"](f"progreso del orquestador: {est['ok']}/{est['total']} pistas ok")
            except Exception:  # noqa: BLE001 — estado aún no escrito
                pass
            time.sleep(1.0)
            if time.time() - t0 > 1800:
                proc.cancel()
                raise RuntimeError("timeout del lote del álbum (1800s): proceso cancelado")
        if ctx["cancel_event"].is_set():
            return {"ok": False, "cancelado": True,
                    "estado": ALB.estado_produccion(album_id),
                    "nota": "lote cancelado: las pistas ya producidas conservan su MIDI "
                            "(reanuda re-ejecutando)"}
        est = ALB.estado_produccion(album_id)
        ctx["log"](f"lote terminado: {est['ok']}/{est['total']} pistas ok")
        return {"ok": est["ok"] == est["total"], "estado": est}
    return _run


def _album_activo(album_id: str):
    try:
        aid = store.safe_pid(album_id)
    except store.StoreError as e:
        raise HTTPException(400, str(e))
    if not ALB.load_album(aid):
        raise HTTPException(404, "álbum no encontrado")
    return aid


@app.post("/api/albums/{album_id}/produce_all")
def post_album_produce_all(album_id: str):
    aid = _album_activo(album_id)
    if not _dmd_path():
        raise HTTPException(400, "sin DMD descubierto: no se puede producir el álbum")
    try:
        j = jobs.submit("album", f"album:{aid}", _album_worker(aid), timeout=1900)
    except jobs.JobBusy as e:
        raise HTTPException(409, f"ya hay una producción activa para este álbum ({e})")
    except (ALB.AlbumError, ValueError) as e:
        raise HTTPException(400, str(e))
    return JSONResponse({"jid": j["jid"], "state": j["state"], "album_id": aid},
                        status_code=202)


@app.post("/api/albums/{album_id}/tracks/{n}/midi")
def post_album_track_midi(album_id: str, n: int):
    """Regenera UNA pista (--regen del orquestador real)."""
    aid = _album_activo(album_id)
    try:
        tid = ALB.track_id(ALB.load_album(aid), n)
    except ALB.AlbumError as e:
        raise HTTPException(400, str(e))
    try:
        j = jobs.submit("album", f"album:{aid}", _album_worker(aid, regen=[tid]),
                        timeout=1900)
    except jobs.JobBusy as e:
        raise HTTPException(409, f"ya hay una producción activa para este álbum ({e})")
    except (ALB.AlbumError, ValueError) as e:
        raise HTTPException(400, str(e))
    return JSONResponse({"jid": j["jid"], "state": j["state"], "album_id": aid,
                         "pista": n, "track_id": tid}, status_code=202)


@app.get("/api/albums/{album_id}/production")
def get_album_production(album_id: str):
    aid = _album_activo(album_id)
    est = ALB.estado_produccion(aid)
    job = jobs.find_by_scope(f"album:{aid}")
    est["job"] = job
    if job and job.get("state") in jobs.ACTIVE_STATES:
        est["state"] = "generando"
    elif est["ok"] == est["total"]:
        est["state"] = "ok"
    else:
        est["state"] = "parcial" if est["ok"] else "sin_midi"
    return est


@app.post("/api/albums/{album_id}/cancel")
def post_album_cancel(album_id: str):
    aid = _album_activo(album_id)
    j = jobs.find_by_scope(f"album:{aid}", only_active=True)
    if not j:
        return {"ok": False, "nota": "no hay producción activa para este álbum"}
    return {"ok": jobs.cancel(j["jid"])}


@app.get("/api/albums/{album_id}/tracks/{n}/download")
def get_album_track_download(album_id: str, n: int):
    aid = _album_activo(album_id)
    p = ALB.ruta_midi_pista(aid, n)
    if not p:
        raise HTTPException(404, "la pista aún no tiene MIDI producido")
    est = ALB.estado_produccion(aid)
    fila = next((t for t in est["pistas"] if t["n"] == int(n)), {})
    if fila.get("estado_midi") == "fallo":
        raise HTTPException(409, "la pista quedó en fallo según el orquestador")
    return FileResponse(p, media_type="audio/midi",
                        headers={"Content-Disposition":
                                 f'attachment; filename="{p.stem}.mid"'})


@app.get("/api/albums/{album_id}/tracks/{n}/events")
def get_album_track_events(album_id: str, n: int):
    """events.json de una pista de álbum (bajo demanda, verificado contra la
    evidencia del orquestador; se genera la primera vez y queda en caché)."""
    aid = _album_activo(album_id)
    if not _dmd_path():
        raise HTTPException(400, "sin DMD descubierto: no se pueden generar eventos")
    try:
        p = ALB.generar_events_pista(aid, n, _dmd_path())
    except (ALB.AlbumError, store.StoreError) as e:
        raise HTTPException(409, str(e))
    if not p or not p.is_file():
        raise HTTPException(404, "events no disponibles para esta pista")
    return PlainTextResponse(p.read_text(encoding="utf-8"), media_type="application/json")


# ------------------------------------------------------------------ estáticos
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/favicon.ico")
def favicon():
    f = WEB / "favicon.svg"
    if f.exists():
        return FileResponse(f, media_type="image/svg+xml")
    raise HTTPException(404)
