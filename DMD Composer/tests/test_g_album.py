"""G · Modo álbum — trece pistas de un mismo universo con diversidad real."""
import json
import tempfile
import unittest
from pathlib import Path

from util import HAS_DMD, DMD_PATH, MANIFEST

from composer import albums as ALB, model, store, engine


def _base_project():
    p = model.new_project("Vibraphone After Midnight")
    p.pid = ""
    p.decisions.update({
        "identity": model.decision("fixed", "dark_triphop"),
        "mood": model.decision("fixed", "melancholic"),
        "harmony_mode": model.decision("fixed", "guided"),
        "protagonist": model.decision("fixed", "vibraphone"),
        "spaces": model.decision("fixed", "suggested"),
    })
    p.instruments["vibraphone"] = model.InstrumentDecision(role="protagonist")
    return p


class TestGAlbum(unittest.TestCase):

    def setUp(self):
        self._albums_dir_orig = ALB.ALBUMS_DIR
        self._projects_orig = store.PROJECTS_DIR
        self._output_orig = store.OUTPUT_DIR
        self._tmp = tempfile.mkdtemp(prefix="dmdc_album_")
        ALB.ALBUMS_DIR = Path(self._tmp) / "albumes"
        # D-10 del manual v1.0: los tests NO deben dejar proyectos de pistas
        # en el projects/ real del usuario (datos de usuario = zona sagrada).
        store.PROJECTS_DIR = Path(self._tmp) / "projects"
        store.OUTPUT_DIR = Path(self._tmp) / "output"
        self.base = _base_project()

    def tearDown(self):
        ALB.ALBUMS_DIR = self._albums_dir_orig
        store.PROJECTS_DIR = self._projects_orig
        store.OUTPUT_DIR = self._output_orig
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_g1_plan_de_13_pistas(self):
        plan = ALB.new_album("Noches Largas", 13, self.base)
        self.assertEqual(len(plan["pistas"]), 13)
        self.assertEqual(plan["compartido"]["identity"], "dark_triphop")
        self.assertEqual(plan["compartido"]["protagonist"], "vibraphone")

    def test_g2_diversidad_real_no_basta_con_cambiar_seed(self):
        plan = ALB.new_album("Diversidad", 6, self.base)
        keys, bpm, plantillas = set(), set(), set()
        for n in range(1, 7):
            t = ALB.prepare_track(plan, n)
            keys.add(t["key"]); bpm.add(t["bpm"]); plantillas.add(t["plantilla"])
        ALB.save_album(plan)
        self.assertGreater(len(keys), 1, "todas las pistas en la misma tonalidad")
        self.assertGreater(len(plantillas), 1, "todas las pistas con la misma estructura")
        self.assertGreater(len(bpm), 1, "todas las pistas al mismo BPM")
        # huellas: sin combinaciones exactas repetidas
        self.assertEqual(len(plan["huellas"]), len({json.dumps(h, sort_keys=True)
                                                    for h in plan["huellas"]}))

    def test_g3_restricciones_compartidas_en_proyecto_de_pista(self):
        plan = ALB.new_album("Universo", 3, self.base)
        proj = ALB.track_project(plan["album_id"], 1)
        self.assertEqual(proj.fixed_value("identity"), "dark_triphop")
        self.assertEqual(proj.fixed_value("protagonist"), "vibraphone")
        self.assertEqual(proj.fixed_value("spaces"), "suggested")
        self.assertEqual(proj.instruments["vibraphone"].role, "protagonist")

    def test_g4_reanudacion_no_regenera_lo_listo(self):
        plan = ALB.new_album("Reanudar", 3, self.base)
        plan["pistas"][0].update({"estado": "lista", "seed": 12345, "key": "D minor",
                                  "bpm": 86, "language": "pop_dream_pop",
                                  "plantilla": 0, "gen": "gen_0001"})
        t = ALB.prepare_track(plan, 1)
        self.assertEqual(t["seed"], 12345)
        self.assertEqual(t["key"], "D minor")

    def test_g5_reproducibilidad_por_pista(self):
        """El MISMO plan (copia idéntica) produce la misma pista siempre."""
        import copy
        plan = ALB.new_album("Repro", 3, self.base)
        t1 = ALB.prepare_track(copy.deepcopy(plan), 2)
        t2 = ALB.prepare_track(copy.deepcopy(plan), 2)
        self.assertEqual(t1["seed"], t2["seed"])
        self.assertEqual(t1["key"], t2["key"])
        self.assertEqual(t1["language"], t2["language"])

    @unittest.skipUnless(HAS_DMD, "sin DMD real")
    def test_g6_tres_pistas_completas_validas_y_distintas(self):
        plan = ALB.new_album("Ep", 3, self.base)
        docs = []
        for n in (1, 2, 3):
            proj = ALB.track_project(plan["album_id"], n)
            r = engine.compose(proj, DMD_PATH, MANIFEST, save=False)
            self.assertTrue(r["ok"], f"pista {n}: {r['errores']}")
            docs.append(r["doc"])
        self.assertEqual(len({json.dumps(d, sort_keys=True) for d in docs}), 3,
                         "hay pistas duplicadas")

    def test_g7_fuera_de_rango_rechazado(self):
        plan = ALB.new_album("Rango", 2, self.base)
        with self.assertRaises(ALB.AlbumError):
            ALB.prepare_track(plan, 3)


if __name__ == "__main__":
    unittest.main()
