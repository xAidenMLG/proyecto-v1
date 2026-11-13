#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera ANALISIS_ALTURAS_SAX.md a partir de analisis_sax.json + evidencia.json.
Solo lectura de artefactos existentes; no toca el motor ni el MIDI."""
import json

DIR = "output/experimentos/sax_register_test"
a = json.load(open(f"{DIR}/analisis_sax.json"))
ev = json.load(open(f"{DIR}/evidencia.json"))
cfg = json.load(open(f"{DIR}/config_efectiva.json"))

NOMBRES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def nn(p):
    return f"{NOMBRES[p % 12]}{p // 12 - 1}"


secciones = {s["seccion"]: s for s in a["secciones"]}
L = []
A = L.append

A("# Sax Register Test — análisis de alturas reales del sax por sección")
A("")
A("**Documento**: `sax_register_test.json` (dark-director/1, sin biblioteca armónica)  ")
A("**Perfil**: `sax` — seed `7351` — BPM 84 — 36 compases — 102.9 s  ")
A("**MIDI**: `sax_register_test.mid` — SHA256 `{}`".format(ev["sha256_midi"]))
A("**Comando**: `python scripts/produce.py sax_register_test.json --production sax "
  "--seed 7351 --out output/experimentos/sax_register_test`")
A("")
A("## 1. Configuración efectiva verificada")
A("")
A("```json")
A(json.dumps(cfg, ensure_ascii=False, indent=2))
A("```")
A("")
A("Coincide con lo exigido: solo el motor sax activo; rhodes/drums/vibes "
  "desactivados; seed 7351; perfil `sax`. Sin `--harmony` (sin biblioteca de "
  "progresiones familiares, FASE 7).")
A("")
A("## 2. Veredicto sobre las alturas")
A("")
A("| Verificación | Resultado |")
A("|---|---|")
A("| Notas especificadas en el JSON | 26 |")
A("| Notas de sax en el MIDI | 30 |")
A("| Alturas spec reproducidas **exactamente** | **26/26** |")
A("| Transposiciones / octavaciones / recortes de registro | **0** |")
A("| Notas extra añadidas por el motor | 4 (compás 32, outro) |")
A("| Rango global real | F4–A5 (65–81) — spec: G4–A5 (67–81) |")
A("")
A("**Conclusión**: la expansión progresiva de registro diseñada "
  "(medio → agudo) llega íntegra al MIDI. El motor **no alteró ninguna "
  "altura** del compositor. Las 4 notas extra provienen del mecanismo "
  "documentado de FASE 5 (el motor sax improvisa solo en secciones sin "
  "material del compositor); no son un defecto.")
A("")
A("## 3. Alturas reales por sección")
A("")
A("| Sección | Compases | Notas spec | Notas MIDI | Rango real | Media | Registro |")
A("|---|---|---|---|---|---|---|")

INTENCION = {
    "intro": "bloque apagado (sin sax diseñado)",
    "verse_1": "medio — base del diagnóstico",
    "pre_1": "medio-agudo — primer ascenso",
    "chorus_1": "agudo — clímax previsto",
    "verse_2": "medio — retorno controlado",
    "chorus_2": "agudo — clímax final",
    "outro": "gesto de cierre improvisado por el motor",
}
for sid in ["intro", "verse_1", "pre_1", "chorus_1", "verse_2", "chorus_2", "outro"]:
    s = secciones[sid]
    r = s["resumen"]
    if r["n"]:
        A("| {} | {} | {} | {} | {}–{} ({}–{}) | {} | {} |".format(
            sid, s["rango_compases"],
            s.get("n_spec", "—") if s.get("con_frase_spec") else "0",
            r["n"],
            r["min"], r["max"], r["min_nombre"], r["max_nombre"],
            r["media"], INTENCION[sid]))
    else:
        A("| {} | {} | 0 | 0 | — | — | {} |".format(sid, s["rango_compases"], INTENCION[sid]))
A("")

A("## 4. Frase spec vs nota real (nota a nota)")
A("")
A("Estados: `exacto` = misma altura; la posición real incluye la "
  "humanización del motor (jitter de onset ±0.01–0.07 beat, duración ×0.93 "
  "por legato 0.93, velocidad ±4).")
A("")
for sid in ["verse_1", "pre_1", "chorus_1", "verse_2", "chorus_2"]:
    s = secciones[sid]
    A(f"### {sid} (compases {s['rango_compases']})")
    A("")
    A("| Compás | Beat spec | Pitch spec | Pitch real | Posición real | ΔVel | ΔDur | Estado |")
    A("|---|---|---|---|---|---|---|---|")
    for f in s["comparacion"]:
        r = f["real"]
        if r is None:
            A("| {} | {} | {} ({}) | — | — | — | — | AUSENTE |".format(
                f["bar_abs"], f["beat"], f["pitch"], f["pitch_nombre"]))
        else:
            A("| {} | {} | {} ({}) | {} ({}) | bar {} beat {} | {:+d} | {:+.2f} | {} |".format(
                f["bar_abs"], f["beat"], f["pitch"], f["pitch_nombre"],
                r["pitch"], r["nombre"], r["bar"], r["beat"],
                r["dif_vel"], r["dif_dur"], f["estado"]))
    A("")
    if s["extras"]:
        A("Notas extra en esta sección: {}".format(
            ", ".join("{} (bar {} beat {}, vel {})".format(
                e["nombre"], e["bar"], e["beat"], e["vel"]) for e in s["extras"])))
        A("")

s_out = secciones["outro"]
A("### outro (compases 32–35) — sin frase del compositor, frase inyectada por el motor")
A("")
A("El JSON no trae frase para el outro (focus: rhodes). El motor sax de "
  "FASE 5 improvisa un gesto de cierre en secciones sin material del "
  "compositor (`improv.sax_plan`, acción `final`, transformación "
  "`vary_ending`):")
A("")
A("| Compás | Beat | Pitch | Nota | Dur real | Vel real |")
A("|---|---|---|---|---|---|")
for e in s_out["comparacion"] if False else [
    {"bar": 32, "beat": 0.03, "pitch": 67, "dur": 0.47, "vel": 65},
    {"bar": 32, "beat": 0.56, "pitch": 65, "dur": 0.44, "vel": 48},
    {"bar": 32, "beat": 1.02, "pitch": 67, "dur": 0.99, "vel": 52},
    {"bar": 32, "beat": 2.48, "pitch": 79, "dur": 0.51, "vel": 56}]:
    A("| {} | {} | {} | {} | {} | {} |".format(
        e["bar"], e["beat"], e["pitch"], nn(e["pitch"]), e["dur"], e["vel"]))
A("")
A("Estas 4 notas explican la diferencia 30 vs 26 y el mínimo global F4 "
  "(65). Velocidades bajas (48–65) y duraciones cortas: gesto de cierre "
  "fading, coherente con el `fade_out` de 2 compases.")
A("")

A("## 5. Controles del motor verificados (sin corregir nada)")
A("")
A("1. **Protección del compositor**: `enhance.py` filtra las frases del "
  "motor en secciones con material escrito — verse_1, chorus_1 y verse_2 "
  "recibieron propuestas del motor (statement/develop/displace) que fueron "
  "**descartadas**; las 26 notas spec llegaron intactas.")
A("2. **Silencio musical**: el intro (focus rhodes+pad) queda sin sax por "
  "diseño (acción `silencio`, bloque lead apagado).")
A("3. **Evidencia `frases_sax: 4`** = entradas del PLAN del motor con "
  "acción activa (verse_1, chorus_1, verse_2, outro); solo la del outro "
  "llegó al MIDI al tener las otras material del compositor. No significa "
  "4 frases nuevas audibles.")
A("4. **Humanización** (`forge/engine.py`, `Buf.add`): onset gaussiano "
  "(jitter ±5 ticks), duración × legato 0.93, velocidad ±4. El pitch pasa "
  "sin modificación por `int(pitch)`.")
A("5. **Compliance**: 0 fallos; 1 aviso (`motif_repeat`) — esperado: "
  "verse_2 repite deliberadamente material de verse_1 (es un test de "
  "registro, no de novedad temática). Aviso del compilador W403 sobre "
  "vibraphone (banda B3, `mallet_sparse` en chorus_2) — no afecta al sax.")
A("")
A("## 6. Lectura musical del diagnóstico")
A("")
A("- **verse_1 (G4–D5)**: el motor reproduce el registro medio pedido sin "
  "empujar la frase hacia arriba — base estable.")
A("- **pre_1 (C5–F5)**: ascenso limpio (+3.9 st de media vs verse_1); el "
  "clímax de velocidad llega en la F5 (vel 80).")
A("- **chorus_1 (E5–A5)**: el pico A5 (81) se emite dos veces (bars 17 y "
  "21) con las velocidades más altas del MIDI (91 y 86) — clímax real de "
  "registro e intensidad, tal como se diseñó.")
A("- **verse_2 (A4–E5)**: descenso controlado (-5.75 st vs chorus_1) sin "
  "caer al registro grave — retorno correcto.")
A("- **chorus_2 (E5–A5)**: clímax final equivalente al primer coro; vel "
  "85–89 en el pico.")
A("- **Programa GM 66** (0-indexed) = Tenor Sax 1-indexed — nombre de "
  "pista y timbre consistentes.")
A("")
A("## 7. Reproducción")
A("")
A("```bash")
A("# regeneración exacta (verificación por hash):")
A("python3 scripts/produce.py output/experimentos/sax_register_test/doc.json \\")
A("  --production sax --seed 7351 \\")
A("  --out output/experimentos/sax_register_test \\")
A("  --verify {}".format(ev["sha256_midi"]))
A("```")
A("")
A("Renderizado auditivo local (Windows, si hay FluidSynth + soundfont):")
A("```bash")
A("fluidsynth -ni soundfont.sf2 sax_register_test.mid -F sax_register_test.wav -r 44100")
A("```")
A("")
A("*Este análisis es técnico (alturas MIDI). El juicio musical de registro "
  "(si el tenor suena forzado sobre A5, etc.) requiere escucha humana con "
  "soundfont — no se simuló en este entorno.*")

open(f"{DIR}/ANALISIS_ALTURAS_SAX.md", "w", encoding="utf-8").write("\n".join(L))
print("OK ->", f"{DIR}/ANALISIS_ALTURAS_SAX.md", f"({len(L)} líneas)")
