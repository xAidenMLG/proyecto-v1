"""Gestión del puente con el DMD REAL: descubrimiento, manifiesto, llamadas.

Composer NUNCA importa DMD en su propio proceso (aislamiento total, mismo
patrón que studio.runner): todo va por subprocess con un spec JSON validado
y timeouts. El manifiesto de capacidades se cachea en
``composer_data/dmd_manifest.json`` con fingerprint; si el DMD cambia, se
detecta la discrepancia y la UI lo muestra (misión §10).

Produce (misión de integración): ``produce``/``produce_start`` ejecutan el
núcleo REAL (scripts/produce.py::producir_cancion) en un hijo aislado con un
``BridgeProcess`` cancelable (poll/cancel/timeout; taskkill /T en Windows,
killpg en POSIX). El MIDI sigue siendo del pipeline único de DMD.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from . import __version__

RUNNER = Path(__file__).resolve().parent / "dmd_bridge_runner.py"

#: Tamaño máximo de spec (protección de entrada, misión §11).
MAX_SPEC_BYTES = 8 * 1024 * 1024      # 8 MB
TIMEOUTS = {"introspect": 60, "validate": 60, "compile_preview": 120,
            "parse_chords": 60, "produce": 300}

_IS_WIN = (os.name == "nt")


def _child_env() -> dict:
    """Entorno del hijo: UTF-8 explícito (Windows cp1252 sería letal para
    JSON con acentos — fix P0 absorbido del roadmap §9)."""
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


class BridgeProcess:
    """Proceso hijo del puente CANCELABLE (produce/lote pueden durar minutos).

    Windows: CREATE_NEW_PROCESS_GROUP + taskkill /F /T (árbol completo).
    POSIX: sesión propia (start_new_session) + killpg. Sin shell del sistema
    (argv fijo).
    El resultado viaja por el archivo ``--out`` (JSON); stderr queda en una
    tubería para diagnóstico.
    """

    def __init__(self, argv: list, out_file: Path,
                 tmp_dir: Optional[tempfile.TemporaryDirectory] = None,
                 timeout: Optional[float] = None, cwd: Optional[str] = None):
        self.out_file = Path(out_file)
        self._tmp = tmp_dir
        self.timeout = timeout
        self.cancelled = False
        kwargs: Dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.PIPE,
            "shell": False,
            "env": _child_env(),
        }
        if cwd:
            kwargs["cwd"] = cwd
        if _IS_WIN:
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        self.proc = subprocess.Popen(argv, **kwargs)
        self._started = time.time()

    def alive(self) -> bool:
        return self.proc.poll() is None

    def stderr_tail(self, limit: int = 800) -> str:
        try:
            raw = self.proc.stderr.read() if self.proc.stderr else b""
            return (raw.decode("utf-8", errors="replace") or "").strip()[-limit:]
        except Exception:  # noqa: BLE001
            return ""

    def result(self, timeout: float = 0.0) -> Optional[Dict[str, Any]]:
        """Dict del hijo si ya terminó (y el JSON existe); None si sigue vivo.
        Nunca lanza por JSON ilegible: devuelve un estado de error claro."""
        if self.alive():
            if timeout and (time.time() - self._started) > timeout:
                return {"ok": False, "error": f"timeout ({int(timeout)}s) del proceso del puente"}
            return None
        try:
            self.proc.stderr.close()
        except Exception:  # noqa: BLE001
            pass
        if not self.out_file.exists():
            return {"ok": False,
                    "error": f"el puente no produjo resultado (rc={self.proc.returncode}): "
                             f"{self.stderr_tail()}"}
        try:
            return json.loads(self.out_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return {"ok": False, "error": f"salida ilegible del puente: {e}"}

    def wait(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Bloquea hasta resultado/timeout. En timeout NO mata el proceso:
        el llamador decide (cancel())."""
        tmo = timeout or self.timeout or 60
        while True:
            r = self.result(timeout=tmo)
            if r is not None:
                self.cleanup()
                return r
            if (time.time() - self._started) > tmo:
                return {"ok": False, "error": f"timeout ({int(tmo)}s) ejecutando el puente"}
            time.sleep(0.15)

    def cancel(self) -> None:
        """Mata el árbol del proceso (Windows taskkill /T; POSIX killpg)."""
        self.cancelled = True
        if not self.alive():
            return
        pid = self.proc.pid
        try:
            if _IS_WIN:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               shell=False, capture_output=True, timeout=10)
            else:
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
                for _ in range(25):          # ~5 s de gracia
                    if not self.alive():
                        break
                    time.sleep(0.2)
                if self.alive():
                    try:
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
        except Exception:  # noqa: BLE001
            try:
                self.proc.kill()
            except Exception:  # noqa: BLE001
                pass

    def cleanup(self) -> None:
        if self._tmp is not None:
            try:
                self._tmp.cleanup()
            except Exception:  # noqa: BLE001
                pass
            self._tmp = None


