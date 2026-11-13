"""Informe de álbum y manifiesto de reproducibilidad — FASE 8.

Genera en la carpeta del álbum:
  - ``informe_album.json``  — máquina: por pista, diversidad POST, coherencia,
    duplicados, reproducibilidad (versiones, semillas, comandos, hashes).
  - ``informe_album.md``    — humano: resumen, tabla de pistas, chequeos y la
    sección «técnico vs musical» (qué está medido y qué requiere escucha).
  - ``manifiesto.json``     — reproducción completa: por pista la config
    efectiva, el comando exacto de regeneración con --verify y los hashes.

Las métricas técnicas NUNCA se presentan como veredictos musicales: la
sección ``pendiente_escucha`` lista lo que solo el oído del usuario decide.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from . import esquema as ES
from . import diversidad as DV


def _leer(out, nombre, defecto=None):
    p = Path(out) / nombre
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return defecto
    return defecto


def _evidencia_pista(carpeta):
    p = Path(carpeta) / "evidencia.json"
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {}


def _int_o(x):
    """Entero si es un float integral (82.0 → 82); si no, el valor tal cual."""
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def generar(out):
    """Genera informe_album.json/.md y manifiesto.json. Devuelve ruta .json."""
    out = Path(out)
    plan = _leer(out, "plan.json")
    estado = _leer(out, "estado.json", {})
    huellas = _leer(out, "huellas.json", {})
    if plan is None:
        raise FileNotFoundError("no hay plan.json en %s (ejecuta 'album plan' o "
                                "'album producir' primero)" % out)
    pistas_plan = plan["pistas"]
    st = estado.get("pistas", {})

    # ------------------------------------------------------------- por pista
    filas = []
    for t in pistas_plan:
        reg = st.get(t["id"], {})
        filas.append({
            "indice": t["indice"], "id": t["id"], "titulo": t.get("titulo"),
            "estado": reg.get("estado", "no_ejecutada"),
            "razon": reg.get("razon"),
            "error": reg.get("error"),
            "perfil": t["perfil"], "perfil_origen": t.get("perfil_origen"),
            "seed": t["seed"], "seed_origen": t.get("origen_seed"),
            "harmony": t.get("harmony"),
            "bpm": _int_o(reg.get("bpm", (t.get("digest") or {}).get("bpm"))),
            "tonalidad": (t.get("digest") or {}).get("tonalidad"),
            "compases": reg.get("compases", (t.get("digest") or {}).get("compases")),
            "duracion_s": reg.get("duracion_s"),
            "sha256_midi": reg.get("sha256_midi"),
            "sha256_doc": t.get("sha256_doc"),
            "compliance_fails": reg.get("compliance_fails", []),
            "compliance_warns": reg.get("compliance_warns", []),
            "carpeta": reg.get("carpeta"),
        })
    ok = [f for f in filas if f["estado"] == "ok"]
    fallo = [f for f in filas if f["estado"] == "fallo"]

    # ------------------------------------------------------------ diversidad
    post = DV.analizar_post({"pistas": st}, pistas_plan, huellas=huellas)
    pre = plan.get("analisis", {}).get("diversidad_pre", {})
    curva = plan.get("analisis", {}).get("curva_energia", {})

    # ----------------------------------------------------------- coherencia
    identidad_ok = all((f["perfil"] is not None) for f in filas) and plan.get("identidad") == ES.IDENTIDAD_ALBUM
    coherencia = {
        "identidad": plan.get("identidad"),
        "identidad_ok": identidad_ok,
        "tonalidades": sorted({f["tonalidad"] for f in filas if f["tonalidad"]}),
        "bpm_valores": sorted({f["bpm"] for f in filas if f["bpm"]}),
        "bpm_rango_referencia": DV.BPM_SANO,
        "bpm_todos_en_rango": all(f["bpm"] and DV.BPM_SANO[0] <= f["bpm"] <= DV.BPM_SANO[1] for f in ok),
        "distancia_tonal_consecutivas": pre.get("distancia_tonal_consecutivas", []),
        "tonalidades_pegadas": pre.get("tonalidades_pegadas", []),
    }

    # ------------------------------------------------------ reproducibilidad
    versiones = plan.get("versiones", {})
    regenerar_pistas = {}
    manifiesto_pistas = []
    for f in filas:
        if f["estado"] != "ok":
            continue
        evid = _evidencia_pista(f["carpeta"]) if f["carpeta"] else {}
        cmd = None
        if f["carpeta"] and f["sha256_midi"]:
            cmd = ("python3 scripts/produce.py %s/%s/doc.json --production %s --seed %d%s"
                   " --out %s --verify %s"
                   % (out, Path(f["carpeta"]).name, f["perfil"], f["seed"],
                      (" --harmony-id %s" % f["harmony"]["id"]) if (f["harmony"] or {}).get("id")
                      else (" --harmony %s" % f["harmony"]["keyword"]) if (f["harmony"] or {}).get("keyword")
                      else "",
                      f["carpeta"], f["sha256_midi"]))
        regenerar_pistas[f["id"]] = cmd
        manifiesto_pistas.append({
            "id": f["id"], "indice": f["indice"],
            "doc": f["carpeta"] and str(Path(f["carpeta"]) / "doc.json"),
            "sha256_doc": f["sha256_doc"],
            "perfil": f["perfil"], "seed": f["seed"],
            "harmony": f["harmony"],
            "sha256_midi": f["sha256_midi"],
            "config_efectiva": (f["carpeta"] and
                                _leer(Path(f["carpeta"]), "config_efectiva.json")),
            "regenerar": cmd,
            "evidencia": (f["carpeta"] and str(Path(f["carpeta"]) / "evidencia.json")),
            "evidencia_sha256_midi": evid.get("sha256_midi"),
        })

    manifiesto = {
        "schema": "dmd-album-manifiesto/1",
        "album": plan.get("album"),
        "semilla_album": plan.get("semilla_album"),
        "creado_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "versiones": versiones,
        "regenerar_album": ("python3 -m album producir %s --out %s --forzar"
                            % (plan.get("raiz") and (Path(plan["raiz"]) / "album.json"), out)),
        "pistas": manifiesto_pistas,
        "hashes": {
            "plan_json": _sha_archivo(out / "plan.json"),
            "estado_json": _sha_archivo(out / "estado.json"),
            "huellas_json": _sha_archivo(out / "huellas.json"),
        },
    }
    (out / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2),
                                         encoding="utf-8")

    informe = {
        "schema": ES.SCHEMA_INFORME,
        "album": plan.get("album"),
        "generado_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "resumen": {
            "pistas_totales": len(filas),
            "ok": len(ok),
            "fallo": len(fallo),
            "no_ejecutadas": len(filas) - len(ok) - len(fallo),
            "duracion_total_s": round(sum(f["duracion_s"] or 0 for f in ok), 1),
            "avisos_plan": plan.get("analisis", {}).get("avisos", []),
        },
        "pistas": filas,
        "diversidad": {
            "pre": pre,
            "post": {k: post[k] for k in ("duplicados_exactos", "similares_sospechosos",
                                          "umbral_similitud", "pares_analizados")},
            "curva_energia": curva,
        },
        "coherencia": coherencia,
        "tecnico_vs_musical": {
            "metricas_tecnicas": [
                "duplicados exactos por SHA256 del MIDI",
                "similitud material por Jaccard de huellas (umbral %.2f)" % post["umbral_similitud"],
                "distribución y fracción de perfiles",
                "variedad en consecutivas (perfil+tonalidad+BPM)",
                "ventanas de respiro", "rango de BPM de referencia",
                "distancia tonal entre consecutivas", "adherencia a curva de energía",
                "compliance del validador de forge por pista",
            ],
            "pendiente_escucha": [
                "coherencia de identidad audible entre pistas",
                "fatiga de densidad o saturación de perfiles",
                "naturalidad de las transiciones entre pistas (orden de reproducción)",
                "calidad de las progresiones familiares activadas (si las hay)",
                "equilibrio sax/Rhodes/vibes/batería en el conjunto",
            ],
        },
        "reproducibilidad": {
            "semilla_album": plan.get("semilla_album"),
            "versiones": versiones,
            "regenerar_album": manifiesto["regenerar_album"],
            "regenerar_pistas": regenerar_pistas,
            "manifiesto": "manifiesto.json",
        },
    }
    ruta_json = out / "informe_album.json"
    ruta_json.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    _markdown(out, informe)
    return ruta_json


def _sha_archivo(ruta):
    p = Path(ruta)
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _fmt_harmony(h):
    if not h:
        return "—"
    if h.get("id"):
        return "%s (%s)" % (h["id"], h.get("variacion", "subtle"))
    if h.get("progressions"):
        return "pins %s" % ",".join(sorted(h["progressions"]))
    return "%s (%s)" % (h.get("keyword"), h.get("variacion", "subtle"))


def _markdown(out, inf):
    L = []
    L.append("# Informe de álbum — %s" % inf["album"])
    L.append("")
    L.append("Generado: %s · esquema %s" % (inf["generado_utc"][:19], inf["schema"]))
    L.append("")
    r = inf["resumen"]
    L.append("**Pistas:** %d · **OK:** %d · **fallo:** %d · **no ejecutadas:** %d · "
             "**duración total:** %.1f s (~%.1f min)"
             % (r["pistas_totales"], r["ok"], r["fallo"], r["no_ejecutadas"],
                r["duracion_total_s"], r["duracion_total_s"] / 60.0))
    L.append("")
    L.append("| # | Pista | Perfil | Seed | Armonía | Tonalidad | BPM | Comp. | Dur s | SHA256(16) | Estado |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for f in inf["pistas"]:
        L.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            f["indice"], f["id"], f["perfil"] or "—",
            f["seed"] if f["seed"] is not None else "—",
            _fmt_harmony(f["harmony"]), f["tonalidad"] or "—",
            f["bpm"] or "—", f["compases"] or "—",
            ("%.1f" % f["duracion_s"]) if f["duracion_s"] else "—",
            (f["sha256_midi"] or "—")[:16], f["estado"] + (("" if not f["error"] else " ⚠")))
        )
    L.append("")
    d = inf["diversidad"]
    L.append("## Diversidad y coherencia (métricas técnicas)")
    L.append("")
    pre = d.get("pre", {})
    L.append("- Distribución de perfiles: %s" % pre.get("perfiles", {}))
    L.append("- Exceso de perfil (> %.0f%%): %s" % (100 * (pre.get("frac_max_config") or 0.4),
                                                    pre.get("exceso_perfil") or "ninguno"))
    L.append("- Consecutivas idénticas (perfil+tonalidad+BPM): %s"
             % (pre.get("consecutivos_iguales") or "ninguna"))
    L.append("- Ventanas sin respiro: %s" % (pre.get("ventanas_sin_respiro") or "ninguna"))
    L.append("- Duplicados exactos (SHA256): %s" % (d["post"]["duplicados_exactos"] or "ninguno"))
    L.append("- Similares sospechosos (Jaccard ≥ %.2f): %s"
             % (d["post"]["umbral_similitud"],
                d["post"]["similares_sospechosos"] or "ninguno"))
    if d.get("curva_energia", {}).get("objetivo"):
        L.append("- Curva de energía objetivo: %s" % d["curva_energia"]["objetivo"])
        L.append("- Curva de energía real:    %s" % d["curva_energia"]["real"])
        L.append("- Desviación máxima: %.2f" % max(d["curva_energia"]["desviacion"] or [0.0]))
    c = inf["coherencia"]
    L.append("- Identidad del álbum: %s (%s)" % (c["identidad"],
                                                 "consistente" if c["identidad_ok"] else "INCONSISTENTE"))
    L.append("- Tonalidades: %s" % ", ".join(c["tonalidades"]))
    L.append("- BPM: %s (referencia %d–%d)" % (", ".join(str(b) for b in c["bpm_valores"]),
                                               c["bpm_rango_referencia"][0],
                                               c["bpm_rango_referencia"][1]))
    L.append("")
    if r["avisos_plan"]:
        L.append("## Avisos de planificación")
        L.append("")
        for a in r["avisos_plan"]:
            L.append("- %s" % a)
        L.append("")
    for f in inf["pistas"]:
        if f["estado"] == "fallo":
            L.append("- **FALLO %s:** %s" % (f["id"], f["error"]))
    if any(f["estado"] == "fallo" for f in inf["pistas"]):
        L.append("")
    L.append("## Técnico vs musical")
    L.append("")
    L.append("Medido automáticamente (técnico):")
    L.append("")
    for m in inf["tecnico_vs_musical"]["metricas_tecnicas"]:
        L.append("- %s" % m)
    L.append("")
    L.append("**Requiere escucha humana (pendiente de validación del usuario):**")
    L.append("")
    for m in inf["tecnico_vs_musical"]["pendiente_escucha"]:
        L.append("- %s" % m)
    L.append("")
    L.append("## Reproducir")
    L.append("")
    L.append("```bash")
    L.append("# álbum completo (regenera todo)")
    L.append(inf["reproducibilidad"]["regenerar_album"])
    L.append("")
    L.append("# una pista, verificada por hash")
    ejemplo = next(iter(inf["reproducibilidad"]["regenerar_pistas"].values()), None)
    if ejemplo:
        L.append(ejemplo)
    L.append("```")
    L.append("")
    L.append("Manifiesto completo (config efectiva, hashes y comandos por pista): "
             "`manifiesto.json` · estado de ejecución: `estado.json`.")
    (out / "informe_album.md").write_text("\n".join(L) + "\n", encoding="utf-8")
