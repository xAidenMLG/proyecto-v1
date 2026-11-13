#!/usr/bin/env python3
"""FASE 5 — Generación del material comparativo (misión §15).

8 escenarios sobre la MISMA composición (mismo doc, seed, tempo, estructura):
  01_original               — sin motores (control base; path ORIGINAL)
  02_sax                    — sax engine
  03_sax_rhodes             — sax + Rhodes (control sin Rhodes = 02)
  04_drums                  — drums engine
  05_sax_rhodes_drums
  06_sax_vibes              — sax + vibráfono (control = 02: el eco del vibes
                              necesita huecos del sax; con el lead generativo
                              denso del ORIGINAL el vibes no tiene dónde)
  07_full                   — todos los motores
  08_variation_atmospheric  — todos + variación controlada «atmospheric»

Salida: output/fase5_comparativos/ con doc.json, config_<esc>.json,
<esc>.mid, evidencia_<esc>.json, proyecto_<esc>.json y RESUMEN.md.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dark_director import compilador, forge_link  # noqa: E402
import jazz_engine as je  # noqa: E402

forge_link.import_forge()
from forge import adapter as A  # noqa: E402
from forge import engine as E  # noqa: E402
from forge import validate as V  # noqa: E402

OUT = ROOT / 'output' / 'fase5_comparativos'

DOC = {
    "schema": "dark-director/1",
    "meta": {
        "title": "Nocturno Terminal",
        "notes": "FASE 5 — composición de comparación dark_triphop (identidad activa única). "
                 "Mismo doc/seed/tempo/estructura para los 8 escenarios.",
    },
    "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
    "global": {"bpm": 86, "seed": 2026},
    "harmony": {
        "key": "D minor",
        "language": "pop_dream_pop",
        "harmonic_rhythm_bars": 1,
        "progressions": {
            "verse": ["Dm9", "Bbmaj7", "Fmaj9", "C7sus4"],
            "chorus": ["Bbmaj9", "Fmaj9", "Gm9", "A7sus4"],
        },
    },
    "structure": [
        {"id": "intro", "type": "intro", "bars": 4, "energy": 0.25, "tension": 0.2,
         "density": 0.25, "focus": ["rhodes", "pad"], "drums": "air"},
        {"id": "verse_1", "type": "verse", "bars": 8, "energy": 0.45, "tension": 0.35,
         "density": 0.45, "focus": ["sax_tenor", "drums"], "drums": "groove"},
        {"id": "pre_1", "type": "pre_chorus", "bars": 4, "energy": 0.6, "tension": 0.55,
         "density": 0.55, "focus": ["pad", "vibraphone"], "drums": "light"},
        {"id": "chorus_1", "type": "chorus", "bars": 8, "energy": 0.8, "tension": 0.5,
         "density": 0.65, "focus": ["sax_tenor", "drums", "bass"], "drums": "heavy"},
        {"id": "bridge_1", "type": "bridge", "bars": 4, "energy": 0.5, "tension": 0.6,
         "density": 0.55, "focus": ["rhodes"], "drums": "light"},
        {"id": "break_1", "type": "break", "bars": 4, "energy": 0.35, "tension": 0.6,
         "density": 0.3, "focus": ["vibraphone"], "drums": "light",
         "active": ["vibraphone", "rhodes", "pad"]},
        {"id": "verse_2", "type": "verse", "bars": 8, "energy": 0.5, "tension": 0.4,
         "density": 0.5, "focus": ["sax_tenor"], "drums": "groove"},
        {"id": "chorus_2", "type": "chorus", "bars": 8, "energy": 0.85, "tension": 0.55,
         "density": 0.7, "focus": ["sax_tenor", "drums"], "drums": "heavy", "final": True},
        {"id": "outro", "type": "outro", "bars": 4, "energy": 0.2, "tension": 0.15,
         "density": 0.2, "focus": ["rhodes"], "drums": "air"},
    ],
    "ending": {"fade_out": {"enabled": True, "bars": 3}},
}

SEED = 2026
ENGINES_ALL = {"sax": True, "rhodes": True, "drums": True, "vibes": True}

ESCENARIOS = [
    ("01_original", None),
    ("02_sax", {"engines": {"sax": True, "rhodes": False, "drums": False, "vibes": False}}),
    ("03_sax_rhodes", {"engines": {"sax": True, "rhodes": True, "drums": False, "vibes": False}}),
    ("04_drums", {"engines": {"sax": False, "rhodes": False, "drums": True, "vibes": False}}),
    ("05_sax_rhodes_drums", {"engines": {"sax": True, "rhodes": True, "drums": True, "vibes": False}}),
    ("06_sax_vibes", {"engines": {"sax": True, "rhodes": False, "drums": False, "vibes": True}}),
    ("07_full", {"engines": dict(ENGINES_ALL)}),
    ("08_variation_atmospheric", {"engines": dict(ENGINES_ALL), "variation": "atmospheric"}),
]


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'doc.json').write_text(json.dumps(DOC, ensure_ascii=False, indent=2), encoding='utf-8')
    resumen = []
    for nombre, config in ESCENARIOS:
        r = compilador.compilar(copy.deepcopy(DOC))
        proj = r['proyecto']
        avisos = r['avisos']
        if config is None:
            # path ORIGINAL: normalize + generate (sin jazz_engine)
            pn, rep = A.normalize(copy.deepcopy(proj), None)
            res = E.generate(pn)
            evid = {"path": "original (sin jazz_engine)", "engines": "none"}
            plan = None
        else:
            cfg = dict(config, seed=SEED)
            res = je.render.generate(copy.deepcopy(proj), cfg)
            plan = getattr(res, 'plan', None)
            evid = getattr(res, 'evidence', {})
            pn = res.ctx.project
            (OUT / ('config_%s.json' % nombre)).write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
        val = V.validate(res)
        mid_path = OUT / ('%s.mid' % nombre)
        mid_path.write_bytes(res.midi)
        sha = _sha(res.midi)
        m = je.render.metrics(res)
        sax_activas = m.get('sax_frases_activas', []) if plan else []
        evidencia = {
            "escenario": nombre,
            "sha256_midi": sha,
            "bytes": len(res.midi),
            "bpm": res.ctx.bpm,
            "compases": res.ctx.total_bars,
            "duracion_segundos": m['duration_seconds'],
            "seed": SEED,
            "motores": (config or {}).get('engines', "ninguno (ORIGINAL)"),
            "variacion": (config or {}).get('variation', 'n/a'),
            "notas_por_pista": m['notas_por_pista'],
            "frases_sax": [{"seccion": f['seccion'], "accion": f['accion'],
                            "transform": f.get('transform'), "notas": f['notas']}
                           for f in sax_activas],
            "frases_sax_total": len(sax_activas),
            "rhodes_melodico_por_seccion": m.get('rhodes_melodico_por_seccion'),
            "vibes_eco_por_seccion": m.get('vibes_eco_por_seccion'),
            "densidad_notas_por_compas": {
                tid: round(n / float(res.ctx.total_bars), 2)
                for tid, n in m['notas_por_pista'].items()},
            "compliance_fails": [c['id'] for c in val['compliance'] if c['status'] == 'fail'],
            "compliance_warns": [c['id'] for c in val['compliance'] if c['status'] == 'warn'],
            "choques_semitono": val['semitone_clashes_unintended'],
            "avisos_compilador": avisos,
            "evidencia_motores": evid,
        }
        (OUT / ('evidencia_%s.json' % nombre)).write_text(
            json.dumps(evidencia, ensure_ascii=False, indent=2), encoding='utf-8')
        # proyecto compilado de referencia (para reproducir sin DMD)
        (OUT / ('proyecto_%s.json' % nombre)).write_text(
            json.dumps(pn, ensure_ascii=False, indent=2), encoding='utf-8')
        resumen.append({
            "escenario": nombre, "sha256": sha[:16] + '…',
            "duracion_s": m['duration_seconds'],
            "sax": m['notas_por_pista'].get('sax_tenor', 0),
            "rhodes": m['notas_por_pista'].get('rhodes', 0),
            "vibes": m['notas_por_pista'].get('vibraphone', 0),
            "drums": m['notas_por_pista'].get('drums', 0),
            "bass": m['notas_por_pista'].get('bass', 0),
            "frases_sax": len(sax_activas),
            "fails": evidencia['compliance_fails'],
        })
        print("%-26s %s  %5.1fs  sax=%-3d rhodes=%-3d vibes=%-3d drums=%-4d fails=%s"
              % (nombre, sha[:12], m['duration_seconds'],
                 m['notas_por_pista'].get('sax_tenor', 0),
                 m['notas_por_pista'].get('rhodes', 0),
                 m['notas_por_pista'].get('vibraphone', 0),
                 m['notas_por_pista'].get('drums', 0),
                 evidencia['compliance_fails'] or 'ninguno'))
    lineas = ["# FASE 5 — Material comparativo (Nocturno Terminal, seed %d, 86 BPM, 52 compases)" % SEED,
              "",
              "| Escenario | SHA256 (16) | Dur s | sax | rhodes | vibes | drums | bass | frases sax | fails |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in resumen:
        lineas.append("| %s | %s | %.1f | %d | %d | %d | %d | %d | %d | %s |"
                      % (r['escenario'], r['sha256'], r['duracion_s'], r['sax'], r['rhodes'],
                         r['vibes'], r['drums'], r['bass'], r['frases_sax'],
                         r['fails'] or 'ninguno'))
    (OUT / 'RESUMEN.md').write_text('\n'.join(lineas) + '\n', encoding='utf-8')
    print("\nRESUMEN.md + evidencias en", OUT)


if __name__ == '__main__':
    main()
