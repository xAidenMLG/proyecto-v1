"""Datos y funciones puras del contrato ``dark-director/1`` (Fase 0).

Fuente de verdad: chain documental rev. 3 + rev. 3.1 + rev. 3.2
(``respuesta_03``, ``respuesta_04``, ``respuesta_05``). Cada bloque cita su
sección. Aquí NO hay traducción musical, ni generación, ni validador E1xx
completo (eso es el compilador, Fase 1): solo el dato de contrato que la
suite de pruebas de contrato debe verificar.
"""

# ---------------------------------------------------------------------------
# Versiones (alcance D de Fase 0)
# ---------------------------------------------------------------------------

CONTRACT_ID = "dark-director/1"      # §3.3: literal del campo `schema` (E102)
CONTRACT_REV = "3.2"                 # rev. 3.2 (respuesta_05)
TARGET_SCHEMA = "midi-forge/1"       # §3.3: proyecto emitido; el original viaja en meta.director
COMPILER_VERSION = "0.1.0"           # versión del compilador (dark_director/compilador.py)
COMPILER_STAGE = "fase1"             # etapa del roadmap (auditoría §7)

_VERSION_KEYS = ("contract", "contract_rev", "compiler_version", "compiler_stage", "target_schema")


def contract_info():
    """Mecanismo de identificación de versiones (alcance D)."""
    return {
        "contract": CONTRACT_ID,
        "contract_rev": CONTRACT_REV,
        "compiler_version": COMPILER_VERSION,
        "compiler_stage": COMPILER_STAGE,
        "target_schema": TARGET_SCHEMA,
    }


def build_director_meta(x_fields=None):
    """Construye la zona de anotaciones ``meta.director`` del proyecto emitido.

    El contrato (§3.3, fila ``schema``; nota de campos ``x_*``) establece que el
    proyecto emitido lleva ``schema="midi-forge/1"`` y conserva el original y las
    extensiones ``x_*`` incrustados en ``meta.director`` (roundtrip verificado por
    la auditoría). Fase 0 define aquí el formato de esa zona: versiones del
    contrato/compilador + extensiones ``x_*`` del compositor. Las claves de
    versión están reservadas: una colisión es error explícito, no silencio.
    """
    meta = contract_info()
    if x_fields:
        for k, v in x_fields.items():
            if k in _VERSION_KEYS:
                raise ValueError(f"colisión con clave reservada de versión: {k!r}")
            if not es_campo_extension(k):
                raise ValueError(f"solo se incrustan extensiones con prefijo x_: {k!r}")
            meta[k] = v
    return meta


# ---------------------------------------------------------------------------
# Catálogo cerrado (§2.5, párrafo inicial — texto de rev. 3.1 §2.2)
# ---------------------------------------------------------------------------

INSTRUMENT_IDS = ("sax_tenor", "rhodes", "vibraphone", "bass", "drums", "piano", "pad", "strings")
SECTION_TYPES = ("intro", "verse", "pre_chorus", "chorus", "bridge", "break", "outro")  # 7 types
DRUMS_LADDER = ("off", "air", "light", "groove", "heavy")  # §2.6.3: off→air→light→groove→heavy
IDENTITIES = ("dark_triphop", "doom_triphop", "doom_dark_jazz")
ACCESSIBILITIES = ("commercial", "balanced", "experimental")
LANGUAGES = ("pop_dream_pop", "hybrid", "experimental")
RESOLUTIONS = ("tonal", "modal", "deceptive", "chromatic", "open")  # §2.4/§2.4.1: 5 valores; defaults por language (pop→tonal, hybrid→modal, experimental→chromatic)

# 3 identidades × 3 accesibilidades × 3 lenguajes = 27 combinaciones, todas válidas
# (§2.1: sin E2xx bloqueante para combinaciones).
TOTAL_COMBINACIONES = 27

# Sets base por identidad — **SUPUESTO PROVISIONAL de datos de receta** (§5.0.1 de
# rev. 3.1). NO son valores del motor: el set base real lo fija la receta N1 en
# Fase 1 (dark_director/identities/<id>.py). Van etiquetados para que ningún
# consumidor los trate como dato definitivo.
BASE_SETS_SUPUESTO_PROVISIONAL = {
    "dark_triphop": ("sax_tenor", "rhodes", "vibraphone", "bass", "drums", "pad"),
    "doom_triphop": ("sax_tenor", "rhodes", "vibraphone", "bass", "drums", "pad", "strings"),
    # §5.0.1: doom_dark_jazz con piano y strings; pad OFF
    "doom_dark_jazz": ("sax_tenor", "rhodes", "vibraphone", "bass", "drums", "piano", "strings"),
}

