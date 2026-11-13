"""Motif Generator + Motif Development — FASE 5 (mecanismo genérico).

Un MOTIVO es una célula rítmica con un contorno interválico anclado a la
armonía: los tiempos fuertes caen en tonos del acorde (preferencia por guías
3ª/7ª), los débiles en notas de escala, con aproximaciones cromáticas/diatónicas
opcionalmente antes de un objetivo. El desarrollo aplica transformaciones
clásicas SIEMPRE respecto del material previo (nunca desde cero).

Determinismo: toda función recibe ``rng`` (random.Random con semilla compuesta);
misma semilla + mismo contexto → mismo motivo. Sin estado global.

Reglas de calidad (duras, verificables):
  - salto ≥ 5 semitonos → compensación por paso contrario;
  - máx. 2 repeticiones consecutivas del mismo pitch;
  - tiempos fuertes (beat 0 y 2) en tono del acorde;
  - toda nota dentro del registro del instrumento;
  - la última nota de una frase resuelve a guía del acorde siguiente o queda
    abierta (5ª/9ª) según ``open_ending_prob`` del perfil.
"""
import math

from forge import theory as T

FORTE_BEATS = (0.0, 2.0)


def _wc(rng, pairs):
    xs, ws = zip(*pairs)
    return rng.choices(xs, weights=ws, k=1)[0]


