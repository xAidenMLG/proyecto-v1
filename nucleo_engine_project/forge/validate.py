"""Validacion del resultado: choques, polifonia, voice leading, velocidades, rangos, cobertura."""
import statistics as st

from . import engine as E
from . import theory as T
from .midiwriter import read_midi

THIRD = lambda ch: ch.third_pc


def _chk(cid, label, status, detail, requested=False):
    return {'id': cid, 'label': label, 'status': status, 'detail': detail, 'requested': requested}


def compliance(res):
    """Comprobaciones pedidas por specs tipo Shadow Corner: metadatos MIDI, pistas/programas, monofonia, dispersion
    del vibrafono, bajo vs bombo, limites de seccion, anti-four-on-the-floor, repeticion del motivo del coro."""
    ctx, proj = res.ctx, res.ctx.project
    want = proj.get('guardrails') or {}
    decl = (proj.get('meta') or {}).get('declared') or {}
    out = []
    bufs = {b.track['id']: b for b in res.bufs}
    by_role = {}
    for b in res.bufs:
        by_role.setdefault(b.role, []).append(b)
    midi = read_midi(res.midi)
    cond = midi['tracks'][0]
    # --- tempo / compas / compases
    bpm_mid = 60000000.0 / cond['tempo'][0][1] if cond['tempo'] else None
    ok = bpm_mid is not None and abs(bpm_mid - ctx.bpm) < 0.01 and cond['timesig'] == ctx.ts
    msg = 'MIDI escribe %.2f BPM y compas %s/%s' % (bpm_mid or 0, ctx.ts[0], ctx.ts[1])
    if decl.get('bpm') and abs(decl['bpm'] - ctx.bpm) > 0.01:
        ok = False
    tb = decl.get('total_bars')
    if tb:
        ok = ok and int(tb) == ctx.total_bars
        msg += '; %d compases (declarados %d)' % (ctx.total_bars, tb)
    dd = decl.get('duration_seconds')
    if dd:
        dur = ctx.total_beats * 60.0 / ctx.bpm
        okd = abs(dur - dd) <= 1.0
        ok = ok and okd
        msg += '; duracion %.1f s (declarada %.1f s)' % (dur, dd)
    out.append(_chk('tempo_ts_bars', 'BPM, compas y numero de compases', 'pass' if ok else 'fail', msg, True))
    # --- pistas y programas GM
    exp_tracks = decl.get('tracks') or len(proj['tracks'])
    progs = {}
    for t in midi['tracks'][1:]:
        for tick, ch, p in t['programs']:
            progs[(t['name'], ch)] = p
    bad = []
    for tr in proj['tracks']:
        if tr['role'] == 'drums' or not tr.get('enabled', True):
            continue
        dp = (decl.get('programs') or {}).get(tr['id'])
        got = next((p for (nm, ch), p in progs.items() if nm == (tr.get('name') or tr['id'])), None)
        if got is None or (dp is not None and got != dp):
            bad.append('%s: MIDI=%s, declarado=%s' % (tr['id'], got, dp))
    out.append(_chk('tracks_programs', 'Pistas y programas GM', 'pass' if (len(midi['tracks']) - 1 == exp_tracks and not bad) else 'fail',
                    '%d pistas MIDI (esperadas %d)%s' % (len(midi['tracks']) - 1, exp_tracks, ('; ' + '; '.join(bad)) if bad else ''), True))
    # --- canales dedicados
    chans = {}
    for b in res.bufs:
        if b.role != 'drums':
            chans.setdefault(b.track.get('channel'), []).append(b.track['id'])
    shared = {c: l for c, l in chans.items() if len(l) > 1}
    out.append(_chk('dedicated_channels', 'Canal dedicado por pista melodica (bends seguros)', 'pass' if not shared else 'fail',
                    'sin canales compartidos' if not shared else 'compartidos: %s' % shared, True))
    # --- lead: monofonia y rango
    lead = by_role.get('lead', [None])[0]
    if lead:
        ns = sorted(lead.notes, key=lambda n: n.t)
        overl = sum(1 for a, b in zip(ns, ns[1:]) if a.t + a.d > b.t + 0.005)
        lo, hi = (lead.track.get('range') or [0, 127])[:2]
        outr = [n.p for n in ns if not (lo <= n.p <= hi)]
        out.append(_chk('lead_mono_range', 'Lead monofonico y dentro de rango [%d,%d]' % (lo, hi), 'pass' if not overl and not outr else 'fail',
                        '%d solapes, %d notas fuera de rango%s' % (overl, len(outr), (' (' + ', '.join(T.midi_name(p) for p in sorted(set(outr))[:6]) + ')') if outr else ''),
                        bool(want.get('lead_mono_range'))))
        iv = [(n.t, n.t + n.d) for n in ns]
        cover = sum(b - a for a, b in iv) / max(1e-9, ctx.total_beats)
        out.append(_chk('lead_coverage', 'El lead deja silencios (no rellena todos los huecos)', 'pass' if cover <= 0.70 else 'warn',
                        'suena el %.0f%% del tiempo' % (100 * cover), bool(want.get('lead_coverage'))))
    # --- vibrafono (mallet)
    mal = by_role.get('mallet', [None])[0]
    if mal:
        nbars = ctx.total_bars
        bars_with = len({int(n.nom // ctx.bb) for n in mal.notes})
        dens = len(mal.notes) / float(nbars)
        out.append(_chk('mallet_sparse', 'Vibrafono escaso (no arpegio continuo)', 'pass' if dens <= 0.6 and bars_with <= 0.5 * nbars else 'fail',
                        '%d notas (%.2f por compas), presente en %d de %d compases' % (len(mal.notes), dens, bars_with, nbars), bool(want.get('mallet_sparse'))))
        if lead:
            ov = 0
            for n in mal.notes:
                for m in lead.notes:
                    if m.t >= n.t + n.d:
                        break
                    if min(m.t + m.d, n.t + n.d) - max(m.t, n.t) > 0.25 and abs(m.p - n.p) < 5:
                        ov += 1
                        break
            dbl = 0
            for n in mal.notes:
                for m in lead.notes:
                    if abs(m.t - n.t) < 0.1 and m.p % 12 == n.p % 12:
                        dbl += 1
            out.append(_chk('lead_mallet_overlap', 'Vibrafono no pisa ni dobla al lead en el mismo registro', 'pass' if ov == 0 and dbl == 0 else 'fail',
                            '%d solapes de registro, %d dobles simultaneos' % (ov, dbl), bool(want.get('lead_mallet_overlap'))))
    # --- bajo vs bombo
    bass = by_role.get('bass', [None])[0]
    drm = by_role.get('drums', [None])[0]
    if bass and drm and bass.notes:
        kicks = sorted(n.nom for n in drm.notes if n.p in (35, 36))
        import bisect
        co = 0
        for n in bass.notes:
            i = bisect.bisect_left(kicks, n.nom - 0.07)
            if i < len(kicks) and abs(kicks[i] - n.nom) <= 0.07:
                co += 1
        ratio = co / float(len(bass.notes))
        ps = sorted(n.p for n in bass.notes)
        med = ps[len(ps) // 2]
        out.append(_chk('bass_kick', 'Bajo grave y sin chocar con el bombo', 'pass' if ratio <= 0.8 and med <= 45 else 'warn',
                        'mediana %s, %.0f%% de los ataques del bajo coinciden con el bombo' % (T.midi_name(med), 100 * ratio), bool(want.get('bass_kick'))))
    # --- no four-on-the-floor
    if drm:
        kb = {}
        for n in drm.notes:
            if n.p in (35, 36):
                kb.setdefault(int(n.nom // ctx.bb), set()).add(int(round(n.nom % ctx.bb)) % int(ctx.bb))
        fof = sum(1 for k, v in kb.items() if len(v) >= int(ctx.bb))
        out.append(_chk('four_on_floor', 'Sin bombo "four-on-the-floor"', 'pass' if fof == 0 else 'fail',
                        '%d compases con bombo en todas las negras' % fof, bool(want.get('four_on_floor'))))
        if not want.get('four_on_floor') and proj['global'].get('preset') != 'triphop' and out[-1]['status'] == 'fail':
            out[-1]['status'] = 'info'
            out[-1]['detail'] += ' (normal en synthwave; solo se exige si el JSON lo pide o el genero es trip-hop)'
    # --- limites de seccion
    viol = {}
    for b in res.bufs:
        for n in b.notes:
            sec = next((s for s in ctx.secs if s.t0 - 1e-6 <= n.nom < s.t1), None)
            if sec and n.t + n.d > sec.t1 + 0.1 and sec is not ctx.secs[-1]:
                viol[b.track['id']] = viol.get(b.track['id'], 0) + 1
    out.append(_chk('section_bounds', 'Las notas terminan dentro de su seccion', 'pass' if not viol else 'warn',
                    'todas dentro' if not viol else 'cruzan la frontera: %s' % viol, bool(want.get('section_bounds'))))
    # --- repeticion del motivo del coro (ritmo del lead)
    if lead:
        sigs = []
        for s in ctx.secs:
            if s.kind != 'chorus':
                continue
            loop = 8 * ctx.bb
            for k in range(int(s.bars * ctx.bb // loop)):
                a = s.t0 + k * loop
                sig = tuple(round((n.nom - a) * 4) / 4.0 for n in sorted(lead.notes, key=lambda x: x.nom) if a <= n.nom < a + loop)
                sigs.append(('%s[%d-%d]' % (s.id, k * 8, k * 8 + 8), sig))
        pairs = [(x[0], y[0]) for i, x in enumerate(sigs) for y in sigs[i + 1:] if x[1] and x[1] == y[1]]
        if sigs:
            out.append(_chk('motif_repeat', 'El motivo del coro repite con ritmo consistente', 'pass' if pairs else 'warn',
                            ('bucles con ritmo identico: ' + ', '.join('%s = %s' % p for p in pairs)) if pairs else 'ningun bucle del coro repite su ritmo exacto',
                            bool(want.get('motif_repeat'))))
    # --- velocidades: sin maxima constante
    cap = ctx.vcap
    allv = [n.v for b in res.bufs if b.role in E.PITCHED for n in b.notes]
    if allv:
        frac = sum(1 for v in allv if v >= cap - 1) / float(len(allv))
        out.append(_chk('no_constant_max', 'Sin intensidad maxima constante', 'pass' if frac <= 0.10 else 'warn',
                        '%.1f%% de las notas en el tope (%d); velocidad maxima %d' % (100 * frac, cap, max(allv))))
    # --- instrucciones que el motor no puede cumplir en MIDI
    for u in (proj.get('meta') or {}).get('unsupported') or []:
        out.append(_chk('unsupported', 'Instruccion no soportada en MIDI', 'info', u, True))
    if proj.get('guardrails'):
        out.append(_chk('no_auto_score', 'Atractivo / "catchiness"', 'info',
                        'No se puntua automaticamente: requiere escucha y la rubrica humana del JSON.'))
    return out


def validate(res):
    ctx = res.ctx
    bufs = [b for b in res.bufs if b.role in E.PITCHED]
    out = {}
    # --- choques de semitono (1 o 13) no intencionales
    clashes, intent = [], 0
    for b in bufs:
        intent += sum(1 for n in b.notes if n.intent)
    allnotes = [(n, b) for b in bufs for n in b.notes]
    buckets = {}
    for n, b in allnotes:
        for i in range(int(n.t), int(n.t + n.d) + 1):
            buckets.setdefault(i, []).append((n, b))
    seen = set()
    for n, b in allnotes:
        if n.intent:
            continue
        for i in range(int(n.t), int(n.t + n.d) + 1):
            for m, bm in buckets.get(i, []):
                if m is n or m.intent or id(m) < id(n) or (id(n), id(m)) in seen:
                    continue
                if min(n.t + n.d, m.t + m.d) - max(n.t, m.t) >= 0.2 and abs(n.p - m.p) in (1, 13):
                    seen.add((id(n), id(m)))
                    clashes.append(dict(bar=int(max(n.t, m.t) // ctx.bb) + 1, a=b.track['id'], b=bm.track['id'], pitches=[n.p, m.p]))
    out['semitone_clashes_unintended'] = len(clashes)
    out['clash_examples'] = clashes[:8]
    out['intentional_dissonant_notes'] = intent
    out['repairs'] = {'moved': sum(1 for r in ctx.repairs if r['action'] == 'mover'),
                      'removed': sum(1 for r in ctx.repairs if r['action'] == 'quitar')}
    # --- polifonia
    def poly(tol):
        ev = []
        for n, _ in allnotes:
            e = n.t + n.d - tol
            if e > n.t:
                ev += [(n.t, 1), (e, -1)]
        ev.sort(key=lambda x: (x[0], x[1]))
        cur = mx = 0
        for _, d in ev:
            cur += d
            mx = max(mx, cur)
        return mx
    out['max_pitched_polyphony'] = {'raw': poly(0), 'ignoring_legato_overlap': poly(0.06)} if allnotes else {}
    # --- voice leading
    vl = {}
    for tid, log in ctx.voice_log.items():
        mv, gaps, no3, tot = [], [], 0, 0
        for a, b in zip(log, log[1:]):
            if len(a['notes']) == len(b['notes']) and (a['sym'], a['mode']) != (b['sym'], b['mode']):
                mv += [abs(x - y) for x, y in zip(sorted(a['notes']), sorted(b['notes']))]
        seen_k = None
        for e in log:
            k = (e['sym'], tuple(e['notes']))
            if k == seen_k:
                continue
            seen_k = k
            ns = sorted(e['notes'])
            gaps += [y - x for x, y in zip(ns, ns[1:])]
            ch = ctx.chord(e['sym'])
            if ch.true_third:
                tot += 1
                if ch.third_pc not in {x % 12 for x in ns}:
                    no3 += 1
        if mv:
            vl[tid] = dict(avg_movement=round(st.mean(mv), 2), max_movement=max(mv),
                           gaps=[min(gaps), max(gaps)] if gaps else None, chords_without_third='%d/%d' % (no3, tot))
    out['voice_leading'] = vl
    # --- velocidades por seccion
    vel = {}
    for s in ctx.secs:
        row = {}
        for b in res.bufs:
            vs = [n.v for n in b.notes if s.t0 <= n.nom < s.t1]
            if vs:
                row[b.track['id']] = [min(vs), max(vs), len(vs)]
        vel[s.id] = row
    out['velocity_by_section'] = vel
    # --- notas fuera de rango declarado
    oor = {}
    for b in bufs:
        lo, hi = (b.track.get('range') or [0, 127])[:2]
        c = sum(1 for n in b.notes if not (lo - 12 <= n.p <= hi + 12))
        if c:
            oor[b.track['id']] = c
    out['notes_far_outside_range'] = oor
    # --- bateria
    dr = [b for b in res.bufs if b.role == 'drums']
    if dr:
        sn = [(n.t - n.nom) * 60.0 / ctx.bpm * 1000 for n in dr[0].notes
              if getattr(n, 'inst', None) in ('snare', 'snare2') and round(n.nom % ctx.bb, 3) in (1.0, 2.0, 3.0)]
        if sn:
            out['snare_avg_delay_ms'] = round(st.mean(sn))
    # --- cobertura
    empty = [s.name for s in ctx.secs if not any(s.t0 <= n.nom < s.t1 for b in res.bufs for n in b.notes)]
    out['empty_sections'] = empty
    out['bars'] = ctx.total_bars
    out['duration_seconds'] = round(ctx.total_beats * 60.0 / ctx.bpm, 1)
    out['note_counts'] = {b.track['id']: len(b.notes) for b in res.bufs}
    out['lead_notes_by_section'] = {s.id: sum(1 for b in res.bufs if b.role == 'lead' for n in b.notes if s.t0 <= n.nom < s.t1)
                                    for s in ctx.secs}
    out['warnings'] = list(ctx.warnings)
    try:
        out['compliance'] = compliance(res)
    except Exception as e:  # noqa: BLE001
        out['compliance'] = [_chk('compliance_error', 'Error al comprobar', 'warn', '%s: %s' % (type(e).__name__, e))]
    return out
