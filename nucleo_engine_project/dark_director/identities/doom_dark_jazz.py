"""RECETA N1 REAL — identidad ``doom_dark_jazz`` (RESPUESTA 09 §4, Fase 2).

IDENTIDAD: 50/50 CONCEPTUAL entre Doom y Dark Jazz. Motor compositivo dominante:
ALTERNANCIA E INTERACCIÓN INSTRUMENTAL entre dos estados:

  Estado DOOM       = drones (strings bare + bass long + piano hold), vacío,
                      tensión prolongada, ambigüedad armónica, silencio con
                      función compositiva, sax subordinado (tonos largos) o ausente.
  Estado DARK JAZZ  = sax expresivo, rhodes rootless, vibráfono que dialoga,
                      bajo con movimiento, percusión orgánica con feel de jazz.

El 50/50 NO es dividir la canción en dos mitades ni contar notas: ambos
universos tienen presencia real por DURACIÓN, PROTAGONISMO, FUNCIÓN y
DESARROLLO. La receta lo garantiza por diseño:
  - en toda sección Dark Jazz el estrato Doom sigue presente (strings bare
    re-atacando cada compás a velocidad baja: un drone que respira, no un fondo
    estático);
  - en toda sección Doom el jazz queda reducido (sax tonos largos o ausente,
    rhodes/piano en función armónica, vibráfono campanas aisladas);
  - el COMPOSITOR (L-15) escribe el arco real en ``structure`` alternando types
    con flips de drums (light↔off), saltos de banda de density y de tension;
    las transiciones graduales emergen de las rampas de velocity entre secciones.

Mapeo de estados por type (default de receta): intro/bridge/outro = DOOM;
verse/pre_chorus/chorus/break = DARK JAZZ. chorus NO escala a heavy: el clímax
dark jazz es EXPRESIÓN, no peso de beat.

DECISIÓN SOBRE CLUSTERS SIN PAD (instrucción Fase B/C, corrección B, verificada
en código, no inventada): el mecanismo real ``tension[]`` de clusters NO es
exclusivo del pad — vive en ``gen_chordal`` (engine.py:434-453), que sirve a
pad, strings y keys por igual. doom_dark_jazz NO tiene pad (D-02): sus clusters
B3 se declaran sobre la pista de STRINGS vía ``clusters_b3`` (la pista de drones
de la identidad). Si además el compositor habilita un pad fuera de base con
tension B3, el compilador aplica §2.6.6 con PAD_TENSION_CLUSTER (abajo). No se
inventa ninguna alternativa: es el mismo mecanismo verificado del motor.

HONESTIDAD SOBRE EL BAJO (corrección B): el bajo de Dark Jazz usa patrones con
tokens S (7ª) / T (3ª) y el gesto cromático ``approach`` del motor (aplicado por
el compilador solo con resolution tonal/chromatic, D-03). Eso APROXIMA el
comportamiento jazzístico (conducción con color y aproximaciones cromáticas);
NO es un walking bass auténtico (el motor no tiene walking generativo, L-13) y
así debe describirse.

Fuentes: A. Contrato rev. 3.2 · B. Parámetros reales verificados de MIDI Forge
v1.2.0 (presets DRUM_PRESETS, capas con inst/grid/pick/prob/vel/vel_rand/
jitter/drag/when, instrumentos de percusión 'ride'/'shaker' en theory.DRUM_NOTES,
estilos STYLE_SCHEMA por rol, perfiles voicing.PROFILES bare/compact/rootless/
full, tokens de bajo R/F/O/T/S/A, ``hold: 'bar'`` y ``modes`` de strings,
seeds de bloque) · C. Decisiones de receta etiquetadas (C).
"""

IDENTITY = "doom_dark_jazz"

# --- (C/D-02) Base sonora: SIN pad (los drones los llevan strings bare + bass
# long + piano hold). piano entra como segunda voz armónica (rol keys, programa 0).
SET_BASE = ("sax_tenor", "rhodes", "vibraphone", "bass", "drums", "piano", "strings")
LEAD = "sax_tenor"

# --- (C) BPM y ritmo armónico
BPM_DEFAULT = 62
BPM_RANGO_TIPICO = (50, 74)          # W401: fuera de este rango → recomendación
HARMONIC_RHYTHM_BARS = 2             # D-05: peso armónico Doom; 1:1 → W402

