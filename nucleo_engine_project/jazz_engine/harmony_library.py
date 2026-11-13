"""Harmonic Familiarity Library — FASE 7.

Biblioteca de progresiones armónicas FAMILIARES (arquetipos recurrentes de la
música popular) expresadas en GRADOS FUNCIONALES (numerales romanos), nunca en
melodías, riffs ni material protegido de canciones concretas. Las progresiones
comunes son referencias de diseño, no instrucciones para reconstruir canciones.

Separación estricta de responsabilidades (misión FASE 7 §8):
  - ESTE módulo   : datos + validación del esquema (biblioteca).
  - harmony_select: búsqueda/selección (keyword → progresión por tipo).
  - harmony_adapt : adaptación (grados → tonalidad/modo reales + variaciones).

Esquema de entrada (mínimo de la misión §3, más campos operativos):
  id                único, estable, MAYÚSCULAS_CON_GUION (p.ej. "CINE01").
  nombre            descriptivo, en español.
  keywords          lista de keywords de búsqueda.
  familia           una de FAMILIAS.
  funcion           etiqueta de función armónica (texto libre corto).
  modo              "mayor" | "menor"  (clase modal de la progresión).
  grados            secuencia de tokens de grado (ver _GRADO_RE).
  emociones         lista corta de características emocionales.
  familiaridad      0..1 (arquetipo 1.0 → variación original ~0.4).
  tension           0..1.
  resolucion        0..1 (capacidad de resolución del final del ciclo).
  estructura        tipos de sección compatibles (contract.SECTION_TYPES).
  variaciones       subconjunto de VOCABULARIO_VARIACIONES disponibles.
  ritmo             ritmo armónico sugerido en compases por acorde (1 o 2).
  referencias       texto honesto: qué está documentado y qué es diseño propio.
  tipo_ref          "arquetipo_documentado" | "arquetipo_genero" |
                    "variacion_original".

Gramática de grado (token):
  [b#]? NUMERAL [sufijo] [/ NUMERAL]
  - NUMERAL en mayúsculas o minúsculas (caso = calidad base: mayor/menor).
  - sufijos válidos (SUFIJOS): triada vacía, 7 9 11 13 6, maj7 maj9, sus4 sus2,
    add9 add2, dim dim7 m7b5 aug 5. Restricciones por caso (ver validar_grado).
  - "/3" "/5" "/7" → bajo en esa nota del acorde (inversión; teoría de forge).

Extensión SIN tocar el motor: ``biblioteca(extra)`` acepta progresiones de un
JSON externo con el mismo esquema (ver docs/HARMONIA_BIBLIOTECA.md); el motor
de selección y el de adaptación consumen la biblioteca validada, no datos
incrustados.
"""
import copy
import re

FAMILIAS = ("familiaridad_pop", "melancolia_nostalgia", "oscuridad_cinematografica",
            "dream_pop_alternative", "soul_rnb", "balada_cinematica")

TIPOS_ESTRUCTURA = ("intro", "verse", "pre_chorus", "chorus", "bridge", "break", "outro")

#: Vocabulario CERRADO de variaciones que harmony_adapt sabe aplicar. Una
#: entrada solo puede pedir variaciones de esta lista (validación).
VOCABULARIO_VARIACIONES = (
    "extensiones",              # colores de séptima/9a según familia
    "sus_flavor",               # V → Vsus4 / V7 → V7sus4
    "inversion_paso",           # inversión con bajo escalerado al acorde siguiente
    "sustitucion_diatonica",    # sustituto funcional interno (I↔vi, IV↔ii, V↔vii°)
    "dominante_secundaria",     # cola: V7/x aproximando la sección siguiente
    "acorde_paso",              # cola: aproximación diatónica por grado conjunto
    "intercambio_modal",        # préstamo modal controlado (iv en mayor, IV en menor)
    "resolucion_deceptiva",     # final de sección: V→vi (mayor) / V→VI (menor)
    "colas_extra",              # completar/girar el ciclo para cerrar la sección
)

NIVELES_VARIACION = ("none", "subtle", "medium", "rich")

_GRADO_RE = re.compile(
    r"^(?P<acc>[b#])?(?P<rom>III|IV|VII|VI|V|II|I|iii|iv|vii|vi|v|ii|i)"
    r"(?P<suf>[a-z0-9#b]*)?(?:/(?P<sl>[b#]?(?:III|IV|VII|VI|V|II|I|iii|iv|vii|vi|v|ii|i)"
    r"(?:[a-z0-9#b]*)?))?$")

SUFIJOS = ("", "7", "9", "11", "13", "6", "maj7", "maj9", "sus4", "sus2",
           "add9", "add2", "dim", "dim7", "m7b5", "aug", "5", "7sus4")

ROMAN_INDEX = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}

