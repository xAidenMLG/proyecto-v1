"""Biblioteca de estilos: esquemas de parametros (alimentan los formularios de la UI), presets de bateria,
patrones de bajo/arpegio y bloques por defecto por genero (synthwave / triphop)."""
import copy

ROLES = ['pad', 'strings', 'keys', 'bass', 'arp', 'mallet', 'lead', 'drums']
KINDS = ['intro', 'verse', 'pre', 'chorus', 'bridge', 'break', 'outro']
PRESETS = ['synthwave', 'triphop']

ROLE_DEFAULTS = {
    'pad': dict(program=88, volume=88, pan=64, reverb=120, chorus=60, detune=70, offset_ticks=0, jitter_ticks=6,
                vel_jitter=3, range=[40, 72], mono=False),
    'strings': dict(program=50, volume=92, pan=48, reverb=100, chorus=70, detune=-90, offset_ticks=17,
                    jitter_ticks=6, vel_jitter=3, range=[48, 76], mono=False),
    'bass': dict(program=38, volume=112, pan=64, reverb=20, chorus=0, detune=0, offset_ticks=-3, jitter_ticks=4,
                 vel_jitter=4, range=[28, 52], mono=True),
    'arp': dict(program=4, volume=96, pan=86, reverb=95, chorus=50, detune=55, offset_ticks=10, jitter_ticks=5,
                vel_jitter=5, range=[58, 90], mono=False),
    'lead': dict(program=81, volume=100, pan=72, reverb=100, chorus=30, detune=-35, offset_ticks=14,
                 jitter_ticks=12, vel_jitter=5, range=[62, 90], mono=True),
    'keys': dict(program=4, volume=76, pan=74, reverb=72, chorus=55, detune=20, offset_ticks=5, jitter_ticks=5,
                 vel_jitter=4, range=[45, 76], mono=False),
    'mallet': dict(program=11, volume=58, pan=92, reverb=112, chorus=40, detune=0, offset_ticks=16, jitter_ticks=6,
                   vel_jitter=4, range=[60, 88], mono=False),
    'drums': dict(program=None, volume=106, pan=64, reverb=60, chorus=0, detune=0, offset_ticks=0, jitter_ticks=4,
                  vel_jitter=5, range=[35, 82], mono=False),
}
ROLE_VEL_OFFSET = {'pad': -8, 'strings': -4, 'keys': -6, 'arp': -2, 'mallet': -12, 'bass': 2, 'lead': 4, 'drums': 0}
ROLE_PRIORITY = {'lead': 5, 'bass': 4, 'pad': 3, 'strings': 2, 'keys': 2, 'arp': 1, 'mallet': 1}   # mayor = se protege al reparar choques

ARP_PATTERNS = {
    'p1': [0, 2, 1, 3, 2, 3, 1, 2], 'p2': [0, 1, 2, 3, 2, 1, 0, 1], 'up': [0, 1, 2, 3], 'down': [3, 2, 1, 0],
    'updown': [0, 1, 2, 3, 4, 3, 2, 1], 'alt': [0, 2, 1, 3], 'p16': [0, 2, 1, 3, 2, 3, 1, 2, 0, 2, 1, 3, 3, 2, 1, 0],
    'sparse': [0, None, 2, None, 1, None, 3, None], 'sparse2': [0, None, None, 2, None, 1, None, None],
}

_A = [[0, 'R', 1.25, 0], [1.5, 'F', 0.5, -6], [2.5, 'R', 0.75, -3], [3.5, 'F', 0.5, -8]]
_B = [[0, 'R', 1.25, 0], [1.5, 'F', 0.5, -6], [2.0, 'O', 0.5, -4], [2.5, 'F', 0.5, -6], [3.5, 'R', 0.5, -8]]
BASS_SETS = {
    'synth_verse': [_A, _B],
    'synth_pre': [[[0, 'R', 0.5, 0], [0.5, 'R', 0.5, -12], [1.5, 'F', 0.5, -4], [2, 'R', 0.5, -2],
                   [2.5, 'O', 0.5, -4], [3.5, 'F', 0.5, -8]]],
    'synth_chorus': [[[0, 'R', 0.75, 2], [0.75, 'O', 0.25, -14], [1.5, 'F', 0.5, -4], [2, 'R', 0.5, 0],
                      [2.5, 'O', 0.5, -4], [3.25, 'F', 0.25, -10], [3.5, 'R', 0.5, -6]]],
    'trip_long': [[[0, 'R', 1.4, 0], [1.5, 'F', 1.4, -6], [3, 'R', 0.9, -4]],
                  [[0, 'R', 1.4, 0], [1.5, 'F', 1.4, -6], [3, 'F', 0.9, -4]]],
    'trip_two_bars': [[[0, 'R', 7.6, 0]], []],
    'trip_chorus': [[[0, 'R', 1.4, 2], [1.5, 'F', 0.9, -4], [2.5, 'R', 0.4, -8], [3, 'F', 0.9, -4]],
                    [[0, 'R', 1.4, 2], [1.5, 'O', 0.9, -6], [2.75, 'F', 1.1, -4]]],
    'whole': [[[0, 'R', 3.9, 0]]],
}


def _hats_grid(step, vel):
    return {'inst': 'closed_hat', 'grid': step, 'vel': vel, 'jitter': 0.02, 'drag': [0.2, 0.037], 'skip_if_open': True}


