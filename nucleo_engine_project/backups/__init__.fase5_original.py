"""jazz_engine — motores musicales especializados del universo DARK TRIP HOP.

FASE 5 — Dark Trip Hop Unification & Musical Engine Expansion.

Componentes:
  context      Context Analyzer (armonía/drama por sección, reutiliza forge.theory)
  profiles     Perfiles de identidad (dark_triphop ACTIVO; doom_* archivados)
  motif        Motif Generator + Motif Development (mecanismo genérico)
  improv       Phrase Generator/Scheduler (sax) + Rhodes Engine (behaviors A-E)
  drums_engine Groove de batería (microvariación, transiciones, ruptura)
  vibes_engine Vibráfono contextual (params + ecos motivicos)
  coordinator  Coordinador instrumental (protagonismo, densidad, espacios)
  enhance      Enriquecimiento puro del proyecto compilado (sax/drums/vibes)
  render       Orquestación con hooks de buffer (Rhodes/vibes) sobre forge

Propiedades:
  - Sin dependencias externas (stdlib + forge); NO importa dark_director.
  - Determinista: misma (proyecto, config) → mismo MIDI byte a byte.
  - Apagable: ``render.generate(project, None)`` == forge.engine.generate.
  - El contrato dark-director/1 rev 3.2 no se toca; el material se inyecta en
    vocabulario NATIVO midi-forge/1 (lead.phrases, params de bloques).
"""

__version__ = "5.0.0"

from . import (coordinator, context, drums_engine, improv, motif,  # noqa: F401
               profiles, render, vibes_engine)
from . import enhance as _enhance_mod  # noqa: F401
from .profiles import ACTIVE_IDENTITY, ARCHIVED_IDENTITIES  # noqa: F401


def generate(project, config=None):
    """Atajo del pipeline mejorado (ver render.generate)."""
    return render.generate(project, config)


def enhance(project, config=None):
    """Atajo del enriquecimiento puro (ver enhance.enhance)."""
    return _enhance_mod.enhance(project, config)
