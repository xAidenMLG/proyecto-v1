"""RECETA N1 REAL — identidad ``dark_triphop`` (§2.3 rev. 3.1, nivel N1).

Esta es la PRIMERA receta real del proyecto (instrucción 09, alcance Fase 1).
Declara la base sonora completa que el compilador expande por tipo de sección.
Todo valor está fundamentado en una de estas tres fuentes, citadas por dato:

  A. Contrato ``dark-director/1`` rev. 3.2 (tablas §2.6.2 energy, §2.6.3 drums,
     §2.6.4 focus, §2.6.5 density/D_receta, §2.6.6 tension, §2.11 guardrails).
  B. Parámetros REALES existentes de MIDI Forge: presets de batería
     ``intro_air / trip_bridge / trip_verse / trip_chorus`` y sets de bajo
     ``trip_long / trip_two_bars / trip_chorus / whole`` (``styles.DRUM_PRESETS``
     y ``styles.BASS_SETS``), rangos y velocidades del bloque trip-hop del
     propio motor (``styles.default_block`` rama ``_triphop``) y vocabulario de
     perfiles de ``voicing.PROFILES``. El compilador NUNCA añade parámetros
     nuevos al motor (§2.5.1).
  C. Decisión de receta documentada (valores propios de N1, etiquetados):
     D_receta/energy/tension/focus por tipo, rango típico de BPM y las
     progresiones por (language, type) instanciables en la tonalidad del
     proyecto. Son DATO DE RECETA: el compositor no los escribe y el contrato
     los exige en N1 («siempre existe una progresión para cada
     (type, language): las recetas están validadas por pares», §2.8).

Las progresiones N1 se declaran como pares (offset en semitonos sobre la
tónica, sufijo de calidad). Las calidades usan EXCLUSIVAMENTE el vocabulario
de §2.4 del language correspondiente (pop_dream_pop / hybrid / experimental);
la instancia final se emite con la tónica real de ``harmony.key``.
"""

IDENTITY = "dark_triphop"

# --- (C) Base sonora: pistas que suenan sin `active` ni `enabled` explícitos.
# §5.0.1 de rev. 3.1 declaraba este set como supuesto provisional de receta;
# como receta N1 real pasa a ser el dato que gobierna la identidad.
SET_BASE = ("sax_tenor", "rhodes", "vibraphone", "bass", "drums", "pad")
LEAD = "sax_tenor"

# --- (C) BPM y ritmo armónico (defaults N1; §3.1/§3.2: default = receta)
BPM_DEFAULT = 86
BPM_RANGO_TIPICO = (70, 96)          # W401: fuera de este rango → recomendación
HARMONIC_RHYTHM_BARS = 1

# --- (C) Registro por defecto por instrumento (solo pistas base de esta
# identidad; el lead usa el rango dark del propio motor: [62, 81]).
REGISTER_DEFAULT = {
    "sax_tenor": [62, 81],           # motor: bloque lead triphop `range: [62, 81]`
    "rhodes": [45, 76],              # motor: ROLE_DEFAULTS["keys"]["range"]
    "vibraphone": [60, 88],          # motor: ROLE_DEFAULTS["mallet"]["range"]
    "bass": [28, 52],                # motor: ROLE_DEFAULTS["bass"]["range"]
    "pad": [40, 72],                 # motor: ROLE_DEFAULTS["pad"]["range"]
}

# --- (C) D_receta(type): density BASE por tipo de sección (§2.6.5). Valores de
# receta (fuente única de la fórmula de coexistencia; nunca se infiere del JSON
# del compositor). Compatibilidad verificada: con esta tabla, los avisos
# documentados de los 3 ejemplos del contrato se recomputan exactos (rev. 3.1,
# propiedad 6 + barrido de invarianza).
D_RECETA = {
    "intro": 0.25,
    "verse": 0.45,
    "pre_chorus": 0.55,
    "chorus": 0.65,
    "bridge": 0.55,
    "break": 0.35,
    "outro": 0.20,
}

