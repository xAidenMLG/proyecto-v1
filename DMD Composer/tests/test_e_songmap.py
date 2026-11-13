"""E · Song Map — compases, correspondencia con el JSON y con el compilado."""
import unittest

from util import DMD_PATH, HAS_DMD, basic_sections, compose_project, new_test_project

from composer import model, songmap as SM


class TestESongMap(unittest.TestCase):

    def _compose(self, seed=31, **kw):
        p = new_test_project(mood="melancholic", **kw)
        p.decisions["key"] = model.decision("fixed", "D minor")
        p.sections = basic_sections()
        p.harmony_sections = {
            "verso_1": model.HarmonySection(mode="guided", numerals="i - III - VII - VI"),
            "estribillo": model.HarmonySection(mode="guided", numerals="VI - VII - i - V"),
        }
        return compose_project(p, seed=seed, validate=False)

    def test_e1_compases_iniciales_y_finales_correctos(self):
        r = self._compose()
        self.assertTrue(r["ok"], r["errores"])
        rows = r["song_map"]["secciones"]
        esperados = [("intro", 1, 4), ("verso_1", 5, 20), ("pre", 21, 28),
                     ("estribillo", 29, 44), ("puente", 45, 52), ("outro", 53, 60)]
        for row, (sid, ini, fin) in zip(rows, esperados):
            self.assertEqual((row["id"], row["compas_inicial"], row["compas_final"]),
                             (sid, ini, fin))
        self.assertEqual(r["song_map"]["compases_totales"], 60)

    def test_e2_progresiones_del_mapa_coinciden_con_el_json(self):
        r = self._compose()
        progs_doc = r["doc"]["harmony"]["progressions"]
        for row in r["song_map"]["secciones"]:
            if row["id"] in progs_doc:
                self.assertEqual(row["progresion"], progs_doc[row["id"]])
                self.assertEqual(row["fuente_armonia"], "progressions_id")

    def test_e3_duracion_correcta(self):
        r = self._compose()
        bpm = r["doc"]["global"]["bpm"]
        fila_verso = r["song_map"]["secciones"][1]
        self.assertEqual(fila_verso["compases"], 16)
        esperado = round(16 * 4 * 60.0 / bpm, 2)
        self.assertEqual(fila_verso["duracion_seg"], esperado)

    def test_e4_csv_con_correspondencia(self):
        r = self._compose()
        csv = r["song_map_csv"]
        lines = csv.strip().split("\n")
        self.assertEqual(lines[0].split(",")[1:5], ["id", "nombre_visible", "tipo_funcional", "compas_inicial"])
        self.assertEqual(len(lines), 7)          # cabecera + 6 secciones
        self.assertIn("verso_1", lines[2])

    def test_e5_grid_por_compas_real(self):
        r = self._compose()
        grid = r["song_map"]["secciones"][1]["grid_por_compas"]
        self.assertEqual(len(grid), 16)
        # i - III - VII - VI con ritmo armónico de la receta (1 compás por acorde
        # en dark_triphop; si el plan eligió 2, el grid respeta el ciclo del motor)
        hr = r["doc"]["harmony"]["harmonic_rhythm_bars"]
        if hr == 1:
            self.assertEqual(grid[:4], ["Dm", "F", "C", "Bb"])

    def test_e6_bloque_para_letras(self):
        r = self._compose()
        letras = r["song_map"]["notas_para_letras"]
        self.assertEqual(len(letras), 6)
        self.assertIn("[Verso 1]", letras[1])
        self.assertIn("5–20", letras[1])

    @unittest.skipUnless(HAS_DMD, "sin DMD real")
    def test_e7_correspondencia_con_estructura_compilada(self):
        """El Song Map debe coincidir con lo que el COMPILADOR REAL emite."""
        from composer import bridge
        r = self._compose(seed=2026)
        self.assertTrue(r["ok"])
        c = bridge.compile_preview(DMD_PATH, r["doc"])
        self.assertTrue(c.get("ok"), c.get("error"))
        por_id = {s["id"]: s for s in c["secciones"]}
        for row in r["song_map"]["secciones"]:
            sid = row["id"]
            self.assertIn(sid, por_id)
            comp = por_id[sid]
            self.assertEqual(comp["bars"], row["compases"])
            # acordes: la cadena de precedencia id > type > N1 debe dar lo mismo
            if row["fuente_armonia"] == "progressions_id":
                self.assertEqual(comp["chords"], row["progresion"])
            elif row["fuente_armonia"] == "receta_n1":
                self.assertEqual(comp["chords"], row["progresion"],
                                 f"N1 mal calculado en {sid}: motor={comp['chords']} mapa={row['progresion']}")


if __name__ == "__main__":
    unittest.main()
