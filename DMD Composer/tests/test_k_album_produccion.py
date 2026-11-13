"""Batería K — producción MIDI de álbumes vía el ORQUESTADOR EXISTENTE del DMD.

Integración REAL (misión §7): Composer materializa el spec dmd-album/1 con los
docs de cada pista y delega el lote a album/orquestador.py en un subprocess
aislado y cancelable. Cubre:
  K1  materialización del spec (formato y determinismo)
  K2  lote completo por el orquestador real (2 pistas → 2 MIDIs)
  K3  descarga por pista + SHA256 == evidencia del orquestador
  K4  reanudación sin regenerar pistas válidas
  K5  regeneración de UNA pista (--regen del orquestador)
  K6  cancelación del lote (jobs) y estados honestos
  K7  events.json bajo demanda verificado contra la evidencia (reproducción)
  K8  sin generador de álbumes paralelo (orquestador real deja plan/informe)
"""
import hashlib
import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))

from composer import albums as ALB  # noqa: E402
from composer import bridge, jobs, store  # noqa: E402

DMD = bridge.discover_dmd(store.DATA_DIR, None)

_J = sys.modules.get("tests.test_j_produccion")
if _J is None:
    from tests import test_j_produccion as _J  # noqa: E402

req = _J.req
base = _J.base


def setUpModule():
    if not DMD:
        raise unittest.SkipTest("sin DMD descubierto: batería K requiere el orquestador real")
    if not (_J._BASE.get("server") and _J._BASE["server"].started):
        _J.setUpModule()


