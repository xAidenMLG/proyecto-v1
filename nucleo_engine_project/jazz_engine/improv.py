"""Phrase Generator + Phrase Scheduler + Rhodes Engine — FASE 5.

Mecanismo genérico de improvisación contextual. Las decisiones musicales viven
en ``profiles.py``; este módulo solo sabe de motivos, frases, silencios y
comportamientos (SUPPORT/RESPONSE/COUNTERPOINT/INDEPENDENT/INTERACTION).

API:
  - ``sax_plan(contexts, plan, profile, seed)`` → {sec_id: [notas]} + evidencia.
    Las notas son frases ``phrases`` del vocabulario nativo de MIDI Forge
    (bar/beat relativos a la sección, pitch entero, dur en beats, vel opcional)
    — se inyectan en ``project['lead']['phrases']`` y el motor las toca con el
    estilo nativo ``auto/phrases`` (scoop/fall, humanización y guardrails del
    motor intactos).
  - ``rhodes_notes(contexts, plan, profile, seed, lead_intervals)`` → notas de
    buffer (render post-generación vía Buf.add en render.py).

Reglas de densidad (obligatorias):
  - el scheduler puede dejar secciones SIN sax (silencio = decisión);
  - máx. N secciones consecutivas con sax y tope de share activo;
  - respiración: tras una frase, la siguiente no arranca en el beat siguiente;
  - Rhodes melódico: tope por sección, nunca llena todos los huecos.
"""
import random

from . import motif as M


def _rng(seed, *parts):
    return random.Random('|'.join(str(x) for x in (seed,) + parts))


# ---------------------------------------------------------------------------
# Scheduler del sax
# ---------------------------------------------------------------------------
def _acciones_sax(contexts, plan, profile):
    """Decide por sección: acción de sax o None (silencio), con caps globales."""
    sx = profile.sax
    plan_secc = plan['sections']
    acciones = {}
    consecutivos = 0
    activas = 0
    total = max(1, len(contexts))
    tope_activas = int(round(total * float(sx.get('max_active_share', 0.65))))
    idx_verse_vista = 0
    for sc in contexts:
        dec = plan_secc[sc.id]
        accion_base = sx['section_plan'].get(sc.type, 'respond')
        prob = sx.get('prob_overrides', {}).get(sc.type, 1.0)
        rng = _rng(plan.get('seed_used', 0), 'sax_sched', sc.id)
        accion = None
        if accion_base != 'absent':
            if consecutivos >= int(sx.get('max_consecutive', 2)):
                accion = None                      # respiración obligatoria
            elif activas >= tope_activas and accion_base not in ('statement', 'final'):
                accion = None
            elif rng.random() < float(dec.get('density', 1.0)) * prob:
                accion = accion_base
                if accion_base == 'statement':
                    idx_verse_vista += 1
                    if idx_verse_vista > 1:
                        accion = 'develop'         # verses posteriores: desarrollo
        else:
            accion = None
        acciones[sc.id] = accion
        if accion:
            consecutivos += 1
            activas += 1
        else:
            consecutivos = 0
    return acciones


def _vel_para(sc, sx, rng, frac, vel_range):
    base_lo, base_hi = sx.get('vel_by_type', {}).get(sc.type, vel_range)
    lo, hi = base_lo, base_hi
    v = lo + (hi - lo) * (0.35 + 0.65 * frac) + rng.uniform(-4, 4)
    # acento suave en nota fuerte
    return v


