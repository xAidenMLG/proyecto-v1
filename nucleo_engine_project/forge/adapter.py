"""Adaptador: cualquier JSON soportado -> proyecto canonico 'midi-forge/1' + informe de lo que se interpreto."""
import copy
import json
import math
import re
import unicodedata

from . import styles as S
from . import theory as T

SCHEMA = 'midi-forge/1'
GLOBAL_DEFAULTS = {'bpm': 100, 'time_signature': [4, 4], 'key': 'C major', 'ticks_per_beat': 480, 'seed': 92,
                   'humanize': 1.0, 'velocity_cap': 110, 'pitch_bend_range': 2, 'preset': 'synthwave',
                   'repair_clashes': True}

# El orden importa: la primera coincidencia gana. Solo se mira nombre / gm_name / instrument (nunca la descripcion en "role").
_ROLE_WORDS = [
    ('drums', ['drum', 'bateria', 'percus', 'kit']),
    ('bass', ['bass', 'bajo']),
    ('mallet', ['vibraphone', 'vibrafono', 'vibes', 'marimba', 'glockenspiel', 'xylophone', 'mallet', 'bells']),
    ('pad', ['pad', 'choir', 'ambient', 'atmos']),
    ('strings', ['string', 'cuerda', 'violin', 'cello', 'orchestra', 'ensemble']),
    ('lead', ['lead', 'sax', 'voice', 'voz', 'melod', 'vocal', 'solo']),
    ('arp', ['arp', 'texture', 'textura', 'celesta', 'pluck']),
    ('keys', ['rhodes', 'piano', 'keys', 'wurli', 'electric piano']),
]
_ALIASES = {
    'drums': ['drum', 'drums', 'bateria', 'percusion', 'percussion', 'perc', 'kit', 'beat'],
    'bass': ['bass', 'bajo', 'sub'], 'pad': ['pad', 'pads', 'choir', 'haze'],
    'strings': ['string', 'strings', 'cuerda', 'cuerdas'],
    'lead': ['lead', 'sax', 'saxophone', 'tenor', 'voice', 'voz', 'melodia', 'melody', 'vocal'],
    'keys': ['rhodes', 'piano', 'ep', 'keys', 'wurlitzer', 'epiano'],
    'mallet': ['vibraphone', 'vibes', 'vibe', 'marimba', 'glockenspiel', 'xylophone', 'mallet', 'bells'],
    'arp': ['arp', 'arpegio', 'arpeggio', 'texture', 'textura', 'pluck']}
_ALL_ALIASES = {a for v in _ALIASES.values() for a in v}
_FAMILY = {'verso': 'verse', 'estrofa': 'verse', 'coro': 'chorus', 'estribillo': 'chorus', 'hook': 'chorus',
           'puente': 'bridge', 'cierre': 'outro', 'ending': 'outro', 'prechorus': 'pre_chorus'}


