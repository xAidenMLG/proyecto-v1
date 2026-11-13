"""FASE 5 — Suite de pruebas de jazz_engine y unificación Dark Trip Hop.

Ejecución:  python3 -m pytest tests/fase5 -q   (desde la raíz del proyecto)

Alcance:
  A. Unificación (identidad activa única, doom archivado no destruido).
  B. Determinismo byte a byte (5 semillas) y delegación OFF == forge puro.
  C. Sax: validez de frases (mono/rango/sección/E111), silencios, densidad,
     desarrollo de motivos (difiere del statement), objetivos armónicos.
  D. Rhodes: behaviors, tope de notas, registro, no pisa al sax.
  E. Vibes: params + ecos, presupuesto de presencia (mallet_sparse).
  F. Drums: layers válidas, fills solo en build, variación real, bass_kick.
  G. Coordinador: plan determinista, cuotas de interacción.
  H. Compatibilidad: goldens DMD intactos; JSON antiguos compilan igual.
  I. Desactivación individual y global de motores.
"""
import copy
import hashlib
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import compilador, forge_link, identities  # noqa: E402
import jazz_engine as je  # noqa: E402
from jazz_engine import coordinator, improv, motif, profiles  # noqa: E402

forge_link.import_forge()
from forge import adapter as A  # noqa: E402
from forge import engine as E  # noqa: E402
from forge import validate as V  # noqa: E402

_GOLDEN = ROOT / 'tests' / 'dmd' / 'golden' / 'dark_triphop_balanced.json'
_CFG_FULL = {"engines": {"sax": True, "rhodes": True, "drums": True, "vibes": True}, "seed": 7}


def _proyecto_base():
    doc = json.loads(_GOLDEN.read_text(encoding='utf-8'))
    return compilador.compilar(copy.deepcopy(doc))['proyecto']


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _contextos(proj, profile=None):
    profile = profile or profiles.resolve_profile('dark_triphop')
    return je.context.build_contexts(proj, profile)


def _generar(cfg=None, proj=None):
    proj = proj if proj is not None else _proyecto_base()
    return je.render.generate(copy.deepcopy(proj), cfg if cfg is not None else dict(_CFG_FULL))


class TestUnificacion(unittest.TestCase):
    """FASE 5 §11: una identidad activa; doom archivado, no destruido."""

    def test_identidad_activa_unica(self):
        self.assertEqual(identities.IDENTIDAD_ACTIVA, "dark_triphop")
        self.assertEqual(identities.es_activa("dark_triphop"), True)

    def test_doom_archivado_pero_registrado(self):
        for iid in ("doom_triphop", "doom_dark_jazz"):
            self.assertEqual(identities.estado_identidad(iid), "archivada")
            self.assertIn(iid, identities.CON_RECETA)          # receta viva (compat)
            self.assertFalse(identities.es_activa(iid))

    def test_doom_no_es_recomendado_ni_default(self):
        # el perfil activo de jazz_engine es dark_triphop
        self.assertEqual(profiles.ACTIVE_IDENTITY, "dark_triphop")

    def test_recipes_doom_siguen_cargando(self):
        from dark_director import recetas
        tabla = recetas.load_receta("doom_dark_jazz")
        self.assertEqual(recetas.verificar_completitud(tabla), ())

    def test_documentos_doom_siguen_compilando(self):
        """Compatibilidad: un JSON doom antiguo compila (archivado ≠ roto)."""
        p = ROOT / 'tests' / 'dmd' / 'golden' / 'doom_dark_jazz_experimental.json'
        doc = json.loads(p.read_text(encoding='utf-8'))
        r = compilador.compilar(copy.deepcopy(doc))
        self.assertEqual(r['proyecto']['schema'], 'midi-forge/1')