_CAMPOS_REQUERIDOS = ("id", "nombre", "keywords", "familia", "funcion", "modo",
                      "grados", "emociones", "familiaridad", "tension", "resolucion",
                      "estructura", "variaciones", "ritmo", "referencias", "tipo_ref")
_TIPOS_REF = ("arquetipo_documentado", "arquetipo_genero", "variacion_original")


def validar_grado(tok):
    """Valida un token de grado. Devuelve (romano, accidental, sufijo, slash)
    o lanza ValueError con mensaje claro. El slash se valida recursivamente."""
    m = _GRADO_RE.match(tok)
    if not m:
        raise ValueError("token de grado no reconocido: %r (gramática: [b#]?NUMERAL"
                         "[sufijo][/NUMERAL]; numerales I–VII en un solo caso)" % (tok,))
    acc, rom, suf, sl = m.group("acc") or "", m.group("rom"), m.group("suf") or "", m.group("sl")
    if suf not in SUFIJOS:
        raise ValueError("sufijo no soportado en %r (válidos: %s)" % (tok, " ".join(SUFIJOS)))
    if rom.isupper() and suf in ("dim", "dim7", "m7b5"):
        raise ValueError("sufijo %r exige numeral minúscula: %r" % (suf, tok))
    if rom.islower() and suf in ("maj9", "aug"):
        raise ValueError("sufijo %r no combinable con numeral minúscula: %r" % (suf, tok))
    if sl is not None and sl not in ("3", "5", "7"):
        raise ValueError("inversión /N solo admite 3, 5 o 7 (nota del acorde): %r" % (tok,))
    return rom, acc, suf, sl


def validar_entrada(e):
    """Valida el esquema de una progresión. Devuelve la entrada normalizada
    (copia) o lanza ValueError. Sin melodías: solo grados funcionales."""
    faltan = [c for c in _CAMPOS_REQUERIDOS if c not in e]
    if faltan:
        raise ValueError("progresión sin campos %s: %r" % (", ".join(faltan), e.get("id")))
    eid = e["id"]
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,15}", str(eid)):
        raise ValueError("id inválido %r (MAYÚSCULAS_CON_GUION, 2-16 caracteres)" % (eid,))
    if e["familia"] not in FAMILIAS:
        raise ValueError("familia desconocida en %s: %r" % (eid, e["familia"]))
    if e["modo"] not in ("mayor", "menor"):
        raise ValueError("modo debe ser mayor|menor en %s: %r" % (eid, e["modo"]))
    if not isinstance(e["grados"], (list, tuple)) or not (2 <= len(e["grados"]) <= 8):
        raise ValueError("grados debe ser una lista de 2 a 8 tokens en %s" % (eid,))
    for tok in e["grados"]:
        try:
            validar_grado(str(tok))
        except ValueError as exc:
            raise ValueError("%s: %s" % (eid, exc))
    if not isinstance(e["keywords"], (list, tuple)) or not e["keywords"]:
        raise ValueError("keywords vacías en %s" % (eid,))
    for k in e["keywords"]:
        if not re.fullmatch(r"[a-z0-9_]{2,32}", str(k)):
            raise ValueError("keyword inválida %r en %s (a-z0-9_)" % (k, eid))
    for campo in ("familiaridad", "tension", "resolucion"):
        v = e[campo]
        if not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
            raise ValueError("%s debe estar en [0,1] en %s: %r" % (campo, eid, v))
    desconocidas = [v for v in e["variaciones"] if v not in VOCABULARIO_VARIACIONES]
    if desconocidas:
        raise ValueError("variaciones fuera de vocabulario en %s: %s (válidas: %s)"
                         % (eid, ", ".join(desconocidas), ", ".join(VOCABULARIO_VARIACIONES)))
    mal_estructura = [t for t in e["estructura"] if t not in TIPOS_ESTRUCTURA]
    if mal_estructura or not e["estructura"]:
        raise ValueError("estructura vacía o con tipos desconocidos en %s: %s"
                         % (eid, mal_estructura))
    if e["ritmo"] not in (1, 2):
        raise ValueError("ritmo debe ser 1 o 2 en %s (compases por acorde)" % (eid,))
    if e["tipo_ref"] not in _TIPOS_REF:
        raise ValueError("tipo_ref inválido en %s: %r" % (eid, e["tipo_ref"]))
    if not str(e["referencias"]).strip():
        raise ValueError("referencias vacías en %s (documentación honesta obligatoria)" % (eid,))
    out = copy.deepcopy(dict(e))
    out["grados"] = [str(t) for t in e["grados"]]
    out["keywords"] = [str(k) for k in e["keywords"]]
    out["estructura"] = list(e["estructura"])
    out["variaciones"] = list(e["variaciones"])
    out["emociones"] = list(e["emociones"])
    return out


