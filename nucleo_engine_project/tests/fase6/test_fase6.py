"""FASE 6 — Suite de pruebas: Production Profiles, referencias doradas,
generalización y regresiones.

Ejecución:  python3 -m pytest tests/fase6 -q   (desde la raíz del proyecto)

Alcance:
  A. Integridad de las referencias doradas FASE 5 (manifiesto + hashes misión).
  B. Regeneración byte-idéntica vía perfiles de producción (01/07/08).
  C. Perfiles de producción: catálogo, errores claros, inmutabilidad,
     config explícita gana, idempotencia de normalización.
  D. Generalización: matriz committed sin fallos, sax no monopoliza,
     material del compositor respetado.
  E. Determinismo, motores OFF, compatibilidad doom archivada.
  F. F6-L1: comportamiento de density.sax CONGELADO (ver DECISIONS.md).
"""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import compilador, forge_link  # noqa: E402
import jazz_engine as je  # noqa: E402
from jazz_engine import coordinator as CO, production as PR  # noqa: E402

forge_link.import_forge()
from forge import adapter as A  # noqa: E402
from forge import engine as E  # noqa: E402
from forge import validate as V  # noqa: E402

_GOLDEN_DIR = ROOT / 'output' / 'fase5_comparativos'
_GEN_DIR = ROOT / 'output' / 'generalizacion_fase6'

# hashes de las referencias doradas (documento de misión FASE 6 §2.1)
HASHES_MISION = {
    '01_original': '046c94b1599e34fed228e6dd997611a27ac46835bc4946632a8cebb96d76271f',
    '02_sax': 'ecebb36d94a4499b8f50e8ddc7a2f291402a09f4372247568e9989119ce621fe',
    '03_sax_rhodes': '25a6f2234cab102eed50b71fde0d14e86e8a1318a0ac4f493a62598767e5ce47',
    '04_drums': 'cf4ebc9db2cd8b8a976b64a0861bdb4d149936266201e6dfc2fda465eb3eee89',
    '05_sax_rhodes_drums': '04fb03b87ab4314b74e78ffad8d008bfba10a326fe56e2d4de1a102ff991a383',
    '06_sax_vibes': '98dd0b576b2466cf9a529960af379a6aa7f0ff4bcdd35526b2656faf5e824355',
    '07_full': '3930cadc34ec3bcb4dc2cab9788122aa64fdbec2adf10b17b807366e70d7f228',
    '08_variation_atmospheric': '864b9302591f2655fdcdee6f3128a9b5f82464cea5b143959eb4e1e62fd18d57',
}


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _proyecto_nocturno():
    doc = json.loads((_GOLDEN_DIR / 'doc.json').read_text(encoding='utf-8'))
    return compilador.compilar(copy.deepcopy(doc))['proyecto']


def _verificar_golden():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'verificar_golden', ROOT / 'manifests' / 'verificar_golden.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.verify()


# ---------------------------------------------------------------------------
# A. Integridad de referencias doradas
# ---------------------------------------------------------------------------
class TestGolden(unittest.TestCase):

    def test_01_manifiesto_golden_integro(self):
        self.assertEqual(_verificar_golden(), 0, 'manifiesto golden_fase5.json no íntegro')

    def test_02_hashes_de_la_mision(self):
        for esc, want in HASHES_MISION.items():
            p = _GOLDEN_DIR / ('%s.mid' % esc)
            self.assertTrue(p.is_file(), 'falta referencia %s' % esc)
            self.assertEqual(_sha(p.read_bytes()), want, 'hash alterado: %s' % esc)

    def test_03_regeneracion_byte_identica_01_07_08(self):
        proj = _proyecto_nocturno()
        casos = {'01_original': 'original', '07_full': 'full',
                 '08_variation_atmospheric': 'atmospheric'}
        for esc, perfil in casos.items():
            res = je.render.generate(copy.deepcopy(proj),
                                     {"production": perfil, "seed": 2026})
            self.assertEqual(_sha(res.midi), HASHES_MISION[esc],
                             'regeneración no idéntica: %s' % esc)

    def test_04_experimental_no_altera_golden(self):
        # generar y escribir SOLO en memoria/tmp; el golden queda intacto
        proj = _proyecto_nocturno()
        res = je.render.generate(copy.deepcopy(proj),
                                 {"production": "full", "seed": 999})
        self.assertTrue(res.midi)
        self.assertEqual(_verificar_golden(), 0)


