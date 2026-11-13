"""Teoria musical: notas, acordes, tonalidades, instrumentos GM y mapa de percusion."""
import re
import unicodedata

NOTE_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
FLAT_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


def _acc(s):
    return str(s).replace('\u266d', 'b').replace('\u266f', '#')


def slug(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')


def parse_pc(name):
    m = re.fullmatch(r'([A-Ga-g])([#b]{0,2})', _acc(name).strip())
    if not m:
        raise ValueError('nota invalida: %r' % (name,))
    return (NOTE_PC[m.group(1).upper()] + m.group(2).count('#') - m.group(2).count('b')) % 12


def parse_pitch(x):
    """'Bb3' -> 58 (C4 = 60). Acepta enteros y cadenas numericas."""
    if isinstance(x, bool):
        raise ValueError('pitch invalido')
    if isinstance(x, (int, float)):
        return int(x)
    s = _acc(x).strip()
    if re.fullmatch(r'-?\d+', s):
        return int(s)
    m = re.fullmatch(r'([A-Ga-g])([#b]{0,2})(-?\d+)', s)
    if not m:
        raise ValueError('pitch invalido: %r' % (x,))
    raw = NOTE_PC[m.group(1).upper()] + m.group(2).count('#') - m.group(2).count('b')
    return 12 * (int(m.group(3)) + 1) + raw


def midi_name(n):
    return '%s%d' % (FLAT_NAMES[n % 12], n // 12 - 1)


# --------------------------------------------------------------------------
# Acordes
# --------------------------------------------------------------------------
_TOKENS = ['maj13', 'maj11', 'maj9', 'maj7', 'mmaj7', 'm7b5', 'dim7', 'sus2', 'sus4', 'add13', 'add11', 'add9',
           'add2', 'add4', 'maj', 'min', 'dim', 'aug', 'sus', 'm13', 'm11', 'm9', 'm7', 'm6', '13', '11', '9', '7',
           '6', '5', 'b5', '#5', 'b9', '#9', '#11', 'b13', 'm', 'M7', 'M9', 'M', '+', '-', 'o', '\u00b0', '\u00f8',
           '\u0394']
_TOK_RE = re.compile('|'.join(re.escape(t) for t in sorted(_TOKENS, key=len, reverse=True)))


class Chord(object):
    """deg: grado -> semitonos sobre la raiz. El grado 3 vale la sus-nota si el acorde es sus."""

    def __init__(self, symbol, root, deg, true_third, bass=None):
        self.symbol, self.root, self.deg, self.true_third, self.bass = symbol, root, deg, true_third, bass

    def tone(self, d, color=False):
        off = self.deg.get(d)
        if off is None and color:
            off = {9: 2}.get(d)
        return None if off is None else (self.root + off) % 12

    def has(self, d):
        return d in self.deg

    @property
    def third_pc(self):
        return (self.root + self.deg[3]) % 12 if self.true_third and 3 in self.deg else None

    def __repr__(self):
        return 'Chord(%s)' % self.symbol


def parse_chord(sym):
    s = _acc(sym).strip()
    if not s:
        raise ValueError('acorde vacio')
    s = re.sub(r'[()\s]', '', s)
    s = re.sub(r'(?i)maj', 'maj', s)
    s = re.sub(r'(?i)min', 'min', s)
    s = re.sub(r'(?i)dim', 'dim', s)
    s = re.sub(r'(?i)aug', 'aug', s)
    s = re.sub(r'(?i)sus', 'sus', s)
    s = re.sub(r'(?i)add', 'add', s)
    bass = None
    if '/' in s:
        s, b = s.split('/', 1)
        bass = parse_pc(b)
    m = re.match(r'^([A-G])([#b]?)(.*)$', s)
    if not m:
        raise ValueError('acorde no reconocido: %r' % (sym,))
    root = (NOTE_PC[m.group(1)] + {'#': 1, 'b': -1, '': 0}[m.group(2)]) % 12
    q = m.group(3)
    st = dict(third=4, fifth=7, seventh=None, sixth=None, ninth=None, eleventh=None, thirteenth=None, sus=None,
              power=False)
    pos = 0
    while pos < len(q):
        t = _TOK_RE.match(q, pos)
        if not t:
            raise ValueError('acorde no reconocido: %r' % (sym,))
        tok = t.group(0)
        pos = t.end()
        if tok in ('m', 'min', '-'):
            st['third'] = 3
        elif tok in ('maj', 'M'):
            pass
        elif tok in ('maj7', 'M7', '\u0394'):
            st['seventh'] = 11
        elif tok in ('maj9', 'M9'):
            st.update(seventh=11, ninth=2)
        elif tok == 'maj11':
            st.update(seventh=11, ninth=2, eleventh=5)
        elif tok == 'maj13':
            st.update(seventh=11, ninth=2, thirteenth=9)
        elif tok == 'mmaj7':
            st.update(third=3, seventh=11)
        elif tok in ('m7b5', '\u00f8'):
            st.update(third=3, fifth=6, seventh=10)
        elif tok in ('dim', 'o', '\u00b0'):
            st.update(third=3, fifth=6)
        elif tok == 'dim7':
            st.update(third=3, fifth=6, seventh=9)
        elif tok in ('aug', '+'):
            st['fifth'] = 8
        elif tok == 'sus2':
            st['sus'] = 2
        elif tok in ('sus4', 'sus'):
            st['sus'] = 5
        elif tok in ('add9', 'add2'):
            st['ninth'] = 2
        elif tok in ('add11', 'add4'):
            st['eleventh'] = 5
        elif tok == 'add13':
            st['thirteenth'] = 9
        elif tok == 'm6':
            st.update(third=3, sixth=9)
        elif tok == 'm7':
            st.update(third=3, seventh=10)
        elif tok == 'm9':
            st.update(third=3, seventh=10, ninth=2)
        elif tok == 'm11':
            st.update(third=3, seventh=10, ninth=2, eleventh=5)
        elif tok == 'm13':
            st.update(third=3, seventh=10, ninth=2, thirteenth=9)
        elif tok == '6':
            st['sixth'] = 9
        elif tok == '7':
            if st['seventh'] is None:
                st['seventh'] = 10
        elif tok == '9':
            st.update(ninth=2)
            st['seventh'] = st['seventh'] or 10
        elif tok == '11':
            st.update(ninth=2, eleventh=5)
            st['seventh'] = st['seventh'] or 10
        elif tok == '13':
            st.update(ninth=2, thirteenth=9)
            st['seventh'] = st['seventh'] or 10
        elif tok == '5':
            st['power'] = True
        elif tok == 'b5':
            st['fifth'] = 6
        elif tok == '#5':
            st['fifth'] = 8
        elif tok == 'b9':
            st['ninth'] = 1
        elif tok == '#9':
            st['ninth'] = 3
        elif tok == '#11':
            st['eleventh'] = 6
        elif tok == 'b13':
            st['thirteenth'] = 8
    deg = {1: 0, 5: st['fifth']}
    true_third = st['sus'] is None and not st['power']
    if st['sus'] is not None:
        deg[3] = st['sus']
    elif not st['power']:
        deg[3] = st['third']
    for k, key in ((7, 'seventh'), (9, 'ninth'), (11, 'eleventh'), (13, 'thirteenth'), (6, 'sixth')):
        if st[key] is not None:
            deg[k] = st[key]
    return Chord(str(sym).strip(), root, deg, true_third, bass)


def safe_chord(sym, fallback_root=0):
    try:
        return parse_chord(sym), None
    except ValueError as e:
        return Chord(str(sym), fallback_root, {1: 0, 3: 4, 5: 7}, True), str(e)


# --------------------------------------------------------------------------
# Tonalidades / modos
# --------------------------------------------------------------------------
MODES = {
    'ionian': [0, 2, 4, 5, 7, 9, 11], 'dorian': [0, 2, 3, 5, 7, 9, 10], 'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11], 'mixolydian': [0, 2, 4, 5, 7, 9, 10], 'aeolian': [0, 2, 3, 5, 7, 8, 10],
    'locrian': [0, 1, 3, 5, 6, 8, 10], 'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
    'pentatonic_minor': [0, 3, 5, 7, 10], 'pentatonic_major': [0, 2, 4, 7, 9], 'blues': [0, 3, 5, 6, 7, 10],
}
_MODE_WORDS = [('harmonic minor', 'harmonic_minor'), ('pentatonic minor', 'pentatonic_minor'),
               ('pentatonic major', 'pentatonic_major'), ('mixolydian', 'mixolydian'), ('mixolidio', 'mixolydian'),
               ('phrygian', 'phrygian'), ('frigio', 'phrygian'), ('locrian', 'locrian'), ('locrio', 'locrian'),
               ('lydian', 'lydian'), ('lidio', 'lydian'), ('dorian', 'dorian'), ('dorico', 'dorian'),
               ('aeolian', 'aeolian'), ('eolico', 'aeolian'), ('ionian', 'ionian'), ('jonico', 'ionian'),
               ('blues', 'blues'), ('minor', 'aeolian'), ('menor', 'aeolian'), ('major', 'ionian'),
               ('mayor', 'ionian')]
_MODE_OFFSET = {'ionian': 0, 'dorian': 2, 'phrygian': 4, 'lydian': 5, 'mixolydian': 7, 'aeolian': 9, 'locrian': 11}


def parse_key(text, default=(0, 'ionian')):
    """'D minor (1 bemol)' -> (2, 'aeolian')."""
    t = _acc(text or '').strip()
    m = re.match(r'^\s*([A-Ga-g])([#b]?)(.*)$', t)
    if not m:
        return default
    tonic = (NOTE_PC[m.group(1).upper()] + {'#': 1, 'b': -1, '': 0}[m.group(2)]) % 12
    rest = unicodedata.normalize('NFKD', m.group(3)).encode('ascii', 'ignore').decode().lower()
    for word, mode in _MODE_WORDS:
        if word in rest:
            return tonic, mode
    r = rest.strip()
    if r.startswith('m') and not r.startswith('maj'):
        return tonic, 'aeolian'
    return tonic, 'ionian'


def scale_pcs(tonic, mode):
    return [(tonic + i) % 12 for i in MODES.get(mode, MODES['ionian'])]


_KEYSIG = {0: 0, 7: 1, 2: 2, 9: 3, 4: 4, 11: 5, 6: 6, 5: -1, 10: -2, 3: -3, 8: -4, 1: -5}


def key_signature(tonic, mode):
    """(sf, mi) para el meta-evento de armadura."""
    parent = (tonic - _MODE_OFFSET.get(mode, 0)) % 12
    return _KEYSIG.get(parent, 0), (1 if mode == 'aeolian' else 0)


# --------------------------------------------------------------------------
# GM
# --------------------------------------------------------------------------
GM_NAMES = [
    'Acoustic Grand Piano', 'Bright Acoustic Piano', 'Electric Grand Piano', 'Honky-tonk Piano', 'Electric Piano 1',
    'Electric Piano 2', 'Harpsichord', 'Clavinet', 'Celesta', 'Glockenspiel', 'Music Box', 'Vibraphone', 'Marimba',
    'Xylophone', 'Tubular Bells', 'Dulcimer', 'Drawbar Organ', 'Percussive Organ', 'Rock Organ', 'Church Organ',
    'Reed Organ', 'Accordion', 'Harmonica', 'Tango Accordion', 'Acoustic Guitar (nylon)', 'Acoustic Guitar (steel)',
    'Electric Guitar (jazz)', 'Electric Guitar (clean)', 'Electric Guitar (muted)', 'Overdriven Guitar',
    'Distortion Guitar', 'Guitar Harmonics', 'Acoustic Bass', 'Electric Bass (finger)', 'Electric Bass (pick)',
    'Fretless Bass', 'Slap Bass 1', 'Slap Bass 2', 'Synth Bass 1', 'Synth Bass 2', 'Violin', 'Viola', 'Cello',
    'Contrabass', 'Tremolo Strings', 'Pizzicato Strings', 'Orchestral Harp', 'Timpani', 'String Ensemble 1',
    'String Ensemble 2', 'Synth Strings 1', 'Synth Strings 2', 'Choir Aahs', 'Voice Oohs', 'Synth Voice',
    'Orchestra Hit', 'Trumpet', 'Trombone', 'Tuba', 'Muted Trumpet', 'French Horn', 'Brass Section',
    'Synth Brass 1', 'Synth Brass 2', 'Soprano Sax', 'Alto Sax', 'Tenor Sax', 'Baritone Sax', 'Oboe',
    'English Horn', 'Bassoon', 'Clarinet', 'Piccolo', 'Flute', 'Recorder', 'Pan Flute', 'Blown Bottle',
    'Shakuhachi', 'Whistle', 'Ocarina', 'Lead 1 (square)', 'Lead 2 (sawtooth)', 'Lead 3 (calliope)',
    'Lead 4 (chiff)', 'Lead 5 (charang)', 'Lead 6 (voice)', 'Lead 7 (fifths)', 'Lead 8 (bass + lead)',
    'Pad 1 (new age)', 'Pad 2 (warm)', 'Pad 3 (polysynth)', 'Pad 4 (choir)', 'Pad 5 (bowed)', 'Pad 6 (metallic)',
    'Pad 7 (halo)', 'Pad 8 (sweep)', 'FX 1 (rain)', 'FX 2 (soundtrack)', 'FX 3 (crystal)', 'FX 4 (atmosphere)',
    'FX 5 (brightness)', 'FX 6 (goblins)', 'FX 7 (echoes)', 'FX 8 (sci-fi)', 'Sitar', 'Banjo', 'Shamisen', 'Koto',
    'Kalimba', 'Bagpipe', 'Fiddle', 'Shanai', 'Tinkle Bell', 'Agogo', 'Steel Drums', 'Woodblock', 'Taiko Drum',
    'Melodic Tom', 'Synth Drum', 'Reverse Cymbal', 'Guitar Fret Noise', 'Breath Noise', 'Seashore', 'Bird Tweet',
    'Telephone Ring', 'Helicopter', 'Applause', 'Gunshot']
assert len(GM_NAMES) == 128
_GM_SLUGS = [slug(n) for n in GM_NAMES]


def resolve_program(v):
    """int (0-127, base 0), 'pad-1-new-age', 'Pad 4 (choir)', 'choir'... -> int o None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return max(0, min(127, int(v)))
    s = slug(v)
    if not s:
        return None
    if s.isdigit():
        return max(0, min(127, int(s)))
    if s in _GM_SLUGS:
        return _GM_SLUGS.index(s)
    for i, g in enumerate(_GM_SLUGS):
        if g.startswith(s):
            return i
    for i, g in enumerate(_GM_SLUGS):
        if s in g:
            return i
    return None


DRUM_NOTES = {
    'kick': 36, 'kick2': 35, 'bass_drum': 36, 'rim': 37, 'rimshot': 37, 'sidestick': 37, 'snare': 38,
    'snare2': 40, 'electric_snare': 40, 'clap': 39, 'closed_hat': 42, 'hat': 42, 'chh': 42, 'pedal_hat': 44,
    'open_hat': 46, 'ohh': 46, 'tom_floor': 41, 'tom_lo': 45, 'tom_mid': 47, 'tom_hi': 50, 'crash': 49,
    'crash2': 57, 'ride': 51, 'ride_bell': 53, 'bell': 53, 'splash': 55, 'tambourine': 54, 'cowbell': 56,
    'shaker': 82,
}


def drum_note(name, drum_map=None):
    if isinstance(name, (int, float)):
        return int(name)
    k = slug(name)
    if drum_map and k in drum_map:
        return int(drum_map[k])
    if k in DRUM_NOTES:
        return DRUM_NOTES[k]
    raise ValueError('instrumento de percusion desconocido: %r' % (name,))
