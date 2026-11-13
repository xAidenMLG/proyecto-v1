# Informe de álbum — Bateria K

Generado: 2026-11-11T08:27:12 · esquema dmd-album-informe/1

**Pistas:** 2 · **OK:** 2 · **fallo:** 0 · **no ejecutadas:** 0 · **duración total:** 302.2 s (~5.0 min)

| # | Pista | Perfil | Seed | Armonía | Tonalidad | BPM | Comp. | Dur s | SHA256(16) | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | track01 | drums | 296522 | — | B minor | 93 | 52 | 134.2 | b25bd019ea7920cd | ok |
| 2 | track02 | full | 346470 | — | E minor | 80 | 56 | 168.0 | e33fdd6e8f18f826 | ok |

## Diversidad y coherencia (métricas técnicas)

- Distribución de perfiles: {'drums': 1, 'full': 1}
- Exceso de perfil (> 40%): [{'perfil': 'drums', 'cuenta': 1, 'frac': 0.5}, {'perfil': 'full', 'cuenta': 1, 'frac': 0.5}]
- Consecutivas idénticas (perfil+tonalidad+BPM): ninguna
- Ventanas sin respiro: [['track01', 'track02']]
- Duplicados exactos (SHA256): ninguno
- Similares sospechosos (Jaccard ≥ 0.85): ninguno
- Identidad del álbum: dark_triphop (consistente)
- Tonalidades: B minor, E minor
- BPM: 80, 93 (referencia 76–92)

## Avisos de planificación

- W-A4: el perfil 'drums' cubre 1/2 pistas (> 40%) — perfiles explícitos del compositor: se respetan
- W-A4: el perfil 'full' cubre 1/2 pistas (> 40%) — perfiles explícitos del compositor: se respetan
- W-A5: ventana track01–track02 sin pista de respiro (original/atmospheric)
- W-A7: 'track01' con BPM 93 fuera del rango de referencia 76–92 (Dark Trip Hop)

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
python3 -m album producir /home/z/my-project/DMD_Composer/output/albumes/bateria_k_2/produccion/album.json --out /home/z/my-project/DMD_Composer/output/albumes/bateria_k_2/produccion --forzar

# una pista, verificada por hash
python3 scripts/produce.py /home/z/my-project/DMD_Composer/output/albumes/bateria_k_2/produccion/01_track01/doc.json --production drums --seed 296522 --out /home/z/my-project/DMD_Composer/output/albumes/bateria_k_2/produccion/01_track01 --verify b25bd019ea7920cd6df717446ed037302950f9e5757e85b66fa0ccfd1a085c2e
```

Manifiesto completo (config efectiva, hashes y comandos por pista): `manifiesto.json` · estado de ejecución: `estado.json`.