def _runner_script() -> str:
    """Ruta del runner dentro del paquete instalado (soporta PyInstaller-like)."""
    return str(RUNNER)


def discover_dmd(config_dir: Path, configured: Optional[str] = None) -> Optional[str]:
    """Descubre el DMD real: ruta configurada → hermanos → cwd.

    No asume rutas absolutas fijas (misión §10): busca ``dark_director/``.
    """
    candidates = []
    if configured:
        candidates.append(Path(configured))
    here = Path(__file__).resolve().parent
    for anc in (here.parent, here.parent.parent, Path.cwd()):
        if not anc or not anc.exists():
            continue
        for sib in sorted(anc.iterdir()):
            if sib.is_dir() and (sib / "dark_director" / "contract.py").is_file():
                candidates.append(sib)
    for c in candidates:
        try:
            if (c / "dark_director" / "contract.py").is_file():
                return str(c.resolve())
        except OSError:
            continue
    return None


def _run_task(task: str, dmd_path: str, payload: Dict[str, Any],
              timeout: Optional[float] = None) -> Dict[str, Any]:
    """Ejecuta el runner en proceso aislado. Sin shell, argv fijo."""
    if dmd_path and ("\x00" in dmd_path or len(dmd_path) > 400):
        return {"ok": False, "error": "ruta de DMD inválida"}
    spec = {"task": task, "dmd_path": dmd_path, **payload}
    with tempfile.TemporaryDirectory(prefix="dmdc_") as td:
        tdp = Path(td)
        spec_file, out_file = tdp / "spec.json", tdp / "out.json"
        raw = json.dumps(spec, ensure_ascii=False)
        if len(raw.encode("utf-8")) > MAX_SPEC_BYTES:
            return {"ok": False, "error": "spec demasiado grande (límite 8 MB)"}
        spec_file.write_text(raw, encoding="utf-8")
        tmo = timeout or TIMEOUTS.get(task, 60)
        try:
            cp = subprocess.run(
                [sys.executable, _runner_script(), "--spec", str(spec_file),
                 "--out", str(out_file)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=tmo, shell=False, cwd=str(RUNNER.parent), env=_child_env())
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timeout ({tmo}s) ejecutando '{task}' en el DMD"}
        if not out_file.exists():
            err = (cp.stderr or cp.stdout or "sin salida").strip()[-800:]
            return {"ok": False, "error": f"el puente no produjo resultado: {err}"}
        try:
            return json.loads(out_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"salida ilegible del puente: {e}"}


def introspect(dmd_path: str) -> Dict[str, Any]:
    """Manifiesto de capacidades REALES del DMD descubierto."""
    r = _run_task("introspect", dmd_path, {})
    if r.get("ok"):
        r["manifest_meta"] = {
            "dmd_path": dmd_path,
            "captured_at": time.time(),
            "composer_version": __version__,
        }
    return r


def validate_doc(dmd_path: str, doc: dict) -> Dict[str, Any]:
    """Validación con el validador REAL (única fuente de verdad)."""
    return _run_task("validate", dmd_path, {"doc": doc})


def compile_preview(dmd_path: str, doc: dict) -> Dict[str, Any]:
    """Compilación real SIN renderizar (errores, avisos y acordes compilados)."""
    return _run_task("compile_preview", dmd_path, {"doc": doc})


def parse_chords(dmd_path: str, symbols: list) -> Dict[str, Any]:
    """Validación de acordes literales con el parser REAL (forge/theory)."""
    return _run_task("parse_chords", dmd_path, {"simbolos": symbols})


# ------------------------------------------------------------------ produce

def _write_spec(task: str, dmd_path: str, payload: Dict[str, Any],
                spec_file: Path) -> Optional[str]:
    """Escribe el spec JSON. Devuelve un mensaje de error o None."""
    if dmd_path and ("\x00" in dmd_path or len(dmd_path) > 400):
        return "ruta de DMD inválida"
    spec = {"task": task, "dmd_path": dmd_path, **payload}
    raw = json.dumps(spec, ensure_ascii=False)
    if len(raw.encode("utf-8")) > MAX_SPEC_BYTES:
        return "spec demasiado grande (límite 8 MB)"
    spec_file.write_text(raw, encoding="utf-8")
    return None


def produce_start(dmd_path: str, doc: dict, out_dir: str, *,
                  production: str = "full", seed: Optional[int] = None,
                  harmony: Optional[dict] = None, events: bool = False) -> BridgeProcess:
    """Lanza producir_cancion en un hijo AISLADO y devuelve el proceso
    cancelable (jobs.py gobierna el ciclo de vida: poll/cancel/timeout)."""
    tmp = tempfile.TemporaryDirectory(prefix="dmdc_prod_")
    tdp = Path(tmp.name)
    spec_file, out_file = tdp / "spec.json", tdp / "out.json"
    err = _write_spec("produce", dmd_path,
                      {"doc": doc, "out_dir": out_dir, "production": production,
                       "seed": seed, "harmony": harmony, "events": bool(events)},
                      spec_file)
    if err:
        tmp.cleanup()
        raise ValueError(err)
    return BridgeProcess([sys.executable, _runner_script(), "--spec", str(spec_file),
                          "--out", str(out_file)],
                         out_file, tmp_dir=tmp, timeout=TIMEOUTS["produce"])


def produce(dmd_path: str, doc: dict, out_dir: str, *,
            production: str = "full", seed: Optional[int] = None,
            harmony: Optional[dict] = None, events: bool = False,
            timeout: Optional[float] = None) -> Dict[str, Any]:
    """Versión síncrona de produce_start (tests y usos puntuales)."""
    proc = produce_start(dmd_path, doc, out_dir, production=production,
                         seed=seed, harmony=harmony, events=events)
    return proc.wait(timeout or TIMEOUTS["produce"])


# ------------------------------------------------------------------ álbum

def album_start(dmd_path: str, album_json: str, out_dir: str, *,
                regen: Optional[list] = None, solo: Optional[list] = None) -> BridgeProcess:
    """Lanza el ORQUESTADOR EXISTENTE del DMD (``python -m album producir``)
    en un hijo AISLADO y cancelable. Composer no orquesta por su cuenta:
    reanudación, --regen, diversidad e informe son del orquestador real.

    El "resultado" del proceso es el estado.json del orquestador (crash-safe,
    se actualiza tras CADA pista): se pasa como ``out_file`` al BridgeProcess.
    """
    root = Path(dmd_path).resolve()
    if not (root / "album" / "orquestador.py").is_file():
        raise FileNotFoundError(f"el DMD en '{root}' no tiene el paquete album/")
    argv = [sys.executable, "-m", "album", "producir", str(album_json),
            "--out", str(out_dir)]
    if regen:
        argv += ["--regen", ",".join(str(x) for x in regen)]
    if solo:
        argv += ["--solo", ",".join(str(x) for x in solo)]
    tmp = tempfile.TemporaryDirectory(prefix="dmdc_album_")
    tdp = Path(tmp.name)
    out_file = tdp / "estado_copia.json"
    spec_file = tdp / "spec.json"
    spec_file.write_text(json.dumps({"album": album_json, "out": out_dir}), encoding="utf-8")
    return BridgeProcess(argv, out_file, tmp_dir=tmp, timeout=1800, cwd=str(root))
