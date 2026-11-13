"""D · Randomización — condicionada, coherente y reproducible."""
import json
import unittest

from util import MANIFEST, basic_sections, compose_project, new_test_project

from composer import model, randomizer as R


class TestDRandomizacion(unittest.TestCase):

    def test_d1_todo_automatico_produce_plan_completo(self):
        p = new_test_project(mood="neutral")
        for eje in ("identity", "accessibility", "bpm", "key", "language"):
            p.decisions[eje] = model.decision("auto")
        p.sections = basic_sections()
        r = compose_project(p, seed=100, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertIn("identity", r["doc"]["direction"])
        self.assertIn("bpm", r["doc"]["global"])
        self.assertIn("key", r["doc"]["harmony"])
        # explicabilidad: cada eje automático tiene entrada de log
        ejes_log = {l["axis"] for l in r["log"]}
        for eje in ("identity", "bpm", "key", "language", "accessibility"):
            self.assertIn(eje, ejes_log)

    def test_d2_todo_fijado_se_respeta_exacto(self):
        p = new_test_project(mood="dark")
        p.decisions.update({
            "identity": model.decision("fixed", "dark_triphop"),
            "accessibility": model.decision("fixed", "commercial"),
            "bpm": model.decision("fixed", 86),
            "key": model.decision("fixed", "G minor"),
            "language": model.decision("fixed", "hybrid"),
            "resolution": model.decision("fixed", "tonal"),
            "harmonic_rhythm_bars": model.decision("fixed", 1),
            "ending": model.decision("fixed", "fade_out"),
            "seed": model.decision("fixed", 55),
        })
        p.sections = basic_sections()
        r = compose_project(p, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        d = r["doc"]
        self.assertEqual(d["direction"]["accessibility"], "commercial")
        self.assertEqual(d["global"]["bpm"], 86)
        self.assertEqual(d["global"]["seed"], 55)
        self.assertEqual(d["harmony"]["key"], "G minor")
        self.assertEqual(d["harmony"]["language"], "hybrid")
        self.assertEqual(d["harmony"]["resolution"], "tonal")
        self.assertEqual(d["harmony"]["harmonic_rhythm_bars"], 1)
        self.assertIn("fade_out", d["ending"])

    def test_d3_configuracion_mixta(self):
        """Fijada manda; auto se resuelve; libre no aparece en el doc."""
        p = new_test_project(mood="melancholic")
        p.decisions["key"] = model.decision("fixed", "D minor")
        p.decisions["bpm"] = model.decision("auto")
        p.decisions["resolution"] = model.decision("free")
        p.sections = basic_sections()
        r = compose_project(p, seed=42, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertEqual(r["doc"]["harmony"]["key"], "D minor")
        self.assertIn("bpm", r["doc"]["global"])
        self.assertNotIn("resolution", r["doc"]["harmony"])
        self.assertIn("resolution", r["free_axes"])

    def test_d4_seed_identica_resultado_identico(self):
        def mk():
            p = new_test_project(mood="melancholic")
            p.decisions["key"] = model.decision("fixed", "D minor")
            p.sections = basic_sections()
            return p
        r1 = compose_project(mk(), seed=2026, validate=False, save=False)
        r2 = compose_project(mk(), seed=2026, validate=False, save=False)
        self.assertEqual(r1["doc"], r2["doc"])
        self.assertEqual(r1["log"], r2["log"])

    def test_d5_seeds_diferentes_resultados_diferentes(self):
        seen = set()
        for seed in (1, 2, 3, 4, 5, 6):
            p = new_test_project(mood="neutral")
            for eje in ("identity", "bpm", "key", "language", "accessibility"):
                p.decisions[eje] = model.decision("auto")
            p.sections = basic_sections()
            r = compose_project(p, seed=seed, validate=False, save=False)
            self.assertTrue(r["ok"], r["errores"])
            seen.add(json.dumps(r["doc"], sort_keys=True))
        self.assertGreater(len(seen), 3, "6 seeds produjeron casi el mismo documento")

    def test_d6_restricciones_contradictorias_informadas_no_silenciadas(self):
        p = new_test_project()
        p.decisions["identity"] = model.decision("fixed", "dark_triphop")
        p.decisions["bpm"] = model.decision("fixed", 150)     # fuera de [70, 96]
        p.sections = basic_sections()
        r = compose_project(p, seed=1, validate=False)
        self.assertTrue(r["ok"])        # compila (W401 no bloquea)...
        codigos_avisos = {a["code"] for a in r["avisos"]}
        self.assertIn("W401", codigos_avisos)  # ...pero se INFORMA
        self.assertEqual(r["doc"]["global"]["bpm"], 150)  # y se RESPETA la decisión

    def test_d7_protagonista_dos_veces_conflicto(self):
        p = new_test_project()
        p.decisions["protagonist"] = model.decision("fixed", "vibraphone")
        p.instruments["sax_tenor"] = model.InstrumentDecision(role="protagonist")
        p.sections = basic_sections()
        r = compose_project(p, seed=1, validate=False)
        self.assertFalse(r["ok"])       # dos protagonistas = conflicto duro
        self.assertTrue(any("protagonistas" in e["message"] for e in r["errores"]))

    def test_d8_compatibilidad_bpm_dentro_del_rango_auto(self):
        rec = MANIFEST["recetas"]["dark_triphop"]
        lo, hi = rec["bpm_rango"]
        for seed in range(20):
            p = new_test_project(mood="neutral")
            p.decisions["identity"] = model.decision("fixed", "dark_triphop")
            p.sections = basic_sections()
            r = compose_project(p, seed=seed, validate=False, save=False)
            bpm = r["doc"]["global"]["bpm"]
            self.assertTrue(lo <= bpm <= hi, f"seed {seed}: bpm {bpm} fuera de [{lo},{hi}]")

    def test_d9_doom_con_ritmo_armonico_coherente(self):
        """Regla de compatibilidad: doom auto NUNCA deja ritmo armónico 1:1."""
        for seed in range(12):
            p = new_test_project(mood="dark")
            p.decisions["identity"] = model.decision("fixed", "doom_triphop")
            p.sections = basic_sections()
            r = compose_project(p, seed=seed, validate=False, save=False)
            hr = r["doc"]["harmony"]["harmonic_rhythm_bars"]
            self.assertGreaterEqual(hr, 2, f"seed {seed}: doom con harmonic_rhythm {hr}")

    def test_d10_espacios_obligatorios_se_honran_en_auto(self):
        p = new_test_project(mood="melancholic")
        p.decisions["spaces"] = model.decision("fixed", "mandatory")
        p.sections = []            # estructura automática
        r = compose_project(p, seed=13, validate=False, save=False)
        self.assertTrue(r["ok"], r["errores"])
        tipos = [s["type"] for s in r["doc"]["structure"]]
        self.assertIn("break", tipos)
        breaks = [s for s in r["doc"]["structure"] if s["type"] == "break"]
        self.assertTrue(breaks and breaks[0].get("drums") == "light")

    def test_d11_diversidad_afloja_y_endurece(self):
        """Contenida tiende al default; aventurada explora (ambas coherentes)."""
        keys = {"restrained": set(), "adventurous": set()}
        for nivel in keys:
            for seed in range(15):
                p = new_test_project(mood="dark")
                p.diversity = nivel
                p.sections = basic_sections()
                r = compose_project(p, seed=seed, validate=False, save=False)
                keys[nivel].add(r["doc"]["harmony"]["key"])
        self.assertGreaterEqual(len(keys["adventurous"]), len(keys["restrained"]) - 1)


if __name__ == "__main__":
    unittest.main()
