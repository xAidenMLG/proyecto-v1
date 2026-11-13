# AUDIT_EXECUTIVE_SUMMARY — Resumen ejecutivo de la auditoría arquitectónica integral

> **Misión**: DMD Composer como centro de producción musical (investigación, SIN implementación).
> **Fecha**: 2026-11-11 · **Entorno de auditoría**: sandbox Linux (espejo del repo) · **Máquina objetivo**: Windows 10, Python 3.12, Ryzen 7 3700X, 16 GB.
> **Método**: 6 agentes especializados (A Composer Core, B Pipeline, C MIDI Forensics, D Audio, F Álbum, H Seguridad) + verificación cruzada de los hallazgos críticos por el auditor principal + pruebas controladas de ejecución real en `/tmp` (cero escrituras en el repo).
> **Clasificación de evidencia**: `VERIFIED` (comprobado por código o ejecución) / `PARTIALLY VERIFIED` / `UNVERIFIED` / `NOT AVAILABLE`.

---

## 1. Estado real del sistema (foto verificada hoy)

| Subsistema | Estado verificado |
|---|---|
| **DMD Composer 1.1** (`DMD_Composer/`, FastAPI en `127.0.0.1:8898`) | Funcional para su alcance actual: 6 pantallas, 16 ejes fixed/auto/free, armonía nativa/guiada, acordes literales prevalidados con `forge/theory` real, protagonista con propuesta de distribución, modo álbum compositivo 2–64 pistas, doc `dark-director/1` validado con el validador REAL y compilado con el compilador REAL. **114/114 tests OK** y **5 demos reproducibles por SHA256** (ejecutados hoy en sandbox). |
| **Producción MIDI** (`scripts/produce.py::producir_cancion`) | **VERIFIED de extremo a extremo**: headless, sin Studio, desde cualquier CWD, determinista byte a byte, con `--verify` sin efectos laterales. Pista real de 4:30 min producida en **0,174 s con pico de 22,3 MiB de RAM**. |
| **Orquestador de álbumes DMD** (`album/`, CLI `python3 -m album`) | **VERIFIED** por código + álbum demo «Noches Largas» 13/13 pistas (~27,8 min) con estado, resume, `--solo/--regen/--forzar`, aislamiento de fallos y diversidad PRE/POST. |
| **DMD Studio** (`studio/`, `127.0.0.1:8899`) | Operativo como cliente del mismo pipeline (subproceso `python -m studio.runner`). **No es necesario para producir**. |
| **Render WAV (FluidSynth)** | Código completo y correcto en `forge/audio.py` (PARTIALLY VERIFIED), pero **0 renders exitosos en la historia del repo**: los 8 jobs de Studio con `wav=true` terminaron `done` con `RuntimeError: FluidSynth no encontrado` — causa raíz identificada: el hijo se arranca con un **entorno sin `PATH`** (`studio/jobs.py:265-270`). FluidSynth no existe en el sandbox (NOT AVAILABLE aquí; sí en `C:\tools\FluidSynth` del usuario). |
| **MP3** | **VERIFIED en sandbox end-to-end** con ffmpeg 7.1.5 + libmp3lame (CBR 192/320, VBR q2, ID3, loudnorm 2 pasadas, alimiter). El código del repo ya llama a ffmpeg/lame (`forge/audio.py`). En Windows falta localizar `ffmpeg.exe`/`lame.exe` (el código ya busca en `C:/ffmpeg/bin`, `C:/tools/ffmpeg/bin`). |
| **sfizz / SFZ** | **NOT AVAILABLE en sandbox** y **cero referencias en todo el repo**. El código actual solo soporta **un único SF2 para todo el MIDI**; no hay capa de asignación por instrumento ni soporte SFZ. |
| **Soundfonts** | **Cero `.sf2/.sf3/.sfz/.exe/.dll` en el árbol del repo** (verificado con globs y `unzip -l` sobre los zips). Los 5 soundfonts del usuario son UNVERIFIED desde aquí (comandos de verificación en `AUDIT_AUDIO_RENDERING.md §6`). |
| **MIDI producido** | Forense sobre 27 SMF reales: plantilla **invariante 7 tracks × 6 canales** (sax ch0 GM66, rhodes ch1 GM4, vibraphone ch2 GM11, bass ch3 GM38, drums ch9, pad ch5 GM91; ch4 vacío), GM puro, sin keyswitches/SysEx/aftertouch, mezcla incrustada (CC7/10/91/93), markers de sección con nombres DMD. |

