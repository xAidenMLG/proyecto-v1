"""Perfil de accesibilidad (nivel N2 de la escalera de precedencia, §2.3).

La accesibilidad gobierna ESCRITURA Y DESARROLLO, nunca BPM/groove/timbres
(§2.1). En Fase 1 su única traducción real es la de guardrails (§2.11):
``motif_repeat`` y ``lead_coverage`` ON en commercial y balanced, OFF en
experimental; los otros 6 guardrails reales de ``forge.validate`` están
siempre ON. ``qa.guardrails`` (N7) sobrescribe estos defaults (§2.3,
excepción 4) — lo aplica el compilador.
"""

#: guardrails SIEMPRE ON por defecto (§2.11)
GUARDRAILS_SIEMPRE_ON = ("mallet_sparse", "lead_mallet_overlap", "lead_mono_range",
                         "bass_kick", "four_on_floor", "section_bounds")

#: defaults de accesibilidad para los guardrails condicionados (§2.11)
GUARDRAILS_POR_ACCESIBILIDAD = {
    "commercial": {"motif_repeat": True, "lead_coverage": True},
    "balanced": {"motif_repeat": True, "lead_coverage": True},
    "experimental": {"motif_repeat": False, "lead_coverage": False},
}


def guardrails_default(accessibility):
    """Dict con los 8 guardrails reales según el perfil de accesibilidad (§2.11)."""
    if accessibility not in GUARDRAILS_POR_ACCESIBILIDAD:
        raise ValueError(f"accesibilidad fuera del contrato: {accessibility!r}")
    out = {nombre: True for nombre in GUARDRAILS_SIEMPRE_ON}
    out.update(GUARDRAILS_POR_ACCESIBILIDAD[accessibility])
    return out
