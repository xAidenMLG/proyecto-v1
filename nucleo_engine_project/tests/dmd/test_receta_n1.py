"""Fase 1 — receta N1 REAL de dark_triphop (instrucción 09; §2.3 rev. 3.1, §2.6.5).

Obligación de §2.6.5 cumplida aquí: la fórmula de coexistencia se prueba con
los defaults REALES importados de la receta (no fixtures inventados). Las
identidades doom siguen sin receta: su obligación queda documentada.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import accesibilidad, contract, recetas, identities
from dark_director.identities import dark_triphop as R


class TestRecetaN1Real(unittest.TestCase):
    def test_completitud_los_7_types(self):
        self.assertEqual(sorted(R.D_RECETA), sorted(contract.SECTION_TYPES))
        self.assertEqual(recetas.verificar_completitud(R.D_RECETA), ())
        for t, v in R.D_RECETA.items():
            self.assertTrue(0.0 <= v <= 1.0, msg=f"D_receta[{t}]={v} fuera de [0,1]")

    def test_energia_tension_drums_focus_cubren_los_7_types(self):
        for t in contract.SECTION_TYPES:
            self.assertIn(t, R.ENERGY_BASE)
            self.assertTrue(0.0 <= R.ENERGY_BASE[t] <= 1.0)
            self.assertIn(t, R.TENSION_BASE)
            self.assertTrue(0.0 <= R.TENSION_BASE[t] <= 1.0)
            self.assertIn(t, R.DRUMS_NIVEL)
            self.assertIn(R.DRUMS_NIVEL[t], contract.DRUMS_LADDER)
            self.assertIn(t, R.FOCUS_DEFAULT)
            self.assertLessEqual(len(R.FOCUS_DEFAULT[t]), 3)
            for f in R.FOCUS_DEFAULT[t]:
                self.assertIn(f, R.SET_BASE, msg=f"focus default {f} no es pista base")

    def test_set_base_y_lead(self):
        self.assertEqual(R.IDENTITY, "dark_triphop")
        for iid in R.SET_BASE:
            self.assertIn(iid, contract.INSTRUMENT_IDS)
        self.assertIn(R.LEAD, R.SET_BASE)
        # §5.0.1 rev. 3.1: el supuesto provisional de dark_triphop pasa a ser real
        self.assertEqual(R.SET_BASE, contract.BASE_SETS_SUPUESTO_PROVISIONAL["dark_triphop"])

    def test_escalera_drums_usa_presets_reales_del_motor(self):
        f = __import__("dark_director").forge_link.import_forge()
        for nivel, preset in R.DRUMS_PRESET_POR_NIVEL.items():
            self.assertIn(preset, f.styles.DRUM_PRESETS,
                          msg=f"preset de batería '{preset}' no existe en el motor")
        for nivel, vs in R.DRUMS_VEL_SCALE_POR_NIVEL.items():
            if vs is not None:
                self.assertIn(vs, (0.85, 0.95, 1.0, 1.1),
                              msg=f"vel_scale {vs} del nivel {nivel} no es el de §2.6.3")
        # fills de heavy usan vocabulario real del motor (snare2 existe en trip_*)
        for fill in R.DRUMS_FILLS_HEAVY:
            for roll in fill["rolls"]:
                self.assertEqual(roll["inst"], "snare2")

    def test_patrones_de_bajo_y_ultima_nota_apto_para_approach(self):
        f = __import__("dark_director").forge_link.import_forge()
        tokens = {"R", "F", "O", "T", "S", "A"}
        # El requisito de última nota en pos >= bb−0.75 aplica a los tipos que
        # PUEDEN iniciar una transición (todo menos el último). `outro` usa la
        # forma `whole` real del motor (nota entera): si algún compositor
        # colocara un outro no-final, el gesto approach no dispararía (mecanismo
        # del motor dependiente del patrón); el split armónico sí se aplica.
        for t, patrones in R.BASS_PATRONES.items():
            if patrones is None:
                continue
            for patt in patrones:
                self.assertTrue(patt, msg=f"{t}: patrón vacío")
                for ent in patt:
                    self.assertIn(ent[1], tokens, msg=f"{t}: token {ent[1]!r} fuera del motor")
                if t != "outro":
                    ultima = patt[-1]
                    self.assertGreaterEqual(ultima[0], 3.25,
                                            msg=f"{t}: la última nota (pos {ultima[0]}) no permite el gesto approach del motor (pos >= bb-0.75)")

    def test_progresiones_por_language_y_type_en_vocabulario(self):
        f = __import__("dark_director").forge_link.import_forge()
        tonic = 2  # D: instancia en una tónica real para verificar símbolos
        nombres = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
        for language, tabla in R.PROGRESIONES.items():
            self.assertEqual(sorted(tabla), sorted(contract.SECTION_TYPES),
                             msg=f"{language}: progresiones incompletas por type")
            for t, pares in tabla.items():
                self.assertTrue(pares, msg=f"{language}.{t}: sin progresión (§2.8 exige una por (type, language))")
                for off, cal in pares:
                    self.assertIsInstance(off, int)
                    if language != "experimental":
                        self.assertIn(cal, _vocab(language),
                                      msg=f"{language}.{t}: calidad {cal} fuera del vocabulario §2.4")
                    simbolo = nombres[(tonic + off) % 12] + cal
                    try:
                        f.theory.parse_chord(simbolo)
                    except ValueError:
                        self.fail(f"{language}.{t}: símbolo instanciado {simbolo!r} no parsea en el motor")

    def test_bpm_y_rango_tipico(self):
        self.assertTrue(20 <= R.BPM_DEFAULT <= 300)
        self.assertLessEqual(R.BPM_RANGO_TIPICO[0], R.BPM_DEFAULT)
        self.assertGreaterEqual(R.BPM_RANGO_TIPICO[1], R.BPM_DEFAULT)


class TestFormulaConDefaultsReales(unittest.TestCase):
    """§2.6.5: la fórmula se prueba con la tabla D_receta REAL importada."""

    def test_formula_con_defaults_reales_dark_triphop(self):
        tabla = R.D_RECETA
        for t in contract.SECTION_TYPES:
            d_r = tabla[t]
            # propiedad 1 (con defaults reales): solo sección → efectiva exacta
            for d_secc in (0.0, 0.2, 0.45, 0.7, 1.0):
                self.assertAlmostEqual(contract.density_efectiva(None, d_secc, d_r), d_secc, places=12)
            # propiedad 2: solo instrumento → efectiva == D_inst
            self.assertAlmostEqual(contract.density_efectiva(0.45, None, d_r), 0.45, places=12)
            # propiedad 3: ambas → evolución conservada sobre la base real
            e1 = contract.density_efectiva(0.45, 0.45, d_r)
            e2 = contract.density_efectiva(0.45, 0.50, d_r)
            self.assertAlmostEqual(e2 - e1, 0.05, places=12)

    def test_compatibilidad_con_los_3_ejemplos_del_contrato(self):
        # rev. 3.1 (propiedad 6 + barrido): los avisos documentados de los
        # ejemplos son invariantes; con la tabla real de dark_triphop se
        # verifican dos casos concretos de H.1 (Midnight Tape):
        d_r_verse = R.D_RECETA["verse"]
        # verse_1: 0.45 + (0.45 − D_r) ; verse_2: 0.45 + (0.50 − D_r) → ambos B2
        e1 = contract.density_efectiva(0.45, 0.45, d_r_verse)
        e2 = contract.density_efectiva(0.45, 0.50, d_r_verse)
        self.assertEqual(contract.density_band(e1), "B2")
        self.assertEqual(contract.density_band(e2), "B2")
        # H.3 (Cold Harbor, doom_dark_jazz sin receta): máx. efectiva 0.55 < 0.67
        # → B3 imposible para CUALQUIER receta (rev. 3.1 §3, comprobación analítica)
        self.assertLess(0.55, contract.BAND_B3_MIN)


class TestPerfilAccesibilidad(unittest.TestCase):
    def test_guardrails_por_accesibilidad(self):
        self.assertTrue(accesibilidad.guardrails_default("commercial")["motif_repeat"])
        self.assertTrue(accesibilidad.guardrails_default("balanced")["motif_repeat"])
        self.assertFalse(accesibilidad.guardrails_default("experimental")["motif_repeat"])
        self.assertFalse(accesibilidad.guardrails_default("experimental")["lead_coverage"])
        for acc in contract.ACCESSIBILITIES:
            g = accesibilidad.guardrails_default(acc)
            self.assertEqual(len(g), 8)
            for nombre in accesibilidad.GUARDRAILS_SIEMPRE_ON:
                self.assertTrue(g[nombre])

    def test_balanced_es_el_perfil_del_alcance_fase1(self):
        # instrucción 09: accesibilidad balanced → motif_repeat y lead_coverage ON
        g = accesibilidad.guardrails_default("balanced")
        self.assertTrue(g["motif_repeat"])
        self.assertTrue(g["lead_coverage"])


def _vocab(language):
    if language == "pop_dream_pop":
        return {"", "6", "m", "add9", "sus2", "sus4", "7sus4", "maj7", "maj9", "m7", "m9"}
    if language == "hybrid":
        return _vocab("pop_dream_pop") | {"7", "9", "11", "13", "m11", "m13", "7#11", "m7b5", "5"}
    return None  # experimental: todo lo que parsea el motor


if __name__ == "__main__":
    unittest.main()
