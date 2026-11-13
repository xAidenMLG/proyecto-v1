# AUDIT_PROJECT_LIBRARY — Diseño de la biblioteca de proyectos (persistencia, versionado, integridad, recuperación)

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11 · Diseño basado en patrones ya VERIFIED en el repo (`gen_NNNN` exclusivo, escrituras atómicas de Composer/Studio, `estado.json` del orquestador, manifiestos con `--verify`).

---

## 1. Principios

1. **Ficheros + JSON + SHA256, sin base de datos** (patrón DS-6 ya probado; volumen local lo permite).
2. **Referencias, no copias**, para activos pesados compartidos (soundfonts): ruta + sha256 + tamaño + nombre.
3. **Nunca sobrescribir resultados aceptados**: generaciones `gen_NNNN` exclusivas (store.py:179-194) y drift → `pendiente` (F8-6).
4. **Escrituras atómicas en todo el estado** (gap actual en `album/`: orquestador.py:57-60,210 — fix Fase 0).
5. IDs estables derivados de slugs seguros (`^[a-z0-9][a-z0-9_-]{0,47}$` en Composer; `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` en el spec de álbum).

## 2. Estructura de directorios propuesta (evolución de la propuesta de la misión, alineada con el código real)

```
DMD_Library/
└── Albums/
    └── Dark_TripHop_Vol_01/                # slug seguro; único (sufijo _2,_3… como albums.py:44-48)
        ├── album.json                      # spec dmd-album/1 REAL (el export de Composer)
        ├── estado.json                     # estado por pista del orquestador (ok|fallo|pendiente)
        ├── plan.json                       # plan dmd-album-plan/1 del orquestador
        ├── informe_album.json/.md          # informe + diversidad POST
        ├── manifiesto.json                 # hashes + comandos --verify (reproducibilidad)
        ├── huellas.json                    # huellas técnicas de diversidad POST
        ├── render/                         # configuración de render del álbum
        │   ├── render_profile.json         # dmd-render-profile/1 (ver AUDIT_HYBRID)
        │   └── soundfonts.json             # REFERENCIAS: [{name, path, sha256, size, format}]
        ├── logs/                           # job logs por corrida (runner-YYYYMMDD-HHMMSS.log)
        ├── docs/                           # ESPEJO de los doc.json elegidos (evita A201 si se borra el proyecto fuente)
        ├── 01_medianoche_puerto/
        │   ├── doc.json                    # doc de la pista (espejo)
        │   ├── 01_medianoche_puerto.mid
        │   ├── evidencia.json              # sha256 midi+doc, compliance, comando regenerar
        │   ├── 01_medianoche_puerto.wav    # fase audio (opcional)
        │   ├── 01_medianoche_puerto.mp3    # fase audio (opcional)
        │   └── song_map.json/.csv          # si viene de Composer
        └── 13_ultimo_metro/ …
```

Justificación de desviaciones respecto a la propuesta literal de la misión: los nombres `NN_<id>/` y los ficheros `estado.json/plan.json/informe_album/manifiesto/huellas` **ya existen** así en el orquestador (`orquestador.py:140`, `informe.py`) — adoptarlos evita traducciones y migraciones. El espejo `docs/` es el único añadido estructural necesario (riesgo A201 documentado).

## 3. Archivos de metadatos y su schema

| Fichero | Contenido mínimo | Ya existe |
|---|---|---|
| `album.json` | esquema `dmd-album/1` completo (A1xx) | sí (formato), como export nuevo desde Composer |
| `estado.json` | `{schema, album, semilla_album, actualizado_utc, pistas:{id:{estado,sha256_midi,perfil,seed,harmony,especificacion,carpeta,intentos,error?,traceback?}}}` | sí (orquestador) |
| `manifiesto.json` | config efectiva por pista + hashes + comandos `--verify` | sí (informe.py:117-157) |
| `soundfonts.json` | referencias con sha256; detectadas rotas | **nuevo** |
| `render_profile.json` | `dmd-render-profile/1` | **nuevo** (AUDIT_HYBRID §2) |
| `song_map.json/.csv` | por pista cuando la fuente es Composer | sí (store.py:197-214) |
| `generation_manifest.json` | por generación Composer (sha256 del doc) | sí |