# ---------------------------------------------------------------------------
# B/C. Perfiles de producción
# ---------------------------------------------------------------------------
class TestProductionProfiles(unittest.TestCase):

    def test_05_catalogo_perfiles(self):
        self.assertEqual(PR.nombres(), ('original', 'sax', 'sax_rhodes', 'drums',
                                        'sax_vibes', 'full', 'atmospheric'))

    def test_06_perfil_desconocido_error_claro(self):
        with self.assertRaises(ValueError) as ctx:
            CO.normalize_config({"production": "jazz_latino"})
        self.assertIn('jazz_latino', str(ctx.exception))
        self.assertIn('full', str(ctx.exception))

    def test_07_original_no_admite_overrides(self):
        with self.assertRaises(ValueError):
            CO.normalize_config({"production": "original",
                                 "engines": {"sax": True}})
        # seed sí está permitida
        cfg = CO.normalize_config({"production": "original", "seed": 5})
        self.assertEqual(cfg['engines'], {})

    def test_08_presets_inmutables(self):
        a = PR.resolver('full')
        a['engines']['sax'] = False
        b = PR.resolver('full')
        self.assertTrue(b['engines']['sax'])
        # mutar un perfil no contamina a otro
        c = PR.resolver('sax')
        c['engines']['rhodes'] = True
        self.assertFalse(PR.resolver('sax')['engines']['rhodes'])

    def test_09_config_explicita_gana_sobre_preset(self):
        cfg = CO.normalize_config({"production": "full",
                                   "engines": {"rhodes": False}, "seed": 3})
        self.assertTrue(cfg['engines']['sax'])
        self.assertFalse(cfg['engines']['rhodes'])
        self.assertTrue(cfg['engines']['drums'])

    def test_10_atmospheric_preset_aplica_variation(self):
        cfg = CO.normalize_config({"production": "atmospheric", "seed": 1})
        self.assertEqual(cfg['variation'], 'atmospheric')
        self.assertAlmostEqual(cfg['density']['drums'], 0.75, places=6)

    def test_11_normalizacion_estable_dos_pasadas(self):
        """render→enhance re-normaliza; el perfil debe sobrevivir igual."""
        una = CO.normalize_config({"production": "sax", "seed": 7})
        dos = CO.normalize_config(una)
        self.assertEqual(una['engines'], dos['engines'])
        self.assertEqual(una['production'], dos['production'])
        self.assertEqual(una['density'], dos['density'])


# ---------------------------------------------------------------------------
# D. Generalización (artefactos de la matriz committed)
# ---------------------------------------------------------------------------
class TestGeneralizacion(unittest.TestCase):

    COMPS = ('nocturno_terminal', 'medianoche_puerto_nuevo', 'calles_de_neon',
             'habitacion_314', 'casa_de_espejos')

    def test_12_matriz_completa_sin_fallos(self):
        total = 0
        for comp in self.COMPS:
            d = _GEN_DIR / comp
            evs = sorted(d.glob('evidencia_*.json'))
            self.assertTrue(evs, 'sin evidencias en %s' % comp)
            for ev in evs:
                data = json.loads(ev.read_text(encoding='utf-8'))
                self.assertEqual(data['fallos'], [],
                                 '%s: %s → %s' % (comp, ev.name, data['fallos']))
                self.assertTrue(data['checks']['determinismo'])
                total += 1
        self.assertGreaterEqual(total, 30)

    def test_13_sax_no_monopoliza_ninguna_composicion(self):
        for comp in self.COMPS:
            ev = json.loads((_GEN_DIR / comp / 'evidencia_full.json')
                            .read_text(encoding='utf-8'))
            share = ev['checks']['sax_share']
            self.assertLessEqual(share, 0.85, '%s: sax monopoliza (%.2f)' % (comp, share))

    def test_14_material_compositor_respetado(self):
        doc = json.loads((_GEN_DIR / 'calles_de_neon' / 'doc.json').read_text(encoding='utf-8'))
        proj = compilador.compilar(copy.deepcopy(doc))['proyecto']
        res = je.render.generate(copy.deepcopy(proj),
                                 {"production": "full", "seed": 9021})
        respetadas = set(res.evidence['sax']['respetadas_material_compositor'])
        self.assertEqual(respetadas, {'verse_1', 'chorus_1', 'verse_2'})
        frases = set((res.plan.get('sax_phrases') or {}).keys())
        self.assertFalse(frases & respetadas,
                         'el sax engine escribió sobre material del compositor')