# --- (C) Registro por defecto por instrumento (solo pistas base).
REGISTER_DEFAULT = {
    "sax_tenor": [58, 79],           # (C) más oscuro que dark_triphop [62,81]
    "rhodes": [45, 76],              # motor: ROLE_DEFAULTS["keys"]["range"]
    "vibraphone": [60, 88],          # motor: ROLE_DEFAULTS["mallet"]["range"]
    "bass": [28, 52],                # motor: ROLE_DEFAULTS["bass"]["range"]
    "piano": [45, 76],               # motor: ROLE_DEFAULTS["keys"]["range"]
    "strings": [48, 76],             # motor: ROLE_DEFAULTS["strings"]["range"]
}

# --- (C) D_receta(type): density BASE por tipo (§2.6.5).
D_RECETA = {
    "intro": 0.18,
    "verse": 0.38,
    "pre_chorus": 0.50,
    "chorus": 0.58,
    "bridge": 0.30,
    "break": 0.42,
    "outro": 0.15,
}

# --- (C) energy / tension / drums / focus por defecto por type (RESPUESTA 09 §4.3).
ENERGY_BASE = {
    "intro": 0.15, "verse": 0.35, "pre_chorus": 0.50, "chorus": 0.65,
    "bridge": 0.25, "break": 0.45, "outro": 0.10,
}
TENSION_BASE = {
    "intro": 0.45, "verse": 0.55, "pre_chorus": 0.60, "chorus": 0.55,
    "bridge": 0.75, "break": 0.45, "outro": 0.35,
}
# chorus NO escala a heavy (clímax = expresión); bridge = DOOM puro (off);
# break con drums air (no off) para que la improvisación del sax no dispare W418 (D-09).
DRUMS_NIVEL = {
    "intro": "air", "verse": "light", "pre_chorus": "light", "chorus": "light",
    "bridge": "off", "break": "air", "outro": "air",
}
FOCUS_DEFAULT = {
    "intro": ["strings", "bass"],
    "verse": ["sax_tenor", "rhodes"],
    "pre_chorus": ["vibraphone", "sax_tenor"],
    "chorus": ["sax_tenor", "bass", "drums"],
    "bridge": ["strings", "piano"],
    "break": ["sax_tenor", "vibraphone"],
    "outro": ["strings", "vibraphone"],
}

# --- (B) Escalera de drums §2.6.3 → presets REALES (usada si el compositor
# fuerza un nivel distinto del default del type, o la improvisación baja un nivel).
DRUMS_PRESET_POR_NIVEL = {
    "off": "none",
    "air": "intro_air",
    "light": "trip_bridge",
    "groove": "trip_verse",
    "heavy": "trip_chorus",
}
DRUMS_VEL_SCALE_POR_NIVEL = {
    "off": None, "air": 0.85, "light": 0.95, "groove": 1.0, "heavy": 1.1,
}
DRUMS_FILLS_HEAVY = [
    {"when": {"last": True},
     "rolls": [{"inst": "snare", "start": 3.0, "steps": 4, "step": 0.25,
                "v0": 50, "v1": 72}]},
]

# --- (B/C) Cluster Doom sobre strings para tension B3 (mecanismo real
# ``tension`` de gen_chordal, verificado para pad/strings/keys; ver docstring).
DOOM_CLUSTER_STRINGS = {
    "offset": 1, "near": 54, "beat": 2.0, "dur": 2.0, "vel": 40,
    "quality": "all", "when": {"bar_mod": [4, [0, 1]]},
}
# --- (B) Cluster del pad SOLO para pistas pad INICIALIZADAS fuera del set base
# (§2.5.1; el compilador lo aplica si el compositor habilita el pad con tension B3).
PAD_TENSION_CLUSTER = {
    "offset": 1, "near": 54, "beat": 2.0, "dur": 1.5, "vel": 42,
    "quality": "minor", "when": {"bar_mod": [4, [0, 1]]},
}

# --- (B) lead generativo (motor: generate_phrase; density lo fija la banda)
LEAD_GENERATIVO = {"long_prob": 0.85, "motif_bars": 4}

# --- (C) Automatización de receta (D-04). Referencias por TYPE (el compilador
# las resuelve a la primera sección de ese type; type ausente → entrada omitida).
AUTOMACION = [
    {"track": "strings", "cc": 11,
     "from": {"section": "intro", "bar": 0}, "to": {"section": "intro", "bar": 4},
     "v0": 35, "v1": 85, "step": 1.0, "curve": 1.0},
    {"track": "rhodes", "cc": 11,
     "from": {"section": "outro", "bar": 0}, "to": {"section": "outro", "bar": 2},
     "v0": 100, "v1": 30, "step": 1.0, "curve": 1.2},
]

