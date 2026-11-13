"""H · Seguridad y robustez — auditoría técnica automatizada.

Cubre los requisitos de la misión §11: servidor solo-localhost, protección
path traversal, límites de tamaño, escritura atómica, no-eval, no-sobrescritura
de generaciones y no-ejecución de código desde la interfaz.
"""
import json
import tempfile
import unittest
from pathlib import Path

import util
from util import HAS_DMD

from composer import bridge, model, store

PKG = util.PKG


class TestHSeguridad(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="dmdc_sec_")
        self._projects = store.PROJECTS_DIR
        self._output = store.OUTPUT_DIR
        store.PROJECTS_DIR = Path(self._tmp) / "projects"
        store.OUTPUT_DIR = Path(self._tmp) / "output"

    def tearDown(self):
        import shutil
        store.PROJECTS_DIR = self._projects
        store.OUTPUT_DIR = self._output
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ---- path traversal -------------------------------------------------------
    def test_h1_path_traversal_en_ids(self):
        for bad in ("../etc", "..\\x", "a/b", ".oculto", "x" * 60, "", "p;id"):
            with self.assertRaises(store.StoreError):
                store.safe_pid(bad)

    def test_h2_ids_validos_aceptados(self):
        self.assertEqual(store.safe_pid("mi_proyecto-1"), "mi_proyecto-1")

    def test_h3_nombres_peligrosos_rechazados(self):
        for bad in ("con\\barra", "dos:puntos", "aster*isco", "", ".", "..", "a" * 70):
            with self.assertRaises(store.StoreError):
                store.safe_name(bad)

    def test_h4_nombre_traversal_rechazado_sin_crearse(self):
        """safe_name protege: un nombre con '/' se rechaza y no se crea nada."""
        with self.assertRaises(store.StoreError):
            store.create_project("../../etc/passwd")
        self.assertFalse((store.PROJECTS_DIR / ".." / "etc").exists())
        self.assertEqual(list(store.PROJECTS_DIR.glob("*")), [])

    # ---- servidor -------------------------------------------------------------
    def test_h5_bind_solo_localhost(self):
        src = (PKG / "composer" / "__main__.py").read_text(encoding="utf-8")
        self.assertIn('HOST = "127.0.0.1"', src)
        self.assertNotIn("0.0.0.0", src)

    def test_h6_sin_eval_ni_exec_en_composer(self):
        """No se ejecuta código suministrado (misión §11): ni eval ni exec."""
        for f in (PKG / "composer").rglob("*.py"):
            src = f.read_text(encoding="utf-8")
            self.assertNotIn("eval(", src, f"{f.name} usa eval")
            self.assertNotIn("exec(", src, f"{f.name} usa exec")
            self.assertNotIn("shell=True", src, f"{f.name} usa shell")

    def test_h7_bridge_sin_shell_argv_fijo(self):
        src = (PKG / "composer" / "bridge.py").read_text(encoding="utf-8")
        self.assertIn("shell=False", src)
        self.assertIn("timeout", src)

    # ---- límites y escritura ----------------------------------------------------
    def test_h8_escritura_atomica_y_carga_idempotente(self):
        p = store.create_project("Atomico")
        p.decisions["bpm"] = model.decision("fixed", 90)
        store.save_project(p)
        p2 = store.load_project(p.pid)
        self.assertEqual(p2.fixed_value("bpm"), 90)
        # no quedan .tmp tras escribir
        leftovers = list((store.PROJECTS_DIR / p.pid).glob("*.tmp"))
        self.assertEqual(leftovers, [])

    def test_h9_no_sobrescribe_generaciones(self):
        p = store.create_project("Historial")
        p.sections = [
            model.Section(id="intro", label="I", type="intro", bars=4),
            model.Section(id="out", label="O", type="outro", bars=8, final=True),
        ]
        from composer import engine
        r1 = engine.compose(p, None, util.MANIFEST, seed_override=5, save=True, validate=False)
        r2 = engine.compose(p, None, util.MANIFEST, seed_override=5, save=True, validate=False)
        self.assertEqual(r1["generation"]["gen_id"], "gen_0001")
        self.assertEqual(r2["generation"]["gen_id"], "gen_0002")

    def test_h10_generaciones_sobreviven_ids_malignos(self):
        with self.assertRaises(store.StoreError):
            store.get_generation("../../etc", "gen_0001")
        with self.assertRaises(store.StoreError):
            store.get_generation("p", "../../etc/passwd")

    # ---- validación de entrada ---------------------------------------------------
    def test_h11_proyecto_corrupto_da_error_limpio(self):
        (store.PROJECTS_DIR / "roto").mkdir(parents=True)
        (store.PROJECTS_DIR / "roto" / "project.json").write_text("{ no-json")
        with self.assertRaises(Exception):
            store.load_project("roto")

    def test_h12_decisiones_desconocidas_rechazadas_por_api(self):
        """La API no acepta ejes fuera del vocabulario (sin campos inventados)."""
        from fastapi.testclient import TestClient
        from composer import server
        client = TestClient(server.app)
        p = client.post("/api/projects", json={"name": "H11 test"}).json()
        r = client.put(f"/api/projects/{p['pid']}", json={
            "decisions": {"eje_inventado": {"mode": "fixed", "value": 1}}})
        self.assertEqual(r.status_code, 400)

    def test_h13_instrumento_fuera_de_catalogo_rechazado(self):
        from fastapi.testclient import TestClient
        from composer import server
        client = TestClient(server.app)
        p = client.post("/api/projects", json={"name": "H13 test"}).json()
        r = client.put(f"/api/projects/{p['pid']}", json={
            "instruments": {"guitarra_electrica": {"role": "support"}}})
        self.assertEqual(r.status_code, 400)

    def test_h14_seccion_tipo_inventado_rechazado(self):
        from fastapi.testclient import TestClient
        from composer import server
        client = TestClient(server.app)
        p = client.post("/api/projects", json={"name": "H14 test"}).json()
        r = client.put(f"/api/projects/{p['pid']}", json={
            "sections": [{"id": "a", "label": "A", "type": "drop_the_bass", "bars": 8},
                         {"id": "b", "label": "B", "type": "chorus", "bars": 8}]})
        self.assertEqual(r.status_code, 400)

    def test_h15_ruta_dmd_invalida_rechazada_por_config(self):
        from fastapi.testclient import TestClient
        from composer import server
        client = TestClient(server.app)
        r = client.put("/api/config", json={"dmd_path": "/tmp/definitivamente/no/existe"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