**Conclusión central**: la distancia entre «Composer como director» y «Composer como centro de producción» **no requiere ningún motor nuevo**: requiere un *Production Bridge* por subproceso (patrón ya probado en Composer), el **export del spec `dmd-album/1` real**, una capa de estados por pista, y después las capas de audio (WAV→MP3→asignación de soundfonts). Todo lo costoso (compilar, generar MIDI, orquestar álbumes, renderizar WAV) **ya existe y está verificado**.

---

## 2. Capacidades verificadas (resumen)

1. Componer y validar documentos `dark-director/1 rev 3.2` desde Composer con el validador/compilador reales vía subproceso aislado (`composer/bridge.py`, `dmd_bridge_runner.py`) — VERIFIED.
2. Producir MIDI real sin Studio: `python3 scripts/produce.py DOC.json --production P --seed N --out DIR` (rc 0/1/2; sin artefactos parciales en fallo; determinismo byte-idéntico reproducido en 5 pruebas) — VERIFIED.
3. Producir un álbum completo de 13 pistas con resume y diversidad — VERIFIED (lado DMD) por demo + código.
4. Reconstruir instrumentación desde el MIDI sin tocarlo: biyección estable track→canal→programa GM — VERIFIED (27 ficheros).
5. Codificar MP3 con metadatos y normalización — VERIFIED (sandbox).
6. Seguridad local sólida en Composer y Studio (bind 127.0.0.1, whitelists de ids, escritura atómica en Composer, single-flight 409 en Studio) — VERIFIED por tests H y por código.

## 3. Limitaciones reales (las que importan)

1. Composer **no produce** MIDI/WAV/MP3 hoy: solo emite la instrucción CLI (`engine.py:90-96`) y la marca «seleccionado_pendiente_de_aplicar».
2. El plan interno de álbum de Composer (`composer/albums.py:58`) se autodenomina `"dmd-album/1"` pero **NO es el esquema real** de `album/esquema.py` — colisión de nombre con estructura distinta. Un export directo hoy **rompería** la validación A1xx.
3. El render WAV **nunca se ha ejecutado con éxito** (bug de entorno en el hijo de Studio) y no admite SFZ ni asignación por instrumento (un solo SF2 por render).
4. El orquestador de álbumes escribe `estado.json`/`huellas.json`/`plan.json` **sin escritura atómica** (`album/orquestador.py:57-60,210`) y **sin timeout por pista**.
5. No hay capas de audio-player, Soundfont Manager ni Project Library (a diseñar: `AUDIT_TARGET_ARCHITECTURE.md`).
6. Techo GM: sin keyswitches/aftertouch/SysEx en el MIDI, el control fino de instrumentos SFZ se limita a velocity + pitch bend (RPN0 ±2 st ya presente) + CC.

## 4. Riesgos principales (priorizados)

| ID | Riesgo | Severidad | Evidencia |
|---|---|---|---|
| P0-1 | `POST /api/harmony/templates` → HTTP 500 `NameError: hashlib` (también `random` sin importar). Rompe el botón «Aplicar plantilla del mood» de la Vista 3. No cubierto por tests. | Alta (funcional) | `DMD_Composer/composer/server.py:465-466` (imports en :12-33); reproducido con TestClient por 2 agentes |
| P0-2 | El hijo de Studio arranca con env mínimo **sin PATH/SystemRoot** → `shutil.which('fluidsynth')` falla en Windows → WAV imposible desde Studio (8/8 jobs fallidos). | Alta | `studio/jobs.py:265-270` + `forge/audio.py:17` + `studio_data/jobs/j_2026…*.json` (8 registros con error) |
| P0-3 | Corte a mitad de álbum → `estado.json` truncado → `_cargar_estado` reinicia a vacío → pérdida de reanudación y riesgo de regenerar pistas aceptadas. **Escenario principal de fallo del sistema.** | Alta | `album/orquestador.py:47-60,210`; `planificador.py:318-324` |
| P1-4 | Colisión `dmd-album/1` (plan interno Composer ≠ esquema real) + dos semánticas de hash (sha256 de fichero vs canónico `sort_keys`). | Alta en integración | `DMD_Composer/composer/albums.py:58` vs `album/esquema.py:43-51,239` |
| P1-5 | Studio sin límite de tamaño de cuerpo; `delete_project` no tolera ficheros bloqueados (reproductor/AV) → 500; el orquestador no tiene timeout por pista; `bridge.py:72-78` sin `encoding` (cp1252 en Windows). | Media | `studio/` (grep 0 límites), `studio/projects.py:187-192`, `orquestador.py:138-208`, `composer/bridge.py:72-78` |
| P2-6 | Efectos laterales menores: `INDICE.md` escapa de `out_dir` (CLI), nombre del MIDI = nombre de la carpeta, `.pyc` de `forge/` se escriben fuera del modo sin-bytecode, `producir_cancion` sin soporte de stems. | Baja | `produce.py:112,157-170`; `jazz_engine/forge_link.py:112-140` |