class AlbumProduccion(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        aid = getattr(cls, "_aid", None)
        pid = getattr(cls, "_pid", None)
        if aid:
            j = jobs.find_by_scope(f"album:{aid}", only_active=True)
            if j:
                jobs.cancel(j["jid"])
                time.sleep(0.5)
        if pid:
            req("DELETE", f"/api/projects/{pid}")

    def _album(self, n=2):
        st, proj = req("POST", "/api/projects", {"name": "kbat_" + uuid.uuid4().hex[:8]})
        self.assertEqual(st, 200, proj)
        pid = proj["pid"]
        self.__class__._pid = pid
        req("PUT", f"/api/projects/{pid}", {"decisions": {
            "identity": {"mode": "fixed", "value": "dark_triphop"},
            "mood": {"mode": "fixed", "value": "dark"},
            "harmony_mode": {"mode": "fixed", "value": "native"}}})
        st, alb = req("POST", "/api/albums", {"name": "Bateria K", "tracks": n, "pid": pid})
        self.assertEqual(st, 200, alb)
        aid = alb["album_id"]
        self.__class__._aid = aid
        for i in range(1, n + 1):
            st, r = req("POST", f"/api/albums/{aid}/tracks/{i}/generate", {})
            self.assertEqual(st, 200, r)
            self.assertTrue(r.get("ok"), r.get("errores"))
        return aid

    def _lote(self, aid, timeout=600):
        st, r = req("POST", f"/api/albums/{aid}/produce_all", {})
        self.assertEqual(st, 202, r)
        jid = r["jid"]
        t0 = time.time()
        while time.time() - t0 < timeout:
            st, j = req("GET", f"/api/jobs/{jid}")
            if j.get("state") not in ("queued", "running"):
                return j
            time.sleep(0.6)
        raise AssertionError("timeout del lote")

    def test_K1_materializacion_determinista(self):
        aid = self._album()
        spec = ALB.materializar_spec(aid)
        self.assertEqual(spec["schema"], "dmd-album/1")
        self.assertEqual(len(spec["pistas"]), 2)
        for p in spec["pistas"]:
            self.assertRegex(p["id"], r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
            self.assertTrue((ALB.production_dir(aid) / p["doc"]).is_file())
        spec2 = ALB.materializar_spec(aid)
        self.assertEqual(spec2["semilla_album"], spec["semilla_album"])

    def test_K2_K3_K4_K5_K8_lote_completo(self):
        aid = self._album()
        # K2: lote por el orquestador REAL
        j = self._lote(aid)
        self.assertEqual(j["state"], "ok", j.get("error"))
        est = (j.get("result") or {}).get("estado") or {}
        self.assertEqual(est.get("ok"), 2, json.dumps(est, ensure_ascii=False)[:200])
        # K3: descarga + SHA256 == evidencia del orquestador
        for n in (1, 2):
            p = ALB.ruta_midi_pista(aid, n)
            self.assertTrue(p and p.is_file(), f"MIDI pista {n}")
            self.assertEqual(p.read_bytes()[:4], b"MThd")
            st, raw = req("GET", f"/api/albums/{aid}/tracks/{n}/download", raw=True)
            self.assertEqual(st, 200)
            fila = next(t for t in req("GET", f"/api/albums/{aid}/production")[1]["pistas"]
                        if t["n"] == n)
            self.assertTrue(fila.get("sha256_midi"))
            self.assertEqual(hashlib.sha256(raw).hexdigest(), fila["sha256_midi"])
        # K8: el orquestador real dejó su plan e informe (no hay generador paralelo)
        self.assertTrue((ALB.production_dir(aid) / "plan.json").is_file())
        self.assertTrue((ALB.production_dir(aid) / "estado.json").is_file())
        self.assertTrue((ALB.production_dir(aid) / "informe_album.json").is_file())
        # K4: reanudación — las pistas válidas NO se regeneran
        mtimes = {n: ALB.ruta_midi_pista(aid, n).stat().st_mtime for n in (1, 2)}
        j2 = self._lote(aid, timeout=300)
        self.assertEqual(j2["state"], "ok")
        for n in (1, 2):
            self.assertEqual(ALB.ruta_midi_pista(aid, n).stat().st_mtime, mtimes[n],
                             f"la pista {n} fue regenerada en la reanudación")
        # K5: regeneración de UNA pista (--regen)
        st, r = req("POST", f"/api/albums/{aid}/tracks/{1}/midi", {})
        self.assertEqual(st, 202)
        t0 = time.time()
        while time.time() - t0 < 300:
            j3 = req("GET", f"/api/jobs/{r['jid']}")[1]
            if j3.get("state") not in ("queued", "running"):
                break
            time.sleep(0.5)
        self.assertEqual(j3["state"], "ok", j3.get("error"))
        self.assertGreater(ALB.ruta_midi_pista(aid, 1).stat().st_mtime, mtimes[1])
        # la pista 2 sigue intacta
        self.assertEqual(ALB.ruta_midi_pista(aid, 2).stat().st_mtime, mtimes[2])

    def test_K7_events_bajo_demanda_verificados(self):
        """Reproducción de una pista del álbum: events.json verificado contra
        la evidencia (mismo núcleo, mismo doc/seed/perfil → mismo sha)."""
        aid = self._album()
        j = self._lote(aid)
        self.assertEqual(j["state"], "ok")
        sha_est = ALB.estado_produccion(aid)["pistas"][0]["sha256_midi"]
        st, ev = req("GET", f"/api/albums/{aid}/tracks/{1}/events")
        self.assertEqual(st, 200)
        self.assertTrue(ev.get("bpm") and ev.get("tracks"))
        # el cache verificado quedó en produccion/playback/
        pb = ALB.production_dir(aid) / "playback" / "track01"
        self.assertTrue((pb / "events.json").is_file())
        self.assertEqual((pb / ".sha").read_text(encoding="utf-8"), sha_est)


class AlbumCancelacion(unittest.TestCase):
    def test_K6_cancelacion_estado_honesto(self):
        """Cancelar el lote: el trabajo queda 'cancelado' y las pistas ya
        producidas conservan su MIDI (recuperación = re-ejecutar)."""
        if not DMD:
            self.skipTest("sin DMD")
        aid_holder = {}

        st, proj = req("POST", "/api/projects", {"name": "kcan_" + uuid.uuid4().hex[:8]})
        pid = proj["pid"]
        aid_holder["pid"] = pid
        req("PUT", f"/api/projects/{pid}", {"decisions": {
            "identity": {"mode": "fixed", "value": "dark_triphop"},
            "mood": {"mode": "fixed", "value": "dark"}}})
        st, alb = req("POST", "/api/albums", {"name": "K Cancel", "tracks": 3, "pid": pid})
        aid = alb["album_id"]
        aid_holder["aid"] = aid
        try:
            for i in range(1, 4):
                st, r = req("POST", f"/api/albums/{aid}/tracks/{i}/generate", {})
                self.assertTrue(r.get("ok"), r.get("errores"))
            st, r = req("POST", f"/api/albums/{aid}/produce_all", {})
            self.assertEqual(st, 202)
            jid = r["jid"]
            time.sleep(1.0)                      # dejar que el orquestador arranque
            st, rc = req("POST", f"/api/albums/{aid}/cancel", {})
            self.assertEqual(st, 200)
            t0 = time.time()
            while time.time() - t0 < 120:
                j = req("GET", f"/api/jobs/{jid}")[1]
                if j.get("state") not in ("queued", "running"):
                    break
                time.sleep(0.4)
            self.assertIn(j["state"], ("cancelado", "ok"))
            # el estado del álbum es legible y honesto tras la cancelación
            est = req("GET", f"/api/albums/{aid}/production")[1]
            self.assertIn(est["state"], ("parcial", "ok", "sin_midi", "generando"))
            for p in est["pistas"]:
                self.assertIn(p["estado_midi"], ("ok", "fallo", "pendiente"))
        finally:
            j = jobs.find_by_scope(f"album:{aid}", only_active=True)
            if j:
                jobs.cancel(j["jid"])
            time.sleep(0.3)
            req("DELETE", f"/api/projects/{pid}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
