"""Disciplina de trabajos en segundo plano (espejo de studio/jobs.py, en hilos).

* Un SOLO trabajo activo por ámbito (scope): una segunda petición para el
  mismo ámbito recibe JobBusy → el API responde 409 (nada de producciones
  solapadas sobre la misma generación).
* Estado persistido en disco (``jobs/<jid>.json``, escritura atómica vía
  store.atomic_write_json): si el servidor se cierra a mitad, al arrancar
  el trabajo se marca "interrumpido" (honestidad de estado, misión §11).
* Trabajadores en hilos (ThreadPoolExecutor, max_workers=2): sin fork ni
  señales → seguro en Windows. El trabajador puede registrar un proceso
  externo (BridgeProcess del puente) para que cancel()/timeout lo maten de
  forma determinista con su ``.cancel()`` (mata el árbol de procesos).
* Contrato del trabajador: ``worker(ctx)`` con
  ctx = {"jid", "cancel_event": threading.Event, "log": fn(str),
         "progress": fn(dict) (se fusiona en job["result"] en vivo),
         "register_process": fn(proc)}.
  Si devuelve dict → estado "ok" (o "cancelado" si devolvió
  {"ok": False, "cancelado": True}); si lanza excepción → estado "error".
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import store

#: Carpeta de trabajos (raíz del repositorio de Composer).
ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = ROOT / "jobs"

#: Estados posibles de un trabajo (español, como el resto de la UI).
STATES = ("queued", "running", "ok", "error", "cancelado", "timeout", "interrumpido")
ACTIVE_STATES = ("queued", "running")

MAX_LOG_LINES = 400          # tope de líneas de log por trabajo
MAX_JOBS_IN_MEMORY = 500     # poda del caché en memoria (el disco manda)

_JID_RE = re.compile(r"^[a-z][a-z0-9-]{3,63}$")
_KIND_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

_lock = threading.Lock()
_init_lock = threading.Lock()
_jobs: Dict[str, dict] = {}          # jid → job (incluye claves "_" transitorias)
_procs: Dict[str, Any] = {}          # jid → proceso registrado (con .cancel())
_executor: Optional[ThreadPoolExecutor] = None


class JobBusy(Exception):
    """Ya hay un trabajo activo para el mismo ámbito."""


class JobNotFound(Exception):
    """El jid pedido no existe (ni en memoria ni en disco)."""


# ------------------------------------------------------------- utilidades
def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _valid_jid(jid: str) -> str:
    if not _JID_RE.fullmatch(jid or ""):
        raise ValueError("jid no válido")
    return jid


def _jobfile(jid: str) -> Path:
    return JOBS_DIR / f"{_valid_jid(jid)}.json"


def _load_job_file(f: Path) -> Optional[dict]:
    try:
        j = json.loads(f.read_text(encoding="utf-8"))
        return j if isinstance(j, dict) and j.get("jid") else None
    except Exception:
        return None


def _persist(job: dict) -> None:
    """Escritura atómica del estado (sin claves transitorias "_…")."""
    try:
        data = {k: v for k, v in job.items() if not k.startswith("_")}
        store.atomic_write_json(_jobfile(job["jid"]), data)
    except (OSError, ValueError):
        pass  # el disco no puede derribar al servidor por un log


def _append_log(job: dict, line: str) -> None:
    log = job.setdefault("log", [])
    log.append(f"[{_utc()}] {line}")
    del log[:-MAX_LOG_LINES]
    _persist(job)


def _public(job: dict, tail: Optional[int] = None) -> dict:
    log = list(job.get("log") or [])
    out = {k: job.get(k) for k in
           ("jid", "kind", "scope", "state", "created_utc", "started_utc",
            "finished_utc", "timeout", "result", "error")}
    out["log"] = log if tail is None else log[-tail:]
    out["log_line_count"] = len(log)
    return out


# ------------------------------------------------------------- finalización
def _finish(job: dict, state: str, *, error: Optional[str] = None,
            result: Any = None) -> None:
    with _lock:
        if job.get("state") not in ACTIVE_STATES:
            return  # ya terminó (carrera con el temporizador/cancelación)
        job["state"] = state
        job["finished_utc"] = _utc()
        if error is not None:
            job["error"] = error
        if result is not None:
            job["result"] = result
        job.pop("_cancel_requested", None)
        proc = _procs.pop(job["jid"], None)
        # limpieza del temporal del puente (spec/out JSON del hijo cancelable)
        if proc is not None and hasattr(proc, "cleanup"):
            try:
                proc.cleanup()
            except Exception:  # noqa: BLE001
                pass
        # poda del caché en memoria (el disco conserva el historial)
        finished = [j for j in _jobs.values()
                    if j.get("state") not in ACTIVE_STATES]
        if len(finished) > MAX_JOBS_IN_MEMORY:
            finished.sort(key=lambda j: j.get("finished_utc") or "")
            for old in finished[:len(finished) - MAX_JOBS_IN_MEMORY]:
                _jobs.pop(old["jid"], None)
    _persist(job)


def _execute(job: dict, worker: Callable[[dict], Any]) -> None:
    """Cuerpo del trabajador: corre en un hilo del executor."""
    jid = job["jid"]
    ev: threading.Event = job["_event"]
    with _lock:
        job["state"] = "running"
        job["started_utc"] = _utc()
    _persist(job)
    _append_log(job, "trabajo en ejecución")

    def log(msg: str) -> None:
        _append_log(job, str(msg))

    def progress(part: dict) -> None:
        if isinstance(part, dict):
            with _lock:
                res = job.get("result") if isinstance(job.get("result"), dict) else {}
                res.update(part)
                job["result"] = res
        _persist(job)

    def register_process(proc: Any) -> None:
        with _lock:
            _procs[jid] = proc
        _append_log(job, "proceso externo registrado (cancelable)")

    ctx = {"jid": jid, "kind": job["kind"], "scope": job["scope"],
           "cancel_event": ev, "log": log, "progress": progress,
           "register_process": register_process}
    try:
        res = worker(ctx)
    except Exception as e:  # noqa: BLE001 — el fallo del trabajador es el resultado
        with _lock:
            timed_out = bool(job.get("_timed_out"))
            cancelled = bool(job.get("_cancel_requested"))
        if timed_out:
            _finish(job, "timeout", error=f"timeout duro de {job['timeout']}s")
        elif cancelled:
            _finish(job, "cancelado", error="trabajo cancelado por el usuario")
        else:
            detail = str(e) or type(e).__name__
            _finish(job, "error", error=detail,
                    result={"ok": False, "error": detail,
                            "log_tail": list(job.get("log") or [])[-30:]})
        return
    with _lock:
        timed_out = bool(job.get("_timed_out"))
        cancelled = bool(job.get("_cancel_requested"))
    if timed_out:
        _finish(job, "timeout", error=f"timeout duro de {job['timeout']}s")
    elif cancelled or (isinstance(res, dict) and res.get("cancelado")):
        _finish(job, "cancelado", error="trabajo cancelado por el usuario",
                result=res if isinstance(res, dict) else None)
    else:
        _finish(job, "ok", result=res if isinstance(res, dict) else {"ok": True})


def _arm_timer(job: dict) -> None:
    """Timeout duro: cancela el proceso registrado y marca el trabajo."""
    def _fire() -> None:
        with _lock:
            if job.get("state") not in ACTIVE_STATES:
                return
            job["_timed_out"] = True
            proc = _procs.get(job["jid"])
        job["_event"].set()
        _append_log(job, f"timeout duro de {job['timeout']}s: se cancela el trabajo")
        if proc is not None:
            try:
                proc.cancel()
            except Exception:
                pass
    t = threading.Timer(job["timeout"], _fire)
    t.daemon = True
    t.start()


def _executor_submit(job: dict, worker: Callable[[dict], Any]) -> None:
    global _executor
    with _init_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=2,
                                           thread_name_prefix="composer-job")
    _executor.submit(_execute, job, worker)


# ------------------------------------------------------------- API pública
def submit(kind: str, scope: str, worker: Callable[[dict], Any],
           timeout: float = 300) -> dict:
    """Crea un trabajo en cola y lo lanza. UNO activo por scope (JobBusy)."""
    kind = str(kind or "").strip().lower()
    if not _KIND_RE.fullmatch(kind):
        raise ValueError("kind de trabajo no válido (minúsculas, sin espacios)")
    if not scope or len(scope) > 120:
        raise ValueError("scope de trabajo no válido")
    jid = f"{kind}-{int(time.time() * 1000):x}-{os.urandom(2).hex()}"
    if not _JID_RE.fullmatch(jid):
        raise ValueError("jid generado no válido")
    with _lock:
        # un solo trabajo activo por ámbito: memoria + disco (bajo el mismo Lock)
        for j in _jobs.values():
            if j.get("scope") == scope and j.get("state") in ACTIVE_STATES:
                raise JobBusy(j["jid"])
        if JOBS_DIR.exists():
            for f in JOBS_DIR.glob("*.json"):
                jd = _load_job_file(f)
                if jd and jd.get("scope") == scope and jd.get("state") in ACTIVE_STATES:
                    raise JobBusy(jd["jid"])
        job: dict = {
            "jid": jid, "kind": kind, "scope": scope, "state": "queued",
            "created_utc": _utc(), "started_utc": None, "finished_utc": None,
            "timeout": timeout, "result": None, "error": None, "log": [],
            # transitorias (nunca se persisten)
            "_event": threading.Event(), "_timed_out": False,
            "_cancel_requested": False,
        }
        _jobs[jid] = job
    _persist(job)
    _arm_timer(job)
    _executor_submit(job, worker)
    return _public(job)


def get(jid: str) -> dict:
    jid = _valid_jid(jid)
    with _lock:
        job = _jobs.get(jid)
    if job:
        return _public(job)
    f = _jobfile(jid)
    if f.exists():
        j = _load_job_file(f)
        if j:
            return _public(j)
    raise JobNotFound(jid)


def list_jobs(limit: int = 50) -> List[dict]:
    """Trabajos recientes, el más nuevo primero (memoria + disco)."""
    try:
        limit = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        limit = 50
    seen: Dict[str, dict] = {}
    with _lock:
        for j in _jobs.values():
            seen[j["jid"]] = j
    if JOBS_DIR.exists():
        for f in JOBS_DIR.glob("*.json"):
            if f.stem in seen:
                continue
            j = _load_job_file(f)
            if j:
                seen[j["jid"]] = j
    rows = sorted(seen.values(),
                  key=lambda j: j.get("created_utc") or "", reverse=True)
    return [_public(j, tail=30) for j in rows[:limit]]


def find_by_scope(scope: str, only_active: bool = False) -> Optional[dict]:
    """Trabajo más reciente de un ámbito (para el estado por generación)."""
    rows = [j for j in list_jobs(200)
            if j.get("scope") == scope and (not only_active or j.get("state") in ACTIVE_STATES)]
    return rows[0] if rows else None


def cancel(jid: str) -> bool:
    """Pide cancelación: marca el evento y mata el proceso registrado.

    Devuelve False si el trabajo no existe o ya no está activo.
    """
    jid = _valid_jid(jid)
    with _lock:
        job = _jobs.get(jid)
        if job is None:
            f = _jobfile(jid)
            if f.exists():
                job = _load_job_file(f)
                if job:
                    job.setdefault("_event", threading.Event())
                    _jobs[jid] = job
        if not job or job.get("state") not in ACTIVE_STATES:
            return False
        job["_cancel_requested"] = True
        proc = _procs.get(jid)
    job["_event"].set()
    _append_log(job, "cancelación solicitada por el usuario")
    if proc is not None:
        try:
            proc.cancel()
        except Exception:
            pass
    return True


def recover_interrupted() -> int:
    """Al arrancar: todo trabajo queued/running persistido → interrumpido."""
    n = 0
    if not JOBS_DIR.exists():
        return n
    for f in JOBS_DIR.glob("*.json"):
        j = _load_job_file(f)
        if not j or j.get("state") not in ACTIVE_STATES:
            continue
        j["state"] = "interrumpido"
        j["finished_utc"] = _utc()
        j["error"] = "el servidor se reinició durante el trabajo"
        log = j.setdefault("log", [])
        log.append("## el servidor se reinició durante el trabajo (interrumpido)")
        del log[:-MAX_LOG_LINES]
        _persist(j)
        n += 1
    return n
