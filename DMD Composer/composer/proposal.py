"""Propuesta de distribución instrumental del protagonista (v1.1, misión §2.2).

En 1.0 el protagonista solo GARANTIZABA sonido (enabled=true si está fuera
del set base) y validaba conflictos (D-01 del manual). En 1.1 Composer
PROPONE una distribución coherente usando SOLO campos reales del contrato:

  * ``instruments[prot].role``       → "protagonist" (coherencia de la tabla)
  * ``instruments[prot].enabled``    → true si está fuera del set base
                                       (única forma real de que suene)
  * ``instruments[prot].density``    → propuesta SOLO para instrumentos con
                                       traducción real (W410: bass/drums/
                                       pad/strings no la traducen)
  * ``structure[].focus``            → protagonista primero + hasta 2 miembros
                                       del focus_default REAL de la receta
  * ``structure[].active``           → si la sección tiene whitelist y el
                                       protagonista no está, se propone añadirlo
                                       (una whitelist que lo excluye lo silencia)

REGLA DE ORO: la propuesta NUNCA se aplica sola. El usuario la ACEPTA (los
campos quedan escritos y editables en la UI), la MODIFICA después de aplicar,
o la RECHAZA. Las secciones con focus definido por el usuario NO se tocan.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from . import model

#: Instrumentos cuya density NO tiene traducción en el motor (W410 real).
DENSITY_SIN_TRADUCCION = ("bass", "drums", "pad", "strings")

#: Density propuesta para el protagonista (presencia reconocible sin saturar).
#: 0.6 = banda B2 del contrato (rev 3.2 §2.6.5): ni discreta (B1) ni banda B3,
#: donde el guardrail mallet_sparse de la identidad dispara W403 con vibes.
DENSITY_PROPUESTA = 0.6


def _protagonista_efectivo(project: model.ComposerProject,
                           manifest: Optional[dict]) -> Optional[str]:
    """Protagonista fijo; si no, el LEAD de la receta (mismo criterio que el
    randomizador para protagonist=auto)."""
    prot = project.fixed_value("protagonist")
    if prot not in (None, "", "none"):
        return prot
    if (project.decisions.get("protagonist") or {}).get("mode") == model.AUTO:
        identity = project.fixed_value("identity")
        receta = ((manifest or {}).get("recetas") or {}).get(identity) or {}
        return receta.get("lead") or "sax_tenor"
    return None


def proponer_distribucion(project: model.ComposerProject,
                          manifest: Optional[dict]) -> Dict[str, Any]:
    """Calcula la propuesta SIN modificar el proyecto (solo lectura)."""
    cat = (manifest or {}).get("catalogos") or {}
    inst_catalog = cat.get("instruments") or []
    prot = _protagonista_efectivo(project, manifest)
    if not prot or prot == "none":
        return {"protagonista": None,
                "cambios": [], "secciones_sin_cambio": [],
                "notas": ["sin protagonista fijado: fija uno o ponlo en Automático "
                          "(usa el LEAD de la receta de la identidad)"]}
    if prot not in inst_catalog:
        return {"protagonista": prot, "cambios": [], "secciones_sin_cambio": [],
                "notas": [f"'{prot}' no está en el catálogo real del contrato"]}

    identity = project.fixed_value("identity")
    receta = ((manifest or {}).get("recetas") or {}).get(identity) or {}
    base_set = set(receta.get("set_base") or [])
    focus_default = receta.get("focus_default") or {}

    cambios: List[dict] = []
    sin_cambio: List[dict] = []
    notas: List[str] = []

    # ---- 1) tabla de instrumentos -------------------------------------------
    conf = project.instruments.get(prot) or model.InstrumentDecision()
    if conf.role != model.ROLE_PROTAGONIST:
        cambios.append({"tipo": "instruments", "iid": prot, "campo": "role",
                        "antes": conf.role or model.ROLE_AUTO,
                        "despues": model.ROLE_PROTAGONIST,
                        "porque": "coherencia: el protagonista declarado debe ser el rol en la tabla"})
    if prot not in base_set and conf.enabled is not True:
        cambios.append({"tipo": "instruments", "iid": prot, "campo": "enabled",
                        "antes": conf.enabled, "despues": True,
                        "porque": f"'{prot}' está fuera del set base de {identity}: sin enabled=true no suena"})
    if prot not in DENSITY_SIN_TRADUCCION and conf.density is None:
        cambios.append({"tipo": "instruments", "iid": prot, "campo": "density",
                        "antes": None, "despues": DENSITY_PROPUESTA,
                        "porque": "presencia reconocible del lead (editable; el motor la usa en su banda de lead)"})
    elif prot in DENSITY_SIN_TRADUCCION:
        notas.append(f"density de '{prot}' NO se propone: el validador real avisa W410 "
                     "(sin traducción en el motor para este instrumento)")

    # ---- 2) focus / active por sección --------------------------------------
    for s in project.sections:
        if s.focus is None:
            extra = [i for i in (focus_default.get(s.type) or []) if i != prot][:2]
            cambios.append({"tipo": "seccion", "sid": s.id, "campo": "focus",
                            "antes": None, "despues": [prot] + extra,
                            "porque": f"focus de la receta para '{s.type}' con el protagonista primero"})
        elif prot not in s.focus:
            sin_cambio.append({"sid": s.id,
                               "motivo": "ya tiene focus definido por el usuario: no se modifica"})
        if s.active is not None and prot not in s.active:
            cambios.append({"tipo": "seccion", "sid": s.id, "campo": "active",
                            "antes": list(s.active),
                            "despues": list(s.active) + [prot],
                            "porque": "la whitelist 'active' excluye al protagonista: lo silenciaría en esa sección"})

    if not project.sections:
        notas.append("sin estructura propia: la distribución por sección se decidirá con la "
                     "estructura automática; puedes volver a proponer tras construirla")
    return {"protagonista": prot, "cambios": cambios,
            "secciones_sin_cambio": sin_cambio, "notas": notas}


def aplicar_propuesta(project: model.ComposerProject,
                      propuesta: Dict[str, Any]) -> int:
    """Aplica los cambios de la propuesta al proyecto (escritura real de
    campos del contrato). Devuelve el número de cambios aplicados.

    Los campos quedan EDITABLES en la UI: aceptar no bloquea nada.
    """
    prot = propuesta.get("protagonista")
    if not prot:
        return 0
    n = 0
    for c in propuesta.get("cambios", []):
        if c["tipo"] == "instruments":
            conf = project.instruments.setdefault(prot, model.InstrumentDecision())
            if c["campo"] == "role":
                conf.role = c["despues"]
            elif c["campo"] == "enabled":
                conf.enabled = bool(c["despues"])
            elif c["campo"] == "density":
                conf.density = c["despues"]
            n += 1
        elif c["tipo"] == "seccion":
            for s in project.sections:
                if s.id == c["sid"]:
                    if c["campo"] == "focus":
                        s.focus = list(c["despues"])[:3]
                    elif c["campo"] == "active":
                        s.active = list(c["despues"])
                    n += 1
                    break
    project.protagonist_proposal = {
        "estado": "aplicada", "protagonista": prot,
        "cambios_aplicados": n, "timestamp": time.time(),
    }
    return n


def rechazar_propuesta(project: model.ComposerProject,
                       propuesta: Dict[str, Any]) -> None:
    """Registra el rechazo SIN tocar ningún campo (decisión explícita del
    usuario; queda en el proyecto y en el manifest de las generaciones)."""
    project.protagonist_proposal = {
        "estado": "descartada", "protagonista": propuesta.get("protagonista"),
        "timestamp": time.time(),
    }
