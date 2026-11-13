"""album — ALBUM PRODUCTION SYSTEM (FASE 8).

Capa de planificación, orquestación, control de diversidad, validación y
reproducibilidad para producir álbumes completos con el pipeline existente:

    album.json (side-file dmd-album/1)
        → planificador   (plan por pista: perfil, seed, armonía, digest de docs)
        → orquestador    (produce cada pista REUTILIZANDO scripts/produce.py)
        → diversidad     (métricas técnicas de variedad/duplicados/coherencia)
        → informe        (informe_album.json/.md + manifiesto reproducible)

Principios (misión FASE 8):
  - El álbum ORGANIZA composiciones individuales; NO compone (los docs los
    escribe el compositor; aquí solo se validan y se ejecutan).
  - Reutiliza los motores existentes: dark_director.compilador + jazz_engine
    (mismo núcleo que scripts/produce.py). No hay segundo motor ni segundo
    sistema de configuración: la config por pista es el side-config estándar.
  - La biblioteca de familiaridad armónica es OPCIONAL y EXPLÍCITA por pista
    (keyword/ID); nunca se activa sola y jamás en el camino ORIGINAL.
  - Determinista: mismo album.json → mismo plan → mismos MIDIs byte a byte.

CLI:
    python3 -m album plan     <album.json> --out DIR
    python3 -m album producir <album.json> --out DIR [--regen IDS] [--solo IDS]
                              [--forzar] [--sin-informe]
    python3 -m album informe  <DIR>
    python3 -m album estado   <DIR>

Este paquete DEPENDE de dark_director y jazz_engine; jamás al revés.
No toca forge/, styles.py, dark_triphop.py, contract.py ni los goldens.
"""
from .esquema import (SCHEMA_ALBUM, SCHEMA_PLAN, SCHEMA_INFORME,
                      validar_album, AlbumInvalido, cargar_album)

__version__ = "8.0.0"

__all__ = ["SCHEMA_ALBUM", "SCHEMA_PLAN", "SCHEMA_INFORME", "validar_album",
           "AlbumInvalido", "cargar_album", "__version__"]
