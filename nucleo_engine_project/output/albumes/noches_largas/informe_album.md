# Informe de álbum — Noches Largas

Generado: 2026-11-09T06:06:47 · esquema dmd-album-informe/1

**Pistas:** 13 · **OK:** 13 · **fallo:** 0 · **no ejecutadas:** 0 · **duración total:** 1669.6 s (~27.8 min)

| # | Pista | Perfil | Seed | Armonía | Tonalidad | BPM | Comp. | Dur s | SHA256(16) | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | medianoche_puerto | sax | 2026 | — | F# minor | 78 | 60 | 184.6 | 41058bc61dd40c03 | ok |
| 2 | calles_de_neon | full | 2026 | familiar_pop (subtle) | A minor | 92 | 36 | 93.9 | 07b97c86a1e00cd3 | ok |
| 3 | habitacion_314 | atmospheric | 2026 | melancholic (medium) | G minor | 80 | 64 | 192.0 | 7252a5953f2a2993 | ok |
| 4 | bruma_dorada | original | 3504 | — | Bb minor | 80 | 40 | 120.0 | 7573247183da19c1 | ok |
| 5 | casa_de_espejos | sax_rhodes | 2026 | soulful (medium) | C minor | 84 | 44 | 125.7 | 75cb88be775105d0 | ok |
| 6 | neblina_alta | drums | 3706 | tension_release (subtle) | E minor | 76 | 36 | 113.7 | c44c010b2665b1eb | ok |
| 7 | viaducto_sur | full | 3807 | CINE01 (medium) | D minor | 90 | 44 | 117.3 | bd123097c269dec9 | ok |
| 8 | habitacion_vacia | atmospheric | 3908 | dream_pop (subtle) | F minor | 82 | 40 | 117.1 | 15e9399ba5783030 | ok |
| 9 | asfalto_humedo | sax_vibes | 4009 | alternative (subtle) | A minor | 86 | 44 | 122.8 | 2366c75942dca0c1 | ok |
| 10 | portico_sur | original | 4110 | — | D minor | 79 | 36 | 109.4 | 6797453d959b0636 | ok |
| 11 | nocturno_terminal | full | 2026 | dark_cinematic (medium) | D minor | 86 | 52 | 145.1 | cd3c7303db17d662 | ok |
| 12 | marea_baja | sax | 4312 | emotional_resolution (subtle) | F minor | 84 | 40 | 114.3 | bd2208f4460e715b | ok |
| 13 | ultimo_metro | atmospheric | 4413 | familiarity_auto (subtle) | C minor | 76 | 36 | 113.7 | 9ccab4118229e2e7 | ok |

## Diversidad y coherencia (métricas técnicas)

- Distribución de perfiles: {'sax': 2, 'full': 3, 'atmospheric': 3, 'original': 2, 'sax_rhodes': 1, 'drums': 1, 'sax_vibes': 1}
- Exceso de perfil (> 40%): ninguno
- Consecutivas idénticas (perfil+tonalidad+BPM): ninguna
- Ventanas sin respiro: ninguna
- Duplicados exactos (SHA256): ninguno
- Similares sospechosos (Jaccard ≥ 0.85): ninguno
- Curva de energía objetivo: [0.48, 0.59, 0.49, 0.42, 0.46, 0.39, 0.48, 0.36, 0.48, 0.33, 0.5, 0.46, 0.34]
- Curva de energía real:    [0.475, 0.59, 0.495, 0.424, 0.456, 0.387, 0.485, 0.359, 0.476, 0.327, 0.5, 0.459, 0.343]
- Desviación máxima: 0.01
- Identidad del álbum: dark_triphop (consistente)
- Tonalidades: A minor, Bb minor, C minor, D minor, E minor, F minor, F# minor, G minor
- BPM: 76, 78, 79, 80, 82, 84, 86, 90, 92 (referencia 76–92)

## Avisos de planificación

- W-A3: la pista 'ultimo_metro' usa familiarity_auto declarada EXPLÍCITAMENTE en el spec (el sistema nunca la activa solo)

## Técnico vs musical

Medido automáticamente (técnico):

- duplicados exactos por SHA256 del MIDI
- similitud material por Jaccard de huellas (umbral 0.85)
- distribución y fracción de perfiles
- variedad en consecutivas (perfil+tonalidad+BPM)
- ventanas de respiro
- rango de BPM de referencia
- distancia tonal entre consecutivas
- adherencia a curva de energía
- compliance del validador de forge por pista

**Requiere escucha humana (pendiente de validación del usuario):**

- coherencia de identidad audible entre pistas
- fatiga de densidad o saturación de perfiles
- naturalidad de las transiciones entre pistas (orden de reproducción)
- calidad de las progresiones familiares activadas (si las hay)
- equilibrio sax/Rhodes/vibes/batería en el conjunto

## Reproducir

```bash
# álbum completo (regenera todo)
python3 -m album producir /home/z/my-project/nucleo_engine_project/albumes/noches_largas/album.json --out output/albumes/noches_largas --forzar

# una pista, verificada por hash
python3 scripts/produce.py output/albumes/noches_largas/01_medianoche_puerto/doc.json --production sax --seed 2026 --out output/albumes/noches_largas/01_medianoche_puerto --verify 41058bc61dd40c030f6b45873041cae76c789046e90c16b51a30a1eced67c315
```

Manifiesto completo (config efectiva, hashes y comandos por pista): `manifiesto.json` · estado de ejecución: `estado.json`.
