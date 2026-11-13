"""FASE 7 — Suite de pruebas: Harmonic Familiarity Engine.

Ejecución:  python3 -m pytest tests/fase7 -q   (desde la raíz del proyecto)

Alcance (misión FASE 7 §9):
  A. Biblioteca: integridad del esquema, gramática de grados (sin melodías),
     vocabulario cerrado de variaciones, extensión vía JSON externo.
  B. Búsqueda: por keyword (todos los oficiales), por ID, errores claros,
     determinismo de la selección.
  C. Adaptación: tonalidades y modos distintos, coherencia diatónica, huella
     del arquetipo, ancla intacta, presupuesto de transformaciones.
  D. Estructuras: secciones cortas/largas, compacta, giro de turnaround,
     transiciones entre secciones (cola de aproximación).
  E. Integración: determinismo byte a byte, camino base intocado (hash FASE 6),
     material del compositor respetado, original+harmony rechazado,
     compatibilidad con los 7 perfiles, contrato sin cambios.
  F. Dorados: regeneración byte-idéntica de 01/07 y hashes de disco.
"""
import copy
import hashlib
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import compilador, contract, forge_link, validador  # noqa: E402
import jazz_engine as je  # noqa: E402
from jazz_engine import harmony_adapt as AD  # noqa: E402
from jazz_engine import harmony_library as HL  # noqa: E402
from jazz_engine import harmony_select as SEL  # noqa: E402

forge_link.import_forge()
from forge import adapter as A  # noqa: E402
from forge import engine as E  # noqa: E402
from forge import theory as T  # noqa: E402
from forge import validate as V  # noqa: E402

_GOLDEN_DIR = ROOT / 'output' / 'fase5_comparativos'
_GEN_DIR = ROOT / 'output' / 'generalizacion_fase6'

# hashes de la misión FASE 6 (los dorados NO cambian en FASE 7)
HASH_01 = '046c94b1599e34fed228e6dd997611a27ac46835bc4946632a8cebb96d76271f'
HASH_07 = '3930cadc34ec3bcb4dc2cab9788122aa64fdbec2adf10b17b807366e70d7f228'
HASH_08 = '864b9302591f2655fdcdee6f3128a9b5f82464cea5b143959eb4e1e62fd18d57'
HASH_C1_MEDIANOCHE_FULL = '32199acc254a2eeff93a12d15df3b38ec2c541a45a10a4719d493c696b29a9ff'

COMPOS = ['nocturno_terminal', 'medianoche_puerto_nuevo', 'calles_de_neon',
          'habitacion_314', 'casa_de_espejos']


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _proyecto(nombre):
    doc = json.loads((_GEN_DIR / nombre / 'doc.json').read_text(encoding='utf-8'))
    return compilador.compilar(copy.deepcopy(doc))['proyecto']


def _proyecto_nocturno():
    doc = json.loads((_GOLDEN_DIR / 'doc.json').read_text(encoding='utf-8'))
    return compilador.compilar(copy.deepcopy(doc))['proyecto']


def _normaliza_kw(kw, seed=1, **extra):
    return SEL.normalizar_activacion(dict(keyword=kw, seed=seed, **extra))


