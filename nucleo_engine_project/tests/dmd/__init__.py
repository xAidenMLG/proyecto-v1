"""Suite de pruebas de contrato de Dark Music Director (Fase 0 + Fase 1).

Ejecución (solo librería estándar, convención del proyecto MIDI Forge):
    python -m unittest discover -s tests -t . -v

Alcance Fase 0 (instrucción de Fase 0, puntos E/F/G):
  - 9 tests de frontera de density de la rev. 3.2 + cobertura de [0.0, 1.0]
  - fórmula de coexistencia §2.6.5 (propiedades contractuales)
  - códigos E/W (40 activos, retiro E201/E202)
  - preservación de x_* (meta.director)
  - completitud de recetas (mecanismo fail-fast; estado Fase 0 documentado)
  - inicialización de instrumentos adicionales (dato §2.5.1 + decisión de seguridad)
  - enlace a forge/ sin modificarlo (capacidades citadas por contrato/auditoría)

Alcance Fase 1 (instrucción 09):
  - receta N1 real de dark_triphop (completitud, D_receta real, fórmula con
    defaults reales — obligación de §2.6.5)
  - validador E1xx/E2xx/E3xx + W4xx (rev. 3.2)
  - compilador mínimo: traducción de los 7 tipos de sección, meta.director,
    precedencia §2.3, ending, guardrails §2.11
  - golden test determinista de principio a fin (JSON → proyecto → MIDI
    reproducible)

NOTA DE ENTORNO (instrucción 09.2): los tests viven FUERA del proyecto MIDI
Forge, así que activan explícitamente el modo auditoría para usar la copia
auditada del sandbox. En producción (dark_director/ copiado junto a forge/)
eso no hace falta y la ruta de auditoría es inalcanzable.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("DARK_DIRECTOR_AUDIT_MODE", "1")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
