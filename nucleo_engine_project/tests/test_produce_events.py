"""Regresión Opción A — events.json en producir_cancion (misión de integración).

Garantías:
  R1  mismo doc + seed → MIDI BYTE A BYTE idéntico con events=False (histórico)
  R2  events=False → NO se escribe events.json; result["events"] is None
  R3  events=True  → events.json válido (formato to_events) y MIDI idéntico
  R4  evidencia.json registra el sha256 real del MIDI en ambos modos
  R5  CLI: --verify sigue funcionando y --events no altera el MIDI
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.produce import producir_cancion  # noqa: E402

DOC_REF = ROOT / "output" / "produccion" / "demo_medianoche" / "doc.json"
SHA_REF = "32199acc254a2eeff93a12d15df3b38ec2c541a45a10a4719d493c696b29a9ff"


def _mid_de(out: Path) -> bytes:
    mids = list(out.glob("*.mid"))
    assert len(mids) == 1, mids
    return mids[0].read_bytes()


@unittest.skipUnless(DOC_REF.is_file(), "doc de referencia demo_medianoche no disponible")
class RegresionEvents(unittest.TestCase):
    def test_R1_R2_sin_events_comportamiento_historico(self):
        doc = json.loads(DOC_REF.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as ta, tempfile.TemporaryDirectory() as tb:
            ra = producir_cancion(doc, production="full", seed=3113, out_dir=ta, indice=False)
            rb = producir_cancion(doc, production="full", seed=3113, out_dir=tb, indice=False,
                                  events=False)
            self.assertEqual(ra["sha256"], SHA_REF)
            self.assertEqual(rb["sha256"], SHA_REF)
            self.assertEqual(_mid_de(Path(ta)), _mid_de(Path(tb)))
            self.assertIsNone(ra.get("events"))
            self.assertIsNone(rb.get("events"))
            self.assertFalse((Path(tb) / "events.json").exists())
            ev = json.loads((Path(ta) / "evidencia.json").read_text(encoding="utf-8"))
            self.assertEqual(ev["sha256_midi"], SHA_REF)

    def test_R3_con_events_midi_identico(self):
        doc = json.loads(DOC_REF.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as ta, tempfile.TemporaryDirectory() as tb:
            ra = producir_cancion(doc, production="full", seed=3113, out_dir=ta, indice=False)
            rb = producir_cancion(doc, production="full", seed=3113, out_dir=tb, indice=False,
                                  events=True)
            self.assertEqual(_mid_de(Path(ta)), _mid_de(Path(tb)),
                             "events=True NO debe alterar el MIDI")
            self.assertEqual(rb["sha256"], SHA_REF)
            f = Path(rb["events"])
            self.assertTrue(f.is_file())
            ev = json.loads(f.read_text(encoding="utf-8"))
            for k in ("bpm", "total_beats", "tracks", "sections"):
                self.assertIn(k, ev)
            self.assertTrue(all(isinstance(t.get("notes"), list) for t in ev["tracks"]))
            self.assertTrue(all(len(n) == 4 for t in ev["tracks"] for n in t["notes"][:5]))

    def test_R4_evidencia_sha_en_ambos_modos(self):
        doc = json.loads(DOC_REF.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            r = producir_cancion(doc, production="full", seed=3113, out_dir=td,
                                 indice=False, events=True)
            ev = json.loads((Path(td) / "evidencia.json").read_text(encoding="utf-8"))
            self.assertEqual(ev["sha256_midi"], hashlib.sha256(_mid_de(Path(td))).hexdigest())
            self.assertEqual(ev["sha256_midi"], r["sha256"])

    def test_R5_cli_verify_y_events(self):
        with tempfile.TemporaryDirectory() as td:
            cp = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "produce.py"), str(DOC_REF),
                 "--production", "full", "--seed", "3113", "--out", td,
                 "--verify", SHA_REF],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=300, shell=False, cwd=str(ROOT))
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertIn("VERIFICACION: OK", cp.stdout)
            self.assertFalse((Path(td) / "events.json").exists())
        with tempfile.TemporaryDirectory() as td2:
            cp2 = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "produce.py"), str(DOC_REF),
                 "--production", "full", "--seed", "3113", "--out", td2, "--events"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=300, shell=False, cwd=str(ROOT))
            self.assertEqual(cp2.returncode, 0, cp2.stdout + cp2.stderr)
            self.assertTrue((Path(td2) / "events.json").exists())
            self.assertIn(SHA_REF[:32], cp2.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