class TestDelegacionYGolden(unittest.TestCase):
    """OFF == motor puro, byte a byte; goldens intactos."""

    def test_off_es_byte_identico_a_forge(self):
        proj = _proyecto_base()
        esperado = _sha(E.generate(copy.deepcopy(proj)).midi)
        self.assertEqual(_sha(je.render.generate(copy.deepcopy(proj), None).midi), esperado)
        cfg_off = {"engines": {"sax": False, "rhodes": False, "drums": False, "vibes": False},
                   "seed": 3}
        self.assertEqual(_sha(je.render.generate(copy.deepcopy(proj), cfg_off).midi), esperado)

    def test_enhance_off_devuelve_proyecto_identico(self):
        proj = _proyecto_base()
        proj2, plan, ev = je.enhance(proj, {"engines": {"sax": False, "rhodes": False,
                                                        "drums": False, "vibes": False}})
        self.assertEqual(proj2, proj)

    def test_golden_dark_triphop_reproducible(self):
        """El path ORIGINAL dark_triphop sigue siendo determinista (protección §13)."""
        doc = json.loads(_GOLDEN.read_text(encoding='utf-8'))
        r = compilador.compilar(copy.deepcopy(doc))
        p, _ = A.normalize(copy.deepcopy(r['proyecto']), None)
        res = E.generate(p)
        p2, _ = A.normalize(copy.deepcopy(r['proyecto']), None)
        res2 = E.generate(p2)
        self.assertEqual(_sha(res.midi), _sha(res2.midi))


class TestDeterminismo(unittest.TestCase):
    """Determinismo byte a byte con varias semillas."""

    def test_cinco_semmas_byte_identicas(self):
        proj = _proyecto_base()
        for seed in (0, 1, 7, 42, 2026):
            cfg = {"engines": {"sax": True, "rhodes": True, "drums": True, "vibes": True},
                   "seed": seed}
            h1 = _sha(je.render.generate(copy.deepcopy(proj), cfg).midi)
            h2 = _sha(je.render.generate(copy.deepcopy(proj), cfg).midi)
            self.assertEqual(h1, h2, msg="seed %d no reproducible" % seed)

    def test_coordinator_plan_determinista(self):
        proj = _proyecto_base()
        profile = profiles.resolve_profile('dark_triphop')
        ctxs = _contextos(proj, profile)
        cfg = coordinator.normalize_config({"seed": 9})
        p1 = coordinator.build_plan(proj, ctxs, profile, cfg)
        p2 = coordinator.build_plan(proj, ctxs, profile, cfg)
        self.assertEqual(p1, p2)

    def test_seed_distinto_resultado_distinto(self):
        proj = _proyecto_base()
        h1 = _sha(_generar({"engines": dict(_CFG_FULL['engines']), "seed": 1}).midi)
        h2 = _sha(_generar({"engines": dict(_CFG_FULL['engines']), "seed": 2}).midi)
        self.assertNotEqual(h1, h2)


