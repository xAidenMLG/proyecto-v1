"""Persistencia de Composer: proyectos, generaciones y escritura atómica.

Estructura (misión §13):
    projects/<pid>/project.json          — proyecto de Composer (dmd-composer/1)
    output/<pid>/gen_NNNN/doc.json       — documento dark-director/1 emitido
    output/<pid>/gen_NNNN/song_map.json  — Song Map
    output/<pid>/gen_NNNN/song_map.csv   — Song Map CSV
    output/<pid>/gen_NNNN/generation_manifest.json — seed, decisiones, SHA256

Seguridad (misión §11): ids validados contra patrón estricto (sin path
traversal), escritura atómica (tmp + replace), JAMÁS se sobrescribe una
generación existente (nuevo número siempre), tamaños acotados.

MIDI (misión de integración): la producción real añade la subcarpeta
``midi/<nombre>/`` y el bloque ``midi`` del manifest (ver helpers al final).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__, model

ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT / "projects"
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "composer_data"

_PID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
_GEN_RE = re.compile(r"^gen_\d{4,}$")
_NAME_BAD = re.compile(r"[\\/:*?\"<>|\x00-\x1f]")
MAX_PROJECT_BYTES = 512 * 1024


class StoreError(ValueError):
    """Error de validación de store (mensaje para el usuario)."""


def safe_pid(pid: str) -> str:
    if not _PID_RE.fullmatch(pid or ""):
        raise StoreError("id de proyecto no válido (sin / ni .. ni caracteres raros)")
    return pid


def safe_gen(gen_id: str) -> str:
    if not _GEN_RE.fullmatch(gen_id or ""):
        raise StoreError("id de generación no válido")
    return gen_id


def safe_name(name: str) -> str:
    n = (name or "").strip()
    if not n or len(n) > 64 or n.startswith(".") or _NAME_BAD.search(n):
        raise StoreError("nombre no válido (sin / \\ : * ? \" < > | ni control)")
    return n


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return (s or "proyecto")[:48]


def atomic_write_json(path: Path, data: Any) -> None:
    """Escritura atómica: tmp en el mismo dir + os.replace (misión §11)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------- proyectos

def create_project(name: str, notes: str = "") -> model.ComposerProject:
    name = safe_name(name)
    base = slugify(name)
    pid, n = base, 2
    while (PROJECTS_DIR / pid).exists():
        pid = f"{base}_{n}"
        n += 1
    proj = model.new_project(name)
    proj.pid = pid
    proj.notes = (notes or "")[:300]
    proj.touch()
    atomic_write_json(PROJECTS_DIR / pid / "project.json", proj.to_dict())
    return proj


def save_project(proj: model.ComposerProject) -> None:
    proj.touch()
    atomic_write_json(PROJECTS_DIR / safe_pid(proj.pid) / "project.json", proj.to_dict())


def load_project(pid: str) -> Optional[model.ComposerProject]:
    f = PROJECTS_DIR / safe_pid(pid) / "project.json"
    if not f.exists():
        return None
    raw = f.read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) > MAX_PROJECT_BYTES:
        raise StoreError("proyecto demasiado grande")
    return model.ComposerProject.from_dict(json.loads(raw))


def list_projects() -> List[Dict[str, Any]]:
    out = []
    if not PROJECTS_DIR.exists():
        return out
    for d in sorted(PROJECTS_DIR.iterdir()):
        f = d / "project.json"
        if d.is_dir() and f.exists():
            try:
                p = model.ComposerProject.from_dict(json.loads(f.read_text(encoding="utf-8")))
                out.append({"pid": d.name, "name": p.name, "notes": p.notes,
                            "updated": p.updated, "secciones": len(p.sections),
                            "identity": p.fixed_value("identity"),
                            "generaciones": len(list_generations(d.name))})
            except Exception as e:
                out.append({"pid": d.name, "name": "(ilegible)", "error": str(e)})
    return out


def duplicate_project(pid: str, new_name: Optional[str] = None) -> model.ComposerProject:
    src = load_project(pid)
    if not src:
        raise StoreError("proyecto no encontrado")
    name = safe_name(new_name) if new_name else f"{src.name} (copia)"
    dst = create_project(name)
    dst.decisions = json.loads(json.dumps(src.decisions))
    dst.instruments = json.loads(json.dumps({k: v.to_dict() for k, v in src.instruments.items()}))
    dst.instruments = {k: model.InstrumentDecision(**v) for k, v in dst.instruments.items()}
    dst.sections = json.loads(json.dumps([s.to_dict() for s in src.sections]))
    dst.sections = [model.Section(**{k: v for k, v in s.items() if k in model.Section.__dataclass_fields__})
                    for s in dst.sections]
    dst.harmony_sections = json.loads(json.dumps({k: v.to_dict() for k, v in src.harmony_sections.items()}))
    dst.harmony_sections = {k: model.HarmonySection(**v) for k, v in dst.harmony_sections.items()}
    dst.production = json.loads(json.dumps(src.production))
    dst.diversity = src.diversity
    dst.notes = src.notes
    save_project(dst)
    return dst


