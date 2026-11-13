"""Utilidades compartidas de la batería de pruebas A–H."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))

from composer import bridge, manifest as MF, model, store, engine  # noqa: E402
from composer import randomizer as R, builder as B, harmony as H  # noqa: E402
#: DMD real descubierto en esta máquina (fallback: instantánea incluida).
DMD_PATH = bridge.discover_dmd(store.DATA_DIR, None)
MANIFEST = MF.get_manifest(DMD_PATH, store.DATA_DIR, refresh=False)
CAT = MF.catalog(MANIFEST)
HAS_DMD = bool(DMD_PATH)

DOC_BUILTIN = MF.load_builtin()


def new_test_project(name="Proyecto de prueba", **kw):
    """Proyecto de prueba con decisiones CANÓNICAS.

    v1.1: los tests pasaban decisiones crudas (p. ej. ``mood="dark"``) y el
    randomizador las ignoraba en silencio (el mood era siempre neutral: el
    arnés no ejercitaba la ruta real). Ahora toda decisión no-canónica se
    interpreta como FIJADA — que es la intención de cada test — y el plan
    refleja el valor. Las decisiones dict pasan tal cual.
    """
    p = model.new_project(name)
    p.pid = ""
    for k, v in kw.items():
        p.decisions[k] = v if isinstance(v, dict) else model.decision("fixed", v)
    return p


def basic_sections():
    return [
        model.Section(id="intro", label="Intro", type="intro", bars=4),
        model.Section(id="verso_1", label="Verso 1", type="verse", bars=16),
        model.Section(id="pre", label="Pre-Chorus", type="pre_chorus", bars=8),
        model.Section(id="estribillo", label="Chorus", type="chorus", bars=16, final=True),
        model.Section(id="puente", label="Bridge", type="bridge", bars=8),
        model.Section(id="outro", label="Outro", type="outro", bars=8),
    ]


def compose_project(p, seed=2026, save=False, validate=True):
    return engine.compose(p, DMD_PATH, MANIFEST, seed_override=seed, save=save, validate=validate)


def codes_out(r):
    return {e["code"] for e in r.get("errores", [])}