def _open(at, vel, omit, when=None, dur=0.4):
    d = {'inst': 'open_hat', 'at': at, 'vel': vel, 'dur': dur, 'omit': omit, 'jitter': 0.02, 'drag': [0.2, 0.037]}
    if when:
        d['when'] = when
    return d


_VERSE_FILL_1 = [{'when': {'last': True}, 'rolls': [
    {'inst': 'snare', 'start': 3.0, 'steps': 4, 'step': 0.25, 'v0': 62, 'v1': 84}]}]
_VERSE_FILL_2 = [{'when': {'last': True}, 'rolls': [
    {'inst': 'snare', 'start': 2.0, 'steps': 4, 'step': 0.5, 'v0': 70, 'v1': 88},
    {'inst': 'snare', 'start': 3.0, 'steps': 4, 'step': 0.25, 'v0': 84, 'v1': 112}],
    'hits': [{'inst': 'tom_lo', 'at': 2.0, 'vel': 84}, {'inst': 'tom_mid', 'at': 2.5, 'vel': 88}]}]

_VERSE_LAYERS = [
    {'inst': 'kick', 'at': [0, 1.5], 'vel': [92, 80], 'offset': -0.006},
    {'inst': 'kick', 'at': [2.5], 'vel': 76, 'offset': -0.006, 'when': {'bar_mod': [2, 1]}},
    {'inst': 'kick', 'pick': [2.25, 2.75, 3.25], 'prob': 0.5, 'vel_rand': [44, 56], 'offset': -0.006},
    {'inst': 'snare', 'at': [1, 3], 'vel': [86, 88], 'offset': 0.05},
    {'inst': 'rim', 'at': [2.5], 'vel': 52, 'offset': 0.035, 'prob': 0.6, 'when': {'bar_mod': [4, 3]}},
    _open([3.5], 66, 0.25, {'bar_mod': [2, 0]}),
    _open([1.5, 3.5], 66, 0.25, {'bar_mod': [2, 1]}),
    _hats_grid(0.5, [66, 54]),
]