# ---------------------------------------------------------------- tabla BLOQUES
# C1: misma convención que doom_triphop (``lead_auto``, ``clusters_b3``; drums de
# tabla = default del type; override del compositor/improv → escalera genérica).
BLOQUES = {
    # -------------------------------------------------------------- intro (DOOM)
    "intro": {
        "drums": {"style": "pattern",
                  "params": {"preset": "intro_air", "vel_scale": 0.85}},
        "bass": {"style": "long", "params": {"center": 38, "legato": 0.97},
                 "velocity": 55},                     # drone grave
        "piano": {"style": "hold",
                  "params": {"voicing": {"profile": "full"}, "restrike_beats": 0},
                  "velocity": 40},                    # swells oscuros (con CC11)
        "rhodes": {"style": "hold",
                   "params": {"voicing": {"profile": "compact"},
                              "restrike_beats": 0}, "velocity": 42},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}}, "velocity": 48},
        "vibraphone": {"style": "pings", "params": {"count": 1, "dur": 6},
                       "velocity": 38, "from_bar": 4},   # campanas: 2ª mitad
        "sax_tenor": {"enabled": False, "style": "none", "params": {}},
    },
    # -------------------------------------------------------------- verse (DJ)
    "verse": {
        "drums": {"style": "pattern",
                  "params": {"vel_scale": 0.9,
                             # (C) capas propias con feel de jazz: ride en corcheas
                             # (el tiempo del jazz), kick suave, rim esporádico;
                             # jitter/drag = mecánica real del motor.
                             "layers": [
                                 {"inst": "ride", "grid": 0.5, "vel": [48, 38],
                                  "jitter": 0.02, "drag": [0.2, 0.037]},
                                 {"inst": "kick", "at": [0], "vel": 72,
                                  "offset": -0.006},
                                 {"inst": "rim", "at": [2], "vel": 54,
                                  "offset": 0.037, "prob": 0.5},
                                 {"inst": "closed_hat", "pick": [1.5, 3.5],
                                  "prob": 0.35, "vel_rand": [26, 36],
                                  "jitter": 0.025},
                             ]}},
        "bass": {"style": "pattern",
                 "params": {"patterns": [
                     # (C) conducción APROXIMADA (no walking auténtico, L-13):
                     # raíz → 7ª (S) → 3ª (T) del acorde, variante con 5ª (F).
                     [[0, "R", 1.5, 0], [1.5, "S", 1.0, -4], [2.5, "T", 1.25, -2]],
                     [[0, "R", 1.5, 0], [2.0, "F", 1.0, -8], [3.25, "S", 0.75, -4]],
                 ],
                     "center": 38, "slide_in": {"every": 4}, "slide_out": True},
                 "velocity": 70},
        "piano": {"style": "broken",
                  "params": {"voicing": {"profile": "bare"}, "step": 1.0,
                             "pattern": "up", "ring": 2.5, "rest_prob": 0.35},
                  "velocity": 50},       # comping disperso; bare complementa al
                                         # rhodes rootless (sin doblar 3as)
        "rhodes": {"style": "broken",
                   "params": {"voicing": {"profile": "rootless"}, "step": 1.0,
                              "pattern": "up", "ring": 2.5, "rest_prob": 0.20},
                   "velocity": 56},                     # voicing jazz: sin raíz
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}, "hold": "bar"},
                    "velocity": 36},          # estrato Doom que respira SIEMPRE
        "vibraphone": {"style": "replies",
                       "params": {"prob": 0.55, "margin": 0.25, "dur": 2.0,
                                  "max_per_bar": 2}, "velocity": 50},
        "sax_tenor": {"style": "auto", "lead_auto": True,
                      "params": {"long_prob": 0.6}, "velocity": 64},
    },
    # -------------------------------------------------------------- pre_chorus (DJ)
    "pre_chorus": {
        "drums": {"style": "pattern",
                  "params": {"vel_scale": 0.9,
                             "layers": [
                                 {"inst": "ride", "grid": 0.5, "vel": [50, 40],
                                  "jitter": 0.02, "drag": [0.2, 0.037]},
                                 {"inst": "kick", "at": [0], "vel": 76,
                                  "offset": -0.006},
                                 {"inst": "rim", "at": [2], "vel": 56,
                                  "offset": 0.037, "prob": 0.6},
                                 {"inst": "closed_hat", "pick": [1.5, 3.5],
                                  "prob": 0.35, "vel_rand": [26, 36],
                                  "jitter": 0.025},
                             ]}},
        "bass": {"style": "pattern",
                 "params": {"patterns": [
                     [[0, "R", 2.4, 0], [2.5, "F", 1.2, -8]], [],
                 ],
                     "center": 38, "slide_in": {"every": 4}, "slide_out": True},
                 "velocity": 66},          # el movimiento respira: compás sí/no
        "piano": {"style": "broken",
                  "params": {"voicing": {"profile": "bare"}, "step": 1.0,
                             "pattern": "up", "ring": 2.5, "rest_prob": 0.25},
                  "velocity": 54},
        "rhodes": {"style": "broken",
                   "params": {"voicing": {"profile": "rootless"}, "step": 1.0,
                              "pattern": "up", "ring": 2.5, "rest_prob": 0.15},
                   "velocity": 58},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}}, "velocity": 40},
        "vibraphone": {"style": "replies",
                       "params": {"prob": 0.6, "margin": 0.25, "dur": 2.0,
                                  "max_per_bar": 2}, "velocity": 52},
        "sax_tenor": {"style": "generative", "lead_auto": True,
                      "params": {"contour": "rising", "long_prob": 0.6},
                      "velocity": 62},
    },
    # -------------------------------------------------------------- chorus (DJ clímax)
    "chorus": {
        "drums": {"style": "pattern",
                  "params": {"preset": "trip_verse", "vel_scale": 1.0,
                             "fills": [{"when": {"last": True},
                                        "rolls": [{"inst": "snare", "start": 3.0,
                                                   "steps": 4, "step": 0.25,
                                                   "v0": 50, "v1": 72}]}]}},
        "bass": {"style": "pattern",
                 "params": {"patterns": [
                     [[0, "R", 1.4, 2], [1.5, "F", 0.9, -4], [2.5, "T", 0.4, -8],
                      [3.25, "S", 0.5, -4]],
                     [[0, "R", 1.4, 2], [1.5, "T", 0.9, -6], [3.25, "F", 0.5, -4]],
                 ],
                     "center": 38, "slide_in": {"every": 4}, "slide_out": True},
                 "velocity": 78},
        "piano": {"style": "broken",
                  "params": {"voicing": {"profile": "bare"}, "step": 1.0,
                             "pattern": "up", "ring": 2.5, "rest_prob": 0.20},
                  "velocity": 62},
        "rhodes": {"style": "broken",
                   "params": {"voicing": {"profile": "rootless"}, "step": 1.0,
                              "pattern": "up", "ring": 2.5, "rest_prob": 0.10},
                   "velocity": 66},          # el rhodes empuja en el clímax
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}}, "velocity": 44},
        "vibraphone": {"style": "replies",
                       "params": {"prob": 0.4, "margin": 0.3, "max_per_bar": 2},
                       "velocity": 58},
        "sax_tenor": {"style": "auto", "lead_auto": True, "params": {},
                      "velocity": 78},
    },
    # -------------------------------------------------------------- bridge (DOOM)
    "bridge": {
        "drums": {"enabled": False, "style": "none", "params": {}},
        "bass": {"style": "long",
                 "params": {"center": 38, "fifth_at": 4, "legato": 0.97},
                 "velocity": 50},                     # quinta abierta
        "piano": {"style": "hold",
                  "params": {"voicing": {"profile": "full"}, "restrike_beats": 4},
                  "velocity": 45},
        "rhodes": {"style": "hold",
                   "params": {"voicing": {"profile": "rootless"},
                              "restrike_beats": 4}, "velocity": 46},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"},
                               "modes": ["bare", "full"]}, "velocity": 55,
                    "clusters_b3": [DOOM_CLUSTER_STRINGS]},   # clusters SIN pad
        "vibraphone": {"style": "pings", "params": {"count": 2, "dur": 6},
                       "velocity": 40, "seed": 214},
        "sax_tenor": {"style": "hold", "lead_auto": True,
                      "params": {"legato": 1.0}, "velocity": 48},
    },
    # -------------------------------------------------------------- break (DJ dúo)
    "break": {
        "drums": {"style": "pattern",
                  "params": {"vel_scale": 0.85,
                             "layers": [
                                 {"inst": "crash", "at": [0], "vel": 42,
                                  "dur": 3.5, "when": {"bars": [0]}},
                                 {"inst": "shaker", "grid": 1.0, "vel": [40, 34],
                                  "jitter": 0.02},
                             ]}},
        "bass": {"style": "pattern",
                 "params": {"patterns": [
                     [[0, "R", 1.4, 0], [1.5, "F", 1.4, -6], [3.25, "R", 0.5, -4]],
                     [[0, "R", 1.4, 0], [1.5, "F", 1.4, -6], [3.25, "F", 0.5, -4]],
                 ],
                     "center": 38, "slide_in": {"every": 4}, "slide_out": True},
                 "velocity": 66},
        "piano": {"style": "tail",
                  "params": {"voicing": {"profile": "bare"}, "notes_per_chord": 2,
                             "ring": 6}, "velocity": 44},
        "rhodes": {"style": "broken",
                   "params": {"voicing": {"profile": "rootless"}, "step": 1.0,
                              "pattern": "up", "ring": 2.5, "rest_prob": 0.30},
                   "velocity": 52},          # deja espacio al sax: dúo cámara
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}}, "velocity": 30},
        "vibraphone": {"style": "replies",
                       "params": {"prob": 0.7, "margin": 0.25, "dur": 1.5,
                                  "glint_gap": 0.75, "max_per_bar": 1},
                       "velocity": 52},
        "sax_tenor": {"style": "generative", "lead_auto": True,
                      "params": {"long_prob": 0.45}, "velocity": 70},
    },
    # -------------------------------------------------------------- outro (DOOM)
    "outro": {
        "drums": {"style": "pattern",
                  "params": {"preset": "intro_air", "vel_scale": 0.7}},
        "bass": {"style": "long", "params": {"center": 38, "legato": 0.97},
                 "velocity": [48, 20]},
        "piano": {"style": "tail",
                  "params": {"voicing": {"profile": "bare"}, "notes_per_chord": 2,
                             "ring": 6}, "velocity": [40, 16]},
        "rhodes": {"style": "tail",
                   "params": {"voicing": {"profile": "rootless"},
                              "notes_per_chord": 2, "ring": 6},
                   "velocity": [48, 18]},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}},
                    "velocity": [46, 20]},
        "vibraphone": {"style": "pings", "params": {"count": 2, "dur": 6},
                       "velocity": [38, 15]},
        "sax_tenor": {"style": "hold", "lead_auto": True,
                      "params": {"legato": 1.0}, "velocity": [52, 18]},
    },
}

