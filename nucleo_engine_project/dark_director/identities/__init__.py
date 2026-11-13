"""Carga y registro de recetas N1 (``dark_director/identities/<id>.py``).

El registro usa el fail-fast de ``dark_director.recetas`` (§2.6.5): una tabla
D_receta incompleta o fuera de rango detiene la carga al importar (fallo
interno de receta, nunca un código E/W del contrato).

ESTADO FASE 2 (RESPUESTA 09, Fase B/C): las TRES identidades del contrato
tienen receta real registrada:
  - ``dark_triphop`` (Fase 1, instrucción 09; receta congelada, intacta);
  - ``doom_triphop``  (Fase 2; tabla declarativa BLOQUES + AUTOMACION);
  - ``doom_dark_jazz``(Fase 2; tabla declarativa BLOQUES + AUTOMACION).
Además del fail-fast de D_receta, las recetas con tabla BLOQUES se verifican
con ``recetas.verificar_tabla_bloques`` (delta C5 de RESPUESTA 09 §6.3): una
receta incoherente (filas incompletas, estilos inexistentes, tipos inválidos)
NO se registra y la carga se detiene.
"""

from .. import recetas
from . import dark_triphop        # noqa: F401  (receta N1 real, congelada)
from . import doom_triphop        # noqa: F401  (receta N1 real, Fase 2)
from . import doom_dark_jazz      # noqa: F401  (receta N1 real, Fase 2)

__all__ = ["dark_triphop", "doom_triphop", "doom_dark_jazz",
           "RECETA_DARK_TRIPHOP", "RECETA_DOOM_TRIPHOP", "RECETA_DOOM_DARK_JAZZ"]


def _tabla_receta(mod):
    """Extrae la tabla D_receta de un módulo de receta para el registro fail-fast."""
    return dict(mod.D_RECETA)


# Registro fail-fast: si alguna tabla D_receta faltara o estuviera fuera de
# rango, ESTE import lanza RecetaError y la compilación nunca comienza.
RECETA_DARK_TRIPHOP = recetas.registrar_receta(dark_triphop.IDENTITY,
                                               _tabla_receta(dark_triphop))
RECETA_DOOM_TRIPHOP = recetas.registrar_receta(doom_triphop.IDENTITY,
                                               _tabla_receta(doom_triphop))
RECETA_DOOM_DARK_JAZZ = recetas.registrar_receta(doom_dark_jazz.IDENTITY,
                                                 _tabla_receta(doom_dark_jazz))

# Delta C5 (RESPUESTA 09 §6.3): coherencia estructural de las tablas BLOQUES.
# dark_triphop no declara tabla (consumidor de ramas por rol) → sin obligación.
for _mod in (dark_triphop, doom_triphop, doom_dark_jazz):
    _problemas = recetas.verificar_tabla_bloques(_mod)
    if _problemas:
        raise recetas.RecetaError(
            f"receta '{_mod.IDENTITY}' incoherente (C5): " + "; ".join(_problemas))

#: identidades con receta real registrada (las 3 del contrato)
CON_RECETA = (dark_triphop.IDENTITY, doom_triphop.IDENTITY, doom_dark_jazz.IDENTITY)
#: identidades previstas por el contrato que aún no tienen receta (ninguna)
SIN_RECETA = tuple(i for i in recetas.IDENTITIES if i not in CON_RECETA)

# ---------------------------------------------------------------------------
# FASE 5 — UNIFICACIÓN: una sola identidad MUSICAL activa.
#
# Decisión del usuario (FASE 5 §0/§11): el proyecto se especializa en
# ``dark_triphop``. Las identidades doom quedan ARCHIVADAS, no destruidas:
#   - sus recetas siguen registradas (compatibilidad total con documentos
#     anteriores; el contrato rev. 3.2 NO cambia);
#   - sus perfiles de improvisación siguen disponibles en jazz_engine.profiles
#     para reproducibilidad histórica;
#   - NO aparecen como identidad recomendada ni predeterminada (los ejemplos
#     nuevos y la documentación usan dark_triphop).
# ---------------------------------------------------------------------------
IDENTIDAD_ACTIVA = "dark_triphop"
IDENTIDADES_ARCHIVADAS = ("doom_triphop", "doom_dark_jazz")


def estado_identidad(identity):
    """'activa' | 'archivada' | 'fuera' (fuera del contrato)."""
    if identity == IDENTIDAD_ACTIVA:
        return "activa"
    if identity in IDENTIDADES_ARCHIVADAS:
        return "archivada"
    return "fuera"


def es_activa(identity):
    return estado_identidad(identity) == "activa"