DRUM_PRESETS = {
    'none': {'layers': [], 'fills': []},
    'intro_air': {'layers': [
        {'inst': 'crash', 'at': [0], 'vel': 50, 'dur': 3.5, 'when': {'bars': [0]}},
        {'inst': 'closed_hat', 'grid': 0.5, 'vel': {'v0': 26, 'v1': 48, 'over': 'steps'}, 'jitter': 0.02,
         'when': {'last': True}}], 'fills': []},
    'synth_verse_light': {'layers': [
        {'inst': 'kick', 'at': [0], 'vel': 72, 'offset': -0.006},
        _open([3.5], 52, 0.25, {'bars': [3]}),
        {'inst': 'closed_hat', 'grid': 0.5, 'vel': [52, 40], 'jitter': 0.02, 'drag': [0.2, 0.037],
         'skip_if_open': True}], 'fills': []},
    'synth_verse': {'layers': _VERSE_LAYERS, 'fills': _VERSE_FILL_1},
    'synth_verse2': {'layers': _VERSE_LAYERS + [
        {'inst': 'snare', 'at': [3.75], 'vel': 36, 'when': {'bar_mod': [2, 1]}}], 'fills': _VERSE_FILL_2},
    'synth_pre': {'layers': [
        {'inst': 'kick', 'at': [0, 2], 'vel': [92, 86], 'offset': -0.006, 'when': {'to': 4}},
        {'inst': 'snare', 'at': [1, 3], 'vel': [88, 90], 'offset': 0.03, 'when': {'to': 4}},
        _hats_grid(0.5, [70, 58]),
        {'inst': 'kick', 'at': [0, 2], 'vel': [96, 90], 'offset': -0.006, 'when': {'from': 4, 'to': 6}},
        {'inst': 'snare', 'at': [0, 1, 2, 3], 'vel': {'v0': 70, 'v1': 84, 'over': 'when'}, 'when': {'from': 4, 'to': 6}},
        {'inst': 'kick', 'at': [0, 2], 'vel': [100, 94], 'offset': -0.006, 'when': {'bars': [6]}},
        {'inst': 'snare', 'grid': 0.5, 'vel': {'v0': 72, 'v1': 98, 'over': 'steps'}, 'when': {'bars': [6]}},
        {'inst': 'kick', 'at': [0], 'vel': 104, 'offset': -0.006, 'when': {'last': True}},
        {'inst': 'snare', 'grid': 0.25, 'vel': {'v0': 62, 'v1': 114, 'over': 'steps'}, 'when': {'last': True}},
    ], 'fills': []},
    'synth_chorus': {'layers': [
        {'inst': 'kick', 'at': [0, 1, 2, 3], 'vel': [104, 94, 100, 94], 'offset': -0.004},
        {'inst': 'kick', 'at': [3.5], 'vel': 75, 'offset': -0.004, 'when': {'final': True}},
        {'inst': 'snare', 'at': [1, 3], 'vel': 106, 'offset': 0.02},
        {'inst': 'clap', 'at': [1, 3], 'vel': 82, 'dur': 0.2, 'offset': 0.03},
        {'inst': 'open_hat', 'at': [0.5, 1.5, 2.5, 3.5], 'vel': 74, 'dur': 0.25, 'jitter': 0.015, 'drag': [0.2, 0.037]},
        {'inst': 'closed_hat', 'grid': 0.25, 'vel': [86, 50, 50, 50], 'jitter': 0.015, 'drag': [0.2, 0.037],
         'skip_if_open': True},
        {'inst': 'crash', 'at': [0], 'vel': 110, 'dur': 3.0, 'when': {'bars': [0, 8]}},
        {'inst': 'crash', 'at': [0], 'vel': 88, 'dur': 2.0, 'when': {'bars': [4, 12]}},
        {'inst': 'ride_bell', 'at': [0], 'vel': 68, 'dur': 0.5, 'when': {'bar_mod': [4, 2]}},
    ], 'fills': [{'when': {'bars': [7, 15]}, 'mute': [{'inst': 'snare', 'from': 3}, {'inst': 'clap', 'from': 3}],
                  'hits': [{'inst': 'tom_hi', 'at': 3.0, 'vel': 96}, {'inst': 'tom_hi', 'at': 3.25, 'vel': 92},
                           {'inst': 'tom_mid', 'at': 3.5, 'vel': 100}, {'inst': 'tom_lo', 'at': 3.75, 'vel': 106}]}]},
    'synth_outro': {'layers': [
        {'inst': 'crash', 'at': [0], 'vel': 84, 'dur': 3.5, 'when': {'bars': [0]}},
        {'inst': 'kick', 'at': [0], 'vel': {'v0': 72, 'v1': 60, 'over': 'when'}, 'offset': -0.006, 'when': {'to': 4}},
        {'inst': 'kick', 'at': [2.5], 'vel': {'v0': 62, 'v1': 50, 'over': 'when'}, 'offset': -0.006, 'when': {'to': 4}},
        {'inst': 'snare', 'at': [1], 'vel': {'v0': 50, 'v1': 32, 'over': 'when'}, 'offset': 0.05, 'when': {'to': 4}},
        {'inst': 'closed_hat', 'grid': 0.5, 'vel': {'v0': 46, 'v1': 34, 'over': 'when'}, 'jitter': 0.02,
         'when': {'to': 4}},
        {'inst': 'kick', 'at': [0], 'vel': 56, 'offset': -0.006, 'when': {'from': 4, 'to': 6}},
        {'inst': 'closed_hat', 'at': [0, 1, 2, 3], 'vel': 40, 'jitter': 0.02, 'when': {'from': 4, 'to': 6}},
    ], 'fills': []},
    # ---- trip-hop (Shadow Corner): beat roto, snare retrasado ----
    'trip_verse': {'layers': [
        {'inst': 'kick', 'at': [0], 'vel': 92, 'offset': -0.006},
        {'inst': 'kick', 'pick': [1.75, 2.5, 3.25], 'prob': 0.6, 'vel_rand': [44, 58], 'offset': -0.006},
        {'inst': 'snare2', 'at': [2], 'vel': 86, 'offset': 0.054},
        {'inst': 'rim', 'at': [3.5], 'vel': 50, 'prob': 0.25, 'offset': 0.037},
        _open([1.5, 3.5], 62, 0.25),
        {'inst': 'closed_hat', 'pick': [0.75, 2.75], 'prob': 0.4, 'vel_rand': [24, 36], 'jitter': 0.025},
        _hats_grid(0.5, [52, 40]),
    ], 'fills': []},
    'trip_bridge': {'layers': [
        {'inst': 'kick', 'at': [0], 'vel': 84, 'offset': -0.006},
        {'inst': 'rim', 'at': [2], 'vel': 60, 'offset': 0.037, 'when': {'bar_mod': [2, 0]}},
        {'inst': 'open_hat', 'pick': [1.5, 3.5], 'prob': 0.4, 'vel_rand': [46, 58], 'dur': 0.4},
        {'inst': 'ride_bell', 'at': [0], 'vel': 55, 'dur': 0.5, 'when': {'bar_mod': [4, 0]}},
    ], 'fills': []},
    'trip_chorus': {'layers': [
        {'inst': 'kick', 'at': [0, 1.5], 'vel': [100, 84], 'offset': -0.006, 'when': {'bar_mod': [2, 0]}},
        {'inst': 'kick', 'at': [0, 2.75], 'vel': [100, 82], 'offset': -0.006, 'when': {'bar_mod': [2, 1]}},
        {'inst': 'snare2', 'at': [2], 'vel': 96, 'offset': 0.054},
        {'inst': 'clap', 'at': [2], 'vel': 80, 'dur': 0.2, 'offset': 0.0625},
        _open([1.5, 3.5], 70, 0.15),
        {'inst': 'closed_hat', 'pick': [0.75, 2.25, 3.25], 'prob': 0.5, 'vel_rand': [26, 40], 'jitter': 0.025},
        _hats_grid(0.5, [64, 48]),
        {'inst': 'ride_bell', 'at': [0], 'vel': 70, 'dur': 0.5, 'when': {'bar_mod': [4, 0]}},
    ], 'fills': []},
    'trip_outro': {'layers': [
        {'inst': 'kick', 'at': [0], 'vel': {'v0': 70, 'v1': 40, 'over': 'when'}, 'offset': -0.006, 'when': {'to': 3}},
        {'inst': 'snare2', 'at': [2], 'vel': {'v0': 64, 'v1': 32, 'over': 'when'}, 'offset': 0.054, 'when': {'to': 3}},
        _open([1.5], {'v0': 56, 'v1': 30, 'over': 'when'}, 0.0, {'to': 3}),
    ], 'fills': []},
}

