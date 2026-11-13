"""Capacidades reales del backend, expuestas tal cual a la interfaz.

La UI no inventa opciones: todo lo que muestra (catálogos del contrato,
perfiles de producción, keywords de la biblioteca Fase 7, estado de audio)
se lee EN VIVO de los módulos de los motores. Si un motor cambia, la UI lo
refleja sin tocar JavaScript.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract  # noqa: E402
import jazz_engine as je  # noqa: E402
from jazz_engine import production as production_profiles  # noqa: E402
from jazz_engine import harmony_library as hlib  # noqa: E402
from dark_director import forge_link  # noqa: E402

forge_link.import_forge()
from forge import audio as forge_audio  # noqa: E402  # noqa: E402

from . import settings as S  # noqa: E402

#: Nombres humanos para la UI (el identificador interno viaja aparte y es el
#: exacto admitido por ``jazz_engine.production``).
PROFILE_LABELS = {
    "original": "Original (camino directo a MIDI Forge)",
    "sax": "Sax",
    "sax_rhodes": "Sax + Rhodes",
    "drums": "Drums",
    "sax_vibes": "Sax + Vibes",
    "full": "Full (todos los motores)",
    "atmospheric": "Atmospheric (full + variación atmospheric)",
}

PROFILE_ENGINES = {
    "original": {"sax": None, "rhodes": None, "drums": None, "vibes": None},
    "sax": {"sax": True, "rhodes": False, "drums": False, "vibes": False},
    "sax_rhodes": {"sax": True, "rhodes": True, "drums": False, "vibes": False},
    "drums": {"sax": False, "rhodes": False, "drums": True, "vibes": False},
    "sax_vibes": {"sax": True, "rhodes": False, "drums": False, "vibes": True},
    "full": {"sax": True, "rhodes": True, "drums": True, "vibes": True},
    "atmospheric": {"sax": True, "rhodes": True, "drums": True, "vibes": True},
}

#: Especificación de campos para los controles de la UI. ES UN ESPEJO de las
#: reglas de ``dark_director/validador.py`` (único árbitro real): si el
#: validador cambia, la validación del backend sigue siendo la del validador.
FIELD_SPECS = {
    "bpm": {"min": 20, "max": 300, "type": "int"},
    "harmonic_rhythm_bars": {"min": 1, "max": 8, "type": "int"},
    "bars": {"min": 1, "max": 512, "type": "int"},
    "chord_bars": {"min": 1, "max": 8, "type": "int"},
    "loop_bars": {"min": 1, "max": 32, "type": "int"},
    "energy": {"min": 0.0, "max": 1.0, "step": 0.05, "type": "float"},
    "tension": {"min": 0.0, "max": 1.0, "step": 0.05, "type": "float"},
    "density": {"min": 0.0, "max": 1.0, "step": 0.05, "type": "float"},
    "velocity_cap": {"min": 1, "max": 127, "type": "int"},
    "humanize": {"min": 0.0, "max": 1.0, "step": 0.05, "type": "float"},
    "note_beat": {"min": 0.0, "max": 4.0, "type": "float"},
    "harmony_variaciones": list(hlib.NIVELES_VARIACION),
}

#: Keywords canónicas de la biblioteca Fase 7 (las mismas del CLI produce.py).
HARMONY_KEYWORDS = ("familiar_pop", "melancholic", "nostalgic", "dark_cinematic",
                    "dream_pop", "alternative", "soulful", "emotional_resolution",
                    "tension_release", "familiarity_auto")


def catalogos():
    """Catálogos cerrados del contrato rev 3.2 (contrato.py, §2.5)."""
    return {
        "instruments": list(contract.INSTRUMENT_IDS),
        "section_types": list(contract.SECTION_TYPES),
        "drums_ladder": list(contract.DRUMS_LADDER),
        "identities": list(contract.IDENTITIES),
        "accessibilities": list(contract.ACCESSIBILITIES),
        "languages": list(contract.LANGUAGES),
        "resolutions": list(contract.RESOLUTIONS),
        "base_sets": {k: list(v) for k, v in contract.BASE_SETS_SUPUESTO_PROVISIONAL.items()},
        "combinaciones_validas": contract.TOTAL_COMBINACIONES,
        "ew_codes": {k: {"familia": v[0], "resumen": v[1]} for k, v in contract.EW_CODES.items()},
    }


def perfiles():
    """Perfiles de producción reales (jazz_engine.production)."""
    out = []
    for name in production_profiles.nombres():
        preset = production_profiles.resolver(name) or {}
        out.append({
            "id": name,
            "label": PROFILE_LABELS.get(name, name),
            "engines": PROFILE_ENGINES.get(name, preset.get("engines")),
            "variation": preset.get("variation"),
            "es_default": name == production_profiles.DEFAULT_PROFILE,
        })
    return out


def biblioteca_armonia():
    """Entradas de la biblioteca de familiaridad (Fase 7) — opción adicional.

    Se expone id + nombre + keywords para que la UI pueda ofrecer la selección
    por keyword o por progresión concreta, tal como el CLI ``--harmony`` /
    ``--harmony-id``.
    """
    try:
        lib = hlib.biblioteca()
    except Exception:
        return []
    out = []
    for eid in sorted(lib):
        e = lib[eid]
        out.append({
            "id": e.get("id"),
            "nombre": e.get("nombre"),
            "keywords": list(e.get("keywords") or []),
            "familia": e.get("familia"),
            "funcion": e.get("funcion"),
            "modo": e.get("modo"),
        })
    return out


def audio_status() -> dict:
    st = forge_audio.status() or {}
    st = dict(st)
    s = S.load_settings()
    sf = S.find_soundfont(s.get("soundfont_path", ""))
    st["soundfont_encontrado"] = sf
    if s.get("fluidsynth_path"):
        st["fluidsynth"] = s["fluidsynth_path"] if Path(s["fluidsynth_path"]).is_file() else None
    st["wav_posible"] = bool(st.get("fluidsynth") and st.get("soundfont_encontrado"))
    return st


def capabilities() -> dict:
    from dark_director import compilador
    info = contract.contract_info()
    return {
        "studio": {"version": __import__("studio").__version__},
        "contrato": info,
        "jazz_engine_version": je.__version__,
        "compiler_version": compilador.COMPILER_VERSION
        if hasattr(compilador, "COMPILER_VERSION") else info.get("compiler_version"),
        "catalogos": catalogos(),
        "perfiles": perfiles(),
        "field_specs": FIELD_SPECS,
        "harmony_keywords": list(HARMONY_KEYWORDS),
        "biblioteca_fase7": biblioteca_armonia(),
        "audio": audio_status(),
    }