# ============================================================================
# A. Biblioteca
# ============================================================================
class TestBiblioteca(unittest.TestCase):
    def setUp(self):
        self.lib = HL.biblioteca()

    def test_a1_catalogo_minimo(self):
        """Biblioteca útil y ampliable: ≥40 progresiones en 6 familias."""
        self.assertGreaterEqual(len(self.lib), 40)
        familias = {e['familia'] for e in self.lib.values()}
        self.assertEqual(familias, set(HL.FAMILIAS))

    def test_a2_ids_unicos_y_esquema(self):
        for pid, e in self.lib.items():
            self.assertEqual(pid, e['id'])
            for campo in ('nombre', 'keywords', 'familia', 'funcion', 'modo',
                          'grados', 'emociones', 'familiaridad', 'tension',
                          'resolucion', 'estructura', 'variaciones', 'ritmo',
                          'referencias', 'tipo_ref'):
                self.assertIn(campo, e, '%s sin %s' % (pid, campo))
            self.assertTrue(0.0 <= e['familiaridad'] <= 1.0)
            self.assertTrue(0.0 <= e['tension'] <= 1.0)
            self.assertTrue(0.0 <= e['resolucion'] <= 1.0)

    def test_a3_sin_melodias_solo_grados(self):
        """No hay material protegido: solo tokens de grado (gramática)."""
        for pid, e in self.lib.items():
            self.assertTrue(2 <= len(e['grados']) <= 8, pid)
            for tok in e['grados']:
                rom, acc, suf, sl = HL.validar_grado(tok)   # ValueError si no
                self.assertIn(rom.upper(), HL.ROMAN_INDEX, pid)
                self.assertIn(suf, HL.SUFIJOS, pid)

    def test_a4_variaciones_en_vocabulario(self):
        for pid, e in self.lib.items():
            for v in e['variaciones']:
                self.assertIn(v, HL.VOCABULARIO_VARIACIONES, pid)
            self.assertTrue(set(e['estructura']) <= set(HL.TIPOS_ESTRUCTURA), pid)

    def test_a5_progresiones_de_la_mision_presentes(self):
        """Las 8 secuencias listadas en la misión §4 existen como entradas."""
        limpio = lambda tok: tok.rstrip('97231').replace('maj7', '').replace('maj9', '')
        expect = {
            'familiaridad_pop': {('I', 'V', 'vi', 'IV'), ('vi', 'IV', 'I', 'V'),
                                 ('I', 'vi', 'IV', 'V'), ('I', 'IV', 'V', 'IV')},
            'melancolia_nostalgia': {('I', 'iii', 'IV', 'iv')},
            'oscuridad_cinematografica': {('i', 'VI', 'III', 'VII'),
                                          ('i', 'iv', 'VI', 'V'),
                                          ('i', 'VII', 'VI', 'VII')},
        }
        vistos = {}
        for e in self.lib.values():
            vistos.setdefault(e['familia'], set()).add(
                tuple(limpio(t) for t in e['grados']))
        for fam, progs in expect.items():
            for p in progs:
                self.assertIn(p, vistos[fam], '%s sin %s' % (fam, p))

    def test_a6_keywords_oficiales_cubiertos(self):
        """Todo keyword oficial simple encuentra entradas (búsqueda directa)."""
        for kw in ('familiar_pop', 'melancholic', 'nostalgic', 'dark_cinematic',
                   'dream_pop', 'alternative', 'soulful'):
            HL.buscar_por_keyword(self.lib, kw)          # KeyError si vacío

    def test_a7_extension_json_externo(self):
        """Añadir progresiones SIN tocar el motor: JSON externo validado igual."""
        nueva = {"progressiones": [{
            "id": "XX01", "nombre": "Prueba Externa", "keywords": ["test"],
            "familia": "familiaridad_pop", "funcion": "prueba", "modo": "mayor",
            "grados": ["I", "IV"], "emociones": ["t"], "familiaridad": 0.5,
            "tension": 0.4, "resolucion": 0.6, "estructura": ["verse"],
            "variaciones": ["colas_extra"], "ritmo": 1,
            "referencias": "prueba unitaria", "tipo_ref": "variacion_original"}]}
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                         encoding='utf-8') as fh:
            json.dump(nueva, fh)
            ruta = fh.name
        try:
            lib2 = HL.biblioteca(ruta)
            self.assertIn('XX01', lib2)
            self.assertIn('POP01', lib2)
        finally:
            Path(ruta).unlink(missing_ok=True)
        dup = dict(nueva['progressiones'][0], id='POP01')
        with self.assertRaises(ValueError):
            HL.biblioteca({'progressiones': [dup]})

    def test_a8_entrada_invalida_error_claro(self):
        mala = dict(self.lib['POP01'], grados=['I', 'Z9'])
        with self.assertRaises(ValueError):
            HL.validar_entrada(mala)
        mala2 = dict(self.lib['POP01'], variaciones=['no_existe'])
        with self.assertRaises(ValueError):
            HL.validar_entrada(mala2)


