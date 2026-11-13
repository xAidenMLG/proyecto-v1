"""API local de DMD STUDIO (FastAPI) — solo localhost.

Reglas de seguridad:
  * Se vincula SIEMPRE a 127.0.0.1 (nunca expuesto a la red).
  * Nada del navegador ejecuta comandos: el pipeline se lanza como subproceso
    fijo (``python -m studio.runner``) con un spec JSON validado.
  * Ninguna ruta del cliente decide rutas de disco: los ids se validan contra
    patrones estrictos (sin traversal) y todas las salidas viven bajo
    ``studio_data/``.
  * El JSON del editor no se ``eval``: solo ``json.loads`` y validación con el
    validador REAL del motor.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dark_director import compilador, validador
from jazz_engine import production as production_profiles
from jazz_engine import harmony_library as hlib

from studio import __version__
from studio import capabilities as CAP
from studio import jobs as JOBS
from studio import projects as P
from studio import settings as S

app = FastAPI(title="DMD STUDIO", version=__version__, docs_url="/api/docs")

WEB = Path(__file__).resolve().parent / "static"

_PID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
_GEN_RE = re.compile(r"^gen_\d{4,}$")
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$")
# nombres visibles: se permiten acentos/unicode; se rechazan los caracteres
# peligrosos de ruta y los de control (los ids de carpeta salen de slugify).
_NAME_BAD = re.compile(r"[\\/:*?\"<>|\x00-\x1f]")
_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}\.(mid|wav|mp3|json)$")
_JSON_ARTIFACTS = ("doc.json", "config_efectiva.json", "evidencia.json", "job.json",
                   "job_spec.json")


def _pid(pid: str) -> str:
    if not _PID_RE.fullmatch(pid or ""):
        raise HTTPException(400, "id de proyecto no válido")
    return pid


def _gen(gen_id: str) -> str:
    if not _GEN_RE.fullmatch(gen_id or ""):
        raise HTTPException(400, "id de generación no válido")
    return gen_id


def _safe_name(name: str) -> str:
    n = (name or "").strip()
    if not n or len(n) > 64 or n.startswith(".") or _NAME_BAD.search(n):
        raise HTTPException(400, "nombre no válido (sin / \\ : * ? \" < > | ni control)")
    return n


def _err(status: int, msg: str):
    return JSONResponse({"error": msg}, status_code=status)


class DocBody(BaseModel):
    doc: dict


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    doc: dict | None = None
    production: dict | None = None


class GenerateBody(BaseModel):
    production: str | None = None
    seed: int | None = None
    harmony: dict | None = None
    wav: bool | None = None
    out_name: str | None = None
    doc: dict | None = None          # edición no guardada (se valida antes de usar)
    validate_first: bool = True


class SettingsPatch(BaseModel):
    soundfont_path: str | None = None
    fluidsynth_path: str | None = None
    port: int | None = None


# --------------------------------------------------------------------- sistema
@app.get("/api/capabilities")
def get_capabilities():
    return CAP.capabilities()


@app.get("/api/system")
def get_system():
    s = S.load_settings()
    return {
        "studio_version": __version__,
        "contrato": CAP.capabilities()["contrato"],
        "settings": s,
        "audio": CAP.audio_status(),
        "data_dir": str(S.DATA_DIR),
        "proyectos_dir": str(S.PROJECTS_DIR),
    }


@app.get("/api/settings")
def get_settings():
    return S.load_settings()


@app.put("/api/settings")
def put_settings(patch: SettingsPatch):
    return S.save_settings(patch.model_dump(exclude_none=True))


# ------------------------------------------------------------------- proyectos
@app.get("/api/projects")
def get_projects():
    return P.list_projects()


@app.post("/api/projects")
def post_project(body: ProjectCreate):
    try:
        name = _safe_name(body.name)
        return P.create_project(name, body.description or "")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    p = P.get_project(_pid(pid))
    if not p:
        raise HTTPException(404, "proyecto no encontrado")
    return p


@app.put("/api/projects/{pid}")
def put_project(pid: str, body: ProjectPatch):
    try:
        if body.name is not None:
            _safe_name(body.name)
        return P.save_project(_pid(pid), body.model_dump(exclude_none=True))
    except FileNotFoundError:
        raise HTTPException(404, "proyecto no encontrado")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/projects/{pid}/duplicate")
def post_duplicate(pid: str, body: ProjectCreate | None = None):
    try:
        name = _safe_name(body.name) if (body and body.name) else None
        return P.duplicate_project(_pid(pid), name)
    except FileNotFoundError:
        raise HTTPException(404, "proyecto no encontrado")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    try:
        ok = P.delete_project(_pid(pid))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ok:
        raise HTTPException(404, "proyecto no encontrado")
    return {"ok": True}


# ----------------------------------------------------------------- validación
def _validar_doc(doc: dict) -> dict:
    """Validación con el validador REAL del motor (única fuente de verdad)."""
    try:
        v = validador.validar(doc)
    except Exception as e:
        return {"errores": [["E101", f"no se pudo validar: {type(e).__name__}: {e}"]],
                "e3xx": [], "avisos": [], "no_verificados": []}
    return {
        "errores": [list(x) for x in v.get("errores", [])],
        "e3xx": [list(x) for x in v.get("e3xx", [])],
        "avisos": [list(x) for x in v.get("avisos", [])],
        "no_verificados": list(v.get("no_verificados", [])),
    }


@app.post("/api/validate")
def post_validate(body: DocBody):
    return _validar_doc(body.doc)


@app.post("/api/compile-preview")
def post_compile_preview(body: DocBody):
    """Compila SIN renderizar (mismo compilador real): errores y avisos W."""
    out = {"validacion": _validar_doc(body.doc)}
    v = out["validacion"]
    if v["errores"]:
        out["compila"] = False
        return out
    try:
        r = compilador.compilar(json.loads(json.dumps(body.doc, ensure_ascii=False)))
    except compilador.DirectorInvalido as e:
        out["compila"] = False
        out["error_compilador"] = str(e)
        return out
    except compilador.StrictBloqueante as e:
        out["compila"] = False
        out["error_compilador"] = str(e)
        out["strict"] = True
        return out
    out["compila"] = True
    proj = r.get("proyecto") or {}
    g = (proj.get("global") or proj.get("context") or {})
    secs = proj.get("structure") or proj.get("sections") or []
    out["resumen"] = {
        "avisos_compilador": r.get("avisos", []),
        "secciones": len(secs) if isinstance(secs, list) else None,
    }
    return out


# ----------------------------------------------------------------- generación
def _validate_harmony(h: dict) -> dict:
    if not isinstance(h, dict):
        raise HTTPException(400, "harmony debe ser un objeto")
    clean = {}
    if h.get("keyword"):
        clean["keyword"] = str(h["keyword"])
    if h.get("id"):
        clean["id"] = str(h["id"])
    if h.get("variacion"):
        if h["variacion"] not in hlib.NIVELES_VARIACION:
            raise HTTPException(400, f"variacion no válida: {h['variacion']!r}")
        clean["variacion"] = h["variacion"]
    if h.get("seed") is not None:
        try:
            clean["seed"] = int(h["seed"])
        except (TypeError, ValueError):
            raise HTTPException(400, "harmony.seed debe ser entero")
    if not clean:
        raise HTTPException(400, "harmony vacío")
    if "keyword" in clean:
        lib = hlib.biblioteca()
        try:
            hlib.buscar_por_keyword(lib, clean["keyword"])
        except KeyError as e:
            raise HTTPException(400, str(e))
    return clean


@app.post("/api/projects/{pid}/generate")
def post_generate(pid: str, body: GenerateBody):
    pid = _pid(pid)
    prod = body.production or (P.get_project(pid) or {}).get("production", {}).get("profile")
    if prod not in production_profiles.nombres():
        raise HTTPException(400, f"perfil de producción no válido: {prod!r} "
                                 f"(válidos: {', '.join(production_profiles.nombres())})")
    if body.seed is not None and (isinstance(body.seed, bool) or body.seed < 0):
        raise HTTPException(400, "seed debe ser un entero ≥ 0")

    doc = body.doc
    if body.validate_first:
        target = doc if doc is not None else (P.get_project(pid) or {}).get("doc")
        if not isinstance(target, dict):
            raise HTTPException(404, "proyecto no encontrado")
        v = _validar_doc(target)
        if v["errores"]:
            return JSONResponse({"error": "validación previa fallida", "validacion": v},
                                status_code=422)
        if doc is not None:  # el doc no guardado además debe COMPILAR
            try:
                compilador.compilar(json.loads(json.dumps(doc, ensure_ascii=False)))
            except (compilador.DirectorInvalido, compilador.StrictBloqueante) as e:
                return JSONResponse({"error": f"el compilador rechaza el documento: {e}",
                                     "validacion": v}, status_code=422)

    harmony = _validate_harmony(body.harmony) if body.harmony else None
    try:
        job = JOBS.start_job(pid, {
            "production": prod,
            "seed": body.seed,
            "harmony": harmony,
            "wav": body.wav,
            "out_name": body.out_name,
            "doc": doc,
        })
    except JOBS.JobBusy as e:
        return JSONResponse({"error": f"ya hay una generación en marcha ({e}); "
                                     "solo se permite una a la vez"}, status_code=409)
    except FileNotFoundError:
        raise HTTPException(404, "proyecto no encontrado")
    return job


@app.get("/api/jobs")
def get_jobs(pid: str | None = None):
    return JOBS.list_jobs(pid)


@app.get("/api/jobs/{jid}")
def get_job(jid: str):
    try:
        return JOBS.get_job(jid)
    except JOBS.JobNotFound:
        raise HTTPException(404, "trabajo no encontrado")


@app.post("/api/jobs/{jid}/cancel")
def post_cancel(jid: str):
    try:
        return JOBS.cancel_job(jid)
    except JOBS.JobNotFound:
        raise HTTPException(404, "trabajo no encontrado")


# ------------------------------------------------------- artefactos y archivos
@app.get("/api/projects/{pid}/generations/{gen_id}/logfile")
def get_gen_logfile(pid: str, gen_id: str):
    pid, gen_id = _pid(pid), _gen(gen_id)
    f = P.gen_dir(pid, gen_id) / "job.log"
    if not f.exists():
        raise HTTPException(404, "log no encontrado")
    return FileResponse(f, media_type="text/plain; charset=utf-8")


@app.get("/api/projects/{pid}/export")
def get_export(pid: str):
    p = P.get_project(_pid(pid))
    if not p:
        raise HTTPException(404, "proyecto no encontrado")
    data = json.dumps(p.get("doc") or {}, ensure_ascii=False, indent=2)
    fname = f"{pid}.doc.json"
    return JSONResponse(content=json.loads(data), headers={
        "Content-Disposition": f'attachment; filename="{fname}"'})


@app.get("/api/projects/{pid}/generations/{gen_id}")
def get_generation(pid: str, gen_id: str):
    pid, gen_id = _pid(pid), _gen(gen_id)
    gdir = P.gen_dir(pid, gen_id)
    if not gdir.exists():
        raise HTTPException(404, "generación no encontrada")
    out = {"gen_id": gen_id, "carpetas": [], "archivos": {}}
    # JSON de control a nivel de generación
    for fname in ("job_spec.json", "job.log"):
        f = gdir / fname
        if f.exists():
            out["archivos"][fname] = (json.loads(f.read_text(encoding="utf-8"))
                                      if fname.endswith(".json") else {"_log": True})
    # contenido de las carpetas de salida (produce escribe aquí)
    for d in sorted(gdir.iterdir()):
        if not d.is_dir():
            continue
        out["carpetas"].append(d.name)
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            key = f"{d.name}/{f.name}"
            if f.suffix == ".json":
                try:
                    out["archivos"][key] = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    out["archivos"][key] = {"_error": "JSON ilegible"}
            else:
                out["archivos"][key] = {"bytes": f.stat().st_size}
    return out


@app.get("/api/projects/{pid}/generations/{gen_id}/files/{fname}")
def get_gen_file(pid: str, gen_id: str, fname: str):
    pid, gen_id = _pid(pid), _gen(gen_id)
    if fname not in _JSON_ARTIFACTS:
        raise HTTPException(400, "archivo no permitido")
    f = P.gen_dir(pid, gen_id) / fname
    if not f.exists():
        raise HTTPException(404, "archivo no encontrado")
    return FileResponse(f, media_type="application/json")


@app.get("/api/projects/{pid}/audio/{gen_id}/{out_name}/{fname}")
def get_audio(pid: str, gen_id: str, out_name: str, fname: str):
    pid, gen_id = _pid(pid), _gen(gen_id)
    if not _NAME_RE.fullmatch(out_name or ""):
        raise HTTPException(400, "nombre de carpeta no válido")
    if not _FILE_RE.fullmatch(fname or ""):
        raise HTTPException(400, "archivo no permitido")
    f = P.gen_dir(pid, gen_id) / out_name / fname
    if not f.is_file():
        raise HTTPException(404, "archivo no encontrado")
    media = {"mid": "audio/midi", "wav": "audio/wav", "mp3": "audio/mpeg",
             "json": "application/json"}[fname.rsplit(".", 1)[1]]
    return FileResponse(f, media_type=media, filename=fname)


# --------------------------------------------------------------------- estáticos
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
