"""Genera las 5 composiciones de DEMOSTRACIÓN (misión §13).

Todas son proyectos Composer REALES que pasan por la cadena completa
(randomizador → conflictos → doc → Song Map → validador REAL → compilador
REAL). Cada carpeta en ``profiles/`` contiene:

    proyecto.json        — proyecto dmd-composer/1 (importable en la UI)
    doc.json             — documento dark-director/1 rev 3.2
    song_map.json        — Song Map
    song_map.csv         — Song Map CSV
    generacion.json      — resumen: seed, decisiones, SHA256, validación

Determinismo: mismas seeds → mismos documentos (bit a bit).

Uso:  python scripts/demostraciones.py            (crea/actualiza profiles/)
      python scripts/demostraciones.py --verificar (solo verifica SHAs)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))

from composer import engine, manifest as MF, model, store  # noqa: E402
from composer import bridge  # noqa: E402

PROFILES = PKG / "profiles"




def demo_1_totalmente_automatica():
    """1. Composición completamente automática: solo el nombre y el mood."""
    p = model.new_project("Nocturno Automatico")
    p.pid = "demo_1_totalmente_automatica"
    p.decisions["mood"] = model.decision("fixed", "melancholic")
    # todo lo demás queda automático o libre, tal cual new_project
    p.notes = "Demo 1: todo automático salvo el mood. Composer decide, DMD libera."
    return p


def demo_2_solo_vibraphone():
    """2. Solo de vibraphone con acompañamiento automático (misión §3)."""
    p = model.new_project("Vibraphone Desnudo")
    p.pid = "demo_2_solo_vibraphone"
    p.decisions.update({
        "identity": model.decision("fixed", "dark_triphop"),
        "mood": model.decision("fixed", "melancholic"),
        "key": model.decision("fixed", "D minor"),
        "harmony_mode": model.decision("fixed", "guided"),
        "protagonist": model.decision("fixed", "vibraphone"),
        "spaces": model.decision("fixed", "mandatory"),
    })
    p.instruments["vibraphone"] = model.InstrumentDecision(role="protagonist")
    p.sections = [
        model.Section(id="intro", label="Intro", type="intro", bars=8, drums="air",
                      focus=["vibraphone"], active=["vibraphone", "rhodes", "pad"]),
        model.Section(id="solo", label="Solo de Vibes", type="break", bars=16,
                      focus=["vibraphone"], active=["vibraphone", "rhodes", "pad"],
                      drums="light"),
        model.Section(id="eco", label="Eco", type="break", bars=8,
                      focus=["vibraphone"], active=["vibraphone", "pad"], drums="air"),
        model.Section(id="outro", label="Outro", type="outro", bars=8, drums="air",
                      focus=["vibraphone"], active=["vibraphone", "rhodes", "pad"]),
    ]
    p.harmony_sections = {
        "intro": model.HarmonySection(mode="guided", numerals="i - III"),
        "solo": model.HarmonySection(mode="guided", numerals="i - VI - III - VII"),
        "eco": model.HarmonySection(mode="guided", numerals="iv - i"),
        "outro": model.HarmonySection(mode="guided", numerals="i - VI"),
    }
    p.notes = "Demo 2: vibraphone protagonista con espacios obligatorios; el resto automático."
    return p


def demo_3_sax_rhodes_espacios():
    """3. Sax + Rhodes con espacios (config clásica del ecosistema)."""
    p = model.new_project("Sax y Rhodes en el Puro")
    p.pid = "demo_3_sax_rhodes_espacios"
    p.decisions.update({
        "identity": model.decision("fixed", "dark_triphop"),
        "mood": model.decision("fixed", "dark"),
        "key": model.decision("fixed", "C minor"),
        "language": model.decision("fixed", "hybrid"),
        "bpm": model.decision("fixed", 82),
        "harmony_mode": model.decision("fixed", "guided"),
        "spaces": model.decision("fixed", "suggested"),
    })
    p.instruments["sax_tenor"] = model.InstrumentDecision(role="protagonist")
    p.instruments["rhodes"] = model.InstrumentDecision(role="support")
    p.instruments["vibraphone"] = model.InstrumentDecision(role="off")
    p.instruments["pad"] = model.InstrumentDecision(role="support")
    p.sections = [
        model.Section(id="intro", label="Intro", type="intro", bars=8, drums="air",
                      focus=["rhodes", "pad"]),
        model.Section(id="verso_1", label="Verse 1", type="verse", bars=16,
                      focus=["sax_tenor", "drums"]),
        model.Section(id="puente_aire", label="Puente de Aire", type="bridge", bars=8,
                      active=["sax_tenor", "rhodes", "pad"], drums="air",
                      focus=["rhodes"]),
        model.Section(id="verso_2", label="Verse 2", type="verse", bars=16,
                      focus=["sax_tenor", "drums"]),
        model.Section(id="outro", label="Outro", type="outro", bars=8, drums="air",
                      focus=["rhodes"], final=True),
    ]
    p.harmony_sections = {
        "intro": model.HarmonySection(mode="guided", numerals="i - bVI"),
        "verso_1": model.HarmonySection(mode="guided", numerals="i - iim7b5 - bVI - V7"),
        "puente_aire": model.HarmonySection(mode="guided", numerals="bVI - bVII"),
        "verso_2": model.HarmonySection(mode="guided", numerals="i - i - bVI - bVII - i - i - bVI - V7:2"),
        "outro": model.HarmonySection(mode="guided", numerals="i - bVI"),
    }
    p.notes = "Demo 3: sax protagonista, Rhodes acompañante, vibráfono fuera, espacios de aire."
    return p


def demo_4_estructura_personalizada():
    """4. Canción con estructura personalizada y progresión por sección
    (el ejemplo EXACTO de la misión §4/§5)."""
    p = model.new_project("Preludio Para Letras")
    p.pid = "demo_4_estructura_personalizada"
    p.decisions.update({
        "identity": model.decision("fixed", "dark_triphop"),
        "mood": model.decision("fixed", "melancholic"),
        "key": model.decision("fixed", "C major"),
        "harmony_mode": model.decision("fixed", "guided"),
        "harmonic_rhythm_bars": model.decision("fixed", 1),
        "accessibility": model.decision("fixed", "commercial"),
    })
    p.sections = [
        model.Section(id="intro", label="Intro", type="intro", bars=4),
        model.Section(id="verso_1", label="Verse 1", type="verse", bars=16),
        model.Section(id="pre", label="Pre-Chorus", type="pre_chorus", bars=8),
        model.Section(id="verso_2", label="Verse 2", type="verse", bars=16),
        model.Section(id="estribillo", label="Chorus", type="chorus", bars=16, loop_bars=8),
        model.Section(id="preludio", label="Preludio", type="break", bars=8,
                      active=["rhodes", "pad", "vibraphone"], drums="light"),
        model.Section(id="verso_3", label="Verse 3", type="verse", bars=16),
        model.Section(id="estribillo_2", label="Chorus Final", type="chorus", bars=16,
                      loop_bars=8, final=True),
        model.Section(id="puente", label="Bridge", type="bridge", bars=8),
        model.Section(id="outro", label="Outro", type="outro", bars=8),
    ]
    progresion_mision = {
        "intro": "I - III - vi - V",
        "verso_1": "I - III - vi - V",
        "pre": "IV - I - vi - V",
        "verso_2": "I - III - vi - V",
        "estribillo": "IV - I - vi - V",
        "preludio": "vi - IV - I - V",
        "verso_3": "I - III - vi - V",
        "estribillo_2": "IV - I - vi - V",
        "puente": "IV - I - vi - V",
        "outro": "I - III - vi - V",
    }
    for sid, num in progresion_mision.items():
        p.harmony_sections[sid] = model.HarmonySection(mode="guided", numerals=num)
    p.notes = ("Demo 4: estructura de 10 secciones con nombres visibles y las progresiones "
               "por sección del documento de misión (I-III-vi-V → C-Em-Am-G). Pensada para escribir letras.")
    return p


def demo_5_restricciones_parciales():
    """5. Restricciones parcialmente definidas: solo 4 decisiones fijadas."""
    p = model.new_project("Cuatro Decisiones")
    p.pid = "demo_5_restricciones_parciales"
    p.decisions.update({
        "identity": model.decision("fixed", "dark_triphop"),
        "protagonist": model.decision("fixed", "sax_tenor"),
        "mood": model.decision("fixed", "tense"),
        "spaces": model.decision("fixed", "suggested"),
        # key, bpm, lenguaje, accesibilidad, ending... → automáticos
    })
    p.instruments["sax_tenor"] = model.InstrumentDecision(role="protagonist")
    p.sections = []          # estructura automática del mood
    p.notes = "Demo 5: solo 4 restricciones fijadas; todo lo demás lo decide Composer con coherencia."
    return p


DEMOS = [
    ("demo_1_totalmente_automatica", demo_1_totalmente_automatica, 2026),
    ("demo_2_solo_vibraphone", demo_2_solo_vibraphone, 2026),
    ("demo_3_sax_rhodes_espacios", demo_3_sax_rhodes_espacios, 2026),
    ("demo_4_estructura_personalizada", demo_4_estructura_personalizada, 2026),
    ("demo_5_restricciones_parciales", demo_5_restricciones_parciales, 2026),
]


def generar(dmd_path, manifest):
    PROFILES.mkdir(parents=True, exist_ok=True)
    resumen = {}
    for nombre, builder_fn, seed in DEMOS:
        p = builder_fn()
        r = engine.compose(p, dmd_path, manifest, seed_override=seed, save=False, validate=True)
        if not r.get("ok"):
            print(f"[ERROR] {nombre}: {r.get('errores')}")
            sys.exit(1)
        d = PROFILES / nombre
        d.mkdir(exist_ok=True)
        store.atomic_write_json(d / "proyecto.json", p.to_dict())
        store.atomic_write_json(d / "doc.json", r["doc"])
        store.atomic_write_json(d / "song_map.json", r["song_map"])
        store.atomic_write_text(d / "song_map.csv", r["song_map_csv"])
        gen = {
            "nombre": nombre, "seed": seed,
            "sha256_doc": store.sha256_file(d / "doc.json"),
            "sha256_song_map": store.sha256_file(d / "song_map.json"),
            "validacion": {"errores": r["validacion"]["errores"],
                           "avisos": [list(a) for a in r["validacion"]["avisos"]],
                           "e3xx": r["validacion"].get("e3xx", [])},
            "compilado": {"total_bars": r["compilado"]["total_bars"],
                          "target_schema": r["compilado"]["target_schema"]},
            "decisiones": {"fijadas": {k: v.get("value") for k, v in p.decisions.items()
                                       if v.get("mode") == "fixed"},
                           "automaticas": {k: v for k, v in r["log"]
                                           and {l["axis"]: l["valor"] for l in r["log"]
                                                if l["estado"] == "auto"}.items()},
                           "log": r["log"]},
        }
        store.atomic_write_json(d / "generacion.json", gen)
        av = [a[0] for a in r["validacion"]["avisos"]]
        print(f"[OK] {nombre}: {r['compilado']['total_bars']} compases · "
              f"doc {gen['sha256_doc'][:12]} · avisos W: {av if av else 'ninguno'}")
        resumen[nombre] = gen["sha256_doc"]
    return resumen


def verificar():
    ok = True
    for nombre, _, seed in DEMOS:
        f = PROFILES / nombre / "generacion.json"
        if not f.exists():
            print(f"[FALTA] {nombre}")
            ok = False
            continue
        g = json.loads(f.read_text(encoding="utf-8"))
        actual = store.sha256_file(PROFILES / nombre / "doc.json")
        if actual != g["sha256_doc"]:
            print(f"[DIFIERE] {nombre}: {actual[:12]} != {g['sha256_doc'][:12]}")
            ok = False
        else:
            print(f"[OK] {nombre}: {actual[:12]} (reproducible)")
    return ok


def main():
    if "--verificar" in sys.argv:
        sys.exit(0 if verificar() else 1)
    dmd = bridge.discover_dmd(store.DATA_DIR, None)
    manifest = MF.get_manifest(dmd, store.DATA_DIR, refresh=False)
    if not manifest.get("ok"):
        print("sin manifiesto de capacidades: ejecuta primero check.bat")
        sys.exit(1)
    print(f"DMD: {dmd} · {MF.fingerprint_of(manifest)}")
    generar(dmd, manifest)


if __name__ == "__main__":
    main()