# ---------------------------------------------------------------------------
# Esquemas de parametros (formularios de la UI)
# ---------------------------------------------------------------------------
def _f(key, label, typ, default=None, options=None, help=''):
    d = {'key': key, 'label': label, 'type': typ, 'default': default, 'help': help}
    if options is not None:
        d['options'] = options
    return d


_VOICING = [
    _f('voicing.profile', 'Perfil de voicing', 'select', 'full',
       ['rootfifth', 'triad', 'full', 'bare', 'shell', 'open4', 'spread'], 'rootfifth=raiz+quinta, bare=sin tercera'),
    _f('voicing.voices', 'Voces', 'int', None, None, 'vacio = segun perfil'),
    _f('voicing.range', 'Rango [min,max] MIDI', 'range', None, None, 'vacio = rango de la pista'),
    _f('voicing.min_gap', 'Separacion minima (st)', 'int', None),
    _f('voicing.max_gap', 'Separacion maxima (st)', 'int', None),
    _f('voicing.max_move', 'Movimiento maximo por voz (st)', 'int', 5),
]
_DRUM_PRESET_NAMES = [k for k in DRUM_PRESETS]

STYLE_SCHEMA = {
    'pad': {
        'sustain': {'label': 'Sostenido (acordes largos)', 'fields': _VOICING + [
            _f('hold', 'Duracion', 'select', 'chord', ['chord', 'bar'], 'chord = todo el acorde; bar = re-ataque cada compas'),
            _f('legato', 'Legato', 'number', 0.995),
            _f('tension', 'Notas de tension (JSON)', 'json', [], None,
               'p.ej. [{"offset":1,"near":60,"beat":2,"dur":1.5,"vel":50,"quality":"minor","when":{"from":8,"bar_mod":[4,[0,1]]}}]')]},
        'none': {'label': 'Silencio', 'fields': []},
    },
    'strings': {
        'sustain': {'label': 'Sostenido', 'fields': _VOICING + [
            _f('hold', 'Duracion', 'select', 'chord', ['chord', 'bar']),
            _f('modes', 'Modos por ciclo (lista)', 'list', None, None, 'p.ej. bare,full (alterna por ciclo)'),
            _f('modes_by_cycle', 'Modos por ciclo (JSON)', 'json', None, None, 'p.ej. {"2":"full","3":"bare"}'),
            _f('mode_cycle', 'Compases por ciclo', 'int', None, None, 'vacio = largo de la progresion'),
            _f('legato', 'Legato', 'number', 0.995)]},
        'stabs': {'label': 'Golpes ritmicos', 'fields': _VOICING + [
            _f('rhythm', 'Ritmo [[pos,dur,velDelta],...]', 'json', [[0, 1.5, 0], [1.5, 1.5, -8], [3, 1, -4]]),
            _f('legato', 'Legato', 'number', 0.97)]},
        'none': {'label': 'Silencio', 'fields': []},
    },
    'bass': {
        'pattern': {'label': 'Patron ritmico', 'fields': [
            _f('pattern_set', 'Set de patrones', 'select', 'synth_verse', sorted(BASS_SETS), 'se alternan por compas'),
            _f('patterns', 'Patrones propios (JSON)', 'json', None, None,
               '[[ [pos,"R|F|O|T|S|A",dur,velDelta], ... ], ...] (A = aproximacion cromatica)'),
            _f('center', 'Centro de registro (MIDI)', 'int', 38),
            _f('approach.enabled', 'Aproximacion cromatica', 'bool', True),
            _f('approach.every', 'Cada N compases', 'int', 2),
            _f('approach.offset', 'Desfase', 'int', 1),
            _f('slide_in.every', 'Slide de entrada cada N compases (0=no)', 'int', 8),
            _f('slide_out', 'Slide de salida al final de la seccion', 'bool', True),
            _f('slide_semitones', 'Slide (semitonos)', 'number', 2),
            _f('light_bars', 'Compases suaves al inicio', 'int', 0),
            _f('light_delta', 'Delta de velocidad suave', 'int', -8),
            _f('legato', 'Legato', 'number', 0.92)]},
        'long': {'label': 'Notas largas', 'fields': [
            _f('center', 'Centro de registro (MIDI)', 'int', 38),
            _f('fifth_at', 'Quinta a los N beats (0=no)', 'number', 4),
            _f('legato', 'Legato', 'number', 0.97)]},
        'none': {'label': 'Silencio', 'fields': []},
    },
    'arp': {
        'arp': {'label': 'Arpegio', 'fields': [
            _f('step', 'Paso (beats)', 'number', 0.5),
            _f('pattern', 'Patron', 'select', 'p1', sorted(ARP_PATTERNS), 'indices sobre las notas del acorde'),
            _f('pattern_list', 'Patron propio (lista)', 'json', None, None, '[0,2,1,3,null,2] (null = silencio)'),
            _f('alt_patterns', 'Patrones alternos por compas', 'list', None, None, 'p.ej. p1,p2'),
            _f('range', 'Ventana [min,max] MIDI', 'range', [60, 88]),
            _f('size', 'Notas por acorde', 'int', 4),
            _f('degrees', 'Grados (lista)', 'list', [1, 3, 5]),
            _f('ext_degrees', 'Extensiones (lista)', 'list', None, None, 'p.ej. 9 (solo sobre ext_min_pitch)'),
            _f('ext_min_pitch', 'Pitch minimo de extensiones', 'int', 72),
            _f('accent', 'Acento', 'number', 6),
            _f('legato', 'Legato', 'number', 1.05),
            _f('rest_prob', 'Probabilidad de silencio', 'number', 0),
            _f('step_changes', 'Cambios de paso (JSON)', 'json', None, None, '[{"from_bar":6,"step":0.25}]')]},
        'pings': {'label': 'Notas sueltas (atmosfera)', 'fields': [
            _f('every_bars', 'Cada N compases', 'int', 1), _f('beat', 'Beat', 'number', 2),
            _f('dur', 'Duracion', 'number', 3), _f('range', 'Ventana MIDI', 'range', [72, 90]),
            _f('degrees', 'Grados', 'list', [3, 5, 1]),
            _f('dyads', 'Dyads de tension (JSON)', 'json', None, None,
               '[{"bars":[1,5],"beat":2,"pitches":["D5","Eb5"],"dur":3.5,"vel":38}]')]},
        'none': {'label': 'Silencio', 'fields': []},
    },
    'keys': {
        'hold': {'label': 'Acordes sostenidos', 'fields': _VOICING + [
            _f('restrike_beats', 'Re-ataque cada N beats (0=no)', 'number', 0), _f('legato', 'Legato', 'number', 0.97)]},
        'broken': {'label': 'Acorde roto suave', 'fields': _VOICING + [
            _f('step', 'Paso (beats)', 'number', 1.0), _f('pattern', 'Patron', 'select', 'up', sorted(ARP_PATTERNS)),
            _f('pattern_list', 'Patron propio (lista de voces; null=silencio)', 'json', None),
            _f('ring', 'Duracion de cada nota (beats)', 'number', 2.5), _f('rest_prob', 'Probabilidad de silencio', 'number', 0.0),
            _f('accent', 'Acento', 'number', 4)]},
        'tail': {'label': 'Colas (decaen)', 'fields': _VOICING + [
            _f('notes_per_chord', 'Notas por acorde', 'int', 2), _f('ring', 'Duracion (beats)', 'number', 6)]},
        'none': {'label': 'Silencio', 'fields': []},
    },
    'mallet': {
        'replies': {'label': 'Respuestas en los huecos del lead', 'fields': [
            _f('respond_to', 'Responder a (pista o rol)', 'text', 'lead'), _f('prob', 'Probabilidad por hueco', 'number', 0.5),
            _f('min_gap', 'Hueco minimo del lead (beats)', 'number', 1.75), _f('margin', 'Margen tras el lead (beats)', 'number', 0.5),
            _f('glint_gap', 'Hueco minimo para una nota suelta (beats)', 'number', 1.0),
            _f('fragment', 'Notas por fragmento [min,max]', 'range', [2, 3]), _f('step', 'Separacion (beats)', 'number', 1.0),
            _f('dur', 'Duracion de nota (beats)', 'number', 2.5), _f('degrees', 'Grados (9,6,5...)', 'list', [9, 6, 5]),
            _f('range', 'Rango MIDI', 'range', [72, 88]), _f('min_distance', 'Distancia minima al lead (st)', 'int', 5),
            _f('max_per_bar', 'Maximo de notas por compas', 'int', 2)]},
        'pings': {'label': 'Notas sueltas (largas)', 'fields': [
            _f('count', 'Notas en el bloque', 'int', 2), _f('dur', 'Duracion (beats)', 'number', 6),
            _f('degrees', 'Grados', 'list', [9, 5]), _f('range', 'Rango MIDI', 'range', [72, 88]),
            _f('beat', 'Beat dentro del compas', 'number', 0.5)]},
        'none': {'label': 'Silencio', 'fields': []},
    },
    'lead': {
        'auto': {'label': 'Auto (frases si existen, si no generativo)', 'fields': None},
        'phrases': {'label': 'Frases del JSON', 'fields': None},
        'generative': {'label': 'Generativo', 'fields': None},
        'hold': {'label': 'Notas largas por acorde', 'fields': None},
        'none': {'label': 'Silencio', 'fields': []},
    },
    'drums': {
        'pattern': {'label': 'Capas de bateria', 'fields': [
            _f('preset', 'Preset', 'select', 'synth_verse', _DRUM_PRESET_NAMES),
            _f('layers', 'Capas propias (JSON; sustituyen al preset)', 'json', None),
            _f('fills', 'Fills propios (JSON)', 'json', None),
            _f('vel_scale', 'Escala de velocidad', 'number', 1.0)]},
        'none': {'label': 'Silencio', 'fields': []},
    },
}
_LEAD_FIELDS = [
    _f('legato', 'Legato', 'number', 0.93), _f('accent', 'Acento en primera nota del compas', 'number', 4),
    _f('transpose', 'Transposicion (st)', 'int', 0),
    _f('loop_bars', 'Repetir frase cada N compases (0=no)', 'int', 0),
    _f('bends.scoop.enabled', 'Scoop tras silencios', 'bool', True),
    _f('bends.scoop.semitones', 'Scoop (st)', 'number', 0.5), _f('bends.scoop.beats', 'Scoop (beats)', 'number', 0.25),
    _f('bends.scoop.min_gap', 'Silencio minimo (beats)', 'number', 0.75),
    _f('bends.scoop.prob', 'Probabilidad del scoop', 'number', 1.0),
    _f('bends.fall.enabled', 'Caida en notas largas', 'bool', True),
    _f('bends.fall.semitones', 'Caida (st)', 'number', 0.5), _f('bends.fall.beats', 'Caida (beats)', 'number', 0.46),
    _f('bends.fall.min_dur', 'Duracion minima (beats)', 'number', 3),
    _f('bends.fall.prob', 'Probabilidad de la caida', 'number', 1.0),
]
_GEN_FIELDS = [
    _f('density', 'Densidad (0-1)', 'number', 0.35), _f('range', 'Rango [min,max]', 'range', [67, 88]),
    _f('long_prob', 'Prob. nota larga', 'number', 0.5), _f('motif_bars', 'Compases de motivo', 'int', 4),
    _f('contour', 'Contorno', 'select', 'arch', ['arch', 'rising', 'falling', 'flat']),
    _f('scale_notes', 'Usar notas de la escala como paso', 'bool', True),
]
for _s in ('auto', 'phrases', 'generative', 'hold'):
    STYLE_SCHEMA['lead'][_s]['fields'] = list(_LEAD_FIELDS) + (_GEN_FIELDS if _s in ('auto', 'generative') else [])