class TestSax(unittest.TestCase):
    """Frases del sax: validez E111, registro, mono, densidad, desarrollo."""

    def setUp(self):
        self.res = _generar()
        self.val = V.validate(self.res)
        self.m = je.render.metrics(self.res)

    def test_guardrails_verdes(self):
        fails = [c['id'] for c in self.val['compliance'] if c['status'] == 'fail']
        self.assertEqual(fails, [], msg=str(fails))

    def test_frases_dentro_de_seccion_y_rango(self):
        """MIS frases (no el material del compositor) respetan rango y frontera."""
        ctx = self.res.ctx
        lo, hi = 62, 81
        secciones = {s.id: s for s in ctx.secs}
        for sid, frase in self.res.plan.get('sax_phrases', {}).items():
            sec = secciones[sid]
            for n in frase:
                self.assertGreaterEqual(n['pitch'], lo, msg="%s bajo del rango" % sid)
                self.assertLessEqual(n['pitch'], hi, msg="%s alto del rango" % sid)
                self.assertGreaterEqual(n['bar'], 0)
                self.assertLess(n['bar'], sec.bars, msg="bar fuera de la sección")
                self.assertLessEqual(n['bar'] * 4.0 + n['beat'] + n['dur'], sec.bars * 4.0 + 1e-6,
                                     msg="%s cruza frontera" % sid)

    def test_intro_sin_sax(self):
        self.assertEqual(self.m['lead_por_seccion'].get('intro', 0), 0)

    def test_silencios_reales(self):
        """El sax NO toca en todas las secciones (densidad controlada)."""
        activas = self.m.get('sax_frases_activas', [])
        total = len(self.m['secciones'])
        self.assertLess(len(activas), total, msg="sax en todas las secciones")
        self.assertGreaterEqual(len(activas), 2, msg="sax ausente en todas")

    def test_cobertura_lead_baja(self):
        cover = [c for c in self.val['compliance'] if c['id'] == 'lead_coverage'][0]
        self.assertEqual(cover['status'], 'pass')

    def test_desarrollo_difiere_del_statement(self):
        res = _generar({"engines": dict(_CFG_FULL['engines']), "seed": 7})
        frases = res.plan['sax_phrases']
        if 'verse_1' in frases and len(frases) > 1:
            base = {(n['bar'], n['beat'], n['pitch']) for n in frases['verse_1']}
            otras = {sid: ns for sid, ns in frases.items() if sid != 'verse_1'}
            self.assertTrue(otras)
            for sid, ns in otras.items():
                iguales = base == {(n['bar'], n['beat'], n['pitch']) for n in ns}
                self.assertFalse(iguales, msg="%s idéntico al statement" % sid)

    def test_varias_semmas_producen_material_distinto(self):
        proj = _proyecto_base()
        frases_por_seed = []
        for seed in (1, 2, 3, 4, 5):
            res = je.render.generate(copy.deepcopy(proj),
                                     {"engines": {"sax": True, "rhodes": False, "drums": False,
                                                  "vibes": False}, "seed": seed})
            frases_por_seed.append(json.dumps(res.plan['sax_phrases'], sort_keys=True))
        self.assertGreaterEqual(len(set(frases_por_seed)), 3,
                                msg="las semillas producen material demasiado parecido")

    def test_objetivos_armonicos_en_evidencia(self):
        evid = self.res.evidence['sax']['frases']
        activas = [e for e in evid if e.get('notas', 0) > 0 and e.get('accion') != 'silencio']
        self.assertTrue(activas)
        objetivos = sum(e.get('objetivos_armonicos', 0) for e in activas)
        self.assertGreater(objetivos, 0, msg="sin objetivos armónicos")

    def test_desactivar_sax_deja_el_path_original(self):
        """Sax OFF ⇒ las notas de lead son EXACTAMENTE las del motor puro
        (desactivación = volver al comportamiento base, no silencio)."""
        proj = _proyecto_base()
        res_off = _generar({"engines": {"sax": False, "rhodes": True, "drums": True,
                                        "vibes": True}, "seed": 7}, proj)
        pn, _ = A.normalize(copy.deepcopy(proj), None)   # el path mejorado normaliza
        res_base = E.generate(pn)
        notas_off = [(round(n.t, 3), n.p, n.v) for b in res_off.bufs if b.role == 'lead' for n in b.notes]
        notas_base = [(round(n.t, 3), n.p, n.v) for b in res_base.bufs if b.role == 'lead' for n in b.notes]
        self.assertEqual(notas_off, notas_base)


