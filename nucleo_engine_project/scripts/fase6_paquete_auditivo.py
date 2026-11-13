#!/usr/bin/env python3
"""FASE 6 — ETAPA G: paquete auditivo para validación del usuario.

Ensambla en output/fase6_paquete_auditivo/ una selección PEQUEÑA de MIDIs con
guía de escucha: referencias doradas (copias verificadas por hash) + resultados
de generalización en composiciones nuevas. Sin FluidSynth en este entorno, no
hay WAV: ver README del paquete para reproducir en Windows.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / 'output' / 'fase5_comparativos'
GEN = ROOT / 'output' / 'generalizacion_fase6'
OUT = ROOT / 'output' / 'fase6_paquete_auditivo'

# (origen_relativo, nombre_paquete, composición, perfil, seed, qué comprobar)
SELECCION = [
    ("fase5_comparativos/01_original.mid", "A1_nocturno_original.mid",
     "Nocturno Terminal (D minor, 86)", "original", 2026,
     "REFERENCIA: composición base aprobada (4 iteraciones Suno). Todo se compara contra esto."),
    ("fase5_comparativos/07_full.mid", "A2_nocturno_full.mid",
     "Nocturno Terminal (D minor, 86)", "full", 2026,
     "REFERENCIA: los 4 motores con protagonismo distribuido; músicos con roles propios."),
    ("fase5_comparativos/08_variation_atmospheric.mid", "A3_nocturno_atmospheric.mid",
     "Nocturno Terminal (D minor, 86)", "atmospheric", 2026,
     "REFERENCIA: más libertad instrumental, breakdowns, improvisación controlada."),
    ("fase5_comparativos/03_sax_rhodes.mid", "A4_nocturno_sax_rhodes.mid",
     "Nocturno Terminal (D minor, 86)", "sax_rhodes", 2026,
     "REFERENCIA: diálogo sax↔Rhodes aprobado (para comparar con B2)."),
    ("generalizacion_fase6/casa_de_espejos/original.mid", "B1_casa_espejos_original.mid",
     "Casa de Espejos (C minor, 84)", "original", 5150,
     "NUEVA composición, camino base: sin sax en focus. ¿Se sostiene el universo sin sax protagonista?"),
    ("generalizacion_fase6/casa_de_espejos/sax_rhodes.mid", "B2_casa_espejos_sax_rhodes.mid",
     "Casa de Espejos (C minor, 84)", "sax_rhodes", 5150,
     "Diálogo sax↔Rhodes en una composición DISTINTA: ¿el Rhodes responde igual de bien con otra armonía/estructura?"),
    ("generalizacion_fase6/medianoche_puerto_nuevo/full.mid", "C1_medianoche_full.mid",
     "Medianoche en Puerto Nuevo (F# minor, 78)", "full", 3113,
     "Groove lento (78 BPM), ritmo armónico 2 compases, secciones largas: ¿mantienen los motores el espacio y la respiración?"),
    ("generalizacion_fase6/habitacion_314/atmospheric.mid", "D1_habitacion_atmospheric.mid",
     "Habitación 314 (G minor, 80)", "atmospheric", 4104,
     "Forma larga (64 compases), tensión alta, break y tape_stop: ¿los breakdowns funcionan y se recupera el groove?"),
    ("generalizacion_fase6/calles_de_neon/drums.mid", "E1_calles_neon_drums.mid",
     "Calles de Neón (A minor, 92)", "drums", 9021,
     "Batería sobre material melódico ESCRITO y tempo rápido: ¿groove sin competir con el bajo ni sonar mecánico?"),
]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    filas, hashes = [], {}
    for rel, nombre, comp, perfil, seed, que in SELECCION:
        src = ROOT / 'output' / rel
        if not src.is_file():
            print("FALTA:", src)
            return 1
        dst = OUT / nombre
        shutil.copyfile(src, dst)
        sha = _sha(dst)
        hashes[nombre] = {"sha256": sha, "origen": rel,
                          "copia_verificada": sha == _sha(src)}
        filas.append((nombre, comp, perfil, seed, sha, que))
        print("%-38s %s" % (nombre, sha[:16]))
    # README
    l = ["# FASE 6 — Paquete auditivo (validación del usuario)", "",
         "Selección mínima para validar la GENERALIZACIÓN de los motores fuera de "
         "«Nocturno Terminal». Los archivos A* son COPIAS verificadas por hash de las "
         "referencias doradas de FASE 5 (`output/fase5_comparativos/GOLDEN.md`). "
         "Los archivos B–E son resultados NUEVOS en composiciones distintas.", "",
         "## Cómo escuchar (Windows)", "",
         "1. FluidSynth con tu soundfont:",
         "   `fluidsynth -ni C:\\ruta\\soundfont.sf2 ARCHIVO.mid -F ARCHIVO.wav -r 44100`",
         "   (programas GM ya embebidos: sax 66, Rhodes 4, vibes 11, bass 38, pad 91)",
         "2. O abrir los .mid en tu DAW habitual.", "",
         "## Qué evaluar (solo tú puedes decidirlo)", "",
         "- ¿Se reconoce el MISMO universo musical (identidad) en composiciones distintas?",
         "- ¿El sax desarrolla material propio en cada canción o repite fórmulas?",
         "- ¿El Rhodes sigue subordinado y musical en otra armonía?",
         "- ¿La batería mantiene groove y transiciones sin mecánica?",
         "- ¿Los espacios/silencios siguen respirando?", "",
         "## Archivos", "",
         "| Archivo | Composición | Perfil | Seed | SHA256(16) | Qué comprobar |",
         "|---|---|---|---|---|---|"]
    for nombre, comp, perfil, seed, sha, que in filas:
        l.append("| %s | %s | %s | %d | %s | %s |" % (nombre, comp, perfil, seed, sha[:16], que))
    l.append("")
    l.append("Config exacta y evidencia de cada run: `output/generalizacion_fase6/<composicion>/` "
             "(config_<perfil>.json, evidencia_<perfil>.json). Comando de regeneración "
             "exacta en cada evidencia.json.")
    (OUT / 'README.md').write_text('\n'.join(l) + '\n', encoding='utf-8')
    (OUT / 'hashes.json').write_text(
        json.dumps(hashes, ensure_ascii=False, indent=2), encoding='utf-8')
    print("\nPaquete en", OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