# --- (C) Progresiones N1 por (language, type): pares (offset sobre la tónica,
# calidad). verse hybrid = linaje i–iø–VI–V del dark jazz (offsets 3/8/7 con
# calidades tensas); los drones de bridge usan m7b5/7#11 = suspensión.
PROGRESIONES = {
    "pop_dream_pop": {
        "intro":      [(0, "m9")],
        "verse":      [(0, "m9"), (5, "maj9"), (8, "maj7"), (7, "7sus4")],
        "pre_chorus": [(5, "maj9"), (7, "7sus4")],
        "chorus":     [(8, "maj9"), (10, "m9"), (5, "maj9"), (9, "7sus4")],
        "bridge":     [(1, "maj7"), (5, "add9")],
        "break":      [(0, "m9"), (8, "maj7")],
        "outro":      [(0, "add9")],
    },
    "hybrid": {
        "intro":      [(0, "m9")],
        "verse":      [(0, "m9"), (3, "m7b5"), (8, "maj7"), (7, "9")],
        "pre_chorus": [(5, "9"), (7, "13")],
        "chorus":     [(0, "m9"), (10, "m13"), (8, "13"), (7, "7sus4")],
        "bridge":     [(3, "m7b5"), (7, "7#11")],
        "break":      [(0, "m11"), (8, "maj7")],
        "outro":      [(0, "m9")],
    },
    "experimental": {
        "intro":      [(0, "m9")],
        "verse":      [(0, "m11"), (3, "m7b5"), (8, "maj9"), (7, "7b9")],
        "pre_chorus": [(5, "m9"), (7, "9")],
        "chorus":     [(0, "m11"), (6, "dim7"), (8, "maj9"), (7, "7#5b9")],
        "bridge":     [(3, "m7b5"), (7, "7b9")],
        "break":      [(0, "m11"), (6, "dim7")],
        "outro":      [(0, "m9")],
    },
}
