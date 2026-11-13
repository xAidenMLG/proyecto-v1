"""CLI de jazz_engine — pipeline mejorado JSON-first.

Uso (desde la raíz del proyecto):
  # proyecto midi-forge/1 ya compilado:
  python3 -m jazz_engine proyecto.json --config config.json -o salida.mid

  # documento dark-director/1 (compila + enriquece + genera):
  python3 -m jazz_engine doc.json --dark-director --config config.json -o salida.mid

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
    ap = argparse.ArgumentParser(prog="jazz_engine")
    ap.add_argument("input", help="JSON: proyecto midi-forge/1 o documento dark-director/1")
    ap.add_argument("--dark-director", action="store_true",
                    help="la entrada es un documento dark-director/1 (se compila primero)")
    ap.add_argument("--config", help="config JSON de motores (opcional)")
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
