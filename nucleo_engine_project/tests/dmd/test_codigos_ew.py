"""Alcance G de Fase 0: códigos E/W (rev. 3 §4 + fila E114 de rev. 3.1).

Reglas verificadas: 40 códigos activos, un código = un significado, familias
contiguas, E201/E202 retirados y sin reasignar, doctrina E114 sin bloque parcial.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract


class TestRegistroEW(unittest.TestCase):
    def test_total_40_activos(self):
        activos = contract.codigos_activos()
        self.assertEqual(len(activos), contract.TOTAL_CODIGOS_ACTIVOS)
        self.assertEqual(len(activos), 40)

    def test_familias_contiguas_y_tamanos(self):
        esperado = {
            "E1xx": ([f"E{n:03d}" for n in range(101, 115)], 14),   # E101–E114
            "E2xx": (["E203", "E204"], 2),
            "E3xx": (["E301", "E302", "E303"], 3),
            "W4xx": ([f"W{n:03d}" for n in range(401, 422)], 21),   # W401–W421
        }
        for fam, (codigos, n) in esperado.items():
            activos_fam = [c for c in contract.codigos_activos() if contract.EW_CODES[c][0] == fam]
            self.assertEqual(activos_fam, codigos, msg=fam)
            self.assertEqual(len(activos_fam), n, msg=fam)

    def test_e201_e202_retirados_y_sin_reasignar(self):
        self.assertNotIn("E201", contract.EW_CODES)
        self.assertNotIn("E202", contract.EW_CODES)
        for code in ("E201", "E202"):
            self.assertIn("RETIRADO", contract.RETIRED_CODES[code])
            self.assertIn("No se reasigna", contract.RETIRED_CODES[code])

    def test_un_codigo_un_significado(self):
        resumenes = [s for _, s in contract.EW_CODES.values()]
        self.assertEqual(len(resumenes), len(set(resumenes)), "hay resúmenes duplicados")

    def test_semantica_de_familias(self):
        self.assertEqual(contract.FAMILIAS["E1xx"], ("estructural", True))
        self.assertEqual(contract.FAMILIAS["E2xx"], ("contradicción", True))
        self.assertEqual(contract.FAMILIAS["E3xx"], ("capacidad no soportada", True))
        self.assertEqual(contract.FAMILIAS["W4xx"], ("recomendación", False))
        for fam, (_, bloquea) in contract.FAMILIAS.items():
            if not bloquea:
                self.assertTrue(fam.startswith("W"))

    def test_anclas_contra_colisiones_historicas(self):
        # rev. 3: E106 = SOLO structure inválida; E113 = SOLO acordes; E110 = catálogo
        self.assertIn("exclusivamente structure", contract.EW_CODES["E106"][1])
        self.assertIn("no parseable", contract.EW_CODES["E113"][1])
        self.assertIn("catálogo de 8", contract.EW_CODES["E110"][1])
        self.assertEqual(contract.EW_CODES["E102"][1], "schema ausente o != 'dark-director/1'")

    def test_doctrina_e114_sin_bloque_parcial(self):
        resumen = contract.EW_CODES["E114"][1]
        self.assertEqual(contract.EW_CODES["E114"][0], "E1xx")
        self.assertIn("no se emite pista parcial", resumen)
        self.assertIn("no puede inicializarse con seguridad", resumen)

    def test_anchors_de_bandas_en_los_codigos(self):
        # W403/W409 citan bandas sin redeclarar rangos (rev. 3.2: definición única §2.6.5)
        self.assertIn("banda B3", contract.EW_CODES["W403"][1])
        self.assertIn("banda B3", contract.EW_CODES["W409"][1])
        for code in ("W403", "W409"):
            self.assertNotIn("0.34", contract.EW_CODES[code][1])


if __name__ == "__main__":
    unittest.main()
