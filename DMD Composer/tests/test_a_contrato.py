"""A · Contrato — compatibilidad REAL con dark-director/1 rev 3.2.

El árbitro es el validador REAL del DMD descubierto (puente aislado).
Si no hay DMD, los tests de validación viva se marcan skip con honestidad.
"""
from util import (DMD_PATH, HAS_DMD, MANIFEST, DOC_BUILTIN, basic_sections,
                  codes_out, compose_project, new_test_project)
from composer import bridge, model, builder as B, randomizer as R
from composer import harmony as H
import unittest


@unittest.skipUnless(HAS_DMD, "sin DMD real descubierto: no se puede validar en vivo")
class TestAContrato(unittest.TestCase):
    """Compatibilidad real con el validador y compilador del DMD."""

    def _validar(self, doc):
        r = bridge.validate_doc(DMD_PATH, doc)
        self.assertTrue(r.get("ok"), f"puente falló: {r.get('error')}")
        return r["validacion"]

    def test_a1_documento_guided_valido_sin_errores(self):
        p = new_test_project(mood="melancholic")
        p.decisions["key"] = model.decision("fixed", "D minor")
        p.sections = basic_sections()
        p.harmony_sections = {
            "intro": model.HarmonySection(mode="guided", numerals="i - III"),
            "verso_1": model.HarmonySection(mode="guided", numerals="i - III - VII - VI"),
            "estribillo": model.HarmonySection(mode="guided", numerals="VI - VII - i - V"),
            "outro": model.HarmonySection(mode="guided", numerals="i - VI"),
        }
        r = compose_project(p, seed=11, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        v = self._validar(r["doc"])
        self.assertEqual(v["errores"], [], f"E-codes reales: {v['errores']}")

    def test_a2_cero_campos_inventados_E109(self):
        """El documento nunca dispara E109 (campo desconocido) en NINGÚN nivel."""
        p = new_test_project(mood="dark")
        p.decisions["key"] = model.decision("fixed", "C minor")
        p.decisions["bpm"] = model.decision("fixed", 84)
        p.decisions["accessibility"] = model.decision("fixed", "experimental")
        p.decisions["language"] = model.decision("fixed", "hybrid")
        p.decisions["resolution"] = model.decision("fixed", "chromatic")
        p.instruments["strings"] = model.InstrumentDecision(role="support", enabled=True)
        p.sections = basic_sections()
        p.sections[1].energy, p.sections[1].tension, p.sections[1].density = 0.5, 0.4, 0.5
        p.sections[1].drums = "groove"
        p.sections[1].focus = ["sax_tenor", "drums"]
        p.sections[3].loop_bars = 8
        p.harmony_sections = {
            "verso_1": model.HarmonySection(mode="guided", numerals="i - iim7b5 - bVI - V7"),
            "estribillo": model.HarmonySection(mode="guided", numerals="bVI - bVII - i - i"),
        }
        r = compose_project(p, seed=7, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        v = self._validar(r["doc"])
        e109 = [e for e in v["errores"] if e[0] == "E109"]
        self.assertEqual(e109, [], "campos no admitidos por el validador: " + str(e109))

    def test_a3_native_harmony_libre_del_motor(self):
        """Native Harmony: sin progressions en el doc; la receta N1 decide."""
        p = new_test_project()
        p.decisions["harmony_mode"] = model.decision("fixed", "native")
        p.decisions["key"] = model.decision("fixed", "D minor")
        p.sections = basic_sections()
        r = compose_project(p, seed=3, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertNotIn("progressions", r["doc"]["harmony"])
        self.assertEqual(r["build"]["nativas_n1"], True)

    def test_a4_guided_y_native_se_preservan_como_rutas_distingibles(self):
        p = new_test_project()
        p.decisions["key"] = model.decision("fixed", "D minor")
        p.sections = basic_sections()
        p.harmony_sections["verso_1"] = model.HarmonySection(mode="guided", numerals="i - VI - III - VII")
        r = compose_project(p, seed=3, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        # solo la sección guiada viaja; el resto queda libre (receta por type)
        progs = r["doc"]["harmony"]["progressions"]
        self.assertEqual(list(progs.keys()), ["verso_1"])

    def test_a5_x_fields_no_los_usa_composer(self):
        """Composer no necesita x_* (nada de información privada viaja al doc)."""
        p = new_test_project()
        p.sections = basic_sections()
        r = compose_project(p, seed=5, validate=False)
        for k in r["doc"]:
            self.assertFalse(k.startswith("x_"), "extensión inesperada en la raíz")

    def test_a6_f7_opcional_no_se_mezcla_silenciosamente(self):
        """F7 (biblioteca Fase 7) es opcional de Studio; el doc NUNCA la contiene."""
        p = new_test_project()
        p.sections = basic_sections()
        p.production = {"profile": "full", "f7_keyword": "melancholic",
                        "f7_variation": "subtle", "wav": False}
        r = compose_project(p, seed=9, validate=False)
        self.assertTrue(r["ok"])
        self.assertNotIn("x_f7", r["doc"])
        self.assertNotIn("harmony_keyword", r["doc"].get("harmony", {}))

    def test_a7_ejemplo_exacto_de_la_mision(self):
        """C major I-III-vi-V → C-Em-Am-G (tabla de conversión de la misión)."""
        key = H.parse_key("C major")
        ch = H.resolve_progression("I - III - vi - V", key)
        self.assertEqual([c.symbol for c in ch], ["C", "Em", "Am", "G"])

    def test_a8_documentos_builtin_coinciden_con_dmd_vivo(self):
        """La instantánea incluida (fallback offline) es VERIFICABLE contra el vivo."""
        if not DOC_BUILTIN:
            self.skipTest("no hay instantánea incluida")
        self.assertEqual(DOC_BUILTIN["catalogos"], MANIFEST["catalogos"])
        self.assertEqual(DOC_BUILTIN["recetas"], MANIFEST["recetas"])


if __name__ == "__main__":
    unittest.main()