# ============================================================================
# B. Búsqueda / selección
# ============================================================================
class TestSeleccion(unittest.TestCase):
    def setUp(self):
        self.lib = HL.biblioteca()
        self.proj = _proyecto('medianoche_puerto_nuevo')
        self.tonico, self.modo, self.info = je.harmony._tipo_y_drama(self.proj)

    def test_b1_keyword_desconocido_valueerror(self):
        with self.assertRaises(ValueError) as cm:
            SEL.normalizar_activacion({'keyword': 'no_existe'})
        self.assertIn('dark_cinematic', str(cm.exception))

    def test_b2_id_desconocido_error_claro(self):
        with self.assertRaises(KeyError) as cm:
            HL.por_id(self.lib, 'NOPE99')
        self.assertIn('CINE01', str(cm.exception))

    def test_b3_keyword_y_id_a_la_vez_rechazado(self):
        with self.assertRaises(ValueError):
            SEL.normalizar_activacion({'keyword': 'soulful', 'id': 'CINE01'})

    def test_b4_claves_desconocidas_rechazadas(self):
        with self.assertRaises(ValueError):
            SEL.normalizar_activacion({'magia': True})

    def test_b5_activacion_vacia_rechazada(self):
        with self.assertRaises(ValueError):
            SEL.normalizar_activacion({})

    def test_b6_defaults_de_activacion(self):
        act = SEL.normalizar_activacion({'keyword': 'soulful'}, seed_base=3113)
        self.assertEqual(act['seed'], 3113)             # hereda seed de motores
        self.assertEqual(act['variacion'], 'subtle')
        self.assertTrue(act['respetar_material'])

    def test_b7_seleccion_por_tipo_con_recurrencia(self):
        """Una progresión por TIPO: las apariciones del mismo tipo comparten."""
        act = _normaliza_kw('dark_cinematic', 77)
        eleccion, ev = SEL.seleccionar(self.lib, self.info, self.tonico,
                                       self.modo, act)
        tipos = {m['tipo'] for m in self.info}
        self.assertEqual(set(eleccion), tipos)
        verses = [m['id'] for m in self.info if m['tipo'] == 'verse']
        self.assertGreater(len(verses), 1)              # hay recurrencia real

    def test_b8_seleccion_determinista(self):
        act = _normaliza_kw('familiarity_auto', 5)
        e1, _ = SEL.seleccionar(self.lib, self.info, self.tonico, self.modo, act)
        e2, _ = SEL.seleccionar(self.lib, self.info, self.tonico, self.modo, act)
        self.assertEqual({t: v['id'] for t, v in e1.items()},
                         {t: v['id'] for t, v in e2.items()})

    def test_b9_pins_por_tipo(self):
        act = SEL.normalizar_activacion({'progressions': {'verse': 'CINE07',
                                                          'chorus': 'CINE02'}})
        eleccion, _ = SEL.seleccionar(self.lib, self.info, self.tonico,
                                      self.modo, act)
        self.assertEqual(eleccion['verse']['id'], 'CINE07')
        self.assertEqual(eleccion['chorus']['id'], 'CINE02')

    def test_b10_pin_id_inexistente_error(self):
        act = SEL.normalizar_activacion({'progressions': {'verse': 'NOPE99'}})
        with self.assertRaises(KeyError):
            SEL.seleccionar(self.lib, self.info, self.tonico, self.modo, act)

    def test_b11_por_id_aplica_a_todos_los_tipos(self):
        act = SEL.normalizar_activacion({'id': 'CINE01', 'seed': 3})
        eleccion, _ = SEL.seleccionar(self.lib, self.info, self.tonico,
                                      self.modo, act)
        self.assertEqual({v['id'] for v in eleccion.values()}, {'CINE01'})

    def test_b12_cuota_de_progresiones_distintas(self):
        """Una canción vive de 2-4 progresiones: cuota máxima por canción."""
        proj = _proyecto('nocturno_terminal')
        tonico, modo, info = je.harmony._tipo_y_drama(proj)
        act = _normaliza_kw('dark_cinematic', 77)
        eleccion, ev = SEL.seleccionar(self.lib, info, tonico, modo, act)
        self.assertLessEqual(len({v['id'] for v in eleccion.values()}),
                             SEL.CUOTA_DISTINTAS)
        self.assertTrue(any('cuota' in a for a in ev['avisos']))
        # determinismo de la reasignación
        e2, _ = SEL.seleccionar(self.lib, info, tonico, modo, act)
        self.assertEqual({t: v['id'] for t, v in eleccion.items()},
                         {t: v['id'] for t, v in e2.items()})


