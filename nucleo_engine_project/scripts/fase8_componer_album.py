#!/usr/bin/env python3
"""FASE 8 — composición del álbum demo «Noches Largas» (13 pistas).

El sistema de álbumes NO genera documentos (los docs los escribe el
compositor); este script es ese flujo compositivo, determinista y
re-ejecutable: escribe los 13 documentos dark-director/1 (5 reutilizados de
la matriz de generalización FASE 6 + 8 nuevos) y el album.json del álbum.

Diseño según docs/PROPUESTA_VARIACION_ALBUM.md §2:
  - BPM 76–92 · tonalidades menores cercanas · 36–64 compases · 5–10 secciones
  - UNA dimensión especial por pista (tape_stop, break tenso, textura vibes…)
  - Distribución de perfiles: máx 3/13 (23%) por perfil; respiro cada ≤5 pistas
  - Armonía: ruta ORIGINAL en 5 pistas; biblioteca FASE 7 EXPLÍCITA en 8
    (9 de 10 keywords; familiarity_auto SOLO como declaración explícita)
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALBUM_DIR = ROOT / "albumes" / "noches_largas"
DOCS_DIR = ALBUM_DIR / "docs"
BASE_F6 = ROOT / "output" / "generalizacion_fase6"


def doc(title, key, bpm, seed, secciones, progs, *, resolution=None, ending=None):
    h = {"key": key, "language": "pop_dream_pop", "harmonic_rhythm_bars": 1,
         "progressions": progs}
    if resolution:
        h["resolution"] = resolution
    return {
        "schema": "dark-director/1",
        "meta": {"title": title,
                 "notes": "FASE 8 — álbum «Noches Largas» (composición nueva)."},
        "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
        "global": {"bpm": bpm, "seed": seed},
        "harmony": h,
        "structure": secciones,
        "ending": ending or {"fade_out": {"enabled": True, "bars": 3}},
    }


def s(id_, tipo, bars, e, t, d, focus, drums, **extra):
    sec = {"id": id_, "type": tipo, "bars": bars, "energy": e, "tension": t,
           "density": d, "focus": focus, "drums": drums}
    sec.update(extra)
    return sec


NUEVOS = {
    "bruma_dorada": doc(
        "Bruma Dorada", "Bb minor", 80, 8101,
        [s("intro", "intro", 4, 0.20, 0.20, 0.20, ["rhodes", "pad"], "air"),
         s("verse_1", "verse", 8, 0.40, 0.30, 0.40, ["sax_tenor", "bass"], "groove"),
         s("pre_1", "pre_chorus", 4, 0.52, 0.42, 0.50, ["rhodes", "vibraphone"], "light"),
         s("chorus_1", "chorus", 8, 0.68, 0.45, 0.55, ["sax_tenor", "rhodes"], "heavy"),
         s("break_1", "break", 4, 0.30, 0.55, 0.30, ["vibraphone"], "light",
           active=["vibraphone", "rhodes", "pad"]),
         s("chorus_2", "chorus", 8, 0.72, 0.50, 0.60, ["sax_tenor", "rhodes"], "heavy",
           final=True),
         s("outro", "outro", 4, 0.15, 0.15, 0.15, ["rhodes"], "air")],
        {"verse": ["Bbm9", "Gbmaj7", "Dbmaj9", "Ab7sus4"],
         "chorus": ["Gbmaj9", "Dbmaj9", "Bbm9", "Ab7sus4"]},
        resolution="tonal"),

    "neblina_alta": doc(
        "Neblina Alta", "E minor", 76, 8102,
        [s("intro", "intro", 4, 0.20, 0.20, 0.20, ["pad", "rhodes"], "air"),
         s("verse_1", "verse", 8, 0.42, 0.40, 0.45, ["bass", "drums"], "groove"),
         s("chorus_1", "chorus", 8, 0.62, 0.55, 0.55, ["bass", "rhodes"], "heavy"),
         s("bridge_1", "bridge", 4, 0.48, 0.70, 0.45, ["rhodes"], "light"),
         s("verse_2", "verse", 8, 0.45, 0.42, 0.48, ["bass", "drums"], "groove"),
         s("outro", "outro", 4, 0.15, 0.15, 0.15, ["pad"], "air")],
        {"verse": ["Em9", "Cmaj7", "Gmaj9", "D7sus4"],
         "chorus": ["Cmaj9", "Gmaj9", "Am9", "B7sus4"]},
        resolution="modal"),

    "viaducto_sur": doc(
        "Viaducto Sur", "D minor", 90, 8103,
        [s("intro", "intro", 4, 0.25, 0.25, 0.25, ["pad", "drums"], "air"),
         s("verse_1", "verse", 8, 0.45, 0.40, 0.45, ["sax_tenor", "drums"], "groove"),
         s("pre_1", "pre_chorus", 4, 0.58, 0.55, 0.55, ["rhodes", "bass"], "light"),
         s("chorus_1", "chorus", 8, 0.75, 0.55, 0.65, ["sax_tenor", "rhodes", "drums"],
           "heavy"),
         s("break_1", "break", 4, 0.32, 0.62, 0.32, ["vibraphone"], "light",
           active=["vibraphone", "rhodes", "pad"]),
         s("bridge_1", "bridge", 4, 0.55, 0.68, 0.50, ["rhodes", "strings"], "light"),
         s("chorus_2", "chorus", 8, 0.80, 0.60, 0.65, ["sax_tenor", "drums"], "heavy"),
         s("outro", "outro", 4, 0.18, 0.18, 0.18, ["pad", "rhodes"], "air")],
        {"verse": ["Dm9", "Bbmaj7", "Fmaj9", "C7sus4"],
         "chorus": ["Bbmaj9", "Fmaj9", "Gm9", "A7sus4"]},
        resolution="tonal",
        ending={"tape_stop": {"enabled": True, "bars": 3, "semitones": 8}}),

    "habitacion_vacia": doc(
        "Habitación Vacía", "F minor", 82, 8104,
        [s("intro", "intro", 4, 0.18, 0.18, 0.18, ["rhodes", "pad"], "air"),
         s("verse_1", "verse", 8, 0.38, 0.30, 0.38, ["rhodes", "bass"], "groove"),
         s("pre_1", "pre_chorus", 4, 0.50, 0.42, 0.48, ["vibraphone"], "light"),
         s("chorus_1", "chorus", 8, 0.65, 0.48, 0.55, ["rhodes", "vibraphone"], "heavy"),
         s("break_1", "break", 4, 0.28, 0.52, 0.28, ["pad"], "light",
           active=["pad", "rhodes", "vibraphone"]),
         s("verse_2", "verse", 8, 0.40, 0.32, 0.40, ["rhodes", "bass"], "groove"),
         s("outro", "outro", 4, 0.12, 0.12, 0.12, ["rhodes"], "air")],
        {"verse": ["Fm9", "Dbmaj7", "Abmaj9", "Eb7sus4"],
         "chorus": ["Dbmaj9", "Abmaj9", "Bbm7", "C7sus4"]},
        resolution="deceptive"),

    "asfalto_humedo": doc(
        "Asfalto Húmedo", "A minor", 86, 8105,
        [s("intro", "intro", 4, 0.25, 0.22, 0.25, ["rhodes"], "air"),
         s("verse_1", "verse", 8, 0.45, 0.38, 0.45, ["sax_tenor", "bass"], "groove"),
         s("pre_1", "pre_chorus", 4, 0.55, 0.48, 0.52, ["vibraphone", "drums"], "light"),
         s("chorus_1", "chorus", 8, 0.70, 0.50, 0.60, ["sax_tenor", "rhodes"], "heavy"),
         s("verse_2", "verse", 8, 0.48, 0.40, 0.48, ["sax_tenor", "bass"], "groove"),
         s("chorus_2", "chorus", 8, 0.75, 0.52, 0.62, ["sax_tenor", "rhodes"], "heavy",
           final=True),
         s("outro", "outro", 4, 0.15, 0.15, 0.15, ["rhodes", "pad"], "air")],
        {"verse": ["Am9", "Fmaj7", "Cmaj9", "G6"],
         "chorus": ["Fmaj9", "Cmaj9", "Dm9", "E7sus4"]},
        resolution="tonal"),

    "portico_sur": doc(
        "Pórtico Sur", "D minor", 79, 8106,
        [s("intro", "intro", 4, 0.18, 0.18, 0.18, ["pad", "rhodes"], "air"),
         s("verse_1", "verse", 8, 0.38, 0.30, 0.38, ["rhodes", "bass"], "groove"),
         s("chorus_1", "chorus", 8, 0.60, 0.42, 0.52, ["rhodes", "vibraphone"], "heavy"),
         s("break_1", "break", 4, 0.28, 0.50, 0.28, ["vibraphone"], "light",
           active=["vibraphone", "rhodes", "pad"]),
         s("verse_2", "verse", 8, 0.40, 0.32, 0.40, ["rhodes", "bass"], "groove"),
         s("outro", "outro", 4, 0.12, 0.12, 0.12, ["pad"], "air")],
        {"verse": ["Dm9", "Gm7", "Bbmaj7", "Asus4"],
         "chorus": ["Gm9", "Bbmaj7", "Fmaj9", "C7sus4"]},
        resolution="tonal"),

    "marea_baja": doc(
        "Marea Baja", "F minor", 84, 8107,
        [s("intro", "intro", 4, 0.22, 0.20, 0.22, ["rhodes", "pad"], "air"),
         s("verse_1", "verse", 8, 0.42, 0.35, 0.42, ["sax_tenor", "bass"], "groove"),
         s("pre_1", "pre_chorus", 4, 0.52, 0.45, 0.50, ["rhodes", "vibraphone"], "light"),
         s("chorus_1", "chorus", 8, 0.68, 0.48, 0.58, ["sax_tenor", "rhodes"], "heavy"),
         s("bridge_1", "bridge", 4, 0.50, 0.62, 0.48, ["strings", "rhodes"], "light"),
         s("chorus_2", "chorus", 8, 0.72, 0.50, 0.60, ["sax_tenor", "rhodes"], "heavy",
           final=True),
         s("outro", "outro", 4, 0.15, 0.15, 0.15, ["rhodes"], "air")],
        {"verse": ["Fm9", "Dbmaj7", "Abmaj7", "C7"],
         "chorus": ["Dbmaj9", "Abmaj9", "Fm9", "C7sus4"]},
        resolution="tonal"),

    "ultimo_metro": doc(
        "Último Metro", "C minor", 76, 8108,
        [s("intro", "intro", 4, 0.15, 0.15, 0.15, ["pad", "rhodes"], "air"),
         s("verse_1", "verse", 8, 0.36, 0.28, 0.36, ["rhodes", "bass"], "groove"),
         s("chorus_1", "chorus", 8, 0.58, 0.40, 0.50, ["rhodes", "vibraphone"], "heavy"),
         s("break_1", "break", 4, 0.25, 0.48, 0.25, ["vibraphone"], "light",
           active=["vibraphone", "rhodes", "pad"]),
         s("chorus_2", "chorus", 8, 0.62, 0.42, 0.52, ["rhodes", "vibraphone"], "heavy",
           final=True),
         s("outro", "outro", 4, 0.10, 0.10, 0.10, ["pad", "rhodes"], "air")],
        {"verse": ["Cm9", "Abmaj9", "Bbmaj7", "G7sus4"],
         "chorus": ["Abmaj9", "Ebmaj9", "Fm9", "G7sus4"]},
        resolution="open"),
}

REUTILIZADOS = ["medianoche_puerto_nuevo", "calles_de_neon", "habitacion_314",
                "casa_de_espejos", "nocturno_terminal"]

# Orden del álbum: id de carpeta → (doc fuente, perfil o None=asignado, harmony, rol)
ORDEN = [
    ("medianoche_puerto", "medianoche_puerto_nuevo", "sax", None,
     "apertura — melódico contenido"),
    ("calles_de_neon", "calles_de_neon", "full", {"keyword": "familiar_pop", "variacion": "subtle"},
     "energía urbana — material escrito respetado"),
    ("habitacion_314", "habitacion_314", "atmospheric",
     {"keyword": "melancholic", "variacion": "medium"}, "respiro atmosférico"),
    ("bruma_dorada", "bruma_dorada", "original", None,
     "respiro — camino ORIGINAL sin motores"),
    ("casa_de_espejos", "casa_de_espejos", "sax_rhodes",
     {"keyword": "soulful", "variacion": "medium"}, "dueto sax+Rhodes"),
    ("neblina_alta", "neblina_alta", "drums",
     {"keyword": "tension_release", "variacion": "subtle"}, "textura de batería"),
    ("viaducto_sur", "viaducto_sur", "full", {"id": "CINE01", "variacion": "medium"},
     "clímax 1 — tape_stop final"),
    ("habitacion_vacia", "habitacion_vacia", "atmospheric",
     {"keyword": "dream_pop", "variacion": "subtle"}, "vacío luminoso"),
    ("asfalto_humedo", "asfalto_humedo", None,
     {"keyword": "alternative", "variacion": "subtle"}, "perfil asignado por el planificador"),
    ("portico_sur", "portico_sur", "original", None,
     "respiro — camino ORIGINAL sin motores"),
    ("nocturno_terminal", "nocturno_terminal", "full",
     {"keyword": "dark_cinematic", "variacion": "medium"}, "referencia de identidad"),
    ("marea_baja", "marea_baja", "sax",
     {"keyword": "emotional_resolution", "variacion": "subtle"}, "resolución emocional"),
    ("ultimo_metro", "ultimo_metro", "atmospheric",
     {"keyword": "familiarity_auto", "variacion": "subtle"},
     "cierre — familiarity_auto EXPLÍCITA del compositor"),
]

SEMILLAS = {  # explícitas solo en las 5 reutilizadas (paridad FASE 6); el resto: derivadas
    "medianoche_puerto": 2026, "calles_de_neon": 2026, "habitacion_314": 2026,
    "casa_de_espejos": 2026, "nocturno_terminal": 2026,
}


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # 1) copiar los 5 documentos reutilizados (bytes idénticos a FASE 6)
    for _, fuente, _, _, _ in ORDEN:
        if fuente in REUTILIZADOS:
            origen = BASE_F6 / fuente / "doc.json"
            destino = DOCS_DIR / (fuente + ".json")
            shutil.copyfile(origen, destino)

    # 2) escribir los 8 documentos nuevos
    for id_carpeta, fuente, _, _, _ in ORDEN:
        if fuente in NUEVOS:
            (DOCS_DIR / (fuente + ".json")).write_text(
                json.dumps(NUEVOS[fuente], ensure_ascii=False, indent=2),
                encoding="utf-8")

    # 3) energías reales medias → curva objetivo del álbum (redondeada)
    curva = []
    for id_carpeta, fuente, _, _, _ in ORDEN:
        d = json.loads((DOCS_DIR / (fuente + ".json")).read_text(encoding="utf-8"))
        secs = d["structure"]
        curva.append(round(sum(x["energy"] for x in secs) / len(secs), 2))

    # 4) album.json
    pistas = []
    for i, (id_carpeta, fuente, perfil, harmony, rol) in enumerate(ORDEN):
        p = {"id": id_carpeta, "doc": "docs/%s.json" % fuente, "rol": rol}
        if perfil:
            p["perfil"] = perfil
        if id_carpeta in SEMILLAS:
            p["seed"] = SEMILLAS[id_carpeta]
        if harmony:
            p["harmony"] = harmony
        pistas.append(p)

    spec = {
        "schema": "dmd-album/1",
        "album": "Noches Largas",
        "identidad": "dark_triphop",
        "semilla_album": 3100,
        "objetivo": {"pistas": 13},
        "curva_energia": curva,
        "restricciones": {"perfil_frac_max": 0.4, "respiro_cada": 5,
                          "prohibir_consecutivos_iguales": True},
        "pistas": pistas,
    }
    (ALBUM_DIR / "album.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ALBUM ESCRITO: %s" % (ALBUM_DIR / "album.json"))
    print("docs: %d · curva_energia: %s" % (len(list(DOCS_DIR.glob('*.json'))), curva))
    return 0


if __name__ == "__main__":
    sys.exit(main())
