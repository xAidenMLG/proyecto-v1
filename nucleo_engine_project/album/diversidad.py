"""Control de diversidad y coherencia del álbum — FASE 8.

Métricas TÉCNICAS (medibles) y CHEQUEOS estructurales del álbum. Ninguna de
estas métricas es un juicio musical: el informe las separa explícitamente de
lo que requiere escucha humana.

Dos momentos:
  - PRE (planificación): sobre los documentos (tonalidad, BPM, estructura,
    energía, perfiles). Detecta colchones de variedas incumplidos ANTES de
    producir nada (PROPUESTA_VARIACION_ALBUM §4).
  - POST (producción): sobre los MIDIs generados. Duplicados exactos
    (SHA256) y similitud material sospechosa (Jaccard de huellas de eventos).

Umbrales (constantes documentadas, NO juicios musicales):
  - SIMILITUD_SOSPECHOSA = 0.85 de Jaccard de huella (misma música casi
    segura: mismo material en la misma rejilla y registros).
  - BPM_SANO (esquema) 76–92: referencia del universo Dark Trip Hop; fuera
    de rango → aviso, no fallo.
  - Distancia de tonalidad entre consecutivas: 1 semitono → aviso
    (PROPUESTA §2: «semitonos consecutivos rompen continuidad»).
"""
from .esquema import BPM_SANO, PERFILES_RESPIRO

SIMILITUD_SOSPECHOSA = 0.85

_NOTAS = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_ALT = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def tonalidad_a_pc(texto):
    """'D minor' → 2 (clase de altura de la tónica). None si no parsea."""
    try:
        nombre = str(texto).strip().split()[0]
        base = nombre[:-1] if nombre[-1] in "b#" else nombre
        pc = _ALT.get(base.upper() if len(base) == 1 else base.capitalize())
        if pc is None:
            return None
        if nombre[-1] == "#":
            pc += 1
        elif nombre[-1] == "b":
            pc -= 1
        return pc % 12
    except Exception:
        return None


def distancia_tonalidad(t1, t2):
    """Distancia en semitonos (círculo, 0–6) entre dos textos de tonalidad."""
    a, b = tonalidad_a_pc(t1), tonalidad_a_pc(t2)
    if a is None or b is None:
        return None
    d = abs(a - b)
    return min(d, 12 - d)


# ---------------------------------------------------------------- PRE (docs)

def analizar_pre(pistas, restricciones):
    """Chequeos de diversidad sobre el PLAN (antes de producir).

    ``pistas``: lista de dicts de plan (con 'perfil', 'seed', 'digest').
    ``restricciones``: dict con perfil_frac_max / respiro_cada /
    prohibir_consecutivos_iguales. Devuelve dict de análisis.
    """
    n = len(pistas)
    perfiles = {}
    for p in pistas:
        if p["perfil"] is None:
            continue  # pista con error de documento: sin perfil asignado
        perfiles[p["perfil"]] = perfiles.get(p["perfil"], 0) + 1

    frac_max = float(restricciones.get("perfil_frac_max", 0.4))
    respiro_cada = int(restricciones.get("respiro_cada", 5))
    prohib_consec = bool(restricciones.get("prohibir_consecutivos_iguales", True))

    exceso_perfil = []
    for nombre, cuenta in sorted(perfiles.items()):
        if cuenta > frac_max * n + 1e-9:
            exceso_perfil.append({"perfil": nombre, "cuenta": cuenta,
                                  "frac": round(cuenta / n, 3) if n else 0.0})

    ventana_huerfana = []
    for i in range(0, max(0, n - respiro_cada) + 1):
        ventana = pistas[i:i + respiro_cada]
        if ventana and all(p["perfil"] not in PERFILES_RESPIRO for p in ventana):
            ventana_huerfana.append([ventana[0]["id"], ventana[-1]["id"]])

    consecutivos = []
    for a, b in zip(pistas, pistas[1:]):
        if a.get("error_plan") or b.get("error_plan"):
            continue  # sin digest: no comparable
        d1, d2 = a["digest"], b["digest"]
        if (a["perfil"] == b["perfil"] and d1.get("tonalidad") == d2.get("tonalidad")
                and d1.get("bpm") == d2.get("bpm")):
            consecutivos.append({"pistas": [a["id"], b["id"]],
                                 "motivo": "perfil+tonalidad+bpm idénticos"})
        elif prohib_consec and a["perfil"] == b["perfil"]:
            consecutivos.append({"pistas": [a["id"], b["id"]],
                                 "motivo": "perfil repetido consecutivo"})

    tono_pegada = []
    for a, b in zip(pistas, pistas[1:]):
        if a.get("error_plan") or b.get("error_plan"):
            continue
        d = distancia_tonalidad(a["digest"].get("tonalidad"), b["digest"].get("tonalidad"))
        if d == 1:
            tono_pegada.append({"pistas": [a["id"], b["id"]], "semitonos": 1})

    bpm_fuera = [{"pista": p["id"], "bpm": p["digest"].get("bpm")}
                 for p in pistas if not p.get("error_plan")
                 and not (BPM_SANO[0] <= (p["digest"].get("bpm") or 0) <= BPM_SANO[1])]

    distancias = []
    for a, b in zip(pistas, pistas[1:]):
        if a.get("error_plan") or b.get("error_plan"):
            distancias.append(None)
            continue
        distancias.append(distancia_tonalidad(a["digest"].get("tonalidad"),
                                              b["digest"].get("tonalidad")))

    return {
        "perfiles": perfiles,
        "frac_max_config": frac_max,
        "exceso_perfil": exceso_perfil,
        "respiro_cada": respiro_cada,
        "ventanas_sin_respiro": ventana_huerfana,
        "consecutivos_iguales": consecutivos,
        "tonalidades_pegadas": tono_pegada,
        "bpm_fuera_de_rango": bpm_fuera,
        "bpm_rango_sano": [BPM_SANO[0], BPM_SANO[1]],
        "distancia_tonal_consecutivas": distancias,
    }


