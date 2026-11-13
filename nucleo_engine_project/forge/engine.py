"""Motor: proyecto canonico (dict) -> notas -> MIDI + eventos para vista previa + informe."""
import base64
import bisect
import math
import random

from . import styles as S
from . import theory as T
from . import voicing as V
from .midiwriter import MidiTrack, build_midi

PITCHED = ('pad', 'strings', 'keys', 'bass', 'arp', 'mallet', 'lead')
HUM_KEY = {'kick': 'kick', 'kick2': 'kick', 'snare': 'snare', 'snare2': 'snare', 'clap': 'clap', 'rim': 'rim',
           'rimshot': 'rim', 'closed_hat': 'hat', 'open_hat': 'hat'}


def clamp(x, a, b):
    return max(a, min(b, x))


def lerp(a, b, x):
    return a + (b - a) * clamp(x, 0.0, 1.0)


def deep_merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_path(d, path, default=None):
    cur = d
    for p in path.split('.'):
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def when_ok(w, k, nb, sec):
    """Condicion sobre el compas k (relativo a la seccion) de una seccion de nb compases."""
    if not w:
        return True
    if 'bars' in w and k not in w['bars']: return False
    if 'not_bars' in w and k in w['not_bars']: return False
    if 'from' in w and k < w['from']: return False
    if 'to' in w and k >= w['to']: return False
    if w.get('last') and k != nb - 1: return False
    if 'bar_mod' in w:
        m, r = w['bar_mod']
        if (k % max(1, int(m))) not in (r if isinstance(r, list) else [r]):
            return False
    if w.get('cycle_parity'):
        cb = w.get('cycle_bars') or (w['bar_mod'][0] if 'bar_mod' in w else sec.cycle_bars)
        odd = (k // max(1, int(cb))) % 2 == 1
        if (w['cycle_parity'] == 'odd') != odd:
            return False
    if 'final' in w and bool(sec.d.get('final')) != bool(w['final']): return False
    if 'occurrence_min' in w and sec.d.get('occurrence', 0) < w['occurrence_min']: return False
    if 'occurrence_max' in w and sec.d.get('occurrence', 0) > w['occurrence_max']: return False
    return True


# --------------------------------------------------------------------------
# Timeline
# --------------------------------------------------------------------------
class Span(object):
    __slots__ = ('t0', 't1', 'sym', 'chord', 'sec', 'k0')

    def __init__(self, t0, t1, sym, chord, sec, k0):
        self.t0, self.t1, self.sym, self.chord, self.sec, self.k0 = t0, t1, sym, chord, sec, k0


def _chord_tokens(chords, default_bars):
    out = []
    for c in (chords or ['C']):
        if isinstance(c, dict):
            out.append((str(c.get('chord', 'C')), float(c.get('bars', default_bars))))
            continue
        s, bars = str(c).strip(), default_bars
        if ':' in s:
            s, b = s.rsplit(':', 1)
            try:
                bars = float(b)
            except ValueError:
                s = s + ':' + b
        out.append((s, bars))
    return out


def _replace_range(segs, a, b, new):
    out = []
    for s0, s1, sym in segs:
        if s1 <= a + 1e-9 or s0 >= b - 1e-9:
            out.append([s0, s1, sym])
            continue
        if s0 < a - 1e-9:
            out.append([s0, a, sym])
        if s1 > b + 1e-9:
            out.append([b, s1, sym])
    for p0, p1, sym in new:
        out.append([a + p0, a + p1, sym])
    out.sort(key=lambda s: s[0])
    return out


class Sec(object):
    def __init__(self, d, idx, start_bar, bb, ctx):
        self.d, self.idx, self.id = d, idx, d['id']
        self.name, self.kind, self.bars = d.get('name', d['id']), d.get('kind', 'verse'), int(d['bars'])
        self.start_bar, self.bb = start_bar, bb
        self.t0, self.t1 = start_bar * bb, (start_bar + self.bars) * bb
        toks = _chord_tokens(d.get('chords'), float(d.get('chord_bars', 1) or 1))
        self.cycle_bars = int(d.get('cycle_bars') or max(1, math.ceil(sum(b for _, b in toks) - 1e-9)))
        total = self.bars * bb
        segs, t, i = [], 0.0, 0
        while t < total - 1e-9:
            sym, b = toks[i % len(toks)]
            e = min(total, t + max(0.25, b * bb))
            segs.append([t, e, sym])
            t, i = e, i + 1
        for ov in d.get('chord_overrides') or []:
            when = ov.get('when') or {k: ov[k] for k in ('bars', 'bar_mod', 'cycle_parity', 'from', 'to') if k in ov}
            for k in range(self.bars):
                if when_ok(when, k, self.bars, self):
                    segs = _replace_range(segs, k * bb, (k + 1) * bb, ov.get('split') or [])
        merged = []
        for s in segs:
            if merged and merged[-1][2] == s[2] and abs(merged[-1][1] - s[0]) < 1e-9:
                merged[-1][1] = s[1]
            else:
                merged.append(list(s))
        self.spans = [Span(self.t0 + a, self.t0 + b, sym, ctx.chord(sym), self, int(a // bb + 1e-9))
                      for a, b, sym in merged]
        self.bar_segs = []
        for k in range(self.bars):
            a, b = k * bb, (k + 1) * bb
            self.bar_segs.append([(max(s0, a) - a, min(s1, b) - a, sym) for s0, s1, sym in segs
                                  if s1 > a + 1e-9 and s0 < b - 1e-9])


class Note(object):
    __slots__ = ('t', 'd', 'p', 'v', 'nom', 'intent', 'alts', 'slide', 'bend', 'inst', 'removed', 'sec')

    def __init__(self, t, d, p, v, nom):
        self.t, self.d, self.p, self.v, self.nom = t, d, p, v, nom
        self.intent, self.alts, self.slide, self.bend, self.inst, self.removed, self.sec = \
            False, None, None, None, None, False, None


class Buf(object):
    def __init__(self, track, ctx):
        self.track, self.ctx, self.notes = track, ctx, []
        self.role = track['role']

    def add(self, nominal, dur, pitch, vel, rng, legato=1.0, jit=None, extra=0.0, intent=False, sec=None):
        tr, ctx = self.track, self.ctx
        tpb = ctx.tpb
        j = (tr.get('jitter_ticks', 5) / float(tpb) if jit is None else jit) * ctx.humanize
        t = max(0.0, nominal + tr.get('offset_ticks', 0) / float(tpb) + extra + rng.gauss(0, j))
        end = nominal + dur * legato + rng.gauss(0, j * 0.5)
        d = max(0.06, end - t)
        vj = int(round(tr.get('vel_jitter', 4) * ctx.humanize))
        cap = ctx.vcap if (self.role != 'drums' or ctx.g.get('cap_drums')) else 127
        v = int(clamp(round(vel + (rng.randint(-vj, vj) if vj else 0)), 1, cap))
        n = Note(t, d, int(pitch), v, nominal)
        n.intent, n.sec = intent, sec.id if sec else None
        self.notes.append(n)
        return n

    def finalize(self):
        ns = sorted([n for n in self.notes if not n.removed], key=lambda n: (n.t, n.p))
        if self.track.get('mono') and self.role != 'drums':
            for i in range(len(ns) - 1):
                if ns[i].t + ns[i].d > ns[i + 1].t - 0.01:
                    ns[i].d = max(0.05, ns[i + 1].t - 0.01 - ns[i].t)
        else:
            by = {}
            for n in ns:
                by.setdefault(n.p, []).append(n)
            for lst in by.values():
                for i in range(len(lst) - 1):
                    if lst[i].t + lst[i].d > lst[i + 1].t - 0.01:
                        lst[i].d = max(0.05, lst[i + 1].t - 0.01 - lst[i].t)
        self.notes = ns


# --------------------------------------------------------------------------
# Contexto
# --------------------------------------------------------------------------
class Ctx(object):
    def __init__(self, project):
        self.project = project
        g = project.get('global', {})
        self.g = g
        ts = g.get('time_signature') or [4, 4]
        self.ts = (int(ts[0]), int(ts[1]))
        self.bb = self.ts[0] * 4.0 / self.ts[1]
        self.tpb = int(g.get('ticks_per_beat') or 480)
        self.bpm = float(g.get('bpm') or 100)
        self.seed = g.get('seed', 0)
        self.humanize = float(g.get('humanize', 1.0))
        self.vcap = int(g.get('velocity_cap', 110))
        self.bend_range = float(g.get('pitch_bend_range', 2))
        self.warnings, self._chords = [], {}
        self.key = T.parse_key(g.get('key') or 'C major')
        self.scale = T.scale_pcs(*self.key)
        tonic = self.key[0]
        self.tracks = project.get('tracks', [])
        self.tr_by_id = {t['id']: t for t in self.tracks}
        self.secs, bar = [], 0
        for i, s in enumerate(project.get('sections', [])):
            self.secs.append(Sec(s, i, bar, self.bb, self))
            bar += int(s['bars'])
        self.total_bars, self.total_beats = bar, bar * self.bb
        self.spans = [sp for s in self.secs for sp in s.spans]
        self._span_t0 = [sp.t0 for sp in self.spans]
        self.voice_log, self.repairs, self.drum_log, self.generated = {}, [], [], {}
        self.drum_map = {}
        for t in self.tracks:
            if t['role'] == 'drums' and t.get('drum_map'):
                self.drum_map = {T.slug(k): v for k, v in t['drum_map'].items()}

    def warn(self, msg):
        if msg not in self.warnings:
            self.warnings.append(msg)

    def chord(self, sym):
        if sym not in self._chords:
            ch, err = T.safe_chord(sym, self.key[0])
            if err:
                self.warn('Acorde no reconocido "%s": se usa una triada mayor.' % sym)
            self._chords[sym] = ch
        return self._chords[sym]

    def span_at(self, t):
        if not self.spans:
            return None
        i = bisect.bisect_right(self._span_t0, t + 1e-9) - 1
        return self.spans[clamp(i, 0, len(self.spans) - 1)]

    def rng(self, *parts):
        return random.Random('|'.join(str(p) for p in (self.seed,) + parts))

    def blocks(self, track):
        for sec in self.secs:
            b = (sec.d.get('blocks') or {}).get(track['id'])
            if not b or not b.get('enabled', True) or b.get('style') in (None, 'none'):
                continue
            fb = int(clamp(b.get('from_bar') or 0, 0, sec.bars))
            tb = b.get('to_bar')
            tb = sec.bars if tb is None else int(clamp(tb, fb, sec.bars))
            if tb <= fb:
                continue
            style = b['style']
            p = deep_merge(S.style_defaults(track['role'], style), b.get('params') or {})
            yield sec, b, p, fb, tb

    def vel(self, sec, block, role, frac):
        v = block.get('velocity')
        add = 0
        if v is None:
            v = sec.d.get('velocity')
            add = S.ROLE_VEL_OFFSET.get(role, 0)
        if v is None:
            v = 80
        val = lerp(v[0], v[1], frac) if isinstance(v, (list, tuple)) and len(v) >= 2 else (
            v[0] if isinstance(v, (list, tuple)) else v)
        out = val + add + float(block.get('_vel_add', 0) or 0)
        if add > 0 and block.get('velocity') is None:          # el offset de rol no debe superar el tope de la seccion
            sv = sec.d.get('velocity')
            if sv:
                top = max(sv) if isinstance(sv, (list, tuple)) else sv   # tolera velocity escalar (p.ej. 80 en vez de [80, 96])
                out = min(out, top)
        return out

    def root_pitch(self, chord, center, lo, hi):
        pc = chord.bass if chord.bass is not None else chord.root
        best = None
        for p in range(lo - 12, hi + 13):
            if p % 12 == pc:
                key = (abs(p - center), p)
                if best is None or key < best[0]:
                    best = (key, p)
        return best[1] if best else center


# --------------------------------------------------------------------------
# Generadores
# --------------------------------------------------------------------------
def _resolve_voicing(params, mode=None):
    vo = dict(params.get('voicing') or {})
    prof = vo.get('profile', 'full')
    if mode:
        base = V.resolve_profile(mode if isinstance(mode, str) else mode)
        for k in ('voices', 'min_gap', 'max_gap'):
            if vo.get(k) is not None:
                base[k] = vo[k]
        return base
    return V.resolve_profile(dict(vo, profile=prof))


def _clip_voice_range(track, params):
    r = get_path(params, 'voicing.range') or track.get('range') or [48, 72]
    return int(r[0]), int(r[1])


def gen_chordal(ctx, track, buf):
    role = track['role']
    events, plan = [], []
    for sec, block, p, fb, tb in ctx.blocks(track):
        style, bb = block['style'], ctx.bb
        lo, hi = _clip_voice_range(track, p)
        w0, w1 = sec.t0 + fb * bb, sec.t0 + tb * bb
        if style in ('stabs', 'broken') or p.get('hold') == 'bar':
            pieces = []
            for k in range(fb, tb):
                for a, b, sym in sec.bar_segs[k]:
                    pieces.append((sec.t0 + k * bb + a, sec.t0 + k * bb + b, sym, k))
        else:
            pieces = [(max(sp.t0, w0), min(sp.t1, w1), sp.sym, sp.k0) for sp in sec.spans
                      if sp.t1 > w0 + 1e-9 and sp.t0 < w1 - 1e-9]
        for t0, t1, sym, k in pieces:
            cyc = int((t0 - sec.t0) // bb // sec.cycle_bars)
            mode = None
            mbc, modes = p.get('modes_by_cycle'), p.get('modes')
            if mbc and str(cyc) in mbc:
                mode = mbc[str(cyc)]
            elif modes:
                mode = modes[cyc % len(modes)]
            prof = _resolve_voicing(p, mode)
            events.append((ctx.chord(sym), prof, lo, hi))
            plan.append(dict(sec=sec, block=block, p=p, t0=t0, t1=t1, sym=sym, mode=mode, fb=fb, tb=tb, k=k))
    if not events:
        return
    max_move = max([int(get_path(e['p'], 'voicing.max_move', 5) or 5) for e in plan] or [5])
    voiced = V.voice_sequence(events, max_move=max_move)
    log = ctx.voice_log.setdefault(track['id'], [])
    vmap = {}
    for ev, v in zip(plan, voiced):
        log.append(dict(t0=ev['t0'], sym=ev['sym'], mode=ev['mode'] or get_path(ev['p'], 'voicing.profile', 'full'),
                        notes=list(v), sec=ev['sec'].id))
        vmap[(ev['sec'].id, round(ev['t0'], 4))] = v
    rngs = {}
    for ev in plan:
        sec, block, p = ev['sec'], ev['block'], ev['p']
        rng = rngs.setdefault(sec.id, ctx.rng(track['id'], sec.id, block.get('seed', 0)))
        span_len = (ev['tb'] - ev['fb']) * ctx.bb
        v = vmap[(sec.id, round(ev['t0'], 4))]
        st = block['style']
        frac = (ev['t0'] - (sec.t0 + ev['fb'] * ctx.bb)) / max(1e-9, span_len)
        if st in ('sustain', 'hold'):
            vel = ctx.vel(sec, block, role, frac)
            rs = float(p.get('restrike_beats', 0) or 0)
            if rs > 0:
                t = ev['t0']
                while t < ev['t1'] - 0.25:
                    for pitch in v:
                        buf.add(t, min(rs, ev['t1'] - t), pitch, vel - (4 if t > ev['t0'] else 0), rng, legato=float(p.get('legato', 0.97)), sec=sec)
                    t += rs
            else:
                for pitch in v:
                    buf.add(ev['t0'], ev['t1'] - ev['t0'], pitch, vel, rng, legato=float(p.get('legato', 0.995)), sec=sec)
        elif st == 'tail':
            vel = ctx.vel(sec, block, role, frac)
            n_notes = max(1, int(p.get('notes_per_chord', 2)))
            top = sorted(v)[-n_notes:]
            ring = float(p.get('ring', 6))
            for i, pitch in enumerate(top):
                t = ev['t0'] + i * 0.75
                buf.add(t, min(ring, max(0.5, sec.t1 - t - 0.1)), pitch, vel - 3 * i, rng, legato=1.0, sec=sec)
    # stabs: por compas, con re-ataque al cambiar de acorde
    for sec, block, p, fb, tb in ctx.blocks(track):
        if block['style'] != 'stabs':
            continue
        rng = ctx.rng(track['id'], sec.id, block.get('seed', 0), 'stabs')
        rhythm = p.get('rhythm') or [[0, ctx.bb, 0]]
        for k in range(fb, tb):
            segs = sec.bar_segs[k]
            bar_t = sec.t0 + k * ctx.bb
            onsets = {}
            for r in rhythm:
                onsets[round(float(r[0]), 4)] = (float(r[1]), float(r[2]) if len(r) > 2 else 0.0)
            last_dv = 0.0
            for a, b, sym in segs:
                if round(a, 4) not in onsets:
                    onsets[round(a, 4)] = (None, None)
            order = sorted(onsets)
            for i, pos in enumerate(order):
                nxt = order[i + 1] if i + 1 < len(order) else ctx.bb
                hd, dv = onsets[pos]
                if dv is None:
                    dv = last_dv
                else:
                    last_dv = dv
                dur = (nxt - pos) if hd is None else min(hd, nxt - pos)
                seg = next((s for s in segs if s[0] - 1e-9 <= pos < s[1] - 1e-9), segs[-1])
                vv = vmap.get((sec.id, round(bar_t + seg[0], 4)))
                if not vv:
                    continue
                frac = (k - fb + pos / ctx.bb) / float(tb - fb)
                vel = ctx.vel(sec, block, role, frac) + dv
                for pitch in vv:
                    buf.add(bar_t + pos, dur, pitch, vel, rng, legato=float(p.get('legato', 0.97)), sec=sec)
    # acorde roto: notas de la voz una a una (keys)
    for sec, block, p, fb, tb in ctx.blocks(track):
        if block['style'] != 'broken':
            continue
        rng = ctx.rng(track['id'], sec.id, block.get('seed', 0), 'broken')
        step = max(0.25, float(p.get('step', 1.0)))
        pat = p.get('pattern_list') or S.ARP_PATTERNS.get(p.get('pattern', 'up'), S.ARP_PATTERNS['up'])
        ring, rest_p, accent = float(p.get('ring', 2.5)), float(p.get('rest_prob', 0) or 0), float(p.get('accent', 4))
        n = max(1, int(round(ctx.bb / step)))
        for k in range(fb, tb):
            bar_t = sec.t0 + k * ctx.bb
            for i in range(n):
                idx = pat[(k * n + i) % len(pat)]
                if idx is None or (rest_p and rng.random() < rest_p):
                    continue
                pos = i * step
                segs = sec.bar_segs[k]
                seg = next((sg for sg in segs if sg[0] - 1e-9 <= pos < sg[1] - 1e-9), segs[-1])
                vv = vmap.get((sec.id, round(bar_t + seg[0], 4)))
                if not vv:
                    continue
                vs = sorted(vv)
                frac = (k - fb + pos / ctx.bb) / float(max(1, tb - fb))
                vel = ctx.vel(sec, block, role, frac) + (accent if i == 0 else -2 * (i % 2))
                t = bar_t + pos
                buf.add(t, min(ring, max(0.5, sec.t1 - t - 0.1)), vs[int(idx) % len(vs)], vel, rng, legato=1.0, sec=sec)
    # notas de tension (clusters)
    for sec, block, p, fb, tb in ctx.blocks(track):
        rng = ctx.rng(track['id'], sec.id, 'tension')
        for rule in p.get('tension') or []:
            for k in range(fb, tb):
                if not when_ok(rule.get('when'), k, sec.bars, sec):
                    continue
                beat = float(rule.get('beat', 0))
                t = sec.t0 + k * ctx.bb + beat
                sp = ctx.span_at(t)
                ch = sp.chord
                q = rule.get('quality', 'all')
                is_minor = ch.true_third and ch.deg.get(3) == 3
                if (q == 'minor' and not is_minor) or (q == 'major' and (is_minor or not ch.true_third)):
                    continue
                pc = (ch.root + int(rule.get('offset', 1))) % 12
                near = int(rule.get('near', 60))
                pitch = min((x for x in range(near - 12, near + 13) if x % 12 == pc), key=lambda x: abs(x - near))
                buf.add(t, float(rule.get('dur', 1.5)), pitch, float(rule.get('vel', 50)), rng, sec=sec, intent=True)



def _lead_intervals(ctx, ref):
    """Intervalos (t0, t1, pitch) de la pista a la que responde el vibrafono."""
    out = []
    for key, b in ctx.generated.items():
        if key == ref or b.role == ref:
            out += [(n.t, n.t + n.d, n.p) for n in b.notes]
    return sorted(out)


def _clear_of(iv, p, t0, t1, mind):
    for a, b, q in iv:
        if a >= t1:
            break
        if b > t0 + 0.25 and min(b, t1) - max(a, t0) > 0.25 and abs(p - q) < mind:
            return False
    return True


def gen_mallet(ctx, track, buf):
    for sec, block, p, fb, tb in ctx.blocks(track):
        rng = ctx.rng(track['id'], sec.id, block.get('seed', 0))
        bb = ctx.bb
        lo, hi = (p.get('range') or track.get('range') or [72, 88])[:2]
        degs = [int(d) for d in (p.get('degrees') or [9, 5])]
        mind = int(p.get('min_distance', 5))
        iv = _lead_intervals(ctx, p.get('respond_to', 'lead'))
        w0, w1 = sec.t0 + fb * bb, sec.t0 + tb * bb

        def place(t, di, dur, vel):
            nxt = next((x[0] for x in iv if x[0] >= t), None)
            short = None if nxt is None else min(dur, nxt - t + 0.2)
            for k in range(len(degs)):
                pc = ctx.span_at(t).chord.tone(degs[(di + k) % len(degs)], color=True)
                if pc is None:
                    continue
                base = [x for x in range(lo, hi + 1) if x % 12 == pc]
                mid = (lo + hi) / 2.0 + rng.uniform(-3, 3)
                for pitch in sorted(base, key=lambda x: abs(x - mid)):
                    for d_try in ([dur] + ([short] if short is not None and short >= 0.75 and short < dur else [])):
                        if _clear_of(iv, pitch, t, t + d_try, mind):
                            buf.add(t, min(d_try, max(0.5, w1 - t - 0.1)), pitch, vel, rng, legato=1.0, sec=sec)
                            return True
            return False

        if block['style'] == 'pings':
            cnt = max(1, int(p.get('count', 2)))
            for i in range(cnt):
                k = fb + int((i + 0.5) * (tb - fb) / cnt)
                t = sec.t0 + k * bb + float(p.get('beat', 0.5))
                frac = (t - w0) / max(1e-9, w1 - w0)
                place(t, i, float(p.get('dur', 6)), ctx.vel(sec, block, 'mallet', frac))
            continue
        # replies: huecos del lead
        prob, min_gap, margin = float(p.get('prob', 0.5)), float(p.get('min_gap', 1.75)), float(p.get('margin', 0.5))
        frag = p.get('fragment') or [2, 3]
        glint = float(p.get('glint_gap', 1.0))
        step, dur, max_bar = float(p.get('step', 1.0)), float(p.get('dur', 2.5)), int(p.get('max_per_bar', 2))
        edges, prev = [], w0
        for a, b, q in iv:
            if b <= w0 or a >= w1:
                continue
            edges.append((prev, max(prev, a)))
            prev = max(prev, b)
        edges.append((prev, w1))
        per_bar, di = {}, rng.randint(0, 3)
        for g0, g1 in edges:
            g0 += margin
            g1 -= 0.25
            while g1 - g0 >= glint:
                win_end = min(g1, g0 + 8.0)
                if rng.random() < prob:
                    n = rng.randint(int(frag[0]), int(frag[1])) if g1 - g0 >= min_gap else 1    # huecos cortos: una sola nota
                    t = math.ceil(g0 * 2.0) / 2.0
                    for i in range(n):
                        bar = int(t // bb)
                        if t + 0.5 > win_end or per_bar.get(bar, 0) >= max_bar:
                            break
                        frac = (t - w0) / max(1e-9, w1 - w0)
                        if place(t, di, dur, ctx.vel(sec, block, 'mallet', frac) + rng.randint(-3, 3)):
                            per_bar[bar] = per_bar.get(bar, 0) + 1
                        di += 1
                        t += step
                g0 = win_end + margin


def _bass_pitch(kind, ch, center, lo, hi, ctx):
    r = ctx.root_pitch(ch, center, lo, hi)
    if kind == 'R': return r
    if kind == 'F': return r + ch.deg.get(5, 7)
    if kind == 'O': return r + 12
    if kind == 'T': return r + ch.deg.get(3, 4)
    if kind == 'S': return r + ch.deg.get(7, ch.deg.get(5, 7))
    return T.parse_pitch(kind)


def gen_bass(ctx, track, buf):
    lo, hi = (track.get('range') or [28, 52])[:2]
    for sec, block, p, fb, tb in ctx.blocks(track):
        rng = ctx.rng(track['id'], sec.id, block.get('seed', 0))
        center, bb = int(p.get('center', 38)), ctx.bb
        legato = float(p.get('legato', 0.92))
        if block['style'] == 'long':
            fifth_at = float(p.get('fifth_at', 0) or 0)
            for sp in sec.spans:
                t0, t1 = max(sp.t0, sec.t0 + fb * bb), min(sp.t1, sec.t0 + tb * bb)
                if t1 - t0 < 0.5:
                    continue
                frac = (t0 - sec.t0 - fb * bb) / ((tb - fb) * bb)
                vel = ctx.vel(sec, block, 'bass', frac)
                r = _bass_pitch('R', sp.chord, center, lo, hi, ctx)
                if fifth_at and (t1 - t0) > fifth_at + 1:
                    buf.add(t0, fifth_at, r, vel, rng, legato=1.0, sec=sec)
                    buf.add(t0 + fifth_at, t1 - t0 - fifth_at - 0.2, _bass_pitch('F', sp.chord, center, lo, hi, ctx),
                            vel - 12, rng, legato=1.0, sec=sec)
                else:
                    buf.add(t0, t1 - t0 - 0.2, r, vel, rng, legato=1.0, sec=sec)
            continue
        patterns = p.get('patterns') or S.BASS_SETS.get(p.get('pattern_set'), S.BASS_SETS['synth_verse'])
        ap = p.get('approach') or {}
        ap_on, ap_every, ap_off = ap.get('enabled', True), max(1, int(ap.get('every', 2))), int(ap.get('offset', 1))
        slide_every = int(get_path(p, 'slide_in.every', 0) or 0)
        slide_st = float(p.get('slide_semitones', 2))
        light_bars, light_delta = int(p.get('light_bars', 0) or 0), int(p.get('light_delta', -8))
        for k in range(fb, tb):
            bar_t = sec.t0 + k * bb
            patt = patterns[k % len(patterns)] if patterns else []
            vbase = ctx.vel(sec, block, 'bass', (k - fb) / float(max(1, tb - fb)))
            if k - fb < light_bars:
                vbase += light_delta
            for idx, ent in enumerate(patt):
                pos, kind, dur, dv = float(ent[0]), ent[1], float(ent[2]), float(ent[3]) if len(ent) > 3 else 0.0
                t = bar_t + pos
                sp = ctx.span_at(t)
                is_last = idx == len(patt) - 1
                alts = None
                if kind == 'A' or (ap_on and is_last and pos >= bb - 0.75 and (k % ap_every) == ap_off % ap_every):
                    nxt = ctx.span_at(bar_t + bb + 0.01)
                    cur = _bass_pitch('R', sp.chord, center, lo, hi, ctx)
                    if nxt is not None and nxt.chord.root != sp.chord.root or kind == 'A':
                        nr = _bass_pitch('R', (nxt or sp).chord, center, lo, hi, ctx)
                        cs = sorted([nr - 1, nr + 1], key=lambda c: (abs(c - cur), c))
                        pitch, alts = cs[0], [cs[1], _bass_pitch('F', sp.chord, center, lo, hi, ctx), cur]
                    else:
                        pitch = _bass_pitch('R' if kind == 'A' else kind, sp.chord, center, lo, hi, ctx)
                else:
                    pitch = _bass_pitch(kind, sp.chord, center, lo, hi, ctx)
                n = buf.add(t, dur, pitch, vbase + dv, rng, legato=legato, sec=sec)
                n.alts = alts
                if idx == 0 and slide_every and (k % slide_every) == 0:
                    n.slide = ('in', slide_st, 0.3)
                if is_last and p.get('slide_out') and k == tb - 1 and tb == sec.bars:
                    n.slide = ('out', slide_st, 0.9)


def _arp_tones(ch, p, cache):
    key = (ch.symbol, tuple(p.get('degrees') or ()), tuple(p.get('ext_degrees') or ()), int(p.get('size', 4)),
           tuple(p.get('range') or ()), int(p.get('ext_min_pitch', 72)))
    if key in cache:
        return cache[key]
    lo, hi = (p.get('range') or [60, 88])[:2]
    base = {ch.tone(int(d)) for d in (p.get('degrees') or [1, 3, 5]) if ch.tone(int(d)) is not None}
    ext = {ch.tone(int(d), color=True) for d in (p.get('ext_degrees') or []) if ch.tone(int(d), color=True) is not None}
    pitches = sorted(set([x for x in range(lo, hi + 1) if x % 12 in base] +
                         [x for x in range(max(lo, int(p.get('ext_min_pitch', 72))), hi + 1) if x % 12 in ext]))
    tones = pitches[:max(1, int(p.get('size', 4)))] or [lo]
    cache[key] = tones
    return tones


def gen_arp(ctx, track, buf):
    cache = {}
    for sec, block, p, fb, tb in ctx.blocks(track):
        rng = ctx.rng(track['id'], sec.id, block.get('seed', 0))
        bb = ctx.bb
        if block['style'] == 'pings':
            lo, hi = (p.get('range') or [72, 90])[:2]
            every = max(1, int(p.get('every_bars', 1)))
            degs = [int(d) for d in (p.get('degrees') or [3, 5, 1])]
            j = 0
            for k in range(fb, tb):
                if (k - fb) % every:
                    continue
                t = sec.t0 + k * bb + float(p.get('beat', 2))
                sp = ctx.span_at(t)
                pc = sp.chord.tone(degs[j % len(degs)], color=True)
                j += 1
                if pc is None:
                    continue
                pitch = min((x for x in range(lo, hi + 1) if x % 12 == pc), key=lambda x: abs(x - (lo + hi) / 2.0), default=None)
                if pitch is not None:
                    vel = ctx.vel(sec, block, 'arp', (k - fb) / float(max(1, tb - fb)))
                    buf.add(t, float(p.get('dur', 3)), pitch, vel, rng, legato=1.0, sec=sec)
            for dy in p.get('dyads') or []:
                for k in dy.get('bars', []):
                    if fb <= k < tb:
                        for pit in dy.get('pitches', []):
                            buf.add(sec.t0 + k * bb + float(dy.get('beat', 2)), float(dy.get('dur', 3.5)),
                                    T.parse_pitch(pit), float(dy.get('vel', 40)), rng, legato=1.0, sec=sec, intent=True)
            continue
        step0 = float(p.get('step', 0.5))
        changes = sorted(p.get('step_changes') or [], key=lambda c: c.get('from_bar', 0))
        names = p.get('alt_patterns') or [p.get('pattern', 'p1')]
        plist = p.get('pattern_list')
        accent, legato = float(p.get('accent', 6)), float(p.get('legato', 1.05))
        rest_prob = float(p.get('rest_prob', 0) or 0)
        for k in range(fb, tb):
            step = step0
            for c in changes:
                if k >= int(c.get('from_bar', 0)):
                    step = float(c.get('step', step))
            pat = plist if plist else S.ARP_PATTERNS.get(names[(k - fb) % len(names)], S.ARP_PATTERNS['p1'])
            n = max(1, int(round(bb / step)))
            bar_t = sec.t0 + k * bb
            for i in range(n):
                idx = pat[i % len(pat)]
                if idx is None or (rest_prob and rng.random() < rest_prob):
                    continue
                t = bar_t + i * step
                tones = _arp_tones(ctx.span_at(t).chord, p, cache)
                frac = (k - fb + i / float(n)) / float(max(1, tb - fb))
                half = max(1, n // 2)
                vel = ctx.vel(sec, block, 'arp', frac) + (accent if i % half == 0 else (-3 if i % 2 else 0))
                buf.add(t, step, tones[int(idx) % len(tones)], vel, rng, legato=legato, sec=sec)


def generate_phrase(ctx, sec, fb, tb, p, rng, track=None):
    """Frase generativa (lista de dict bar/beat/pitch/dur) para un tramo de la seccion."""
    lo, hi = (p.get('range') or (track or {}).get('range') or [67, 88])[:2]
    scale = [x for x in range(lo, hi + 1) if x % 12 in ctx.scale]
    if not scale:
        scale = list(range(lo, hi + 1))
    dens = clamp(float(p.get('density', 0.35)), 0.02, 1.0)
    long_p = clamp(float(p.get('long_prob', 0.5)), 0.0, 1.0)
    motif = max(1, int(p.get('motif_bars', 4)))
    contour, bb = p.get('contour', 'arch'), ctx.bb
    nbars = tb - fb
    out, prev = [], scale[len(scale) // 2]
    rhythm = {}

    def target(i):
        x = (i + 0.5) / max(1, nbars)
        if contour == 'rising': return lo + (hi - lo) * (0.3 + 0.55 * x)
        if contour == 'falling': return lo + (hi - lo) * (0.85 - 0.5 * x)
        if contour == 'flat': return (lo + hi) / 2.0
        return lo + (hi - lo) * (0.35 + 0.5 * math.sin(math.pi * x))

    for i in range(nbars):
        k = fb + i
        if (i % motif) in rhythm and i >= motif and rng.random() < 0.7:
            onsets = rhythm[i % motif]
        else:
            n_notes = max(1, int(round(rng.gauss(dens * 5.0, 0.7))))
            grid = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5][:int(bb * 2)]
            w = [3.0 if g % 1 == 0 else 1.0 for g in grid]
            chosen = set()
            while len(chosen) < min(n_notes, len(grid)):
                chosen.add(rng.choices(grid, weights=w)[0])
            onsets = sorted(chosen)
            if i < motif:
                rhythm[i] = onsets
        bar_t = sec.t0 + k * bb
        for j, pos in enumerate(onsets):
            nxt = onsets[j + 1] if j + 1 < len(onsets) else bb
            dur = nxt - pos
            if rng.random() < long_p and j == len(onsets) - 1:
                dur = min(dur + bb * 0.5, bb * 1.5)
            ch = ctx.span_at(bar_t + pos).chord
            tones = {ch.tone(d) for d in (1, 3, 5, 7) if ch.tone(d) is not None}
            tgt = target(i)
            best, bw = scale[0], -1
            for c in scale:
                wgt = math.exp(-abs(c - tgt) / 5.0) * math.exp(-abs(c - prev) / 3.0)
                if pos % 2 == 0 and c % 12 in tones:
                    wgt *= 3.0
                if c == prev:
                    wgt *= 0.3
                wgt *= rng.uniform(0.6, 1.4)
                if wgt > bw:
                    best, bw = c, wgt
            prev = best
            out.append({'bar': k, 'beat': round(pos, 3), 'pitch': best, 'dur': round(max(0.25, dur - 0.1), 3)})
    return out


def _lead_notes(ctx, track, sec, block, p, fb, tb, rng):
    style = block['style']
    phrases = (ctx.project.get('lead') or {}).get('phrases', {}).get(sec.id)
    if style == 'auto':
        style = 'phrases' if phrases else 'generative'
    if style == 'phrases':
        notes = []
        loop = int(p.get('loop_bars', 0) or 0)
        for n in phrases or []:
            k = int(n.get('bar', 0))
            reps = range(k, sec.bars, loop) if loop and k < loop else [k]
            for kk in reps:
                if fb <= kk < tb:
                    notes.append(dict(n, bar=kk))
        return notes
    if style == 'generative':
        return generate_phrase(ctx, sec, fb, tb, p, rng, track)
    if style == 'hold' and phrases:
        return list(phrases)
    if style == 'hold':
        lo, hi = (p.get('range') or track.get('range') or [62, 88])[:2]
        out, degs = [], [3, 5, 1, 5]
        for i, sp in enumerate([s for s in sec.spans if s.t1 > sec.t0 + fb * ctx.bb and s.t0 < sec.t0 + tb * ctx.bb]):
            pc = sp.chord.tone(degs[i % len(degs)], color=True)
            if pc is None:
                continue
            pitch = min((x for x in range(lo, hi + 1) if x % 12 == pc), key=lambda x: abs(x - (lo + hi) / 2.0), default=None)
            if pitch is None:
                continue
            k = int((sp.t0 - sec.t0) // ctx.bb)
            out.append({'bar': k, 'beat': round(sp.t0 - sec.t0 - k * ctx.bb, 3), 'pitch': pitch,
                        'dur': round((sp.t1 - sp.t0) * 0.97, 3)})
        return out
    return []


def gen_lead(ctx, track, buf):
    for sec, block, p, fb, tb in ctx.blocks(track):
        rng = ctx.rng(track['id'], sec.id, block.get('seed', 0))
        notes = _lead_notes(ctx, track, sec, block, p, fb, tb, rng)
        accent, legato, tr = float(p.get('accent', 4)), float(p.get('legato', 0.93)), int(p.get('transpose', 0) or 0)
        seen_bars = set()
        for n in sorted(notes, key=lambda n: (n.get('bar', 0), n.get('beat', 0))):
            try:
                pitch = T.parse_pitch(n['pitch']) + tr
            except (ValueError, KeyError):
                ctx.warn('Nota de lead invalida en "%s": %r' % (sec.name, n))
                continue
            k, beat = int(n.get('bar', 0)), float(n.get('beat', 0))
            first = k not in seen_bars
            seen_bars.add(k)
            frac = (k - fb + beat / ctx.bb) / float(max(1, tb - fb))
            vel = n['vel'] if n.get('vel') is not None else ctx.vel(sec, block, 'lead', frac) + (accent if first else 0) + (
                2 if beat % 1 == 0 else -2)
            nt = buf.add(sec.t0 + k * ctx.bb + beat, float(n.get('dur', 1)), pitch, vel, rng, legato=legato, sec=sec)
            nt.bend = p.get('bends')


def _vel_spec(L, i, n, k, nb, sec, bb, pos, rng, scale):
    if 'vel_rand' in L:
        return rng.randint(int(L['vel_rand'][0]), int(L['vel_rand'][1])) * scale
    v = L.get('vel', 80)
    if isinstance(v, dict):
        over = v.get('over', 'steps')
        if over == 'steps':
            fr = i / float(max(1, n - 1))
        elif over == 'when':
            w = L.get('when') or {}
            wf, wt = w.get('from', min(w['bars']) if w.get('bars') else 0), w.get('to', (max(w['bars']) + 1) if w.get('bars') else nb)
            fr = ((k - wf) + pos / bb) / float(max(1, wt - wf))
        else:
            fr = (k + pos / bb) / float(max(1, nb))
        return lerp(v['v0'], v['v1'], fr) * scale
    if isinstance(v, (list, tuple)):
        return v[i % len(v)] * scale
    return v * scale


def gen_drums(ctx, track, buf):
    bb = ctx.bb
    for sec, block, p, fb, tb in ctx.blocks(track):
        rng = ctx.rng(track['id'], sec.id, block.get('seed', 0))
        scale = float(p.get('vel_scale', 1.0) or 1.0)
        fscale = scale
        if block.get('velocity') is not None:
            fscale = scale

        def preset_of(name):
            return S.DRUM_PRESETS.get(name) or S.DRUM_PRESETS['none']

        main = preset_of(p.get('preset'))
        layers = p.get('layers') or main['layers']
        fills = p.get('fills') if p.get('fills') is not None else main.get('fills', [])
        light_bars = int(p.get('light_bars', 0) or 0)
        light = preset_of(p.get('light_preset') or 'synth_verse_light')
        for k in range(fb, tb):
            use_light = k - fb < light_bars
            lay = light['layers'] if use_light else layers
            fl = [] if use_light else fills
            evs, open_pos = [], set()
            ordered = sorted(lay, key=lambda L: 1 if L.get('skip_if_open') else 0)
            for L in ordered:
                if not when_ok(L.get('when'), k, sec.bars, sec):
                    continue
                if 'at' in L:
                    poss = [float(x) for x in L['at'] if float(x) < bb]
                elif 'grid' in L:
                    g = float(L['grid'])
                    poss = [i * g for i in range(int(bb / g + 1e-6))]
                elif 'pick' in L:
                    poss = [float(rng.choice(L['pick']))]
                else:
                    continue
                try:
                    note = T.drum_note(L['inst'], ctx.drum_map)
                except ValueError as e:
                    ctx.warn(str(e))
                    continue
                hz = track.get('drum_humanize') or {}
                hkey = HUM_KEY.get(T.slug(L['inst']))
                l_off, l_jit, l_drag = float(L.get('offset', 0)), L.get('jitter'), L.get('drag')
                if hkey == 'hat' and isinstance(hz.get('hat'), dict):
                    l_jit, l_drag = hz['hat'].get('jitter', l_jit), hz['hat'].get('drag', l_drag)
                elif hkey and isinstance(hz.get(hkey), (int, float)):
                    l_off = float(hz[hkey])
                l_omit, l_velrand = L.get('omit'), L.get('vel_rand')
                if hkey == 'hat' and isinstance(hz.get('hat'), dict) and L.get('inst') == 'closed_hat' and 'grid' in L:
                    hh = hz['hat']
                    if hh.get('grid'):
                        poss = [i * float(hh['grid']) for i in range(int(bb / float(hh['grid']) + 1e-6))]
                    if hh.get('omit') is not None:
                        om = hh['omit']
                        l_omit = rng.uniform(om[0], om[1]) if isinstance(om, (list, tuple)) else float(om)
                    if hh.get('vel_rand'):
                        l_velrand = hh['vel_rand']
                for i, pos in enumerate(poss):
                    if L.get('skip_if_open') and pos in open_pos:
                        continue
                    if L.get('prob', 1.0) < 1.0 and rng.random() >= L['prob']:
                        continue
                    if l_omit and rng.random() < l_omit:
                        continue
                    vel = _vel_spec(dict(L, vel_rand=l_velrand) if l_velrand else L, i, len(poss), k, sec.bars, sec, bb, pos, rng, fscale)
                    extra = l_off + (float(l_drag[1]) if l_drag and rng.random() < l_drag[0] else 0.0)
                    evs.append(dict(inst=L['inst'], note=note, pos=pos, vel=vel, dur=float(L.get('dur', 0.15)),
                                    extra=extra, jit=l_jit))
                    if note == T.DRUM_NOTES['open_hat']:
                        open_pos.add(pos)
            for f in fl:
                if not when_ok(f.get('when'), k, sec.bars, sec):
                    continue
                for m in f.get('mute') or []:
                    evs = [e for e in evs if not (T.slug(e['inst']) == T.slug(m['inst']) and e['pos'] >= m.get('from', 0))]
                for h in f.get('hits') or []:
                    evs.append(dict(inst=h['inst'], note=T.drum_note(h['inst'], ctx.drum_map), pos=float(h['at']),
                                    vel=h.get('vel', 90) * scale, dur=0.15, extra=0.0, jit=None))
                for r in f.get('rolls') or []:
                    for i in range(int(r['steps'])):
                        evs.append(dict(inst=r['inst'], note=T.drum_note(r['inst'], ctx.drum_map),
                                        pos=float(r['start']) + i * float(r['step']),
                                        vel=lerp(r['v0'], r['v1'], i / float(max(1, r['steps'] - 1))) * scale,
                                        dur=0.15, extra=0.0, jit=None))
            bar_t = sec.t0 + k * bb
            for e in evs:
                if e['pos'] >= bb:
                    continue
                n = buf.add(bar_t + e['pos'], e['dur'], e['note'], e['vel'], rng, legato=1.0, jit=e['jit'],
                            extra=e['extra'], sec=sec)
                n.inst = e['inst']


GENERATORS = {'pad': gen_chordal, 'strings': gen_chordal, 'keys': gen_chordal, 'bass': gen_bass, 'arp': gen_arp,
              'mallet': gen_mallet, 'lead': gen_lead, 'drums': gen_drums}


# --------------------------------------------------------------------------
# Post-proceso: reparacion de choques, bends, automatizacion
# --------------------------------------------------------------------------
def _clash(a_p, b_p):
    return abs(a_p - b_p) in (1, 13)


def repair_clashes(ctx, bufs):
    pitched = [b for b in bufs if b.role in PITCHED]
    allnotes = [(n, b) for b in pitched for n in b.notes if not n.removed]
    buckets = {}

    def index():
        buckets.clear()
        for n, b in allnotes:
            if n.removed:
                continue
            for i in range(int(n.t), int(n.t + n.d) + 1):
                buckets.setdefault(i, []).append((n, b))

    def neighbors(n):
        seen, out = set(), []
        for i in range(int(n.t), int(n.t + n.d) + 1):
            for m, bm in buckets.get(i, []):
                if m is not n and not m.removed and id(m) not in seen:
                    seen.add(id(m))
                    if min(n.t + n.d, m.t + m.d) - max(n.t, m.t) >= 0.2:
                        out.append((m, bm))
        return out

    count = 0
    for _ in range(3):
        index()
        changed = False
        for n, b in allnotes:
            if n.removed or n.intent:
                continue
            for m, bm in neighbors(n):
                if m.intent or m.removed or not _clash(n.p, m.p):
                    continue
                pa, pb = S.ROLE_PRIORITY.get(b.role, 0), S.ROLE_PRIORITY.get(bm.role, 0)
                if (pa, -n.t) > (pb, -m.t):
                    continue          # n es la nota protegida: se arreglara desde m
                victim, vb, other = n, b, m
                if vb.role == 'lead' and bm.role == 'lead':
                    continue
                opts = list(victim.alts or []) + [victim.p + 12, victim.p - 12, victim.p + 24]
                lo, hi = (vb.track.get('range') or [0, 127])[:2]
                fixed = False
                for cand in opts:
                    if cand < 12 or cand > 120:
                        continue
                    if cand not in (victim.alts or []) and not (lo - 1 <= cand <= hi + 1):
                        continue          # no sacar la nota del rango declarado de la pista
                    old = victim.p
                    victim.p = cand
                    if not any(_clash(cand, o.p) and not o.intent for o, _ in neighbors(victim)):
                        ctx.repairs.append(dict(t=round(victim.t, 2), track=vb.track['id'], action='mover',
                                                from_pitch=old, to_pitch=cand))
                        fixed = changed = True
                        count += 1
                        break
                    victim.p = old
                if not fixed:
                    if vb.role in ('arp', 'strings', 'pad', 'keys', 'mallet'):
                        victim.removed = True
                        ctx.repairs.append(dict(t=round(victim.t, 2), track=vb.track['id'], action='quitar',
                                                from_pitch=victim.p))
                        changed = True
                    else:
                        ctx.warn('Choque de semitono no resuelto en beat %.1f (%s)' % (victim.t, vb.track['id']))
                break
        if not changed:
            break
    for b in bufs:
        b.notes = [n for n in b.notes if not n.removed]


def compute_bends(ctx, buf, tape):
    """-> lista de (beat, valor) en unidades de pitch-bend (+ rango actual) y lista (beat, cents)."""
    tr, role = buf.track, buf.role
    rng_st = ctx.bend_range
    unit = 8192.0 / rng_st
    base = int(tr.get('detune', 0) or 0)
    evs = [(0.0, base)]
    ns = buf.notes
    prev_end = -99.0
    cut = (tape['t0'] - 0.5) if tape else 1e18
    for i, n in enumerate(ns):
        end = n.t + n.d
        nxt = ns[i + 1].t if i + 1 < len(ns) else 1e9
        if n.t >= cut:
            break
        if role == 'lead' and n.bend:
            sc, fa = (n.bend.get('scoop') or {}), (n.bend.get('fall') or {})
            did = False
            _r = random.Random('%s|bend|%.3f' % (ctx.seed, n.t))
            if sc.get('enabled', True) and (n.t - prev_end) >= float(sc.get('min_gap', 0.75)) and _r.random() < float(sc.get('prob', 1.0)):
                amt, bt = float(sc.get('semitones', 0.5)) * unit, float(sc.get('beats', 0.25))
                evs.append((max(0.0, n.t - 0.004), base - amt))
                for k in range(1, 7):
                    evs.append((n.t + bt * k / 6.0, base - amt * (1 - k / 6.0)))
                did = True
            if fa.get('enabled', True) and n.d >= float(fa.get('min_dur', 3)) and _r.random() < float(fa.get('prob', 1.0)):
                amt, bt = float(fa.get('semitones', 0.5)) * unit, float(fa.get('beats', 0.46))
                fs = end - bt
                for k in range(1, 7):
                    evs.append((fs + bt * k / 6.0 - 0.01, base - amt * k / 6.0))
                did = True
            if did:
                evs.append((min(end + 0.01, nxt - 0.006), base))
        if role == 'bass' and n.slide:
            kind, st, bt = n.slide
            amt = clamp(st * unit, 0, 8191)
            if kind == 'in':
                evs.append((max(0.0, n.t - 0.004), -amt))
                for k in range(1, 7):
                    evs.append((n.t + bt * k / 6.0, -amt * (1 - k / 6.0)))
            else:
                for k in range(1, 7):
                    evs.append((n.t + n.d * bt * k / 6.0, -amt * k / 6.0))
                evs.append((min(end + 0.01, nxt - 0.006), 0))
        prev_end = end
    cents_range = [(0.0, rng_st)]
    if tape:
        evs = [e for e in evs if e[0] < cut]
        evs.append((cut, int(base * rng_st / tape['range'])))
        total = tape['t1'] - tape['t0']
        steps = 32
        for i in range(1, steps + 1):
            x = i / float(steps)
            evs.append((tape['t0'] + x * total - 0.25, -8191 * (abs(tape['semitones']) / tape['range']) * (x ** tape['exponent'])))
        cents_range.append((cut, tape['range']))
    evs.sort(key=lambda e: e[0])
    out = [(round(b, 4), int(clamp(round(v), -8192, 8191))) for b, v in evs]

    def cents(beat, val):
        r = rng_st
        for b0, r0 in cents_range:
            if beat >= b0 - 1e-9:
                r = r0
        return round(val / 8192.0 * r * 100.0, 1)
    return out, [(b, cents(b, v)) for b, v in out]


def resolve_pos(ctx, spec):
    if isinstance(spec, (int, float)):
        return float(spec)
    spec = spec or {}
    if 'beat' in spec:
        return float(spec['beat'])
    sid = spec.get('section')
    if sid in (None, 'start'):
        return float(spec.get('bar', 0)) * ctx.bb
    if sid == 'end':
        return ctx.total_beats
    sec = None
    if sid == 'last':
        sec = ctx.secs[-1]
    elif isinstance(sid, int):
        sec = ctx.secs[clamp(sid, 0, len(ctx.secs) - 1)]
    else:
        sec = next((s for s in ctx.secs if s.id == sid), None)
    if sec is None:
        ctx.warn('Seccion desconocida en automatizacion: %r' % (sid,))
        return 0.0
    return sec.t0 + float(spec.get('bar', 0)) * ctx.bb


def target_tracks(ctx, bufs, sel):
    sel = sel or 'all'
    if sel == 'all':
        return bufs
    if sel == 'pitched':
        return [b for b in bufs if b.role in PITCHED]
    return [b for b in bufs if b.track['id'] == sel or b.role == sel]


def build_ccs(ctx, bufs, tape):
    """CCs por pista: mezcla, rpn, automatizacion, fade. -> {track_id: [(beat, cc, val)]}"""
    ccs = {}
    auto = ctx.project.get('automation') or []
    for b in bufs:
        tr = b.track
        lst = ccs.setdefault(tr['id'], [])
        init11 = 127
        for a in auto:
            if a.get('cc', 11) == 11 and resolve_pos(ctx, a.get('from')) <= 0.0 and b in target_tracks(ctx, bufs, a.get('track')):
                init11 = a.get('v0', 127)
        lst += [(0.0, 7, tr.get('volume', 100)), (0.0, 10, tr.get('pan', 64)), (0.0, 91, tr.get('reverb', 40)),
                (0.0, 93, tr.get('chorus', 0)), (0.0, 11, init11)]
        if b.role != 'drums':
            rs = int(round(ctx.bend_range))
            lst += [(0.0, 101, 0), (0.0, 100, 0), (0.0, 6, rs), (0.0, 38, 0), (0.0, 101, 127), (0.0, 100, 127)]
        if b.role == 'lead':
            lst.append((0.0, 1, 14))
        for key, cc_no in (('attack', 73), ('release', 72), ('brightness', 74)):
            if tr.get(key) is not None:
                lst.append((0.0, cc_no, tr[key]))
        for k_, v_ in (tr.get('cc_extra') or {}).items():
            lst.append((0.0, int(k_), v_))
        if tape and b.role != 'drums':
            tr_rng = int(tape['range'])
            lst += [(tape['t0'] - 0.5, 101, 0), (tape['t0'] - 0.5, 100, 0), (tape['t0'] - 0.5, 6, tr_rng),
                    (tape['t0'] - 0.5, 38, 0), (tape['t0'] - 0.5, 101, 127), (tape['t0'] - 0.5, 100, 127)]
    for a in auto:
        t0, t1 = resolve_pos(ctx, a.get('from')), resolve_pos(ctx, a.get('to'))
        if t1 <= t0:
            continue
        step, cur = float(a.get('step', 1.0)), float(a.get('curve', 1.0))
        for b in target_tracks(ctx, bufs, a.get('track')):
            n = max(1, int((t1 - t0) / step))
            for i in range(n + 1):
                x = i / float(n)
                ccs[b.track['id']].append((t0 + x * (t1 - t0), int(a.get('cc', 11)),
                                           lerp(a.get('v0', 0), a.get('v1', 127), x ** cur)))
    fo = (ctx.project.get('ending') or {}).get('fade_out') or {}
    if fo.get('enabled'):
        t0 = resolve_pos(ctx, fo.get('start') or {'section': 'last', 'bar': 0})
        t1 = ctx.total_beats
        for b in target_tracks(ctx, bufs, fo.get('tracks', 'all')):
            n = int((t1 - t0) * 2)
            for i in range(n + 1):
                x = i / float(max(1, n))
                ccs[b.track['id']].append((t0 + x * (t1 - t0), int(fo.get('cc', 11)), 127 * (1 - x) ** float(fo.get('exponent', 1.5))))
    return ccs


# --------------------------------------------------------------------------
# Orquestacion
# --------------------------------------------------------------------------
class Result(object):
    pass


def _active_tracks(project):
    tracks = [t for t in project.get('tracks', []) if t.get('enabled', True)]
    solo = [t for t in tracks if t.get('solo')]
    if solo:
        return solo
    return [t for t in tracks if not t.get('mute')]


def generate(project):
    ctx = Ctx(project)
    res = Result()
    res.ctx = ctx
    bufs = []
    raw = project.get('raw')
    active = _active_tracks(project)
    if raw:
        bufs = _raw_bufs(ctx, active, raw)
    else:
        ctx.generated = {}
        for tr in sorted(active, key=lambda t: 1 if t['role'] == 'mallet' else 0):   # el vibrafono lee al lead
            buf = Buf(tr, ctx)
            gen = GENERATORS.get(tr['role'])
            if gen is None:
                ctx.warn('Rol desconocido: %s' % tr['role'])
                continue
            gen(ctx, tr, buf)
            ctx.generated[tr['id']] = buf
        bufs = [ctx.generated[t['id']] for t in active if t['id'] in ctx.generated]
        if ctx.g.get('repair_clashes', True):
            repair_clashes(ctx, bufs)
    for b in bufs:
        b.finalize()
    ending = project.get('ending') or {}
    tape = None
    ts = ending.get('tape_stop') or {}
    if ts.get('enabled') and not raw:
        nb = float(ts.get('bars', 2))
        tape = dict(t0=ctx.total_beats - nb * ctx.bb, t1=ctx.total_beats, semitones=float(ts.get('semitones', -8.4)),
                    range=float(ts.get('range', 12)), exponent=float(ts.get('exponent', 1.7)))
        for b in bufs:
            if b.role != 'drums':
                # el tape-stop no debe cortar notas: nada que hacer, solo se ignoran scoops posteriores
                pass
    res.tape = tape
    res.bufs = bufs
    if raw:
        res.bends = {b.track['id']: (b.raw_bends, [(x, round(v / 8192.0 * ctx.bend_range * 100, 1)) for x, v in b.raw_bends])
                     for b in bufs}
        res.ccs = {b.track['id']: b.raw_ccs for b in bufs}
    else:
        res.bends = {b.track['id']: compute_bends(ctx, b, tape) for b in bufs if b.role != 'drums'}
        res.ccs = build_ccs(ctx, bufs, tape)
    res.midi = build_midi_bytes(ctx, bufs, res)
    return res


class _RawBuf(Buf):
    pass


def _raw_bufs(ctx, active, raw):
    out = []
    by = {t.get('id'): t for t in raw.get('tracks', [])}
    for tr in active:
        rt = by.get(tr['id'])
        if rt is None:
            continue
        b = _RawBuf(tr, ctx)
        for n in rt.get('notes', []):
            nt = Note(float(n['start']), float(n['duration']), int(n['pitch']), int(n['velocity']), float(n['start']))
            b.notes.append(nt)
        b.raw_bends = [(float(x['beat']), int(x['value'])) for x in rt.get('pitch_bend', [])]
        b.raw_ccs = [(float(x['beat']), int(x['cc']), int(x['value'])) for x in rt.get('controllers', [])]
        out.append(b)
    return out


def build_midi_bytes(ctx, bufs, res):
    tpb = ctx.tpb
    tick = lambda beat: int(round(beat * tpb))
    cond = MidiTrack('Conductor')
    cond.tempo(0, ctx.bpm)
    cond.timesig(0, ctx.ts[0], ctx.ts[1])
    sf, mi = T.key_signature(*ctx.key)
    cond.keysig(0, sf, mi)
    for s in ctx.secs:
        cond.marker(tick(s.t0), s.name)
    tracks = [cond]
    used = {}
    for b in bufs:
        tr = b.track
        ch = 9 if b.role == 'drums' else clamp(int(tr.get('channel', 1)) - 1, 0, 15)
        if ch == 9 and b.role != 'drums':
            ch = 0
            ctx.warn('La pista "%s" usaba el canal 10 (percusion); se movio al canal 1.' % tr.get('name'))
        if ch in used and used[ch] != tr['id']:
            ctx.warn('Canal %d compartido por "%s" y "%s": los CC/bends pueden interferir.' % (ch + 1, used[ch], tr['id']))
        used[ch] = tr['id']
        mt = MidiTrack(tr.get('name') or tr['id'])
        if b.role != 'drums':
            prog = tr.get('program')
            mt.program(0, ch, 0 if prog is None else int(prog))
        for beat, num, val in sorted(res.ccs.get(tr['id'], []), key=lambda e: e[0]):
            mt.cc(tick(beat), ch, num, val)
        if b.role != 'drums' and tr['id'] in res.bends:
            for beat, val in res.bends[tr['id']][0]:
                mt.bend(tick(beat), ch, val)
        for n in b.notes:
            mt.note(tick(n.t), max(1, tick(n.d)), ch, n.p, n.v)
        tracks.append(mt)
    return build_midi(tracks, tpb)


def to_events(res):
    ctx = res.ctx
    out = []
    for b in res.bufs:
        tr = b.track
        bends = res.bends.get(tr['id'], ([], []))[1] if tr['id'] in res.bends else []
        expr = sorted(((round(bt, 3), int(v)) for bt, c, v in res.ccs.get(tr['id'], []) if c == 11), key=lambda e: e[0])
        out.append(dict(id=tr['id'], name=tr.get('name'), role=b.role, channel=tr.get('channel'),
                        program=tr.get('program'), volume=tr.get('volume', 100), pan=tr.get('pan', 64), gain=tr.get('gain', 1.0),
                        notes=[[round(n.t, 4), round(n.d, 4), n.p, n.v] for n in b.notes], bends=bends, expr=expr))
    return dict(bpm=ctx.bpm, ticks_per_beat=ctx.tpb, bar_beats=ctx.bb, total_beats=ctx.total_beats, tracks=out,
                sections=[dict(id=s.id, name=s.name, kind=s.kind, t0=s.t0, t1=s.t1, bars=s.bars) for s in ctx.secs])


def midi_b64(res):
    return base64.b64encode(res.midi).decode('ascii')


def export_events(res):
    """Formato de eventos reimportable (notas + bends crudos + controladores)."""
    ctx = res.ctx
    tracks = []
    for b in res.bufs:
        tr = b.track
        tracks.append(dict(
            id=tr['id'], name=tr.get('name'), role=b.role, channel=10 if b.role == 'drums' else tr.get('channel'),
            program=tr.get('program'),
            notes=[dict(start=round(n.t, 4), duration=round(n.d, 4), pitch=n.p, velocity=n.v) for n in b.notes],
            pitch_bend=[dict(beat=bt, value=v) for bt, v in res.bends.get(tr['id'], ([], []))[0]],
            controllers=[dict(beat=round(bt, 3), cc=c, value=int(v)) for bt, c, v in
                         sorted(res.ccs.get(tr['id'], []), key=lambda e: e[0])]))
    return dict(title=ctx.project.get('meta', {}).get('name', ''), bpm=ctx.bpm, ticks_per_beat=ctx.tpb,
                time_signature=list(ctx.ts), unit='beats (negra = 1)', tracks=tracks)
