"""Dark Music Director — capa de intención compositiva sobre MIDI Forge.

Contrato: ``dark-director/1`` rev. 3.2 (fuente de verdad: chain documental
rev. 3 + rev. 3.1 + rev. 3.2 en ``download/``).

FASE 1 (estado actual): compilador mínimo dark-director/1 → midi-forge/1.
  - Receta N1 real de ``dark_triphop`` (``identities/dark_triphop.py``);
  - validador E1xx/E2xx/E3xx + W4xx del contrato (``validador.py``);
  - perfil de accesibilidad N2 (``accesibilidad.py``);
  - compilador mínimo (``compilador.py``): expande la escalera §2.3 y emite un
    proyecto ``midi-forge/1`` con ``meta.director``, listo para el motor.

Reglas que este paquete sigue cumpliendo por diseño:
  - No modifica ``forge/`` ni ``styles.py``: la importación del motor es
    perezosa, con protección de ``.pyc`` DE ÁMBITO (``forge_link.sin_bytecode``)
    que restaura el estado del intérprete al salir (instrucción 09.1).
  - La copia auditada del sandbox solo se usa con ``DARK_DIRECTOR_AUDIT_MODE=1``
    (herramienta de auditoría/QA; nunca dependencia de producción — 09.2).
  - No implementa capacidades nuevas del motor ni modifica el contrato.
"""
import sys

CONTRACT_ID = "dark-director/1"
CONTRACT_REV = "3.2"
TARGET_SCHEMA = "midi-forge/1"
COMPILER_VERSION = "0.1.0"
COMPILER_STAGE = "fase1"

from . import accesibilidad, compilador, contract, forge_link, inicializacion, recetas, validador  # noqa: E402,F401
from . import identities  # noqa: E402,F401  (registra la receta N1 real de dark_triphop)

__all__ = ["CONTRACT_ID", "CONTRACT_REV", "TARGET_SCHEMA", "COMPILER_VERSION",
           "COMPILER_STAGE", "accesibilidad", "compilador", "contract", "forge_link",
           "inicializacion", "recetas", "validador", "identities"]
