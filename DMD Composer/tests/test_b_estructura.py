"""B · Estructura — editor libre dentro del contrato."""
import unittest

from util import (DMD_PATH, HAS_DMD, basic_sections, codes_out, compose_project,
                  new_test_project)

from composer import model, structure as ST


class TestBEstructura(unittest.TestCase):

    def test_b1_estructura_con_una_sola_seccion_rechazada(self):
        p = new_test_project()
        p.sections = [model.Section(id="solo", label="Solo", type="break", bars=8)]
        r = compose_project(p, seed=1, validate=False)
        self.assertFalse(r["ok"])
        self.assertIn("E106", codes_out(r))

    def test_b2_estructura_larga_compases_distintos(self):
        p = new_test_project(mood="melancholic")
        p.decisions["key"] = model.decision("fixed", "A minor")
        p.sections = [
            model.Section(id=f"parte_{i}", label=f"Parte {i}", type="break", bars=bars)
            for i, bars in enumerate([4, 8, 12, 16, 8, 4, 8, 16, 8, 4], 1)
        ]
        p.sections[-1].final = True
        p.sections[0].type, p.sections[-1].type = "intro", "outro"
        r = compose_project(p, seed=2, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        tl = ST.timeline(p.sections, 86)
        self.assertEqual(tl["total_bars"], 88)
        self.assertEqual(tl["rows"][2]["start_bar"], 13)   # 4+8+1

    def test_b3_secciones_repetidas_con_ids_unicos(self):
        p = new_test_project(mood="hopeful")
        p.decisions["key"] = model.decision("fixed", "C major")
        p.sections = basic_sections() + [
            model.Section(id="chorus_2", label="Chorus 2", type="chorus", bars=8)]
        r = compose_project(p, seed=4, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertEqual(len(r["doc"]["structure"]), 7)

    def test_b4_nombres_personalizados_mapa_visible(self):
        """'Preludio' (nombre visible) viaja al Song Map; el tipo es del contrato."""
        from composer import songmap
        p = new_test_project(mood="neutral")
        p.decisions["key"] = model.decision("fixed", "D minor")
        p.sections = [
            model.Section(id="preludio", label="Preludio", type="intro", bars=4),
            model.Section(id="coda", label="Coda final", type="outro", bars=8, final=True),
        ]
        r = compose_project(p, seed=6, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        sm = r["song_map"]
        labels = {row["id"]: row["nombre_visible"] for row in sm["secciones"]}
        self.assertEqual(labels["preludio"], "Preludio")
        self.assertEqual(labels["coda"], "Coda final")
        # el JSON del contrato NUNCA contiene el nombre visible como campo nuevo
        self.assertEqual(set(r["doc"]["structure"][0].keys()),
                         {"id", "type", "bars"})

    def test_b5_reordenar_duplicar_eliminar(self):
        secs = basic_sections()
        ST.reorder(secs, 1, 3)                       # verso al puesto del pre
        self.assertEqual(secs[3].id, "verso_1")
        dup = ST.duplicate_section(secs, 3)
        secs.insert(4, dup)
        self.assertTrue(any(s.id == "verso_1_copy" for s in secs))
        ST.normalize_sections(secs, None)            # ids únicos tras duplicar
        del secs[4]
        self.assertEqual(len(secs), 6)

    def test_b6_ids_duplicados_detectados(self):
        p = new_test_project()
        p.sections = [
            model.Section(id="igual", label="A", type="verse", bars=8),
            model.Section(id="igual", label="B", type="chorus", bars=8),
        ]
        r = compose_project(p, seed=1, validate=False)
        self.assertFalse(r["ok"])
        self.assertIn("E106", codes_out(r))

    def test_b7_duracion_total_coherente_bpm(self):
        secs = basic_sections()                       # 4+16+8+16+8+8 = 60
        tl = ST.timeline(secs, 84)
        self.assertEqual(tl["total_bars"], 60)
        esperado = round(60 * 4 * 60.0 / 84, 2)
        self.assertEqual(tl["total_duration_sec"], esperado)

    def test_b8_seccion_invalida_bars_cero(self):
        p = new_test_project()
        p.sections = [
            model.Section(id="intro", label="I", type="intro", bars=0),
            model.Section(id="b", label="B", type="chorus", bars=8),
        ]
        r = compose_project(p, seed=1, validate=False)
        self.assertFalse(r["ok"])

    def test_b9_tipo_fuera_del_catalogo_rechazado(self):
        p = new_test_project()
        p.sections = [
            model.Section(id="s1", label="Solo", type="solo_synth", bars=8),
            model.Section(id="s2", label="B", type="chorus", bars=8),
        ]
        r = compose_project(p, seed=1, validate=False)
        self.assertFalse(r["ok"])
        self.assertTrue(any("catálogo" in e["message"] for e in r["errores"]))


if __name__ == "__main__":
    unittest.main()