Versionado: cada JSON lleva `schema` y, cuando cambie la estructura, `schema_version` (migraciones = lectores tolerantes + conversión explícita, nunca reescritura silenciosa).

## 4. Estados de producción por pista (propuesta, separando MIDI de audio)

```
PLANNED → JSON_READY → VALIDATED → MIDI_RUNNING → MIDI_READY → AUDIO_RUNNING → AUDIO_READY
                                   ↘ MIDI_FAILED              ↘ AUDIO_FAILED (el MIDI READY se CONSERVA)
```
- Los estados MIDI los escribe el orquestador (`ok|fallo|pendiente`); la capa Composer los traduce.
- AUDIO_* solo los introduce la nueva capa de render (Fase audio del roadmap): un MP3 roto **no invalida ni regenera** el MIDI (requisito explícito de la misión).
- `pendiente` (drift) se muestra con su `razon` y la acción sugerida (`--regen <id>`).

## 5. Integridad, checksums y verificación

- Cada pista: sha256 del doc y del MIDI en `estado.json` + `evidencia.json` (ya lo hace `producir_cancion`).
- Verificación de un álbum completo: `python -m album informe` + los comandos `produce.py … --verify <sha>` que el manifiesto ya imprime.
- Verificación de referencias de soundfonts: recomputar sha256 contra `soundfonts.json`; si difiere o falta → **error explícito** con el nombre y el campo culpable (requisito de la misión §3.G).
- Escrituras: `tmp + os.replace` (+`.bak` opcional) para `estado.json`, `huellas.json`, `plan.json`, job files y cualquier metadato; los MIDIs/WAV/MP3 se escriben una vez y nunca se editan (regeneración = carpeta/intento nuevo).

## 6. Temporales, limpieza y duplicados

- Todo el trabajo intermedio (stems, MIDIs filtrados, WAV temporal) en `TemporaryDirectory` → cero residuos (patrón `forge/audio.py:74`).
- `INDICE.md` lateral del CLI: en la Library no aplica (el orquestador ya usa `indice=False`).
- Duplicados de álbum: slug único con sufijo `_2` (albums.py:44-48); duplicados de pistas: detectados por huellas POST (Jaccard/SHA) como **aviso**, no bloqueo.
- Historial: las corridas del orquestador son idempotentes sobre el mismo out_dir (SALTADA/pendiente/fallo con `intentos`); los job logs quedan en `logs/` por corrida.
- Retención: decisión del usuario (OPEN_QUESTIONS #12); mecanismo propuesto: archivar generaciones Composer antiguas (los `gen_NNNN` nunca se borran automáticamente).

## 7. Recuperación tras cierres inesperados

| Escenario | Comportamiento con los fixes de Fase 0 |
|---|---|
| Corte a mitad de pista | El doc/MIDI parcial queda en la carpeta de pista (sin estado `ok`) → la próxima corrida la reintenta; `estado.json` atómico nunca queda truncado |
| Corte entre pistas | `estado.json` refleja las pistas terminadas → resume exacto (SALTADA) |
| Composer cerrado durante producción | El subproceso del orquestador es independiente: puede seguir (patrón runner) o ser cancelado; el estado persistido decide |
| Fichero bloqueado por reproductor/AV (Windows) | La capa Library captura el error y lo reporta con nombre de fichero (mejora sobre projects.py:187-192 que hoy da 500 crudo) |

## 8. Soundfonts por referencia — reglas

1. `soundfonts.json` del álbum: `{name, path, sha256, size, format}` por banco usado por `render_profile.json`.
2. El Soundfont Manager valida en cada render: existencia, legibilidad, sha256 (o al menos tamaño>1024 como hace settings.py).
3. Referencia rota → **error explícito** (nunca fallback silencioso a otro banco; el fallback GM es decisión del perfil, no un accidente).
4. Si el usuario mueve un banco: el Manager ofrece re-vincular (actualiza `path`, conserva `name`+`sha256`) — operación explícita del usuario.
