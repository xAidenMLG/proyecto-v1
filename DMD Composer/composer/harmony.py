"""Parser armónico REAL de grados romanos → símbolos de acorde del contrato.

Este módulo es el corazón del Módulo C (Harmonic Composer). Convierte
progresiones como ``I - III - vi - V`` en ``C - Em - Am - G`` usando la
tonalidad declarada, y garantiza que TODO símbolo emitido sea parseable por
la gramática real del motor (``forge/theory.py::parse_chord``, misma que
aplica el validador E113).

Reglas de conversión (documentadas para el usuario):
  * La tonalidad fija la RAÍZ de cada grado (escala del modo) y la calidad
    DIATÓNICA por defecto: en C major, ``I - III - vi - V`` → ``C - Em - Am - G``
    (III es Em porque E-G-B es la tríada diatónica del 3er grado).
  * Tokens de calidad explícitos SUSTITUYEN al default: ``maj`` ``M`` ``m``
    ``min`` ``7`` (dominante: 3ª mayor + 7ª menor) ``maj7`` ``m7`` ``mmaj7``
    ``9`` ``maj9`` ``m9`` ``11`` ``maj11`` ``m11`` ``13`` ``maj13`` ``m13``
    ``sus4`` ``sus2`` ``sus`` ``7sus4`` ``add9`` ``add11`` ``add13`` ``add6``
    ``dim`` ``o`` ``°`` ``dim7`` ``aug`` ``+`` ``m7b5`` ``ø`` ``m6`` ``5``
    ``7b9`` ``7#11`` ``7#5b9`` ``7b5`` ``7#5``.
    En tonalidades menores, ``V7`` da la dominante (E7 en A minor): el uso
    estándar de la notación popular. ``Vmaj`` daría Em→E mayor explícito.
  * La MAYÚSCULA/MINÚSCULA del numeral es decorativa (no cambia la calidad):
    lo que manda es la escala o el token explícito. La vista previa en vivo
    muestra SIEMPRE el acorde real que se escribirá en el JSON.
  * ``b``/``#`` antes del numeral altera la raíz ±1 semitono (``bVI``, ``#iv°``).
  * Cifrado clásico de inversión: ``6`` (primera inversión) y ``64`` (segunda),
    emitidas como acorde con bajo (``Am/C``). También ``/3`` ``/5`` y bajo
    literal ``/B``. La inversión SIEMPRE es representable: el contrato admite
    acordes con bajo real (``G/B``).
  * ``Grado:N`` fija los compases de ESE acorde (``I:2 - V:1``); se emite con la
    sintaxis real ``Chord:bars`` del motor (distribución definida por usuario).
  * La progresión repite en ciclo hasta llenar la sección (comportamiento REAL
    del motor: ``forge/engine.py::_chord_tokens`` cicla los tokens).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

#: Ortografía con bemoles — la misma de ``forge/theory.py::FLAT_NAMES`` y de la
#: instanciación N1 del compilador (_NOMBRES_NOTA). Coherencia garantizada.
NOTE_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

_PCS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

#: Escalas de 7 grados admitidas para grados romanos (misma tabla del motor).
MODES = {
    "ionian": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
}

#: Nombres de modo aceptados (ES/EN) → modo canónico. Composer es ESTRICTO:
#: una tonalidad ambigua es error, porque el motor interpretaría otra cosa.
_MODE_WORDS = {
    "major": "ionian", "mayor": "ionian", "ionian": "ionian", "jonico": "ionian",
    "minor": "aeolian", "menor": "aeolian", "aeolian": "aeolian", "eolico": "aeolian",
    "dorian": "dorian", "dorico": "dorian",
    "phrygian": "phrygian", "frigio": "phrygian",
    "lydian": "lydian", "lidio": "lydian",
    "mixolydian": "mixolydian", "mixolidio": "mixolydian",
    "locrian": "locrian", "locrio": "locrian",
    "harmonic minor": "harmonic_minor", "harmonicminor": "harmonic_minor",
    "menor armonica": "harmonic_minor", "armonica menor": "harmonic_minor",
}

#: Modos con nombre de etiqueta legible.
MODE_LABELS = {
    "ionian": "major", "aeolian": "minor", "dorian": "dorian", "phrygian": "phrygian",
    "lydian": "lydian", "mixolydian": "mixolydian", "locrian": "locrian",
    "harmonic_minor": "harmonic minor",
}

_NUMERAL = r"(VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i)"

#: Tokens de calidad explícitos (orden: los largos primero — la alternancia
#: regex es de un solo pase). 'maj'/'m'/'M'/'min' fuerzan tríada explícita.
_QUALITIES = [
    "7#5b9", "7#11", "7b9", "7b5", "7#5", "7sus4",
    "maj13", "maj11", "maj9", "maj7", "maj", "M7", "M",
    "mmaj7", "m13", "m11", "m9", "m7b5", "m7", "m6", "min", "m",
    "dim7", "dim", "o7", "°7", "07", "o", "°", "0", "ø", "aug", "+",
    "sus4", "sus2", "sus", "add13", "add11", "add9", "add6",
    "13", "11", "9", "7", "5",
]

#: Sufijo de símbolo que emite cada token (siempre parseable por parse_chord).
_QUALITY_SUFFIX = {
    "maj": "", "M": "", "min": "m", "m": "m",
    "maj7": "maj7", "M7": "maj7", "maj9": "maj9", "maj11": "maj11", "maj13": "maj13",
    "m7": "m7", "m9": "m9", "m11": "m11", "m13": "m13", "m6": "m6", "mmaj7": "mmaj7",
    "m7b5": "m7b5", "ø": "m7b5",
    "dim": "dim", "o": "dim", "°": "dim", "dim7": "dim7", "o7": "dim7", "°7": "dim7",
    "0": "dim", "07": "dim7",
    "aug": "aug", "+": "aug",
    "sus4": "sus4", "sus2": "sus2", "sus": "sus", "7sus4": "7sus4",
    "add9": "add9", "add11": "add11", "add13": "add13", "add6": "6",
    "7": "7", "9": "9", "11": "11", "13": "13", "5": "5",
    "7b9": "7b9", "7#11": "7#11", "7#5b9": "7#5b9", "7b5": "7b5", "7#5": "7#5",
}

#: Vocabulario de TIER rev. 3.2 §2.4 (espejo del validador; para W414 anticipado).
TIER_POP = {"", "6", "m", "add9", "sus2", "sus4", "sus", "7sus4", "maj7", "maj9", "m7", "m9"}
TIER_HYBRID = TIER_POP | {"7", "9", "11", "13", "maj11", "maj13", "m11", "m13",
                          "add11", "add13", "5", "7#11", "m7b5"}

_LANG_TIERS = {"pop_dream_pop": ("pop",), "hybrid": ("pop", "hybrid"),
               "experimental": ("pop", "hybrid", "experimental")}


def quality_tier(suffix: str) -> str:
    """'pop' | 'hybrid' | 'experimental' para un sufijo SIN raíz ni bajo."""
    return "pop" if suffix in TIER_POP else ("hybrid" if suffix in TIER_HYBRID else "experimental")


def tier_of_language(language: str) -> Tuple[str, ...]:
    return _LANG_TIERS.get(language, ("pop", "hybrid", "experimental"))


class HarmonyError(ValueError):
    """Progresión/tonalidad inválida o ambigua (mensaje para el usuario)."""


# --------------------------------------------------------------------------
# Tonalidad
# --------------------------------------------------------------------------

@dataclass
class KeyInfo:
    tonic: int          # pitch class 0–11
    mode: str           # modo canónico (clave de MODES)
    label: str          # etiqueta canónica: "Eb minor", "A dorian", ...

    @property
    def scale(self) -> List[int]:
        return [(self.tonic + i) % 12 for i in MODES[self.mode]]

    @property
    def is_minorish(self) -> bool:
        return self.mode in ("aeolian", "dorian", "phrygian", "harmonic_minor", "locrian")


_KEY_RE = re.compile(r"^\s*([A-Ga-g])\s*([#b])?\s*(.*)$", re.S)


def parse_key(text: str) -> KeyInfo:
    """Tonalidad ESTRICTA: 'C major', 'Dm', 'D minor', 'A dorian',
    'Eb minor', 'F# harmonic minor', 'sol menor'→NO (solo letras A–G).

    A diferencia de ``theory.parse_key`` (que cae a C major en silencio),
    aquí una tonalidad desconocida es ERROR: Composer no debe escribir en el
    JSON una tonalidad que el motor leería distinto a lo que el usuario quiso.
    """
    m = _KEY_RE.match(text or "")
    if not m:
        raise HarmonyError(f"tonalidad no reconocida: {text!r} (usa 'C major', 'D minor', 'A dorian'...)")
    letter = m.group(1).upper()
    acc = m.group(2) or ""
    tonic = (_PCS[letter] + (1 if acc == "#" else -1 if acc == "b" else 0)) % 12
    rest = (m.group(3) or "").strip().lower()
    rest = re.sub(r"\s+", " ", rest)
    if not rest:
        mode = "ionian"
    else:
        # Coincidencia EXACTA de palabras (no substring): 'Do menor' es error,
        # porque el motor lo leería como D minor y el usuario quiso G minor.
        words = rest.split()
        candidates = []
        if len(words) >= 2:
            candidates.append(" ".join(words[:2]))
        candidates.append(words[0])
        mode = None
        for cand in candidates:
            if cand in ("m", "min"):
                mode = "aeolian"
                break
            if cand in _MODE_WORDS:
                mode = _MODE_WORDS[cand]
                break
        if mode is None:
            raise HarmonyError(
                f"modo no reconocido en {text!r}. Usa: major/minor, dorian, phrygian, "
                "lydian, mixolydian, locrian o 'harmonic minor'.")
    label = f"{NOTE_NAMES[tonic]} {MODE_LABELS[mode]}"
    return KeyInfo(tonic=tonic, mode=mode, label=label)


# --------------------------------------------------------------------------
# Grados romanos
# --------------------------------------------------------------------------

@dataclass
class ParsedDegree:
    """Un grado parseado, antes de instanciar la tonalidad."""
    raw: str                # texto original del token
    degree: int             # 1..7
    upper: bool             # calidad default mayor (True) o menor (False)
    alteration: int         # -1 (b), 0, +1 (#)
    quality: Optional[str]  # token de calidad explícito o None
    bars: Optional[float]   # compases de este acorde (Chord:bars) o None
    bass: Optional[str]     # None | '3' | '5' | nota literal ('Bb')
    figure: Optional[str]   # None | '6' | '64'


_DEGREE_TOKEN = re.compile(
    r"^([b#]?)\s*" + _NUMERAL + r"\s*(" + "|".join(re.escape(q) for q in _QUALITIES) + r")?\s*"
    r"(6|64)?\s*(?::\s*([0-9]*\.?[0-9]+))?\s*(?:/\s*(3|5|[A-G][#b]?))?$"
)


def _split_tokens(text: str) -> List[str]:
    """Divide la progresión en tokens por separadores - – | , y espacios."""
    return [t for t in re.split(r"\s*[-–—|,]\s*|\s+", (text or "").strip()) if t]


def parse_numerals(text: str) -> List[ParsedDegree]:
    """Parsea la progresión completa. Lanza HarmonyError con posición clara."""
    tokens = _split_tokens(text)
    if not tokens:
        raise HarmonyError("progresión vacía")
    out: List[ParsedDegree] = []
    for i, tok in enumerate(tokens, 1):
        m = _DEGREE_TOKEN.match(tok)
        if not m:
            pista = ""
            if "0" in tok:
                pista = " ¿quisiste 'iio' (con la letra o) para el acorde disminuido?"
            raise HarmonyError(
                f"grado no reconocido en la posición {i}: {tok!r}. "
                "Formato: [b|#]I..VII [calidad] [6|64] [:compases] [/bajo]." + pista)
        alt = m.group(1)
        num = m.group(2)
        degree = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7}[num.lower()]
        upper = num[0].isupper()
        quality = m.group(3)
        figure = m.group(4)
        bars = float(m.group(5)) if m.group(5) else None
        if bars is not None and (bars != int(bars) or not (1 <= bars <= 64)):
            raise HarmonyError(
                f"compases por acorde inválidos en la posición {i}: {tok!r} — "
                "usa un ENTERO de 1 a 64 ('I:2'); los fraccionarios no existen en este contrato")
        bass = m.group(6)
        if bass and figure:
            raise HarmonyError(f"cifrado y bajo a la vez no se admiten: {tok!r}")
        if quality and figure:
            raise HarmonyError(
                f"calidad + cifra de inversión juntas no se admiten ({tok!r}); "
                "usa el bajo explícito, p. ej. 'V7/B'")
        out.append(ParsedDegree(raw=tok, degree=degree, upper=upper, alteration=1 if alt == "#" else -1 if alt == "b" else 0,
                                quality=quality, bars=bars, bass=bass, figure=figure))
    return out


# --------------------------------------------------------------------------
# Instanciación con tonalidad
# --------------------------------------------------------------------------

@dataclass
class ResolvedChord:
    symbol: str             # símbolo final ('Em', 'G/B', 'C:2'...)
    root_pc: int
    suffix: str             # calidad emitida ('', 'm', 'maj7', ...)
    bars: Optional[float]   # compases declarados por el usuario (None = default)
    roman: str              # numeral original
    diatonic: bool
    tier: str               # pop | hybrid | experimental
    bass_note: Optional[str] = None


def _diatonic_quality(key: "KeyInfo", idx: int, altered: bool = False) -> str:
    """Tríada por defecto del grado idx (0-based).

    Sin alteración: tríada DIATÓNICA de la escala (III en C major → Em).
    Con alteración (b/#): tríada MAYOR por defecto — es la práctica estándar
    del pop (bVI, bVII, bII prestados del modo paralelo; en C major, bVI → Ab
    mayor, bVII → Bb mayor). Un token explícito ('m', 'o', '+') siempre gana.
    En tonalidades menores, el grado V es la DOMINANTE MAYOR (en D minor,
    ``V`` → A, no Am; para el v menor escribe ``Vm``).
    """
    if altered:
        return ""
    third = (key.scale[(idx + 2) % 7] - key.scale[idx]) % 12
    fifth = (key.scale[(idx + 4) % 7] - key.scale[idx]) % 12
    if idx == 4 and key.is_minorish and key.mode != "harmonic_minor" and third == 3 and fifth == 7:
        return ""                       # dominante mayor del modo menor
    if third == 3 and fifth == 7:
        return "m"
    if third == 3 and fifth == 6:
        return "dim"
    if third == 4 and fifth == 8:
        return "aug"
    return ""                       # mayor (3ª mayor + 5ª justa)


def _suffix_for(degree: ParsedDegree, key: "KeyInfo", idx: int) -> str:
    """Sufijo final: tríada por defecto del grado o token explícito del usuario."""
    q = degree.quality
    if q is None:
        return _diatonic_quality(key, idx, altered=(degree.alteration != 0))
    return _QUALITY_SUFFIX[q]


def resolve_degree(deg: ParsedDegree, key: KeyInfo) -> ResolvedChord:
    """Un grado + tonalidad → acorde real (raíz y calidad DIATÓNICA por escala;
    los tokens de calidad del usuario sustituyen al default)."""
    idx = deg.degree - 1
    if not (0 <= idx < 7):
        raise HarmonyError(f"grado fuera de rango: {deg.raw!r}")
    root_pc = (key.scale[idx] + deg.alteration) % 12
    suffix = _suffix_for(deg, key, idx)
    bass_note = None
    if deg.figure in ("6", "64") or deg.bass in ("3", "5"):
        minor_third = suffix.startswith("m") or suffix in ("dim", "dim7")
        if suffix in ("sus4", "sus2", "sus", "7sus4"):
            third_iv, fifth_iv = (2 if suffix == "sus2" else 5), 7
        elif suffix == "5":
            third_iv, fifth_iv = None, 7     # power chord: sin tercera
        else:
            third_iv = 3 if minor_third else 4
            fifth_iv = 6 if suffix in ("dim", "dim7", "m7b5") else 8 if suffix == "aug" else 7
        if third_iv is None:
            bass_note = NOTE_NAMES[(root_pc + fifth_iv) % 12]      # solo queda el quinto
        elif (deg.figure == "64" or deg.bass == "5"):
            bass_note = NOTE_NAMES[(root_pc + fifth_iv) % 12]
        else:
            bass_note = NOTE_NAMES[(root_pc + third_iv) % 12]
    elif deg.bass:
        bass_note = deg.bass
    symbol = NOTE_NAMES[root_pc] + suffix
    if bass_note:
        symbol += "/" + bass_note
    if deg.bars is not None:
        symbol += f":{deg.bars:g}"
    diatonic = root_pc in key.scale
    tier = quality_tier(suffix.split("/")[0] if "/" in suffix else suffix)
    return ResolvedChord(symbol=symbol, root_pc=root_pc, suffix=suffix, bars=deg.bars,
                         roman=deg.raw, diatonic=diatonic, tier=tier, bass_note=bass_note)


def resolve_progression(text: str, key: KeyInfo) -> List[ResolvedChord]:
    """Progresión completa → acordes reales con la tonalidad aplicada."""
    return [resolve_degree(d, key) for d in parse_numerals(text)]


def tier_warnings(chords: List[ResolvedChord], language: str) -> List[str]:
    """Avisos W414 anticipados: acordes fuera del vocabulario del language."""
    allowed = tier_of_language(language)
    out = []
    for c in chords:
        if c.tier not in allowed:
            out.append(f"acorde '{c.symbol}' ({c.roman}) está fuera del vocabulario "
                       f"'{language}' (W414): el motor lo respeta, pero suena fuera del idioma elegido")
    return out


def diatonic_warnings(chords: List[ResolvedChord]) -> List[str]:
    out = []
    for c in chords:
        if not c.diatonic:
            out.append(f"'{c.roman}' → {c.symbol} es no diatónico en la tonalidad "
                       "(permitido; el validador no lo bloquea)")
    return out


# --------------------------------------------------------------------------
# Recetas N1: instanciación de progresiones nativas (para el Song Map)
# --------------------------------------------------------------------------

def instantiate_n1(pairs: List, key: KeyInfo) -> List[str]:
    """Pares (offset, calidad) de la receta N1 → símbolos con la tónica real.

    Espejo exacto de ``dark_director/compilador.py::_instanciar_simbolo``:
    nombre con bemoles + calidad, sobre ``(tonic + offset) % 12``.
    """
    out = []
    for off, cal in pairs:
        out.append(NOTE_NAMES[(key.tonic + int(off)) % 12] + str(cal))
    return out
