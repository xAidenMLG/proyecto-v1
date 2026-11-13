"""Rutas y ajustes de DMD STUDIO.

Todo lo que la aplicación escribe vive bajo ``studio_data/`` (proyectos,
trabajos, salidas). Los motores y su ``output/`` histórico nunca se tocan.
Los ajustes se guardan en ``studio_data/studio_settings.json``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "studio_data"
PROJECTS_DIR = DATA_DIR / "projects"
JOBS_DIR = DATA_DIR / "jobs"

SETTINGS_FILE = DATA_DIR / "studio_settings.json"

DEFAULT_SETTINGS = {
    # Ruta al soundfont (.sf2) usado para renderizar WAV. En Windows el
    # usuario suele tener GeneralUser-GS.sf2; se autodetecta en el paquete
    # y en las ubicaciones típicas si queda vacío.
    "soundfont_path": "",
    # Ruta opcional al ejecutable fluidsynth (vacío = autodetección).
    "fluidsynth_path": "",
    # Puerto por defecto del servidor local (127.0.0.1).
    "port": 8899,
}

_SF2_NAMES = ("GeneralUser-GS.sf2", "GeneralUser GS.sf2", "generaluser-gs.sf2")


def ensure_dirs() -> None:
    for d in (DATA_DIR, PROJECTS_DIR, JOBS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    ensure_dirs()
    s = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass  # ajustes corruptos → defaults (nunca bloquear el arranque)
    return s


def save_settings(patch: dict) -> dict:
    s = load_settings()
    for k in DEFAULT_SETTINGS:
        if k in patch:
            s[k] = patch[k]
    if isinstance(s.get("port"), str) and s["port"].isdigit():
        s["port"] = int(s["port"])
    ensure_dirs()
    SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return s


def slugify(name: str, fallback: str = "proyecto") -> str:
    """Identificador seguro de proyecto/carpeta: sin traversal, sin espacios."""
    name = (name or "").strip().lower()
    name = re.sub(r"[áàä]", "a", name)
    name = re.sub(r"[éèë]", "e", name)
    name = re.sub(r"[íìï]", "i", name)
    name = re.sub(r"[óòö]", "o", name)
    name = re.sub(r"[úùü]", "u", name)
    name = re.sub(r"[ñ]", "n", name)
    name = re.sub(r"[^a-z0-9_-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:48] or fallback


def find_soundfont(configured: str = "") -> str | None:
    """Autodetección del soundfont: configurado → paquete → rutas típicas."""
    cand: list[Path] = []
    if configured:
        cand.append(Path(configured))
    for n in _SF2_NAMES:
        cand.append(ROOT / n)
        cand.append(ROOT / "soundfonts" / n)
        cand.append(DATA_DIR / n)
    for p in cand:
        try:
            if p.is_file() and p.stat().st_size > 1024:
                return str(p)
        except OSError:
            continue
    return None