def delete_project(pid: str) -> bool:
    pid = safe_pid(pid)
    d = PROJECTS_DIR / pid
    if not d.exists():
        return False
    shutil.rmtree(d)
    od = OUTPUT_DIR / pid
    if od.exists():
        shutil.rmtree(od)
    return True


# ---------------------------------------------------------------- generaciones

def next_gen_dir(pid: str) -> Path:
    """NUEVO directorio de generación siempre (nunca sobrescribe: misión §11).

    Creación EXCLUSIVA (mkdir exist_ok=False) para que dos composiciones
    concurrentes no colisionen en el mismo gen_NNNN (auditoría m7).
    """
    pid = safe_pid(pid)
    base = OUTPUT_DIR / pid
    n = 1
    while True:
        d = base / f"gen_{n:04d}"
        try:
            d.mkdir(parents=True, exist_ok=False)
            return d
        except FileExistsError:
            n += 1


def save_generation(pid: str, doc: dict, song_map: dict, csv_text: str,
                    manifest: dict) -> Dict[str, Any]:
    """Guarda la generación completa en un directorio NUEVO y EXCLUSIVO
    (reservado en el mismo paso: nunca sobrescribe, sin carreras)."""
    gdir = next_gen_dir(pid)
    atomic_write_json(gdir / "doc.json", doc)
    atomic_write_json(gdir / "song_map.json", song_map)
    atomic_write_text(gdir / "song_map.csv", csv_text)
    atomic_write_json(gdir / "generation_manifest.json", manifest)
    return {
        "gen_id": gdir.name,
        "pid": pid,
        "sha256_doc": sha256_file(gdir / "doc.json"),
        "sha256_song_map": sha256_file(gdir / "song_map.json"),
        "seed": manifest.get("seed_used"),
        "timestamp": time.time(),
        "archivos": ["doc.json", "song_map.json", "song_map.csv", "generation_manifest.json"],
    }


def list_generations(pid: str) -> List[Dict[str, Any]]:
    pid = safe_pid(pid)
    base = OUTPUT_DIR / pid
    out = []
    if not base.exists():
        return out
    for d in sorted(base.iterdir()):
        f = d / "generation_manifest.json"
        if d.is_dir() and f.exists():
            try:
                m = json.loads(f.read_text(encoding="utf-8"))
                out.append({"gen_id": d.name, "seed": m.get("seed_used"),
                            "timestamp": m.get("timestamp"),
                            "title": (m.get("obra") or ""),
                            "sha256_doc": m.get("sha256_doc"),
                            "midi_estado": _midi_estado_barato(pid := d.parent.name, d),
                            "sha256_midi": ((m.get("midi") or {}).get("sha256")
                                            if isinstance(m.get("midi"), dict) else None),
                            "validacion_ok": m.get("validacion", {}).get("ok")
                            if isinstance(m.get("validacion"), dict) else None})
            except Exception:
                out.append({"gen_id": d.name, "error": "manifest ilegible"})
    return out


def get_generation(pid: str, gen_id: str) -> Optional[Dict[str, Any]]:
    pid, gen_id = safe_pid(pid), safe_gen(gen_id)
    d = OUTPUT_DIR / pid / gen_id
    if not d.exists():
        return None
    out = {"gen_id": gen_id, "archivos": {}}
    for f in sorted(d.iterdir()):
        if f.suffix == ".json" or f.suffix == ".csv":
            try:
                out["archivos"][f.name] = f.read_text(encoding="utf-8")
            except Exception:
                out["archivos"][f.name] = None
    return out




def gen_dir(pid: str, gen_id: str) -> Path:
    """Carpeta de la generación (ids validados)."""
    return OUTPUT_DIR / safe_pid(pid) / safe_gen(gen_id)

# ------------------------------------------------- artefactos MIDI (producción)
# El MIDI de una generación se produce FUERA de Composer (puente con el DMD)
# y se registra en el generation_manifest bajo la clave "midi". Desde aquí se
# verifica la integridad REAL del artefacto (cabecera MThd + SHA256) antes de
# declarar la instrucción de producción como "aplicado" (misión §11).

def _contained(p: Path, base: Path) -> Optional[Path]:
    """Ruta resuelta SOLO si vive dentro de base (defensa en profundidad)."""
    try:
        rp, rb = p.resolve(), base.resolve()
    except OSError:
        return None
    try:
        rp.relative_to(rb)
    except ValueError:
        return None
    return rp


def midi_name(pid: str, gen_id: str, obra: str) -> str:
    """Nombre canónico de la carpeta/obra del MIDI: <slug32>_<gen_id>."""
    slug = slugify(obra or "")[:32] or "obra"
    return safe_name(f"{slug}_{safe_gen(gen_id)}")


def prepare_midi_dir(pid: str, gen_id: str, nombre: str) -> Path:
    """Carpeta limpia output/<pid>/<gen>/midi/<nombre>/ para el puente.

    Si ya existía era un intento anterior fallido (los callers garantizan que
    NO hay bloque midi registrado): se borra para no mezclar artefactos.
    """
    pid, gen_id = safe_pid(pid), safe_gen(gen_id)
    nombre = safe_name(nombre)
    d = OUTPUT_DIR / pid / gen_id / "midi" / nombre
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d