# ---------------------------------------------------------------------------
# Generación
# ---------------------------------------------------------------------------
def _cell_notes(sc, bar, cell, rng, movement, register, bh, prev_pitch, bh_next,
                open_ending_prob, approach_prob, tension_prob, first_strong_guide=True):
    """Notas de UN compás a partir de una celda. Devuelve (notas, prev_pitch)."""
    lo, hi = register
    out = []
    strong_i = None
    for i, (onset, _d) in enumerate(cell):
        if onset in FORTE_BEATS and strong_i is None:
            strong_i = i
    pitch = prev_pitch
    last_off = None
    for i, (onset, dur) in enumerate(cell):
        es_forte = onset in FORTE_BEATS
        es_ultimo = i == len(cell) - 1
        objetivo_pc = None
        if es_forte:
            guias = bh.guide_pcs
            tonos = bh.chord_tone_pcs
            if first_strong_guide and i == strong_i and guias:
                objetivo_pc = guias[rng.randrange(len(guias))]
            elif tonos:
                objetivo_pc = tonos[rng.randrange(len(tonos))]
        if pitch is None:
            if objetivo_pc is not None:
                pitch = sc.nearest_pitch_with_pc(objetivo_pc, (lo + hi) // 2, lo, hi) or (lo + hi) // 2
            else:
                pitch = sc.snap_to_scale((lo + hi) // 2, lo, hi)
            out.append({"bar": bar, "beat": onset, "dur": dur, "pitch": int(pitch),
                        "strong": es_forte, "tension": False})
            continue
        # movimiento desde la nota previa
        if last_off is not None and abs(last_off) >= 5:
            # compensación obligatoria: paso contrario pequeño
            step = -int(math.copysign(rng.choice((1, 2)), last_off))
            cand = pitch + step
        elif es_ultimo and bh_next is not None and rng.random() >= open_ending_prob:
            # resolución: guía del acorde siguiente, vía aproximación
            guia = bh_next.guide_pcs[rng.randrange(len(bh_next.guide_pcs))] if bh_next.guide_pcs else None
            if guia is None:
                cand = pitch + _wc(rng, movement)
            else:
                destino = sc.nearest_pitch_with_pc(guia, pitch + rng.choice((-3, -2, 2, 3)), lo, hi)
                if destino is None:
                    cand = pitch + _wc(rng, movement)
                else:
                    paso = destino - pitch
                    paso = max(-5, min(5, paso))
                    cand = pitch + paso
        else:
            cand = pitch + _wc(rng, movement)
        # anclaje a la armonía
        if objetivo_pc is not None:
            fijado = sc.nearest_pitch_with_pc(objetivo_pc, cand, lo, hi)
            if fijado is not None:
                cand = fijado
        elif not es_ultimo:
            cand = sc.snap_to_scale(cand, lo, hi)
        else:
            cand = max(lo, min(hi, cand))
        # tensiones de color en nota débil previa al objetivo (9/13)
        es_tension = False
        if (not es_forte) and (not es_ultimo) and rng.random() < tension_prob:
            tpcs = bh.tension_pcs
            if tpcs:
                t_pitch = sc.nearest_pitch_with_pc(tpcs[rng.randrange(len(tpcs))], cand, lo, hi)
                if t_pitch is not None and abs(t_pitch - pitch) <= 4:
                    cand, es_tension = t_pitch, True
        # aproximación cromática ANTES de un fuerte (nota de paso medio tono abajo/arriba)
        if es_forte and i > 0 and rng.random() < approach_prob and not es_tension:
            obj = cand
            ap = obj + rng.choice((-1, 1))
            if lo <= ap <= hi and ap != pitch:
                out.append({"bar": bar, "beat": max(0.0, onset - 0.25), "dur": min(0.25, onset),
                            "pitch": int(ap), "strong": False, "tension": False, "approach": True})
        out.append({"bar": bar, "beat": onset, "dur": dur, "pitch": int(cand),
                    "strong": es_forte, "tension": es_tension})
        last_off = cand - pitch
        pitch = cand
    return out, pitch


def generar_motivo(sc, bar_ini, n_bars, rng, profile, register, estilo="statement"):
    """Motivo nuevo de ``n_bars`` compases desde ``bar_ini`` (relativo a la sección).

    estilo: statement (células completas) | response (células de respuesta) |
            suspension (tonos largos). Devuelve (notas, meta) — meta incluye el
            contorno para evidencia de desarrollo.
    """
    sx = profile.sax
    if estilo == "response":
        cells = sx.get("cells_response")
    elif estilo == "suspension":
        cells = sx.get("cells_suspension")
    else:
        cells = sx.get("cells")
    movement = sx.get("movement")
    lo, hi = register
    notes = []
    prev = None
    contour = []
    for j in range(n_bars):
        bh = sc.harmony_at_bar(bar_ini + j)
        bh_next = sc.next_harmony(bar_ini + j)
        es_ultimo = j == n_bars - 1
        cell = cells[(rng.randrange(len(cells)) if j else _celula_inicial(rng, cells))]
        open_p = sx.get("open_ending_prob", 0.3) if es_ultimo else 0.0
        trozo, prev = _cell_notes(sc, bar_ini + j, cell, rng, movement, register, bh, prev,
                                  bh_next if es_ultimo else None, open_p,
                                  sx.get("approach_prob", 0.4),
                                  sx.get("tension_tone_prob", 0.3) if not es_ultimo else 0.15)
        notes.extend(trozo)
        contour.append(tuple(n["pitch"] for n in trozo))
    notes = _limpiar(notes, lo, hi)
    meta = {"cells": n_bars, "contour": contour, "pitches": [n["pitch"] for n in notes]}
    return notes, meta


def _celula_inicial(rng, cells):
    """Primera celda: preferencia por entrada en downbeat (identidad reconocible)."""
    fuertes = [i for i, c in enumerate(cells) if c[0][0] == 0.0]
    idx = rng.choice(fuertes) if fuertes and rng.random() < 0.75 else rng.randrange(len(cells))
    return idx


def _limpiar(notes, lo, hi):
    """Reglas duras: registro, repetición triple, solapes dentro de la frase."""
    out = []
    prev_p = None
    repes = 0
    for n in sorted(notes, key=lambda x: (x["bar"], x["beat"])):
        p = max(lo, min(hi, int(n["pitch"])))
        if prev_p is not None and p == prev_p:
            repes += 1
            if repes >= 2:                     # 3ª repetición: paso obligatorio
                p = p + (1 if p + 1 <= hi else -1)
                repes = 0
        else:
            repes = 0
        n = dict(n, pitch=p)
        out.append(n)
        prev_p = p
    return out


# ---------------------------------------------------------------------------
# Desarrollo (transformaciones del material previo)
# ---------------------------------------------------------------------------
TRANSFORMS = ("reharmonize", "fragment", "displace", "invert", "vary_ending", "register_shift")


def reharmonize(notes, sc_dest, bar_ini, register):
    """Re-armonización: mismo contorno rítmico/interválico anclado a la NUEVA
    armonía (equivalente melódico de la transposición con re-target armónico)."""
    lo, hi = register
    if not notes:
        return []
    base = notes[0]["pitch"]
    bh0 = sc_dest.harmony_at_bar(bar_ini + notes[0]["bar"])
    nuevo_base = None
    for pc in bh0.chord_tone_pcs:
        cand = sc_dest.nearest_pitch_with_pc(pc, base, lo, hi)
        if cand is not None and (nuevo_base is None or abs(cand - base) < abs(nuevo_base - base)):
            nuevo_base = cand
    nuevo_base = nuevo_base if nuevo_base is not None else max(lo, min(hi, base))
    delta = nuevo_base - base
    out = []
    for n in notes:
        out.append(dict(n, bar=n["bar"] - notes[0]["bar"] + bar_ini,
                        pitch=max(lo, min(hi, n["pitch"] + delta))))
    return _limpiar(out, lo, hi)


def fragment(notes, n_frag, bar_ini, sc_dest=None):
    """Fragmentación: primeras ``n_frag`` notas; el resto se calla (silencio con
    función). Se reancora al compás ``bar_ini``."""
    sel = notes[:max(2, n_frag)]
    out = []
    for n in sel:
        out.append(dict(n, bar=n["bar"] - notes[0]["bar"] + bar_ini))
    return out


def displace(notes, delta_beat=0.5, bb=4.0):
    """Desplazamiento rítmico: todos los onsets +delta (sin cruzar el compás)."""
    out = []
    for n in notes:
        b, bt = n["bar"], n["beat"] + delta_beat
        if bt >= bb:
            b, bt = b + 1, bt - bb
        out.append(dict(n, bar=b, beat=round(bt, 3)))
    return out


def invert(notes, register):
    """Inversión interválica alrededor de la primera nota."""
    lo, hi = register
    if not notes:
        return []
    eje = notes[0]["pitch"]
    out = []
    for n in notes:
        out.append(dict(n, pitch=max(lo, min(hi, eje - (n["pitch"] - eje)))))
    return _limpiar(out, lo, hi)


def vary_ending(notes, sc_dest, last_bar, register, open_prob, rng):
    """Alteración del final: resolución a guía del acorde destino o nota abierta."""
    if not notes:
        return []
    lo, hi = register
    out = [dict(n) for n in notes]
    ultima = out[-1]
    bh_next = sc_dest.next_harmony(last_bar)
    if rng.random() < open_prob:
        tonos = bh_next.chord_tone_pcs
        pc = tonos[-1] if tonos else (bh_next.chord.root + 7) % 12
        cand = sc_dest.nearest_pitch_with_pc(pc, ultima["pitch"] + rng.choice((-2, 2, 3)), lo, hi)
    else:
        guias = bh_next.guide_pcs
        pc = guias[rng.randrange(len(guias))] if guias else bh_next.chord.root
        cand = sc_dest.nearest_pitch_with_pc(pc, ultima["pitch"], lo, hi)
    if cand is not None:
        ultima["pitch"] = int(cand)
        ultima["tension"] = False
    return _limpiar(out, lo, hi)


def register_shift(notes, semitones, register):
    lo, hi = register
    out = [dict(n, pitch=max(lo, min(hi, n["pitch"] + semitones))) for n in notes]
    return _limpiar(out, lo, hi)


def transformar(notes, transform, sc_dest, bar_ini, rng, profile, register, bb=4.0):
    """Aplica UNA transformación y devuelve (notas, nombre). Nunca inventa desde
    cero: todas parten del material recibido."""
    sx = profile.sax
    if not notes:
        return [], "empty"
    if transform == "reharmonize":
        return reharmonize(notes, sc_dest, bar_ini, register), "reharmonize"
    if transform == "fragment":
        return fragment(notes, max(2, (len(notes) + 1) // 2), bar_ini), "fragment"
    if transform == "displace":
        return displace(notes, rng.choice((0.5, -0.5)), bb), "displace"
    if transform == "invert":
        return invert(notes, register), "invert"
    if transform == "vary_ending":
        last_bar = max(n["bar"] for n in notes)
        return vary_ending(notes, sc_dest, last_bar, register,
                           sx.get("open_ending_prob", 0.35), rng), "vary_ending"
    if transform == "register_shift":
        return register_shift(notes, rng.choice((-5, 5, 7, -7)), register), "register_shift"
    raise ValueError("transform desconocida: %r" % (transform,))
