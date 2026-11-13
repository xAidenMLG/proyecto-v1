"""RECETA N1 REAL — identidad ``doom_triphop`` (RESPUESTA 09 §3, Fase 2).

IDENTIDAD: no es trip hop lento/pesado ni decorado con Doom. Es una identidad
que ROMPE y contamina el lenguaje trip hop mediante TRANSFORMACIÓN ESTRUCTURAL
(motor compositivo dominante), siguiendo la cadena aprobada:

    FAMILIARIDAD → DEFORMACIÓN → RUPTURA → RECONSTRUCCIÓN → NUEVA RUPTURA

  - verse      = familiaridad  (groove trip + motivo reconocible)
  - pre_chorus = deformación   (drums bajan, rim en compases alternos, la pulsa
                               del rhodes se deshace hacia rootless, sax asciende)
  - break      = ruptura I     (drums OFF, sax en planos, clusters B3, glints del
                               vibráfono en el vacío, bajo quinta abierta)
  - chorus     = reconstrucción(máxima energía pero armonía hybrid/dissonante:
                               el material viejo vuelve en un mundo deformado)
  - bridge     = ruptura II    (drums light con entrada suave, strings alternando
                               bare/full por ciclo, cluster B3 en compases 0/1)
  - outro      = colapso       (rampas de velocity hacia el silencio)

Fuentes de cada dato (mismo régimen que dark_triphop.py):
  A. Contrato ``dark-director/1`` rev. 3.2 (§2.6.2 energy, §2.6.3 drums,
     §2.6.4 focus, §2.6.5 density/D_receta, §2.6.6 tension, §2.11 guardrails).
  B. Parámetros REALES de MIDI Forge v1.2.0: presets ``intro_air /
     trip_bridge / trip_verse / trip_chorus`` (styles.DRUM_PRESETS), vocabulario
     de capas (inst/at/grid/pick/prob/vel/vel_rand/offset/jitter/drag/omit/
     skip_if_open/when), tokens de bajo R/F/O/T/S/A, estilos de
     styles.STYLE_SCHEMA por rol, perfiles de voicing.PROFILES (bare, shell,
     rootless, spread, rootoctave, rootfifth, full), condiciones ``when`` de
     engine.when_ok (bar_mod, last, bars...), fills con mute/hits/rolls,
     ``light_bars``/``light_preset`` de drums, ``hold: 'bar'`` y ``tension[]``
     del pad/strings, ``modes`` de strings, seeds de bloque (engine Ctx.rng).
     La tabla BLOQUES usa EXCLUSIVAMENTE nombres de campo verificados en el
     motor (RESPUESTA 09 §1, filas A1–A18; §2, matriz con archivo y línea).
  C. Decisión de receta (valores propios N1 de doom_triphop, etiquetados (C)):
     D_receta/energy/tension/drums/focus por type, BPM, registros, progresiones
     por (language, type), velocidades, capas propias y automatización.
     Los presets trip_* y sus capas se citan del MOTOR (styles.py), no de
     dark_triphop.py: esta receta NO copia dark_triphop cambiando parámetros;
     declara su propia lógica por sección y sus propias capas (los bloques con
     ``layers`` SUSTITUYEN al preset, engine.gen_drums: «p.get('layers') or
     main['layers']»), que es donde vive la deformación.

Decisiones registradas (RESPUESTA 09 §0.3/§8): D-01 paleta mutable
(sax/rhodes/vibráfono aparecen, se fragmentan o desaparecen; el TIMBRE/rol de
cada pista es fijo), D-03 approach solo con resolution tonal/chromatic (lo
aplica el compilador), D-04 automation como dato de receta, D-05 ritmo
armónico default 2 compases, D-06 break/bridge con drums off/light (la ruptura
real es silencio), D-07 sin four-on-floor, D-09 improvisación solo con drums ≥ air.
"""

IDENTITY = "doom_triphop"