# ============================================================================
# C. Adaptación
# ============================================================================
class TestAdaptacion(unittest.TestCase):
    def setUp(self):
        self.lib = HL.biblioteca()

    def test_c1_tonalidades_distintas(self):
        """Grados → tonalidad real: i–VI–III–VII en 5 tonalidades menores."""
        e = self.lib['CINE01']
        esperado = {(2, 'aeolian'): ['Dm', 'Bb', 'F', 'C'],
                    (9, 'aeolian'): ['Am', 'F', 'C', 'G'],
                    (6, 'aeolian'): ['F#m', 'D', 'A', 'E'],
                    (7, 'aeolian'): ['Gm', 'Eb', 'Bb', 'F'],
                    (0, 'aeolian'): ['Cm', 'Ab', 'Eb', 'Bb']}
        sec = {'id': 's', 'bars': 8, 'chord_bars': 2, 'type': 'verse',
               'final': False}
        for (tonico, modo), simbs in esperado.items():
            out, _log = AD.adaptar(e, tonico, modo, sec, 'none', random.Random(1))
            self.assertEqual(out, simbs, '%d %s' % (tonico, modo))

    def test_c2_modo_mayor(self):
        """I–V–vi–IV en Do mayor = C, G, Am, F."""
        sec = {'id': 's', 'bars': 8, 'chord_bars': 2, 'type': 'verse',
               'final': False}
        out, _log = AD.adaptar(self.lib['POP01'], 0, 'ionian', sec, 'none',
                               random.Random(1))
        self.assertEqual(out, ['C', 'G', 'Am', 'F'])

    def test_c3_relajacion_de_modo_diatonica(self):
        """Progresión mayor sobre composición menor: diatónica y reconocible."""
        sec = {'id': 's', 'bars': 8, 'chord_bars': 2, 'type': 'verse',
               'final': False}
        out, _log = AD.adaptar(self.lib['POP01'], 2, 'aeolian', sec, 'none',
                               random.Random(1))
        self.assertEqual(out, ['Dm', 'A', 'Bb', 'Gm'])   # i–V–VI–iv
        pcs = T.scale_pcs(2, 'aeolian')
        for s in out:
            self.assertIn(T.parse_chord(s).root, pcs)

    def test_c4_todos_los_simbolos_parsean_con_forge(self):
        """Vocabulario exacto de forge.theory, 44 entradas × 4 contextos."""
        claves = [(2, 'aeolian'), (0, 'ionian'), (6, 'aeolian'), (2, 'dorian')]
        sec = {'id': 's', 'bars': 8, 'chord_bars': 1, 'type': 'verse',
               'final': False}
        for pid in sorted(self.lib):
            e = self.lib[pid]
            for tonico, modo in claves:
                for var in HL.NIVELES_VARIACION:
                    out, _log = AD.adaptar(e, tonico, modo, sec, var,
                                           random.Random(3))
                    for s in out:
                        cs = s['chord'] if isinstance(s, dict) else s
                        _ch, err = T.safe_chord(cs, tonico)
                        self.assertIsNone(err, '%s %s %s' % (pid, var, cs))

    def test_c5_ancla_intacta_en_subtle(self):
        """Familiaridad: la RAÍZ del primer acorde nunca cambia (≤ rich)."""
        sec = {'id': 's', 'bars': 8, 'chord_bars': 1, 'type': 'verse',
               'final': False}
        for pid in sorted(self.lib):
            e = self.lib[pid]
            base, _ = AD.adaptar(e, 2, 'aeolian', sec, 'none', random.Random(0))
            r_base = T.parse_chord(base[0]).root
            for var in ('subtle', 'medium'):
                out, _log = AD.adaptar(e, 2, 'aeolian', sec, var,
                                       random.Random(11))
                self.assertEqual(T.parse_chord(out[0]['chord']
                                               if isinstance(out[0], dict)
                                               else out[0]).root, r_base,
                                 '%s: ancla cambiada en %s' % (pid, var))

    def test_c6_presupuesto_de_transformaciones(self):
        """medium ≤2 estructurales, rich ≤3 (extensiones tienen tope propio)."""
        sec = {'id': 's', 'bars': 32, 'chord_bars': 1, 'type': 'verse',
               'final': False}
        for var, tope in (('medium', 2), ('rich', 3)):
            for pid in sorted(self.lib):
                e = self.lib[pid]
                for seed in range(4):
                    _out, log = AD.adaptar(e, 2, 'aeolian', sec, var,
                                           random.Random(seed))
                    estructurales = [t for t in log['transformaciones']
                                     if t['tipo'] not in ('extension', 'sus_flavor',
                                                          'ajuste_estructura',
                                                          'cola_aproximacion')]
                    self.assertLessEqual(len(estructurales), tope,
                                         '%s %s seed %d' % (pid, var, seed))

    def test_c7_variacion_controlada(self):
        """none es el arquetipo puro; rich lo transforma sin romperlo."""
        sec = {'id': 's', 'bars': 16, 'chord_bars': 1, 'type': 'verse',
               'final': False}
        # SOUL04 en C: el ciclo puro del turnaround R&B
        out_none, _ = AD.adaptar(self.lib['SOUL04'], 0, 'ionian', sec, 'none',
                                 random.Random(2))
        self.assertEqual(out_none[:4], ['Cmaj7', 'Am7', 'Dm7', 'G7'])
        # POP01 (con extensiones+sus en su vocabulario): rich ≠ none
        pop_none, _ = AD.adaptar(self.lib['POP01'], 0, 'ionian', sec, 'none',
                                 random.Random(2))
        self.assertEqual(pop_none[:4], ['C', 'G', 'Am', 'F'])
        pop_rich, log = AD.adaptar(self.lib['POP01'], 0, 'ionian', sec, 'rich',
                                   random.Random(2))
        self.assertNotEqual(pop_none, pop_rich)
        self.assertTrue(log['transformaciones'])
        self.assertGreaterEqual(log['huella_arquetipo'], 0.5)

    def test_c8_resolucion_deceptiva_solo_en_final(self):
        sec = {'id': 's', 'bars': 8, 'chord_bars': 2, 'type': 'outro',
               'final': False}
        # MEL02 (i–VII–VI–V) declara resolucion_deceptiva; sin final: V mayor
        out, _log = AD.adaptar(self.lib['MEL02'], 2, 'aeolian', sec, 'none',
                               random.Random(5))
        self.assertEqual(out, ['Dm', 'C', 'Bb', 'A'])
        secf = dict(sec, final=True)
        hits = 0
        for seed in range(12):
            out, log = AD.adaptar(self.lib['MEL02'], 2, 'aeolian', secf,
                                  'medium', random.Random(seed))
            if out[-1] == 'Bb' and any(t['tipo'] == 'resolucion_deceptiva'
                                       for t in log['transformaciones']):
                hits += 1
        self.assertGreater(hits, 0)                      # V→VI deceptiva posible

    def test_c9_determinismo_de_adaptacion(self):
        sec = {'id': 's', 'bars': 16, 'chord_bars': 1, 'type': 'verse',
               'final': False}
        for pid in ('POP07', 'CINE03', 'SOUL06', 'DREAM06'):
            e = self.lib[pid]
            a, _ = AD.adaptar(e, 9, 'aeolian', sec, 'medium', random.Random(99))
            b, _ = AD.adaptar(e, 9, 'aeolian', sec, 'medium', random.Random(99))
            self.assertEqual(a, b, pid)

    def test_c10_inversiones_usan_vocabulario_forge(self):
        """Las inversiones /3 son notas del acorde (teoría de forge, no propia)."""
        sec = {'id': 's', 'bars': 32, 'chord_bars': 1, 'type': 'bridge',
               'final': False}
        encontradas = 0
        for pid in sorted(self.lib):
            e = self.lib[pid]
            for seed in range(8):
                out, _log = AD.adaptar(e, 0, 'ionian', sec, 'rich',
                                       random.Random(seed))
                for s in out:
                    cs = s['chord'] if isinstance(s, dict) else s
                    if '/' in cs:
                        ch, err = T.safe_chord(cs, 0)
                        self.assertIsNone(err, cs)
                        encontradas += 1
        self.assertGreater(encontradas, 0)