def style_defaults(role, style):
    out = {}
    for f in (STYLE_SCHEMA.get(role, {}).get(style, {}).get('fields') or []):
        if f['default'] is None:
            continue
        cur = out
        parts = f['key'].split('.')
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = copy.deepcopy(f['default'])
    return out


# ---------------------------------------------------------------------------
# Bloques por defecto segun genero / tipo de seccion / rol
# ---------------------------------------------------------------------------
def _blk(style, params=None, velocity=None, enabled=True, from_bar=0, to_bar=None):
    b = {'enabled': enabled, 'style': style, 'params': params or {}, 'from_bar': from_bar, 'to_bar': to_bar}
    if velocity is not None:
        b['velocity'] = velocity
    return b


def default_block(preset, sec, role):
    kind, bars = sec.get('kind', 'verse'), int(sec.get('bars', 8))
    final, occ = bool(sec.get('final')), int(sec.get('occurrence', 0))
    kind = kind if kind in KINDS else 'verse'
    kk = 'pre' if kind == 'bridge' else kind
    if preset == 'triphop':
        return _triphop(kk, bars, final, occ, role)
    return _synthwave(kk, bars, final, occ, role)


def _lead_block(kind, final):
    gen = {'verse': dict(density=0.28, long_prob=0.7), 'pre': dict(density=0.4, contour='rising', long_prob=0.5),
           'chorus': dict(density=0.6, long_prob=0.35), 'break': dict(density=0.3), 'outro': dict(density=0.12)}
    if kind == 'intro':
        return _blk('none', enabled=False)
    if kind == 'outro':
        return _blk('hold', {'legato': 1.0}, velocity=[78, 64])
    vel = {'verse': 80, 'pre': [84, 96], 'chorus': 106 if final else 102, 'break': 80}[kind]
    return _blk('auto', dict(gen.get(kind, {})), velocity=vel)


