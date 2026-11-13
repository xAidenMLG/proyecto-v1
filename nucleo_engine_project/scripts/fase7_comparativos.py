#!/usr/bin/env python3
"""FASE 7 — Comparativos de la biblioteca de familiaridad armónica.

Para CADA composición de la matriz de generalización FASE 6 genera:

  A_original_<perfil>.mid      producción full SIN biblioteca (regresión: debe
                               ser byte-idéntico al full.mid de FASE 6)
  B_familiar_<kw>.mid          misma producción + biblioteca, variación NONE
                               (la progresión familiar pura, tal cual)
  C_transformado_<kw>.mid      misma progresión y seed, variación RICH
                               (la variación transformada)

B y C comparten keyword y seed de biblioteca → MISMA progresión elegida; la
diferencia audible es solo el nivel de transformación. Cada familia musical
se prueba en una tonalidad distinta. Además, dos D_familiarity_auto para
demostrar la selección automática.

Salida: output/fase7_comparativos/<composicion>/ (+ RESUMEN.md + hashes.json)
Escritura SOLO en output/fase7_comparativos (los dorados no se tocan).
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
from forge import validate as V  # noqa: E402

# composición → (keyword, seed_biblioteca, descripción musical)
PLAN = {
    "nocturno_terminal":       ("dark_cinematic", 777, "Dm · baseline de FASE 5/6"),
    "medianoche_puerto_nuevo": ("dream_pop",       311, "F#m · groove lento, 78 BPM"),
    "casa_de_espejos":         ("soulful",         555, "Cm · sax fuera de focus"),
    "habitacion_314":          ("melancholic",     410, "Gm · forma larga, tensión alta"),
    "calles_de_neon":          ("familiar_pop",    902, "Am · material escrito (respetado)"),
}
EXTRAS_AUTO = ["nocturno_terminal", "casa_de_espejos"]


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    base_out = ROOT / "output" / "fase7_comparativos"
    base_out.mkdir(parents=True, exist_ok=True)
    filas, hashes = [], {}

    for comp, (kw, hseed, desc) in PLAN.items():
        out_dir = base_out / comp
        out_dir.mkdir(parents=True, exist_ok=True)
        doc = json.loads((ROOT / "output" / "generalizacion_fase6" / comp /
                          "doc.json").read_text(encoding="utf-8"))
        proj = compilador.compilar(copy.deepcopy(doc))["proyecto"]
        seed_doc = int((doc.get("global") or {}).get("seed", 0) or 0)
        golden_full = ROOT / "output" / "generalizacion_fase6" / comp / "full.mid"
        hash_golden = _sha(golden_full.read_bytes())

        runs = [
            ("A_original", {"production": "full", "seed": seed_doc}, None),
            ("B_familiar_%s" % kw,
             {"production": "full", "seed": seed_doc,
              "harmony": {"keyword": kw, "seed": hseed, "variacion": "none"}}, kw),
            ("C_transformado_%s" % kw,
             {"production": "full", "seed": seed_doc,
              "harmony": {"keyword": kw, "seed": hseed, "variacion": "rich"}}, kw),
        ]
        for nombre, cfg, kw_run in runs:
            res = je.render.generate(copy.deepcopy(proj), cfg)
            val = V.validate(res)
            sha = _sha(res.midi)
            fallos = [c["id"] for c in val["compliance"] if c["status"] == "fail"]
            (out_dir / ("%s.mid" % nombre)).write_bytes(res.midi)
            ev_har = (getattr(res, "evidence", None) or {}).get("harmony")
            regen = ("python3 -m jazz_engine output/generalizacion_fase6/%s/doc.json "
                     "--dark-director --production full --seed %d -o regen.mid"
                     % (comp, seed_doc))
            if kw_run:
                regen += (" --harmony %s --harmony-seed %d --harmony-variacion %s"
                          % (kw, hseed, cfg["harmony"]["variacion"]))
            evid = {
                "composicion": comp, "run": nombre, "keyword": kw_run,
                "seed_doc": seed_doc, "seed_harmony": hseed,
                "sha256_midi": sha, "regeneracion": regen,
                "compliance_fails": fallos,
                "duracion_s": round(res.ctx.total_beats * 60.0 / res.ctx.bpm, 1),
            }
            if ev_har is not None:
                evid["armonia"] = {
                    "eleccion_por_seccion": {
                        sid: {"entrada": s["entrada"], "simbolos": s["simbolos"]}
                        for sid, s in ev_har["secciones"].items()},
                    "respetadas_material": ev_har["respetadas_material"],
                    "resumen": ev_har["resumen"],
                }
            (out_dir / ("evidencia_%s.json" % nombre)).write_text(
                json.dumps(evid, ensure_ascii=False, indent=2), encoding="utf-8")
            hashes["%s/%s" % (comp, nombre)] = sha
            nota = ""
            if nombre == "A_original":
                nota = ("== FASE 6 OK" if sha == hash_golden
                        else "!! DIFIERE DEL GOLDEN FASE 6")
            filas.append((comp, nombre, kw_run, seed_doc, sha, nota, fallos))
            print("  %-24s %-26s %s %s" % (comp, nombre, sha[:16],
                                           nota or ("fallos=%s" % (fallos or "ninguno"))))

        # D_familiarity_auto (selección automática por contexto)
        if comp in EXTRAS_AUTO:
            nombre = "D_familiarity_auto"
            cfg = {"production": "full", "seed": seed_doc,
                   "harmony": {"keyword": "familiarity_auto", "seed": hseed + 1,
                               "variacion": "medium"}}
            res = je.render.generate(copy.deepcopy(proj), cfg)
            val = V.validate(res)
            sha = _sha(res.midi)
            fallos = [c["id"] for c in val["compliance"] if c["status"] == "fail"]
            (out_dir / ("%s.mid" % nombre)).write_bytes(res.midi)
            ev_har = (getattr(res, "evidence", None) or {}).get("harmony")
            evid = {
                "composicion": comp, "run": nombre, "keyword": "familiarity_auto",
                "seed_doc": seed_doc, "seed_harmony": hseed + 1,
                "sha256_midi": sha, "compliance_fails": fallos,
                "armonia": {
                    "eleccion_por_seccion": {
                        sid: {"entrada": s["entrada"], "simbolos": s["simbolos"]}
                        for sid, s in (ev_har["secciones"] or {}).items()},
                    "resumen": ev_har["resumen"]},
            }
            (out_dir / ("evidencia_%s.json" % nombre)).write_text(
                json.dumps(evid, ensure_ascii=False, indent=2), encoding="utf-8")
            hashes["%s/%s" % (comp, nombre)] = sha
            filas.append((comp, nombre, "familiarity_auto", seed_doc, sha, "", fallos))
            print("  %-24s %-26s %s" % (comp, nombre, sha[:16]))

    (base_out / "hashes.json").write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8")
    lineas = ["# FASE 7 — Comparativos de la biblioteca de familiaridad armónica",
              "",
              "A = producción full SIN biblioteca (regresión FASE 6) · "
              "B = progresión familiar pura (variación none) · "
              "C = la MISMA progresión transformada (variación rich, misma seed).",
              "", "| Composición | Run | Keyword | Seed doc | SHA256(16) | Nota | Fallos |",
              "|---|---|---|---|---|---|---|"]
    for comp, nombre, kw, seed_doc, sha, nota, fallos in filas:
        lineas.append("| %s | %s | %s | %d | %s | %s | %s |"
                      % (comp, nombre, kw or "—", seed_doc, sha[:16],
                         nota or "—", fallos or "ninguno"))
    lineas += ["", "Regeneración exacta: comando dentro de cada evidencia_*.json.",
               "Escucha (Windows): `fluidsynth -ni soundfont.sf2 ARCHIVO.mid -F out.wav -r 44100`",
               "", "La validación musical corresponde al usuario (no se declara éxito "
               "musical por métricas ni hashes)."]
    (base_out / "RESUMEN.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("OK: %s (%d runs)" % (base_out, len(filas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