# ============================================================================
# D. Estructuras y transiciones
# ============================================================================
class TestEstructuras(unittest.TestCase):
    def setUp(self):
        self.lib = HL.biblioteca()

    def test_d1_largos_de_seccion(self):
        """2/4/8/16/64 compases con cb 1 y 2: símbolos válidos siempre."""
        e = self.lib['CINE01']
        for bars, cb in ((4, 2), (4, 1), (8, 2), (16, 1), (64, 1), (2, 1)):
            sec = {'id': 's', 'bars': bars, 'chord_bars': cb, 'type': 'verse',
                   'final': False}
            out, log = AD.adaptar(e, 9, 'aeolian', sec, 'medium', random.Random(1))
            slots = max(1, int(round(bars / cb)))
            self.assertLessEqual(len(out), slots + 1)     # +1 cola rich
            for s in out:
                cs = s['chord'] if isinstance(s, dict) else s
                _ch, err = T.safe_chord(cs, 9)
                self.assertIsNone(err, cs)

    def test_d2_compacta_conserva_ancla_y_cadencia(self):
        """4 acordes en 2 slots: ancla + cadencia (nunca truncamiento ciego)."""
        sec = {'id': 's', 'bars': 4, 'chord_bars': 2, 'type': 'verse',
               'final': False}
        out, log = AD.adaptar(self.lib['CINE01'], 9, 'aeolian', sec, 'none',
                              random.Random(1))
        self.assertEqual(len(out), 2)
        self.assertEqual(out, ['Am', 'G'])          # i (ancla) + VII (cadencia)
        self.assertEqual(log['transformaciones'][0]['tipo'], 'ajuste_estructura')

    def test_d3_giro_de_turnaround(self):
        """slots % len ≠ 0: el ciclo se completa con giro y cierra en cadencia."""
        sec = {'id': 's', 'bars': 6, 'chord_bars': 1, 'type': 'verse',
               'final': False}
        out, log = AD.adaptar(self.lib['CINE01'], 9, 'aeolian', sec, 'none',
                              random.Random(1))
        self.assertEqual(len(out), 6)
        ajustes = [t for t in log['transformaciones']
                   if t['tipo'] == 'ajuste_estructura']
        self.assertTrue(ajustes and ajustes[0]['detalle'].startswith('giro'))
        self.assertEqual(out[-1], 'E7')             # cierra en la cadencia (V7)

    def test_d4_cola_de_aproximacion_a_seccion_siguiente(self):
        """rich + dominante_secundaria: mitad + aproximación V7 del acorde real."""
        sec = {'id': 's', 'bars': 8, 'chord_bars': 2, 'type': 'verse',
               'final': False}
        e = self.lib['POP08']                       # ii–V–I con dominante_secundaria
        out, log = AD.adaptar(e, 2, 'aeolian', sec, 'rich', random.Random(0),
                              primer_simbolo_siguiente='Dm')
        colas = [t for t in log['transformaciones']
                 if t['tipo'] == 'cola_aproximacion']
        for c in colas:
            self.assertEqual(c['sabor'], 'dominante_secundaria')
            ultimo = out[-1]
            self.assertIsInstance(ultimo, dict)
            self.assertEqual(ultimo['chord'], 'A7')  # V7 de Dm
            self.assertEqual(ultimo['bars'], 1.0)

    def test_d5_cola_no_en_seccion_final(self):
        sec = {'id': 's', 'bars': 8, 'chord_bars': 2, 'type': 'outro',
               'final': True}
        out, log = AD.adaptar(self.lib['POP08'], 2, 'aeolian', sec, 'rich',
                              random.Random(0), primer_simbolo_siguiente='Dm')
        self.assertFalse(any(t['tipo'] == 'cola_aproximacion'
                             for t in log['transformaciones']))

    def test_d6_huella_del_arquetipo_registrada(self):
        sec = {'id': 's', 'bars': 16, 'chord_bars': 1, 'type': 'verse',
               'final': False}
        for pid in ('POP01', 'CINE02', 'SOUL04'):
            e = self.lib[pid]
            for var in HL.NIVELES_VARIACION:
                _out, log = AD.adaptar(e, 9, 'aeolian', sec, var,
                                       random.Random(3))
                self.assertIn('huella_arquetipo', log)
                self.assertGreaterEqual(log['huella_arquetipo'],
                                        AD.UMBRAL_HUELLA[var] - 1e-9,
                                        '%s %s' % (pid, var))


