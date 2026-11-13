#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis diagnóstico de alturas reales del sax por sección.
Entrada : output/experimentos/sax_register_test/sax_register_test.mid
Salida  : analisis_sax.json + ANALISIS_ALTURAS_SAX.md en la misma carpeta.
NO modifica el motor ni el MIDI: solo lectura.
"""
import json
import sys
from collections import defaultdict

import mido

MIDI_DIR = "output/experimentos/sax_register_test"
MIDI_PATH = f"{MIDI_DIR}/sax_register_test.mid"

# Secciones según la estructura del documento (índices de compás 0-based)
SECCIONES = [
    ("intro",    0,  4),
    ("verse_1",  4,  12),
    ("pre_1",    12, 16),
    ("chorus_1", 16, 24),
    ("verse_2",  24, 28),
    ("chorus_2", 28, 32),
    ("outro",    32, 36),
]

# Frases especificadas en el JSON (bar/beat relativos a la sección, pitch, dur, vel)
FRASES_SPEC = {
    "verse_1": [(0, 0.5, 67, 1.5, 68), (1, 0.0, 69, 1.5, 70), (2, 1.0, 72, 1.0, 72),
                (3, 0.5, 71, 1.5, 68), (5, 0.0, 74, 2.0, 74), (6, 1.0, 72, 1.5, 70)],
    "pre_1":   [(0, 0.0, 72, 1.0, 72), (1, 0.5, 74, 1.0, 74), (2, 0.0, 76, 1.5, 78),
                (3, 1.0, 77, 1.5, 80)],
    "chorus_1": [(0, 0.0, 76, 1.0, 82), (0, 1.5, 79, 1.0, 84), (1, 0.0, 81, 1.5, 86),
                 (2, 0.5, 79, 1.0, 80), (3, 0.0, 77, 2.0, 78), (5, 0.0, 81, 1.5, 86),
                 (6, 0.5, 79, 1.0, 82), (7, 0.0, 76, 2.0, 78)],
    "verse_2": [(0, 0.5, 69, 1.5, 68), (1, 0.0, 72, 1.5, 72), (2, 0.5, 74, 1.5, 74),
                (3, 0.0, 76, 2.0, 76)],
    "chorus_2": [(0, 0.0, 79, 1.0, 84), (1, 0.5, 81, 1.5, 88), (2, 0.0, 79, 1.0, 84),
                 (3, 0.5, 76, 2.0, 80)],
}

NOMBRES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

INICIO = {nombre: a for nombre, a, _ in SECCIONES}


def nota_nombre(p):
    return f"{NOMBRES[p % 12]}{p // 12 - 1}"


def carga_notas(mid):
    """Extrae notas por pista con tiempo absoluto en beats."""
    tpq = mid.ticks_per_beat
    pistas = []
    for i, trk in enumerate(mid.tracks):
        prog = None
        nombre = ""
        t = 0
        abiertas = {}
        notas = []
        for msg in trk:
            t += msg.time
            if msg.type == "track_name":
                nombre = msg.name
            elif msg.type == "program_change":
                prog = msg.program
            elif msg.type == "note_on" and msg.velocity > 0:
                abiertas.setdefault(msg.note, []).append((t, msg.velocity))
            elif msg.type in ("note_off", "note_on"):
                if msg.note in abiertas and abiertas[msg.note]:
                    ini, vel = abiertas[msg.note].pop(0)
                    notas.append({
                        "ini_beat": ini / tpq,
                        "fin_beat": t / tpq,
                        "dur_beats": (t - ini) / tpq,
                        "pitch": msg.note,
                        "vel": vel,
                    })
        if notas:
            notas.sort(key=lambda n: (n["ini_beat"], n["pitch"]))
            for n in notas:
                n["bar"] = int(n["ini_beat"] // 4)
                n["beat"] = round(n["ini_beat"] % 4, 3)
            pistas.append({
                "indice": i, "nombre": nombre, "programa": prog,
                "num_notas": len(notas), "notas": notas,
            })
    return pistas


def ubica_seccion(bar):
    for nombre, a, b in SECCIONES:
        if a <= bar < b:
            return nombre
    return "?"


def clasifica_match(p_spec, p_real):
    dif = p_real - p_spec
    if dif == 0:
        return "exacto", dif
    if dif % 12 == 0:
        return "octava", dif
    return "otra_altura", dif


def analiza_sax(pistas):
    sax = None
    for p in pistas:
        if "sax" in p["nombre"].lower() or p["programa"] in (65, 66):
            sax = p
            break
    if sax is None:
        return None
    por_seccion = defaultdict(list)
    for n in sax["notas"]:
        por_seccion[ubica_seccion(n["bar"])].append(n)
    return sax, por_seccion


def compara_seccion(sec, notas_reales):
    """Compara notas reales contra la frase especificada."""
    spec = FRASES_SPEC.get(sec)
    if spec is None:
        return {"seccion": sec, "con_frase_spec": False,
                "notas_reales": len(notas_reales)}
    inicio = INICIO[sec]
    especs = [{
        "bar_abs": inicio + b, "beat": bt, "pitch": p, "dur": d, "vel": v,
        "pitch_nombre": nota_nombre(p),
    } for (b, bt, p, d, v) in spec]
    usadas = set()
    filas = []
    for e in especs:
        objetivo = e["bar_abs"] * 4.0 + e["beat"]   # beat absoluto
        mejor = None
        for i, n in enumerate(notas_reales):
            if i in usadas:
                continue
            # tolerancia 0.12 beats: absorbe el jitter de humanización (±5
            # ticks ≈ 0.01 beat, 3σ ≈ 0.03) y el cruce de barra por jitter
            abs_real = n["ini_beat"]
            if abs(abs_real - objetivo) < 0.12:
                mejor = i
                break
        if mejor is None:
            filas.append({**e, "estado": "AUSENTE", "real": None})
        else:
            usadas.add(mejor)
            n = notas_reales[mejor]
            estado, dif = clasifica_match(e["pitch"], n["pitch"])
            filas.append({
                **e,
                "estado": estado,
                "real": {
                    "pitch": n["pitch"], "nombre": nota_nombre(n["pitch"]),
                    "bar": n["bar"], "beat": n["beat"],
                    "dur": round(n["dur_beats"], 3), "vel": n["vel"],
                    "dif_semitonos": dif,
                    "dif_vel": n["vel"] - e["vel"],
                    "dif_dur": round(n["dur_beats"] - e["dur"], 3),
                },
            })
    extras = [n for i, n in enumerate(notas_reales) if i not in usadas]
    return {
        "seccion": sec, "con_frase_spec": True,
        "n_spec": len(especs), "n_real": len(notas_reales),
        "comparacion": filas,
        "extras": [{
            "pitch": n["pitch"], "nombre": nota_nombre(n["pitch"]),
            "bar": n["bar"], "beat": n["beat"], "dur": round(n["dur_beats"], 3),
            "vel": n["vel"],
        } for n in extras],
    }


def resumen_alturas(notas):
    if not notas:
        return {"n": 0}
    ps = [n["pitch"] for n in notas]
    return {
        "n": len(notas),
        "min": min(ps), "max": max(ps),
        "min_nombre": nota_nombre(min(ps)), "max_nombre": nota_nombre(max(ps)),
        "media": round(sum(ps) / len(ps), 2),
        "mediana": sorted(ps)[len(ps) // 2],
        "ambito_semitonos": max(ps) - min(ps),
        "distribucion_registros": {
            "grave(<C4)": sum(1 for p in ps if p < 60),
            "medio(C4-B4)": sum(1 for p in ps if 60 <= p < 72),
            "agudo(C5-B5)": sum(1 for p in ps if 72 <= p < 84),
            "sobreagudo(>=C6)": sum(1 for p in ps if p >= 84),
        },
    }


def main():
    mid = mido.MidiFile(MIDI_PATH)
    tpq = mid.ticks_per_beat
    pistas = carga_notas(mid)

    print(f"TPQ={tpq}  pistas con notas={len(pistas)}")
    for p in pistas:
        ps = [n["pitch"] for n in p["notas"]]
        print(f"  [{p['indice']}] '{p['nombre']}' prog={p['programa']} "
              f"notas={p['num_notas']} rango={min(ps)}-{max(ps)} "
              f"({nota_nombre(min(ps))}-{nota_nombre(max(ps))})")

    res = analiza_sax(pistas)
    if res is None:
        print("ERROR: no se encontró pista de sax")
        sys.exit(1)
    sax, por_seccion = res
    print(f"\nPISTA SAX: '{sax['nombre']}' prog={sax['programa']} "
          f"notas={sax['num_notas']} (spec JSON: 26)")

    secciones_out = []
    for nombre, a, b in SECCIONES:
        notas = por_seccion.get(nombre, [])
        comp = compara_seccion(nombre, notas)
        comp["rango_compases"] = f"{a}-{b - 1}"
        comp["resumen"] = resumen_alturas(notas)
        secciones_out.append(comp)
        r = comp["resumen"]
        if r["n"]:
            print(f"  {nombre:9s} bars {a}-{b-1}: n={r['n']:2d} "
                  f"rango={r['min']}({r['min_nombre']})-{r['max']}({r['max_nombre']}) "
                  f"media={r['media']}")
        else:
            print(f"  {nombre:9s} bars {a}-{b-1}: SIN notas")

    # Orden temporal global
    print("\nSECUENCIA CRONOLÓGICA DE NOTAS SAX:")
    for n in sax["notas"]:
        print(f"  bar {n['bar']:2d} beat {n['beat']:.2f}  pitch {n['pitch']:3d} "
              f"({nota_nombre(n['pitch']):4s}) dur {n['dur_beats']:.2f} vel {n['vel']}")

    out = {
        "archivo": MIDI_PATH,
        "tpq": tpq,
        "pistas": [{k: p[k] for k in ("indice", "nombre", "programa", "num_notas")}
                   for p in pistas],
        "sax": {
            "pista": sax["nombre"], "programa_gm": sax["programa"],
            "total_notas": sax["num_notas"],
            "total_notas_spec_json": sum(len(v) for v in FRASES_SPEC.values()),
        },
        "secciones": secciones_out,
        "secuencia_cronologica": sax["notas"],
        "global": resumen_alturas(sax["notas"]),
    }
    with open(f"{MIDI_DIR}/analisis_sax.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nOK -> {MIDI_DIR}/analisis_sax.json")


if __name__ == "__main__":
    main()
