"""Punto de entrada: ``python -m composer`` → http://127.0.0.1:8898"""
from __future__ import annotations

import sys

import uvicorn

from . import __version__

HOST = "127.0.0.1"
DEFAULT_PORT = 8898


def main() -> int:
    port = DEFAULT_PORT
    if "--port" in sys.argv:
        try:
            port = int(sys.argv[sys.argv.index("--port") + 1])
        except (ValueError, IndexError):
            pass
    print(f"DMD COMPOSER {__version__} → http://{HOST}:{port}", flush=True)
    uvicorn.run("composer.server:app", host=HOST, port=port,
                log_level="warning", workers=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
