#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnóstico: volcar el bloque LEAD del outro tal como lo ejecutó el motor.
SOLO LECTURA del pipeline — no modifica nada."""
import json
import sys

sys.path.insert(0, "/home/z/my-project/nucleo_engine_project")
from dark_director import compilador  # noqa: E402
import jazz_engine as je  # noqa: E402
from jazz_engine.render import enhance_mod as EN, coordinator as CO  # noqa: E402
from forge import adapter as A  # noqa: E402

doc = json.load(open("/home/z/my-project/nucleo_engine_project/sax_register_test.json"))
r = compilador.compilar(json.loads(json.dumps(doc)))
proj = r["proyecto"]
cfg = CO.normalize_config({"production": "sax", "seed": 7351})
proj2, plan, ev = EN.enhance(json.loads(json.dumps(proj)), cfg)
proj2, _rep = A.normalize(proj2, None)

# pistas y roles
print("TRACKS:")
lead = None
for t in proj2.get("tracks", []):
    print("  role=%-6s id=%-12s prog=%s" % (t.get("role"), t.get("id"), t.get("program")))
    if t.get("role") == "lead":
        lead = t

print("\nSECCIONES:")
for s in proj2.get("sections", []):
    print("  id=%-10s kind=%-10s bars=%s" % (s.get("id"), s.get("kind"), s.get("bars")))

# frases lead tras enhance+normalize
lead_phr = ((proj2.get("lead") or {}).get("phrases") or {})
print("\nFRASES LEAD en proyecto normalizado:", {k: len(v) for k, v in lead_phr.items()})

# bloques por sección del track lead
print("\nBLOQUES LEAD por sección:")
for b in (lead or {}).get("blocks", []) or []:
    print("  ", json.dumps(b, ensure_ascii=False))

# block por defecto / estilo
print("\nlead.style global:", (lead or {}).get("style"))
print("lead.range:", (lead or {}).get("range"))

# ¿qué generó gen_lead en el outro? replicar llamada
from forge import engine as E, styles as S, theory as T  # noqa: E402
import math  # noqa: E402

print("\nLEAD_BLOCKS_STYLE_SCHEMA intro/verse/outro:", json.dumps(
    {k: S.STYLE_SCHEMA['lead'][k].get('fields') for k in ('hold',)}, ensure_ascii=False))
