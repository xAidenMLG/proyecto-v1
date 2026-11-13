"""Alcance D de Fase 0: identificación de versiones del contrato y del compilador.

Contrato: §3.3 (schema literal ``dark-director/1`` → proyecto emitido
``midi-forge/1``; original viaja en ``meta.director``) + instrucción de Fase 0 (D).
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import dark_director
from dark_director import contract


class TestVersiones(unittest.TestCase):
    def test_valores_exactos(self):
        info = contract.contract_info()
        self.assertEqual(info["contract"], "dark-director/1")
        self.assertEqual(info["contract_rev"], "3.2")
        self.assertEqual(info["target_schema"], "midi-forge/1")
        self.assertEqual(info["compiler_version"], "0.1.0")
        self.assertEqual(info["compiler_stage"], "fase1")

    def test_paquete_expone_las_mismas_versiones(self):
        self.assertEqual(dark_director.CONTRACT_ID, contract.CONTRACT_ID)
        self.assertEqual(dark_director.CONTRACT_REV, contract.CONTRACT_REV)
        self.assertEqual(dark_director.TARGET_SCHEMA, contract.TARGET_SCHEMA)
        self.assertEqual(dark_director.COMPILER_STAGE, "fase1")

    def test_mecanismo_meta_director_con_versiones(self):
        meta = contract.build_director_meta()
        self.assertEqual(meta["contract"], "dark-director/1")
        self.assertEqual(meta["contract_rev"], "3.2")
        self.assertEqual(meta["target_schema"], "midi-forge/1")

    def test_extensiones_x_se_incrustan_en_meta_director(self):
        meta = contract.build_director_meta(x_fields={"x_palette": {"a": 1}, "x_nota": 3})
        self.assertEqual(meta["x_palette"], {"a": 1})
        self.assertEqual(meta["x_nota"], 3)
        self.assertEqual(meta["contract_rev"], "3.2")

    def test_colision_con_clave_reservada_es_error(self):
        with self.assertRaises(ValueError):
            contract.build_director_meta(x_fields={"contract_rev": "9.9"})
        with self.assertRaises(ValueError):
            contract.build_director_meta(x_fields={"campo_sin_prefijo": 1})


if __name__ == "__main__":
    unittest.main()
