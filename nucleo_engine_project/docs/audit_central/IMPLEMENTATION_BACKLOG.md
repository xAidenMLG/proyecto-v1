# IMPLEMENTATION_BACKLOG — Backlog técnico priorizado

> ⚠️ **SUPERSEDED (2026-11-11, misión de planificación v1.2).** El backlog
> OFICIAL de DMD Composer es ahora la sección 9 de
> `DMD_Composer/IMPLEMENTATION_ROADMAP.md` (tareas C-01…C-13). Tareas
> **EXCLUIDAS del producto** por la decisión D22 (`DMD_Composer/DECISIONS.md`):
> B-15 (Soundfont Manager), B-16 (render WAV), B-17 (player `<audio>` de
> ficheros), B-18 (MP3/loudnorm), B-21 (stems SF2+ffmpeg) y todo lo dependiente
> de FluidSynth/soundfonts/ffmpeg en Composer. Las tareas B-08…B-10, B-11…B-14
> (producción MIDI y álbumes) y los fixes B-01…B-07 conservan valor y fueron
> absorbidos/reordenados en el roadmap vigente. Este documento se conserva como
> historial.

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11 · Cada tarea con ID, archivos, dependencias, riesgo, prioridad, criterio de aceptación y pruebas. **Sin implementar.**
> Fase = fase del roadmap donde pertenece. Prioridad: P0 bloquea al objetivo general · P1 necesario para paridad de producción · P2 mejora · P3 opcional.

