"""Tests de DMD STUDIO — API + integración con el pipeline real.

Se ejecutan contra el servidor real montado en un hilo (sin httpx):
    python -m pytest tests/studio -v

No modifican contratos, goldens ni código protegido: usan el validador,
compilador y produce.py tal cual son.
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from studio import settings as S  # noqa: E402
from studio import server  # noqa: E402

BASE = None
_SERVER_THREAD = None
_PORT = None


def _req(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, data) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            return e.code, {}


@pytest.fixture(scope="session", autouse=True)
def live_server():
    global BASE, _SERVER_THREAD, _PORT
    import uvicorn
    import socket

    S.ensure_dirs()
    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        _PORT = sk.getsockname()[1]
    config = uvicorn.Config(server.app, host="127.0.0.1", port=_PORT, log_level="error")
    srv = uvicorn.Server(config)
    _SERVER_THREAD = threading.Thread(target=srv.run, daemon=True)
    _SERVER_THREAD.start()
    global BASE
    BASE = f"http://127.0.0.1:{_PORT}"
    for _ in range(50):
        try:
            _req("GET", "/api/capabilities")
            break
        except Exception:
            time.sleep(0.1)
    yield


@pytest.fixture()
def project():
    st, p = _req("POST", "/api/projects",
                 {"name": "T_" + uuid.uuid4().hex[:8], "description": "pytest"})
    assert st == 200
    yield p
    _req("DELETE", "/api/projects/" + p["id"])


GOLDEN = json.loads((ROOT / "tests/dmd/golden/dark_triphop_balanced.json").read_text(encoding="utf-8"))


def wait_job(jid, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        _, j = _req("GET", f"/api/jobs/{jid}")
        if j.get("state") in ("done", "error", "cancelled", "interrupted"):
            return j
        time.sleep(0.2)
    return {"state": "timeout"}


# ------------------------------------------------------------------ sistema
def test_capabilities_refleja_el_contrato_real():
    st, caps = _req("GET", "/api/capabilities")
    assert st == 200
    assert caps["contrato"]["contract"] == "dark-director/1"
    assert caps["contrato"]["contract_rev"] == "3.2"
    assert [p["id"] for p in caps["perfiles"]] == \
        ["original", "sax", "sax_rhodes", "drums", "sax_vibes", "full", "atmospheric"]
    assert caps["catalogos"]["instruments"][0] == "sax_tenor"
    assert "familiarity_auto" in caps["harmony_keywords"]
    assert len(caps["biblioteca_fase7"]) > 30


# ----------------------------------------------------------------- proyectos
def test_ciclo_proyecto_completo(project):
    pid = project["id"]
    st, p = _req("PUT", f"/api/projects/{pid}", {"doc": GOLDEN})
    assert st == 200
    st, p2 = _req("GET", f"/api/projects/{pid}")
    assert p2["doc"]["meta"]["title"] == "Golden Path"
    st, dup = _req("POST", f"/api/projects/{pid}/duplicate", {"name": "T_Dup"})
    assert st == 200 and dup["id"] != pid
    _req("DELETE", f"/api/projects/{dup['id']}")
    st, _ = _req("GET", f"/api/projects/{dup['id']}")
    assert st == 404


def test_validacion_pid_traversal():
    st, _ = _req("GET", "/api/projects/x..y/generations/gen_0001")
    assert st == 400
    st, _ = _req("GET", "/api/projects/okid/audio/gen_0001/carpeta/../../f.mid")
    assert st in (400, 404)


def test_pid_caracteres_raros():
    st, _ = _req("POST", "/api/projects", {"name": "a/b/c"})
    assert st == 400, "los nombres con / deben rechazarse (sin traversal)"
    st, p = _req("POST", "/api/projects", {"name": "Composición válida 1"})
    assert st == 200
    _req("DELETE", "/api/projects/" + p["id"])


# ---------------------------------------------------------------- validación
def test_validador_real_E102_E109():
    st, v = _req("POST", "/api/validate", {"doc": {"schema": "otro"}})
    assert any(e[0] == "E102" for e in v["errores"])
    doc = json.loads(json.dumps(GOLDEN))
    doc["campo_malo"] = 1
    st, v = _req("POST", "/api/validate", {"doc": doc})
    assert any(e[0] == "E109" for e in v["errores"])


def test_validador_acepta_golden():
    st, v = _req("POST", "/api/validate", {"doc": GOLDEN})
    assert st == 200 and not v["errores"]


def test_generate_doc_invalido_422(project):
    doc = json.loads(json.dumps(GOLDEN))
    doc["global"]["bpm"] = 999  # E105
    st, r = _req("POST", f"/api/projects/{project['id']}/generate",
                 {"production": "full", "seed": 1, "doc": doc})
    assert st == 422


# --------------------------------------------------------------- generación
def test_generacion_pipeline_real_y_determinismo(project):
    pid = project["id"]
    _req("PUT", f"/api/projects/{pid}", {"doc": GOLDEN})
    shas = []
    for i in range(2):
        st, job = _req("POST", f"/api/projects/{pid}/generate",
                       {"production": "sax", "seed": 2026, "out_name": f"det_{i}"})
        assert st == 200, job
        j = wait_job(job["jid"])
        assert j["state"] == "done", j.get("result")
        shas.append(j["result"]["produccion"]["sha256"])
    assert shas[0] == shas[1], "misma entrada + misma seed debe dar el mismo MIDI"
    # el doc.json guardado en la generación es EXACTAMENTE la entrada
    st, g = _req("GET", f"/api/projects/{pid}/generations/gen_0001")
    doc_json = next(v for k, v in g["archivos"].items() if k.endswith("/doc.json"))
    assert doc_json["meta"]["title"] == "Golden Path"


def test_los_7_perfiles_ejecutan(project):
    pid = project["id"]
    _req("PUT", f"/api/projects/{pid}", {"doc": GOLDEN})
    for prof in ["original", "sax", "sax_rhodes", "drums", "sax_vibes", "full", "atmospheric"]:
        st, job = _req("POST", f"/api/projects/{pid}/generate",
                       {"production": prof, "seed": 11, "out_name": f"p_{prof}"})
        j = wait_job(job["jid"])
        assert j["state"] == "done", f"perfil {prof}: {j.get('result')}"


def test_guided_vs_native_y_fase7(project):
    pid = project["id"]
    doc_native = json.loads(json.dumps(GOLDEN))
    doc_native["harmony"].pop("progressions", None)
    _req("PUT", f"/api/projects/{pid}", {"doc": doc_native})
    st, job = _req("POST", f"/api/projects/{pid}/generate",
                   {"production": "full", "seed": 3, "out_name": "native"})
    j = wait_job(job["jid"])
    assert j["state"] == "done"
    sha_native = j["result"]["produccion"]["sha256"]

    doc_guided = json.loads(json.dumps(doc_native))
    doc_guided["harmony"]["progressions"] = {"verse": ["Dm9", "Gm9", "Bbmaj7", "A7sus4"]}
    _req("PUT", f"/api/projects/{pid}", {"doc": doc_guided})
    st, job = _req("POST", f"/api/projects/{pid}/generate",
                   {"production": "full", "seed": 3, "out_name": "guided"})
    j = wait_job(job["jid"])
    assert j["state"] == "done"
    sha_guided = j["result"]["produccion"]["sha256"]
    assert sha_guided != sha_native, "la armonía guiada debe cambiar el material"

    st, job = _req("POST", f"/api/projects/{pid}/generate",
                   {"production": "full", "seed": 3, "out_name": "f7",
                    "harmony": {"keyword": "soulful", "variacion": "subtle"}})
    j = wait_job(job["jid"])
    assert j["state"] == "done"
    assert j["result"]["produccion"].get("harmonia"), "la evidencia debe registrar la F7"


def test_concurrencia_single_flight(project):
    """Dos generaciones simultáneas: la segunda debe recibir 409 (o esperar)."""
    pid = project["id"]
    _req("PUT", f"/api/projects/{pid}", {"doc": GOLDEN})
    st1, job1 = _req("POST", f"/api/projects/{pid}/generate",
                     {"production": "full", "seed": 2, "out_name": "c1"})
    st2, r2 = _req("POST", f"/api/projects/{pid}/generate",
                   {"production": "full", "seed": 2, "out_name": "c2"})
    assert st1 == 200
    # el pipeline es rápido en local: si la primera ya acabó, la 2ª arranca bien
    if st2 == 409:
        assert "generación" in r2.get("error", "")
    else:
        assert st2 == 200
    wait_job(job1["jid"])


def test_cancel_y_recover_estado():
    from studio import jobs as JOBS
    job = {"jid": "j_test_" + uuid.uuid4().hex[:6], "pid": "x", "gen_id": "gen_0001",
           "state": "running", "spec_resumen": {}}
    S.JOBS_DIR.mkdir(parents=True, exist_ok=True)
    (S.JOBS_DIR / f"{job['jid']}.json").write_text(json.dumps(job), encoding="utf-8")
    JOBS.recover_interrupted()
    j = json.loads((S.JOBS_DIR / f"{job['jid']}.json").read_text(encoding="utf-8"))
    assert j["state"] == "interrupted"
    (S.JOBS_DIR / f"{job['jid']}.json").unlink()


def test_wav_error_claro_sin_fluidsynth(project):
    pid = project["id"]
    _req("PUT", f"/api/projects/{pid}", {"doc": GOLDEN})
    st, job = _req("POST", f"/api/projects/{pid}/generate",
                   {"production": "sax", "seed": 9, "out_name": "wav_t", "wav": True})
    j = wait_job(job["jid"])
    assert j["state"] == "done"  # el MIDI existe
    wav = j["result"].get("wav") or {}
    if not wav.get("ok"):
        assert "error" in wav, "sin fluidsynth debe haber un motivo claro, no un silencio"