# ---------------------------------------------------------------------------
# Bandas de density — definición única y cerrada de la rev. 3.2 (§2.6.5)
# ---------------------------------------------------------------------------

BAND_B1_MAX = 0.33   # B1: density <= 0.33
BAND_B3_MIN = 0.67   # B3: density >= 0.67
BAND_CONDITIONS = {
    "B1": "density <= 0.33",
    "B2": "0.33 < density < 0.67",
    "B3": "density >= 0.67",
}
_TOL_DOMINIO = 1e-9  # tolerancia de dominio para flotantes derivados del clamp


def density_band(v):
    """Banda de density (rev. 3.2): partición cerrada de [0.0, 1.0] sin huecos
    ni solapamientos. Comparación sobre el valor declarado, sin redondeo previo
    (la cuantización es la propia bandificación, propiedad 5 de §2.6.5).
    Fuera de [0.0, 1.0] es un valor inválido del contrato (§3.4): error explícito.
    """
    x = float(v)
    if x < 0.0 - _TOL_DOMINIO or x > 1.0 + _TOL_DOMINIO:
        raise ValueError(f"density fuera del dominio [0.0, 1.0]: {v!r}")
    if x <= BAND_B1_MAX:
        return "B1"
    if x < BAND_B3_MIN:
        return "B2"
    return "B3"


# ---------------------------------------------------------------------------
# Fórmula de coexistencia de density (§2.6.5 — texto de rev. 3.1 §2.4)
# ---------------------------------------------------------------------------

def density_efectiva(d_inst, d_secc, d_receta):
    """``density_efectiva(i, S)`` según §2.6.5 (rev. 3.1).

    d_inst    : density declarada en instruments.<i>.density, o None
    d_secc    : density declarada en structure[S].density, o None
    d_receta  : default de density que la RECETA de identidad declara para el
                type de S (dato N1; nunca se infiere del JSON del compositor)

    desv(S)    = 0                       si S no declara density
                 d_secc - d_receta       si S la declara
    base(i,S)  = d_inst                  si i la declara
                 d_receta                si no
    efectiva   = clamp(base + desv, 0.0, 1.0)

    Propiedades contractuales (verificadas por la suite de Fase 0):
      1. solo sección declarada   → efectiva == d_secc exacta (la base se cancela)
      2. solo instrumento         → efectiva == d_inst en todas las secciones
      3. ambas                    → evolución musical conservada sobre la base
      6. invarianza de avisos respecto a D_receta cuando no hay D_inst
    """
    desv = 0.0 if d_secc is None else (d_secc - d_receta)
    base = d_inst if d_inst is not None else d_receta
    return max(0.0, min(1.0, base + desv))


# ---------------------------------------------------------------------------
# Registro de códigos E/W (rev. 3 §4 + fila E114 de rev. 3.1 §2.5)
# ---------------------------------------------------------------------------
# (código) -> (familia, resumen contractual de una línea). Un código = un significado.