def _synthwave(kind, bars, final, occ, role):
    if role == 'pad':
        if kind == 'intro': return _blk('sustain', {'voicing': {'profile': 'rootfifth'}}, 62)
        if kind in ('verse', 'break'): return _blk('sustain', {'voicing': {'profile': 'rootfifth'}}, 60 if occ == 0 else 64)
        if kind == 'pre': return _blk('sustain', {'voicing': {'profile': 'triad'}}, [62, 78])
        if kind == 'chorus':
            p = {'voicing': {'profile': 'shell'}}
            if final:
                p['tension'] = [{'offset': 1, 'near': 60, 'beat': 2, 'dur': 1.5, 'vel': 50, 'quality': 'minor',
                                 'when': {'from': 8, 'bar_mod': [4, [0, 1]]}}]
            return _blk('sustain', p, 82 if final else 78)
        return _blk('sustain', {'voicing': {'profile': 'rootfifth'}}, 60)
    if role == 'strings':
        if kind == 'intro': return _blk('sustain', {'voicing': {'profile': 'full'}}, [44, 56], from_bar=min(2, bars))
        if kind in ('verse', 'break'):
            if occ == 0 and bars >= 12:
                return _blk('sustain', {'modes_by_cycle': {'2': 'full', '3': 'bare'}}, 54, from_bar=8)
            return _blk('sustain', {'modes': ['bare', 'full']}, 62)
        if kind == 'pre': return _blk('sustain', {'voicing': {'profile': 'full'}}, [62, 84])
        if kind == 'chorus':
            return _blk('stabs', {'voicing': {'profile': 'full'}, 'rhythm': [[0, 1.5, 0], [1.5, 1.5, -8], [3, 1, -4]]},
                        100 if final else 94)
        return _blk('sustain', {'voicing': {'profile': 'full'}}, 56)
    if role == 'bass':
        if kind == 'intro': return _blk('none', enabled=False)
        if kind in ('verse', 'break'):
            return _blk('pattern', {'pattern_set': 'synth_verse', 'light_bars': 4 if occ == 0 else 0}, 88 if occ == 0 else 92)
        if kind == 'pre': return _blk('pattern', {'pattern_set': 'synth_pre'}, [90, 100])
        if kind == 'chorus': return _blk('pattern', {'pattern_set': 'synth_chorus'}, 108 if final else 104)
        return _blk('long', {'fifth_at': 4}, 78)
    if role == 'arp':
        if kind == 'intro': return _blk('pings', {'dur': 3}, 52)
        if kind in ('verse', 'break'):
            return _blk('arp', {'pattern': 'p1', 'alt_patterns': ['p1', 'p2'], 'degrees': [1, 3, 5], 'size': 4,
                                'range': [60, 88]}, 66 if occ == 0 else 72)
        if kind == 'pre':
            return _blk('arp', {'pattern': 'p1', 'alt_patterns': ['p1', 'p2'], 'degrees': [1, 3, 5], 'size': 4,
                                'range': [60, 88], 'step_changes': [{'from_bar': max(0, bars - 2), 'step': 0.25}]},
                        [68, 88])
        if kind == 'chorus':
            p = {'pattern': 'updown', 'degrees': [1, 3, 5, 7], 'ext_degrees': [9], 'ext_min_pitch': 72, 'size': 5,
                 'range': [62, 90]}
            if final: p['step_changes'] = [{'from_bar': 8, 'step': 0.25}]
            return _blk('arp', p, 100 if final else 96)
        return _blk('arp', {'pattern': 'alt', 'step': 1, 'degrees': [1, 3, 5], 'size': 4}, 56, to_bar=6)
    if role == 'keys':
        if kind == 'intro': return _blk('hold', {'voicing': {'profile': 'compact'}}, 52)
        if kind == 'pre': return _blk('hold', {'voicing': {'profile': 'compact'}, 'restrike_beats': 4}, [60, 76])
        if kind == 'chorus': return _blk('broken', {'voicing': {'profile': 'compact'}, 'step': 0.5, 'pattern': 'updown', 'ring': 1.5}, 90 if final else 84)
        if kind == 'outro': return _blk('tail', {'voicing': {'profile': 'compact'}}, [56, 20])
        return _blk('broken', {'voicing': {'profile': 'compact'}, 'step': 1.0, 'pattern': 'up', 'ring': 3.0}, 62)
    if role == 'mallet':
        if kind == 'intro': return _blk('pings', {'count': 2, 'dur': 6}, 50)
        if kind == 'outro': return _blk('pings', {'count': 2, 'dur': 7}, [50, 20])
        return _blk('replies', {'prob': 0.3 if kind == 'chorus' else 0.45}, 62 if kind != 'chorus' else 74)
    if role == 'lead':
        return _lead_block(kind, final)
    if role == 'drums':
        if kind == 'intro': return _blk('pattern', {'preset': 'intro_air'})
        if kind in ('verse', 'break'): return _blk('pattern', {'preset': 'synth_verse' if occ == 0 else 'synth_verse2',
                                                               'light_bars': 4 if occ == 0 else 0})
        if kind == 'pre': return _blk('pattern', {'preset': 'synth_pre'})
        if kind == 'chorus': return _blk('pattern', {'preset': 'synth_chorus'})
        return _blk('pattern', {'preset': 'synth_outro'})
    return _blk('none', enabled=False)