def curva_energia_real(pistas):
    """Energía media REAL por pista (del digest del doc)."""
    return [round((p.get("digest") or {}).get("energia_media", 0.0), 3) for p in pistas]


def desviacion_curva(objetivo, real):
    """Desviaciones |objetivo - real| por pista (lista paralela)."""
    if not objetivo:
        return []
    return [round(abs(float(o) - float(r)), 3) for o, r in zip(objetivo, real)]


# --------------------------------------------------------------- POST (MIDI)

def similitud(huella_a, huella_b):
    """Jaccard entre dos huellas (listas de enteros). 0.0 si ambas vacías."""
    a, b = set(huella_a or []), set(huella_b or [])
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return round(inter / union, 4) if union else 0.0


def analizar_post(estado, pistas_plan, huellas=None):
    """Chequeos de diversidad sobre los RESULTADOS (MIDIs producidos).

    ``estado``: dict estado.json (estado por pista con sha256_midi).
    ``huellas``: dict huellas.json (huella técnica por pista); si falta, se
    intenta la clave 'huella' del estado (compatibilidad).
    ``pistas_plan``: lista de dicts del plan (para ids en orden).
    Devuelve dict con duplicados_exactos, similares_sospechosos y matriz.
    """
    st = estado.get("pistas", {})
    huellas = huellas or {}

    def _huella(tid):
        if tid in huellas and huellas[tid]:
            return huellas[tid]
        return (st.get(tid) or {}).get("huella") or []

    ids_ok = [t["id"] for t in pistas_plan
              if (st.get(t["id"], {}) or {}).get("estado") == "ok"]

    por_sha = {}
    for tid in ids_ok:
        sha = st[tid].get("sha256_midi")
        por_sha.setdefault(sha, []).append(tid)
    duplicados = [{"sha256": s, "pistas": g} for s, g in sorted(por_sha.items())
                  if len(g) > 1]

    similares = []
    matriz = {}
    for i, a in enumerate(ids_ok):
        for b in ids_ok[i + 1:]:
            s = similitud(_huella(a), _huella(b))
            if s >= SIMILITUD_SOSPECHOSA:
                similares.append({"pistas": [a, b], "similitud": s})
            matriz["%s|%s" % (a, b)] = s
    similares.sort(key=lambda x: -x["similitud"])

    return {
        "duplicados_exactos": duplicados,
        "similares_sospechosos": similares,
        "umbral_similitud": SIMILITUD_SOSPECHOSA,
        "pares_analizados": len(ids_ok) * (len(ids_ok) - 1) // 2,
        "matriz_similitud": matriz,
    }
