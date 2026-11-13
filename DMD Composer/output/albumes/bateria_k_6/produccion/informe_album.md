# Informe de álbum — Bateria K

Generado: 2026-11-11T08:40:24 · esquema dmd-album-informe/1

**Pistas:** 2 · **OK:** 2 · **fallo:** 0 · **no ejecutadas:** 0 · **duración total:** 372.7 s (~6.2 min)

| # | Pista | Perfil | Seed | Armonía | Tonalidad | BPM | Comp. | Dur s | SHA256(16) | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | track01 | full | 220584 | — | F minor | 80 | 64 | 192.0 | 346a7d607428bd9b | ok |
| 2 | track02 | full | 528685 | — | D minor | 85 | 64 | 180.7 | b3f986eaf1872208 | ok |

## Diversidad y coherencia (métricas técnicas)

- Distribución de perfiles: {'full': 2}
- Exceso de perfil (> 40%): [{'perfil': 'full', 'cuenta': 2, 'frac': 1.0}]
- Consecutivas idénticas (perfil+tonalidad+BPM): [{'pistas': ['track01', 'track02'], 'motivo': 'perfil repetido consecutivo'}]
- Ventanas sin respiro: [['track01', 'track02']]
- Duplicados exactos (SHA256): ninguno
- Similares sospechosos (Jaccard ≥ 0.85): ninguno
- Identidad del álbum: dark_triphop (consistente)
- Tonalidades: D minor, F minor
- BPM: 80, 85 (referencia 76–92)

## Avisos de planificación

- W-A4: el perfil 'full' cubre 2/2 pistas (> 40%) — perfiles explícitos del compositor: se respetan
- W-A5: ventana track01–track02 sin pista de respiro (original/atmospheric)
- W-A6: consecutivas sospechosas track01<->track02 (perfil repetido consecutivo)

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
python3 -m album producir /home/z/my-project/DMD_Composer/output/albumes/bateria_k_6/produccion/album.json --out /home/z/my-project/DMD_Composer/output/albumes/bateria_k_6/produccion --forzar

# una pista, verificada por hash
python3 scripts/produce.py /home/z/my-project/DMD_Composer/output/albumes/bateria_k_6/produccion/01_track01/doc.json --production full --seed 220584 --out /home/z/my-project/DMD_Composer/output/albumes/bateria_k_6/produccion/01_track01 --verify 346a7d607428bd9b5e1c41c713a4ae58f7e103a3cc07b877cdc720a0ed3e2eaf
```

Manifiesto completo (config efectiva, hashes y comandos por pista): `manifiesto.json` · estado de ejecución: `estado.json`.
