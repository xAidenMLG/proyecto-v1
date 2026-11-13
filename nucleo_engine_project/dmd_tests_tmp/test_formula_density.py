"""Alcance G de Fase 0: fórmula de coexistencia de density (§2.6.5, rev. 3.1).

Qué verifica esta suite de Fase 0: las PROPIEDADES CONTRACTUALES de la fórmula,
que valen para CUALQUIER tabla D_receta válida (propiedad 6 es explícitamente
"para cualquier tabla"). Son pruebas de álgebra del contrato, no pruebas de
defaults.

Obligación de Fase 1 (§2.6.5): probar la fórmula con los defaults REALES de las
recetas — la parte dark_triphop se cumple en tests/test_receta_n1.py
(test_formula_con_defaults_reales_dark_triphop); las identidades doom siguen
sin receta y su obligación queda documentada para cuando se implementen.
"""
import sys
import unittest
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract, recetas, identities

SECCIONES = [("verse_1", 0.45), ("verse_2", 0.50), ("chorus_2", 0.70), ("break_1", 0.30), ("outro", 0.20)]


def tablas_d_receta(rng, types):
    """Tablas D_receta arbitrarias (extremos + aleatorias con semilla fija).
    Son tablas sintéticas para probar el ÁLGEBRA de la fórmula; no representan
    defaults de ninguna identidad (ver docstring del módulo)."""
    tablas = [{t: 0.0 for t in types}, {t: 1.0 for t in types}, {t: 0.5 for t in types}]
    for t in types:
        for val in (0.0, 0.33, 0.67, 1.0):
            tab = {x: 0.5 for x in types}
            tab[t] = val
            tablas.append(tab)
    tablas.extend({t: rng.random() for t in types} for _ in range(500))
    return tablas


class TestFormulaCoexistencia(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(20261108)
        self.types = contract.SECTION_TYPES
        self.tablas = tablas_d_receta(self.rng, self.types)

    def test_propiedad_1_solo_seccion_declarada_cancelacion(self):
        # efectiva == density de sección EXACTA para cualquier tabla D_receta
        for tabla in self.tablas:
            for _, d_secc in SECCIONES:
                eff = contract.density_efectiva(None, d_secc, tabla["verse"])
                self.assertAlmostEqual(eff, d_secc, places=12)

    def test_propiedad_2_solo_instrumento_declarado(self):
        for d_inst in (0.2, 0.45, 0.7):
            for tabla in self.tablas[:20]:
                eff = contract.density_efectiva(d_inst, None, tabla["verse"])
                self.assertAlmostEqual(eff, d_inst, places=12)

    def test_propiedad_3_evolucion_conservada(self):
        # con ambas declaradas, la diferencia entre secciones es EXACTAMENTE la
        # diferencia de sus densities de sección, sea cual sea D_receta.
        # Si alguna sección satura el clamp (0 o 1), la diferencia puede colapsar:
        # eso es la semántica del clamp del contrato; se excluyen esos casos y se
        # comprueba que ambos valores quedan dentro de [0, 1].
        d_inst = 0.45
        esperado = SECCIONES[1][1] - SECCIONES[0][1]
        verificadas = 0
        for tabla in self.tablas:
            e1 = contract.density_efectiva(d_inst, SECCIONES[0][1], tabla["verse"])
            e2 = contract.density_efectiva(d_inst, SECCIONES[1][1], tabla["verse"])
            self.assertTrue(0.0 <= e1 <= 1.0 and 0.0 <= e2 <= 1.0)
            if e1 in (0.0, 1.0) or e2 in (0.0, 1.0):
                continue  # saturación del clamp
            self.assertAlmostEqual(e2 - e1, esperado, places=12)
            verificadas += 1
        self.assertGreater(verificadas, 10, msg="la evolución no se pudo verificar sin saturación")

    def test_clamp_al_intervalo_0_1(self):
        self.assertEqual(contract.density_efectiva(1.0, 1.0, 0.0), 1.0)
        self.assertEqual(contract.density_efectiva(0.0, 0.0, 1.0), 0.0)
        self.assertEqual(contract.density_efectiva(1.0, None, 0.5), 1.0)
        self.assertEqual(contract.density_efectiva(0.0, None, 0.5), 0.0)
        for tabla in self.tablas:
            for _, d_secc in SECCIONES:
                eff = contract.density_efectiva(0.9, d_secc, tabla["verse"])
                self.assertTrue(0.0 <= eff <= 1.0)

    def test_bandificacion_cuantiza_determinista(self):
        # propiedad 5: dos valores de la misma banda → mismo bloque (misma banda)
        self.assertEqual(contract.density_band(0.40), "B2")
        self.assertEqual(contract.density_band(0.50), "B2")
        self.assertEqual(contract.density_band(0.35), contract.density_band(0.60))

    def test_los_valores_de_receta_no_vienen_de_ningun_json(self):
        # prohibición §2.6.5: D_receta nunca se infiere del JSON del compositor.
        # Fase 1: la fuente única es la receta N1 real (identities/dark_triphop.py).
        self.assertIn("dark_triphop", recetas.RECETAS_REGISTRADAS)
        self.assertEqual(recetas.RECETAS_REGISTRADAS["dark_triphop"],
                         identities.dark_triphop.D_RECETA)


if __name__ == "__main__":
    unittest.main()