class TestRhodes(unittest.TestCase):
    """Rhodes melódico: behaviors, topes, no pisa al sax."""

    def test_tope_de_notas_por_seccion(self):
        proj = _proyecto_base()
        for seed in (0, 7, 21):
            res = je.render.generate(copy.deepcopy(proj),
                                     {"engines": {"sax": True, "rhodes": True, "drums": False,
                                                  "vibes": False}, "seed": seed})
            ev = res.evidence['rhodes']
            for e in ev.get('evidencia', []):
                self.assertLessEqual(e['notas'], 8, msg="Rhodes rellena demasiado")

    def test_support_no_anade_notas(self):
        """Secciones con modo support NO tienen notas melódicas del Rhodes."""
        res = _generar()
        ev = res.evidence['rhodes']
        for e in ev.get('evidencia', []):
            if e['modo'] == 'support':
                self.assertEqual(e['notas'], 0)

    def test_rhodes_escucha_al_sax(self):
        """Los modos response/interaction exigen frases del sax previas o huecos."""
        res = _generar()
        ev = res.evidence['rhodes']
        for e in ev.get('evidencia', []):
            if e['modo'] in ('response', 'interaction') and e.get('notas', 0) > 0:
                self.assertIn(e['seccion'], res.plan.get('sax_phrases', {}),
                              msg="respuesta sin frase del sax que responder")


class TestVibes(unittest.TestCase):
    """Vibráfono: escaso, no dobla al sax, presupuesto respetado."""

    def test_guardrails_mallet(self):
        res = _generar()
        val = V.validate(res)
        for cid in ('mallet_sparse', 'lead_mallet_overlap'):
            c = [x for x in val['compliance'] if x['id'] == cid][0]
            self.assertNotEqual(c['status'], 'fail', msg=c['detail'])

    def test_ecos_solo_en_secciones_con_sax(self):
        proj = _proyecto_base()
        for seed in (0, 3, 11, 42):
            res = je.render.generate(copy.deepcopy(proj),
                                     {"engines": {"sax": True, "rhodes": False, "drums": False,
                                                  "vibes": True}, "seed": seed})
            ev = res.evidence.get('vibes_eco', {})
            for e in ev.get('evidencia', []):
                if e.get('ecos', 0) > 0:
                    self.assertIn(e['seccion'], res.plan.get('sax_phrases', {}),
                                  msg="eco sin frase del sax")


class TestDrums(unittest.TestCase):
    """Drums engine: layers válidas, fills solo build, groove intacto."""

    def test_layers_y_fills_validos(self):
        proj = _proyecto_base()
        proj2, plan, ev = je.enhance(proj, dict(_CFG_FULL))
        for sec in proj2['sections']:
            blk = sec['blocks']['drums']
            if not blk.get('enabled'):
                continue
            p = blk['params']
            for L in p.get('layers', []):
                self.assertIn('inst', L)
                self.assertTrue('at' in L or 'grid' in L or 'pick' in L)
            for f in p.get('fills', []):
                self.assertIn('when', f)

    def test_bass_kick_se_mantiene(self):
        res = _generar()
        val = V.validate(res)
        c = [x for x in val['compliance'] if x['id'] == 'bass_kick'][0]
        self.assertEqual(c['status'], 'pass', msg=c['detail'])

    def test_desactivar_drums_deja_bateria_base(self):
        proj = _proyecto_base()
        res = _generar({"engines": {"sax": True, "rhodes": False, "drums": False, "vibes": False},
                        "seed": 7}, proj)
        drm = [b for b in res.bufs if b.role == 'drums'][0]
        self.assertTrue(drm.notes)  # el preset base sigue

    def test_variacion_real_no_identica_al_base(self):
        proj = _proyecto_base()
        proj2, plan, ev = je.enhance(proj, dict(_CFG_FULL))
        cambios = [s for s in ev['drums']['secciones'] if s.get('cambios')]
        self.assertGreater(len(cambios), 0, msg="drums engine no añadió variación")