def write_midi_block(pid: str, gen_id: str, block: dict) -> None:
    """Fusiona el bloque "midi" en generation_manifest.json (atómico).

    No toca ninguna otra clave del manifest; si el manifest no existe → error.
    """
    pid, gen_id = safe_pid(pid), safe_gen(gen_id)
    if not isinstance(block, dict):
        raise StoreError("bloque midi no válido")
    f = OUTPUT_DIR / pid / gen_id / "generation_manifest.json"
    if not f.exists():
        raise StoreError("generation_manifest.json no encontrado para esta generación")
    try:
        m = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        raise StoreError(f"manifest de generación ilegible: {e}")
    if not isinstance(m, dict):
        raise StoreError("manifest de generación ilegible")
    m["midi"] = block
    atomic_write_json(f, m)


def read_midi_block(pid: str, gen_id: str) -> Optional[Dict[str, Any]]:
    """Bloque "midi" del manifest de la generación (None si no está)."""
    pid, gen_id = safe_pid(pid), safe_gen(gen_id)
    f = OUTPUT_DIR / pid / gen_id / "generation_manifest.json"
    if not f.exists():
        return None
    try:
        m = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    blk = m.get("midi") if isinstance(m, dict) else None
    return blk if isinstance(blk, dict) else None


def midi_integrity(pid: str, gen_id: str) -> Dict[str, str]:
    """Verificación REAL del artefacto registrado: existe, no vacío, cabecera
    MThd y SHA256 idéntico al registrado en el bloque "midi"."""
    pid, gen_id = safe_pid(pid), safe_gen(gen_id)
    block = read_midi_block(pid, gen_id)
    if not block:
        return {"estado": "sin_midi",
                "detalle": "esta generación no tiene bloque midi registrado"}
    ruta = (block.get("rutas") or {}).get("midi")
    if not ruta:
        return {"estado": "integridad_error",
                "detalle": "el bloque midi no registra la ruta del archivo"}
    base = OUTPUT_DIR / pid / gen_id
    p = _contained(Path(str(ruta)), base)
    if p is None:
        return {"estado": "integridad_error",
                "detalle": "la ruta del MIDI está fuera de la carpeta de la generación"}
    if not p.exists():
        return {"estado": "integridad_error",
                "detalle": "el archivo MIDI registrado no existe"}
    try:
        if p.stat().st_size <= 0:
            return {"estado": "integridad_error", "detalle": "el archivo MIDI está vacío"}
        with open(p, "rb") as fh:
            head = fh.read(4)
    except OSError as e:
        return {"estado": "integridad_error", "detalle": f"no se pudo leer el MIDI: {e}"}
    if head != b"MThd":
        return {"estado": "integridad_error",
                "detalle": "el archivo no empieza con la cabecera MIDI (MThd)"}
    sha = sha256_file(p)
    if block.get("sha256") != sha:
        return {"estado": "integridad_error",
                "detalle": (f"sha256 no coincide (registrado {block.get('sha256')}, "
                            f"actual {sha})")}
    return {"estado": "ok", "detalle": f"MIDI íntegro ({p.name})"}


def list_midi_artifacts(pid: str, gen_id: str) -> Dict[str, bool]:
    """Presencia de los artefactos de producción dentro de midi/<nombre>/."""
    pid, gen_id = safe_pid(pid), safe_gen(gen_id)
    out = {"midi": False, "events": False, "evidencia": False, "config_efectiva": False}
    block = read_midi_block(pid, gen_id)
    if not block:
        return out
    try:
        nombre = safe_name(str(block.get("nombre") or ""))
    except StoreError:
        return out
    gen = OUTPUT_DIR / pid / gen_id
    base = gen / "midi" / nombre
    if not base.is_dir():
        return out
    rutas = block.get("rutas") or {}

    def _hay(ruta: Any, por_defecto: Path) -> bool:
        if ruta:
            p = _contained(Path(str(ruta)), gen)
            if p and p.is_file():
                return True
        return por_defecto.is_file()

    out["midi"] = _hay(rutas.get("midi"), base / f"{nombre}.mid")
    out["events"] = _hay(rutas.get("events"), base / "events.json")
    out["evidencia"] = _hay(rutas.get("evidencia"), base / "evidencia.json")
    out["config_efectiva"] = _hay(rutas.get("config_efectiva"), base / "config_efectiva.json")
    return out


def _midi_estado_barato(pid: str, gen_dir: Path) -> str:
    """midi_estado económico para listados: presencia + existencia del archivo
    (la integridad completa con SHA256 queda en midi_integrity)."""
    blk = read_midi_block(pid, gen_dir.name)
    if not blk:
        return "sin_midi"
    ruta = (blk.get("rutas") or {}).get("midi")
    if not ruta:
        return "integridad_error"
    p = _contained(Path(str(ruta)), gen_dir)
    if p and p.is_file() and p.stat().st_size > 0:
        return "ok"
    return "integridad_error"