def _triphop(kind, bars, final, occ, role):
    if role == 'pad':
        v = {'intro': 45, 'verse': 47, 'pre': 40, 'chorus': 58, 'break': 45, 'outro': [47, 25]}[kind]
        return _blk('sustain', {'voicing': {'profile': 'rootfifth'}}, v)
    if role == 'strings':
        p = {'voicing': {'profile': 'full'}}
        if kind in ('verse', 'chorus', 'break') :
            p['modes'] = ['full', 'bare'] if occ == 0 else ['bare', 'full']
            p['mode_cycle'] = 8
        return _blk('sustain', p, {'intro': 40, 'verse': 52, 'pre': 46, 'chorus': 70, 'break': 50, 'outro': [50, 20]}[kind])
    if role == 'bass':
        if kind == 'intro': return _blk('none', enabled=False)
        ps = {'verse': 'trip_long', 'break': 'trip_long', 'pre': 'trip_two_bars', 'chorus': 'trip_chorus', 'outro': 'whole'}[kind]
        return _blk('pattern', {'pattern_set': ps, 'approach': {'enabled': kind != 'pre'}, 'slide_in': {'every': 8},
                                'slide_out': True}, {'verse': 70, 'pre': 66, 'chorus': 86, 'break': 70, 'outro': [60, 22]}[kind])
    if role == 'arp':
        if kind == 'intro': return _blk('pings', {'dur': 3, 'range': [62, 79]}, 50)
        if kind == 'outro': return _blk('arp', {'pattern': 'sparse', 'step': 0.5}, [55, 20], to_bar=6)
        p = {'pattern': 'sparse', 'step': 0.5, 'degrees': [1, 3, 5, 7], 'size': 4, 'range': [62, 79]}
        if kind == 'chorus': p = dict(p, pattern='alt', step=0.5)
        return _blk('arp', p, {'verse': 55, 'pre': 50, 'chorus': 72, 'break': 52}[kind])
    if role == 'keys':
        vo = {'voicing': {'profile': 'rootless', 'range': None}}
        vo['voicing'].pop('range')
        if kind == 'intro': return _blk('hold', dict(vo, restrike_beats=4), 50)
        if kind == 'outro': return _blk('tail', dict(vo, notes_per_chord=2, ring=7), [56, 18])
        if kind == 'pre': return _blk('hold', dict(vo, restrike_beats=0), 52)
        if kind == 'chorus': return _blk('broken', dict(vo, step=1.0, pattern='updown', ring=3.0, rest_prob=0.1), 70)
        return _blk('broken', dict(vo, step=1.0, pattern='up', ring=3.0, rest_prob=0.25), 56)
    if role == 'mallet':
        if kind == 'intro': return _blk('pings', {'count': 2, 'dur': 6}, 44)
        if kind == 'outro': return _blk('pings', {'count': 2, 'dur': 7}, [44, 18])
        prm = {'prob': {'verse': 0.6, 'pre': 0.75, 'chorus': 0.4, 'break': 0.55}[kind]}
        if kind == 'chorus':
            prm.update(margin=0.25, glint_gap=0.9)
        return _blk('replies', prm, {'verse': 50, 'pre': 46, 'chorus': 62, 'break': 48}[kind])
    if role == 'lead':
        if kind == 'intro': return _blk('none', enabled=False)
        if kind == 'outro': return _blk('hold', {'legato': 1.0}, [60, 20])
        return _blk('auto', {'density': 0.16, 'long_prob': 0.9, 'range': [62, 81]},
                    {'verse': 68, 'pre': 62, 'chorus': 84, 'break': 66}[kind])
    if role == 'drums':
        if kind == 'intro': return _blk('none', enabled=False)
        return _blk('pattern', {'preset': {'verse': 'trip_verse', 'break': 'trip_verse', 'pre': 'trip_bridge',
                                           'chorus': 'trip_chorus', 'outro': 'trip_outro'}[kind]})
    return _blk('none', enabled=False)


