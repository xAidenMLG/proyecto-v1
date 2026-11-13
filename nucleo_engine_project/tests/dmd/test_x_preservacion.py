"""Alcance G de Fase 0: preservación de campos de extensión ``x_*``.

Contrato (§3 nota; fila ``x_*`` de §3.3; E109): los campos con prefijo ``x_``
son extensiones del compositor; viajan incrustados en ``meta.director`` del
proyecto emitido (roundtrip verificado por la auditoría) y nunca afectan a la
música. Todo campo desconocido SIN prefijo ``x_`` es E109.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract


class TestSeparacionXFields(unittest.TestCase):
    def test_separacion_preserva_orden_y_valores(self):
        d = {"schema": "dark-director/1", "x_palette": {"dark": 1}, "direction": {"identity": "dark_triphop"},
             "x_nota": 3, "x_lista": [1, 2, 3]}
        extras, resto = contract.separar_x_fields(d)
        self.assertEqual(list(extras), ["x_palette", "x_nota", "x_lista"])  # orden de inserción
        self.assertEqual(extras["x_palette"], {"dark": 1})
        self.assertEqual(set(resto), {"schema", "direction"})

    def test_sin_x_fields(self):
        extras, resto = contract.separar_x_fields({"schema": "dark-director/1", "bpm": 70})
        self.assertEqual(extras, {})
        self.assertEqual(resto, {"schema": "dark-director/1", "bpm": 70})

    def test_valores_sobreviven_roundtrip_json(self):
        extras, _ = contract.separar_x_fields({"x_a": {"n": [1, 2]}, "x_b": "texto", "x_c": None})
        re = json.loads(json.dumps(extras))
        self.assertEqual(re, extras)

    def test_prefijo_doctrine(self):
        self.assertTrue(contract.es_campo_extension("x_palette"))
        self.assertFalse(contract.es_campo_extension("palette"))
        self.assertFalse(contract.es_campo_extension("swing"))     # funcionalidad futura → E109
        self.assertFalse(contract.es_campo_extension("x_"))        # prefijo sin nombre
        self.assertFalse(contract.es_campo_extension(123))         # no es campo


class TestIncrustacionMetaDirector(unittest.TestCase):
    def test_x_fields_viajan_en_meta_director(self):
        extras, _ = contract.separar_x_fields({"x_palette": {"dark": 1}})
        meta = contract.build_director_meta(x_fields=extras)
        self.assertEqual(meta["x_palette"], {"dark": 1})
        self.assertEqual(meta["contract"], "dark-director/1")
        self.assertEqual(meta["contract_rev"], "3.2")

    def test_campos_sin_prefijo_no_se_incrustan(self):
        with self.assertRaises(ValueError):
            contract.build_director_meta(x_fields={"swing": 0.3})  # E109 en Fase 1; aquí error explícito


if __name__ == "__main__":
    unittest.main()
