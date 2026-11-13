"""CLI del ALBUM PRODUCTION SYSTEM — FASE 8.

Uso (desde la raíz del proyecto):

  Plan de producción (sin producir):
    python3 -m album plan albumes/<nombre>/album.json --out output/albumes/<nombre>

  Producción completa (planifica + produce + informe):
    python3 -m album producir albumes/<nombre>/album.json --out output/albumes/<nombre>

  Reanudar (salta las pistas ya producidas con la misma especificación):
    python3 -m album producir albumes/<nombre>/album.json --out output/albumes/<nombre>

  Regenerar pistas concretas (por id o índice "03"):
    python3 -m album producir albumes/<nombre>/album.json --out ... --regen 3,07_ritual

  Producir solo un bloque (no toca el resto del estado):
    python3 -m album producir albumes/<nombre>/album.json --out ... --solo 1,2,3

  Regenerarlo TODO (reproducibilidad completa):
    python3 -m album producir albumes/<nombre>/album.json --out ... --forzar

  Informe y estado:
    python3 -m album informe output/albumes/<nombre>
    python3 -m album estado output/albumes/<nombre>

Determinista: mismo album.json → mismo plan → mismos MIDIs byte a byte.
"""
import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main(argv=None):
    from . import esquema as ES
    from . import planificador as PL
    from . import orquestador as OR

    ap = argparse.ArgumentParser(prog="album", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="generar/escribir plan.json sin producir")
    p_plan.add_argument("album", help="ruta del album.json")
    p_plan.add_argument("--out", required=True, help="carpeta de salida del álbum")

    p_run = sub.add_parser("producir", help="planificar + producir + informe")
    p_run.add_argument("album", help="ruta del album.json")
    p_run.add_argument("--out", required=True, help="carpeta de salida del álbum")
    p_run.add_argument("--regen", default=None, metavar="IDS",
                       help="regenerar SOLO estas pistas (ids o índices, coma)")
    p_run.add_argument("--solo", default=None, metavar="IDS",
                       help="producir SOLO estas pistas (no toca el resto del estado)")
    p_run.add_argument("--forzar", action="store_true",
                       help="regenerar TODO aunque haya resultados válidos")
    p_run.add_argument("--sin-informe", action="store_true",
                       help="no generar informe/manifiesto al terminar")

    p_inf = sub.add_parser("informe", help="regenerar informe_album.json/.md + manifiesto")
    p_inf.add_argument("out", help="carpeta de salida del álbum")

    p_est = sub.add_parser("estado", help="mostrar estado.json resumido")
    p_est.add_argument("out", help="carpeta de salida del álbum")

    args = ap.parse_args(argv)

    if args.cmd == "plan":
        spec, avisos = ES.cargar_album(args.album)
        raiz = Path(args.album).resolve().parent
        plan, avisos_plan = PL.planificar(spec, raiz)
        ruta = PL.escribir_plan(plan, Path(args.out) / "plan.json")
        print("PLAN OK: %s" % ruta)
        print("  pistas: %d · semilla_album: %s"
              % (len(plan["pistas"]), plan["semilla_album"]))
        for a in avisos + avisos_plan:
            print("  aviso: %s" % a)
        if plan.get("errores_documentos"):
            for e in plan["errores_documentos"]:
                print("  ERROR DOC: %s" % e)
            print("  (corrige los documentos antes de producir; 'producir' ejecutará "
                  "el resto y dejará estas pistas como fallo)")
            return 1
        return 0

    if args.cmd == "producir":
        regen = [x for x in (args.regen or "").split(",") if x.strip()]
        solo = [x for x in (args.solo or "").split(",") if x.strip()]
        cod = OR.ejecutar(args.album, args.out, regen=regen, solo=solo or None,
                          forzar=args.forzar, informe=not args.sin_informe)
        if cod == 0:
            print("ÁLBUM OK: %s" % args.out)
        else:
            print("ÁLBUM CON FALLOS (ver estado.json / informe_album.md): %s" % args.out)
        return cod

    if args.cmd == "informe":
        from . import informe as INF
        ruta = INF.generar(args.out)
        print("INFORME OK: %s\n  + %s\n  + %s" % (ruta, Path(args.out) / "informe_album.md",
                                                  Path(args.out) / "manifiesto.json"))
        return 0

    if args.cmd == "estado":
        estado, lineas = OR.estado_de(args.out)
        print("Álbum: %s · actualizado: %s" % (estado.get("album"),
                                               estado.get("actualizado_utc")))
        for l in lineas:
            print("  %s" % l)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
