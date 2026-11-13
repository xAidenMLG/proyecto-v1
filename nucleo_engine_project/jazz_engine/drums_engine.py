"""Drums Engine — FASE 5 (Dark Trip Hop).

Groove sobre el preset base del compilador: microvariación (ghost notes,
acentos), variación por ciclo, fills de transición SOLO donde el coordinador
marca "build", ruptura controlada con reconstrucción en break/bridge.

Transformación PURA de proyecto: entrada proyecto compilado → salida proyecto
con ``sections[].blocks.drums.params`` enriquecidos con vocabulario NATIVO de
MIDI Forge (layers con at/pick/prob/vel/when, fills con rolls/hits/mute,
light_bars, vel_scale). El resultado sigue siendo midi-forge/1 válido y puede
generarse con ``forge.engine.generate`` sin jazz_engine.
"""
import copy

from forge import styles as S

_PRESETS_CON_GROOVE = {"trip_verse", "trip_chorus"}


def _when_bar_mod(m, r):
    return {"bar_mod": [m, r]}


def aplicar(project, contexts, plan, profile, seed):
    """Devuelve (proyecto_nuevo, evidencia). No muta la entrada."""
    dr = profile.drums
    proj = copy.deepcopy(project)
    secs = {s['id']: s for s in proj.get('sections', [])}
    ev = []
    for sc in contexts:
        dec = plan['sections'][sc.id]
        actitud = dec['drums_attitude']
        sec = secs.get(sc.id)
        if not sec:
            continue
        blocks = sec.setdefault('blocks', {})
        blk = blocks.get('drums')
        if not blk or not blk.get('enabled', True) or blk.get('style') != 'pattern':
            ev.append({"seccion": sc.id, "actitud": actitud, "cambios": 0,
                       "razon": "bloque_drums_ausente"})
            continue
        params = blk.setdefault('params', {})
        cambios = []
        # ---- base: capas del preset actual (se conservan; las nuestras se añaden)
        preset_name = params.get('preset') or 'trip_verse'
        base_layers = copy.deepcopy(params.get('layers') or S.DRUM_PRESETS.get(preset_name, {}).get('layers', []))
        nuevas = list(base_layers)
        # ---- ruptura/reconstrucción (Familiaridad → Deformación → Ruptura → Reconstrucción)
        if actitud == 'drop':
            rup = dr.get('rupture', {})
            lb = int(rup.get('light_bars', 2))
            if lb:
                params['light_bars'] = lb                    # arranque sin groove completo
            if rup.get('vel_scale_delta'):
                params['vel_scale'] = round(float(params.get('vel_scale', 1.0)) + rup['vel_scale_delta'], 4)
                cambios.append('vel_scale-%.2f' % rup['vel_scale_delta'])
        elif actitud == 'recover':
            params['vel_scale'] = round(float(params.get('vel_scale', 1.0)) * 0.94, 4)
            nuevas.append({"inst": "rim", "at": [3.5], "vel": 46, "prob": 0.4,
                           "offset": 0.037})             # reconstrucción tímida
            cambios.append('recover_rim')
        # ---- ghost notes (microvariación; escala con energía de la sección)
        if actitud in ('vary', 'build', 'recover'):
            gh = dr.get('ghost', {})
            prob = float(gh.get('base_prob', 0.3)) * (0.6 + 0.8 * sc.energy) * plan['density']['drums']
            prob = max(0.05, min(0.6, prob))
            for inst in gh.get('insts', ()):
                picks = gh.get('picks', {}).get(inst) or [3.5]
                vel_lo, vel_hi = gh.get('vel_range', (20, 34))
                nuevas.append({"inst": inst, "pick": list(picks), "prob": round(prob, 3),
                               "vel_rand": [vel_lo, vel_hi], "offset": gh.get('offset', 0.05),
                               "when": _when_bar_mod(2, 1)})       # solo compases impares del ciclo
                cambios.append('ghost:%s' % inst)
        # ---- acento de kick fuera del patrón de bajo (no pisa bass_kick)
        if actitud in ('vary', 'build'):
            ak = dr.get('accent_kick', {})
            poses = ak.get('positions_by_type', {}).get(sc.type) or []
            for pos in poses:
                nuevas.append({"inst": "kick", "at": [pos], "vel": ak.get('vel', 58),
                               "prob": ak.get('prob', 0.55), "offset": -0.006,
                               "when": _when_bar_mod(*ak.get('when_bar_mod', [4, 3]))})
                cambios.append('accent_kick@%s' % pos)
        # ---- variación de hats (open hat de acento ocasional)
        if actitud == 'vary':
            hv = dr.get('hat_variation', {})
            nuevas.append({"inst": "open_hat", "at": [hv.get('position', 3.5)],
                           "vel_rand": list(hv.get('vel_range', (50, 62))),
                           "prob": hv.get('prob', 0.25), "dur": 0.25,
                           "when": _when_bar_mod(*hv.get('when_bar_mod', [4, 2]))})
            cambios.append('hat_var')
        # ---- fill de transición SOLO en secciones build (nada de fills constantes)
        if actitud == 'build' and sc.type in dr.get('transition_fill', {}).get('types', ()):
            tf = dr['transition_fill']
            rolls = copy.deepcopy(tf.get('rolls', []))
            fills = list(params.get('fills') or [])
            fills.append({"when": {"last": True},
                          "mute": [{"inst": "snare2", "from": tf.get('mute_from', 3.0)}],
                          "rolls": rolls})
            params['fills'] = fills
            cambios.append('fill_transicion')
        params['layers'] = nuevas
        ev.append({"seccion": sc.id, "actitud": actitud, "preset": preset_name,
                   "cambios": cambios})
    return proj, {"secciones": ev}