## 5. Arquitectura recomendada (una línea por capa)

```
Composer (UI+Core, 8898)
   → Album Manager (plan + export spec dmd-album/1 real + estados por pista)
   → DMD Production Bridge (subprocess: producir_cancion / python -m album producir)   ← ÚNICO generador MIDI
   → Audio Rendering Engine (forge/audio.py WAV + ffmpeg MP3; stems por canal en v2)
   → Audio Player (<audio> HTML sobre WAV/MP3; sin synth JS)
   → Soundfont Manager (registro por REFERENCIA ruta+sha256; detección de referencias rotas)
   → Project Library (DMD_Library/Albums/<slug>/ = ficheros + JSON + hashes; sin DB)
```
Detalle completo y contratos entre componentes: `AUDIT_TARGET_ARCHITECTURE.md`.

## 6. Decisiones importantes (resumen; argumentos completos en §7)

1. El puente de producción es **subproceso con argv fijo, sin shell, con timeout** (misma disciplina que `bridge.py`/`studio.runner`), nunca importar los motores en el proceso del servidor.
2. Composer **exporta** un `album.json` con el esquema REAL `dmd-album/1` + espejo de los docs elegidos; el plan interno compositivo NO viaja al orquestador.
3. v1 de render: **un solo SF2 para todo el MIDI** (GeneralUser-GS autodetectado); stems por canal en v2; SFZ/sfizz solo tras verificación en Windows (v3).
4. El player reproduce **WAV/MP3 con `<audio>`**; no hay reproductor MIDI nativo de navegador sin dependencias nuevas.
5. Persistencia **por ficheros + JSON + SHA256** (sin SQLite), siguiendo el patrón ya probado (`studio_data/`, `gen_NNNN`, `estado.json`).
6. Modelo de ejecución: **un proceso por álbum (CLI del orquestador), secuencial por pista**, watchdog ~900 s/pista, single-flight en Composer; paralelismo solo en WAV si se desea (N=2).
7. **Cero dependencias Python nuevas**; los únicos binarios externos son FluidSynth (ya en Windows) y ffmpeg/lame para MP3 (por localizar en Windows).

## 7. Respuestas a las 20 decisiones que pide la misión (§11)

