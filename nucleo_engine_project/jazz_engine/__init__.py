"""jazz_engine — motores musicales especializados del universo DARK TRIP HOP.

FASE 5 — Dark Trip Hop Unification & Musical Engine Expansion.
FASE 6 — Production Profiles & Musical Generalization.
FASE 7 — Harmonic Familiarity Engine (biblioteca de progresiones + selección
         + adaptación; activación por keyword/ID vía side-file o CLI).

Componentes:
  context      Context Analyzer (armonía/drama por sección, reutiliza forge.theory)
  profiles     Perfiles de identidad (dark_triphop ACTIVO; doom_* archivados)
  production   Perfiles de PRODUCCIÓN (presets reproducibles de los motores)
  motif        Motif Generator + Motif Development (mecanismo genérico)
  improv       Phrase Generator/Scheduler (sax) + Rhodes Engine (behaviors A-E)
  drums_engine Groove de batería (microvariación, transiciones, ruptura)
  vibes_engine Vibráfono contextual (params + ecos motivicos)
  coordinator  Coordinador instrumental (protagonismo, densidad, espacios)
  enhance      Enriquecimiento puro del proyecto compilado (sax/drums/vibes)
  render       Orquestación con hooks de buffer (Rhodes/vibes) sobre forge
  harmony_library Biblioteca de progresiones familiares (grados funcionales)
  harmony_select  Motor de búsqueda/selección (keyword→progresión por tipo)
  harmony_adapt   Motor de adaptación (tonalidad/modo/variaciones controladas)
  harmony      Etapa de integración (reescribe sections[].chords pre-enhance)

Propiedades:
  - Sin dependencias externas (stdlib + forge); NO importa dark_director.
  - Determinista: misma (proyecto, config) → mismo MIDI byte a byte.
  - Apagable: ``render.generate(project, None)`` == forge.engine.generate.
  - El contrato dark-director/1 rev 3.2 no se toca; el material se inyecta en
    vocabulario NATIVO midi-forge/1 (lead.phrases, params de bloques, chords).
  - FASE 7: sin la clave 'harmony' en la config, TODO el pipeline es byte a
    byte el de FASE 6 (los ocho dorados y los 7 perfiles siguen intactos).
"""

__version__ = "7.0.0"

from . import (coordinator, context, drums_engine, harmony, harmony_adapt,     # noqa: F401
               harmony_library, harmony_select, improv, motif,
               production, profiles, render, vibes_engine)
from . import enhance as _enhance_mod  # noqa: F401
from .profiles import ACTIVE_IDENTITY, ARCHIVED_IDENTITIES  # noqa: F401
from .production import PRODUCTION_PROFILES  # noqa: F401


def generate(project, config=None):
    """Atajo del pipeline mejorado (ver render.generate)."""
    return render.generate(project, config)


def enhance(project, config=None):
    """Atajo del enriquecimiento puro (ver enhance.enhance)."""
    return _enhance_mod.enhance(project, config)
