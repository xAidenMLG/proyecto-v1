"""Almacén de proyectos de DMD STUDIO.

Un proyecto es una carpeta bajo ``studio_data/projects/<pid>/``:

    project.json                      → meta + doc dark-director/1 + config de producción + historial
    generations/<gen_id>/             → artefactos reales del pipeline (doc.json, config_efectiva.json,
                                       <nombre>.mid, evidencia.json, wav, job.json)

Persistencia por archivos y metadatos, sin base de datos. Un corte de luz
durante una generación deja la carpeta del trabajo con su log: nunca corrompe
el proyecto (el historial solo se actualiza al terminar).
"""
from __future__ import annotations

import datetime
import json
import shutil
import uuid
from pathlib import Path

from . import settings as S


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _valid_pid(pid: str) -> bool:
    import re
    return bool(pid) and bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,47}", pid)) and \
        "/" not in pid and "\\" not in pid and ".." not in pid


def _pdir(pid: str) -> Path:
    if not _valid_pid(pid):
        raise ValueError(f"id de proyecto no válido: {pid!r}")
    return S.PROJECTS_DIR / pid


def _read_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)  # escritura atómica: nunca un project.json a medias


# Plantilla por defecto: documento mínimo VÁLIDO según dark-director/1 rev 3.2
# (dos secciones, identidad dark_triphop × balanced). La validación real es la
# del validador del motor; esta plantilla pasa el validador.
DEFAULT_DOC = {
    "schema": "dark-director/1",
    "meta": {"title": "Nueva composición", "notes": ""},
    "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
    "global": {"bpm": 86, "seed": 2026},
    "harmony": {
        "key": "D minor",
        "language": "pop_dream_pop",
        "harmonic_rhythm_bars": 1,
    },
    "instruments": {},
    "structure": [
        {"id": "verse_1", "type": "verse", "bars": 16, "energy": 0.45, "tension": 0.35,
         "density": 0.45, "focus": ["sax_tenor", "drums"], "drums": "groove"},
        {"id": "chorus_1", "type": "chorus", "bars": 16, "energy": 0.75, "tension": 0.5,
         "density": 0.65, "focus": ["sax_tenor", "drums", "bass"], "drums": "heavy",
         "final": True},
    ],
    "development": {},
    "x_studio_creado": "",
}


def DEFAULT_PRODUCTION() -> dict:
    return {
        "profile": "full",           # identificador exacto admitido por el backend
        "seed": None,                # None → usa global.seed del documento
        "harmony": None,             # {"keyword"?, "id"?, "variacion"?, "seed"?} — Fase 7, opcional
        "render_wav": False,
        "out_name": "",              # vacío → slug del título
    }


def new_pid(name: str) -> str:
    base = S.slugify(name)
    pid = base
    n = 2
    while (_pdir(pid) if _valid_pid(pid) else S.PROJECTS_DIR / pid).exists():
        pid = f"{base}_{n}"
        n += 1
    return pid


def create_project(name: str, description: str = "", doc: dict | None = None,
                   production: dict | None = None) -> dict:
    if not name or not str(name).strip():
        raise ValueError("el proyecto necesita un nombre")
    pid = new_pid(name)
    d = json.loads(json.dumps(doc, ensure_ascii=False)) if isinstance(doc, dict) \
        else json.loads(json.dumps(DEFAULT_DOC, ensure_ascii=False))
    d.setdefault("schema", "dark-director/1")
    d.setdefault("meta", {})
    d["meta"]["title"] = str(name).strip()
    d.setdefault("x_studio_creado", _now())
    proj = {
        "id": pid,
        "name": str(name).strip(),
        "description": description or "",
        "created_utc": _now(),
        "updated_utc": _now(),
        "doc": d,
        "production": {**DEFAULT_PRODUCTION(), **(production or {})},
        "history": [],
        "seq": 0,
    }
    _write_json(_pdir(pid) / "project.json", proj)
    return proj


def get_project(pid: str) -> dict | None:
    return _read_json(_pdir(pid) / "project.json")


def list_projects() -> list[dict]:
    out = []
    if not S.PROJECTS_DIR.exists():
        return out
    for d in sorted(S.PROJECTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        p = _read_json(d / "project.json")
        if not isinstance(p, dict):
            continue
        out.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "description": p.get("description", ""),
            "created_utc": p.get("created_utc"),
            "updated_utc": p.get("updated_utc"),
            "generaciones": len(p.get("history") or []),
            "bpm": (p.get("doc", {}).get("global") or {}).get("bpm"),
            "identity": (p.get("doc", {}).get("direction") or {}).get("identity"),
        })
    out.sort(key=lambda x: x.get("updated_utc") or "", reverse=True)
    return out


def save_project(pid: str, patch: dict) -> dict:
    p = get_project(pid)
    if not p:
        raise FileNotFoundError(pid)
    for k in ("name", "description"):
        if k in patch and patch[k] is not None:
            p[k] = str(patch[k])
    if "name" in patch and str(patch.get("name") or "").strip():
        p.setdefault("doc", {}).setdefault("meta", {})["title"] = str(patch["name"]).strip()
    if "doc" in patch and isinstance(patch["doc"], dict):
        p["doc"] = patch["doc"]
    if "production" in patch and isinstance(patch["production"], dict):
        base = DEFAULT_PRODUCTION()
        base.update({k: v for k, v in patch["production"].items() if k in base})
        p["production"] = base
    p["updated_utc"] = _now()
    _write_json(_pdir(pid) / "project.json", p)
    return p


def duplicate_project(pid: str, new_name: str | None = None) -> dict:
    src = get_project(pid)
    if not src:
        raise FileNotFoundError(pid)
    name = (new_name or f"{src['name']} (copia)").strip()
    copy = json.loads(json.dumps(src, ensure_ascii=False))
    copy.pop("id", None)
    copy.pop("history", None)
    copy.pop("seq", None)
    return create_project(name, src.get("description", ""), doc=copy.get("doc"),
                          production=copy.get("production"))


def delete_project(pid: str) -> bool:
    d = _pdir(pid)
    if not d.exists():
        return False
    shutil.rmtree(d)
    return True


# ----------------------------------------------------------------- historial
def next_gen_id(pid: str) -> str:
    p = get_project(pid)
    if not p:
        raise FileNotFoundError(pid)
    seq = int(p.get("seq") or 0) + 1
    p["seq"] = seq
    _write_json(_pdir(pid) / "project.json", p)
    return f"gen_{seq:04d}"


def project_dir(pid: str) -> Path:
    return _pdir(pid)


def gen_dir(pid: str, gen_id: str) -> Path:
    if not _valid_pid(pid) or not gen_id or "/" in gen_id or ".." in gen_id:
        raise ValueError("ruta de generación no válida")
    return _pdir(pid) / "generations" / gen_id


def append_history(pid: str, entry: dict) -> None:
    p = get_project(pid)
    if not p:
        return
    p.setdefault("history", []).insert(0, entry)
    p["history"] = p["history"][:100]
    p["updated_utc"] = _now()
    _write_json(_pdir(pid) / "project.json", p)


def read_gen_json(pid: str, gen_id: str, fname: str):
    allowed = {"doc.json", "config_efectiva.json", "evidencia.json", "job.json"}
    if fname not in allowed:
        raise ValueError("archivo no permitido")
    return _read_json(gen_dir(pid, gen_id) / fname)


def fresh_id() -> str:
    return uuid.uuid4().hex[:12]
