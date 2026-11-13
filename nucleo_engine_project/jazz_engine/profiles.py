"""Perfiles de identidad — FASE 5 (Dark Trip Hop unificado).

Las decisiones MUSICALES de cada identidad viven aquí como DATO; el mecanismo
genérico (motif/improv/drums/vibes/coordinator) es agnóstico.

  - ``dark_triphop``   : perfil NUEVO (esta fase). Universo activo.
  - ``doom_triphop``   : ARCHIVADO (Fase 2/4; se conserva reproducible).
  - ``doom_dark_jazz`` : ARCHIVADO (Fase 2/4; se conserva reproducible).

Fuente del perfil dark_triphop:
  A. Receta congelada ``dark_triphop.py`` (energy/tension/focus/registros/BPM —
     copia de datos, la receta NO se toca ni se importa).
  B. Mecánica real de MIDI Forge verificada (capas ``at/pick/prob``, fills,
     replies con respond_to, bends scoop/fall del lead).
  C. Decisiones musicales de la FASE 5, etiquetadas (C): lógica compositiva
     «Familiaridad → Deformación → Ruptura → Reconstrucción» contenida dentro
     del groove trip-hop: motivos reconocibles, apariciones/desapariciones del
     sax, espacios atmosféricos, NADA de jam de jazz.

Reglas de negocio del perfil (C):
  - El sax NO toca en intro; establece motivo en su primera aparición;
    desarrolla después; desaparece en bridge/break con alta probabilidad
    (espacio = decisión musical).
  - El Rhodes es soporte por defecto (el comping lo emite el compilador);
    las notas melódicas del Rhodes son RESPUESTAS breves o contrapunto
    puntual, nunca relleno sistemático.
  - El vibráfono es intermitente (respuestas en huecos + eco ocasional del
    motivo), presente en ≤ 40 % de los compases del tema.
  - La batería conserva el preset base del compilador y añade microvariación
    (ghost notes, acentos) + transiciones; ruptura solo en break/bridge con
    reconstrucción inmediata.
"""

#: identidades activas/archivadas (FASE 5, unificación)
ACTIVE_IDENTITY = "dark_triphop"
ARCHIVED_IDENTITIES = ("doom_triphop", "doom_dark_jazz")