| # | Pregunta | Respuesta (estado de evidencia) |
|---|---|---|
| 1 | ¿Puede Composer producir MIDI directamente sin abrir Studio? | **SÍ, VERIFIED.** El pipeline es headless: CLI (`produce.py`), motor directo (`python -m jazz_engine`) y runner de Studio producen MIDI idéntico byte a byte (TEST01/06/07). Composer debe hacerlo vía subproceso, nunca importando motores. |
| 2 | ¿Qué debe reutilizar exactamente? | `scripts/produce.py::producir_cancion()` (pista), `python -m album` (álbum), `dark_director.validador`/`compilador` (ya lo hace vía bridge), `forge/audio.py::render_wav`/`mp3`/`master` (audio), `forge/theory.parse_chord` (ya lo hace), huellas de diversidad de `produce.py`. |
| 3 | ¿Punto de integración más seguro? | Nueva tarea `produce` en el patrón existente `composer/bridge.py::_run_task` + runner hijo (como `dmd_bridge_runner.py`), invocando `producir_cancion` con `out_dir` único y `indice=False`; para álbumes, subproceso `python -m album producir` con CWD=raíz DMD y rutas absolutas. |
| 4 | ¿Puede Composer producir MP3 con las herramientas instaladas? | En este sandbox **SÍ, VERIFIED** (ffmpeg 7.1.5 + libmp3lame, con ID3/loudnorm/alimiter). En Windows depende de localizar `ffmpeg.exe` o `lame.exe` (UNVERIFIED; el código ya busca en rutas estándar). |
| 5 | ¿Puede combinar FluidSynth y sfizz en un mismo render? | **SÍ, a nivel de stems + mezcla** (render por canal → `ffmpeg amix`), no a nivel de un solo proceso. Hoy no existe soporte SFZ (`forge/audio.py` solo acepta un SF2 para todo el MIDI). Diseño completo: `AUDIT_HYBRID_RENDER_ARCHITECTURE.md`. |
| 6 | ¿Limitaciones reales de sfizz en este entorno? | **NOT AVAILABLE** aquí y sin ninguna referencia en el repo: ejecutables, versión y CLI de render offline son UNVERIFIED hasta probarlos en Windows (`C:\tools\sfizz`). No presuponer CLI de render por MIDI. |
| 7 | ¿Cómo debe realizarse la asignación de soundfonts? | Por **canal MIDI** (biyección estable track→canal→GM verificada en 27 SMF): mapa `{canal → motor, biblioteca, banco/preset}` en un `render_profile.json` versionado, con fallback GM para canales sin asignación y validación de rutas/presets. Percusión = canal 9. El MIDI fuente **nunca se modifica**. |
| 8 | ¿Cómo debe conectarse el orquestador de álbumes? | Composer escribe `album.json` (esquema real) + espejo `docs/` de las generaciones elegidas → subproceso `python -m album producir --out DMD_Library/Albums/<slug>` → Composer lee `estado.json`/`informe_album.json`/`manifiesto.json` y refleja estados por pista. El orquestador SIEMPRE replanifica (idempotente) pero **consumir los docs pre-generados sin regenerarlos: SÍ**; importar un plan externo: NO existe (no hackear). |
| 9 | ¿Cómo debe almacenarse cada álbum? | `DMD_Library/Albums/<slug>/` con `album.json` (spec), `estado.json`, `manifiesto.json`, `diversidad.json`, `NN_<id>/` (doc.json, `<id>.mid`, evidencia, WAV/MP3, `render_profile.json`), `logs/`, `hashes.txt`. Soundfonts por **referencia** (ruta+sha256+tamaño), nunca copiados. Ver `AUDIT_PROJECT_LIBRARY.md`. |
| 10 | ¿Qué debe ocurrir cuando falla una canción? | Hoy ya funciona: aislamiento por pista, `estado.json` actualizado tras cada pista, el resto continúa, reintentos con `--regen`. Añadir: **escritura atómica** del estado, watchdog por pista, y separar el fallo MIDI del fallo de audio (un MP3 roto no invalida el MIDI). |
| 11 | ¿Arquitectura mínima para el objetivo? | Composer (tal cual) + Production Bridge (subproceso) + export de spec álbum + estados por pista + carpeta Library con hashes. Sin sfizz, sin cola de jobs, sin DB, sin reescrituras de UI grandes. |
| 12 | ¿Arquitectura ideal a largo plazo? | La de `AUDIT_TARGET_ARCHITECTURE.md`: 7 módulos (Core, Album Manager, Bridge, Rendering Engine, Player, Soundfont Manager, Library) con jobs asíncronos y progreso en vivo, perfiles de render híbrido y recuperación total. |
| 13 | ¿Qué componentes existentes no debemos tocar? | `forge/` completo (incluido `styles.py`), `dark_director/contract.py` (rev 3.2), `dark_director/identities/dark_triphop.py`, goldens y sus manifiestos, DMD Studio (durante esta misión), y la semántica determinista (doc+seed → bytes). Verificado intacto hoy por hashes. |
| 14 | ¿Qué dependencias nuevas son imprescindibles? | **Ninguna de Python.** Binarios externos: ffmpeg.exe/lame.exe (MP3 — ya buscados por el código) y, solo si se quiere SFZ, sfizz con CLI de render comprobada. |
| 15 | ¿Orden óptimo de implementación? | Fase 0 fixes P0 → 1 Bridge MIDI por pista → 2 álbumes batch (barato: infra ya VERIFIED) → 3 Soundfont Manager + WAV + Player → 4 MP3/master → 5 Library completa → 6 (opcional) híbrido SF2/SFZ. Justificación del reorden frente al propuesto por la misión: el reproductor sin WAV es inviable sin dependencias nuevas, y el batch de álbumes reutiliza infraestructura ya demostrada. Ver `IMPLEMENTATION_ROADMAP.md`. |
| 16 | ¿Qué podría volver el proyecto demasiado complejo? | Duplicar orquestador/render en Composer; integrar SFZ/stems el día 1; cola de jobs con worker persistente; base de datos; reescribir la UI; fragmentar el MIDI en notas (prohibido). |
| 17 | ¿Qué simplificaciones consiguen el mismo resultado? | Un SF2 por render en v1; perfiles de producción como «stems» lógicos (misma seed); mezcla con `ffmpeg filter_complex`; Library = ficheros+JSON; player HTML; reutilizar el patrón `jobs.py` de Studio para jobs asíncronos en Composer. |
| 18 | ¿Qué puede implementarse inmediatamente? | Los 4 fixes P0/P1 (pequeños y localizados), el Bridge MIDI por pista (todo VERIFIED), el export del spec álbum, los estados por pista, y el pipeline MP3 (VERIFIED). |
| 19 | ¿Qué necesita investigación adicional? | Todo lo Windows-only: render real de FluidSynth (1ª ejecución), CLI real de sfizz, presencia/versión de ffmpeg.exe/lame.exe, integridad y tamaños de los 5 soundfonts, rendimiento WAV en el hardware. Comandos listos en `AUDIT_AUDIO_RENDERING.md §6-7` y `OPEN_QUESTIONS.md`. |
| 20 | ¿Principal riesgo técnico y mitigación? | El **ciclo de vida del proceso de producción**: entorno del hijo sin PATH (ya rompió WAV), estado no atómico del álbum y ausencia de timeouts. Mitigación: los 3 fixes de la Fase 0 + watchdog + single-flight + `--verify` SHA256 en cada artefacto. Riesgo estratégico complementario: **no duplicar motores** (el puente es un adaptador, jamás un segundo pipeline). |