| ID | Fase | Descripción | Archivos/módulos | Dependencias | Riesgo | Prioridad | Criterio de aceptación | Pruebas |
|---|---|---|---|---|---|---|---|---|
| B-01 | 0 | Fix P0-1: importar `hashlib` y `random` en server.py | DMD_Composer/composer/server.py:12-33,465-466 | — | Bajo | **P0** | `POST /api/harmony/templates` → 200; determinista por mood+key | Test nuevo del endpoint (no existía); batería 114 |
| B-02 | 0 | Fix P0-2: hijo de Studio hereda `os.environ` + `PYTHONDONTWRITEBYTECODE=1` | studio/jobs.py:265-270 | — | Bajo | **P0** | Job con `wav=true` encuentra fluidsynth si existe (falla solo si no está instalado) | Job real en Windows; suite studio 13 |
| B-03 | 0 | Fix P0-3: escritura atómica de estado.json/huellas.json/plan.json (+.bak) | album/orquestador.py:57-60,210; album/planificador.py:318-324 | — | Medio (código FASE 8) | **P0** | Kill -9 entre pistas → estado íntegro o restaurado desde .bak | Test de corte simulado; suite fase8 39 |
| B-04 | 0 | Watchdog ~900 s por pista de álbum en el llamador + registro | composer/production.py (nuevo) | B-03 | Bajo | P1 | Pista colgada → fallo limpio, álbum continúa | Simulación de proceso bloqueado |
| B-05 | 0 | Límite de tamaño de cuerpo en Studio | studio/server.py | — | Bajo | P1 | Doc > límite → 413 con mensaje | Test con payload gigante |
| B-06 | 0 | `delete_project` tolerante a ficheros bloqueados + blindaje pid «albumes» | studio/projects.py:187-192; composer/store.py:165-174 | — | Bajo | P1 | Mensaje claro con el fichero bloqueado; «albumes» rechazado como pid | Tests unitarios |
| B-07 | 0 | `encoding="utf-8"` explícito en las tuberías de bridge.py | composer/bridge.py:72-78 | — | Bajo | P1 | Rutas con acentos sobreviven en Windows | Test con «Composición» |
| B-08 | 1 | Production Bridge pista individual (tarea `produce` en bridge + runner) | composer/production.py (nuevo), dmd_bridge_runner.py | B-01..B-03 | Medio | **P0** | MIDI real desde la UI con sha256; reproducibilidad byte-idéntica | TEST01 replicado + fallo controlado 422 E105 |
| B-09 | 1 | Endpoint `POST /generations/{gen}/produce` + estados por generación | composer/server.py | B-08 | Bajo | **P0** | Estado PLANNED→…→MIDI_READY visible; 409 single-flight | API tests |
| B-10 | 1 | Almacenamiento de tracks en `DMD_Library/Tracks/` con hashes | composer/library.py (nuevo) | B-08 | Bajo | P1 | Artefactos íntegros y verificables | Verificación sha |
| B-11 | 2 | `export_album_spec()` con esquema REAL dmd-album/1 + hash canónico + espejo docs/ | composer/albums.py | B-03 | Medio | **P0** | El export pasa `ES.cargar_album` sin A1xx/A2xx | Test de round-trip validar+planificar en seco |
| B-12 | 2 | Subproceso `python -m album producir` + polling estado.json → UI | composer/production.py, server.py, albums.py | B-11, B-04 | Medio | **P0** | Álbum 13 pistas producido con progreso por pista | Álbum real en sandbox + Windows |
| B-13 | 2 | Reintentos/cancelación de álbum (`--regen` / cancel del llamador) | composer/production.py | B-12 | Medio | P1 | Fallo de 1 pista no detiene el álbum; reintento selectivo funciona | Simulación de fallo + resume |
| B-14 | 2 | Renombrar label interno del plan de Composer (`dmd-composer-album-plan/1`) | composer/albums.py:58 | B-11 | Bajo | P2 | Sin colisión de nombre; compatibilidad con planes existentes (migración) | Suite G completa |
| B-15 | 3 | Soundfont Manager: descubrir/registrar/validar/re-vincular | composer/soundfonts.py (nuevo) | — | Bajo | P1 | Referencias rotas → error explícito con campo culpable | Test con fichero movido |
| B-16 | 3 | Render WAV v1 (un SF2 master) vía runner con env corregido | composer/audio_render.py (nuevo) | B-02, B-15, FluidSynth Windows | Medio | P1 | WAV con duración ≈ MIDI+cola; validación de duración post-render | 1ª ejecución real FluidSynth (probe Windows) |
| B-17 | 3 | Player `<audio>` WAV/MP3 con endpoints whitelisted | composer/static + server.py | B-16 | Bajo | P1 | Play/pause/stop/volumen/posición; descarga | E2E manual + API tests |
| B-18 | 4 | MP3 320k + ID3 + loudnorm 2p + alimiter + apad 2 s | composer/audio_render.py | B-16, ffmpeg.exe Windows | Bajo | P1 | −16 LUFS ±1, TP ≤−1.5, sin clip, metadatos | ffprobe + medición |
| B-19 | 5 | Project Library completa (índice, historial, recuperación, migraciones) | composer/library.py | B-10..B-18 | Medio | P1–P2 | Recuperación de sesión; reproducción de trabajos anteriores | Suite de persistencia |
| B-20 | 5 | Verificación de hashes de álbum (recomputar sha256 vs manifiesto) | composer/library.py | B-19 | Bajo | P2 | Detecta fichero alterado/truncado | Test de corrupción simulada |
| B-21 | 6 | Stems por canal SF2 + mezcla ffmpeg (v2 híbrido) | composer/audio_render.py | B-16/B-18 | Medio | P2 | 5 stems sincronizados + mezcla con limiter | Comparación de bordes de stems |
| B-22 | 6 | Integración sfizz (v3) tras probe en Windows | composer/audio_render.py + render_profile | B-21, probe sfizz | Alto (UNVERIFIED) | P2–P3 | Stem del canal 0 con SFZ o fallback GM documentado | Probe B1/B2 + render real |
| B-23 | 1 | Corregir «support» role informativo (UI sobre-promete) | composer/static/js/views.js:197; builder.py:453-462 | — | Bajo | P3 | UI describe el rol como informativo o el rol pasa a tener efecto (decisión) | UI + tests |
| B-24 | 1 | Campo muerto `production.wav`: conectar al perfil de render o eliminar del modelo | composer/model.py:181-182; engine.py:75-115 | B-16 | Bajo | P2 | El toggle WAV viaja al perfil de render real | Test de round-trip |
| B-25 | 2 | UI: controles de `loop_bars` y `harmony_sections.chord_bars/resolution` | composer/static/js/views.js:361-403,539-576 | — | Bajo | P2 | Campos editables desde la UI que ya viajan al doc | Suite B/C |
| B-26 | 2 | Informe de diversidad: rellenar tonalidad/BPM por pista en la UI | composer/static/js/views.js:905-913 | — | Bajo | P3 | Tabla sin celdas «—» | UI |
| B-27 | 3 | Logs con módulo `logging` (ficheros rotados) en Composer/Studio | composer/, studio/ | — | Bajo | P2 | Logs persistentes por corrida en Library/logs | Smoke test |
| B-28 | 4 | Cola de reverb ≥2 s en render WAV (coherencia con fallback navegador) | capa audio_render (no forge) | B-16 | Bajo | P2 | Duración WAV ≥ duración MIDI + 2 s | Medición |
| B-29 | — | Documentar bug velocity_cap drums (112–118 > 110) como hallazgo upstream forge | docs/ | — | Bajo | P3 | Registrado en DECISIONS/limitaciones (forge protegido: no tocar) | — |
| B-30 | — | Evaluar `sys.dont_write_bytecode` en forge_link (gap .pyc) — requiere autorización (toca zona sensible) | jazz_engine/forge_link.py:112-140 | autorización usuario | Medio | P3 | 0 `.pyc` nuevos en forge/ tras producción | TEST11 replicado |
| B-31 | 2 | Asistente de import de JSON externos (ChatGPT) con validación previa real | composer/server.py, UI | — | Bajo | P2 | Import → validación real → error/éxito claros | Test con docs externos |
| B-32 | 5 | Export/backup de álbum completo (zip con hashes) para mover entre máquinas | composer/library.py | B-19 | Bajo | P3 | Zip verificable con manifiesto | Round-trip |

Notas:
- B-01/B-02/B-03/B-11/B-12 son el **camino crítico** hacia el objetivo de la misión (producir MIDI/álbumes desde Composer).
- Ninguna tarea toca `forge/`, `dark_director/contract.py`, `dark_director/identities/dark_triphop.py`, goldens ni DMD Studio salvo los fixes puntuales de `studio/` (B-02/B-05/B-06) — que son del árbol `studio/` (no de la UI protegida de producción) y deben confirmarse con el usuario si considera Studio congelado.