class Profile(object):
    """Datos de perfil. Instancias inmutables en la práctica (solo lectura)."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def get(self, k, default=None):
        return self.__dict__.get(k, default)


# ---------------------------------------------------------------------------
# Celdas rítmicas (beats en 4/4). Cada celda es una lista (onset, dur).
# ---------------------------------------------------------------------------
CELLS_CONTENIDO = [
    [(0.0, 1.5), (1.5, 0.5), (2.0, 2.0)],                 # largo-corto-largo
    [(0.0, 0.75), (0.75, 0.75), (1.5, 0.5), (3.0, 1.0)],  # 3+3+2 + respuesta
    [(0.5, 0.5), (1.0, 0.75), (2.0, 0.5), (2.5, 1.5)],    # entrada sincopada
    [(0.0, 2.5), (3.0, 0.5), (3.5, 0.5)],                 # tono largo + pregunta
    [(1.0, 0.5), (1.5, 0.5), (2.5, 1.5)],                 # entra en el beat 2
    [(0.0, 0.5), (0.5, 0.5), (1.0, 1.0), (2.5, 0.5), (3.0, 1.0)],
]
CELLS_RESPUESTA = [
    [(0.5, 0.5), (1.0, 1.5)],                             # respuesta breve
    [(1.5, 0.5), (2.0, 1.0)],
    [(0.0, 0.75), (0.75, 0.75), (1.5, 2.0)],
    [(2.0, 0.5), (2.5, 0.5), (3.0, 1.0)],
]
CELLS_SUSPENSION = [
    [(0.0, 3.5)],                                          # tono largo
    [(1.0, 3.0)],
    [(0.0, 2.0), (2.0, 2.0)],
]

# Movimiento interválico (semitonos) con pesos: pasos y saltos moderados;
# los saltos grandes piden compensación por paso contrario (regla del motor).
MOV_DTH = [(0, 10), (1, 16), (-1, 16), (2, 12), (-2, 12), (3, 7), (-3, 7),
           (5, 4), (-5, 4), (7, 2), (-7, 2), (12, 1), (-12, 1)]

DARK_TRIPHOP = Profile(
    name="dark_triphop",
    active=True,
    archived=False,
    # --- datos (A): energía/tensión/focus de la receta congelada
    ENERGY_BASE={"intro": 0.25, "verse": 0.45, "pre_chorus": 0.60, "chorus": 0.80,
                 "bridge": 0.55, "break": 0.35, "outro": 0.20},
    TENSION_BASE={"intro": 0.20, "verse": 0.35, "pre_chorus": 0.55, "chorus": 0.50,
                  "bridge": 0.60, "break": 0.60, "outro": 0.15},
    FOCUS_DEFAULT={"intro": ["rhodes", "pad"], "verse": ["sax_tenor", "drums"],
                   "pre_chorus": ["pad", "vibraphone"], "chorus": ["sax_tenor", "drums", "bass"],
                   "bridge": ["rhodes", "vibraphone"], "break": ["vibraphone"],
                   "outro": ["rhodes"]},
    REGISTER={"sax_tenor": (62, 81), "rhodes": (45, 76), "vibraphone": (72, 88)},
    # --- sax (C)
    sax={
        "cells": CELLS_CONTENIDO,
        "cells_response": CELLS_RESPUESTA,
        "cells_suspension": CELLS_SUSPENSION,
        "movement": MOV_DTH,
        "phrase_bars": (1, 3),            # frases cortas-contenidas
        "max_consecutive": 2,             # máx. secciones seguidas con sax activo
        "max_active_share": 0.65,         # ≤ 65 % de las secciones con sax
        "section_plan": {
            # acción por type: absent | statement | develop | respond | question | suspend | final
            "intro": "absent",
            "verse": "statement",         # 1ª verse establece; siguientes desarrollan
            "pre_chorus": "respond",
            "chorus": "develop",
            "bridge": "suspend",
            "break": "question",
            "outro": "final",
        },
        "prob_overrides": {               # prob de que la acción ocurra (espacio)
            "pre_chorus": 0.6, "bridge": 0.45, "break": 0.5, "outro": 0.55,
        },
        "vel_range": (58, 84),
        "vel_by_type": {"verse": (62, 74), "pre_chorus": (58, 70), "chorus": (70, 84),
                        "bridge": (54, 64), "break": (56, 66), "outro": (50, 60)},
        "open_ending_prob": 0.35,         # final abierto (9ª/5ª sin resolver)
        "tension_tone_prob": 0.30,        # tensión (9/13) antes de resolver
        "approach_prob": 0.45,            # aproximación cromática/diatónica al objetivo
        "rest_between": True,             # respiración garantizada entre frases
        "bends": {"scoop": {"enabled": True, "prob": 0.35, "semitones": 0.4, "beats": 0.22,
                            "min_gap": 0.9},
                  "fall": {"enabled": True, "prob": 0.22, "semitones": 0.5, "beats": 0.5,
                           "min_dur": 2.5}},
    },
    # --- rhodes (C): comportamiento por type
    rhodes={
        "behavior": {                      # support | response | counterpoint | independent | interaction
            "intro": "independent",
            "verse": "response",
            "pre_chorus": "support",
            "chorus": "counterpoint",
            "bridge": "independent",
            "break": "support",
            "outro": "independent",
        },
        "prob_by_behavior": {"response": 0.55, "counterpoint": 0.5, "independent": 0.4,
                             "interaction": 0.7, "support": 0.0},
        "notes_per_section_cap": (2, 6),   # tope de notas melódicas por sección (mín, máx)
        "vel_range": (42, 58),
        "register": (47, 67),              # bajo el sax: subordinado, no compite
        "answer_gap": (0.75, 1.5),         # tras el fin del sax, beats de espera
        "open_answer_prob": 0.6,           # respuesta sin resolver (5ª/9ª)
        "max_sections_melodic_share": 0.5, # ≤ 50 % de secciones con rhodes melódico
    },
    # --- vibráfono (C)
    vibes={
        "replies_params": {                # ajustes sobre los params del compilador
            "verse": {"prob": 0.30, "max_per_bar": 1},
            "pre_chorus": {"prob": 0.35, "max_per_bar": 1},
            "chorus": {"prob": 0.40, "max_per_bar": 2},
            "bridge": {"prob": 0.30, "max_per_bar": 1},
            "break": {"prob": 0.25, "max_per_bar": 1},
        },
        "echo_prob": 0.5,                  # eco de motivo tras una frase del sax
        "echo_notes": (1, 2),
        "echo_register": (74, 86),
        "echo_vel": (38, 50),
        "max_present_share": 0.40,         # ≤ 40 % de compases del tema con vibes propio
    },
    # --- batería (C): microvariación sobre el preset base del compilador
    drums={
        "ghost": {                          # ghost notes de snare2/rim
            "insts": ("snare2", "rim"),
            "picks": {"snare2": [2.75, 3.75], "rim": [1.75, 3.5]},
            "vel_range": (20, 34),
            "base_prob": 0.30,              # escalado por energía de la sección
            "offset": 0.05,
        },
        "accent_kick": {                    # bombo de acento fuera del patrón de bajo
            "positions_by_type": {"verse": [2.5], "chorus": [2.75], "pre_chorus": [2.5],
                                  "break": [2.5]},
            "vel": 58,
            "prob": 0.55,
            "when_bar_mod": [4, 3],         # 1 de cada 4 compases (el 4º)
        },
        "hat_variation": {                  # open hat ocasional de acento
            "position": 3.5,
            "prob": 0.25,
            "vel_range": (50, 62),
            "when_bar_mod": [4, 2],
        },
        "transition_fill": {                # fill de transición (solo secciones build)
            "types": ("pre_chorus",),
            "rolls": [{"inst": "snare2", "start": 3.0, "steps": 4, "step": 0.25,
                       "v0": 50, "v1": 78}],
            "mute_from": 3.0,
        },
        "rupture": {                        # ruptura controlada + reconstrucción
            "types": ("break", "bridge"),
            "light_bars": 2,                # primeros compases sin groove completo
            "vel_scale_delta": -0.08,
        },
        "build_types": ("pre_chorus", "chorus"),
    },
)

# ---------------------------------------------------------------------------
# Perfiles ARCHIVADOS (Fase 4, preservados: reproducibilidad histórica).
# Mecanismo idéntico; decisiones musicales de Doom, ya no son la dirección.
# ---------------------------------------------------------------------------
DOOM_TRIPHOP = Profile(
    name="doom_triphop",
    active=False,
    archived=True,
    ENERGY_BASE={"intro": 0.20, "verse": 0.45, "pre_chorus": 0.55, "chorus": 0.70,
                 "bridge": 0.40, "break": 0.30, "outro": 0.15},
    TENSION_BASE={"intro": 0.40, "verse": 0.50, "pre_chorus": 0.55, "chorus": 0.60,
                  "bridge": 0.70, "break": 0.65, "outro": 0.35},
    FOCUS_DEFAULT={"intro": ["strings", "bass"], "verse": ["sax_tenor", "drums"],
                   "pre_chorus": ["sax_tenor", "pad"], "chorus": ["drums", "bass"],
                   "bridge": ["strings"], "break": ["vibraphone"], "outro": ["strings"]},
    REGISTER={"sax_tenor": (58, 79), "rhodes": (45, 76), "vibraphone": (72, 88)},
    sax={
        "cells": CELLS_CONTENIDO,
        "cells_response": CELLS_RESPUESTA,
        "cells_suspension": CELLS_SUSPENSION,
        "movement": MOV_DTH,
        "phrase_bars": (1, 2),
        "max_consecutive": 2,
        "max_active_share": 0.55,
        "section_plan": {"intro": "absent", "verse": "statement", "pre_chorus": "respond",
                         "chorus": "develop", "bridge": "absent", "break": "question",
                         "outro": "final"},
        "prob_overrides": {"pre_chorus": 0.5, "break": 0.45, "outro": 0.4},
        "vel_range": (54, 78),
        "vel_by_type": {"verse": (58, 70), "chorus": (64, 78)},
        "open_ending_prob": 0.45, "tension_tone_prob": 0.25, "approach_prob": 0.4,
        "rest_between": True,
        "bends": {"scoop": {"enabled": True, "prob": 0.25, "semitones": 0.5, "beats": 0.2,
                            "min_gap": 1.0},
                  "fall": {"enabled": False}},
    },
    rhodes={
        "behavior": {"intro": "support", "verse": "support", "pre_chorus": "support",
                     "chorus": "counterpoint", "bridge": "support", "break": "support",
                     "outro": "support"},
        "prob_by_behavior": {"response": 0.35, "counterpoint": 0.45, "independent": 0.25,
                             "interaction": 0.4, "support": 0.0},
        "notes_per_section_cap": (1, 4),
        "vel_range": (40, 54),
        "register": (45, 64),
        "answer_gap": (1.0, 2.0),
        "open_answer_prob": 0.7,
        "max_sections_melodic_share": 0.35,
    },
    vibes={
        "replies_params": {"verse": {"prob": 0.25, "max_per_bar": 1},
                           "chorus": {"prob": 0.30, "max_per_bar": 1}},
        "echo_prob": 0.2, "echo_notes": (1, 1), "echo_register": (72, 84),
        "echo_vel": (34, 44), "max_present_share": 0.30,
    },
    drums={
        "ghost": {"insts": ("rim",), "picks": {"rim": [3.5]}, "vel_range": (18, 28),
                  "base_prob": 0.25, "offset": 0.05},
        "accent_kick": {"positions_by_type": {"verse": [2.5]}, "vel": 54, "prob": 0.5,
                        "when_bar_mod": [4, 3]},
        "hat_variation": {"position": 3.5, "prob": 0.2, "vel_range": (46, 56),
                          "when_bar_mod": [4, 2]},
        "transition_fill": {"types": ("pre_chorus",),
                            "rolls": [{"inst": "snare2", "start": 3.0, "steps": 4,
                                       "step": 0.25, "v0": 46, "v1": 72}],
                            "mute_from": 3.0},
        "rupture": {"types": ("bridge",), "light_bars": 2, "vel_scale_delta": -0.1},
        "build_types": ("pre_chorus",),
    },
)

DOOM_DARK_JAZZ = Profile(
    name="doom_dark_jazz",
    active=False,
    archived=True,
    ENERGY_BASE={"intro": 0.15, "verse": 0.35, "pre_chorus": 0.50, "chorus": 0.65,
                 "bridge": 0.25, "break": 0.45, "outro": 0.10},
    TENSION_BASE={"intro": 0.45, "verse": 0.55, "pre_chorus": 0.60, "chorus": 0.55,
                  "bridge": 0.75, "break": 0.45, "outro": 0.35},
    FOCUS_DEFAULT={"intro": ["strings", "bass"], "verse": ["sax_tenor", "rhodes"],
                   "pre_chorus": ["vibraphone", "sax_tenor"], "chorus": ["sax_tenor", "bass"],
                   "bridge": ["strings"], "break": ["sax_tenor", "vibraphone"],
                   "outro": ["strings"]},
    REGISTER={"sax_tenor": (58, 79), "rhodes": (45, 76), "vibraphone": (72, 88)},
    sax={
        "cells": CELLS_CONTENIDO,
        "cells_response": CELLS_RESPUESTA,
        "cells_suspension": CELLS_SUSPENSION,
        "movement": MOV_DTH,
        "phrase_bars": (2, 3),             # frases más largas (dark jazz)
        "max_consecutive": 3,
        "max_active_share": 0.75,
        "section_plan": {"intro": "suspend", "verse": "statement", "pre_chorus": "develop",
                         "chorus": "develop", "bridge": "absent", "break": "respond",
                         "outro": "suspend"},
        "prob_overrides": {"bridge": 0.2, "outro": 0.5},
        "vel_range": (52, 76),
        "vel_by_type": {"verse": (56, 68), "chorus": (62, 76)},
        "open_ending_prob": 0.5, "tension_tone_prob": 0.4, "approach_prob": 0.55,
        "rest_between": True,
        "bends": {"scoop": {"enabled": True, "prob": 0.45, "semitones": 0.4, "beats": 0.25,
                            "min_gap": 0.8},
                  "fall": {"enabled": True, "prob": 0.3, "semitones": 0.5, "beats": 0.55,
                           "min_dur": 2.0}},
    },
    rhodes={
        "behavior": {"intro": "independent", "verse": "interaction", "pre_chorus": "response",
                     "chorus": "counterpoint", "bridge": "support", "break": "interaction",
                     "outro": "independent"},
        "prob_by_behavior": {"response": 0.65, "counterpoint": 0.55, "independent": 0.5,
                             "interaction": 0.75, "support": 0.0},
        "notes_per_section_cap": (3, 8),
        "vel_range": (42, 60),
        "register": (47, 67),
        "answer_gap": (0.5, 1.25),
        "open_answer_prob": 0.5,
        "max_sections_melodic_share": 0.6,
    },
    vibes={
        "replies_params": {"verse": {"prob": 0.45, "max_per_bar": 2},
                           "pre_chorus": {"prob": 0.5, "max_per_bar": 2},
                           "chorus": {"prob": 0.45, "max_per_bar": 2},
                           "break": {"prob": 0.4, "max_per_bar": 2}},
        "echo_prob": 0.45, "echo_notes": (2, 3), "echo_register": (74, 86),
        "echo_vel": (40, 52), "max_present_share": 0.45,
    },
    drums={
        "ghost": {"insts": ("rim", "snare2"), "picks": {"rim": [1.75, 3.5], "snare2": [3.75]},
                  "vel_range": (20, 32), "base_prob": 0.28, "offset": 0.05},
        "accent_kick": {"positions_by_type": {"verse": [2.5]}, "vel": 54, "prob": 0.45,
                        "when_bar_mod": [4, 3]},
        "hat_variation": {"position": 3.5, "prob": 0.22, "vel_range": (48, 58),
                          "when_bar_mod": [4, 2]},
        "transition_fill": {"types": ("pre_chorus", "break"),
                            "rolls": [{"inst": "snare2", "start": 3.25, "steps": 3,
                                       "step": 0.25, "v0": 44, "v1": 70}],
                            "mute_from": 3.25},
        "rupture": {"types": ("bridge",), "light_bars": 0, "vel_scale_delta": -0.06},
        "build_types": ("pre_chorus",),
    },
)

PROFILES = {p.name: p for p in (DARK_TRIPHOP, DOOM_TRIPHOP, DOOM_DARK_JAZZ)}


def resolve_profile(name):
    """Nombre de perfil → Profile. 'auto' usa la identidad activa del proyecto
    (resuelto por el caller); desconocido → perfil activo."""
    if name in PROFILES:
        return PROFILES[name]
    raise KeyError("perfil desconocido: %r (disponibles: %s)" % (name, ", ".join(sorted(PROFILES))))