def _e(id_, nombre, keywords, familia, funcion, modo, grados, emociones, familiaridad,
       tension, resolucion, estructura, variaciones, ritmo, referencias, tipo_ref):
    return {"id": id_, "nombre": nombre, "keywords": keywords, "familia": familia,
            "funcion": funcion, "modo": modo, "grados": grados, "emociones": emociones,
            "familiaridad": familiaridad, "tension": tension, "resolucion": resolucion,
            "estructura": estructura, "variaciones": variaciones, "ritmo": ritmo,
            "referencias": referencias, "tipo_ref": tipo_ref}


#: Biblioteca integrada. 44 progresiones: las listadas en la misión §4 más
#: arquetipos frecuentes y variaciones originales derivadas. Sin melodías,
#: riffs ni atribuciones dudosas a canciones concretas.
_BIBLIOTECA_BASE = [
    # ---------------- familiaridad_pop ----------------
    _e("POP01", "Eje Pop", ["familiar_pop", "pop", "eje"], "familiaridad_pop",
       "tónica–dominante–relativa–subdominante", "mayor", ["I", "V", "vi", "IV"],
       ["directo", "reconocible", "optimista contenido"], 1.0, 0.35, 0.7,
       ["verse", "pre_chorus", "chorus", "outro"],
       ["extensiones", "sus_flavor", "sustitucion_diatonica", "colas_extra"], 1,
       "El arquetipo armónico dominante del pop de las últimas décadas (I–V–vi–IV "
       "y sus rotaciones); documentado ampliamente en análisis armónicos públicos "
       "de música popular.", "arquetipo_documentado"),
    _e("POP02", "Rotación del Eje", ["familiar_pop", "pop", "rotacion"], "familiaridad_pop",
       "relativa–subdominante–tónica–dominante", "mayor", ["vi", "IV", "I", "V"],
       ["nostálgico", "impulso continuo"], 1.0, 0.4, 0.6,
       ["verse", "pre_chorus", "chorus", "bridge"],
       ["extensiones", "sus_flavor", "colas_extra"], 1,
       "La misma rotación del eje pop (vi–IV–I–V); arquetipo documentado, arranca "
       "en la relativa menor y por eso tiñe de melancolía.", "arquetipo_documentado"),
    _e("POP03", "Cadencia Doo Wop", ["familiar_pop", "doo_wop", "soulful"], "familiaridad_pop",
       "círculo I–vi–IV–V", "mayor", ["I", "vi", "IV", "V"],
       ["tierno", "retro", "candor"], 0.95, 0.4, 0.8,
       ["verse", "chorus", "bridge", "outro"],
       ["extensiones", "inversion_paso", "colas_extra"], 1,
       "Progresión doo-wop de los años 50 (I–vi–IV–V); arquetipo documentado de la "
       "era, base de incontables estándares.", "arquetipo_documentado"),
    _e("POP04", "Plagal Oscilante", ["familiar_pop", "pop", "plagal"], "familiaridad_pop",
       "tónica–subdominante–dominante–subdominante", "mayor", ["I", "IV", "V", "IV"],
       ["fluido", "circular"], 0.85, 0.4, 0.6,
       ["verse", "pre_chorus", "chorus"],
       ["extensiones", "sus_flavor", "colas_extra"], 1,
       "I–IV–V–IV (listado en la misión): rotación con cadencia plagal de retorno; "
       "arquetipo frecuente en pop/rock.", "arquetipo_genero"),
    _e("POP05", "Terceras Ascendentes", ["familiar_pop", "pop", "terceras"], "familiaridad_pop",
       "tónica–mediante–relativa–subdominante", "mayor", ["I", "iii", "vi", "IV"],
       ["luminoso", "elevado"], 0.75, 0.35, 0.65,
       ["verse", "pre_chorus", "chorus"],
       ["extensiones", "sustitucion_diatonica", "colas_extra"], 1,
       "I–iii–vi–IV: variante del eje con movimiento por terceras; arquetipo "
       "frecuente en pop moderno.", "arquetipo_genero"),
    _e("POP06", "Rotación Luminosa", ["familiar_pop", "pop"], "familiaridad_pop",
       "subdominante–tónica–dominante–relativa", "mayor", ["IV", "I", "V", "vi"],
       ["abierto", "flotante"], 0.8, 0.35, 0.6,
       ["verse", "chorus", "bridge"],
       ["extensiones", "sus_flavor", "colas_extra"], 1,
       "IV–I–V–vi: rotación del eje que abre por subdominante; variación original "
       "sobre el arquetipo documentado.", "variacion_original"),
    _e("POP07", "Canon Descendente", ["familiar_pop", "canon", "nostalgic"], "familiaridad_pop",
       "descenso diatónico con cadencia", "mayor",
       ["I", "V", "vi", "iii", "IV", "I", "IV", "V"],
       ["solemne", "nostálgico", "envolvente"], 0.8, 0.4, 0.75,
       ["verse", "chorus", "bridge", "outro"],
       ["extensiones", "inversion_paso", "colas_extra"], 1,
       "Fórmula tipo Canon de Pachelbel (I–V–vi–iii–IV–I–IV–V); arquetipo barroco "
       "absorbido por el pop, documentado en análisis públicos.", "arquetipo_documentado"),
    _e("POP08", "Cadencia de Jazz Mayor", ["familiar_pop", "soulful", "jazz"], "familiaridad_pop",
       "ii–V–I (cadencia estándar)", "mayor", ["ii7", "V7", "Imaj7"],
       ["elegante", "resolutivo", "cálido"], 0.9, 0.4, 0.95,
       ["bridge", "break", "outro", "chorus"],
       ["extensiones", "dominante_secundaria", "colas_extra"], 2,
       "ii–V–I: la cadencia estándar del jazz y la música americana; arquetipo "
       "documentado en todo método de armonía.", "arquetipo_documentado"),

    # ---------------- melancolia_nostalgia ----------------
    _e("MEL01", "Suspiro con iv", ["melancholic", "nostalgic", "melancolia"], "melancolia_nostalgia",
       "tónica con subdominante menor prestada", "mayor", ["I", "iii", "IV", "iv"],
       ["melancólico", "íntimo", "afligido"], 0.6, 0.5, 0.55,
       ["verse", "pre_chorus", "bridge", "break"],
       ["extensiones", "colas_extra"], 1,
       "I–iii–IV–iv (listado en la misión): el descenso IV→iv (intercambio modal "
       "integrado) es un tropo melancólico documentado del pop.", "arquetipo_genero"),
    _e("MEL02", "Cadencia Andaluza", ["melancholic", "nostalgic", "dark_cinematic", "andaluz"],
       "melancolia_nostalgia", "cadencia andaluza i–VII–VI–V", "menor",
       ["i", "VII", "VI", "V"], ["nostálgico", "dramático", "ancestral"],
       0.9, 0.55, 0.7, ["verse", "pre_chorus", "chorus", "bridge", "outro"],
       ["extensiones", "sus_flavor", "resolucion_deceptiva", "colas_extra"], 1,
       "Cadencia andaluza (i–VII–VI–V): arquetipo tradicional documentado del "
       "mediterráneo al rock y la balada.", "arquetipo_documentado"),
    _e("MEL03", "Terceras Nostálgicas", ["nostalgic", "melancholic"], "melancolia_nostalgia",
       "descenso por terceras a la tónica", "mayor", ["vi", "iii", "IV", "I"],
       ["evocador", "suave", "recogido"], 0.6, 0.4, 0.7,
       ["verse", "bridge", "break", "outro"],
       ["extensiones", "colas_extra"], 1,
       "vi–iii–IV–I: descenso por terceras hacia resolución; variación original "
       "sobre el arquetipo de terceras diatónicas.", "variacion_original"),
    _e("MEL04", "Plagal Nostálgico", ["nostalgic", "melancholic", "pop"], "melancolia_nostalgia",
       "tónica con relativa intercalada", "mayor", ["I", "IV", "vi", "IV"],
       ["dulce-amargo", "suspendido"], 0.7, 0.4, 0.55,
       ["verse", "pre_chorus", "chorus"],
       ["extensiones", "sus_flavor", "colas_extra"], 1,
       "I–IV–vi–IV: rotación con retorno plagal tras la relativa; variación "
       "original del eje pop.", "variacion_original"),
    _e("MEL05", "Amen Menor", ["melancholic", "nostalgic", "emotional_resolution"],
       "melancolia_nostalgia", "cadencia plagal mayor→menor→tónica", "mayor",
       ["IV", "iv", "I"], ["resignado", "cerrado", "sereno"], 0.55, 0.45, 0.85,
       ["break", "bridge", "outro"],
       ["extensiones", "intercambio_modal", "colas_extra"], 2,
       "IV–iv–I: cadencia plagal con menor prestado (tropo documentado del pop "
       "y gospel); variación corta de cierre.", "arquetipo_genero"),
    _e("MEL06", "Descenso Escalerado", ["melancholic", "nostalgic", "alternative"],
       "melancolia_nostalgia", "línea descendente diatónica", "mayor",
       ["I", "V", "vi", "IV", "I", "iv"], ["paulatino", "hondo", "decae"],
       0.5, 0.5, 0.6, ["bridge", "break", "outro"],
       ["extensiones", "intercambio_modal", "colas_extra"], 1,
       "Extensión del eje con colón iv final (préstamo modal integrado): variación "
       "original sobre el arquetipo, para cierres que se apagan.", "variacion_original"),

    # ---------------- oscuridad_cinematografica ----------------
    _e("CINE01", "Andaluz Cinematográfico", ["dark_cinematic", "cinematic", "melancholic"],
       "oscuridad_cinematografica", "i–VI–III–VII (descenso de tónica)", "menor",
       ["i", "VI", "III", "VII"], ["oscuro", "amplio", "fatalista"], 0.85, 0.6, 0.55,
       ["verse", "pre_chorus", "chorus", "bridge"],
       ["extensiones", "resolucion_deceptiva", "colas_extra"], 1,
       "i–VI–III–VII (listado en la misión): arquetipo menor universalmente usado "
       "en cinematográfico y dark pop.", "arquetipo_documentado"),
    _e("CINE02", "Cadencia Menor Clásica", ["dark_cinematic", "cinematic", "tension_release"],
       "oscuridad_cinematografica", "i–iv–VI–V (dominante armónica)", "menor",
       ["i", "iv", "VI", "V"], ["tenso", "dramático", "resolutivo"], 0.8, 0.6, 0.75,
       ["verse", "pre_chorus", "chorus", "bridge", "break"],
       ["extensiones", "sus_flavor", "colas_extra"], 1,
       "i–iv–VI–V (listado en la misión): cadencia menor clásica con dominante "
       "armónica; arquetipo documentado.", "arquetipo_documentado"),
    _e("CINE03", "Oscilación Frigia", ["dark_cinematic", "cinematic"], "oscuridad_cinematografica",
       "i–VII–VI–VII (vaivén sin cadencia)", "menor", ["i", "VII", "VI", "VII"],
       ["hipnótico", "suspense", "ritual"], 0.75, 0.65, 0.45,
       ["verse", "break", "bridge", "intro"],
       ["extensiones", "colas_extra"], 1,
       "i–VII–VI–VII (listado en la misión): vaivén frigio sin resolución; "
       "arquetipo de suspense cinematográfico.", "arquetipo_genero"),
    _e("CINE04", "Tráiler Épico", ["dark_cinematic", "cinematic", "tension_release"],
       "oscuridad_cinematografica", "i–VI–VII (ascenso de trailer)", "menor",
       ["i", "VI", "VII"], ["épico", "impulsor", "vasto"], 0.8, 0.6, 0.5,
       ["verse", "pre_chorus", "chorus", "break"],
       ["extensiones", "colas_extra"], 1,
       "i–bVI–bVII: fórmula de tráiler/cinemático muy usada (documentada en "
       "análisis públicos de música de tráiler).", "arquetipo_genero"),
    _e("CINE05", "Pulso Menor", ["dark_cinematic", "tension_release", "cinematic"],
       "oscuridad_cinematografica", "i–v (oscilación de tónica)", "menor",
       ["i", "v"], ["estático", "tenso", "hipnótico"], 0.7, 0.7, 0.3,
       ["intro", "verse", "break"],
       ["extensiones", "colas_extra"], 1,
       "i–v: oscilación mínima con dominante natural (sin resolución); arquetipo "
       "de build-up y ambiente oscuro.", "arquetipo_genero"),
    _e("CINE06", "Vaivén a iv", ["dark_cinematic", "cinematic"], "oscuridad_cinematografica",
       "i–iv (plagal menor)", "menor", ["i", "iv"], ["sombrío", "profundo", "grave"],
       0.7, 0.65, 0.35, ["intro", "verse", "break", "bridge"],
       ["extensiones", "colas_extra"], 2,
       "i–iv: vaivén plagal menor; arquetipo de peso cinematográfico lento.",
       "arquetipo_genero"),
    _e("CINE07", "Dominante Armónico", ["dark_cinematic", "emotional_resolution", "cinematic"],
       "oscuridad_cinematografica", "i–V7 (tensión que resuelve)", "menor",
       ["i", "V7"], ["dramático", "urgente", "cierre"], 0.75, 0.7, 0.8,
       ["verse", "break", "bridge", "outro"],
       ["extensiones", "sus_flavor", "colas_extra"], 2,
       "i–V7: tensión del modo menor armónico con resolución fuerte; arquetipo "
       "clásico documentado.", "arquetipo_documentado"),
    _e("CINE08", "Segunda Frigia", ["dark_cinematic", "tension_release", "cinematic"],
       "oscuridad_cinematografica", "i–bII (vecino inferior)", "menor",
       ["i", "bII"], ["crudo", "opresivo", "ritual"], 0.6, 0.9, 0.2,
       ["break", "bridge", "intro"],
       ["colas_extra"], 2,
       "i–bII: vecino frigio, máxima oscuridad sin resolución; arquetipo de "
       "tensión extrema (usar con moderación).", "arquetipo_genero"),

    # ---------------- dream_pop_alternative ----------------
    _e("DREAM01", "Apertura Suspendida", ["dream_pop", "alternative", "pop"],
       "dream_pop_alternative", "tónica suspendida–subdominante–relativa–dominante", "mayor",
       ["Isus2", "IV", "vi", "V"], ["flotante", "luminoso", "abierto"], 0.55, 0.35, 0.5,
       ["intro", "verse", "pre_chorus", "chorus"],
       ["extensiones", "sus_flavor", "colas_extra"], 1,
       "Rotación del eje con tónica sus2 (intercambio de color integrado); "
       "arquetipo frecuente en dream pop/alternativo.", "arquetipo_genero"),
    _e("DREAM02", "Estático Ambiguo", ["dream_pop", "alternative"], "dream_pop_alternative",
       "tónica suspendida oscilante", "mayor", ["Isus2", "Isus4"],
       ["ambiguo", "estático", "brumoso"], 0.5, 0.4, 0.3,
       ["intro", "verse", "break"],
       ["sus_flavor", "colas_extra"], 2,
       "Isus2–Isus4: suspensión interna de la tónica; arquetipo shoegaze/dream "
       "pop de textura estática.", "arquetipo_genero"),
    _e("DREAM03", "Terceras Cristalinas", ["dream_pop", "alternative"], "dream_pop_alternative",
       "relativa–tónica por terceras (7as)", "mayor", ["vi7", "Imaj7"],
       ["cristalino", "cálido", "flotante"], 0.5, 0.35, 0.4,
       ["verse", "bridge", "break"],
       ["extensiones", "colas_extra"], 2,
       "vi7–Imaj7: vaivén de terceras con séptimas (color jazz suave); arquetipo "
       "frecuente en dream pop.", "arquetipo_genero"),
    _e("DREAM04", "Plagal Paralelo", ["dream_pop", "alternative", "melancholic"],
       "dream_pop_alternative", "IV→iv→i (mayor/menor paralelos)", "mayor",
       ["IV", "iv", "i"], ["bicolor", "nostálgico", "sorpresivo"], 0.55, 0.5, 0.7,
       ["bridge", "break", "outro", "chorus"],
       ["extensiones", "colas_extra"], 2,
       "IV→iv: intercambio modal por paralelo menor (tropo documentado del pop "
       "alternativo); cierra en i como sombra de la tónica.", "arquetipo_documentado"),
    _e("DREAM05", "Tercera Menor Prestada", ["dream_pop", "alternative", "nostalgic"],
       "dream_pop_alternative", "I–bIII–IV (préstamo del menor)", "mayor",
       ["I", "bIII", "IV"], ["telúrico", "alternativo", "amplio"], 0.6, 0.45, 0.5,
       ["verse", "pre_chorus", "chorus", "break"],
       ["extensiones", "colas_extra"], 1,
       "I–bIII–IV: bIII prestada del modo menor (intercambio modal integrado); "
       "arquetipo del rock alternativo.", "arquetipo_genero"),
    _e("DREAM06", "Eje con Séptimas", ["dream_pop", "alternative", "familiar_pop"],
       "dream_pop_alternative", "eje pop con colores de séptima", "mayor",
       ["vi7", "IVmaj7", "Imaj9", "V7sus4"], ["etéreo", "sofisticado", "dulce"],
       0.6, 0.35, 0.55, ["verse", "pre_chorus", "chorus"],
       ["sus_flavor", "colas_extra"], 1,
       "El eje pop vestido de séptimas/9as y dominante suspendida; variación "
       "original sobre el arquetipo documentado.", "variacion_original"),
    _e("DREAM07", "Mixolidio Oscuro", ["dream_pop", "alternative", "dark_cinematic"],
       "dream_pop_alternative", "i–VII–IV (dorico/mixolidio menor)", "menor",
       ["i", "VII", "IV", "i"], ["grounded", "groovero", "nocturno"], 0.55, 0.55, 0.45,
       ["verse", "break", "bridge"],
       ["extensiones", "colas_extra"], 1,
       "i–VII–IV–i: IV mayor prestada del dórico (intercambio modal integrado); "
       "arquetipo modal del alternativo oscuro.", "arquetipo_genero"),
    _e("DREAM08", "Construcción a Dos", ["dream_pop", "alternative", "tension_release"],
       "dream_pop_alternative", "IV–V (build de dos acordes)", "mayor", ["IV", "V"],
       ["ascendente", "impaciente", "directo"], 0.75, 0.5, 0.45,
       ["pre_chorus", "break", "bridge"],
       ["sus_flavor", "colas_extra"], 2,
       "IV–V: construcción mínima de dos acordes; arquetipo de build en pop "
       "alternativo y baladas.", "arquetipo_genero"),

    # ---------------- soul_rnb ----------------
    _e("SOUL01", "Dominantes Gemelos", ["soulful", "soul", "rnb"], "soul_rnb",
       "I7–IV7 (dominantes cruzados)", "mayor", ["I7", "IV7"],
       ["groovero", "cálido", "bluesero"], 0.8, 0.45, 0.6,
       ["verse", "chorus", "bridge", "break"],
       ["extensiones", "colas_extra"], 1,
       "I7–IV7: dominantes cruzados sobre un mismo pedal funcional; arquetipo "
       "central del soul/blues.", "arquetipo_documentado"),
    _e("SOUL02", "Cadencia de Jazz", ["soulful", "jazz", "emotional_resolution"], "soul_rnb",
       "ii9–V13–Imaj9 (cadencia extendida)", "mayor", ["ii9", "V13", "Imaj9"],
       ["sofisticado", "sedoso", "resolutivo"], 0.85, 0.4, 0.95,
       ["bridge", "break", "outro", "chorus"],
       ["dominante_secundaria", "colas_extra"], 2,
       "ii–V–I con extensiones (9/13): la cadencia estándar del jazz en vestimenta "
       "R&B; arquetipo documentado.", "arquetipo_documentado"),
    _e("SOUL03", "Doo Wop con Séptimas", ["soulful", "nostalgic", "soul"], "soul_rnb",
       "I–vi–IV–V con séptimas", "mayor", ["Imaj7", "vi7", "IV7", "V7"],
       ["retro", "dulce", "vocal"], 0.9, 0.4, 0.8,
       ["verse", "chorus", "outro"],
       ["inversion_paso", "colas_extra"], 1,
       "I–vi–IV–V con séptimas: arquetipo doo-wop/gospel documentado, vestimenta "
       "soul.", "arquetipo_documentado"),
    _e("SOUL04", "Turnaround R&B", ["soulful", "rnb", "jazz"], "soul_rnb",
       "I–vi–ii–V (círculo de turnaround)", "mayor", ["Imaj7", "vi7", "ii7", "V7"],
       ["circular", "elegante", "propulsor"], 0.85, 0.45, 0.9,
       ["verse", "chorus", "bridge", "outro"],
       ["dominante_secundaria", "colas_extra"], 1,
       "I–vi–ii–V: turnaround de jazz/R&B estándar (documentado); mantiene el "
       "ciclo girando hacia la tónica.", "arquetipo_documentado"),
    _e("SOUL05", "Menor Soul", ["soulful", "soul", "melancholic"], "soul_rnb",
       "i7–iv7 (plagal menor soul)", "menor", ["i7", "iv7"],
       ["hondo", "sensual", "grave"], 0.75, 0.5, 0.4,
       ["verse", "break", "bridge"],
       ["extensiones", "colas_extra"], 2,
       "i7–iv7: vaivén plagal menor con séptimas; arquetipo del soul menor "
       "(ballads y neo-soul).", "arquetipo_genero"),
    _e("SOUL06", "Andaluz Soul", ["soulful", "melancholic", "dark_cinematic"], "soul_rnb",
       "andaldúza menor con extensiones y V7", "menor",
       ["i9", "VII9", "VImaj7", "V7"], ["nocturno", "sedoso", "dramático"], 0.7, 0.55, 0.75,
       ["verse", "pre_chorus", "chorus", "outro"],
       ["sus_flavor", "colas_extra"], 1,
       "Cadencia andaluza con extensiones R&B y dominante armónico final; "
       "variación original del arquetipo documentado.", "variacion_original"),
    _e("SOUL07", "Emocional con VI7", ["soulful", "emotional_resolution", "rnb"], "soul_rnb",
       "II–V con dominante secundaria VI7", "mayor", ["Imaj7", "VI7", "ii9", "V13"],
       ["emotivo", "ascendente", "brillante"], 0.7, 0.45, 0.85,
       ["chorus", "bridge", "outro"],
       ["dominante_secundaria", "colas_extra"], 1,
       "I–VI7–ii–V: turnaround con dominante secundaria (VI7→ii), tropo R&B "
       "documentado.", "arquetipo_documentado"),
    _e("SOUL08", "Amen Gospel", ["soulful", "emotional_resolution", "pop"], "soul_rnb",
       "IV–I con extensiones (amen)", "mayor", ["IVmaj9", "Imaj9"],
       ["cálido", "espiritual", "sereno"], 0.8, 0.35, 0.85,
       ["chorus", "break", "outro"],
       ["colas_extra"], 2,
       "IVmaj9–Imaj9: plagal gospel (amen) extendido; arquetipo documentado del "
       "soul/gospel.", "arquetipo_documentado"),

    # ---------------- balada_cinematica ----------------
    _e("BAL01", "Apertura de Balada", ["pop", "nostalgic", "emotional_resolution"],
       "balada_cinematica", "tónica–subdominante–relativa–dominante", "mayor",
       ["I", "IV", "vi", "V"], ["íntimo", "creciente", "honesto"], 0.7, 0.4, 0.7,
       ["verse", "pre_chorus", "chorus"],
       ["extensiones", "sus_flavor", "colas_extra"], 1,
       "I–IV–vi–V: rotación de balada con apertura plagal; variación original del "
       "eje pop documentado.", "variacion_original"),
    _e("BAL02", "Respiro Cinematográfico", ["cinematic", "dream_pop", "nostalgic"],
       "balada_cinematica", "tónica–mediante–relativa–subdominante", "mayor",
       ["I", "iii", "vi", "IV"], ["aéreo", "contemplativo", "lento"], 0.6, 0.35, 0.6,
       ["intro", "verse", "bridge", "break"],
       ["extensiones", "colas_extra"], 2,
       "I–iii–vi–IV: descenso de terceras de amplio aliento; variación original "
       "del arquetipo de terceras.", "variacion_original"),
    _e("BAL03", "Interrogante de Puente", ["tension_release", "alternative", "pop"],
       "balada_cinematica", "ii7–V7sus4 (pregunta suspendida)", "mayor",
       ["ii7", "V7sus4"], ["suspendido", "pregunta", "en suspenso"], 0.6, 0.5, 0.35,
       ["pre_chorus", "break", "bridge"],
       ["sus_flavor", "colas_extra"], 2,
       "ii7–V7sus4: dominante suspendida que retrasa la resolución; arquetipo de "
       "pre-coro/puente.", "arquetipo_genero"),
    _e("BAL04", "Amen Extendido", ["emotional_resolution", "pop", "nostalgic"],
       "balada_cinematica", "I–IV con sexta/mayor7", "mayor", ["I6", "IVmaj7"],
       ["sereno", "cerrado", "tierno"], 0.6, 0.3, 0.8,
       ["outro", "break", "chorus"],
       ["colas_extra"], 2,
       "I6–IVmaj7: plagal de cierre con colores suaves; variación original del "
       "amen gospel.", "variacion_original"),
    _e("BAL05", "Coro Descendente", ["pop", "nostalgic", "alternative"], "balada_cinematica",
       "relativa–mediante–subdominante–tónica", "mayor", ["vi", "iii", "IV", "I"],
       ["melancólico", "honesto", "resolutivo"], 0.5, 0.4, 0.75,
       ["chorus", "bridge", "outro"],
       ["extensiones", "colas_extra"], 1,
       "vi–iii–IV–I: descenso de terceras que aterriza en tónica; variación "
       "original sobre arquetipos de terceras.", "variacion_original"),
    _e("BAL06", "Andaluza de Balada", ["melancholic", "dark_cinematic", "emotional_resolution"],
       "balada_cinematica", "andaldúza menor con final V7", "menor",
       ["i", "VII", "VI", "V7"], ["nostálgico", "teatral", "gran cierre"], 0.8, 0.55, 0.8,
       ["chorus", "bridge", "outro"],
       ["extensiones", "sus_flavor", "colas_extra"], 1,
       "Cadencia andaluza con dominante de séptima final (V7): variación original "
       "del arquetipo documentado, orientada a gran cierre.", "variacion_original"),
]


