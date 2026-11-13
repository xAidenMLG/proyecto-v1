"""Gestión de trabajos de generación — un solo pipeline en ejecución.

* Ejecuta ``studio.runner`` como subproceso (aislamiento: un fallo del
  pipeline no derriba el servidor; la interfaz nunca se bloquea).
* Concurrencia controlada: SOLO una generación activa. Una segunda petición
  recibe 409 (evita generaciones simultáneas conflictivas sobre los mismos
  recursos y desajustes de determinismo por carga).
* Estado persistido en disco (``jobs/<jid>.json`` + log en la carpeta de la
  generación): si el servidor se cierra a mitad, al reiniciar el trabajo se
  marca ``interrupted`` y el proyecto queda íntegro.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import projects as P
from . import settings as S

MAX_LOG_LINES = 1200
HARD_TIMEOUT_S = 900  # 15 min: margen sobrado para cualquier composición local

_states = {}
_lock = threading.Lock()
_proc = {}


class JobBusy(Exception):
    pass


class JobNotFound(Exception):
    pass


def _jobfile(jid: str) -> Path:
    if not jid or "/" in jid or "\\" in jid or ".." in jid:
        raise ValueError("jid no válido")
    return S.JOBS_DIR / f"{jid}.json"


def _persist(job: dict) -> None:
    try:
        _jobfile(job["jid"]).write_text(
            json.dumps({k: v for k, v in job.items() if k != "_lines"},
                       ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def recover_interrupted() -> None:
    """Al arrancar: todo trabajo 'running/queued' sin proceso vivo → interrupted."""
    S.ensure_dirs()
    for f in S.JOBS_DIR.glob("*.json"):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if j.get("state") in ("running", "queued"):
            j["state"] = "interrupted"
            j.setdefault("_lines", []).append(
                "## El servidor se detuvo durante la generación (trabajo interrumpido).")
            f.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")


def get_job(jid: str) -> dict:
    with _lock:
        j = _states.get(jid)
    if j:
        return _public(j)
    f = _jobfile(jid)
    if f.exists():
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
            j.setdefault("_lines", [])
            j["_lines"] = _read_log_lines(j)
            return _public(j)
        except Exception:
            raise JobNotFound(jid)
    raise JobNotFound(jid)


def _log_path(job: dict) -> Path:
    try:
        return P.gen_dir(job["pid"], job["gen_id"]) / "job.log"
    except Exception:
        return S.JOBS_DIR / f"{job['jid']}.log"


def _read_log_lines(job: dict) -> list[str]:
    lp = _log_path(job)
    try:
        txt = lp.read_text(encoding="utf-8", errors="replace")
        return txt.splitlines()[-MAX_LOG_LINES:]
    except OSError:
        return list(job.get("_lines") or [])


def _public(j: dict) -> dict:
    lines = j.get("_lines") or []
    return {
        "jid": j["jid"], "pid": j.get("pid"), "gen_id": j.get("gen_id"),
        "state": j.get("state"), "step": j.get("step"),
        "created_utc": j.get("created_utc"), "started_utc": j.get("started_utc"),
        "ended_utc": j.get("ended_utc"),
        "spec_resumen": j.get("spec_resumen"),
        "result": j.get("result"),
        "log_tail": lines[-120:],
        "log_line_count": len(lines),
    }


def _reader(job: dict, proc: subprocess.Popen) -> None:
    lp = _log_path(job)
    lp.parent.mkdir(parents=True, exist_ok=True)
    try:
        fh = lp.open("w", encoding="utf-8")
    except OSError:
        fh = None
    t0 = time.time()
    try:
        for raw in iter(proc.stdout.readline, ""):
            line = raw.rstrip("\r\n")
            job.setdefault("_lines", []).append(line)
            if len(job["_lines"]) > MAX_LOG_LINES:
                del job["_lines"][: len(job["_lines"]) - MAX_LOG_LINES]
            if line.startswith("## "):
                job["step"] = line[3:]
            if fh:
                fh.write(line + "\n")
                fh.flush()
            if job.get("cancel_requested"):
                proc.terminate()
                job["cancel_requested"] = False
        rc = proc.wait(timeout=60)
        elapsed = round(time.time() - t0, 1)
        res = _read_runner_result(job)
        _finish(job, rc, elapsed, res)
    except Exception as e:  # noqa: BLE001
        job["state"] = "error"
        job["ended_utc"] = _utc()
        job["result"] = {"ok": False, "error": f"monitor: {type(e).__name__}: {e}"}
    finally:
        if fh:
            fh.close()
        _persist(job)
        with _lock:
            _proc.pop(job["jid"], None)


def _utc() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _read_runner_result(job: dict) -> dict:
    """Lee el _result.json que el runner escribe junto a la carpeta de salida."""
    try:
        gdir = P.gen_dir(job["pid"], job["gen_id"])
        rp = gdir / "_result.json"
        if rp.exists():
            return json.loads(rp.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _finish(job: dict, rc: int | None, elapsed: float, res: dict | None = None) -> None:
    job["ended_utc"] = _utc()
    job["elapsed_s"] = elapsed
    res = res or {}
    if job.get("cancel_requested") or rc is None:
        job["state"] = "cancelled"
        job["result"] = {"ok": False, "error": "generación cancelada por el usuario"}
    elif rc == 0 and res.get("ok"):
        job["state"] = "done"
        job["result"] = res
        _register_history(job)
    else:
        job["state"] = "error"
        msg = res.get("error") or f"el pipeline terminó con código {rc}"
        result = {"ok": False, "error": msg}
        if res.get("traceback"):
            result["traceback"] = res["traceback"]
        job["result"] = result


def _register_history(job: dict) -> None:
    res = job.get("result") or {}
    prod = (res.get("produccion") or {}) if isinstance(res, dict) else {}
    wav = (res.get("wav") or {}) if isinstance(res, dict) else {}
    entry = {
        "gen_id": job.get("gen_id"),
        "fecha_utc": job.get("ended_utc"),
        "perfil": prod.get("perfil") or job.get("spec_resumen", {}).get("production"),
        "seed": prod.get("seed"),
        "sha256_midi": prod.get("sha256"),
        "duracion_s": prod.get("duracion_s"),
        "bpm": prod.get("bpm"),
        "compases": prod.get("compases"),
        "compliance_fails": prod.get("compliance_fails"),
        "compliance_warns": prod.get("compliance_warns"),
        "harmonia": prod.get("harmonia"),
        "out_name": job.get("spec_resumen", {}).get("out_name"),
        "wav": ({"ok": True, "sha256": wav.get("sha256")} if wav.get("ok")
                else ({"ok": False, "error": wav.get("error")} if wav else None)),
        "elapsed_s": job.get("elapsed_s"),
        "carpeta": f"generations/{job.get('gen_id')}",
    }
    try:
        P.append_history(job["pid"], entry)
    except Exception:
        pass


def start_job(pid: str, spec: dict) -> dict:
    """spec: {production, seed, harmony, wav, out_name, doc, validate_first...}"""
    with _lock:
        for j in _states.values():
            if j.get("state") in ("running", "queued"):
                raise JobBusy(j["jid"])
    proj = P.get_project(pid)
    if not proj:
        raise FileNotFoundError(pid)

    gen_id = P.next_gen_id(pid)
    out_name = S.slugify(spec.get("out_name") or proj["doc"].get("meta", {}).get("title", "")
                         or proj["name"], fallback=gen_id)
    gdir = P.gen_dir(pid, gen_id)
    out_dir = gdir / out_name
    out_dir.mkdir(parents=True, exist_ok=True)

    s = S.load_settings()
    run_spec = {
        "doc": spec.get("doc") if spec.get("doc") is not None else proj["doc"],
        "production": spec.get("production") or proj.get("production", {}).get("profile", "full"),
        "seed": spec.get("seed") if spec.get("seed") is not None else proj.get("production", {}).get("seed"),
        "harmony": spec.get("harmony") if spec.get("harmony") is not None else proj.get("production", {}).get("harmony"),
        "wav": bool(spec.get("wav", proj.get("production", {}).get("render_wav", False))),
        "soundfont": s.get("soundfont_path", ""),
        "indice": False,
        "out_dir": str(out_dir),
    }
    spec_file = gdir / "job_spec.json"
    spec_file.write_text(json.dumps(run_spec, ensure_ascii=False, indent=2), encoding="utf-8")

    jid = f"j_{time.strftime('%Y%m%d_%H%M%S')}_{P.fresh_id()}"
    job = {
        "jid": jid, "pid": pid, "gen_id": gen_id,
        "state": "running", "step": "Preparando entorno",
        "created_utc": _utc(), "started_utc": _utc(),
        "spec_resumen": {"production": run_spec["production"], "seed": run_spec["seed"],
                         "harmony": run_spec["harmony"], "wav": run_spec["wav"],
                         "out_name": out_name},
        "spec_file": str(spec_file), "_lines": [],
    }
    with _lock:
        _states[jid] = job
    _persist(job)

    env = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "studio.runner", "--spec", str(spec_file)],
            cwd=str(S.ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", env=env)
    except Exception as e:
        job["state"] = "error"
        job["ended_utc"] = _utc()
        job["result"] = {"ok": False, "error": f"no se pudo lanzar el pipeline: {e}"}
        _persist(job)
        raise
    with _lock:
        _proc[jid] = proc

    th = threading.Thread(target=_reader, args=(job, proc), daemon=True)
    th.start()

    # Vigilante de timeout duro
    def _watch():
        th.join(HARD_TIMEOUT_S)
        with _lock:
            alive = _states.get(jid, {}).get("state") == "running"
            p = _proc.get(jid)
        if alive:
            try:
                if p:
                    p.kill()
            except Exception:
                pass
            job["state"] = "error"
            job["result"] = {"ok": False, "error": f"timeout duro de {HARD_TIMEOUT_S}s"}
            job["ended_utc"] = _utc()
            _persist(job)
    threading.Thread(target=_watch, daemon=True).start()
    return _public(job)


def cancel_job(jid: str) -> dict:
    with _lock:
        job = _states.get(jid)
        proc = _proc.get(jid)
        if not job:
            raise JobNotFound(jid)
        if job["state"] not in ("running", "queued"):
            return _public(job)
        job["cancel_requested"] = True
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
    job["state"] = "cancelled"
    job["ended_utc"] = _utc()
    job["result"] = {"ok": False, "error": "generación cancelada por el usuario"}
    _persist(job)
    return _public(job)


def list_jobs(pid: str | None = None, limit: int = 30) -> list[dict]:
    out = []
    if S.JOBS_DIR.exists():
        for f in sorted(S.JOBS_DIR.glob("*.json"), reverse=True)[:limit]:
            try:
                j = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if pid and j.get("pid") != pid:
                continue
            j.setdefault("_lines", [])
            out.append(_public(j))
    return out