# ============================================================================
# E. Integración con el pipeline
# ============================================================================
class TestIntegracion(unittest.TestCase):
    def test_e1_determinismo_byte_a_byte(self):
        proj = _proyecto('medianoche_puerto_nuevo')
        cfg = {'production': 'full', 'seed': 3113,
               'harmony': {'keyword': 'dark_cinematic', 'seed': 77,
                           'variacion': 'medium'}}
        r1 = je.render.generate(copy.deepcopy(proj), cfg)
        r2 = je.render.generate(copy.deepcopy(proj), cfg)
        self.assertEqual(_sha(r1.midi), _sha(r2.midi))

    def test_e2_camino_base_intocado_hash_fase6(self):
        """Sin harmony: byte-idéntico al full aprobado en FASE 6 (C1)."""
        proj = _proyecto('medianoche_puerto_nuevo')
        res = je.render.generate(copy.deepcopy(proj),
                                 {'production': 'full', 'seed': 3113})
        self.assertEqual(_sha(res.midi), HASH_C1_MEDIANOCHE_FULL)

    def test_e3_generar_sin_config_delega_en_forge(self):
        """config=None delega 1:1 a forge.engine.generate (garantía FASE 5/6);
        el hash 01 del camino ORIGINAL se prueba en test_f4."""
        proj = _proyecto('nocturno_terminal')
        a = je.render.generate(copy.deepcopy(proj), None)
        b = je.render.generate(copy.deepcopy(proj), None)
        self.assertEqual(_sha(a.midi), _sha(b.midi))
        c = E.generate(copy.deepcopy(proj))
        self.assertEqual(_sha(a.midi), _sha(c.midi))

    def test_e4_original_mas_harmony_rechazado(self):
        proj = _proyecto('nocturno_terminal')
        with self.assertRaises(ValueError) as cm:
            je.render.generate(copy.deepcopy(proj),
                               {'production': 'original',
                                'harmony': {'keyword': 'soulful'}})
        self.assertIn('ORIGINAL', str(cm.exception))

    def test_e5_input_no_mutado(self):
        proj = _proyecto('medianoche_puerto_nuevo')
        antes = json.dumps(proj, sort_keys=True, ensure_ascii=False)
        je.render.generate(copy.deepcopy(proj),
                           {'production': 'full', 'seed': 3113,
                            'harmony': {'keyword': 'dream_pop', 'seed': 8}})
        self.assertEqual(antes, json.dumps(proj, sort_keys=True,
                                           ensure_ascii=False))

    def test_e6_material_del_compositor_respetado(self):
        """calles_de_neon: los versos/coro escritos conservan su armonía exacta."""
        proj = _proyecto('calles_de_neon')
        orig = {s['id']: list(s['chords']) for s in proj['sections']}
        proj7, ev = je.harmony.aplicar(
            proj, _normaliza_kw('familiar_pop', 9, variacion='medium'))
        material = {'verse_1', 'verse_2', 'chorus_1'}
        self.assertEqual(set(ev['respetadas_material']), material)
        for s in proj7['sections']:
            if s['id'] in material:
                self.assertEqual(list(s['chords']), orig[s['id']],
                                 'material del compositor alterado: %s' % s['id'])
            else:
                self.assertNotEqual(list(s['chords']), orig[s['id']])

    def test_e7_respetar_material_false_reescribe(self):
        proj = _proyecto('calles_de_neon')
        act = SEL.normalizar_activacion({'keyword': 'soulful', 'seed': 4,
                                         'respetar_material': False}, 9021)
        _proj7, ev = je.harmony.aplicar(proj, act)
        self.assertEqual(ev['respetadas_material'], [])

    def test_e8_siete_perfiles_con_harmony(self):
        """Los 7 perfiles × biblioteca: MIDI válido y compliance sin fallos."""
        proj = _proyecto('casa_de_espejos')
        for perfil in je.production.nombres():
            cfg = {'production': perfil, 'seed': 5150,
                   'harmony': {'keyword': 'soulful', 'seed': 21,
                               'variacion': 'medium'}}
            if perfil == 'original':
                with self.assertRaises(ValueError):
                    je.render.generate(copy.deepcopy(proj), cfg)
                continue
            res = je.render.generate(copy.deepcopy(proj), cfg)
            self.assertTrue(res.midi[:4] == b'MThd', perfil)
            val = V.validate(res)
            fails = [c['id'] for c in val['compliance'] if c['status'] == 'fail']
            self.assertEqual(fails, [], '%s: %s' % (perfil, fails))

    def test_e9_biblioteca_sin_motores(self):
        """harmony con motores apagados: forge puro sobre la nueva armonía."""
        proj = _proyecto('habitacion_314')
        off = {'sax': False, 'rhodes': False, 'drums': False, 'vibes': False}
        res = je.render.generate(copy.deepcopy(proj),
                                 {'engines': off, 'seed': 4104,
                                  'harmony': {'keyword': 'dark_cinematic',
                                              'seed': 3}})
        ev = getattr(res, 'evidence', None) or {}
        self.assertIn('harmony', ev)
        base = je.render.generate(copy.deepcopy(proj),
                                  {'engines': off, 'seed': 4104})
        self.assertNotEqual(_sha(res.midi), _sha(base.midi))

    def test_e10_evidencia_serializable_y_completa(self):
        proj = _proyecto('medianoche_puerto_nuevo')
        res = je.render.generate(copy.deepcopy(proj),
                                 {'production': 'full', 'seed': 3113,
                                  'harmony': {'keyword': 'tension_release',
                                              'seed': 77, 'variacion': 'rich'}})
        ev = res.evidence['harmony']
        json.dumps(ev, ensure_ascii=False, default=str)      # no lanza
        self.assertIn('keyword', ev)
        self.assertIn('secciones', ev)
        for s in ev['secciones'].values():
            self.assertIn('simbolos', s)
            self.assertIn('huella_arquetipo', s['log'])

    def test_e11_cli_harmony_flags(self):
        """CLI: --harmony/--harmony-variacion/--harmony-seed de punta a punta."""
        import importlib
        jm = importlib.import_module('jazz_engine.__main__')
        proj = _proyecto('casa_de_espejos')
        with tempfile.TemporaryDirectory() as tmp:
            pproj = Path(tmp) / 'proj.json'
            pproj.write_text(json.dumps(proj), encoding='utf-8')
            pmid = Path(tmp) / 'out.mid'
            rc = jm.main([str(pproj), '--harmony', 'melancholic',
                          '--harmony-variacion', 'medium',
                          '--harmony-seed', '31', '-o', str(pmid)])
            self.assertEqual(rc, 0)
            self.assertTrue(pmid.exists() and pmid.stat().st_size > 1000)
            pmid2 = Path(tmp) / 'out2.mid'
            jm.main([str(pproj), '--harmony', 'melancholic',
                     '--harmony-variacion', 'medium',
                     '--harmony-seed', '31', '-o', str(pmid2)])
            self.assertEqual(_sha(pmid.read_bytes()), _sha(pmid2.read_bytes()))

    def test_e12_keyword_diferente_armonia_diferente(self):
        proj = _proyecto('habitacion_314')
        hashes = {}
        for kw in ('dark_cinematic', 'soulful', 'dream_pop'):
            res = je.render.generate(
                copy.deepcopy(proj),
                {'production': 'sax', 'seed': 4104,
                 'harmony': {'keyword': kw, 'seed': 7, 'variacion': 'none'}})
            hashes[kw] = _sha(res.midi)
        self.assertEqual(len(set(hashes.values())), 3, hashes)

    def test_e13_seed_diferente_variacion_diferente(self):
        """No siempre la misma progresión: la seed cambia el resultado."""
        proj = _proyecto('casa_de_espejos')
        hashes = set()
        for hseed in range(1, 9):
            res = je.render.generate(
                copy.deepcopy(proj),
                {'production': 'sax', 'seed': 5150,
                 'harmony': {'keyword': 'familiarity_auto', 'seed': hseed,
                             'variacion': 'rich'}})
            hashes.add(_sha(res.midi))
        self.assertGreaterEqual(len(hashes), 4, 'demasiado determinista entre seeds')

    def test_e14_contracts_7_perfiles_sin_harmony_intactos(self):
        """Regresión: los 7 perfiles SIN harmony siguen en pie (ejecutables)."""
        proj = _proyecto('nocturno_terminal')
        for perfil in je.production.nombres():
            if perfil == 'original':
                continue
            res = je.render.generate(copy.deepcopy(proj),
                                     {'production': perfil, 'seed': 2026})
            self.assertTrue(res.midi[:4] == b'MThd', perfil)


