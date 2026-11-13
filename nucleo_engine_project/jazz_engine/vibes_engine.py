"""Vibraphone Engine — FASE 5.

Dos mecanismos COMPLEMENTARIOS (nada duplicado):
  1. Params: ajusta los bloques ``mallet`` del compilador (estilo replies/pings)
     con los params del perfil — transformación PURA de proyecto (midi-forge/1).
  2. Respuestas con material: notas de ECO del motivo del sax en huecos reales
     del lead, en render (vía Buf.add) usando los huecos calculados contra las
     notas del sax ya generadas. Presupuesto estricto: ≤ max_present_share de
     compases del tema (guardrail mallet_sparse del motor se respeta).
"""
import copy
import random


def aplicar_params(project, contexts, plan, profile, seed):
    """Ajuste puro de params mallet por sección. (proyecto_nuevo, evidencia)."""
    vb = profile.vibes
    proj = copy.deepcopy(project)
    secs = {s['id']: s for s in proj.get('sections', [])}
    ev = []
    for sc in contexts:
        sec = secs.get(sc.id)
        if not sec:
            continue
        blk = sec.setdefault('blocks', {}).get('vibraphone')
        if not blk or not blk.get('enabled', True):
            continue
        ajustes = vb.get('replies_params', {}).get(sc.type)
        if ajustes and blk.get('style') == 'replies':
            params = blk.setdefault('params', {})
            dens = plan['density']['vibes']
            params['prob'] = round(min(0.85, float(ajustes.get('prob', params.get('prob', 0.5))) * dens), 3)
            params['max_per_bar'] = max(1, int(round(ajustes.get('max_per_bar', 1) * min(1.0, dens))))
            params.setdefault('respond_to', 'lead')
            ev.append({"seccion": sc.id, "prob": params['prob'], "max_per_bar": params['max_per_bar']})
        elif ajustes and blk.get('style') == 'pings' and plan['density']['vibes'] < 0.8:
            blk['params']['count'] = 1                 # atmósfera: menos pings
            ev.append({"seccion": sc.id, "pings": 1})
    return proj, {"secciones": ev}


def _huecos_de(lead_iv, t0, t1, min_gap):
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


def notas_eco(contexts, plan, profile, seed, lead_iv, lead_phrases_plan):
    """Eco motivico del vibráfono tras frases del sax (render-time).

    ``lead_phrases_plan``: {sec_id: [notas phrases]} — material del sax para
    extraer el eco. Devuelve (notas, evidencia); notas absolutas en beats.
    """
    vb = profile.vibes
    lo, hi = vb.get('echo_register', (74, 86))
    vel_lo, vel_hi = vb.get('echo_vel', (38, 50))
    out, evid = [], []
    usadas = 0
    presupuesto = int(plan.get('vibes_budget', 99))
    for sc in contexts:
        frase = lead_phrases_plan.get(sc.id) or []
        if not frase:
            evid.append({"seccion": sc.id, "ecos": 0, "razon": "sin_frase_sax"})
            continue
        if usadas >= presupuesto:
            evid.append({"seccion": sc.id, "ecos": 0, "razon": "presupuesto"})
            continue
        # dado POR SECCIÓN (mismo criterio que sax/rhodes): el eco RESPONDE al
        # sax, así que se evalúa en secciones CON frase del sax
        rng = random.Random('|'.join(str(x) for x in (seed, 'vibes', sc.id)))
        if rng.random() >= float(vb.get('echo_prob', 0.5)) * plan['density']['vibes']:
            evid.append({"seccion": sc.id, "ecos": 0, "razon": "espacio"})
            continue
        # fin de la frase del sax (última nota) + margen
        fin_frase = max(f['bar'] * 4.0 + f['beat'] + f['dur'] for f in frase) + sc.t0
        huecos = _huecos_de(lead_iv, fin_frase + 0.75, sc.t1, 1.0)
        if not huecos:
            evid.append({"seccion": sc.id, "ecos": 0, "razon": "sin_hueco"})
            continue
        h0, h1 = huecos[0]
        # eco: 1-2 primeras notas del motivo, transpuestas al registro del vibes
        n_echo = rng.randint(*vb.get('echo_notes', (1, 2)))
        base = sorted(frase, key=lambda f: (f['bar'], f['beat']))[:n_echo]
        t = min(h0 + 0.25, h1 - 0.5)
        hechos = 0
        for f in base:
            if hechos >= n_echo or t + 0.4 > min(h1, sc.t1):
                break
            pc_sax = f['pitch'] % 12
            cands = [p for p in range(lo, hi + 1) if p % 12 == pc_sax]
            if not cands:
                continue
            cand = min(cands, key=lambda p: abs(p - (lo + hi) // 2))
            # no pisar al sax
            choque = any(min(b, t + 0.6) - max(a, t) > 0.2 and abs(cand - p) < 5
                         for a, b, p in lead_iv)
            if choque:
                t += 0.5
                continue
            out.append({"t": round(t, 3), "dur": round(max(0.75, min(float(f['dur']), h1 - t)), 3),
                        "pitch": int(cand), "vel": int(rng.randint(vel_lo, vel_hi)),
                        "sec": sc.id})
            hechos += 1
            t += 0.75
        usadas += 1
        evid.append({"seccion": sc.id, "ecos": hechos})
    return out, {"evidencia": evid, "secciones_con_eco": usadas}
