# FASE 6 — Paquete auditivo (validación del usuario)

Selección mínima para validar la GENERALIZACIÓN de los motores fuera de «Nocturno Terminal». Los archivos A* son COPIAS verificadas por hash de las referencias doradas de FASE 5 (`output/fase5_comparativos/GOLDEN.md`). Los archivos B–E son resultados NUEVOS en composiciones distintas.

## Cómo escuchar (Windows)

1. FluidSynth con tu soundfont:
   `fluidsynth -ni C:\ruta\soundfont.sf2 ARCHIVO.mid -F ARCHIVO.wav -r 44100`
   (programas GM ya embebidos: sax 66, Rhodes 4, vibes 11, bass 38, pad 91)
2. O abrir los .mid en tu DAW habitual.

## Qué evaluar (solo tú puedes decidirlo)

- ¿Se reconoce el MISMO universo musical (identidad) en composiciones distintas?
- ¿El sax desarrolla material propio en cada canción o repite fórmulas?
- ¿El Rhodes sigue subordinado y musical en otra armonía?
- ¿La batería mantiene groove y transiciones sin mecánica?
- ¿Los espacios/silencios siguen respirando?

## Archivos

| Archivo | Composición | Perfil | Seed | SHA256(16) | Qué comprobar |
|---|---|---|---|---|---|
| A1_nocturno_original.mid | Nocturno Terminal (D minor, 86) | original | 2026 | 046c94b1599e34fe | REFERENCIA: composición base aprobada (4 iteraciones Suno). Todo se compara contra esto. |
| A2_nocturno_full.mid | Nocturno Terminal (D minor, 86) | full | 2026 | 3930cadc34ec3bcb | REFERENCIA: los 4 motores con protagonismo distribuido; músicos con roles propios. |
| A3_nocturno_atmospheric.mid | Nocturno Terminal (D minor, 86) | atmospheric | 2026 | 864b9302591f2655 | REFERENCIA: más libertad instrumental, breakdowns, improvisación controlada. |
| A4_nocturno_sax_rhodes.mid | Nocturno Terminal (D minor, 86) | sax_rhodes | 2026 | 25a6f2234cab102e | REFERENCIA: diálogo sax↔Rhodes aprobado (para comparar con B2). |
| B1_casa_espejos_original.mid | Casa de Espejos (C minor, 84) | original | 5150 | 44763e9df984dcb3 | NUEVA composición, camino base: sin sax en focus. ¿Se sostiene el universo sin sax protagonista? |
| B2_casa_espejos_sax_rhodes.mid | Casa de Espejos (C minor, 84) | sax_rhodes | 5150 | c0d6b9558c6ddc74 | Diálogo sax↔Rhodes en una composición DISTINTA: ¿el Rhodes responde igual de bien con otra armonía/estructura? |
| C1_medianoche_full.mid | Medianoche en Puerto Nuevo (F# minor, 78) | full | 3113 | 32199acc254a2eef | Groove lento (78 BPM), ritmo armónico 2 compases, secciones largas: ¿mantienen los motores el espacio y la respiración? |
| D1_habitacion_atmospheric.mid | Habitación 314 (G minor, 80) | atmospheric | 4104 | 7bed92325defd464 | Forma larga (64 compases), tensión alta, break y tape_stop: ¿los breakdowns funcionan y se recupera el groove? |
| E1_calles_neon_drums.mid | Calles de Neón (A minor, 92) | drums | 9021 | 430b0a9a6e580a0a | Batería sobre material melódico ESCRITO y tempo rápido: ¿groove sin competir con el bajo ni sonar mecánico? |

Config exacta y evidencia de cada run: `output/generalizacion_fase6/<composicion>/` (config_<perfil>.json, evidencia_<perfil>.json). Comando de regeneración exacta en cada evidencia.json.
