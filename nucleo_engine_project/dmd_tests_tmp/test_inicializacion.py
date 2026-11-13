"""Alcance G de Fase 0: inicialización de instrumentos adicionales (§2.5.1 rev. 3.1).

Fase 0 verifica el DATO del catálogo §2.5.1 y la DECISIÓN de seguridad (E114 /
E110 / ok) como función pura. La emisión del bloque inicializado es del
compilador (Fase 1) — este módulo no emite bloques ni traduce música.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract, inicializacion


class TestCatalogo251(unittest.TestCase):
    def test_cubre_los_8_instrumentos(self):
        # el orden del catálogo §2.5.1 replica su tabla (no el orden del catálogo §2.5)
        self.assertEqual(len(inicializacion.INIT_CATALOG), 8)
        self.assertEqual(set(inicializacion.INIT_CATALOG), set(contract.INSTRUMENT_IDS))

    def test_programas_por_instrumento(self):
        cat = inicializacion.INIT_CATALOG
        self.assertEqual(cat["sax_tenor"]["programa_inicializacion"], 66)   # lead / 66
        self.assertEqual(cat["rhodes"]["programa_inicializacion"], 4)       # keys / 4
        self.assertEqual(cat["piano"]["programa_inicializacion"], 0)        # keys / 0
        self.assertEqual(cat["vibraphone"]["programa_inicializacion"], 11)  # mallet / 11
        self.assertEqual(cat["pad"]["programa_inicializacion"], 91)         # §2.5.1: de 91/89 fija 91
        self.assertEqual(cat["strings"]["programa_inicializacion"], 50)
        self.assertEqual(cat["bass"]["programa"], (38, 32))                 # finger / upright (bass.type)
        self.assertEqual(cat["drums"]["programa"], ("ch10",))

    def test_bloques_inicializados(self):
        cat = inicializacion.INIT_CATALOG
        self.assertEqual(cat["sax_tenor"]["bloque"], "generative")
        self.assertEqual(cat["rhodes"]["bloque"], "hold")
        self.assertEqual(cat["piano"]["bloque"], "hold")
        self.assertEqual(cat["pad"]["bloque"], "sustain")
        self.assertEqual(cat["strings"]["bloque"], "sustain")
        self.assertEqual(cat["vibraphone"]["bloque"], "replies")
        self.assertEqual(cat["bass"]["bloque"], "pattern")
        self.assertEqual(cat["drums"]["bloque"], "capas por nivel")

    def test_solo_vibrafono_requiere_lead_y_solo_bass_drums_dependen_de_receta(self):
        req_lead = [i for i, s in inicializacion.INIT_CATALOG.items() if s["requiere_lead"]]
        dep_rec = [i for i, s in inicializacion.INIT_CATALOG.items() if s["depende_receta"]]
        self.assertEqual(req_lead, ["vibraphone"])
        self.assertEqual(dep_rec, ["bass", "drums"])


class TestDecisionSeguridad(unittest.TestCase):
    def test_id_desconocido_es_e110_no_e114(self):
        estado, detalle = inicializacion.estado_inicializacion("theremin", en_base=False, existe_lead=True)
        self.assertEqual(estado, "E110")
        self.assertIn("catálogo de 8", detalle)

    def test_enabled_sobre_pista_base_sin_efecto(self):
        # §2.5.1: enabled=true sobre pista base no tiene efecto adicional: sin error ni aviso
        estado, detalle = inicializacion.estado_inicializacion("rhodes", en_base=True, existe_lead=True)
        self.assertEqual(estado, "ok-base")
        self.assertIn("sin efecto adicional", detalle)

    def test_vibrafono_sin_lead_es_e114_y_bloquea_siempre(self):
        estado, detalle = inicializacion.estado_inicializacion("vibraphone", en_base=False, existe_lead=False)
        self.assertEqual(estado, "E114")
        self.assertIn("no se emite pista parcial", detalle)
        self.assertIn("sin pista lead existente", detalle)

    def test_vibrafono_con_lead_es_ok(self):
        estado, detalle = inicializacion.estado_inicializacion("vibraphone", en_base=False, existe_lead=True)
        self.assertEqual(estado, "ok")
        self.assertIn("replies", detalle)

    def test_bass_drums_sin_datos_de_receta_es_e114(self):
        for inst in ("bass", "drums"):
            with self.subTest(instrumento=inst):
                estado, detalle = inicializacion.estado_inicializacion(inst, en_base=False,
                                                                       existe_lead=True, receta_da_datos=False)
                self.assertEqual(estado, "E114")
                self.assertIn("no se emite pista parcial", detalle)

    def test_rama_bass_drums_inalcanzable_en_v1_documentada(self):
        # con los sets base de §5.0.1 (supuesto provisional), bass y drums son base en las 3 identidades
        for identity, base in contract.BASE_SETS_SUPUESTO_PROVISIONAL.items():
            with self.subTest(identidad=identity):
                self.assertIn("bass", base)
                self.assertIn("drums", base)

    def test_inicializacion_determinista_de_un_no_base(self):
        # p. ej. pad fuera del set base hypothetical: ok con catálogo determinista
        estado, detalle = inicializacion.estado_inicializacion("pad", en_base=False, existe_lead=True)
        self.assertEqual(estado, "ok")
        self.assertIn("rol=pad", detalle)
        self.assertIn("sustain", detalle)


if __name__ == "__main__":
    unittest.main()