def biblioteca(extra=None):
    """Biblioteca validada. ``extra``: lista de entradas nuevas (dicts con el
    mismo esquema) u objeto con método ``read`` (ruta/``Path``/file-like) que
    contenga ``{"progressiones": [...]}``. Las entradas externas se validan con
    las mismas reglas; ids duplicados → ValueError. Orden estable por id."""
    entradas = list(_BIBLIOTECA_BASE)
    if extra is not None:
        data = extra
        if hasattr(extra, "read") or isinstance(extra, (str, bytes)) or \
                hasattr(extra, "__fspath__"):
            import json
            if hasattr(extra, "read"):
                data = json.load(extra)
            else:
                with open(str(extra), encoding="utf-8") as fh:
                    data = json.load(fh)
        nuevos = data.get("progressiones") if isinstance(data, dict) else data
        if not isinstance(nuevos, (list, tuple)):
            raise ValueError("biblioteca externa debe ser una lista o "
                             "{'progressiones': [...]}")
        entradas = entradas + list(nuevos)
    out, vistos = {}, set()
    for e in entradas:
        v = validar_entrada(e)
        if v["id"] in vistos:
            raise ValueError("id duplicado en la biblioteca: %s" % (v["id"],))
        vistos.add(v["id"])
        out[v["id"]] = v
    return {k: out[k] for k in sorted(out)}


def por_id(lib, pid):
    """Progresión por id exacto (KeyError con mensaje claro)."""
    if pid not in lib:
        raise KeyError("progresión desconocida: %r (ids válidos: %s)"
                       % (pid, ", ".join(sorted(lib))))
    return lib[pid]


def buscar_por_keyword(lib, keyword):
    """Candidatos asociados a un keyword simple (búsqueda por keywords de
    entrada, insensible a familia). Determinista: orden por id."""
    kw = str(keyword).strip().lower()
    out = [e for e in (lib[i] for i in sorted(lib)) if kw in e["keywords"]]
    if not out:
        raise KeyError("ninguna progresión declara el keyword %r" % (kw,))
    return out