def default_automation(preset, sections):
    """Swells / fade-ins por defecto (CC11 expresion)."""
    if preset != 'synthwave':
        return []
    auto = []
    ids = {s.get('kind'): s['id'] for s in sections[::-1]}
    first = {}
    for s in sections:
        first.setdefault(s.get('kind'), s['id'])
    if 'intro' in first:
        auto.append({'track': 'pad', 'cc': 11, 'from': {'section': first['intro'], 'bar': 0},
                     'to': {'section': first['intro'], 'bar': 4}, 'v0': 35, 'v1': 127})
        auto.append({'track': 'strings', 'cc': 11, 'from': {'section': first['intro'], 'bar': 2},
                     'to': {'section': first['intro'], 'bar': 6}, 'v0': 40, 'v1': 127})
    if 'pre' in first:
        for t in ('strings', 'pad'):
            auto.append({'track': t, 'cc': 11, 'from': {'section': first['pre'], 'bar': 0},
                         'to': {'section': first['pre'], 'bar': 8}, 'v0': 88 if t == 'strings' else 100, 'v1': 127})
    return auto


def apply_modifiers(block, role, mods, preset, kind):
    """Sufijos de instrumento en una seccion ("vibraphone_sparse", "pad_wider", "drums_fade"...) -> parametros del bloque."""
    m = set(mods or [])
    if not m:
        return block
    p = block.setdefault('params', {})
    kk = 'pre' if kind == 'bridge' else kind
    tri = preset == 'triphop'
    if role == 'mallet':
        if block['style'] == 'replies':
            if m & {'selective'}: p['prob'] = round(min(p.get('prob', 0.5) * 0.7, 0.3), 2); p['max_per_bar'] = 1
            elif m & {'sparse'}: p['prob'] = round(p.get('prob', 0.5) * 0.85, 2)
        if 'tail' in m:
            block['style'] = 'pings'; block['params'] = {'count': 2, 'dur': 7}
    elif role == 'keys':
        if 'tail' in m:
            block['style'] = 'tail'
            p.update({'notes_per_chord': 2, 'ring': 7})
        if m & {'sparse'} and block['style'] == 'broken':
            p['rest_prob'] = 0.45
    elif role == 'pad':
        if m & {'wider', 'widest'}:
            p.setdefault('voicing', {})['profile'] = 'wide'
            block['_vel_add'] = 8 if 'widest' in m else 4
    elif role == 'bass':
        if 'sparse' in m:
            block['style'] = 'pattern'; p['pattern_set'] = 'trip_two_bars' if tri else 'synth_pre'
        if m & {'fading', 'fade'}:
            block['style'] = 'pattern'; p['pattern_set'] = 'whole'; block.pop('velocity', None)
    elif role == 'drums':
        if 'sparse' in m:
            p['preset'] = 'trip_bridge' if tri else 'synth_verse_light'
        if 'fuller' in m:
            p['preset'] = 'trip_chorus' if tri else 'synth_chorus'
        if m & {'fade', 'fading'}:
            p['preset'] = 'trip_outro' if tri else 'synth_outro'
    return block