# --- (C) Base sonora: strings entra como segundo plano permanente de drones
# (junto al pad); sax/rhodes/vibraphone = paleta mutable (D-01). piano NO es base.
SET_BASE = ("sax_tenor", "rhodes", "vibraphone", "bass", "drums", "pad", "strings")
LEAD = "sax_tenor"

# --- (C) BPM y ritmo armónico (defaults N1; §3.1/§3.2: default = receta)
BPM_DEFAULT = 72
BPM_RANGO_TIPICO = (58, 90)          # W401: fuera de este rango → recomendación
HARMONIC_RHYTHM_BARS = 2             # D-05: peso armónico Doom; evita W402

# --- (C) Registro por defecto por instrumento (solo pistas base).
REGISTER_DEFAULT = {
    "sax_tenor": [62, 81],           # motor: bloque lead triphop `range: [62, 81]`
    "rhodes": [45, 76],              # motor: ROLE_DEFAULTS["keys"]["range"]
    "vibraphone": [60, 88],          # motor: ROLE_DEFAULTS["mallet"]["range"]
    "bass": [28, 52],                # motor: ROLE_DEFAULTS["bass"]["range"]
    "pad": [40, 72],                 # motor: ROLE_DEFAULTS["pad"]["range"]
    "strings": [48, 76],             # motor: ROLE_DEFAULTS["strings"]["range"]
}

# --- (C) D_receta(type): density BASE por tipo (§2.6.5). Máximo 0.60 (B2/B3
# bajo): en doom_triphop la saturación NO es el vehículo de la intensidad.
D_RECETA = {
    "intro": 0.20,
    "verse": 0.40,
    "pre_chorus": 0.50,
    "chorus": 0.60,
    "bridge": 0.45,
    "break": 0.25,
    "outro": 0.15,
}

# --- (C) energy / tension / drums / focus por defecto por type (RESPUESTA 09 §3.3).
ENERGY_BASE = {
    "intro": 0.20, "verse": 0.40, "pre_chorus": 0.55, "chorus": 0.80,
    "bridge": 0.45, "break": 0.20, "outro": 0.15,
}
TENSION_BASE = {
    "intro": 0.35, "verse": 0.50, "pre_chorus": 0.65, "chorus": 0.55,
    "bridge": 0.70, "break": 0.80, "outro": 0.30,
}
# D-06: break con drums OFF (la ruptura real es silencio); bridge light.
DRUMS_NIVEL = {
    "intro": "air", "verse": "groove", "pre_chorus": "light", "chorus": "heavy",
    "bridge": "light", "break": "off", "outro": "air",
}
FOCUS_DEFAULT = {
    "intro": ["pad", "strings"],
    "verse": ["sax_tenor", "drums"],
    "pre_chorus": ["vibraphone", "pad"],
    "chorus": ["sax_tenor", "drums", "bass"],
    "bridge": ["strings", "rhodes"],
    "break": ["pad", "vibraphone"],
    "outro": ["strings", "rhodes"],
}

# --- (B) Escalera de drums §2.6.3 → presets REALES (idéntico mecanismo que
# dark_triphop.py: es el vocabulario del motor, no una copia de identidad).
# Se usa cuando el compositor fuerza un nivel distinto del default del type o
# cuando la improvisación baja un nivel (§2.6.3); el default del type lo decide
# la tabla BLOQUES de abajo.
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
# §2.6.3 heavy: fills sobre el preset (mecanismo rolls existente del motor).
DRUMS_FILLS_HEAVY = [
    {"when": {"last": True},
     "rolls": [{"inst": "snare2", "start": 3.0, "steps": 4, "step": 0.25,
                "v0": 62, "v1": 84}]},
]

# --- (C) Cluster Doom del pad para tension B3 (§2.6.6): segunda menor sobre el
# root, sobre CUALQUIER calidad de acorde (quality "all" = deformación constante,
# no un adorno de acordes menores). Mecanismo real pad.tension (engine.gen_chordal,
# intent=True, immune a reparación). El compilador lo añade SOLO si la banda de
# tension efectiva de la sección es B3 (la tensión la controla el compositor).
DOOM_CLUSTER = {
    "offset": 1, "near": 56, "beat": 2.0, "dur": 2.0, "vel": 46,
    "quality": "all", "when": {"bar_mod": [4, [0, 1]]},
}

