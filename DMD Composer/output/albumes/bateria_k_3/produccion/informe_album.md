# Informe de álbum — Bateria K

Generado: 2026-11-11T08:27:14 · esquema dmd-album-informe/1

**Pistas:** 2 · **OK:** 2 · **fallo:** 0 · **no ejecutadas:** 0 · **duración total:** 328.1 s (~5.5 min)

| # | Pista | Perfil | Seed | Armonía | Tonalidad | BPM | Comp. | Dur s | SHA256(16) | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | track01 | full | 861799 | — | F minor | 87 | 56 | 154.5 | 71bdf6a506101295 | ok |
| 2 | track02 | sax_vibes | 760125 | — | D minor | 94 | 68 | 173.6 | c284c3567c22e911 | ok |

## Diversidad y coherencia (métricas técnicas)

- Distribución de perfiles: {'full': 1, 'sax_vibes': 1}
- Exceso de perfil (> 40%): [{'perfil': 'full', 'cuenta': 1, 'frac': 0.5}, {'perfil': 'sax_vibes', 'cuenta': 1, 'frac': 0.5}]
- Consecutivas idénticas (perfil+tonalidad+BPM): ninguna
- Ventanas sin respiro: [['track01', 'track02']]
- Duplicados exactos (SHA256): ninguno
- Similares sospechosos (Jaccard ≥ 0.85): ninguno
- Identidad del álbum: dark_triphop (consistente)
- Tonalidades: D minor, F minor
- BPM: 87, 94 (referencia 76–92)

## Avisos de planificación

- W-A4: el perfil 'full' cubre 1/2 pistas (> 40%) — perfiles explícitos del compositor: se respetan
- W-A4: el perfil 'sax_vibes' cubre 1/2 pistas (> 40%) — perfiles explícitos del compositor: se respetan
- W-A5: ventana track01–track02 sin pista de respiro (original/atmospheric)
- W-A7: 'track02' con BPM 94 fuera del rango de referencia 76–92 (Dark Trip Hop)

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
python3 -m album producir /home/z/my-project/DMD_Composer/output/albumes/bateria_k_3/produccion/album.json --out /home/z/my-project/DMD_Composer/output/albumes/bateria_k_3/produccion --forzar

# una pista, verificada por hash
python3 scripts/produce.py /home/z/my-project/DMD_Composer/output/albumes/bateria_k_3/produccion/01_track01/doc.json --production full --seed 861799 --out /home/z/my-project/DMD_Composer/output/albumes/bateria_k_3/produccion/01_track01 --verify 71bdf6a50610129546e773cd1d05c5dfa44327d16dd3faa5bfba9207b172cc9d
```

Manifiesto completo (config efectiva, hashes y comandos por pista): `manifiesto.json` · estado de ejecución: `estado.json`.
