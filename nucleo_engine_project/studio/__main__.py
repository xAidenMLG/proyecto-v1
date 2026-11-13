"""Arranque del servidor local: ``python -m studio`` (solo 127.0.0.1)."""
from __future__ import annotations

import argparse
import webbrowser

from . import settings as S


def main() -> None:
    ap = argparse.ArgumentParser(prog="dmd-studio")
    ap.add_argument("--port", type=int, default=None,
                    help="puerto local (default: settings, 8899)")
    ap.add_argument("--no-browser", action="store_true",
                    help="no abrir el navegador automáticamente")
    args = ap.parse_args()

    import uvicorn
    from . import jobs, server

    S.ensure_dirs()
    jobs.recover_interrupted()

    s = S.load_settings()
    port = args.port or int(s.get("port") or 8899)
    url = f"http://127.0.0.1:{port}"
    print(f"DMD STUDIO {server.__version__} — {url}")
    print("Servidor local (solo 127.0.0.1). Ctrl+C para detener.")
    if not args.no_browser:
        threading_delay_open(url)
    uvicorn.run(server.app, host="127.0.0.1", port=port, log_level="warning")


def threading_delay_open(url: str) -> None:
    import threading, time

    def _open():
        time.sleep(1.2)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()


if __name__ == "__main__":
    main()
