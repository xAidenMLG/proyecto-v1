# Informe de álbum — K Cancel

Generado: 2026-11-11T08:40:26 · esquema dmd-album-informe/1

**Pistas:** 3 · **OK:** 3 · **fallo:** 0 · **no ejecutadas:** 0 · **duración total:** 597.0 s (~9.9 min)

| # | Pista | Perfil | Seed | Armonía | Tonalidad | BPM | Comp. | Dur s | SHA256(16) | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | track01 | sax_vibes | 558922 | — | E minor | 82 | 60 | 175.6 | f00be05b06591439 | ok |
| 2 | track02 | full | 289703 | — | B minor | 72 | 52 | 173.3 | 685d1d9eb269999f | ok |
| 3 | track03 | atmospheric | 133178 | — | G minor | 89 | 92 | 248.1 | a7520aadeda633b7 | ok |

## Diversidad y coherencia (métricas técnicas)

- Distribución de perfiles: {'sax_vibes': 1, 'full': 1, 'atmospheric': 1}
- Exceso de perfil (> 40%): ninguno
- Consecutivas idénticas (perfil+tonalidad+BPM): ninguna
- Ventanas sin respiro: ninguna
- Duplicados exactos (SHA256): ninguno
- Similares sospechosos (Jaccard ≥ 0.85): ninguno
- Identidad del álbum: dark_triphop (consistente)
- Tonalidades: B minor, E minor, G minor
- BPM: 72, 82, 89 (referencia 76–92)

## Avisos de planificación

- W-A7: 'track02' con BPM 72 fuera del rango de referencia 76–92 (Dark Trip Hop)

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
python3 -m album producir /home/z/my-project/DMD_Composer/output/albumes/k_cancel_2/produccion/album.json --out /home/z/my-project/DMD_Composer/output/albumes/k_cancel_2/produccion --forzar

# una pista, verificada por hash
python3 scripts/produce.py /home/z/my-project/DMD_Composer/output/albumes/k_cancel_2/produccion/01_track01/doc.json --production sax_vibes --seed 558922 --out /home/z/my-project/DMD_Composer/output/albumes/k_cancel_2/produccion/01_track01 --verify f00be05b06591439032da02a579f914ba64a72ea61310b6cbfbe0774f6a904d0
```

Manifiesto completo (config efectiva, hashes y comandos por pista): `manifiesto.json` · estado de ejecución: `estado.json`.