# --- (C) energy / tension / drums / focus por defecto por tipo (§3.4:
# default = receta por type). Los valores son coherentes con la semántica de
# §2.6 (intro/outro suaves, verse/chorus plenos).
ENERGY_BASE = {
    "intro": 0.25, "verse": 0.45, "pre_chorus": 0.60, "chorus": 0.80,
    "bridge": 0.55, "break": 0.35, "outro": 0.20,
}
TENSION_BASE = {
    "intro": 0.20, "verse": 0.35, "pre_chorus": 0.55, "chorus": 0.50,
    "bridge": 0.60, "break": 0.60, "outro": 0.15,
}
DRUMS_NIVEL = {
    "intro": "air", "verse": "groove", "pre_chorus": "light", "chorus": "heavy",
    "bridge": "light", "break": "light", "outro": "air",
}
FOCUS_DEFAULT = {
    "intro": ["rhodes", "pad"],
    "verse": ["sax_tenor", "drums"],
    "pre_chorus": ["pad", "vibraphone"],
    "chorus": ["sax_tenor", "drums", "bass"],
    "bridge": ["rhodes", "vibraphone"],
    "break": ["vibraphone"],
    "outro": ["rhodes"],
}

# --- (B) Escalera de drums §2.6.3 → presets REALES de styles.DRUM_PRESETS.
# off → bloque silencioso; air → crash + hats decaídos (intro_air);
# light → kick + rim + open hats (trip_bridge); groove → beat roto (trip_verse);
# heavy → beat denso (trip_chorus). vel_scale = tabla contractual §2.6.3.
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
# §2.6.3 heavy: «trip_chorus + fills» — el preset real trip_chorus trae
# fills: [], así que la receta declara el fill (mecanismo `fills`/`rolls`
# existente del motor, vocabulario de snare2 del propio trip-hop).
DRUMS_FILLS_HEAVY = [
    {"when": {"last": True},
     "rolls": [{"inst": "snare2", "start": 3.0, "steps": 4, "step": 0.25,
                "v0": 62, "v1": 84}]},
]

# --- (B) Patrones de bajo por tipo (§2.3 N1 «sets de bajo»). Declarados como
# datos explícitos de la receta (mecanismo real `params.patterns` del motor,
# tokens R/F/O/T/S/A de gen_bass), con las FORMAS de los sets trip_* reales de
# ``styles.BASS_SETS`` (trip_long / trip_two_bars / trip_chorus / whole) y la
# ÚLTIMA nota movida a pos 3.25 (dur 0.5): el gesto approach del motor
# (engine.gen_bass) solo puede dispararse con la última nota del patrón en
# pos >= bb − 0.75, y los sets originales terminan antes (3.0 / 2.75 / 0).
# El compilador fija `approach.every = 2` y `approach.offset = (bars−1) % 2`
# para que el gesto cromático caiga SIEMPRE también en el compás final.
BASS_PATRONES = {
    "intro": None,                      # sin bajo (motor trip-hop: intro sin bass)
    "verse": [                          # forma trip_long (BASS_SETS)
        [[0, "R", 1.4, 0], [1.5, "F", 1.4, -6], [3.25, "R", 0.5, -4]],
        [[0, "R", 1.4, 0], [1.5, "F", 1.4, -6], [3.25, "F", 0.5, -4]],
    ],
    "pre_chorus": [[[0, "R", 3.3, 0], [3.4, "R", 0.45, -10]]],   # forma trip_two_bars
    "chorus": [                         # forma trip_chorus (BASS_SETS)
        [[0, "R", 1.4, 2], [1.5, "F", 0.9, -4], [2.5, "R", 0.4, -8], [3.25, "F", 0.5, -4]],
        [[0, "R", 1.4, 2], [1.5, "O", 0.9, -6], [3.25, "F", 0.5, -4]],
    ],
    "bridge": [[[0, "R", 3.3, 0], [3.4, "R", 0.45, -10]]],       # bridge replica pre
    "break": [                          # forma trip_long
        [[0, "R", 1.4, 0], [1.5, "F", 1.4, -6], [3.25, "R", 0.5, -4]],
        [[0, "R", 1.4, 0], [1.5, "F", 1.4, -6], [3.25, "F", 0.5, -4]],
    ],
    "outro": [[[0, "R", 3.9, 0]]],      # forma whole
}
# Velocidad base del bajo por tipo (velocidades del bloque trip-hop real del
# motor: verse 70, pre 66, chorus 86, break 70, outro rampa [60, 22]; intro
# sin bajo). Los deltas de focus se aplican sobre este valor.
BASS_VELOCITY = {
    "intro": None, "verse": 70, "pre_chorus": 66, "chorus": 86,
    "bridge": 66, "break": 70, "outro": 60,
}