def norm_text(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()


def canon(sl):
    toks = [_FAMILY.get(t, t) for t in sl.split('_') if t]
    out = []
    for t in toks:
        if out and out[-1] == 'pre' and t in ('chorus', 'coro'):
            out[-1] = 'pre_chorus'
        else:
            out.append(t)
    return '_'.join(out)


def infer_role(tr):
    if tr.get('role') in S.ROLES:
        return tr['role']
    text = norm_text(' '.join(str(tr.get(k, '')) for k in ('name', 'gm_name', 'instrument', 'kit')))
    if tr.get('kit') or (str(tr.get('channel')) in ('9', '10') and 'drum' in text):
        return 'drums'
    for role, words in _ROLE_WORDS:
        for w in words:
            if re.search(r'(^|[^a-z])' + re.escape(w), text):
                return role
    prog = T.resolve_program(tr.get('program') if tr.get('program') is not None else tr.get('gm_name'))
    if prog is not None:
        if prog <= 7: return 'keys'
        if 8 <= prog <= 15: return 'mallet'
        if 32 <= prog <= 39: return 'bass'
        if 40 <= prog <= 55: return 'strings'
        if 56 <= prog <= 87: return 'lead'
        if 88 <= prog <= 95: return 'pad'
    return 'arp'


def infer_kind(name, idx, names):
    s = canon(T.slug(name))
    if 'outro' in s: return 'outro'
    if 'intro' in s: return 'intro'
    if 'pre' in s.split('_') or 'pre_chorus' in s or 'prechorus' in s: return 'pre'
    if 'chorus' in s: return 'chorus'
    if 'bridge' in s:
        nxt = canon(T.slug(names[idx + 1])) if idx + 1 < len(names) else ''
        prv = canon(T.slug(names[idx - 1])) if idx > 0 else ''
        return 'pre' if 'chorus' in nxt and 'chorus' not in prv else 'bridge'
    if 'verse' in s: return 'verse'
    if any(w in s for w in ('solo', 'break', 'interlude', 'instrumental')): return 'break'
    return 'verse'


def unique_id(base, used):
    base = T.slug(base) or 'x'
    cand, i = base, 2
    while cand in used:
        cand = '%s_%d' % (base, i)
        i += 1
    used.add(cand)
    return cand


def add(rep, level, msg):
    rep.append({'level': level, 'msg': msg})


# --------------------------------------------------------------------------
def normalize(obj, preset=None):
    rep = []
    if isinstance(obj, (str, bytes)):
        try:
            obj = json.loads(obj)
        except ValueError as e:
            raise ValueError('JSON invalido: %s' % e)
    if not isinstance(obj, dict):
        raise ValueError('El JSON debe ser un objeto {...}')
    if str(obj.get('schema', '')).startswith('midi-forge'):
        project = copy.deepcopy(obj)
        add(rep, 'info', 'Proyecto canonico midi-forge/1 detectado.')
    elif _is_events(obj):
        project = from_events(obj, rep)
    else:
        project = from_spec(obj, rep, preset)
    finalize_project(project, rep, preset)
    return project, rep


def _is_events(obj):
    ts = obj.get('tracks')
    if not isinstance(ts, list) or not ts or not isinstance(ts[0], dict):
        return False
    n = ts[0].get('notes')
    return isinstance(n, list) and (not n or (isinstance(n[0], dict) and 'start' in n[0] and 'pitch' in n[0]))


def _num(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
def from_events(obj, rep):
    add(rep, 'info', 'Formato de EVENTOS detectado (notas ya escritas): se reproduce tal cual, sin generadores.')
    tpb = int(obj.get('ticks_per_beat') or 480)
    tracks, used, raw, maxb = [], set(), [], 0.0
    for i, t in enumerate(obj['tracks']):
        role = infer_role(t)
        if str(t.get('channel')) == '10':
            role = 'drums'
        tid = unique_id(t.get('id') or t.get('name') or role, used)
        notes = t.get('notes', [])
        for n in notes:
            maxb = max(maxb, float(n['start']) + float(n['duration']))
        d = dict(S.ROLE_DEFAULTS.get(role, S.ROLE_DEFAULTS['arp']))
        d.update(id=tid, name=t.get('name', tid), role=role, channel=int(t.get('channel', 10 if role == 'drums' else i + 1)),
                 program=t.get('program', d.get('program')), enabled=True, mute=False, solo=False)
        tracks.append(d)
        raw.append({'id': tid, 'notes': notes, 'pitch_bend': t.get('pitch_bend', []), 'controllers': t.get('controllers', [])})
    g = {'bpm': obj.get('bpm', 100), 'ticks_per_beat': tpb, 'time_signature': obj.get('time_signature', [4, 4])}
    bars = max(1, int(math.ceil(maxb / 4.0)))
    return {'schema': SCHEMA, 'meta': {'name': obj.get('title', 'Eventos importados'), 'description': ''},
            'global': g, 'tracks': tracks, 'raw': {'tracks': raw},
            'sections': [{'id': 'todo', 'name': 'Todo', 'kind': 'verse', 'bars': bars, 'chords': ['C'], 'blocks': {}}]}


# --------------------------------------------------------------------------
def _channel_base(tracks, rep, notes_in=None):
    ch_note = norm_text((notes_in or {}).get('channels', ''))
    if re.search(r'zero[- ]?based|base 0', ch_note):
        return 0
    if re.search(r'one[- ]?based|1[- ]?based|base 1', ch_note):
        return 1
    chans = [t.get('channel') for t in tracks if isinstance(t.get('channel'), int)]
    drums = [t for t in tracks if infer_role(t) == 'drums']
    if 0 in chans:
        return 0
    if any(t.get('channel') == 10 for t in drums):
        return 1
    if any(t.get('channel') == 9 for t in drums):
        return 0
    return 1


def parse_rhythm(text):
    default, per = 1.0, {}
    t = norm_text(text or '')
    for m in re.finditer(r'(\d+)\s*compas(?:es)?\s*por\s*acorde(?:\s*en\s*([a-z ,]+))?', t):
        bars, scope = float(m.group(1)), m.group(2)
        if scope:
            for w in re.split(r'[ ,]+|\by\b', scope):
                k = _FAMILY.get(w, w)
                if k in S.KINDS:
                    per[k] = bars
        else:
            default = bars
    m = (re.search(r'cada\s*(\d+)\s*compas', t) or re.search(r'(\d+)\s*bars?\s*per\s*chord', t)
         or re.search(r'chord\s*(?:every|per)\s*(\d+)\s*bars?', t) or re.search(r'every\s*(\d+)\s*bars?', t))
    if m:
        default = float(m.group(1))
    return default, per


def parse_modes(text):
    t = norm_text(text or '')
    by_cycle, seq = {}, []
    for m in re.finditer(r'(full|bare)', t):
        after = t[m.end():m.end() + 40]
        mm = re.match(r'\s*(?:en\s+el\s+|in\s+the\s+|el\s+)?(\d+)', after)
        if mm:
            by_cycle[str(int(mm.group(1)) - 1)] = m.group(1)
        else:
            seq.append(m.group(1))
    modes = []
    for s in seq:
        if not modes or modes[-1] != s:
            modes.append(s)
    return by_cycle, modes


def _aliases(tr):
    a = set(_ALIASES.get(tr['role'], [])) | {tr['role']}
    toks = set(T.slug(tr.get('name', '')).split('_')) | set(T.slug(str(tr.get('gm_name', ''))).split('_'))
    return a | {t for t in toks if t in _ALL_ALIASES}


def _tok_matches(tok, aliases):
    if tok in aliases:
        return True
    return len(tok) >= 4 and any(len(a) >= 4 and (a.startswith(tok) or tok.startswith(a)) for a in aliases)


def match_entry(entry, tracks):
    """"tenor_sax_hook" -> ([pista lead], ['hook']).  Los tokens sin alias son modificadores."""
    token = re.sub(r'\(.*?\)', '', entry).strip()
    parts = [x for x in T.slug(token).split('_') if x]
    hits, used = [], set()
    for tr in tracks:
        al = _aliases(tr)
        m = [p for p in parts if _tok_matches(p, al)]
        if m:
            hits.append(tr)
            used |= set(m)
    return hits, [p for p in parts if p not in used], token


def _find_progression(progs, sec_slug, kind, rep, sec_name):
    if not progs:
        return None
    cs = canon(sec_slug)
    best, bscore = None, 0
    st = set(cs.split('_'))
    for key in progs:
        ck = canon(T.slug(key))
        if ck == cs:
            return key
        kt = set(ck.split('_'))
        score = len(st & kt) * 10 - 6 * len(kt - st)
        fam = {'pre': {'pre', 'pre_chorus', 'bridge'}, 'bridge': {'bridge'}, 'chorus': {'chorus'},
               'verse': {'verse'}, 'intro': {'intro'}, 'outro': {'outro'}, 'break': {'break', 'solo'}}.get(kind, set())
        if kt & fam or ck in fam:
            score += 5
        if score > bscore:
            best, bscore = key, score
    if best is not None and bscore > 4:
        return best
    return None


def _phrase_note(n, bb, bar_offset, max_bar, rep, where, beat_off=0.0):
    """Nota de frase (beat del tramo) -> {bar, beat, pitch, dur}; None si es invalida. beat_off=1 si los beats son base 1."""
    try:
        beat = float(n['beat']) - beat_off
        pitch = T.parse_pitch(n['pitch'])
        dur = float(n.get('dur', n.get('duration', 1)))
    except (KeyError, TypeError, ValueError):
        add(rep, 'warn', 'Lead "%s": nota invalida ignorada: %s' % (where, json.dumps(n)[:80]))
        return None
    bar = bar_offset + int(beat // bb)
    if beat < 0 or bar >= max_bar:
        add(rep, 'warn', 'Lead "%s": nota fuera de la seccion ignorada (beat %s).' % (where, n.get('beat')))
        return None
    return {'bar': bar, 'beat': round(beat % bb, 4), 'pitch': pitch, 'dur': dur}


def _phrases_from_shadow(mel, sections, bb, rep, beat_off=0.0):
    """phrases_beats_from_loop_start -> {section_id: [notas con bar/beat]}"""
    src = mel.get('phrases_beats_from_loop_start') or {}
    out = {}
    keys = list(src)
    for s in sections:
        sslug, fam = canon(s['id']), s['kind']
        sel = [k for k in keys if canon(T.slug(k)).startswith(sslug + '_') or canon(T.slug(k)) == sslug]
        how = 'exacto'
        if not sel:
            first = sslug.split('_')[0]
            famw = {'pre': 'bridge', 'chorus': 'chorus', 'verse': 'verse', 'outro': 'outro', 'intro': 'intro',
                    'bridge': 'bridge', 'break': 'break'}.get(fam, fam)
            cand = [k for k in keys if canon(T.slug(k)).split('_')[0] in (first, famw)]
            if first.startswith('verse') or famw == 'verse':
                num = re.findall(r'\d+', sslug)
                cand = [k for k in cand if not num or ('_' + num[0]) in canon(T.slug(k))] or cand
            sel, how = cand, 'por familia'
            if sel and 'final' in sslug and len(sel) > 1:
                sel = list(reversed(sel))
                how = 'por familia (orden invertido por "final")'
        if not sel:
            continue
        sel = sorted(sel, key=lambda k: T.slug(k)) if how == 'exacto' else sel
        loop_bars = s['bars'] // len(sel) if s['bars'] % len(sel) == 0 else None
        if not loop_bars:
            try:
                mx = max(float(n['beat']) + float(n.get('dur', 1)) for k in sel for n in src[k])
            except (KeyError, TypeError, ValueError):
                mx = s['bars'] * bb
            loop_bars = max(1, int(math.ceil(mx / bb)))
        notes = []
        for li, key in enumerate(sel):
            for n in src[key]:
                nn = _phrase_note(n, bb, li * loop_bars, s['bars'], rep, s['name'], beat_off)
                if nn:
                    notes.append(nn)
        out[s['id']] = notes
        add(rep, 'info', 'Lead "%s": %d notas de %s (%s, bucles de %d compases).' % (s['name'], len(notes), ', '.join(sel), how, loop_bars))
    return out


def _phrases_from_sections(mel, sections, bb, rep, beat_off=0.0):
    src = mel.get('lead_phrases_by_section') or {}
    out = {}
    for s in sections:
        for key in src:
            if T.slug(key) == T.slug(s['name']) or T.slug(key) == s['id']:
                notes = [nn for nn in (_phrase_note(n, bb, 0, s['bars'], rep, s['name'], beat_off) for n in src[key]) if nn]
                out[s['id']] = notes
    if out:
        add(rep, 'info', 'Lead: frases por seccion para %d secciones.' % len(out))
    return out


def _bend_cfg(text, default_prob):
    t = norm_text(text)
    cfg = {'enabled': True}
    m = re.search(r'(-?\d+(?:\.\d+)?)\s*semiton', t)
    if m:
        cfg['semitones'] = abs(float(m.group(1)))
    m = re.search(r'(\d+)\s*-\s*(\d+)\s*ticks', t)
    if m:
        cfg['beats'] = (int(m.group(1)) + int(m.group(2))) / 2.0 / 480.0
    else:
        m = re.search(r'(\d+)\s*ticks', t)
        if m:
            cfg['beats'] = int(m.group(1)) / 480.0
    cfg['prob'] = 0.5 if re.search(r'selected|never on every|only on|occasional|optional', t) else default_prob
    return cfg


def _bends_from_text(mel, rep):
    b = (mel or {}).get('bends') or {}
    d = {}
    for key, val in b.items():
        k = norm_text(key)
        if 'scoop' in k and isinstance(val, str):
            d['scoop'] = _bend_cfg(val, 1.0)
        elif 'fall' in k and isinstance(val, str):
            d['fall'] = _bend_cfg(val, 1.0)
    if not d:
        return {}
    d.setdefault('scoop', {'enabled': False})
    d.setdefault('fall', {'enabled': False})
    return {'lead': d}


def _parse_hats(text):
    ht = norm_text(text)
    hat = {}
    m = re.search(r'jitter\s*\+-?\s*(\d+)', ht) or re.search(r'\+-?\s*(\d+)', ht)
    if m:
        hat['jitter'] = int(m.group(1)) / 480.0
    m = re.search(r'omit\w*\s*(\d+)\s*-\s*(\d+)\s*%', ht)
    if m:
        hat['omit'] = [int(m.group(1)) / 100.0, int(m.group(2)) / 100.0]
    else:
        m = re.search(r'omit\w*\s*(\d+)\s*%', ht)
        if m:
            hat['omit'] = [int(m.group(1)) / 100.0] * 2
    if re.search(r'16th|sixteenth|semicorchea', ht):
        hat['grid'] = 0.25
    elif re.search(r'8th|eighth|corchea', ht):
        hat['grid'] = 0.5
    if re.search(r'low[- ]velocity|baja velocidad', ht):
        hat['vel_rand'] = [26, 44]
    m = re.search(r'(\d+)\s*%[^+]*\+\s*(\d+)', ht)
    if m:
        hat['drag'] = [int(m.group(1)) / 100.0, int(m.group(2)) / 480.0]
    elif re.search(r'late|arrastr', ht):
        hat['drag'] = [0.15, 0.0375]
    return hat


def _track_hints(tr, text):
    """Texto descriptivo del rol -> CC de ataque/release (FluidSynth: CC73/CC72)."""
    t = norm_text(text)
    if re.search(r'slow attack', t):
        tr['attack'] = 100
    elif re.search(r'soft attack|breathy', t):
        tr['attack'] = 80
    if re.search(r'long release', t):
        tr['release'] = 100


def _parse_render(mr, rep):
    if not isinstance(mr, dict):
        return None
    txt = norm_text(json.dumps(mr, ensure_ascii=False))
    fx = {}
    m = re.search(r'low-?pass[^0-9]{0,40}(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*k', txt)
    if m:
        lo = float(m.group(1))
        hi = float(m.group(2)) if m.group(2) else lo
        fx['lowpass_hz'] = int((lo + hi) / 2.0 * 1000)
    m = re.search(r'(-\d+(?:\.\d+)?)\s*lufs', txt)
    if m:
        fx['loudness_lufs'] = float(m.group(1))
    m = re.search(r'(\d+)\s*-\s*(\d+)\s*second[^"]*fade', txt) or re.search(r'fade[^"]*?(\d+)\s*-\s*(\d+)\s*s', txt)
    if m:
        fx['fade_out_seconds'] = (int(m.group(1)) + int(m.group(2))) / 2.0
        fx['fade_curve'] = 'exp' if 'exponential' in txt else 'tri'
    noise = {}
    if 'hiss' in txt:
        noise['hiss'] = {'level': 0.0012}
    if 'crackle' in txt:
        noise['crackle'] = {'per_second': 3.0, 'level': 0.03}
    if noise:
        edge = bool(re.search(r'mostly in intro|intro/outro|intro and outro|intro y outro', txt))
        prof = {'intro': 1.0, 'outro': 1.0, 'default': 0.25} if edge else {'default': 1.0}
        for v in noise.values():
            v['profile'] = dict(prof)
        fx['noise'] = noise
    if fx:
        fx['enabled'] = True
        add(rep, 'info', 'Render FX detectados: ' + ', '.join(k for k in fx if k not in ('enabled', 'fade_curve')) +
            ' (se aplican al exportar MP3/WAV con FFmpeg; el MP3 del navegador aplica lowpass, ruido y fade).')
    return fx or None


_GUARD_MAP = [
    ('four_on_floor', r'four[- ]on[- ]the[- ]floor|cuatro por cuatro'),
    ('mallet_sparse', r'vibraphone.*(sparse|constant|shimmer)|constant vibraphone'),
    ('lead_mono_range', r'monophon|monofon'),
    ('lead_coverage', r'fill every rest|constant fills|clear rests|leave space|negative space'),
    ('lead_mallet_overlap', r'overlaps? between sax and vibraphone|not .*double the sax'),
    ('bass_kick', r'masking kick|bass and kick'),
    ('motif_repeat', r'chorus motif|repeats with consistent rhythm'),
    ('section_bounds', r'end times stay within|note boundaries'),
]


def from_spec(obj, rep, preset_opt=None):
    g_in = obj.get('global') or {}
    meta_in = obj.get('meta') or {}
    name = meta_in.get('name') or obj.get('title') or obj.get('name') or 'Proyecto'
    desc = meta_in.get('description') or obj.get('description') or ''
    blob = norm_text(json.dumps(obj, ensure_ascii=False))
    notes_in = obj.get('midi_implementation_notes') or {}
    notes_txt = norm_text(json.dumps(notes_in, ensure_ascii=False))
    preset = preset_opt or g_in.get('preset')
    if preset not in S.PRESETS:
        hint = norm_text(desc + ' ' + json.dumps(obj.get('rhythm', {}), ensure_ascii=False))
        preset = 'triphop' if re.search(r'trip[ -]?hop', hint) else 'synthwave'
        add(rep, 'info', 'Genero detectado: %s (cambialo en Global > Preset).' % preset)
    g = dict(GLOBAL_DEFAULTS)
    g['bpm'] = _num(g_in.get('bpm') or obj.get('bpm') or meta_in.get('bpm') or obj.get('tempo'), 100)
    ts = g_in.get('time_signature') or obj.get('time_signature') or [4, 4]
    if isinstance(ts, str) and '/' in ts:
        ts = [int(x) for x in ts.split('/')]
    g['time_signature'] = [int(ts[0]), int(ts[1])]
    g['ticks_per_beat'] = int(g_in.get('ticks_per_beat') or 480)
    g['key'] = str(g_in.get('key_signature') or g_in.get('key') or obj.get('key') or g_in.get('mode') or 'C major')
    if 'seed' in g_in: g['seed'] = g_in['seed']
    g['preset'] = preset
    bb = g['time_signature'][0] * 4.0 / g['time_signature'][1]
    # ---- notas de implementacion (beat_indexing, canales, ...)
    bi = norm_text(notes_in.get('beat_indexing', '') or (obj.get('melody') or {}).get('beat_indexing', ''))
    beat_off = 1.0 if re.search(r'1[- ]based|one[- ]based|base 1', bi) else 0.0
    if beat_off:
        add(rep, 'info', 'beat_indexing = 1-based: los beats de las frases se desplazan -1 (beat 1.0 = inicio del bucle).')
    # ---- dinamica global (tope de velocidad)
    dyn_txt = norm_text(json.dumps(obj.get('dynamics') or {}, ensure_ascii=False))
    m = re.search(r'peaks?\s+(?:around|at|near|of)\s*(\d+)(?:\s*-\s*(\d+))?', dyn_txt)
    if m:
        g['velocity_cap'] = int(m.group(2) or m.group(1))
        g['cap_drums'] = True
        add(rep, 'info', 'Tope de velocidad %d (dynamics.range: "peaks around ...") aplicado a todas las pistas.' % g['velocity_cap'])

    # ---- pistas
    tin = [dict(t) for t in (obj.get('tracks') or []) if isinstance(t, dict)]
    if not tin:
        add(rep, 'warn', 'El JSON no trae "tracks": se crea un set por defecto (pad, bajo, lead, strings, arpegio, bateria).')
        tin = [{'role': r} for r in ('pad', 'bass', 'lead', 'strings', 'arp', 'drums')]
    base = _channel_base(tin, rep, notes_in)
    add(rep, 'info', 'Canales interpretados con base %d.' % base)
    tracks, used = [], set()
    declared_prog = {}
    for i, t in enumerate(tin):
        role = infer_role(t)
        d = dict(S.ROLE_DEFAULTS[role])
        tid = unique_id(role, used)
        prog = t.get('program')
        if prog is None:
            prog = T.resolve_program(t.get('gm_name') or t.get('instrument') or t.get('name'))
            if prog is None or role == 'drums':
                prog = d['program']
        else:
            prog = T.resolve_program(prog)
        ch = t.get('channel')
        ch = (ch + (1 - base)) if isinstance(ch, int) else (10 if role == 'drums' else i + 1)
        d.update(id=tid, name=t.get('name') or tid, role=role, channel=10 if role == 'drums' else ch, program=prog,
                 enabled=True, mute=False, solo=False)
        if 'detune_bend' not in t and 'detune' not in t and any(k.startswith('cc7') for k in t):
            d['detune'] = 0          # el JSON describe la pista con precision y no pide desafinacion: no se inventa
        for src, dst in (('cc7_volume', 'volume'), ('cc10_pan', 'pan'), ('cc91_reverb', 'reverb'), ('cc93_chorus', 'chorus'),
                         ('volume', 'volume'), ('pan', 'pan'), ('reverb', 'reverb'), ('chorus', 'chorus'),
                         ('detune_bend', 'detune'), ('detune', 'detune'), ('timing_offset_ticks', 'offset_ticks'),
                         ('offset_ticks', 'offset_ticks'), ('jitter_ticks', 'jitter_ticks'), ('gain', 'gain')):
            if src in t and _num(t[src]) is not None:
                d[dst] = _num(t[src])
        if isinstance(t.get('range'), list) and len(t['range']) == 2:
            d['range'] = [int(t['range'][0]), int(t['range'][1])]
        if isinstance(t.get('role'), str) and t['role'] not in S.ROLES:
            _track_hints(d, t['role'])
        if role == 'drums':
            if isinstance(t.get('map'), dict):
                d['drum_map'] = {k: int(v) for k, v in t['map'].items()}
            hz = t.get('humanization')
            if isinstance(hz, dict):
                dh = {}
                for k, key in (('kick_ticks', 'kick'), ('snare_ticks', 'snare'), ('clap_ticks', 'clap'), ('rim_ticks', 'rim')):
                    if _num(hz.get(k)) is not None:
                        dh[key] = hz[k] / 480.0
                hat = _parse_hats(hz.get('hats', ''))
                if hat:
                    dh['hat'] = hat
                if dh:
                    d['drum_humanize'] = dh
        declared_prog[tid] = d['program']
        tracks.append(d)
    add(rep, 'info', 'Pistas: ' + ', '.join('%s=%s' % (t['id'], t['name']) for t in tracks))

    # ---- armonia
    harm = obj.get('harmony') or {}
    progs = harm.get('progressions') or obj.get('progressions') or {}
    default_bars, per_kind = parse_rhythm(harm.get('harmonic_rhythm') or '')
    if default_bars != 1.0:
        add(rep, 'info', 'Ritmo armonico: %g compases por acorde.' % default_bars)
    # ---- secciones
    arr = (obj.get('arrangement') or {}).get('sections') or obj.get('sections') or []
    if not arr:
        add(rep, 'warn', 'Sin secciones: se crea una estructura intro/verso/coro/outro por defecto.')
        arr = [{'name': 'Intro', 'bars': 8}, {'name': 'Verso', 'bars': 16}, {'name': 'Coro', 'bars': 16},
               {'name': 'Outro', 'bars': 8}]
    names = [s.get('name', 'seccion') for s in arr]
    sections, sid_used, occ = [], set(), {}
    for i, s in enumerate(arr):
        nm = s.get('name') or 'Seccion %d' % (i + 1)
        kind = infer_kind(nm, i, names)
        sid = unique_id(nm, sid_used)
        bars = int(_num(s.get('bars'), 8))
        sd = {'id': sid, 'name': nm, 'kind': kind, 'bars': bars, 'final': 'final' in T.slug(nm) or 'last' in T.slug(nm),
              'occurrence': occ.get(kind, 0)}
        occ[kind] = occ.get(kind, 0) + 1
        key = _find_progression(progs, sid, kind, rep, nm)
        if key is None and progs:
            key = next(iter(progs))
            add(rep, 'warn', 'Seccion "%s": sin progresion propia; se usa "%s".' % (nm, key))
        elif key is not None and canon(T.slug(key)) != canon(sid):
            add(rep, 'info', 'Seccion "%s" -> progresion "%s".' % (nm, key))
        sd['chords'] = list(progs[key]) if key else ['C']
        sd['chord_bars'] = per_kind.get(kind, default_bars)
        vel = s.get('velocity')
        if isinstance(vel, list) and len(vel) == 2:
            sd['velocity'] = [vel[0], vel[1]]
        elif isinstance(s.get('velocity_pitched'), list) and len(s['velocity_pitched']) == 2:
            lo, hi = s['velocity_pitched']
            sd['velocity'] = [round((lo + hi) / 2.0)] * 2
        if s.get('start_bar') is not None:
            sd['_declared_start'] = int(s['start_bar'])
        sd['_instruments'] = s.get('instruments')
        sd['_text'] = ' '.join(str(s.get(k, '')) for k in ('strings', 'notes'))
        sections.append(sd)
    pos = 1
    for sd in sections:
        ds = sd.pop('_declared_start', None)
        if ds is not None and ds != pos:
            add(rep, 'warn', 'Seccion "%s": start_bar declarado %d, pero por las duraciones empieza en %d.' % (sd['name'], ds, pos))
        pos += sd['bars']

    # ---- bloques por defecto + instrumentos de cada seccion
    unsupported = []
    seen_msgs = set()
    for sd in sections:
        blocks = {t['id']: S.default_block(preset, sd, t['role']) for t in tracks}
        inst = sd.pop('_instruments', None)
        text = sd.pop('_text', '')
        if isinstance(inst, list) and inst:
            mentioned = {}
            for entry in inst:
                e = norm_text(entry)
                fb, tb = None, None
                m = re.search(r'desde\s+compas\s+(\d+)', e)
                if m: fb = int(m.group(1)) - 1
                m = re.search(r'compases?\s+(\d+)\s*-\s*(\d+)', e)
                if m: fb, tb = int(m.group(1)) - 1, int(m.group(2))
                hit, mods, token = match_entry(entry, tracks)
                if not hit:
                    msg = '"%s" no corresponde a una pista (textura de render): se maneja en Render FX.' % token
                    if msg not in seen_msgs:
                        seen_msgs.add(msg)
                        add(rep, 'info', msg)
                for t in hit:
                    mentioned[t['id']] = (fb, tb, mods)
            for t in tracks:
                b = blocks[t['id']]
                if t['id'] in mentioned:
                    fb, tb, mods = mentioned[t['id']]
                    b['enabled'] = b['style'] != 'none'
                    if fb is not None: b['from_bar'] = fb
                    if tb is not None: b['to_bar'] = tb
                    if mods:
                        S.apply_modifiers(b, t['role'], mods, preset, sd['kind'])
                        add(rep, 'info', 'Seccion "%s": %s con modificador(es) %s.' % (sd['name'], t['id'], ', '.join(mods)))
                else:
                    b['enabled'] = False
        by_cycle, modes = parse_modes(text)
        has_strings = any(t['role'] == 'strings' for t in tracks)
        if (by_cycle or modes) and not has_strings:
            msg = 'El campo "strings" de las secciones (full/bare) se ignora: no hay pista de strings.'
            if msg not in seen_msgs:
                seen_msgs.add(msg)
                add(rep, 'info', msg)
        for t in tracks:
            if t['role'] == 'strings' and blocks[t['id']]['style'] == 'sustain':
                p = blocks[t['id']]['params']
                if by_cycle:
                    p.pop('modes', None); p['modes_by_cycle'] = by_cycle
                elif modes:
                    p.pop('modes_by_cycle', None); p['modes'] = modes
        # la velocidad de la seccion manda sobre los valores por defecto de cada bloque
        if sd.get('velocity'):
            hi = max(sd['velocity']) if isinstance(sd['velocity'], (list, tuple)) else sd['velocity']
            for t in tracks:
                b = blocks[t['id']]
                if t['role'] != 'drums':
                    b.pop('velocity', None)
                else:
                    b['params']['vel_scale'] = round(max(0.5, min(1.1, hi / 95.0)), 3)
        sd['blocks'] = blocks

    # ---- texto de ritmo del bajo ("one long note every 2 bars", "one long root note per bar")
    rb = (obj.get('rhythm') or {}).get('bass')
    if isinstance(rb, dict):
        bass_t = next((t for t in tracks if t['role'] == 'bass'), None)
        for key, txt in rb.items():
            tt = norm_text(txt)
            m = re.search(r'one long (?:root )?note every (\d+) bars?', tt)
            per_bar = re.search(r'one long (?:root )?note per bar', tt)
            if not bass_t or not (m or per_bar):
                continue
            ck = canon(T.slug(key))
            for sd in sections:
                if canon(sd['id']) == ck or (ck == 'bridge' and 'bridge' in sd['id']) or (ck in ('pre_chorus', 'prechorus') and sd['kind'] == 'pre'):
                    b = sd['blocks'].get(bass_t['id'])
                    if not b:
                        continue
                    n = int(m.group(1)) if m else 1
                    b['style'] = 'pattern'
                    b['params'] = {'patterns': [[[0, 'R', round(n * bb - 0.4, 2), 0]]] + [[]] * (n - 1),
                                   'approach': {'enabled': False}, 'slide_in': {'every': 0}, 'slide_out': False}
                    add(rep, 'info', 'Bajo "%s": una nota larga cada %d compas(es) (rhythm.bass.%s).' % (sd['name'], n, key))

    # ---- lead
    mel = obj.get('melody') or {}
    phrases = {}
    phrases.update(_phrases_from_shadow(mel, sections, bb, rep, beat_off))
    phrases.update(_phrases_from_sections(mel, sections, bb, rep, beat_off))
    lp = obj.get('lead')
    if isinstance(lp, dict) and isinstance(lp.get('phrases'), dict):
        phrases.update(lp['phrases'])
    bends = _bends_from_text(mel, rep)
    lead_t = next((t for t in tracks if t['role'] == 'lead'), None)
    if bends.get('lead') and lead_t:
        for sd in sections:
            b = sd['blocks'].get(lead_t['id'])
            if b and b['style'] in ('auto', 'phrases', 'generative', 'hold'):
                b['params']['bends'] = copy.deepcopy(bends['lead'])
        add(rep, 'info', 'Bends del lead: scoop %s / caida %s.' % (json.dumps(bends['lead']['scoop']), json.dumps(bends['lead']['fall'])))
    # ---- final
    ending = {'fade_out': {'enabled': False, 'exponent': 1.5, 'cc': 11, 'start': {'section': 'last', 'bar': 0}},
              'tape_stop': {'enabled': False, 'bars': 2, 'semitones': -8.4, 'range': 12, 'exponent': 1.7}}
    if re.search(r'tape[ -]?stop|cinta que se apaga', blob):
        ending['tape_stop']['enabled'] = True
        m = re.search(r'ultimos\s+(\d+)\s+compases', blob)
        if m: ending['tape_stop']['bars'] = int(m.group(1))
        add(rep, 'info', 'Tape-stop activado (%d compases finales).' % ending['tape_stop']['bars'])
    if re.search(r'fade', blob) and (sections and sections[-1]['kind'] == 'outro'):
        ending['fade_out']['enabled'] = True
        add(rep, 'info', 'Fade out (CC11) activado en el outro.')
    # ---- render FX (parte "no MIDI")
    render = _parse_render(obj.get('mp3_render'), rep)
    if norm_text(notes_in.get('non_midi_rendering', '')):
        add(rep, 'info', 'Instrucciones "no MIDI" (reverb, chorus, hiss, crackle, low-pass, loudness, fades): se aplican como CC91/CC93 y Render FX al exportar audio.')
    if any('gain' in t for t in tin):
        unsupported.append('"gain" por pista no es un evento MIDI: solo afecta a la vista previa del navegador (no al MIDI ni al render de FluidSynth).')
    if re.search(r'stereo width|keep low end mono', blob):
        unsupported.append('Ancho estereo / "low end mono": solo se aproxima con CC10 (pan); el bajo se mantiene centrado.')
    if render and 'loudness_lufs' in render:
        unsupported.append('Loudness objetivo (%.0f LUFS): se aplica con FFmpeg (loudnorm) al exportar MP3/WAV en el servidor; el MP3 del navegador solo normaliza el pico.' % render['loudness_lufs'])
    if re.search(r'soundfont|generaluser|fluidsynth', blob):
        unsupported.append('Soundfont recomendado (GeneralUser-GS u otro GM): el motor no lo descarga; copia tu .sf2 a soundfonts/ (ver README).')
    # ---- guardrails pedidos por el texto del JSON
    gtxt = norm_text(json.dumps({k: obj.get(k) for k in ('claude_generation_brief', 'musical_appeal_engine', 'validation', 'midi_implementation_notes')}, ensure_ascii=False))
    guard = {gk: True for gk, rx in _GUARD_MAP if re.search(rx, gtxt)}
    declared = {'bpm': g['bpm'], 'time_signature': g['time_signature'], 'total_bars': _num(g_in.get('total_bars')),
                'duration_seconds': _num(g_in.get('duration_seconds')), 'tracks': len(tracks), 'programs': declared_prog,
                'ranges': {t['id']: t['range'] for t in tracks}}
    project = {'schema': SCHEMA, 'meta': {'name': name, 'description': desc, 'declared': declared}, 'global': g, 'tracks': tracks,
               'sections': sections, 'lead': {'phrases': phrases}, 'automation': S.default_automation(preset, sections),
               'ending': ending}
    if render:
        project['render'] = render
    if guard:
        project['guardrails'] = guard
    if unsupported:
        project['meta']['unsupported'] = unsupported
        for u in unsupported:
            add(rep, 'warn', 'Limite: ' + u)
    if obj.get('automation'):
        project['automation'] = obj['automation']
    if meta_in.get('note'):
        project['meta']['note'] = meta_in['note']
        mb = re.search(r'(\d+)\s*bpm', norm_text(meta_in['note']))
        if mb and float(mb.group(1)) != g['bpm']:
            add(rep, 'warn', 'meta.note menciona %s BPM pero global.bpm = %g: se usa global.bpm.' % (mb.group(1), g['bpm']))
    return project


# --------------------------------------------------------------------------
def finalize_project(p, rep, preset_opt=None):
    p.setdefault('schema', SCHEMA)
    p.setdefault('meta', {})
    g = dict(GLOBAL_DEFAULTS)
    g.update(p.get('global') or {})
    if preset_opt in S.PRESETS:
        g['preset'] = preset_opt
    if g['preset'] not in S.PRESETS:
        g['preset'] = 'synthwave'
    ts = g['time_signature']
    g['time_signature'] = [int(ts[0]), int(ts[1])]
    p['global'] = g
    used = set()
    for i, t in enumerate(p.get('tracks') or []):
        role = t.get('role') if t.get('role') in S.ROLES else infer_role(t)
        d = dict(S.ROLE_DEFAULTS[role])
        d.update({k: v for k, v in t.items() if v is not None or k == 'program'})
        d['role'] = role
        d['id'] = unique_id(t.get('id') or role, used)
        d.setdefault('name', d['id'])
        d.setdefault('enabled', True); d.setdefault('mute', False); d.setdefault('solo', False)
        if role == 'drums':
            d['channel'] = 10
        else:
            d['channel'] = int(d.get('channel') or i + 1)
        if d.get('program') is not None:
            d['program'] = T.resolve_program(d['program'])
        p['tracks'][i] = d
    if not p.get('tracks'):
        raise ValueError('El proyecto no tiene pistas.')
    tids = [t['id'] for t in p['tracks']]
    chans = {}
    for t in p['tracks']:
        if t['role'] != 'drums':
            chans.setdefault(t['channel'], []).append(t['id'])
    for ch, lst in chans.items():
        if len(lst) > 1:
            add(rep, 'warn', 'Canal %d compartido por %s.' % (ch, ', '.join(lst)))
    secs = p.get('sections') or []
    sused, occ = set(), {}
    for i, s in enumerate(secs):
        s['id'] = unique_id(s.get('id') or s.get('name') or 'sec', sused)
        s.setdefault('name', s['id'])
        s['bars'] = max(1, int(_num(s.get('bars'), 8)))
        s['kind'] = s.get('kind') if s.get('kind') in S.KINDS else infer_kind(s['name'], i, [x.get('name', '') for x in secs])
        s.setdefault('final', False)
        s['occurrence'] = occ.get(s['kind'], 0)
        occ[s['kind']] = occ.get(s['kind'], 0) + 1
        s.setdefault('chords', ['C'])
        s.setdefault('chord_bars', 1)
        vel = s.get('velocity')
        if isinstance(vel, bool):
            s.pop('velocity', None)
        elif isinstance(vel, (int, float)):
            s['velocity'] = [int(vel), int(vel)]
            add(rep, 'warn', 'Seccion "%s": velocity escalar (%s); se usa [%s, %s] (el motor espera un rango ini-fin).' % (s['name'], vel, int(vel), int(vel)))
        elif isinstance(vel, (list, tuple)) and len(vel) == 1:
            s['velocity'] = [vel[0], vel[0]]
            add(rep, 'warn', 'Seccion "%s": velocity con un solo valor (%s); se usa [%s, %s].' % (s['name'], vel[0], vel[0], vel[0]))
        bl = s.setdefault('blocks', {})
        if not p.get('raw'):
            for t in p['tracks']:
                if t['id'] not in bl:
                    bl[t['id']] = S.default_block(g['preset'], s, t['role'])
                b = bl[t['id']]
                b.setdefault('enabled', True); b.setdefault('params', {}); b.setdefault('from_bar', 0); b.setdefault('to_bar', None)
                valid = S.STYLE_SCHEMA.get(t['role'], {})
                if b.get('style') not in valid:
                    if b.get('enabled', True):   # los bloques apagados no suenan: no hace falta avisar
                        add(rep, 'warn', 'Seccion "%s" / %s: estilo "%s" invalido para el rol; se usa el predeterminado.' % (s['name'], t['id'], b.get('style')))
                    en = bool(b.get('enabled', True))   # default_block puede traer enabled=True: no reactivar un bloque apagado
                    b.update(S.default_block(g['preset'], s, t['role']))
                    if not en:
                        b['enabled'] = False
            for k in list(bl):
                if k not in tids:
                    del bl[k]
        for sym in {(c.get('chord') if isinstance(c, dict) else str(c).rsplit(':', 1)[0]) for c in s['chords']}:
            try:
                T.parse_chord(sym)
            except ValueError:
                add(rep, 'warn', 'Seccion "%s": acorde "%s" no reconocido.' % (s['name'], sym))
    p['sections'] = secs
    p.setdefault('lead', {}).setdefault('phrases', {})
    p.setdefault('automation', [])
    e = p.setdefault('ending', {})
    e.setdefault('fade_out', {'enabled': False, 'exponent': 1.5, 'cc': 11, 'start': {'section': 'last', 'bar': 0}})
    e.setdefault('tape_stop', {'enabled': False, 'bars': 2, 'semitones': -8.4, 'range': 12, 'exponent': 1.7})
    return p
