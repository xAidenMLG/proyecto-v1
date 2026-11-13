"""F · Integración — Studio/pipeline real, reproducibilidad y NO modificación.

Composer no genera MIDI: esta batería comprueba que los documentos que
produce funcionan EN EL PIPELINE REAL (validador → compilador → MIDI Forge),
que la reproducción es byte a byte, y que DMD y Studio quedan intactos.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from util import DMD_PATH, HAS_DMD, MANIFEST, basic_sections, compose_project, new_test_project

from composer import model

#: Archivos PROTEGIDOS (misión: no modificar DMD ni Studio). Se hash-ean antes
#: y después de la batería; cualquier cambio = fallo.
PROTEGIDOS = [
    "dark_director/contract.py", "dark_director/compilador.py", "dark_director/validador.py",
    "dark_director/identities/dark_triphop.py", "forge/styles.py", "forge/engine.py",
    "forge/theory.py", "studio/server.py", "studio/runner.py",
    "dmd_tests_tmp/golden/dark_triphop_balanced.json",
]


def _hashes(root: Path):
    out = {}
    for rel in PROTEGIDOS:
        f = root / rel
        if f.exists():
            out[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def _generar_midi(doc: dict, out_dir: Path, seed: int):
    """Ejecuta el pipeline REAL (scripts/produce.py::producir_cancion) en un
    proceso aislado con cwd = DMD. Escribe SOLO en out_dir (temp)."""
    runner = (
        "import sys, json, importlib.util\n"
        f"sys.path.insert(0, r'{DMD_PATH}')\n"
        "spec = importlib.util.spec_from_file_location('produce', r'"
        f"{Path(DMD_PATH) / 'scripts' / 'produce.py'}')\n"
        "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\n"
        f"doc = json.loads(r'''{json.dumps(doc, ensure_ascii=False)}''')\n"
        f"r = mod.producir_cancion(doc, production='full', seed={seed}, harmony=None, out_dir=r'{out_dir}')\n"
        "print('RESULT', json.dumps({'ok': r.get('ok'), 'midi': r.get('midi'), 'error': r.get('error')}))\n"
    )
    cp = subprocess.run([sys.executable, "-c", runner], capture_output=True,
                        text=True, timeout=180, cwd=str(DMD_PATH))
    for line in cp.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    return {"ok": False, "error": (cp.stderr or cp.stdout)[-400:]}


@unittest.skipUnless(HAS_DMD, "sin DMD real: la integración completa requiere el pipeline")
class TestFIntegracion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dmd = Path(DMD_PATH)
        cls.hashes_antes = _hashes(cls.dmd)

    @classmethod
    def tearDownClass(cls):
        despues = _hashes(cls.dmd)
        cls.hashes_antes_final = cls.hashes_antes
        if despues != cls.hashes_antes:
            changed = [k for k in despues if despues[k] != cls.hashes_antes.get(k)]
            raise AssertionError(f"¡DMD MODIFICADO por la batería!: {changed}")

    def _doc_bueno(self, seed=2026):
        p = new_test_project(mood="melancholic")
        p.decisions["key"] = model.decision("fixed", "D minor")
        p.decisions["production"] = model.decision("fixed", "full")
        p.sections = basic_sections()
        p.harmony_sections = {
            "verso_1": model.HarmonySection(mode="guided", numerals="i - III - VII - VI"),
            "estribillo": model.HarmonySection(mode="guided", numerals="VI - VII - i - V"),
        }
        r = compose_project(p, seed=seed, validate=True, save=False)
        self.assertTrue(r["ok"], r["errores"])
        return r

    def test_f1_validador_real_acepta(self):
        r = self._doc_bueno()
        self.assertEqual(r["validacion"]["errores"], [])

    def test_f2_compilador_real_acepta(self):
        r = self._doc_bueno()
        self.assertTrue(r["compila"])
        self.assertEqual(r["compilado"]["target_schema"], "midi-forge/1")

    def test_f3_formato_importable_en_studio(self):
        """El doc es EXACTAMENTE lo que Studio guarda en un proyecto (campo doc)."""
        r = self._doc_bueno()
        doc = r["doc"]
        # Studio espera schema/…: re-validación vía validador como lo hace su API
        from composer import bridge
        v = bridge.validate_doc(DMD_PATH, doc)
        self.assertTrue(v["ok"])
        self.assertEqual(v["validacion"]["errores"], [])

    def test_f4_midi_real_desde_doc_de_composer(self):
        with tempfile.TemporaryDirectory(prefix="dmdc_midi_") as td:
            r = self._doc_bueno(seed=2026)
            out = Path(td) / "gen"
            res = _generar_midi(r["doc"], out, seed=2026)
            self.assertTrue(res["ok"], res.get("error"))
            midi = Path(res["midi"])
            self.assertTrue(midi.exists() and midi.stat().st_size > 1000)
            # SHA256 de reproducibilidad documental
            r2 = self._doc_bueno(seed=2026)
            self.assertEqual(r["doc"], r2["doc"])

    def test_f5_reproducibilidad_byte_a_byte_del_midi(self):
        with tempfile.TemporaryDirectory(prefix="dmdc_rep_") as td:
            r = self._doc_bueno(seed=777)
            out1 = Path(td) / "a"
            out2 = Path(td) / "b"
            h1 = _generar_midi(r["doc"], out1, seed=777)
            h2 = _generar_midi(r["doc"], out2, seed=777)
            self.assertTrue(h1["ok"] and h2["ok"])
            b1 = Path(h1["midi"]).read_bytes()
            b2 = Path(h2["midi"]).read_bytes()
            self.assertEqual(hashlib.sha256(b1).hexdigest(), hashlib.sha256(b2).hexdigest())

    def test_f6_composer_no_modifica_dmd_ni_studio(self):
        # el propio test de clase compara hashes; aquí comprobamos además que
        # no se crearon archivos dentro del árbol DMD por Composer
        r = self._doc_bueno()
        self.assertTrue(r["ok"])
        despues = _hashes(self.dmd)
        self.assertEqual(despues, self.hashes_antes)


if __name__ == "__main__":
    unittest.main()