EW_CODES = {
    "E101": ("E1xx", "JSON malformado o raíz no-objeto"),
    "E102": ("E1xx", "schema ausente o != 'dark-director/1'"),
    "E103": ("E1xx", "campo requerido ausente (direction.identity, direction.accessibility, harmony.key, harmony.language, structure)"),
    "E104": ("E1xx", "tipo incorrecto en cualquier campo"),
    "E105": ("E1xx", "valor fuera de rango o fuera de enum"),
    "E106": ("E1xx", "exclusivamente structure inválida: < 2 secciones o ids duplicados"),
    "E107": ("E1xx", "referencia rota a sección inexistente"),
    "E108": ("E1xx", "motif con fuente sin frases"),
    "E109": ("E1xx", "campo desconocido sin prefijo x_ (en cualquier nivel, con sugerencia del campo más cercano)"),
    "E110": ("E1xx", "id de instrumento fuera del catálogo de 8"),
    "E111": ("E1xx", "nota de frase inválida (bar, beat en [0, 4), fin de sección, pitch, dur, vel)"),
    "E112": ("E1xx", "ending inválido (bars no entero, < 1 o mayor que la última sección)"),
    "E113": ("E1xx", "símbolo de acorde no parseable por theory.parse_chord"),
    "E114": ("E1xx", "pista enabled=true fuera del set base que no puede inicializarse con seguridad; no se emite pista parcial ni bloque incompleto"),
    "E203": ("E2xx", "improvisación en una sección cuyo active excluye explícitamente al instrumento"),
    "E204": ("E2xx", "desarrollo sobre pista que no suena"),
    "E301": ("E3xx", "improvisation[].instrument != sax_tenor"),
    "E302": ("E3xx", "responses.<inst>.responds_to apunta a un instrumento que no es el lead"),
    "E303": ("E3xx", "responses declarado sobre un instrumento sin mecanismo replies"),
    "W401": ("W4xx", "BPM fuera del rango típico de la identidad (se compila igual)"),
    "W402": ("W4xx", "ritmo armónico 1:1 en doom_dark_jazz"),
    "W403": ("W4xx", "vibráfono con density efectiva en banda B3 y mallet_sparse ON"),
    "W404": ("W4xx", "commercial sin material de hook en ningún chorus"),
    "W405": ("W4xx", "velocity_cap > 110 en identidades doom"),
    "W406": ("W4xx", "active/focus referencia un instrumento que no suena en la sección → entrada ignorada"),
    "W407": ("W4xx", "material del motif más largo que la sección destino (N notas truncadas)"),
    "W408": ("W4xx", "motif_repeat con motifs de loop_bars != 8"),
    "W409": ("W4xx", "tension en banda B3 sin pad ni strings activos"),
    "W410": ("W4xx", "density sin traducción (bass/drums/pad/strings; sax en bloques escritos) → ignorada donde no aplica"),
    "W411": ("W4xx", "combinación identidad×accessibility×language poco convencional (9/27; informativa)"),
    "W412": ("W4xx", "resolution explícita en la última sección"),
    "W413": ("W4xx", "transpose_st deja notas fuera del registro del lead"),
    "W414": ("W4xx", "acordes explícitos fuera del vocabulario del language (se respetan)"),
    "W415": ("W4xx", "final: true en más de una sección (gana la última en orden)"),
    "W416": ("W4xx", "fade_out y tape_stop ambos activos"),
    "W417": ("W4xx", "chord_bars/harmonic_rhythm_bars no divide los compases de la sección"),
    "W418": ("W4xx", "improvisación en sección con drums: off"),
    "W419": ("W4xx", "loop_bars de motif mayor que los compases del destino"),
    "W420": ("W4xx", "resolución con split (tonal/deceptive) en transición con origen < 2 compases (split omitido)"),
    "W421": ("W4xx", "transición con gesto de bajo imposible (bass inactivo en el origen)"),
}

RETIRED_CODES = {
    "E201": "RETIRADO (rev. 1/borradores). No se reasigna: las combinaciones son válidas (§2.1) y el motif sin material es E108",
    "E202": "RETIRADO (rev. 1/borradores). No se reasigna: la improvisación contra whitelist es E203",
}

FAMILIAS = {
    "E1xx": ("estructural", True),        # bloquea
    "E2xx": ("contradicción", True),      # bloquea
    "E3xx": ("capacidad no soportada", True),
    "W4xx": ("recomendación", False),     # nunca bloquea, nunca cambia valores
}

TOTAL_CODIGOS_ACTIVOS = 40  # 14 E1xx + 2 E2xx + 3 E3xx + 21 W4xx (rev. 3.1 §2.8)


def codigos_activos():
    """Códigos activos ordenados (40: E101–E114, E203–E204, E301–E303, W401–W421)."""
    return tuple(sorted(EW_CODES))


# ---------------------------------------------------------------------------
# Campos de extensión x_* (§3 nota; fila x_* de §3.3; E109)
# ---------------------------------------------------------------------------

def es_campo_extension(nombre):
    """True si el nombre de campo lleva el prefijo de extensión del compositor.
    El prefijo ``x_`` es el único mecanismo de extensión: todo campo desconocido
    sin prefijo es E109 (§4). ``x_`` a secas no es un campo con nombre."""
    return isinstance(nombre, str) and nombre.startswith("x_") and len(nombre) > 2


def separar_x_fields(d):
    """Separa (nivel a nivel) los campos ``x_*`` del resto de un objeto del JSON
    del compositor. Los ``x_*`` viajan incrustados en ``meta.director`` del
    proyecto emitido (roundtrip verificado por la auditoría) y nunca afectan a
    la música. Preserva el orden de inserción. La validación por nivel (E109)
    es tarea del validador del compilador (Fase 1)."""
    extras = {}
    resto = {}
    for k, v in d.items():
        (extras if es_campo_extension(k) else resto)[k] = v
    return extras, resto
