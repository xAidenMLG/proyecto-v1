"""Catálogo cerrado y enums del contrato (§2.2, §2.5, §2.6.3, §2.1, §5.0.1)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract


class TestCatalogo(unittest.TestCase):
    def test_catalogo_cerrado_de_8_instrumentos(self):
        # §2.5 (rev. 3.1 §2.2): otro id → E110
        self.assertEqual(contract.INSTRUMENT_IDS,
                         ("sax_tenor", "rhodes", "vibraphone", "bass", "drums", "piano", "pad", "strings"))
        self.assertEqual(len(contract.INSTRUMENT_IDS), 8)

    def test_7_types_de_seccion(self):
        self.assertEqual(contract.SECTION_TYPES,
                         ("intro", "verse", "pre_chorus", "chorus", "bridge", "break", "outro"))

    def test_escalera_drums(self):
        # §2.6.3: off→air→light→groove→heavy
        self.assertEqual(contract.DRUMS_LADDER, ("off", "air", "light", "groove", "heavy"))

    def test_identidades_accesibilidades_lenguajes(self):
        self.assertEqual(contract.IDENTITIES, ("dark_triphop", "doom_triphop", "doom_dark_jazz"))
        self.assertEqual(contract.ACCESSIBILITIES, ("commercial", "balanced", "experimental"))
        self.assertEqual(contract.LANGUAGES, ("pop_dream_pop", "hybrid", "experimental"))
        # §2.4/§2.4.1 (rev. 3): 5 resoluciones con defaults por language.
        # DEFECTO DE FASE 0 CORREGIDO EN FASE 1: contract.py traía 3 valores
        # (tonal/deceptive/chromatic) frente a los 5 del contrato congelado;
        # el validador real rechazaba 'modal'/'open' (documentado en respuesta_07 §8).
        self.assertEqual(contract.RESOLUTIONS,
                         ("tonal", "modal", "deceptive", "chromatic", "open"))

    def test_27_combinaciones_todas_validas(self):
        # §2.1: 3×3×3 = 27 combinaciones, todas válidas (sin E2xx bloqueante de combinaciones)
        combos = {(i, a, l) for i in contract.IDENTITIES
                  for a in contract.ACCESSIBILITIES for l in contract.LANGUAGES}
        self.assertEqual(len(combos), contract.TOTAL_COMBINACIONES)
        self.assertEqual(len(combos), 27)
        # los únicos E2xx activos son conflictos de desarrollo (E203/E204), no de combinaciones
        e2xx = [c for c, (fam, _) in contract.EW_CODES.items() if fam == "E2xx"]
        self.assertEqual(sorted(e2xx), ["E203", "E204"])

    def test_sets_base_llevan_etiqueta_provisional_y_coinciden_con_5_0_1(self):
        # §5.0.1: los sets base son SUPUESTO PROVISIONAL de datos de receta;
        # el propio nombre del símbolo lo etiqueta (visible en dir(contract))
        nombre = contract.BASE_SETS_SUPUESTO_PROVISIONAL
        self.assertIn("BASE_SETS_SUPUESTO_PROVISIONAL", dir(contract))
        self.assertEqual(set(nombre["dark_triphop"]),
                         {"sax_tenor", "rhodes", "vibraphone", "bass", "drums", "pad"})
        self.assertEqual(set(nombre["doom_triphop"]),
                         {"sax_tenor", "rhodes", "vibraphone", "bass", "drums", "pad", "strings"})
        self.assertEqual(set(nombre["doom_dark_jazz"]),
                         {"sax_tenor", "rhodes", "vibraphone", "bass", "drums", "piano", "strings"})

    def test_doctrina_del_nombre_provisional_en_la_fuente(self):
        # el etiquetado §5.0.1 debe ser visible en la fuente del módulo (honestidad)
        import inspect
        src = inspect.getsource(contract)
        self.assertIn("SUPUESTO PROVISIONAL", src)


if __name__ == "__main__":
    unittest.main()