class TestCoordinator(unittest.TestCase):
    """Plan: cuotas, protagonismo, variaciones."""

    def test_cuotas_de_interaccion(self):
        proj = _proyecto_base()
        profile = profiles.resolve_profile('dark_triphop')
        ctxs = _contextos(proj, profile)
        cfg = coordinator.normalize_config({"seed": 5})
        plan = coordinator.build_plan(proj, ctxs, profile, cfg)
        interacciones = [d for d in plan['sections'].values() if d['rhodes_mode'] == 'interaction']
        self.assertLessEqual(len(interacciones), 1)

    def test_variaciones_cambian_densidad(self):
        a = coordinator.normalize_config({"variation": "melodic"})
        b = coordinator.normalize_config({"variation": "sparse"})
        self.assertGreater(a['density']['sax'], b['density']['sax'])

    def test_config_normalizada_no_muta_entrada(self):
        cfg_in = {"density": {"sax": 9.0}}
        copia = copy.deepcopy(cfg_in)
        coordinator.normalize_config(cfg_in)
        self.assertEqual(cfg_in, copia)


class TestCompatibilidad(unittest.TestCase):
    """Compatibilidad con JSON anteriores y material del compositor."""

    def test_ejemplos_fase2_compilan(self):
        ej = ROOT / 'ejemplos_fase2'
        if not ej.exists():
            self.skipTest("ejemplos_fase2 no presentes en este árbol")
        for p in sorted(ej.glob('*.json')):
            doc = json.loads(p.read_text(encoding='utf-8'))
            r = compilador.compilar(copy.deepcopy(doc))
            self.assertEqual(r['proyecto']['schema'], 'midi-forge/1', msg=p.name)

    def test_x_preservacion_no_afectada(self):
        doc = json.loads(_GOLDEN.read_text(encoding='utf-8'))
        doc['x_prueba_fase5'] = {"nota": "meta"}
        r = compilador.compilar(copy.deepcopy(doc))
        self.assertIn('x_prueba_fase5', r['proyecto']['meta']['director'])

    def test_perfil_doom_reproducible(self):
        """Los perfiles archivados siguen operables (historia reproducible)."""
        p = ROOT / 'tests' / 'dmd' / 'golden' / 'doom_triphop_balanced.json'
        if not p.exists():
            self.skipTest("golden doom ausente")
        doc = json.loads(p.read_text(encoding='utf-8'))
        proj = compilador.compilar(copy.deepcopy(doc))['proyecto']
        res = je.render.generate(copy.deepcopy(proj),
                                 {"engines": {"sax": True, "rhodes": True, "drums": True,
                                              "vibes": True}, "seed": 5})
        self.assertTrue(res.midi)
        self.assertEqual(res.plan['identity'], 'doom_triphop')

    def test_motif_transforms_deterministas(self):
        proj = _proyecto_base()
        profile = profiles.resolve_profile('dark_triphop')
        ctxs = _contextos(proj, profile)
        sc = ctxs[1]
        notas, meta = motif.generar_motivo(sc, 0, 2, random.Random('x'),
                                           profile, (62, 81), 'statement')
        n1 = motif.transformar(notas, 'displace', sc, 1, random.Random('y'),
                               profile, (62, 81))
        n2 = motif.transformar(notas, 'displace', sc, 1, random.Random('y'),
                               profile, (62, 81))
        self.assertEqual(n1, n2)

    def test_material_compositor_protegido(self):
        """Si el compositor escribe frases, el motor NO las silencia ni sustituye."""
        doc = json.loads(_GOLDEN.read_text(encoding='utf-8'))
        sid = doc['structure'][1]['id']          # segunda sección (verse)
        doc['development'] = {"melody": {"phrases": {sid: [
            {"bar": 0, "beat": 0.0, "pitch": "D4", "dur": 1.5},
            {"bar": 0, "beat": 2.0, "pitch": "F4", "dur": 1.0},
        ]}}}
        proj = compilador.compilar(copy.deepcopy(doc))['proyecto']
        res = je.render.generate(copy.deepcopy(proj), dict(_CFG_FULL))
        lead = [b for b in res.bufs if b.role == 'lead'][0]
        self.assertTrue(lead.notes, msg="material del compositor silenciado")
        pitches = {n.p for n in lead.notes}
        self.assertIn(62, pitches, msg="la frase escrita D4 no suena")


if __name__ == '__main__':
    unittest.main()
