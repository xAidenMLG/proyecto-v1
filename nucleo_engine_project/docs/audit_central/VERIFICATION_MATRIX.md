# VERIFICATION_MATRIX — Tabla de todas las verificaciones realizadas

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11 · Estados: VERIFIED (comprobado por código o ejecución) / PARTIALLY VERIFIED / UNVERIFIED / NOT AVAILABLE.
> Evidencia física: `/home/z/my-project/scripts/audit_baseline/` (git status + sha256 de los 583 ficheros trazados), `scripts/audit_a..h/` (informes y artefactos), `/tmp/audit_b|c|d/` (ejecuciones temporales).

| ID | Área | Prueba | Resultado | Evidencia | Estado |
|---|---|---|---|---|---|
| V-01 | Protección | Estado git inicial registrado antes de tocar nada | snapshot guardado | `scripts/audit_baseline/git_status_baseline.txt` | VERIFIED |
| V-02 | Protección | sha256 de los 583 ficheros trazados del proyecto | baseline completo | `scripts/audit_baseline/sha256_all_tracked.txt` | VERIFIED |
| V-03 | Protección | Hashes de protegidos (forge/ completo, dark_triphop.py, contract.py, validador, compilador) | registrados y re-verificados al cierre | baseline + delta git | VERIFIED |
| V-04 | Protección | Delta git al cierre vs baseline | solo `.pyc` regenerados + artefactos de tests (studio_data/jobs ×14) + dirs de auditoría nuevos; **0 fuentes modificadas** | `git status --porcelain` diff | VERIFIED |
| V-05 | Composer | Suite completa de tests de Composer | 114/114 OK (5,1 s) | ejecución `unittest discover` por Agente A | VERIFIED |
| V-06 | Composer | 5 demos reproducibles | SHA256 idénticos a los publicados | `demostraciones.py --verificar` | VERIFIED |
| V-07 | Composer | UI 6 pantallas + endpoints (30 rutas inventariadas) | index.html:18-23; server.py:86-655 | lectura | VERIFIED |
| V-08 | Composer | `POST /api/harmony/templates` roto | HTTP 500 `NameError: hashlib` (y `random`) | server.py:465-466 vs imports :12-33; reproducido con TestClient (Agentes A y H) | VERIFIED |
| V-09 | Composer | 0 campos inventados (0 E109) | test A2 + QA dinámico en verde | tests Composer | VERIFIED |
| V-10 | Composer | Validación/compilación con los motores REALES vía subprocess | bridge.py:57-85; dmd_bridge_runner.py:30-46 | lectura + tests F2 | VERIFIED |
| V-11 | Composer | Plan de álbum interno autodenominado `dmd-album/1` con estructura distinta | albums.py:58 vs album/esquema.py:43-51 | lectura | VERIFIED (colisión) |
| V-12 | Composer | `generate_all` síncrono secuencial, reanudable, re-usa decisiones fijadas | albums.py:275-318; server.py:618-627 | lectura | VERIFIED |
| V-13 | Composer | delete_project puede borrar `OUTPUT_DIR/albumes` si pid="albumes" | store.py:165-174 + albums.py:30 | lectura (edge no ejecutado) | PARTIALLY VERIFIED |
| V-14 | Pipeline | `produce.py` CLI headless produce MIDI real | TEST01: rc 0, 0,174 s, pico 22,3 MiB, MIDI 7.645 B | `/tmp/audit_b/` | VERIFIED |
| V-15 | Pipeline | Determinismo byte-idéntico y CWD-independiente | TEST02/06/07/09 mismo sha `873e19fb…` | ejecuciones | VERIFIED |
| V-16 | Pipeline | `--verify` sin efectos laterales | TEST03 OK / TEST03b FALLO limpio | ejecuciones | VERIFIED |
| V-17 | Pipeline | Fallo controlado: doc inválido → rc 1, E105, **0 artefactos parciales** | TEST04 (bpm 500) | ejecución | VERIFIED |
| V-18 | Pipeline | Camino ORIGINAL (`production=original`) funcional | TEST05 sha `85764883…` | ejecución | VERIFIED |
| V-19 | Pipeline | F7 opcional por CLI | TEST08 (`--harmony dark_cinematic --harmony-variacion medium`) | ejecución | VERIFIED |
| V-20 | Pipeline | Runner headless de Studio produce idéntico al CLI | TEST07 `## RESULT OK` | ejecución | VERIFIED |
| V-21 | Pipeline | Artefacto histórico reproduce byte a byte (`demo_medianoche` + `--verify`) | TEST10 `VERIFICACION: OK` | ejecución | VERIFIED |
| V-22 | Pipeline | `.pyc` se escriben en forge/ sin flag de bytecode | TEST11: 34 .pyc (7 en forge/) | ejecución | VERIFIED (gap R5) |
| V-23 | Pipeline | Efectos laterales completos de `producir_cancion` | 4 ficheros en out_dir + INDICE.md (CLI) + .pyc; nada más | produce.py:106-170 | VERIFIED |
| V-24 | Studio | Single-flight 409, timeout 900 s, recover_interrupted, cancel→terminate | jobs.py:25,55-67,220-321 | lectura + tests 13 ✓ | VERIFIED |
| V-25 | Studio | Hijo con env sin PATH/SystemRoot → fluidsynth no encontrado | jobs.py:265-270 + 8 jobs `wav=true` fallidos reales | studio_data/jobs/ | VERIFIED (causa raíz del 0-WAV) |
| V-26 | Álbum | Esquema dmd-album/1 real (campos, A1xx, MAX 99) | esquema.py completo | lectura | VERIFIED |
| V-27 | Álbum | CLI `python -m album plan|producir|informe|estado` (+--help) | ejecución --help | terminal | VERIFIED |
| V-28 | Álbum | Álbum demo 13/13 ok (~27,8 min) con estado/resume/drift | estado.json/plan.json/informe del demo | lectura de artefactos | VERIFIED (histórico) |
| V-29 | Álbum | Semillas derivadas `semilla_album+101*(i+1)` verificadas en demo | plan.json (3504/3706/…) | lectura | VERIFIED |
| V-30 | Álbum | Estados de pista y transiciones (incl. `pendiente` regenera en corrida siguiente) | orquestador.py:36-40,142-208 | lectura | VERIFIED |
| V-31 | Álbum | `estado.json`/`huellas.json` sin escritura atómica | orquestador.py:57-60,210 | lectura | VERIFIED (riesgo P0-3) |
| V-32 | Álbum | Producción in-process sin timeouts | orquestador.py:125-128,138-208 | lectura | VERIFIED |
| V-33 | MIDI | Plantilla 7 tracks × 6 canales invariante (27 SMF) | matriz track×canal | `scripts/audit_c/results/` | VERIFIED |
| V-34 | MIDI | Parser propio validado contra pipeline (sha/BPM/duración/notas) | 144/144 recuentos coinciden con evidencia.json | audit_c | VERIFIED |
| V-35 | MIDI | GM puro: PC fijos tick 0, sin bank select/SysEx/aftertouch/keyswitches | 27/27 ficheros | audit_c | VERIFIED |
| V-36 | MIDI | Mix incrustado (CC7/10/91/93) y fade CC11 trazable al doc | comparación por canal | audit_c | VERIFIED |
| V-37 | MIDI | Markers de sección con nombres DMD | FF 06 en Conductor | audit_c | VERIFIED |
| V-38 | MIDI | Bug velocity: drums 112–118 > cap 110 del doc | 27/27 | audit_c | VERIFIED (upstream, protegido) |
| V-39 | MIDI | Duplicados pitch+tick cross-track (bass 36=kick) sin conflicto por canal | 34 grupos | audit_c | VERIFIED |
| V-40 | Audio | FluidSynth/sfizz/lame/sox/timidity ausentes en sandbox | `command -v` rc=1 ×5 | terminal | NOT AVAILABLE |
| V-41 | Audio | ffmpeg 7.1.5 con libmp3lame + libshine; licencia GPL build | `ffmpeg -version` + `-encoders` | terminal | VERIFIED |
| V-42 | Audio | MP3 end-to-end (192k/320k/VBR q2) con ffprobe correcto | tamaños 705/1175/546 KiB, ~59× realtime | `/tmp/audit_d/` | VERIFIED |
| V-43 | Audio | ID3 + loudnorm 2 pasadas + alimiter disponibles | encode de prueba | `/tmp/audit_d/` | VERIFIED |
| V-44 | Audio | `forge/audio.py`: comando FluidSynth literal y orden de búsqueda (incl. `C:/tools/fluidsynth/bin`) | audio.py:16-83 | lectura | VERIFIED (código) / ejecución PARTIALLY |
| V-45 | Audio | 0 `.sf2/.sf3/.sfz/.exe/.dll` en el árbol y en los zips | globs + `unzip -l` ×4 | terminal | VERIFIED |
| V-46 | Audio | sfizz: cero referencias en el repo | grep exhaustivo | terminal | VERIFIED (ausencia) |
| V-47 | Audio | Soundfonts del usuario (5 nombres) | no accesibles desde sandbox | — | UNVERIFIED (comandos de probe listos) |
| V-48 | Audio | Render WAV FluidSynth real | nunca ejecutado con éxito (8 fallos por env) | studio_data/jobs | PARTIALLY VERIFIED |
| V-49 | Seguridad | Composer: bind 8898 localhost, límites 512KB/8MB, atómico, sin eval/shell | store.py, __main__.py, tests H1-H15 15 ✓ | tests | VERIFIED |
| V-50 | Seguridad | Studio: bind 8899, whitelists, single-flight, sin límite de cuerpo | server.py + tests | lectura+tests | VERIFIED (gap de tamaño) |
| V-51 | Seguridad | Puertos sin colisión (8898/8899) | __main__.py ambos | lectura | VERIFIED |
| V-52 | Rendimiento | Producción MIDI: 0,174 s / 22,3 MiB pico por pista | `/usr/bin/time -v` TEST01 | terminal | VERIFIED |
| V-53 | Rendimiento | RAM WAV/rendimiento Windows | — | — | ESTIMACIÓN (100–250 MB) |
| V-54 | Protección post | Re-check hashes protegidos al cierre | concatenado estable; 0 fuentes M en git delta | git status | VERIFIED |

**Conclusión de la matriz**: 40+ verificaciones VERIFIED con evidencia física; los UNVERIFIED/NOT AVAILABLE están concentrados exclusivamente en lo Windows-only (FluidSynth real, sfizz, soundfonts, ffmpeg.exe) y tienen comandos de verificación listos (`AUDIT_AUDIO_RENDERING.md §6`).
