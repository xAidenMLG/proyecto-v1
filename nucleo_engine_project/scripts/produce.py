#!/usr/bin/env python3
"""FASE 6 — ETAPA F: CLI de producción reproducible.

Un comando para producir una canción nueva sin reconstruir configuración:

    python3 scripts/produce.py DOC.json --production full --seed 2026 --out output/produccion/mi_tema

Escribe en --out:
  doc.json               documento dark-director/1 (entrada exacta)
  config_efectiva.json   config normalizada de motores (lo que se aplicó)
  <out>.mid              MIDI generado
  evidencia.json         hashes, versiones, fecha, plan/resumen de actividad
  (y actualiza output/produccion/INDICE.md si --out está bajo output/)

Regenerar un resultado anterior:
    python3 scripts/produce.py DOC.json --production full --seed 2026 \
        --out <carpeta> --verify <sha256_esperado>

Reutiliza dark_director.compilador + jazz_engine (nada de renderizado nuevo;
MIDI Forge sigue siendo el único motor).

FASE 8 — el núcleo se expone como ``producir_cancion()`` para que el sistema
de álbumes (paquete ``album/``) orqueste pistas SIN duplicar la lógica de
producción. La conducta del CLI es idéntica a la de FASE 6/7.
"""
import argparse
import copy
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dark_director import compilador, contract, forge_link  # noqa: E402
import jazz_engine as je  # noqa: E402
from jazz_engine import coordinator as CO  # noqa: E402

forge_link.import_forge()
from forge import engine as forge_engine  # noqa: E402
from forge import validate as V  # noqa: E402


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _huella(res):
    """FASE 8 — huella técnica del material musical para control de diversidad.

    Conjunto de eventos (pista_rol, paso_16avos, clase_de_altura). Es una
    métrica TÉCNICA de similitud material, no un juicio musical. Se devuelve
    como lista de enteros compactos (rol*1_000_000 + paso*12 + clase) para
    poder serializarla y comparar pistas entre sí (Jaccard).
    """
    roles = {}
    eventos = set()
    for b in res.bufs:
        rol = b.role
        if rol not in roles:
            roles[rol] = len(roles)
        ri = roles[rol]
        for n in b.notes:
            paso = int(round(float(n.t) / res.ctx.bb * 4.0))
            eventos.add(ri * 1_000_000 + paso * 12 + (int(n.p) % 12))
    return sorted(eventos)


