"""Manifiesto de capacidades: fuente de verdad de los catálogos de Composer.

Principio de la misión §10: "Los catálogos deben provenir de las capacidades
reales del sistema o de manifiestos derivados y verificables. No mantengas
listas independientes que puedan quedar desactualizadas."

  * En vivo   : introspección del DMD descubierto (subprocess aislado).
  * En caché  : ``composer_data/dmd_manifest.json`` con fingerprint.
  * Fallback  : ``manifests/dmd_manifest_builtin.json`` — instantánea DERIVADA
    del DMD real rev 3.2, verificable con la batería de pruebas
    (test A2/A8: builtin == introspección viva cuando hay DMD).

Si el DMD del usuario cambia (otra rev, otra receta), el fingerprint cambia,
Composer avisa la discrepancia en la UI y recalcula lo que dependía del
manifiesto — nunca genera documentos incompatibles sin avisar.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from . import bridge

PKG_ROOT = Path(__file__).resolve().parent.parent
BUILTIN_MANIFEST = PKG_ROOT / "manifests" / "dmd_manifest_builtin.json"


def load_builtin() -> Optional[Dict[str, Any]]:
    """Instantánea derivada incluida en el paquete (fallback offline)."""
    try:
        d = json.loads(BUILTIN_MANIFEST.read_text(encoding="utf-8"))
        return d if d.get("ok") else None
    except Exception:
        return None


def load_cached(data_dir: Path) -> Optional[Dict[str, Any]]:
    f = data_dir / "dmd_manifest.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return d if d.get("ok") else None
    except Exception:
        return None


def save_cached(data_dir: Path, manifest: Dict[str, Any]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    f = data_dir / "dmd_manifest.json"
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(f)


def fingerprint_of(m: Optional[Dict[str, Any]]) -> str:
    if not m:
        return "sin-manifiesto"
    fp = m.get("fingerprint") or {}
    return f"{fp.get('contract')}/{fp.get('contract_rev')}·{fp.get('compiler_version')}·{fp.get('jazz_engine_version')}"


def same_dmd(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> bool:
    """¿Los dos manifiestos describen el MISMO DMD? (fingerprint + recetas)."""
    if not a or not b:
        return False
    return fingerprint_of(a) == fingerprint_of(b) and \
        (a.get("recetas") or {}) == (b.get("recetas") or {}) and \
        (a.get("catalogos") or {}) == (b.get("catalogos") or {})


def get_manifest(dmd_path: Optional[str], data_dir: Path,
                 refresh: bool = False) -> Dict[str, Any]:
    """Manifiesto efectivo: vivo → caché → builtin. Devuelve también su origen.

    Orígenes DISTINTOS (v1.1, D-09 del manual: no etiquetar caché como vivo):
      * "vivo (introspeccionado ahora)"    — el DMD se leyó en ESTA llamada.
      * "caché (misma ruta del DMD)"       — cargado del disco porque la ruta
        coincide; puede no reflejar cambios recientes del DMD (pulsa Verificar).
      * "caché (DMD no disponible ahora)"  — sin DMD descubierto.
      * "instantánea incluida (DMD no descubierto)" — fallback offline.
    """
    live = None
    if dmd_path and not refresh:
        live = load_cached(data_dir)
        if live and (live.get("manifest_meta") or {}).get("dmd_path") != dmd_path:
            live = None
        if live:
            return {**live, "origen": "caché (misma ruta del DMD)"}
    if dmd_path and (refresh or live is None):
        live = bridge.introspect(dmd_path)
        if live.get("ok"):
            save_cached(data_dir, live)
            return {**live, "origen": "vivo (introspeccionado ahora)"}
        live = None
    cached = load_cached(data_dir)
    if cached:
        return {**cached, "origen": "caché (DMD no disponible ahora)"}
    builtin = load_builtin()
    if builtin:
        return {**builtin, "origen": "instantánea incluida (DMD no descubierto)"}
    return {"ok": False, "origen": "ninguno",
            "error": "sin DMD descubierto y sin instantánea: instala/configura la ruta del DMD"}


def catalog(m: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Vistas planas que consumen builder/randomizer/UI."""
    m = m or {}
    cats = m.get("catalogos") or {}
    return {
        "instruments": cats.get("instruments") or
        ["sax_tenor", "rhodes", "vibraphone", "bass", "drums", "piano", "pad", "strings"],
        "section_types": cats.get("section_types") or
        ["intro", "verse", "pre_chorus", "chorus", "bridge", "break", "outro"],
        "drums_ladder": cats.get("drums_ladder") or ["off", "air", "light", "groove", "heavy"],
        "identities": cats.get("identities") or ["dark_triphop", "doom_triphop", "doom_dark_jazz"],
        "accessibilities": cats.get("accessibilities") or ["commercial", "balanced", "experimental"],
        "languages": cats.get("languages") or ["pop_dream_pop", "hybrid", "experimental"],
        "resolutions": cats.get("resolutions") or
        ["tonal", "modal", "deceptive", "chromatic", "open"],
        "recetas": m.get("recetas") or {},
        "perfiles": (m.get("perfiles") or {}).get("nombres") or
        ["original", "sax", "sax_rhodes", "drums", "sax_vibes", "full", "atmospheric"],
        "harmony_keywords": m.get("harmony_keywords") or [],
        "niveles_variacion": m.get("niveles_variacion") or [],
        "vocabulario_tiers": m.get("vocabulario_tiers") or {},
        "fingerprint": m.get("fingerprint") or {},
        "identidad_activa": (m.get("fingerprint") or {}).get("identidad_activa"),
        "identidades_archivadas": (m.get("fingerprint") or {}).get("identidades_archivadas") or [],
        "origen": m.get("origen"),
    }
