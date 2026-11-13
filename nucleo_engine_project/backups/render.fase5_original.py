"""Render con motores — FASE 5.

Orquesta la generación REUTILIZANDO las primitivas de forge (Ctx, Buf,
GENERATORS, repair_clashes, finalize, compute_bends, build_ccs,
build_midi_bytes): jazz_engine NO duplica el motor; solo añade dos hooks de
buffer entre la generación y la reparación de choques:

  - Rhodes melódico: notas escuchando al sax ya generado (Buf.add);
  - Eco del vibráfono: respuestas motivicas en huecos reales del lead (Buf.add).

Garantías:
  - ``generate(project, None)`` == ``forge.engine.generate(project)`` byte a
    byte (delegación directa);
  - con TODOS los motores apagados también delega (idempotencia);
  - con motores activos, todo el azar es semillado (determinismo).
"""
from forge import adapter as A
from forge import engine as E

from . import coordinator, enhance as enhance_mod, improv, vibes_engine
from .context import build_contexts


def generate(project, config=None):
    """Genera MIDI. ``config=None`` → delegación 1:1 al motor (golden path)."""
    if config is None:
        return E.generate(project)
    cfg = coordinator.normalize_config(config)
    if not any(cfg['engines'].values()):
        return E.generate(project)                      # path original intacto

    proj2, plan, ev = enhance_mod.enhance(project, cfg)
    profile = enhance_mod.resolver_profile(project, cfg)
    seed = int(cfg.get('seed', 0))
    # normalización oficial del pipeline (canales, defaults por rol, coerciones):
    # mismo paso que run_generate; las frases/params inyectados sobreviven.
    proj2, _rep = A.normalize(proj2, None)
    contexts = build_contexts(proj2, profile)

    ctx = E.Ctx(proj2)
    res = E.Result()
    res.ctx = ctx
    res.plan = plan
    res.evidence = ev
    res.engines = dict(cfg['engines'])

    active = E._active_tracks(proj2)
    ctx.generated = {}
    for tr in sorted(active, key=lambda t: 1 if t['role'] == 'mallet' else 0):
        buf = E.Buf(tr, ctx)
        gen = E.GENERATORS.get(tr['role'])
        if gen is None:
            ctx.warn('Rol desconocido: %s' % tr['role'])
            continue
        gen(ctx, tr, buf)
        ctx.generated[tr['id']] = buf
    bufs = [ctx.generated[t['id']] for t in active if t['id'] in ctx.generated]

    # ---------------- hooks jazz_engine (post-generación, pre-reparación) ----
    lead_buf = next((b for b in bufs if b.role == 'lead'), None)
    lead_iv = sorted([(n.t, n.t + n.d, n.p) for n in lead_buf.notes]) if lead_buf else []
    sec_by_id = {s.id: s for s in ctx.secs}
    ev['rhodes'] = {"desactivado": True}
    ev['vibes_eco'] = {"desactivado": True}

    if cfg['engines'].get('rhodes') and lead_iv:
        keys_buf = next((b for b in bufs if b.role == 'keys'), None)
        if keys_buf is not None:
            notas, ev_rh = improv.rhodes_notes(contexts, plan, profile, seed, lead_iv)
            for nt in notas:
                sec = sec_by_id.get(nt['sec'])
                if sec is None:
                    continue
                rng = ctx.rng('jazz_rhodes', nt['sec'])
                keys_buf.add(nt['t'], nt['dur'], nt['pitch'], nt['vel'], rng,
                             legato=0.95, sec=sec)
            ev['rhodes'] = ev_rh

    if cfg['engines'].get('vibes') and lead_iv:
        mal_buf = next((b for b in bufs if b.role == 'mallet'), None)
        if mal_buf is not None:
            notas, ev_ve = vibes_engine.notas_eco(contexts, plan, profile, seed, lead_iv,
                                                  plan.get('sax_phrases') or {})
            for nt in notas:
                sec = sec_by_id.get(nt['sec'])
                if sec is None:
                    continue
                rng = ctx.rng('jazz_vibes', nt['sec'])
                mal_buf.add(nt['t'], nt['dur'], nt['pitch'], nt['vel'], rng,
                            legato=1.0, sec=sec)
            ev['vibes_eco'] = ev_ve

    # ---------------- continuación idéntica a forge.engine.generate ----------
    if ctx.g.get('repair_clashes', True):
        E.repair_clashes(ctx, bufs)
    for b in bufs:
        b.finalize()
    ending = proj2.get('ending') or {}
    tape = None
    ts = ending.get('tape_stop') or {}
    if ts.get('enabled'):
        nb = float(ts.get('bars', 2))
        tape = dict(t0=ctx.total_beats - nb * ctx.bb, t1=ctx.total_beats,
                    semitones=float(ts.get('semitones', -8.4)),
                    range=float(ts.get('range', 12)), exponent=float(ts.get('exponent', 1.7)))
    res.tape = tape
    res.bufs = bufs
    res.bends = {b.track['id']: E.compute_bends(ctx, b, tape) for b in bufs if b.role != 'drums'}
    res.ccs = E.build_ccs(ctx, bufs, tape)
    res.midi = E.build_midi_bytes(ctx, bufs, res)
    return res


def metrics(res):
    """Métricas de evidencia a partir de un resultado (con o sin motores)."""
    ctx = res.ctx
    out = {
        "bpm": ctx.bpm,
        "total_bars": ctx.total_bars,
        "duration_seconds": round(ctx.total_beats * 60.0 / ctx.bpm, 1),
        "notas_por_pista": {b.track['id']: len(b.notes) for b in res.bufs},
        "lead_por_seccion": {s.id: sum(1 for b in res.bufs if b.role == 'lead'
                                       for n in b.notes if s.t0 <= n.nom < s.t1)
                             for s in ctx.secs},
        "rhodes_melodico_por_seccion": {},
        "secciones": [s.id for s in ctx.secs],
    }
    ev = getattr(res, 'evidence', None) or {}
    if isinstance(ev.get('rhodes'), dict) and 'evidencia' in ev['rhodes']:
        out['rhodes_melodico_por_seccion'] = {e['seccion']: e['notas'] for e in ev['rhodes']['evidencia']}
    if isinstance(ev.get('vibes_eco'), dict) and 'evidencia' in ev['vibes_eco']:
        out['vibes_eco_por_seccion'] = {e['seccion']: e['ecos'] for e in ev['vibes_eco']['evidencia']}
    if isinstance(ev.get('sax'), dict) and 'frases' in ev.get('sax', {}):
        out['sax_frases'] = [f for f in ev['sax']['frases'] if f.get('accion') != 'silencio'
                             and f.get('notas', 0) > 0 or f.get('accion') == 'silencio']
        out['sax_frases_activas'] = [f for f in ev['sax']['frases']
                                     if f.get('accion') not in (None, 'silencio') and f.get('notas', 0) > 0]
    return out