def sax_plan(contexts, plan, profile, seed):
    """Genera las frases del sax por sección. Devuelve (phrases, evidencia)."""
    sx = profile.sax
    acciones = _acciones_sax(contexts, plan, profile)
    phrases, evid = {}, []
    motivos = {}                     # material previo por 'canción' (id interno)
    motivo_principal = None
    vez = 0
    for sc in contexts:
        accion = acciones[sc.id]
        if accion is None:
            evid.append({"seccion": sc.id, "accion": "silencio"})
            continue
        vez += 1
        rng = _rng(seed, 'sax', sc.id)
        register = profile.REGISTER['sax_tenor']  # noqa: usados por estilo
        _estilo_local = accion
        # localización de la frase: nunca arranca en el beat 1 salvo statement;
        # deja aire al inicio de la sección (respiración)
        if accion in ('statement', 'develop'):
            n_bars = min(sc.bars, rng.randint(*sx.get('phrase_bars', (1, 3))))
            bar_ini = 0 if accion == 'statement' else rng.choice((0, 1)) if sc.bars > n_bars else 0
            if bar_ini + n_bars > sc.bars:
                bar_ini = max(0, sc.bars - n_bars)
            estilo = 'statement' if accion == 'statement' else 'develop'
            notas, meta = M.generar_motivo(sc, bar_ini, n_bars, rng, profile, register, 'statement')
            transform = None
            # DESARROLLO: si hay material previo, transformar (no desde cero).
            # Regla de calidad: la transformación debe DIFERIR audiblemente del
            # material base (≥ 30 % de eventos cambiados); si una transformación
            # no cambia nada (p. ej. reharmonize sobre la misma armonía), se
            # prueba la siguiente en orden determinista.
            if accion == 'develop' and motivo_principal:
                base, base_meta = motivo_principal
                opciones = ['reharmonize', 'displace', 'vary_ending', 'fragment', 'invert']
                rng.shuffle(opciones)
                for trans in opciones:
                    notas2, trans_name = M.transformar(base, trans, sc, bar_ini, rng, profile, register)
                    if len(notas2) >= 2 and _difiere(notas2, base):
                        notas, meta = notas2, dict(base_meta, transform=trans_name)
                        transform = trans_name
                        break
                if transform is None:
                    notas2, transform = M.transformar(base, 'vary_ending', sc, bar_ini,
                                                      rng, profile, register)
                    if len(notas2) >= 2:
                        notas, meta = notas2, dict(base_meta, transform=transform)
                    else:
                        transform = None
            if motivo_principal is None:
                motivo_principal = (list(notas), meta)
        elif accion == 'respond':
            n_bars = 1
            bar_ini = min(sc.bars - 1, rng.choice((1, 2))) if sc.bars >= 2 else 0
            notas, meta = M.generar_motivo(sc, bar_ini, n_bars, rng, profile, register, 'response')
            transform = None
        elif accion == 'question':
            n_bars = 1
            bar_ini = min(sc.bars - 1, 1) if sc.bars >= 2 else 0
            notas, meta = M.generar_motivo(sc, bar_ini, n_bars, rng, profile, register, 'response')
            if motivo_principal and rng.random() < 0.5:
                notas, transform = M.transformar(motivo_principal[0], 'fragment', sc, bar_ini,
                                                 rng, profile, register)
            else:
                transform = None
        elif accion == 'suspend':
            n_bars = 1
            bar_ini = min(sc.bars - 1, 1) if sc.bars >= 2 else 0
            notas, meta = M.generar_motivo(sc, bar_ini, n_bars, rng, profile, register, 'suspension')
            transform = None
        else:  # final
            n_bars = 1
            bar_ini = 0
            if motivo_principal and rng.random() < 0.6:
                trans = rng.choice(('reharmonize', 'vary_ending'))
                notas, transform = M.transformar(motivo_principal[0], trans, sc, bar_ini,
                                                 rng, profile, register)
                notas = notas[:max(2, len(notas) // 2)]      # fragmento final que decae
            else:
                notas, meta = M.generar_motivo(sc, bar_ini, n_bars, rng, profile, register, 'response')
                transform = None
        if not notas:
            evid.append({"seccion": sc.id, "accion": accion, "notas": 0})
            continue
        # recorte duro a la sección (guardrail section_bounds): misma invariante
        # E111 del contrato — bar·4 + beat + dur ≤ bars·4
        notas = [n for n in notas if 0 <= n['bar'] < sc.bars]
        for n in notas:
            fin = n['bar'] * 4.0 + n['beat'] + n['dur']
            if fin > sc.bars * 4.0:
                n['dur'] = round(max(0.25, sc.bars * 4.0 - n['bar'] * 4.0 - n['beat']), 3)
        # velocities: arco de frase + acento suave en fuertes
        lo, hi = sx.get('vel_range', (58, 84))
        vels = []
        n = len(notas)
        for i, nt in enumerate(notas):
            frac = i / float(max(1, n - 1))
            v = _vel_para(sc, sx, rng, frac, (lo, hi))
            if nt.get('strong'):
                v += 4
            if nt.get('tension'):
                v -= 3
            vels.append(int(max(lo - 6, min(hi + 2, v))))
        frase = [{"bar": int(nt['bar']), "beat": round(float(nt['beat']), 3),
                  "pitch": int(nt['pitch']), "dur": round(float(nt['dur']), 3), "vel": v}
                 for nt, v in zip(notas, vels)]
        phrases[sc.id] = frase
        objetivos = sum(1 for nt in notas if nt.get('strong'))
        evid.append({"seccion": sc.id, "accion": accion, "transform": transform,
                     "notas": len(frase), "compases": sorted({nt['bar'] for nt in notas}),
                     "objetivos_armonicos": objetivos, "tensiones": sum(1 for nt in notas if nt.get('tension'))})
    evidencia = {"frases": evid, "secciones_con_sax": sum(1 for a in acciones.values() if a),
                 "secciones_total": len(contexts)}
    return phrases, evidencia


# ---------------------------------------------------------------------------
# Rhodes melódico (comportamientos contextuales)
# ---------------------------------------------------------------------------
def _huecos_de(lead_iv, t0, t1, min_gap):
    """Sub-intervalos de [t0, t1] sin notas del lead. lead_iv: (t0, t1, pitch)."""
    out = []
    cur = t0
    for a, b, _p in lead_iv:
        if b <= t0:
            continue
        if a >= t1:
            break
        if a - cur >= min_gap:
            out.append((cur, a))
        cur = max(cur, b)
    if t1 - cur >= min_gap:
        out.append((cur, t1))
    return out


def rhodes_notes(contexts, plan, profile, seed, lead_iv):
    """Notas melódicas del Rhodes por sección (beats absolutos del proyecto).

    ``lead_iv``: intervalos (t0, t1) de notas del sax ya generadas — el Rhodes
    escucha al sax ANTES de decidir (interacción real, no paralela).
    Devuelve (notas, evidencia). notas: dicts {t, dur, pitch, vel} absolutos.
    """
    rz = profile.rhodes
    lo_r, hi_r = rz['register']
    out, evid = [], []
    melodic_sections = 0
    total = max(1, len(contexts))
    tope = int(round(total * float(rz.get('max_sections_melodic_share', 0.5))))
    motivo_ultimo = None
    for sc in contexts:
        dec = plan['sections'][sc.id]
        beh = dec.get('rhodes_mode') or 'support'
        if beh == 'support':
            evid.append({"seccion": sc.id, "modo": "support", "notas": 0})
            continue
        if melodic_sections >= tope and beh != 'interaction':
            evid.append({"seccion": sc.id, "modo": beh, "notas": 0, "razon": "tope_global"})
            continue
        rng = _rng(seed, 'rhodes', sc.id)
        prob = rz['prob_by_behavior'].get(beh, 0.3) * float(dec.get('density', 1.0))
        if rng.random() >= prob:
            evid.append({"seccion": sc.id, "modo": beh, "notas": 0, "razon": "espacio"})
            continue
        vel_lo, vel_hi = rz['vel_range']
        cap = rng.randint(*rz['notes_per_section_cap'])
        notas = []
        if beh in ('response', 'interaction'):
            # responde a frases del sax: primera respuesta tras el fin de una frase
            frases_fin = _fines_de_frase(lead_iv, sc.t0, sc.t1)
            if frases_fin:
                t_ini = frases_fin[0] + rng.uniform(*rz['answer_gap'])
            else:
                t_ini = sc.t0 + rng.choice((1.0, 1.5))
            gap = 2.5
        elif beh == 'counterpoint':
            # bajo frases sostenidas del sax: notas en los huecos, registro interno
            huecos = _huecos_de(lead_iv, sc.t0, sc.t1, 1.25)
            if not huecos:
                evid.append({"seccion": sc.id, "modo": beh, "notas": 0, "razon": "sin_huecos"})
                continue
            notas_ct = []
            for h0, h1 in huecos[:2]:
                t = h0 + 0.25
                if t + 0.5 > h1:
                    continue
                notas_ct.append(t)
            t_ini = notas_ct[0] if notas_ct else None
            gap = 2.0
        else:  # independent
            t_ini = sc.t0 + rng.choice((0.0, 0.5, 2.0))
            gap = 3.0
        if t_ini is None:
            evid.append({"seccion": sc.id, "modo": beh, "notas": 0, "razon": "sin_espacio"})
            continue
        # material: eco del último motivo del sax (respuesta real) o motivo breve
        sc_local = sc
        if motivo_ultimo and beh in ('response', 'interaction'):
            base = [dict(n) for n in motivo_ultimo[:rng.randint(2, 3)]]
            frag = M.fragment(base, len(base), 0)
            # reancora al acorde local
            frag = M.reharmonize(_relativizar(frag), sc_local, 0, (lo_r, hi_r))
        elif motivo_ultimo and beh == 'counterpoint':
            frag = M.fragment(_relativizar([dict(n) for n in motivo_ultimo]),
                              2, 0) if rng.random() < 0.6 else []
            if frag:
                frag = M.reharmonize(frag, sc_local, 0, (lo_r, hi_r))
        else:
            frag, _meta = M.generar_motivo(sc_local, 0, 1, rng, profile, (lo_r, hi_r), 'response')
            frag = frag[:rng.randint(2, 3)]
        if not frag:
            evid.append({"seccion": sc.id, "modo": beh, "notas": 0, "razon": "material_vacio"})
            continue
        t = t_ini
        for nt in frag:
            if len(notas) >= cap:
                break
            dur = max(0.5, float(nt['dur']))
            pitch = int(nt['pitch'])
            # no pisar al sax (distancia ≥ 2 st si solapa) ni salir del registro
            if not _libre_de_lead(lead_iv, t, t + dur, pitch, 2):
                t += 0.5
                continue
            if t + dur > sc.t1:
                dur = max(0.4, sc.t1 - t)
            vel = int(rng.randint(vel_lo, vel_hi))
            out.append({"t": round(t, 3), "dur": round(dur, 3), "pitch": pitch, "vel": vel,
                        "sec": sc.id, "beh": beh})
            notas.append(nt)
            t += dur + rng.choice((0.25, 0.5, 0.75))
        melodic_sections += 1
        evid.append({"seccion": sc.id, "modo": beh, "notas": len(notas)})
    return out, {"evidencia": evid, "secciones_melodicas": melodic_sections}


def _relativizar(notas):
    """Notas del sax (bar relativo a su sección) → material relativo a bar 0."""
    if not notas:
        return []
    b0 = notas[0]['bar']
    return [dict(n, bar=n['bar'] - b0) for n in notas]


def _difiere(nuevas, base, umbral=0.3):
    """¿Difieren audiblemente? (≥ umbral de eventos con (bar,beat,pitch) distintos)."""
    if not base:
        return bool(nuevas)
    a = {(n['bar'], round(n['beat'], 2), n['pitch']) for n in nuevas}
    b = {(n['bar'], round(n['beat'], 2), n['pitch']) for n in base}
    if not b:
        return bool(a)
    comunes = len(a & b) / float(max(len(a), len(b)))
    return comunes <= (1.0 - umbral)


def _fines_de_frase(lead_iv, t0, t1):
    """Fines de frase del sax dentro de la sección: huecos ≥ 1.5 beats tras notas."""
    fines = []
    starts = sorted(a for a, _b, _p in lead_iv)
    for a, b, _p in lead_iv:
        if a < t0 or a >= t1:
            continue
        nxt = next((x0 for x0 in starts if x0 >= b), None)
        if nxt is None or nxt - b >= 1.5:
            fines.append(b)
    return sorted(set(fines))


def _libre_de_lead(lead_iv, t0, t1, pitch, mind):
    """¿Puede sonar [t0, t1] con ``pitch`` sin pisar al lead? (distancia < mind st
    con solape temporal bloquea; unisión temporal también)."""
    for a, b, p in lead_iv:
        if a >= t1:
            break
        if min(b, t1) - max(a, t0) > 0.2 and abs(pitch - p) < mind:
            return False
    return True
