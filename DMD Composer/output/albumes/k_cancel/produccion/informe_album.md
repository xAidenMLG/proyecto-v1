# Informe de álbum — K Cancel

Generado: 2026-11-11T08:27:07 · esquema dmd-album-informe/1

**Pistas:** 3 · **OK:** 3 · **fallo:** 0 · **no ejecutadas:** 0 · **duración total:** 525.7 s (~8.8 min)

| # | Pista | Perfil | Seed | Armonía | Tonalidad | BPM | Comp. | Dur s | SHA256(16) | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | track01 | atmospheric | 841749 | — | C minor | 71 | 60 | 202.8 | 045bebcda0b7467c | ok |
| 2 | track02 | full | 635379 | — | D minor | 92 | 56 | 146.1 | 5aa34e889d16ede6 | ok |
| 3 | track03 | atmospheric | 403651 | — | E minor | 76 | 56 | 176.8 | 9bc2bd44663bf1b3 | ok |

## Diversidad y coherencia (métricas técnicas)

- Distribución de perfiles: {'atmospheric': 2, 'full': 1}
- Exceso de perfil (> 40%): [{'perfil': 'atmospheric', 'cuenta': 2, 'frac': 0.667}]
- Consecutivas idénticas (perfil+tonalidad+BPM): ninguna
- Ventanas sin respiro: ninguna
- Duplicados exactos (SHA256): ninguno
- Similares sospechosos (Jaccard ≥ 0.85): ninguno
- Identidad del álbum: dark_triphop (consistente)
- Tonalidades: C minor, D minor, E minor
- BPM: 71, 76, 92 (referencia 76–92)

## Avisos de planificación

- W-A4: el perfil 'atmospheric' cubre 2/3 pistas (> 40%) — perfiles explícitos del compositor: se respetan
- W-A7: 'track01' con BPM 71 fuera del rango de referencia 76–92 (Dark Trip Hop)

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
python3 -m album producir /home/z/my-project/DMD_Composer/output/albumes/k_cancel/produccion/album.json --out /home/z/my-project/DMD_Composer/output/albumes/k_cancel/produccion --forzar

# una pista, verificada por hash
python3 scripts/produce.py /home/z/my-project/DMD_Composer/output/albumes/k_cancel/produccion/01_track01/doc.json --production atmospheric --seed 841749 --out /home/z/my-project/DMD_Composer/output/albumes/k_cancel/produccion/01_track01 --verify 045bebcda0b7467c9de3c47a0ab1b1a9a518dc76f53c1442962dfffcb0ace48c
```

Manifiesto completo (config efectiva, hashes y comandos por pista): `manifiesto.json` · estado de ejecución: `estado.json`.