# --- (B) Keys (rhodes, programa 4): estilo real por tipo según el bloque
# trip-hop del motor (intro/outro hold/tail, verse/break broken, pre/bridge hold).
KEYS_ESTILO = {
    "intro": "hold", "verse": "broken", "pre_chorus": "hold",
    "chorus": "broken", "bridge": "hold", "break": "broken", "outro": "tail",
}
KEYS_VELOCITY = {
    "intro": 50, "verse": 56, "pre_chorus": 52, "chorus": 70,
    "bridge": 52, "break": 56, "outro": 56,
}

# --- (B) Mallet (vibráfono, programa 11): pings en intro/outro, replies en el
# resto (motor triphop). prob/max_per_bar y count NO se fijan aquí: los fija la
# banda de density efectiva (§2.6.5).
MALLET_ESTILO = {
    "intro": "pings", "verse": "replies", "pre_chorus": "replies",
    "chorus": "replies", "bridge": "replies", "break": "replies", "outro": "pings",
}
MALLET_VELOCITY = {
    "intro": 44, "verse": 50, "pre_chorus": 46, "chorus": 62,
    "bridge": 46, "break": 48, "outro": 44,
}

# --- (B) Pad: sustain con voicing rootfifth (motor triphop); la automatización
# CC11 de swells queda reservada a recetas en v1 (§11, fila automation).
PAD_VELOCITY = {
    "intro": 45, "verse": 47, "pre_chorus": 40, "chorus": 58,
    "bridge": 40, "break": 45, "outro": 47,
}
# (C) Cluster determinista para tension B3 (§2.6.6: `pad.tension` si pad
# activo). Usa el mecanismo real `tension` del pad (engine.gen_chordal):
# nota a offset=1 semitono sobre el root de cada acorde menor, anclada cerca
# del registro medio del pad, beat 2, 1.5 beats, vel 48, en compases 0/1 de
# cada ciclo de 4 (cuando `bar_mod`). Es DATO DE RECETA.
PAD_TENSION_CLUSTER = {
    "offset": 1, "near": 56, "beat": 2.0, "dur": 1.5, "vel": 48,
    "quality": "minor", "when": {"bar_mod": [4, [0, 1]]},
}

# --- (B) Lead (sax, programa 66): sin lead en intro; hold en outro; auto
# (frases si existen, si no generativo) en el resto — motor triphop.
LEAD_VELOCITY = {
    "intro": None, "verse": 68, "pre_chorus": 62, "chorus": 84,
    "bridge": 62, "break": 66, "outro": [60, 20],
}
LEAD_GENERATIVO = {"long_prob": 0.9, "motif_bars": 4}   # motor triphop (density lo fija la banda)

# --- (C) Progresiones N1 por (language, type): pares (offset sobre la tónica,
# calidad). Calidades dentro del vocabulario §2.4 del language. El compilador
# instancia la tónica real de harmony.key (ortografía con bemoles, coherente
# con los ejemplos del contrato en tonalidades menores).
PROGRESIONES = {
    "pop_dream_pop": {
        "intro":      [(0, "m9")],
        "verse":      [(0, "m9"), (8, "maj7"), (5, "maj9"), (7, "7sus4")],
        "pre_chorus": [(5, "maj9"), (7, "7sus4")],
        "chorus":     [(8, "maj9"), (5, "maj9"), (10, "m9"), (9, "7sus4")],
        "bridge":     [(10, "maj7"), (5, "maj9")],
        "break":      [(0, "m9"), (8, "maj7")],
        "outro":      [(0, "add9")],
    },
    "hybrid": {
        "intro":      [(0, "m9")],
        "verse":      [(0, "m9"), (8, "maj7"), (3, "m7b5"), (7, "9")],
        "pre_chorus": [(5, "9"), (7, "13")],
        "chorus":     [(0, "m9"), (10, "m9"), (8, "13"), (7, "7sus4")],
        "bridge":     [(3, "m7b5"), (7, "7#11")],
        "break":      [(0, "m11"), (8, "maj7")],
        "outro":      [(0, "m9")],
    },
    "experimental": {
        "intro":      [(0, "m9")],
        "verse":      [(0, "m11"), (8, "maj9"), (3, "m7b5"), (7, "7b9")],
        "pre_chorus": [(5, "m9"), (7, "9")],
        "chorus":     [(0, "m11"), (8, "maj9"), (6, "dim7"), (7, "7#5b9")],
        "bridge":     [(3, "m7b5"), (7, "7b9")],
        "break":      [(0, "m11"), (6, "dim7")],
        "outro":      [(0, "m9")],
    },
}
