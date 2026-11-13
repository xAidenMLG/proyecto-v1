"""Módulo E — Song Map: representación estructural legible junto al JSON.

Resuelve DEFINITIVAMENTE el problema de recibir un MIDI sin saber qué
estructura tiene (misión §7). El mapa se calcula con la MISMA cadena de
precedencia del compilador (§2.8) y el MISMO algoritmo de ciclo del motor:

    section.chords  >  progressions[id]  >  progressions[type]  >  receta N1

Si el harmony es nativo, la progresión mostrada es la de la receta N1 real
(pares offset/calidad de la identidad, instanciados con la tónica declarada)
— no se inventa nada: los pares vienen del manifiesto introspeccionado del
DMD real.

El MIDI no lleva marcadores: la integración actual dark-director/1 →
compilador → forge no expone escritura de meta-eventos de marcador, y
modificar Forge para conseguirlo está prohibido (misión §7: "Si no lo es,
conserva el Song Map externo"). Limitación documentada en LIMITATIONS.md.
"""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional

from . import harmony as H
from . import model

SECONDS_PER_BAR = lambda bpm: 4 * 60.0 / bpm  # noqa: E731  (4/4 fijo del contrato)


def build_song_map(doc: dict, project: model.ComposerProject,
                   manifest: Optional[dict] = None) -> Dict[str, Any]:
    """Song Map completo del documento ya construido.

    Requiere el proyecto (para labels visibles) y el manifiesto (recetas N1).
    """
    secs = doc.get("structure") or []
    h = doc.get("harmony") or {}
    identity = (doc.get("direction") or {}).get("identity")
    key_lbl = h.get("key")
    language = h.get("language")
    hr_global = h.get("harmonic_rhythm_bars")
    progs = h.get("progressions") or {}
    receta = ((manifest or {}).get("recetas") or {}).get(identity) or {}
    n1 = (receta.get("progresiones") or {}).get(language) or {}
    labels = {s.id: s.label for s in project.sections}
    keyinfo = None
    if key_lbl:
        try:
            keyinfo = H.parse_key(key_lbl)
        except H.HarmonyError:
            keyinfo = None

    start_bar = 1
    rows: List[Dict[str, Any]] = []
    for order, s in enumerate(secs, 1):
        sid = s.get("id")
        stype = s.get("type")
        bars = int(s.get("bars") or 0)
        chord_bars = s.get("chord_bars") or hr_global or receta.get("harmonic_rhythm_bars") or 1
        # cadena de precedencia §2.8 (idéntica al compilador)
        fuente = "explicito"
        chords = None
        if s.get("chords"):
            chords = list(s["chords"])
        elif sid in progs:
            chords = list(progs[sid])
            fuente = "progressions_id"
        elif stype in progs:
            chords = list(progs[stype])
            fuente = "progressions_type"
        else:
            pairs = n1.get(stype)
            if pairs and keyinfo is not None:
                chords = H.instantiate_n1(pairs, keyinfo)
                fuente = "receta_n1"
        grid = []
        if chords and keyinfo is not None:
            try:
                # los acordes del doc son SÍMBOLOS REALES ('Dm9', 'G/B', 'F:2'):
                # el grid se calcula con los símbolos directamente (espejo del
                # algoritmo de ciclo de forge/engine.Sec)
                tokens = []
                for c in chords:
                    head, _, bars_part = c.partition(":")
                    tokens.append((head, float(bars_part) if bars_part else None))
                grid = _grid_from_symbols(tokens, bars, chord_bars)
            except Exception:
                grid = []
        rows.append({
            "orden": order,
            "id": sid,
            "nombre_visible": labels.get(sid, sid),
            "tipo_funcional": stype,
            "compas_inicial": start_bar,
            "compas_final": start_bar + bars - 1,
            "compases": bars,
            "progresion": chords or [],
            "fuente_armonia": fuente if chords else "sin_progresion",
            "chord_bars": chord_bars,
            "tonalidad": key_lbl,
            "grid_por_compas": grid,
            "duracion_seg": round(bars * SECONDS_PER_BAR(doc.get("global", {}).get("bpm") or 86), 2)
            if doc.get("global", {}).get("bpm") else None,
        })
        start_bar += bars

    total_bars = sum(r["compases"] for r in rows)
    bpm = doc.get("global", {}).get("bpm")
    return {
        "formato": "song-map/1",
        "obra": (doc.get("meta") or {}).get("title"),
        "contrato": "dark-director/1 rev 3.2",
        "tonalidad": key_lbl,
        "bpm": bpm,
        "compases_totales": total_bars,
        "duracion_total_seg": round(total_bars * SECONDS_PER_BAR(bpm), 2) if bpm else None,
        "secciones": rows,
        "notas_para_letras": _lyrics_helper(rows),
    }


def _grid_from_symbols(tokens: List, bars: int, chord_bars: float) -> List[str]:
    """Grid por compás con símbolos REALES (espejo de forge/engine.Sec)."""
    grid = [""] * bars
    t, i = 0.0, 0
    total = float(bars)
    while t < total - 1e-9:
        sym, b = tokens[i % len(tokens)] if tokens else ("", 1)
        e = min(total, t + max(0.25, b if b else chord_bars))
        for k in range(int(t + 1e-9), min(bars, int(e - 1e-9) + 1)):
            grid[k] = sym
        t, i = e, i + 1
    prev = tokens[0][0] if tokens else ""
    for k in range(bars):
        if not grid[k]:
            grid[k] = prev
        else:
            prev = grid[k]
    return grid


def _lyrics_helper(rows: List[Dict[str, Any]]) -> List[str]:
    """Bloque [Sección] listo para pegar sobre la letra (misión §7)."""
    out = []
    for r in rows:
        out.append(f"[{r['nombre_visible']}]  ({r['compas_inicial']}–{r['compas_final']}, "
                   f"{r['compases']} compases · {' - '.join(r['progresion'])})")
    return out


def song_map_csv(song_map: Dict[str, Any]) -> str:
    """CSV del Song Map (Sección, Compases, Progresión... misión §7)."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["orden", "id", "nombre_visible", "tipo_funcional", "compas_inicial",
                "compas_final", "compases", "progresion", "chord_bars", "tonalidad", "duracion_seg"])
    for r in song_map.get("secciones", []):
        w.writerow([r["orden"], r["id"], r["nombre_visible"], r["tipo_funcional"],
                    r["compas_inicial"], r["compas_final"], r["compases"],
                    " - ".join(r["progresion"]), r["chord_bars"], r["tonalidad"], r["duracion_seg"]])
    return buf.getvalue()
