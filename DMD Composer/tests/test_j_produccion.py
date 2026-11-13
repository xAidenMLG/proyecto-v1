"""Batería J — producción MIDI individual (misión de integración §8).

Pruebas de integración REALES contra el servidor de Composer arrancado en un
hilo (uvicorn) con el núcleo de producción real del DMD vía puente aislado.
Cliente HTTP 100 % estándar (urllib) para ser compatible con Windows.

Cubre (misión §8, parte individual):
  J1  generación real de MIDI desde Composer (API → puente → núcleo → .mid)
  J2  idempotencia (nunca reescritura)
  J3  determinismo cross-gen y semilla distinta → resultado distinto
  J4  sha(Composer) == sha(núcleo directo) — no hay segundo generador
  J5  doc inválido → estado de error honesto, sin bloque midi, descarga 4xx
  J6  path traversal y whitelist de artefactos
  J7  disciplina de jobs (JobBusy, cancelación, recuperación)
  J8  integridad: MIDI truncado → integridad_error, nunca éxito falso
  J10 CLI de produce.py intacto (comportamiento histórico byte a byte)
  J11 sin código de conversión de audio en Composer (decisión D22)
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
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
_BASE = {"port": None}


def _free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def setUpModule():
    if not DMD:  # sin DMD real las pruebas de integración no pueden correr
        raise unittest.SkipTest("sin DMD descubierto: batería J requiere el núcleo real")
    import uvicorn
    from composer.server import app
    _BASE["port"] = _free_port()
    cfg = uvicorn.Config(app, host="127.0.0.1", port=_BASE["port"],
                         log_level="error", workers=1)
    _BASE["server"] = uvicorn.Server(cfg)
    _BASE["thread"] = threading.Thread(target=_BASE["server"].run, daemon=True)
    _BASE["thread"].start()
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"{base()}/api/system", timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError("el servidor de prueba no arrancó")


def tearDownModule():
    srv = _BASE.get("server")
    if srv:
        srv.should_exit = True
        _BASE["thread"].join(timeout=10)


def base():
    return f"http://127.0.0.1:{_BASE['port']}"


def req(method, path, body=None, raw=False):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(base() + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            b = resp.read()
            return resp.status, (b if raw else json.loads(b or b"null"))
    except urllib.error.HTTPError as e:
        b = e.read()
        try:
            return e.code, json.loads(b or b"null")
        except Exception:
            return e.code, b.decode("utf-8", errors="replace")


def poll(pid, gen, timeout=150):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st, r = req("GET", f"/api/projects/{pid}/generations/{gen}/midi")
        if st == 200 and r["state"] not in ("en_cola", "generando"):
            return r
        time.sleep(0.4)
    raise AssertionError(f"timeout esperando MIDI de {gen}")


def nuevo_proyecto(seed=2026):
    st, proj = req("POST", "/api/projects", {"name": "jbat_" + uuid.uuid4().hex[:8]})
    assert st == 200, proj
    pid = proj["pid"]
    req("PUT", f"/api/projects/{pid}", {"decisions": {
        "identity": {"mode": "fixed", "value": "dark_triphop"},
        "mood": {"mode": "fixed", "value": "dark"},
        "seed": {"mode": "fixed", "value": seed},
        "harmony_mode": {"mode": "fixed", "value": "native"}}})
    return pid


class ProduccionIndividual(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        # cancelar producciones activas ANTES de borrar (evita la carrera
        # rmtree-vs-hijo que dejaría artefactos huérfanos)
        for pid in getattr(cls, "_pids", []):
            j = jobs.find_by_scope(f"produce:{pid}:gen_0001", only_active=True)
            if j:
                jobs.cancel(j["jid"])
                time.sleep(0.5)
        for pid in getattr(cls, "_pids", []):
            req("DELETE", f"/api/projects/{pid}")

    def _pid(self):
        pid = nuevo_proyecto()
        self.__class__._pids = getattr(self.__class__, "_pids", []) + [pid]
        return pid

    def test_J1_e2e_produccion_descarga_verificacion(self):
        """Del API al .mid verificado: composición → puente aislado → núcleo real."""
        pid = self._pid()
        st, r = req("POST", f"/api/projects/{pid}/compose", {"seed": 2026})
        self.assertEqual(st, 200)
        self.assertTrue(r.get("ok"), r.get("errores"))
        gen1 = r["generation"]["gen_id"]
        st, r = req("POST", f"/api/projects/{pid}/generations/{gen1}/midi", {"events": True})
        self.assertEqual(st, 202, r)
        res = poll(pid, gen1)
        self.assertEqual(res["state"], "ok", res.get("job", {}).get("error"))
        block = res["midi"]
        self.assertTrue(block["sha256"])
        st, raw = req("GET", f"/api/projects/{pid}/generations/{gen1}/midi/download", raw=True)
        self.assertEqual(st, 200)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), block["sha256"])
        self.assertEqual(raw[:4], b"MThd")
        st, ev = req("GET", f"/api/projects/{pid}/generations/{gen1}/events")
        self.assertEqual(st, 200)
        self.assertTrue(ev.get("bpm") and ev.get("tracks"))

    def test_J2_idempotencia_sin_reescritura(self):
        """Segunda petición → 200 idempotente con el MISMO sha; bytes intactos."""
        pid = self._pid()
        st, r = req("POST", f"/api/projects/{pid}/compose", {"seed": 2026})
        gen1 = r["generation"]["gen_id"]
        st, r = req("POST", f"/api/projects/{pid}/generations/{gen1}/midi", {"events": True})
        self.assertEqual(st, 202, r)
        res = poll(pid, gen1)
        self.assertEqual(res["state"], "ok", res.get("job", {}).get("error"))
        st, raw1 = req("GET", f"/api/projects/{pid}/generations/{gen1}/midi/download", raw=True)
        self.assertEqual(st, 200)
        st, r = req("POST", f"/api/projects/{pid}/generations/{gen1}/midi", {"events": True})
        self.assertEqual(st, 200)
        self.assertTrue(r.get("idempotente"))
        st, raw2 = req("GET", f"/api/projects/{pid}/generations/{gen1}/midi/download", raw=True)
        self.assertEqual(raw1, raw2)

    def test_J3_determinismo_y_semilla_distinta(self):
        """Mismo doc+seed → mismo sha (cross-gen); seed distinta → sha distinto."""
        pid = self._pid()
        st, r = req("POST", f"/api/projects/{pid}/compose", {"seed": 2026})
        g1 = r["generation"]["gen_id"]
        st, _ = req("POST", f"/api/projects/{pid}/generations/{g1}/midi", {})
        self.assertEqual(st, 202)
        res = poll(pid, g1)
        self.assertEqual(res["state"], "ok", res.get("job", {}).get("error"))
        sha1 = store.read_midi_block(pid, g1)["sha256"]
        st, r = req("POST", f"/api/projects/{pid}/compose", {"seed": 2026})
        g2 = r["generation"]["gen_id"]
        req("POST", f"/api/projects/{pid}/generations/{g2}/midi", {})
        poll(pid, g2)
        self.assertEqual(store.read_midi_block(pid, g2)["sha256"], sha1)
        req("PUT", f"/api/projects/{pid}", {"decisions": {
            "seed": {"mode": "fixed", "value": 777}}})
        st, r = req("POST", f"/api/projects/{pid}/compose", {"seed": 777})
        g3 = r["generation"]["gen_id"]
        req("POST", f"/api/projects/{pid}/generations/{g3}/midi", {})
        poll(pid, g3)
        self.assertNotEqual(store.read_midi_block(pid, g3)["sha256"], sha1)

    def test_J4_igualdad_con_nucleo_directo(self):
        """sha(Composer) == sha(producir_cancion directo con el perfil declarado)."""
        self.assertIsNotNone(DMD)
        pid = self._pid()
        st, r = req("POST", f"/api/projects/{pid}/compose", {"seed": 2026})
        gen1 = r["generation"]["gen_id"]
        req("POST", f"/api/projects/{pid}/generations/{gen1}/midi", {})
        res = poll(pid, gen1)
        sha1 = res["midi"]["sha256"]
        perfil = res["midi"]["perfil"]
        spec = importlib.util.spec_from_file_location(
            "produce_direct", Path(DMD) / "scripts" / "produce.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["produce_direct"] = mod
        spec.loader.exec_module(mod)
        doc = json.loads((store.gen_dir(pid, gen1) / "doc.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            rr = mod.producir_cancion(doc, production=perfil, seed=2026,
                                      out_dir=td, indice=False)
            self.assertEqual(rr["sha256"], sha1)

    def test_J5_doc_faltante_estado_honesto(self):
        """Almacenamiento dañado (doc.json ausente) → estado error con mensaje
        claro del núcleo, SIN bloque midi y descarga 4xx (nunca éxito falso)."""
        pid = self._pid()
        st, r = req("POST", f"/api/projects/{pid}/compose", {"seed": 2026})
        g1 = r["generation"]["gen_id"]
        # dañar el almacenamiento ANTES de producir (fallo real, no simulado)
        (store.gen_dir(pid, g1) / "doc.json").unlink()
        st, r = req("POST", f"/api/projects/{pid}/generations/{g1}/midi", {})
        self.assertEqual(st, 202)
        res = poll(pid, g1)
        self.assertEqual(res["state"], "error")
        self.assertIsNone(res["midi"])
        self.assertIn("doc.json", str(res.get("job", {}).get("error")))
        st, _ = req("GET", f"/api/projects/{pid}/generations/{g1}/midi/download", raw=True)
        self.assertIn(st, (404, 409))

    def test_J6_traversal_y_whitelist(self):
        """Ids malignos → 4xx; artefactos fuera de whitelist → 400."""
        pid = self._pid()
        st, r = req("POST", f"/api/projects/{pid}/compose", {"seed": 2026})
        g1 = r["generation"]["gen_id"]
        st, _ = req("GET", f"/api/projects/{pid}/generations/{'..%2F..%2Fprojects'}/midi")
        self.assertIn(st, (400, 404, 422))
        st, _ = req("GET", f"/api/projects/{pid}/generations/{g1}/midi/artifacts/generation_manifest.json")
        self.assertEqual(st, 400)
        st, _ = req("GET", f"/api/projects/{pid}/generations/{g1}/midi/artifacts/../../../projects/{pid}/project.json")
        self.assertIn(st, (400, 404))
        st, _ = req("GET", f"/api/projects/{pid}/generations/{g1}/events")
        self.assertEqual(st, 404)  # aún sin events: no se simula

    def test_J8_integridad_midi_truncado(self):
        """MIDI corrompido en disco → integridad_error y 409 (nunca éxito falso)."""
        pid = self._pid()
        st, r = req("POST", f"/api/projects/{pid}/compose", {"seed": 2026})
        g1 = r["generation"]["gen_id"]
        req("POST", f"/api/projects/{pid}/generations/{g1}/midi", {})
        poll(pid, g1)
        block = store.read_midi_block(pid, g1)
        ruta = Path(block["rutas"]["midi"])
        bak = ruta.read_bytes()
        try:
            ruta.write_bytes(bak[:len(bak) // 2])   # corromper tras la producción
            st, r = req("GET", f"/api/projects/{pid}/generations/{g1}/midi")
            self.assertEqual(r["state"], "integridad_error")
            st, r = req("POST", f"/api/projects/{pid}/generations/{g1}/midi", {})
            self.assertEqual(st, 409)
            st, _ = req("GET", f"/api/projects/{pid}/generations/{g1}/midi/download", raw=True)
            self.assertEqual(st, 409)
        finally:
            ruta.write_bytes(bak)   # dejar el artefacto como estaba


class DisciplinaJobs(unittest.TestCase):
    def test_jobbusy_cancel_y_recuperacion(self):
        """Un activo por scope; cancelación; recover_interrupted al arrancar."""
        ev_done = threading.Event()

        def worker_lento(ctx):
            for _ in range(60):
                if ctx["cancel_event"].is_set():
                    return {"ok": False, "cancelado": True}
                time.sleep(0.1)
            return {"ok": True}

        j1 = jobs.submit("test", "jbat-test-scope", worker_lento, timeout=30)
        with self.assertRaises(jobs.JobBusy):
            jobs.submit("test", "jbat-test-scope", worker_lento, timeout=30)
        self.assertTrue(jobs.cancel(j1["jid"]))
        for _ in range(50):
            if jobs.get(j1["jid"])["state"] != "running":
                break
            time.sleep(0.1)
        self.assertIn(jobs.get(j1["jid"])["state"], ("cancelado", "ok"))
        # recuperación: un job 'running' persistido sin proceso vivo → interrumpido
        fake = jobs.JOBS_DIR / "test-aaaa-bbbb.json"
        fake.write_text(json.dumps({"jid": "test-aaaa-bbbb", "kind": "test",
                                    "scope": "jbat-fake", "state": "running",
                                    "created_utc": "x", "timeout": 30}),
                        encoding="utf-8")
        n = jobs.recover_interrupted()
        self.assertGreaterEqual(n, 1)
        self.assertEqual(jobs.get("test-aaaa-bbbb")["state"], "interrumpido")
        fake.unlink()


class CliProduceIntacto(unittest.TestCase):
    def test_J10_cli_historico_y_verify(self):
        """El CLI de produce.py conserva su comportamiento (sha 32199acc…)."""
        if not DMD:
            self.skipTest("sin DMD")
        doc = Path(DMD) / "output" / "produccion" / "demo_medianoche" / "doc.json"
        if not doc.is_file():
            self.skipTest("doc de referencia no disponible")
        with tempfile.TemporaryDirectory() as td:
            cp = subprocess.run(
                [sys.executable, str(Path(DMD) / "scripts" / "produce.py"),
                 str(doc), "--production", "full", "--seed", "3113",
                 "--out", td, "--verify",
                 "32199acc254a2eeff93a12d15df3b38ec2c541a45a10a4719d493c696b29a9ff"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=300, shell=False, cwd=str(DMD))
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertIn("VERIFICACION: OK", cp.stdout)


class SinAudioEnComposer(unittest.TestCase):
    def test_J11_sin_conversion_de_audio(self):
        """Decisión D22: ni endpoints ni llamadas de render/conversión de audio.
        (La mención 'soundfont' en PROSA del disclaimer es legítima: avisa que
        la vista previa WebAudio NO equivale al render externo.)"""
        prohibidos = ["/api/mp3", "/api/wav", "fluidsynth", "sfizz",
                      "lamejs", "renderoffline", "soundfontmanager",
                      "offlineaudiocontext"]
        for f in ("server.py", "jobs.py", "store.py", "engine.py", "bridge.py",
                  "albums.py", "static/js/views.js", "static/js/api.js",
                  "static/js/player.js"):
            src = (PKG / "composer" / f).read_text(encoding="utf-8").lower()
            hit = [p for p in prohibidos if p in src]
            self.assertEqual(hit, [], f"{f} contiene código de audio prohibido: {hit}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
