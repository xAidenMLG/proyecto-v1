"""CLI de jazz_engine — pipeline mejorado JSON-first.

Uso (desde la raíz del proyecto):
  # proyecto midi-forge/1 ya compilado:
  python3 -m jazz_engine proyecto.json --config config.json -o salida.mid

  # documento dark-director/1 (compila + enriquece + genera):
  python3 -m jazz_engine doc.json --dark-director --config config.json -o salida.mid

  # perfil de producción (FASE 6): preset reproducible de los motores
  python3 -m jazz_engine doc.json --dark-director --production full --seed 2026 -o salida.mid
  # perfiles: original | sax | sax_rhodes | drums | sax_vibes | full | atmospheric

  # biblioteca de familiaridad armónica (FASE 7): keyword o ID concreto
  python3 -m jazz_engine doc.json --dark-director --production full --seed 2026 \
      --harmony dark_cinematic --harmony-variacion medium -o salida.mid
  python3 -m jazz_engine doc.json --dark-director --harmony-id CINE01 -o salida.mid

Con --evidence escribe un JSON con plan, métricas y evidencia de los motores.
Determinista: mismo input + misma config → mismo MIDI byte a byte.
"""
import argparse
import copy
import json
import sys


def _compilar_dark_director(doc):
    import dark_director.compilador as compilador
    return compilador.compilar(doc)["proyecto"]


def main(argv=None):
    from . import production
    ap = argparse.ArgumentParser(prog="jazz_engine")
    ap.add_argument("input", help="JSON: proyecto midi-forge/1 o documento dark-director/1")
    ap.add_argument("--dark-director", action="store_true",
                    help="la entrada es un documento dark-director/1 (se compila primero)")
    ap.add_argument("--config", help="config JSON de motores (opcional)")
    ap.add_argument("--production", choices=production.nombres(), metavar="PERFIL",
                    help="perfil de producción (preset reproducible); la --config "
                         "explícita gana sobre el preset si hay solape")
    ap.add_argument("--seed", type=int, help="semilla de los motores (si no, la de --config)")
    ap.add_argument("--harmony", metavar="KEYWORD",
                    help="FASE 7: keyword de la biblioteca de familiaridad "
                         "(familiar_pop | melancholic | nostalgic | dark_cinematic | "
                         "dream_pop | alternative | soulful | emotional_resolution | "
                         "tension_release | familiarity_auto)")
    ap.add_argument("--harmony-id", metavar="ID",
                    help="FASE 7: progresión concreta de la biblioteca (p.ej. CINE01)")
    ap.add_argument("--harmony-variacion", choices=("none", "subtle", "medium", "rich"),
                    help="FASE 7: nivel de transformación (default: subtle)")
    ap.add_argument("--harmony-seed", type=int,
                    help="FASE 7: semilla propia de la biblioteca (si no, la de --seed)")
    ap.add_argument("-o", "--output", required=True, help="MIDI de salida")
    ap.add_argument("--evidence", help="evidencia JSON de salida (opcional)")
    ap.add_argument("--project-out", help="proyecto enriquecido JSON de salida (opcional)")
    args = ap.parse_args(argv)

    with open(args.input, encoding="utf-8") as fh:
        data = json.load(fh)
    if args.dark_director:
        proyecto = _compilar_dark_director(copy.deepcopy(data))
    else:
        proyecto = data
    config = None
    if args.config:
        with open(args.config, encoding="utf-8") as fh:
            config = json.load(fh)
    if args.production is not None:
        config = dict(config or {})
        config["production"] = args.production
    if args.seed is not None:
        config = dict(config or {})
        config["seed"] = args.seed
    har = {}
    if args.harmony:
        har["keyword"] = args.harmony
    if args.harmony_id:
        har["id"] = args.harmony_id
    if args.harmony_variacion:
        har["variacion"] = args.harmony_variacion
    if args.harmony_seed is not None:
        har["seed"] = args.harmony_seed
    if har:
        if "harmony" in (config or {}):
            raise SystemExit("--harmony* entra en conflicto con config['harmony'] "
                             "del --config; usa solo uno")
        config = dict(config or {})
        config["harmony"] = har

    from . import render
    if not config:
        res = render.generate(proyecto, None)
    else:
        res = render.generate(proyecto, config)
    with open(args.output, "wb") as fh:
        fh.write(res.midi)

    if args.evidence:
        from . import render as R
        ev = getattr(res, "evidence", None) or {}
        payload = {"evidence": ev, "metrics": R.metrics(res) if config else None,
                   "config": config}
        with open(args.evidence, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
    if args.project_out:
        proj2 = res.ctx.project
        with open(args.project_out, "w", encoding="utf-8") as fh:
            json.dump(proj2, fh, ensure_ascii=False, indent=2)
    print("OK: %s" % args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