# ============================================================================
# F. Contrato y referencias doradas
# ============================================================================
class TestContratoYDorados(unittest.TestCase):
    def test_f1_contrato_congelado(self):
        info = contract.contract_info()
        self.assertEqual(info.get('contract_rev'), '3.2')

    def test_f2_codigo_protegido_intacto(self):
        import subprocess
        out = subprocess.run([sys.executable, 'manifests/hash_protected.py',
                              'verify'], capture_output=True, text=True,
                             cwd=str(ROOT))
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_f3_dorados_en_disco_intactos(self):
        for nombre, sha in (('01_original.mid', HASH_01), ('07_full.mid', HASH_07),
                            ('08_variation_atmospheric.mid', HASH_08)):
            data = (_GOLDEN_DIR / nombre).read_bytes()
            self.assertEqual(_sha(data), sha, nombre)

    def test_f4_regen_original_byte_identica(self):
        proj = _proyecto_nocturno()
        res = je.render.generate(copy.deepcopy(proj), {'production': 'original'})
        self.assertEqual(_sha(res.midi), HASH_01)

    def test_f5_regen_full_byte_identica(self):
        proj = _proyecto_nocturno()
        res = je.render.generate(copy.deepcopy(proj),
                                 {'production': 'full', 'seed': 2026})
        self.assertEqual(_sha(res.midi), HASH_07)

    def test_f6_validador_sin_cambios(self):
        """El validador DMD sigue aceptando los docs de generalización."""
        for comp in COMPOS:
            doc = json.loads((_GEN_DIR / comp / 'doc.json').read_text(
                encoding='utf-8'))
            r = validador.validar(copy.deepcopy(doc))
            fails = [c['id'] for c in r.get('compliance', [])
                     if c['status'] == 'fail']
            self.assertEqual(fails, [], comp)


if __name__ == '__main__':
    unittest.main()
