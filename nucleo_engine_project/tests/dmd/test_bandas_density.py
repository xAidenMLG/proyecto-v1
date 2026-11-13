"""Alcance F de Fase 0: los 9 tests de frontera de density de la rev. 3.2 (§2.6.5)
+ cobertura total y exclusiva de [0.0, 1.0] (sin huecos ni solapamientos).

Definición rev. 3.2 (única en el contrato):
    B1: density <= 0.33
    B2: 0.33 < density < 0.67
    B3: density >= 0.67
"""
import sys
import unittest
from decimal import Decimal
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract

#: los 9 valores exigidos por la instrucción de la rev. 3.2 y su banda esperada
FRONTERA = [
    ("0.0", "B1"), ("0.33", "B1"), ("0.330001", "B2"), ("0.335", "B2"), ("0.5", "B2"),
    ("0.665", "B2"), ("0.669999", "B2"), ("0.67", "B3"), ("1.0", "B3"),
]


class TestFronterasExigidas(unittest.TestCase):
    def test_los_9_valores_de_frontera(self):
        for s, esperada in FRONTERA:
            with self.subTest(valor=s, esperada=esperada):
                vd, vf = Decimal(s), float(s)
                self.assertEqual(contract.density_band(vd), esperada)  # decimal exacto
                self.assertEqual(contract.density_band(vf), esperada)  # float64 como JSON

    def test_limites_y_condiciones_textuales(self):
        self.assertEqual(contract.BAND_B1_MAX, 0.33)
        self.assertEqual(contract.BAND_B3_MIN, 0.67)
        self.assertEqual(contract.BAND_CONDITIONS,
                         {"B1": "density <= 0.33", "B2": "0.33 < density < 0.67", "B3": "density >= 0.67"})


class TestCoberturaTotal(unittest.TestCase):
    def test_rejilla_decimal_10001_puntos_exactamente_una_banda(self):
        step = Decimal("0.0001")
        for k in range(10001):
            v = step * k
            n = (v <= Decimal("0.33")) + (Decimal("0.33") < v < Decimal("0.67")) + (v >= Decimal("0.67"))
            self.assertEqual(n, 1, msg=f"punto {v} clasificado {n} veces")
            self.assertEqual(contract.density_band(v), contract.density_band(v))  # determinismo

    def test_sondas_aleatorias_exactamente_una_banda(self):
        rng = random.Random(3207)
        for _ in range(50000):
            r = rng.random()
            n = (r <= 0.33) + (0.33 < r < 0.67) + (r >= 0.67)
            self.assertEqual(n, 1, msg=f"sonda {r!r} clasificada {n} veces")

    def test_solapamiento_nulo_en_puntos_de_contacto(self):
        self.assertEqual(contract.density_band(0.33), "B1")   # 0.33 → B1 (no B2)
        self.assertEqual(contract.density_band(0.67), "B3")   # 0.67 → B3 (no B2)
        self.assertEqual(contract.density_band(0.34), "B2")
        self.assertEqual(contract.density_band(0.66), "B2")

    def test_dominio_fuera_de_rango_es_error(self):
        for v in (-0.1, 1.1, 2.0):
            with self.assertRaises(ValueError):
                contract.density_band(v)


if __name__ == "__main__":
    unittest.main()
