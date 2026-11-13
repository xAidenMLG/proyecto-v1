"""Voicings de acordes con voice leading global (Viterbi)."""

PROFILES = {
    # nombre: voces, grados permitidos, requeridos, prohibidos, separacion min/max entre voces adyacentes
    'rootfifth': dict(voices=2, allow=[1, 5], require=[1, 5], forbid=[], min_gap=5, max_gap=9),
    'triad': dict(voices=3, allow=[1, 3, 5], require=[1, 3, 5], forbid=[], min_gap=3, max_gap=9),
    'full': dict(voices=3, allow=[1, 3, 5, 7], require=[3], forbid=[], min_gap=5, max_gap=15),
    'bare': dict(voices=3, allow=[1, 5, 7, 9], require=[], forbid=[3], require_any=[7, 9], min_gap=5, max_gap=15),
    'shell': dict(voices=3, allow=[1, 3, 5, 7], require=[3], forbid=[], avoid=[1], min_gap=2, max_gap=9),
    'open4': dict(voices=4, allow=[1, 3, 5, 7], require=[3], forbid=[], min_gap=3, max_gap=12),
    'spread': dict(voices=3, allow=[1, 3, 5, 7, 9], require=[3], forbid=[], min_gap=4, max_gap=12),
    # pad ancho: raiz + octava / raiz + quinta + octava
    'rootoctave': dict(voices=2, allow=[1], require=[1], forbid=[], min_gap=12, max_gap=12),
    'wide': dict(voices=3, allow=[1, 5], require=[1], forbid=[], min_gap=5, max_gap=12),
    # teclados (Rhodes): compactos y calidos; 'rootless' deja la raiz al bajo y exige 3a y 7a si existen
    'compact': dict(voices=3, allow=[1, 3, 5, 7, 9], require=[3], forbid=[], min_gap=2, max_gap=7),
    'rootless': dict(voices=3, allow=[3, 5, 7, 9], require=[3], forbid=[1], require_any=[7, 9], min_gap=2, max_gap=7),
}


def resolve_profile(spec):
    """spec: nombre | dict (puede traer 'profile' como base)."""
    if isinstance(spec, str):
        spec = {'profile': spec}
    spec = dict(spec or {})
    base = dict(PROFILES.get(spec.pop('profile', 'full'), PROFILES['full']))
    base.update({k: v for k, v in spec.items() if v is not None})
    return base


def _pcs_for(chord, prof):
    pcs = {}
    for d in prof['allow']:
        if d in prof.get('forbid', []):
            continue
        pc = chord.tone(d, color=True)
        if pc is not None:
            pcs.setdefault(pc, d)
    return pcs


def candidates(chord, prof, lo, hi, limit=160, center=None):
    pcs = _pcs_for(chord, prof)
    if not pcs:
        return []
    n, gmin, gmax = prof['voices'], prof['min_gap'], prof['max_gap']
    pitches = [p for p in range(lo, hi + 1) if p % 12 in pcs]
    req = [chord.tone(d) for d in prof.get('require', []) if chord.tone(d) is not None]
    req_any = [chord.tone(d, color=True) for d in prof.get('require_any', []) if chord.tone(d, color=True) is not None]
    avoid = [chord.tone(d) for d in prof.get('avoid', []) if chord.tone(d) is not None]
    distinct = n <= len(pcs)
    out = []

    def rec(cur):
        if len(cur) == n:
            have = {p % 12 for p in cur}
            if any(r not in have for r in req):
                return
            if req_any and not any(r in have for r in req_any):
                return
            out.append(tuple(cur))
            return
        for p in pitches:
            if cur:
                g = p - cur[-1]
                if g < gmin or g > gmax:
                    continue
                if distinct and p % 12 in {q % 12 for q in cur}:
                    continue
            elif len(cur) == 0:
                pass
            rec(cur + [p])

    rec([])
    if not out:
        return []
    c = center if center is not None else (lo + hi) / 2.0

    def local(v):
        pen = 0.18 * abs(sum(v) / float(len(v)) - c)
        pen += 3.0 * sum(1 for p in v if p % 12 in avoid)
        return pen

    out.sort(key=local)
    return out[:limit]


def _fallback(chord, prof, lo, hi):
    """Pila de terceras dentro del rango si no hay candidatos validos."""
    notes = []
    for d in (1, 3, 5, 7):
        pc = chord.tone(d)
        if pc is not None:
            p = lo + ((pc - lo) % 12)
            notes.append(p)
    notes = sorted(set(notes))[:max(1, prof['voices'])]
    return tuple(notes)


def voice_sequence(events, max_move=5):
    """events: lista de (chord, perfil_dict, lo, hi). Devuelve una tupla de pitches por evento
    (minimo movimiento global, Viterbi)."""
    cands, centers = [], []
    for chord, prof, lo, hi in events:
        c = (lo + hi) / 2.0
        centers.append(c)
        cs = []
        for relax in range(4):
            p2, l2, h2 = dict(prof), lo, hi
            if relax == 1:
                p2['min_gap'], p2['max_gap'] = 1, 24
            elif relax == 2:
                p2['min_gap'], p2['max_gap'], p2['require'], p2['require_any'] = 1, 24, [], []
                l2, h2 = lo - 5, hi + 7
            elif relax == 3:
                l2, h2 = lo - 12, hi + 12
            cs = candidates(chord, p2, l2, h2, center=c)
            if cs:
                break
        cands.append(cs or [_fallback(chord, prof, lo, hi)])

    def mean(v):
        return sum(v) / float(len(v))

    def trans(a, b):
        if len(a) == len(b):
            mv = [abs(x - y) for x, y in zip(a, b)]
        else:
            k = min(len(a), len(b))
            mv = [abs(x - y) for x, y in zip(a[:k], b[:k])] + [4] * abs(len(a) - len(b))
        return sum(mv) + 4.0 * sum(1 for m in mv if m > max_move)

    n = len(events)
    if n == 0:
        return []
    cost = [[0.18 * abs(mean(v) - centers[0]) for v in cands[0]]]
    back = [[-1] * len(cands[0])]
    for i in range(1, n):
        row, brow = [], []
        for v in cands[i]:
            best, bk = 1e18, 0
            for k, u in enumerate(cands[i - 1]):
                t = cost[i - 1][k] + trans(u, v)
                if t < best:
                    best, bk = t, k
            row.append(best + 0.18 * abs(mean(v) - centers[i]))
            brow.append(bk)
        cost.append(row)
        back.append(brow)
    j = min(range(len(cost[-1])), key=lambda k: cost[-1][k])
    path = [j]
    for i in range(n - 1, 0, -1):
        j = back[i][j]
        path.append(j)
    path.reverse()
    return [cands[i][path[i]] for i in range(n)]
