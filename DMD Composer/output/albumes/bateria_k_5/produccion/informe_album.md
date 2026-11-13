# Informe de álbum — Bateria K

Generado: 2026-11-11T08:40:22 · esquema dmd-album-informe/1

**Pistas:** 2 · **OK:** 2 · **fallo:** 0 · **no ejecutadas:** 0 · **duración total:** 370.7 s (~6.2 min)

| # | Pista | Perfil | Seed | Armonía | Tonalidad | BPM | Comp. | Dur s | SHA256(16) | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | track01 | full | 203294 | — | C minor | 82 | 64 | 187.3 | 9d5c81aea72252d4 | ok |
| 2 | track02 | sax_vibes | 651837 | — | E minor | 89 | 68 | 183.4 | fe4cf523dd8ce3d6 | ok |

## Diversidad y coherencia (métricas técnicas)

- Distribución de perfiles: {'full': 1, 'sax_vibes': 1}
- Exceso de perfil (> 40%): [{'perfil': 'full', 'cuenta': 1, 'frac': 0.5}, {'perfil': 'sax_vibes', 'cuenta': 1, 'frac': 0.5}]
- Consecutivas idénticas (perfil+tonalidad+BPM): ninguna
- Ventanas sin respiro: [['track01', 'track02']]
- Duplicados exactos (SHA256): ninguno
- Similares sospechosos (Jaccard ≥ 0.85): ninguno
- Identidad del álbum: dark_triphop (consistente)
- Tonalidades: C minor, E minor
- BPM: 82, 89 (referencia 76–92)

## Avisos de planificación

- W-A4: el perfil 'full' cubre 1/2 pistas (> 40%) — perfiles explícitos del compositor: se respetan
- W-A4: el perfil 'sax_vibes' cubre 1/2 pistas (> 40%) — perfiles explícitos del compositor: se respetan
- W-A5: ventana track01–track02 sin pista de respiro (original/atmospheric)

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
python3 -m album producir /home/z/my-project/DMD_Composer/output/albumes/bateria_k_5/produccion/album.json --out /home/z/my-project/DMD_Composer/output/albumes/bateria_k_5/produccion --forzar

# una pista, verificada por hash
python3 scripts/produce.py /home/z/my-project/DMD_Composer/output/albumes/bateria_k_5/produccion/01_track01/doc.json --production full --seed 203294 --out /home/z/my-project/DMD_Composer/output/albumes/bateria_k_5/produccion/01_track01 --verify 9d5c81aea72252d4e234ac583d908b17e91a42cfebfd2afb4df1daa0d054a6b5
```

Manifiesto completo (config efectiva, hashes y comandos por pista): `manifiesto.json` · estado de ejecución: `estado.json`.