# ---------------------------------------------------------------------------
# E. Determinismo / OFF / compatibilidad
# ---------------------------------------------------------------------------
class TestRegresion(unittest.TestCase):

    def test_15_determinismo_semillas(self):
        proj = _proyecto_nocturno()
        for seed in (1, 2026, 7777):
            r1 = je.render.generate(copy.deepcopy(proj),
                                    {"production": "full", "seed": seed})
            r2 = je.render.generate(copy.deepcopy(proj),
                                    {"production": "full", "seed": seed})
            self.assertEqual(_sha(r1.midi), _sha(r2.midi), 'seed %d no determinista' % seed)

    def test_16_motores_off_proyecto_original(self):
        proj = _proyecto_nocturno()
        base = E.generate(copy.deepcopy(proj)).midi
        off = je.render.generate(copy.deepcopy(proj),
                                 {"engines": {"sax": False, "rhodes": False,
                                              "drums": False, "vibes": False},
                                  "seed": 5})
        self.assertEqual(_sha(base), _sha(off.midi))
        # config None también delega
        self.assertEqual(_sha(base),
                         _sha(je.render.generate(copy.deepcopy(proj), None).midi))

    def test_17_doom_archivado_operable(self):
        doc = {"schema": "dark-director/1",
               "meta": {"title": "Compat doom"},
               "direction": {"identity": "doom_triphop", "accessibility": "balanced"},
               "global": {"bpm": 74, "seed": 11},
               "harmony": {"key": "D minor", "language": "hybrid",
                           "harmonic_rhythm_bars": 1,
                           "progressions": {"verse": ["Dm9", "Bb13", "Fmaj9", "C9"]}},
               "structure": [
                   {"id": "v1", "type": "verse", "bars": 8, "energy": 0.5,
                    "tension": 0.5, "density": 0.5, "focus": ["sax_tenor"]},
                   {"id": "c1", "type": "chorus", "bars": 8, "energy": 0.8,
                    "tension": 0.6, "density": 0.6, "focus": ["sax_tenor"],
                    "final": True}]}
        proj = compilador.compilar(copy.deepcopy(doc))['proyecto']
        res = je.render.generate(copy.deepcopy(proj),
                                 {"production": "full", "seed": 11})
        val = V.validate(res)
        fails = [c['id'] for c in val['compliance'] if c['status'] == 'fail']
        self.assertEqual(fails, [])
        self.assertEqual(res.plan['identity'], 'doom_triphop')

    def test_18_f6l1_density_sax_congelado(self):
        """F6-L1 (DECISIONS.md): density.sax NO afecta a la actividad del sax en
        el scheduler actual. COMPORTAMIENTO CONGELADO para no alterar los
        perfiles aprobados en FASE 5 (08_atmospheric depende de esto). Si este
        test falla porque se conectó density.sax, la corrección requiere
        revisión versionada + nueva validación auditiva del usuario."""
        proj = _proyecto_nocturno()
        cfg = {"engines": {"sax": True, "rhodes": False, "drums": False,
                           "vibes": False}, "seed": 2026, "density": {"sax": 0.0}}
        res = je.render.generate(copy.deepcopy(proj), cfg)
        self.assertGreater(res.evidence['sax']['secciones_con_sax'], 0,
                           'density.sax ahora afecta al scheduler: ver DECISIONS F6-L1')


if __name__ == '__main__':
    unittest.main()
