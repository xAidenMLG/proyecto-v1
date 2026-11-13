"""Modelo de proyecto de Composer: decisiones fijadas / automáticas / libres.

Tres estados por decisión (misión §3):
  * ``fixed``  — el usuario exige ese valor: se escribe EXACTO en el JSON.
  * ``auto``   — Composer decide una opción compatible y la ESCRIBE en el JSON
                 (queda registrada en el log de explicabilidad).
  * ``free``   — Composer NO escribe el campo: el motor DMD conserva su
                 libertad mediante sus mecanismos existentes (receta N1).

``auto`` nunca se confunde con ``free`` (misión §3): auto es una decisión
concreta de Composer; free es ausencia deliberada del campo.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from . import PROJECT_FORMAT

# --------------------------------------------------------------------------
# Vocabulario del modelo de Composer (NO del contrato: lo que aquí se llama
# "eje de decisión" es una elección del usuario; su traducción al JSON vive en
# builder.py y SIEMPRE usa campos reales del validador).
# --------------------------------------------------------------------------

#: Modos de una decisión.
FIXED, AUTO, FREE = "fixed", "auto", "free"

#: Ejes de decisión globales admitidos por Composer (módulos A–D).
EJES = (
    "identity",            # identidad musical (dark_triphop | doom_triphop | doom_dark_jazz)
    "accessibility",       # commercial | balanced | experimental
    "bpm",                 # 20–300 (validador); típico por identidad en la receta
    "key",                 # tonalidad canónica: "D minor", "Eb major", "A dorian"...
    "language",            # pop_dream_pop | hybrid | experimental
    "resolution",          # tonal | modal | deceptive | chromatic | open
    "harmonic_rhythm_bars",# 1–8 (compases por acorde, global)
    "harmony_mode",        # native | guided (módulo C)
    "mood",                # preferencia ponderada: melancholic | dark | hopeful | tense | neutral
    "atmosphere",          # spacious | medium | dense
    "groove",              # laid_back | steady | driving (sesgo de drums y energía)
    "spaces",              # free | suggested | mandatory (espacios musicales)
    "protagonist",         # id de instrumento protagonista (o "none")
    "production",          # perfil de producción (opción de Studio, no va en el doc)
    "ending",              # fade_out | tape_stop | none
    "seed",                # semilla del randomizador de Composer
)

#: Diversidad del randomizador (misión §4: evitar fórmula única sin caos).
DIVERSITY_LEVELS = ("restrained", "balanced", "adventurous")

#: Estados de espacio musical.
SPACES_MODES = ("free", "suggested", "mandatory")

#: Roles instrumentales (módulo A).
ROLE_PROTAGONIST = "protagonist"
ROLE_SUPPORT = "support"
ROLE_OFF = "off"
ROLE_AUTO = "auto"
INSTRUMENT_ROLES = (ROLE_PROTAGONIST, ROLE_SUPPORT, ROLE_OFF, ROLE_AUTO)


def decision(mode: str, value: Any = None) -> dict:
    """Decisión canónica: ``{"mode": ..., "value": ...}``."""
    if mode not in (FIXED, AUTO, FREE):
        raise ValueError(f"modo de decisión inválido: {mode!r}")
    if mode == FREE:
        return {"mode": FREE, "value": None}
    if mode == AUTO:
        return {"mode": AUTO, "value": None}   # el valor lo pone el randomizador
    return {"mode": FIXED, "value": value}


def is_fixed(d: Any) -> bool:
    return isinstance(d, dict) and d.get("mode") == FIXED


def is_auto(d: Any) -> bool:
    return isinstance(d, dict) and d.get("mode") == AUTO


def is_free(d: Any) -> bool:
    if d is None:
        return True
    return isinstance(d, dict) and d.get("mode") == FREE


# --------------------------------------------------------------------------
# Secciones (módulo B). ``label`` es el nombre visible (mapa externo); ``type``
# es SIEMPRE un tipo funcional del contrato (7 admitidos). El tipo lo elige
# el usuario en el selector de la interfaz (no se infiere del nombre).
# --------------------------------------------------------------------------

#: Tipos funcionales reales (catálogo del contrato; se replica del manifiesto
#: DMD en runtime — este orden solo sirve como fallback offline).
SECTION_TYPES_FALLBACK = ("intro", "verse", "pre_chorus", "chorus", "bridge", "break", "outro")


def normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", (label or "").strip())[:40]


@dataclass
class Section:
    """Sección del editor estructural (estado de Composer, aún no contrato)."""
    id: str
    label: str                     # nombre visible ("Verse 1", "Preludio"...)
    type: str                      # tipo funcional REAL del contrato
    bars: int
    energy: Optional[float] = None
    tension: Optional[float] = None
    density: Optional[float] = None
    drums: Optional[str] = None    # escalera off/air/light/groove/heavy o None (libre)
    focus: Optional[list] = None   # ≤ 3 ids del catálogo
    active: Optional[list] = None  # whitelist de instrumentos que suenan
    chord_bars: Optional[int] = None  # 1–8 (ritmo armónico por sección)
    resolution: Optional[str] = None
    loop_bars: Optional[int] = None   # hook de chorus (commercial)
    final: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None or k in ("id", "label", "type", "bars")}


# --------------------------------------------------------------------------
# Proyecto
# --------------------------------------------------------------------------

def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")
    return s or "proyecto"


@dataclass
class InstrumentDecision:
    """Decisión de instrumento (módulo A): rol + opcional enabled/density."""
    role: str = ROLE_AUTO              # protagonist | support | off | auto
    enabled: Optional[bool] = None     # None = libertad del motor (no escribir)
    density: Optional[float] = None    # None = libre

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class HarmonySection:
    """Decisión armónica de UNA sección (módulo C).

    ``chords`` son ACORDES LITERALES del contrato (posición 1 de la cadena de
    precedencia §2.8: section.chords > progressions[id] > progressions[type]
    > receta N1): símbolos reales del parser del motor (forge/theory),
    p. ej. ``G/B - Dm9:2 - Fmaj7``. Se escriben en ``structure[].chords`` y
    tienen la precedencia MÁS ALTA incluso con modo global Nativa (son datos
    explícitos del usuario, no una conversión silenciosa de modo).
    """
    mode: str = "native"               # native | guided
    numerals: Optional[str] = None     # "I - III - vi - V" (modo guiado)
    chords: Optional[str] = None       # "G/B - Dm9:2 - Fmaj7" (acordes literales)
    chord_bars: Optional[int] = None   # None = hereda global/libre
    resolution: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ComposerProject:
    """Proyecto completo de Composer (persistencia JSON)."""
    name: str
    pid: str = ""
    notes: str = ""
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    decisions: dict = field(default_factory=dict)       # eje → decisión
    instruments: dict = field(default_factory=dict)     # iid → InstrumentDecision
    sections: list = field(default_factory=list)        # [Section]
    harmony_sections: dict = field(default_factory=dict)  # sid → HarmonySection
    production: dict = field(default_factory=lambda: {"profile": None, "f7_keyword": None,
                                                      "f7_variation": None, "wav": False})
    diversity: str = "balanced"
    album: Optional[dict] = None
    #: Propuesta de distribución del protagonista (v1.1): {estado, propuesta}.
    #: estado: "aplicada" | "descartada" | None. El usuario puede aceptarla,
    #: modificar los campos resultantes o rechazarla: nunca se aplica sola.
    protagonist_proposal: Optional[dict] = None

    # ---------------------------------------------------------------- utils
    def touch(self) -> None:
        self.updated = time.time()

    def section_ids(self) -> list:
        return [s.id for s in self.sections]

    def get_decision(self, eje: str, default: Optional[dict] = None) -> dict:
        return self.decisions.get(eje, default if default is not None else decision(FREE))

    def fixed_value(self, eje: str) -> Any:
        d = self.get_decision(eje)
        return d.get("value") if is_fixed(d) else None

    def to_dict(self) -> dict:
        """Formato PLANO del proyecto en disco y en la API (pid/name/notes al
        primer nivel: un solo formato, sin doble anidamiento)."""
        return {
            "format": PROJECT_FORMAT,
            "pid": self.pid,
            "name": self.name,
            "notes": self.notes,
            "created": self.created,
            "updated": self.updated,
            "decisions": self.decisions,
            "instruments": {k: v.to_dict() for k, v in self.instruments.items()},
            "sections": [s.to_dict() for s in self.sections],
            "harmony_sections": {k: v.to_dict() for k, v in self.harmony_sections.items()},
            "production": self.production,
            "diversity": self.diversity,
            "album": self.album,
            "protagonist_proposal": self.protagonist_proposal,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ComposerProject":
        if not isinstance(d, dict) or d.get("format") != PROJECT_FORMAT:
            raise ValueError("el archivo no es un proyecto dmd-composer/1")
        # formato plano (actual) o anidado (compatibilidad de lectura)
        p = d if "pid" in d or "name" in d else (d.get("project") or {})
        proj = cls(
            name=str(p.get("name") or "Sin nombre"),
            pid=str(p.get("pid") or ""),
            notes=str(p.get("notes") or ""),
            created=float(p.get("created") or time.time()),
            updated=float(p.get("updated") or time.time()),
            decisions=dict(d.get("decisions") or {}),
            diversity=str(d.get("diversity") or "balanced"),
            album=d.get("album"),
        )
        prod = d.get("production") or {}
        proj.production = {
            "profile": prod.get("profile"),
            "f7_keyword": prod.get("f7_keyword"),
            "f7_variation": prod.get("f7_variation"),
            "wav": bool(prod.get("wav", False)),
        }
        for iid, conf in (d.get("instruments") or {}).items():
            proj.instruments[str(iid)] = InstrumentDecision(
                role=str(conf.get("role") or ROLE_AUTO),
                enabled=conf.get("enabled"),
                density=conf.get("density"),
            )
        for s in (d.get("sections") or []):
            proj.sections.append(Section(
                id=str(s.get("id") or ""), label=str(s.get("label") or s.get("id") or ""),
                type=str(s.get("type") or ""), bars=int(s.get("bars") or 4),
                energy=s.get("energy"), tension=s.get("tension"), density=s.get("density"),
                drums=s.get("drums"), focus=s.get("focus"), active=s.get("active"),
                chord_bars=s.get("chord_bars"), resolution=s.get("resolution"),
                loop_bars=s.get("loop_bars"), final=bool(s.get("final", False)),
            ))
        for sid, h in (d.get("harmony_sections") or {}).items():
            proj.harmony_sections[str(sid)] = HarmonySection(
                mode=str(h.get("mode") or "native"),
                numerals=h.get("numerals"),
                chords=h.get("chords"),
                chord_bars=h.get("chord_bars"),
                resolution=h.get("resolution"),
            )
        pp = d.get("protagonist_proposal")
        if isinstance(pp, dict) and pp.get("estado") in ("aplicada", "descartada"):
            proj.protagonist_proposal = {"estado": pp["estado"],
                                         "protagonista": pp.get("protagonista"),
                                         "cambios_aplicados": pp.get("cambios_aplicados"),
                                         "timestamp": pp.get("timestamp")}
        return proj


def new_project(name: str) -> ComposerProject:
    """Proyecto nuevo con defaults razonables (todo automático salvo identidad)."""
    p = ComposerProject(name=name)
    p.pid = _slug(name)[:48]
    p.decisions = {
        "identity": decision(FIXED, "dark_triphop"),   # identidad activa del ecosistema
        "accessibility": decision(AUTO),
        "bpm": decision(AUTO),
        "key": decision(AUTO),
        "language": decision(AUTO),
        "resolution": decision(FREE),
        "harmonic_rhythm_bars": decision(AUTO),
        "harmony_mode": decision(FIXED, "guided"),
        "mood": decision(FIXED, "neutral"),
        "atmosphere": decision(AUTO),
        "groove": decision(AUTO),
        "spaces": decision(FREE),
        "protagonist": decision(FREE),
        "production": decision(AUTO),
        "ending": decision(AUTO),
        "seed": decision(AUTO),
    }
    return p
