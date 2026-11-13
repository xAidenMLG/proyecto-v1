"""Módulo B — constructor estructural: validación, orden y duraciones.

La estructura es una lista de secciones (``model.Section``) con TIPO FUNCIONAL
siempre dentro del catálogo real del contrato (7 tipos). El nombre visible
(``label``) es un mapa externo de Composer: nunca se escribe en el JSON como
campo nuevo (E109) — viaja en el Song Map y en los artefactos de Composer.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from . import model

#: Fallback offline (orden canónico del contrato; en vivo viene del manifiesto).
SECTION_TYPES_FALLBACK = ("intro", "verse", "pre_chorus", "chorus", "bridge", "break", "outro")


class StructureError(ValueError):
    """Estructura inválida (mensaje para el usuario)."""


def section_catalog(manifest: Optional[dict] = None) -> Tuple[str, ...]:
    """Catálogo REAL de tipos (del manifiesto DMD; fallback offline etiquetado)."""
    if manifest:
        cats = (manifest.get("catalogos") or {}).get("section_types")
        if cats:
            return tuple(cats)
    return SECTION_TYPES_FALLBACK


def normalize_sections(sections: List[model.Section], manifest: Optional[dict] = None) -> List[model.Section]:
    """Valida y normaliza la estructura. Lanza StructureError ante E106/E105.

    Comprobaciones que el validador REAL convertirá en E105/E106 (y una más:
    ids únicos), hechas aquí para dárselas al usuario ANTES de generar.
    """
    if not sections:
        raise StructureError("la estructura necesita al menos 2 secciones (E106 del contrato)")
    if len(sections) < 2:
        raise StructureError(
            f"la estructura tiene {len(sections)} sección(es): el contrato exige ≥ 2 (E106)")
    tipos = section_catalog(manifest)
    ids_vistos = set()
    for i, s in enumerate(sections, 1):
        if not s.id or not isinstance(s.id, str):
            raise StructureError(f"sección {i}: falta el id")
        if s.id in ids_vistos:
            raise StructureError(f"id de sección duplicado '{s.id}' (E106): renombra una de las dos")
        ids_vistos.add(s.id)
        if s.type not in tipos:
            raise StructureError(
                f"sección '{s.id}': tipo '{s.type}' fuera del catálogo real {list(tipos)}")
        if not isinstance(s.bars, int) or s.bars < 1 or s.bars > 512:
            raise StructureError(
                f"sección '{s.id}': compases debe ser entero 1–512 (got {s.bars!r})")
        for campo in ("energy", "tension", "density"):
            v = getattr(s, campo)
            if v is not None and not (0.0 <= float(v) <= 1.0):
                raise StructureError(f"sección '{s.id}': {campo} fuera de 0–1 ({v!r})")
        if s.drums is not None and s.drums not in ("off", "air", "light", "groove", "heavy"):
            raise StructureError(f"sección '{s.id}': drums '{s.drums}' fuera de la escalera off/air/light/groove/heavy")
        if s.focus is not None:
            if len(s.focus) > 3:
                raise StructureError(f"sección '{s.id}': focus admite máximo 3 instrumentos")
        if s.chord_bars is not None and not (1 <= s.chord_bars <= 8):
            raise StructureError(f"sección '{s.id}': chord_bars debe ser 1–8")
        if s.loop_bars is not None and not (1 <= s.loop_bars <= 32):
            raise StructureError(f"sección '{s.id}': loop_bars debe ser 1–32")
    return sections


def timeline(sections: List[model.Section], bpm: Optional[int]) -> dict:
    """Cronología: compás de inicio/fin (1-indexado para humanos), compases
    totales y duración aproximada (compás = 4 tiempos; el contrato no admite
    otra métrica — documentado)."""
    start = 1
    total_bars = 0
    rows = []
    for s in sections:
        end = start + s.bars - 1
        dur = (s.bars * 4 * 60.0 / bpm) if bpm else None
        rows.append({"id": s.id, "label": s.label, "type": s.type, "bars": s.bars,
                     "start_bar": start, "end_bar": end, "duration_sec": round(dur, 2) if dur else None})
        start = end + 1
        total_bars += s.bars
    total_dur = (total_bars * 4 * 60.0 / bpm) if bpm else None
    return {"rows": rows, "total_bars": total_bars,
            "total_duration_sec": round(total_dur, 2) if total_dur else None}


def reorder(sections: List[model.Section], from_idx: int, to_idx: int) -> List[model.Section]:
    """Reordenamiento seguro (módulo B: mover sección)."""
    if not (0 <= from_idx < len(sections)) or not (0 <= to_idx < len(sections)):
        raise StructureError("índice fuera de rango al reordenar")
    s = sections.pop(from_idx)
    sections.insert(to_idx, s)
    return sections


def duplicate_section(sections: List[model.Section], idx: int) -> model.Section:
    """Duplica una sección con id único (``chorus_1`` → ``chorus_1_copy``)."""
    src = sections[idx]
    base = f"{src.id}_copy"
    nid, n = base, 2
    while any(x.id == nid for x in sections):
        nid = f"{base}{n}"
        n += 1
    import copy as _copy
    dup = _copy.deepcopy(src)
    dup.id = nid
    dup.label = f"{src.label} (copia)"
    return dup


def suggest_id(label: str, existing: List[str]) -> str:
    """Id de sección a partir del nombre visible (slug único)."""
    base = model._slug(model.normalize_label(label)) or "sec"
    if len(base) > 24:
        base = base[:24]
    nid, n = base, 2
    while nid in existing:
        nid = f"{base}_{n}"
        n += 1
    return nid