# --- (B) lead generativo (motor: generate_phrase; density lo fija la banda §2.6.5)
LEAD_GENERATIVO = {"long_prob": 0.9, "motif_bars": 4}   # recuperación de motivo 70 %

# --- (C) Automatización de receta (D-04; §11 del contrato, fila automation).
# Swells CC11 sobre los planos Doom. Las referencias de sección usan el TYPE
# (intro/pre_chorus): el compilador las resuelve al id de la PRIMERA sección de
# ese type en la estructura; si el type no existe, la entrada se omite (nunca se
# inventa una sección). track admite id o rol (engine.build_ccs/target_tracks).
AUTOMACION = [
    {"track": "pad", "cc": 11,
     "from": {"section": "intro", "bar": 0}, "to": {"section": "intro", "bar": 4},
     "v0": 30, "v1": 90, "step": 1.0, "curve": 1.0},
    {"track": "strings", "cc": 11,
     "from": {"section": "pre_chorus", "bar": 0}, "to": {"section": "pre_chorus", "bar": 6},
     "v0": 40, "v1": 127, "step": 1.0, "curve": 1.0},
]

# ---------------------------------------------------------------- tabla BLOQUES
# C1 (RESPUESTA 09 §6.3): tabla declarativa type → {instrumento → bloque}.
# Formato de bloque = el que el motor espera (enabled/style/params/velocity/
# from_bar/to_bar/seed) más tres claves de receta que el compilador consuma y
# retire: ``lead_auto`` (aplica la lógica §2.7 improvisación / §2.7.1 motifs /
# density por banda al lead) y ``clusters_b3`` (clusters que se añaden SOLO si
# la banda de tension de la sección es B3 — la tensión sigue siendo del
# compositor). Los bloques de drums de la tabla son el DEFAULT del type; si el
# compositor fuerza otro nivel de drums o la improvisación baja un nivel, el
# compilador usa la escalera genérica DRUMS_PRESET_POR_NIVEL (§2.6.3).
# Velocidades de bloque sufren los deltas de focus §2.6.4 igual que dark_triphop.
BLOQUES = {
    # -------------------------------------------------------------- intro
    "intro": {
        "drums": {"style": "pattern",
                  "params": {"preset": "intro_air", "vel_scale": 0.85}},
        "bass": {"style": "long", "params": {"center": 38, "legato": 0.97},
                 "velocity": 55},
        "pad": {"style": "sustain",
                "params": {"voicing": {"profile": "rootfifth"}, "hold": "bar"},
                "velocity": 40},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}}, "velocity": 38},
        "rhodes": {"style": "hold",
                   "params": {"voicing": {"profile": "shell"}, "restrike_beats": 0},
                   "velocity": 46},
        "vibraphone": {"style": "pings", "params": {"count": 1, "dur": 6},
                       "velocity": 40},
        "sax_tenor": {"enabled": False, "style": "none", "params": {}},
    },
    # ------------------------------------------- verse (familiaridad)
    "verse": {
        "drums": {"style": "pattern",
                  "params": {"preset": "trip_verse", "vel_scale": 1.0,
                             "fills": [{"when": {"last": True},
                                        "rolls": [{"inst": "snare2", "start": 3.0,
                                                   "steps": 4, "step": 0.25,
                                                   "v0": 62, "v1": 84}]}]}},
        "bass": {"style": "pattern",
                 "params": {"patterns": [
                     # (C) forma propia de verse: raíz, quinta, destello de octava
                     [[0, "R", 1.4, 0], [1.5, "F", 1.2, -6], [2.75, "O", 0.5, -8],
                      [3.25, "R", 0.6, -4]],
                     [[0, "R", 1.4, 0], [1.5, "F", 1.4, -6], [3.25, "F", 0.5, -4]],
                 ],
                     "slide_in": {"every": 8}, "slide_out": True},
                 "velocity": 70},
        "pad": {"style": "sustain",
                "params": {"voicing": {"profile": "rootfifth"}}, "velocity": 45},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}, "hold": "bar"},
                    "velocity": 30},                     # drone que respira
        "rhodes": {"style": "broken",
                   "params": {"voicing": {"profile": "shell"}, "step": 1.0,
                              "pattern": "up", "ring": 3.0, "rest_prob": 0.30},
                   "velocity": 54},
        "vibraphone": {"style": "replies",
                       "params": {"prob": 0.5, "margin": 0.25, "max_per_bar": 2},
                       "velocity": 50},
        "sax_tenor": {"style": "auto", "lead_auto": True, "params": {},
                      "velocity": 66},
    },
    # ------------------------------------------- pre_chorus (deformación)
    "pre_chorus": {
        "drums": {"style": "pattern",
                  "params": {"vel_scale": 0.95,
                             # (C) capas propias = trip_bridge (motor, styles.py)
                             # + capa de rim en compases impares (deformación: el
                             # ritmo se corroe dentro de la propia sección).
                             "layers": [
                                 {"inst": "kick", "at": [0], "vel": 84,
                                  "offset": -0.006},
                                 {"inst": "rim", "at": [2], "vel": 60,
                                  "offset": 0.037, "when": {"bar_mod": [2, 0]}},
                                 {"inst": "open_hat", "pick": [1.5, 3.5],
                                  "prob": 0.4, "vel_rand": [46, 58], "dur": 0.4},
                                 {"inst": "ride_bell", "at": [0], "vel": 55,
                                  "dur": 0.5, "when": {"bar_mod": [4, 0]}},
                                 {"inst": "rim", "at": [2.5], "vel": 54,
                                  "offset": 0.037, "prob": 0.5,
                                  "when": {"bar_mod": [2, 1]}},
                             ]}},
        "bass": {"style": "pattern",
                 "params": {"patterns": [
                     # (C) compás sonado + compás EN SILENCIO: el groove se retrae
                     [[0, "R", 2.4, 0], [2.5, "F", 1.2, -8]], [],
                 ],
                     "slide_in": {"every": 8}, "slide_out": True},
                 "velocity": 66},
        "pad": {"style": "sustain",
                "params": {"voicing": {"profile": "rootfifth"}}, "velocity": 38},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}}, "velocity": 36},
        "rhodes": {"style": "broken",
                   "params": {"voicing": {"profile": "rootless"}, "step": 1.0,
                              "pattern": "up", "ring": 3.0, "rest_prob": 0.15},
                   "velocity": 56},          # la pulsa se deshace hacia rootless
        "vibraphone": {"style": "replies",
                       "params": {"prob": 0.55, "margin": 0.25, "max_per_bar": 2},
                       "velocity": 46},
        "sax_tenor": {"style": "generative", "lead_auto": True,
                      "params": {"contour": "rising"}, "velocity": 62},
    },
    # ------------------------------------------- chorus (reconstrucción)
    "chorus": {
        "drums": {"style": "pattern",
                  "params": {"vel_scale": 1.1,
                             # (C) capas propias = trip_chorus (motor, styles.py)
                             # + capa de kick en posiciones débiles (beat roto
                             # adicional); fills heavy por §2.6.3.
                             "layers": [
                                 {"inst": "kick", "at": [0, 1.5],
                                  "vel": [100, 84], "offset": -0.006,
                                  "when": {"bar_mod": [2, 0]}},
                                 {"inst": "kick", "at": [0, 2.75],
                                  "vel": [100, 82], "offset": -0.006,
                                  "when": {"bar_mod": [2, 1]}},
                                 {"inst": "snare2", "at": [2], "vel": 96,
                                  "offset": 0.054},
                                 {"inst": "clap", "at": [2], "vel": 80,
                                  "dur": 0.2, "offset": 0.0625},
                                 {"inst": "open_hat", "at": [1.5, 3.5], "vel": 70,
                                  "dur": 0.4, "omit": 0.15, "jitter": 0.02,
                                  "drag": [0.2, 0.037]},
                                 {"inst": "closed_hat", "pick": [0.75, 2.25, 3.25],
                                  "prob": 0.5, "vel_rand": [26, 40],
                                  "jitter": 0.025},
                                 {"inst": "closed_hat", "grid": 0.5,
                                  "vel": [64, 48], "jitter": 0.02,
                                  "drag": [0.2, 0.037], "skip_if_open": True},
                                 {"inst": "ride_bell", "at": [0], "vel": 70,
                                  "dur": 0.5, "when": {"bar_mod": [4, 0]}},
                                 {"inst": "kick", "pick": [2.25, 2.75],
                                  "prob": 0.4, "vel_rand": [44, 56],
                                  "offset": -0.006},
                             ],
                             "fills": [{"when": {"last": True},
                                        "rolls": [{"inst": "snare2", "start": 3.0,
                                                   "steps": 4, "step": 0.25,
                                                   "v0": 62, "v1": 84}]}]}},
        "bass": {"style": "pattern",
                 "params": {"patterns": [
                     [[0, "R", 1.4, 2], [1.5, "F", 0.9, -4], [2.5, "R", 0.4, -8],
                      [3.25, "F", 0.5, -4]],
                     [[0, "R", 1.4, 2], [1.5, "O", 0.9, -6], [3.25, "F", 0.5, -4]],
                 ],
                     "slide_in": {"every": 8}, "slide_out": True},
                 "velocity": 86},
        "pad": {"style": "sustain",
                "params": {"voicing": {"profile": "rootfifth"}}, "velocity": 52,
                "clusters_b3": [DOOM_CLUSTER]},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "spread"}}, "velocity": 52},
        "rhodes": {"style": "broken",
                   "params": {"voicing": {"profile": "shell"}, "step": 1.0,
                              "pattern": "up", "ring": 3.0, "rest_prob": 0.10},
                   "velocity": 68},
        "vibraphone": {"style": "replies",
                       "params": {"prob": 0.35, "margin": 0.25, "glint_gap": 0.9,
                                  "max_per_bar": 2}, "velocity": 60},
        "sax_tenor": {"style": "auto", "lead_auto": True, "params": {},
                      "velocity": 82},
    },
    # ------------------------------------------- bridge (ruptura II)
    "bridge": {
        "drums": {"style": "pattern",
                  "params": {"preset": "trip_bridge", "vel_scale": 0.85,
                             "light_bars": 2, "light_preset": "intro_air"}},
        "bass": {"style": "long",
                 "params": {"center": 38, "fifth_at": 4, "legato": 0.97},
                 "velocity": 50},                     # quinta abierta = drone
        "pad": {"style": "sustain",
                "params": {"voicing": {"profile": "rootfifth"}}, "velocity": 42,
                "clusters_b3": [{"offset": 1, "near": 54, "beat": 2.0, "dur": 2.0,
                                 "vel": 44, "quality": "all",
                                 "when": {"bar_mod": [4, [0, 1]]}}]},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"},
                               "modes": ["bare", "full"]}, "velocity": 45},
        "rhodes": {"style": "hold",
                   "params": {"voicing": {"profile": "rootless"},
                              "restrike_beats": 4}, "velocity": 48},
        "vibraphone": {"style": "pings", "params": {"count": 2, "dur": 6},
                       "velocity": 44, "seed": 307},   # (C) variante controlada
        "sax_tenor": {"style": "hold", "lead_auto": True,
                      "params": {"legato": 1.0}, "velocity": 52},
    },
    # ------------------------------------------- break (ruptura I)
    "break": {
        "drums": {"enabled": False, "style": "none", "params": {}},
        "bass": {"style": "long",
                 "params": {"center": 38, "fifth_at": 0, "legato": 0.97},
                 "velocity": 60},                     # raíz pura, sin quinta
        "pad": {"style": "sustain",
                "params": {"voicing": {"profile": "rootfifth"}}, "velocity": 48,
                "clusters_b3": [DOOM_CLUSTER]},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "rootoctave"}},
                    "velocity": 42},                  # quinta/octava vacía
        "rhodes": {"style": "hold",
                   "params": {"voicing": {"profile": "rootless"},
                              "restrike_beats": 0}, "velocity": 44},
        "vibraphone": {"style": "pings", "params": {"count": 2, "dur": 6},
                       "velocity": 46, "seed": 307},   # (C) campanas aisladas en el
                       # silencio del break; el mecanismo replies (A16) solo produce
                       # notas con el lead AUSENTE (verificado: sobre sax en hold
                       # los huecos no alcanzan glint_gap → 0 notas)
        "sax_tenor": {"style": "hold", "lead_auto": True,
                      "params": {"legato": 1.0}, "velocity": 55},
    },
    # ------------------------------------------- outro (colapso)
    "outro": {
        "drums": {"style": "pattern",
                  "params": {"preset": "intro_air", "vel_scale": 0.7}},
        "bass": {"style": "long", "params": {"center": 38, "legato": 0.97},
                 "velocity": [50, 22]},               # colapso hacia el silencio
        "pad": {"style": "sustain",
                "params": {"voicing": {"profile": "rootfifth"}},
                "velocity": [42, 22]},
        "strings": {"style": "sustain",
                    "params": {"voicing": {"profile": "bare"}},
                    "velocity": [40, 18]},
        "rhodes": {"style": "tail",
                   "params": {"voicing": {"profile": "full"},
                              "notes_per_chord": 2, "ring": 7},
                   "velocity": [50, 18]},
        "vibraphone": {"style": "pings", "params": {"count": 2, "dur": 6},
                       "velocity": [40, 16], "from_bar": 2},
        "sax_tenor": {"style": "hold", "lead_auto": True,
                      "params": {"legato": 1.0}, "velocity": [58, 20]},
    },
}