def producir_cancion(doc, *, production="full", seed=None, harmony=None,
                     out_dir, verify=None, indice=True, events=False):
    """Núcleo de producción (FASE 8): una canción completa, igual que el CLI.

    ``doc`` es el documento dark-director/1 ya cargado (dict). Escribe en
    ``out_dir`` exactamente los mismos artefactos que el CLI de FASE 6
    (doc.json, config_efectiva.json, <carpeta>.mid, evidencia.json) salvo
    cuando ``verify`` no es None: entonces NO escribe nada y solo compara.

    Opción A (OFF por defecto, autorizada en la misión de integración):
    ``events=True`` persiste además ``events.json`` con
    ``forge.engine.to_events(res)`` (datos de reproducción WebAudio del
    navegador; NO es un segundo generador: usa el MISMO ``res`` ya en
    memoria). Con ``events=False`` la salida y el MIDI son byte a byte
    idénticos al comportamiento histórico.

    Devuelve un dict resumen con sha256, rutas, compliance y la huella
    técnica (FASE 8) para el control de diversidad del álbum.

    Lanza las excepciones reales de los motores (DirectorInvalido,
    ValueError de config, etc.): el orquestador del álbum decide cómo
    aislalas por pista.
    """
    doc = copy.deepcopy(doc)
    if seed is None:
        seed = int((doc.get('global') or {}).get('seed', 0) or 0)
    seed = int(seed)
    out = Path(out_dir)

    r = compilador.compilar(copy.deepcopy(doc))
    proj = r['proyecto']
    avisos = r['avisos']
    cfg = {"production": production, "seed": seed}
    if harmony:
        cfg["harmony"] = copy.deepcopy(harmony)
    res = je.render.generate(copy.deepcopy(proj), cfg)
    val = V.validate(res)
    sha = _sha(res.midi)

    if verify is not None:
        return {"ok": sha == str(verify), "sha256": sha, "verificado": str(verify),
                "out_dir": str(out), "perfil": production, "seed": seed,
                "events": None}

    out.mkdir(parents=True, exist_ok=True)
    (out / 'doc.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                                  encoding='utf-8')
    (out / 'config_efectiva.json').write_text(
        json.dumps(CO.normalize_config(cfg), ensure_ascii=False, indent=2),
        encoding='utf-8')
    (out / (out.name + '.mid')).write_bytes(res.midi)

    # Opción A — events.json (default OFF): reproduce en navegador con el
    # Player WebAudio original. Mismo ``res`` que el MIDI: cero recálculo.
    events_path = None
    if events:
        (out / 'events.json').write_text(
            json.dumps(forge_engine.to_events(res), ensure_ascii=False),
            encoding='utf-8')
        events_path = str(out / 'events.json')

    m = je.render.metrics(res) if production != 'original' else None
    ev = {
        "composicion": (doc.get('meta') or {}).get('title') or out.name,
        "perfil_produccion": production,
        "seed": seed,
        "sha256_midi": sha,
        "sha256_doc": _sha(json.dumps(doc, ensure_ascii=False, sort_keys=True).encode('utf-8')),
        "fecha_generacion_utc": datetime.datetime.now(
            datetime.timezone.utc).isoformat(),
        "versiones": {
            "jazz_engine": je.__version__,
            "contrato": contract.contract_info(),
        },
        "bpm": res.ctx.bpm,
        "compases": res.ctx.total_bars,
        "duracion_s": round(res.ctx.total_beats * 60.0 / res.ctx.bpm, 1),
        "notas_por_pista": {b.track['id']: len(b.notes) for b in res.bufs},
        "compliance_fails": [c['id'] for c in val['compliance'] if c['status'] == 'fail'],
        "compliance_warns": [c['id'] for c in val['compliance'] if c['status'] == 'warn'],
        "avisos_compilador": avisos,
        "resumen_actividad": (
            {"frases_sax": len(m.get('sax_frases_activas', [])),
             "rhodes_melodico_por_seccion": m.get('rhodes_melodico_por_seccion'),
             "vibes_eco_por_seccion": m.get('vibes_eco_por_seccion')} if m else
            "camino ORIGINAL (sin motores)"),
        "reproduccion": {
            "regenerar": ("python3 scripts/produce.py doc.json --production %s --seed %d "
                          "--out %s --verify %s" % (production, seed, out, sha)),
            "fluidsynth_windows": ('fluidsynth -ni soundfont.sf2 "%s" -F salida.wav -r 44100'
                                   % (out.name + '.mid')),
        },
    }
    ev_har = (getattr(res, "evidence", None) or {}).get("harmony")
    if ev_har is not None:
        ev["harmonia"] = {"activacion": cfg.get("harmony"),
                          "resumen": ev_har.get("resumen"),
                          "eleccion": {t: {"id": v.get("entrada"), "nombre": v.get("nombre")}
                                       for t, v in (ev_har.get("secciones") or {}).items()},
                          "respetadas_material": ev_har.get("respetadas_material")}
    (out / 'evidencia.json').write_text(json.dumps(ev, ensure_ascii=False, indent=2),
                                        encoding='utf-8')

    # índice de producción (si la salida vive bajo output/)
    if indice:
        try:
            indice_md = out.parent / 'INDICE.md'
            linea = "| %s | %s | %d | %s | %.1fs | %s |\n" % (
                out.name, production, seed, sha[:16], ev['duracion_s'],
                ev['compliance_fails'] or 'OK')
            if not indice_md.exists():
                indice_md.write_text("# Producción — índice de canciones\n\n"
                                     "| Carpeta | Perfil | Seed | SHA256(16) | Dur s | Compliance |\n"
                                     "|---|---|---|---|---|---|\n", encoding='utf-8')
            with open(indice_md, 'a', encoding='utf-8') as fh:
                fh.write(linea)
        except OSError:
            pass

    return {"ok": True, "sha256": sha, "out_dir": str(out),
            "midi": str(out / (out.name + '.mid')),
            "evidencia": str(out / 'evidencia.json'),
            "events": events_path,
            "perfil": production, "seed": seed,
            "bpm": ev["bpm"], "compases": ev["compases"],
            "duracion_s": ev["duracion_s"],
            "compliance_fails": ev["compliance_fails"],
            "compliance_warns": ev["compliance_warns"],
            "harmonia": ev.get("harmonia"),
            "huella": _huella(res)}


def main():
    ap = argparse.ArgumentParser(prog="produce")
    ap.add_argument("doc", help="documento dark-director/1 (JSON)")
    ap.add_argument("--production", default="full", choices=je.production.nombres(),
                    help="perfil de producción (default: full)")
    ap.add_argument("--seed", type=int, default=None,
                    help="semilla de motores (default: global.seed del documento)")
    ap.add_argument("--harmony", metavar="KEYWORD", default=None,
                    help="FASE 7: keyword de la biblioteca de familiaridad "
                         "(familiar_pop | melancholic | nostalgic | dark_cinematic | "
                         "dream_pop | alternative | soulful | emotional_resolution | "
                         "tension_release | familiarity_auto)")
    ap.add_argument("--harmony-id", metavar="ID", default=None,
                    help="FASE 7: progresión concreta de la biblioteca (p.ej. CINE01)")
    ap.add_argument("--harmony-variacion", default=None,
                    choices=("none", "subtle", "medium", "rich"),
                    help="FASE 7: nivel de transformación (default: subtle)")
    ap.add_argument("--harmony-seed", type=int, default=None,
                    help="FASE 7: semilla propia de la biblioteca (si no, la de --seed)")
    ap.add_argument("--out", required=True, help="carpeta de salida (se crea)")
    ap.add_argument("--verify", metavar="SHA256",
                    help="regenerar y comparar contra este hash (reproducibilidad)")
    ap.add_argument("--events", action="store_true",
                    help="Opción A: guardar además events.json (Player WebAudio; "
                         "default OFF, no altera el MIDI)")
    args = ap.parse_args()

    doc = json.loads(Path(args.doc).read_text(encoding='utf-8'))
    har = {}
    if args.harmony:
        har["keyword"] = args.harmony
    if args.harmony_id:
        har["id"] = args.harmony_id
    if args.harmony_variacion:
        har["variacion"] = args.harmony_variacion
    if args.harmony_seed is not None:
        har["seed"] = args.harmony_seed

    r = producir_cancion(doc, production=args.production,
                         seed=args.seed, harmony=(har or None),
                         out_dir=args.out, verify=args.verify,
                         events=args.events)
    if args.verify:
        print("VERIFICACION: %s\n  esperado %s\n  actual   %s"
              % ("OK — resultado idéntico" if r["ok"] else "FALLO — el resultado DIFIERE",
                 args.verify, r["sha256"]))
        return 0 if r["ok"] else 1

    print("OK: %s (%s, seed %d)\n  SHA256 %s\n  evidencia: %s"
          % (r["midi"], r["perfil"], r["seed"], r["sha256"], r["evidencia"]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