## 8. Tabla final de funcionalidades

| Funcionalidad | Estado actual | Viabilidad | Dependencias | Prioridad |
|---|---|---|---|---|
| Generar MIDI desde Composer | No; instrucción CLI emitida (`engine.py:90-96`) | **Alta** — pipeline VERIFIED headless y determinista | Bridge subprocess + estados por pista (diseño listo) | **P0** |
| Reproducir MIDI | No | Alta (vía WAV render + `<audio>`; sin synth JS) | FluidSynth render operativo (fix P0-2) | P1 |
| Renderizar SF2 | Código VERIFIED (`forge/audio.py`); **0 ejecuciones reales exitosas** (bug env P0-2) | Alta tras fix | FluidSynth + sf2 en Windows | P1 |
| Renderizar SFZ | No existe soporte; sfizz sin referencias en repo | Media | sfizz verificado en Windows + capa de asignación (v3) | P2 |
| Render híbrido (SF2+SFZ por instrumento) | No; diseño completo disponible | Media | Stems por canal + mezcla ffmpeg (VERIFIED) | P2–P3 |
| Exportar MP3 | VERIFIED en sandbox (192/320/VBR+ID3); repo ya llama ffmpeg/lame | Alta | Localizar ffmpeg.exe/lame.exe en Windows | P1 |
| Producción batch (13 pistas) | VERIFIED lado DMD (álbum demo 13/13); Composer no exporta spec real | Alta | Export `dmd-album/1` real + subprocess orquestador | P0–P1 |
| Recuperación de álbumes | VERIFIED (resume/`--regen`/`--solo`) pero frágil (estado no atómico) | Alta tras fix | Escrituras atómicas + watchdog | P1 |
| Biblioteca de proyectos | No existe (solo `composer_data/` + `output/`) | Alta | Diseño `AUDIT_PROJECT_LIBRARY.md` (ficheros+JSON) | P1–P2 |

## 9. Próximo paso

Ejecutar **Fase 0** del roadmap (4 fixes localizados con tests de regresión: imports de `server.py`, entorno del hijo de Studio, atomicidad de `estado.json`/`huellas.json`/`plan.json`, watchdog por pista) y, a continuación, **Fase 1** (Production Bridge MIDI por pista). Ninguna fase requiere tocar motores protegidos ni el contrato rev 3.2 — verificado con hashes antes/después de toda la auditoría.

---
*Índice de la carpeta*: `AUDIT_CURRENT_ARCHITECTURE.md` · `AUDIT_PRODUCTION_PIPELINE.md` · `AUDIT_MIDI_FORENSICS.md` · `AUDIT_AUDIO_RENDERING.md` · `AUDIT_HYBRID_RENDER_ARCHITECTURE.md` · `AUDIT_ALBUM_AUTOMATION.md` · `AUDIT_PROJECT_LIBRARY.md` · `AUDIT_SECURITY_PERFORMANCE.md` · `AUDIT_TARGET_ARCHITECTURE.md` · `IMPLEMENTATION_ROADMAP.md` · `IMPLEMENTATION_BACKLOG.md` · `VERIFICATION_MATRIX.md` · `OPEN_QUESTIONS.md`
