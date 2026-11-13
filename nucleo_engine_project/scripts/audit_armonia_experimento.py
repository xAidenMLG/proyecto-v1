#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Experimento de auditoría armónica — SOLO LECTURA, 100% en memoria.
No escribe nada en el repo ni en output/. Responde a las preguntas 4, 5, 6, 7:
- Doc SIN progressions y SIN chords → ¿qué acordes produce? (ruta nativa receta_n1)
- Doc CON progressions → precedencia
- Doc CON chords por sección → precedencia máxima
- FASE 7: ¿se activa sin petición explícita? ¿y con ella, qué respeta?
"""
import copy
import json
import sys

sys.path.insert(0, "/home/z/my-project/nucleo_engine_project")
from dark_director import compilador  # noqa: E402
from jazz_engine.render import enhance_mod as EN, coordinator as CO  # noqa: E402

BASE = {
    "schema": "dark-director/1",
    "meta": {"title": "Audit Native", "notes": "auditoria"},
    "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
    "global": {"bpm": 84, "seed": 100},
    "harmony": {"key": "A minor", "language": "hybrid", "harmonic_rhythm_bars": 1},
    "structure": [
        {"id": "intro", "type": "intro", "bars": 4},
        {"id": "v1", "type": "verse", "bars": 8, "energy": 0.45},
        {"id": "c1", "type": "chorus", "bars": 8, "energy": 0.8},
        {"id": "out", "type": "outro", "bars": 4},
    ],
}


def compila_y_chords(doc, etiqueta):
    r = compilador.compilar(copy.deepcopy(doc))
    proj = r["proyecto"]
    print(f"\n### {etiqueta}")
    for s in proj["sections"]:
        print(f"  {s['id']:6s} ({s['kind']:9s}) chords = {s['chords']}  "
              f"chord_bars={s['chord_bars']}")
    return proj


# --- A: NATIVE (sin progressions, sin chords) ---------------------------------
proj_a = compila_y_chords(BASE, "A — NATIVE: sin progressions ni chords")

# comparar contra la receta esperada (dark_triphop.PROGRESIONES.hybrid)
from dark_director.identities import dark_triphop as RT  # noqa: E402
from dark_director import contract  # noqa: E402
tonic = 9  # A
esperado_v = [contract_or_name(o, c) if False else None for o, c in []]
NOMBRES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
for t in ("intro", "verse", "chorus", "outro"):
    esp = [NOMBRES[(tonic + o) % 12] + c for o, c in RT.PROGRESIONES["hybrid"][t]]
    sid = {"intro": "intro", "verse": "v1", "chorus": "c1", "outro": "out"}[t]
    real = next(s["chords"] for s in proj_a["sections"] if s["id"] == sid)
    print(f"  receta nativa esperada {t}: {esp}  | coincide: {real == esp}")

# --- B: GUIDED (progressions por type) ----------------------------------------
doc_b = copy.deepcopy(BASE)
doc_b["harmony"]["progressions"] = {
    "verse": ["Am9", "Em7", "Fmaj7", "G7sus4"],
}
proj_b = compila_y_chords(doc_b, "B — GUIDED: harmony.progressions['verse']")
assert proj_b["sections"][1]["chords"] == ["Am9", "Em7", "Fmaj7", "G7sus4"], "precedencia B"
print("  => verse usa la progresión declarada; intro/chorus/outro siguen receta nativa")

# --- C: chords por sección (precedencia máxima) --------------------------------
doc_c = copy.deepcopy(doc_b)
doc_c["structure"][1]["chords"] = ["Dm9", "G13", "Cmaj9"]
proj_c = compila_y_chords(doc_c, "C — chords por sección + progressions presentes")
assert proj_c["sections"][1]["chords"] == ["Dm9", "G13", "Cmaj9"], "precedencia C"
print("  => structure[].chords GANA sobre harmony.progressions")

# --- D: FASE 7 sin activación explícita ---------------------------------------
cfg = CO.normalize_config({"production": "sax", "seed": 100})
proj_d, plan, ev = EN.enhance(copy.deepcopy(proj_a), cfg)
print("\n### D — FASE 7 sin activación: ¿aparece en evidencia/plan?")
print("  ev keys:", sorted(ev.keys()))
print("  'harmony' en evidencia:", "harmony" in ev)
print("  chords v1 tras enhance:", proj_d["sections"][1]["chords"])

# --- E: FASE 7 con activación explícita (keyword) — sobre doc sin material ----
from jazz_engine.render import harmony_mod  # noqa: E402
act = harmony_mod.normalizar_activacion({"keyword": "dark_cinematic"}, seed_base=100)
proj_e, ev_har = harmony_mod.aplicar(copy.deepcopy(proj_a), act)
print("\n### E — FASE 7 activada explícitamente (keyword dark_cinematic)")
print("  resumen:", ev_har["resumen"])
for sid, info in ev_har["secciones"].items():
    print(f"  {sid:6s} <- {info['entrada']} ({info['nombre']}) {info['simbolos']}")
print("  chords v1 tras F7:", next(s["chords"] for s in proj_e["sections"] if s["id"] == "v1"))

print("\nTODO EN MEMORIA — nada fue escrito en el repo.")