# --- (C) Progresiones N1 por (language, type): pares (offset sobre la tónica,
# calidad). Calidades dentro del vocabulario §2.4 de cada language. Los OFFSETS
# son el dato Doom: bII frigio (1 st), tritono (6 st), bVI (8 st) sobre menores.
PROGRESIONES = {
    "pop_dream_pop": {
        "intro":      [(0, "m9")],
        "verse":      [(0, "m9"), (1, "maj7"), (8, "maj9"), (7, "7sus4")],
        "pre_chorus": [(5, "maj9"), (7, "7sus4")],
        "chorus":     [(0, "m9"), (8, "maj9"), (10, "m9"), (9, "7sus4")],
        "bridge":     [(6, "add9"), (5, "maj9")],
        "break":      [(0, "m9"), (1, "add9")],
        "outro":      [(0, "add9")],
    },
    "hybrid": {
        "intro":      [(0, "m9")],
        "verse":      [(0, "m11"), (8, "maj7"), (3, "m7b5"), (7, "9")],
        "pre_chorus": [(5, "9"), (7, "13")],
        "chorus":     [(0, "m9"), (10, "m13"), (6, "9"), (7, "7sus4")],
        "bridge":     [(3, "m7b5"), (7, "7#11")],
        "break":      [(0, "m11"), (8, "maj7")],
        "outro":      [(0, "m9")],
    },
    "experimental": {
        "intro":      [(0, "m9")],
        "verse":      [(0, "m11"), (1, "maj9"), (6, "dim7"), (7, "7b9")],
        "pre_chorus": [(5, "m9"), (7, "9")],
        "chorus":     [(0, "m11"), (6, "dim7"), (8, "maj9"), (7, "7#5b9")],
        "bridge":     [(3, "m7b5"), (7, "7b9")],
        "break":      [(0, "m11"), (6, "dim7")],
        "outro":      [(0, "m9")],
    },
}

# --- (B/C) Cluster del pad para pistas pad INICIALIZADAS fuera del set base
# (§2.5.1; el compilador lo usa si el compositor habilita el pad con tension B3).
PAD_TENSION_CLUSTER = DOOM_CLUSTER
