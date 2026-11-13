"""Alcance G de Fase 0 + Fase 1 + Fase 2: completitud de recetas N1 (§2.3 rev. 3.1, §2.6.5).

Qué verifica esta suite:
  - el mecanismo fail-fast de §2.6.5 (receta incompleta/fuera de rango no se registra);
  - el ESTADO REAL de Fase 1: dark_triphop tiene receta N1 REAL registrada
    (instrucción 09) con su tabla D_receta completa;
  - el ESTADO REAL de Fase 2 (RESPUESTA 09): doom_triphop y doom_dark_jazz
    tienen receta N1 REAL registrada (antes, en Fase 1, esta suite afirmaba que
    lanzaban RecetaNoDefinida — estado adaptado, ver TestEstadoFase2) y sus
    tablas BLOQUES pasan el verificador C5.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract, recetas, identities


TABLA_COMPLETA = {t: 0.5 for t in contract.SECTION_TYPES}  # sintética SOLO para probar el CHECKER


class TestVerificarCompletitud(unittest.TestCase):
    def test_tabla_completa_sin_problemas(self):
        self.assertEqual(recetas.verificar_completitud(TABLA_COMPLETA), ())

    def test_type_faltante(self):
        tabla = {t: 0.5 for t in contract.SECTION_TYPES if t != "break"}
        problemas = recetas.verificar_completitud(tabla)
        self.assertEqual(len(problemas), 1)
        self.assertIn("break", problemas[0])

    def test_type_extra(self):
        tabla = dict(TABLA_COMPLETA)
        tabla["drop"] = 0.5
        problemas = recetas.verificar_completitud(tabla)
        self.assertTrue(any("fuera del contrato" in p for p in problemas))

    def test_valores_fuera_de_rango(self):
        tabla = dict(TABLA_COMPLETA, intro=1.5, outro=-0.1)
        problemas = recetas.verificar_completitud(tabla)
        self.assertEqual(len(problemas), 2)

    def test_no_numerico_y_bool(self):
        tabla = dict(TABLA_COMPLETA, verse="alto", chorus=True)
        problemas = recetas.verificar_completitud(tabla)
        self.assertEqual(len(problemas), 2)  # bool NO cuenta como número válido


class TestFailFastRegistro(unittest.TestCase):
    def test_receta_incompleta_no_se_registra(self):
        tabla = {t: 0.5 for t in contract.SECTION_TYPES if t != "intro"}
        with self.assertRaises(recetas.RecetaError):
            recetas.registrar_receta("dark_triphop", tabla)
        # el registro REAL de dark_triphop no se ve afectado por el fallo
        self.assertIn("dark_triphop", recetas.RECETAS_REGISTRADAS)

    def test_receta_valida_se_registra_y_carga(self):
        recetas.registrar_receta("doom_triphop", dict(TABLA_COMPLETA))
        try:
            self.assertEqual(recetas.load_receta("doom_triphop"), TABLA_COMPLETA)
        finally:
            recetas.RECETAS_REGISTRADAS.pop("doom_triphop", None)  # solo la sintética; no contaminar

    def test_identidad_desconocida(self):
        with self.assertRaises(recetas.RecetaError):
            recetas.load_receta("synthwave")
        with self.assertRaises(recetas.RecetaError):
            recetas.registrar_receta("synthwave", TABLA_COMPLETA)


class TestEstadoFase1(unittest.TestCase):
    def test_dark_triphop_tiene_receta_real(self):
        # instrucción 09: primera receta N1 real (dark_director/identities/dark_triphop.py)
        self.assertIn("dark_triphop", recetas.RECETAS_REGISTRADAS)
        tabla = recetas.load_receta("dark_triphop")
        self.assertEqual(tabla, identities.dark_triphop.D_RECETA)
        self.assertEqual(recetas.verificar_completitud(tabla), ())


class TestEstadoFase2(unittest.TestCase):
    """Fase 2 (RESPUESTA 09): las tres identidades del contrato tienen receta
    real registrada. ADAPTADO del estado de Fase 1 (antes afirmaba que doom
    lanzaba RecetaNoDefinida): el registro de las recetas doom es el propio
    objeto de la Fase B/C y el estado antiguo ya no es el vigente."""

    def test_las_tres_identidades_tienen_receta_real(self):
        self.assertEqual(tuple(recetas.RECETAS_REGISTRADAS.keys()),
                         ("dark_triphop", "doom_triphop", "doom_dark_jazz"))
        self.assertEqual(identities.CON_RECETA,
                         ("dark_triphop", "doom_triphop", "doom_dark_jazz"))
        self.assertEqual(identities.SIN_RECETA, ())

    def test_doom_cargan_y_coinciden_con_su_modulo(self):
        for mod in (identities.doom_triphop, identities.doom_dark_jazz):
            with self.subTest(identidad=mod.IDENTITY):
                tabla = recetas.load_receta(mod.IDENTITY)
                self.assertEqual(tabla, mod.D_RECETA)
                self.assertEqual(recetas.verificar_completitud(tabla), ())
                # C5: tabla BLOQUES coherente (sin problemas)
                self.assertEqual(recetas.verificar_tabla_bloques(mod), ())
                self.assertTrue(hasattr(mod, "BLOQUES"))
                self.assertTrue(hasattr(mod, "AUTOMACION"))

    def test_c5_receta_incoherente_no_registraria(self):
        # simulación a nivel de checker: una tabla BLOQUES con un estilo
        # inexistente, velocidades/semillas inválidas y filas ausentes produce
        # problemas (el registro real vive en identities/__init__.py; aquí se
        # prueba el verificador puro)
        class _Falsa:
            IDENTITY = "doom_triphop"
            SET_BASE = ("sax_tenor", "bass")
            BLOQUES = {
                "intro": {"sax_tenor": {"style": "estilo_inexistente"},
                          # falta 'bass'
                          },
                "outro": {"sax_tenor": {"style": "hold", "velocity": [0, 0]},
                          "bass": {"style": "long", "seed": -1}},
            }
        problemas = recetas.verificar_tabla_bloques(_Falsa)
        texto = "; ".join(problemas)
        self.assertIn("estilo_inexistente", texto)
        self.assertIn("'bass'", texto)          # fila ausente en intro
        self.assertIn("velocity", texto)
        self.assertIn("seed", texto)
        self.assertIn("verse", texto)           # types ausentes


if __name__ == "__main__":
    unittest.main()
