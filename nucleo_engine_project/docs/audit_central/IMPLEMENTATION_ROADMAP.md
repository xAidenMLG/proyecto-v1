# IMPLEMENTATION_ROADMAP — Plan de implementación por fases

> ⚠️ **SUPERSEDED (2026-11-11, misión de planificación v1.2).** El roadmap
> OFICIAL de DMD Composer es ahora `DMD_Composer/IMPLEMENTATION_ROADMAP.md`.
> Consecuencias por la decisión D22 (`DMD_Composer/DECISIONS.md`):
> la antigua Fase 3 (audio: `composer/soundfonts.py`, `composer/audio_render.py`,
> render WAV vía FluidSynth, player `<audio>`) y cualquier tarea de MP3/WAV/
> soundfonts/stems quedan **EXCLUIDAS del producto** — la conversión de audio es
> una aplicación Python EXTERNA del usuario. La Fase 0 (fixes P0/P1) conserva
> valor y fue absorbida como prerrequisito de la nueva Fase 1; la antigua Fase
> de álbumes fue reordenada como nueva Fase 3. Este documento se conserva como
> historial de la auditoría de ecosistema; NO debe usarse como plan vigente.

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11 · Plan derivado de la evidencia. **Esta misión NO implementó ninguna fase.**
> Orden ajustado respecto al propuesto por la misión (§8 permite proponer otro orden con justificación): el reproductor MIDI sin render WAV es inviable sin dependencias nuevas, y la producción batch reutiliza infraestructura ya VERIFIED — por eso álbumes va antes que audio. *(Justificación histórica, hoy sin efecto: la reproducción sin WAV SÍ es viable con el Player WebAudio de Forge; ver roadmap v1.2, Fase 2.)*

---

## Fase 0 — Preparación y fixes de robustez (prerrequisito)

| Campo | Contenido |
|---|---|
| **Objetivo** | Eliminar los 4 riesgos P0/P1 que afectan a cualquier integración posterior |
| **Cambios** | (1) `DMD_Composer/composer/server.py`: `import hashlib, random` (fix P0-1, l.465-466); (2) `studio/jobs.py:265-270`: `env={**os.environ, PYTHONIOENCODING…, PYTHONDONTWRITEBYTECODE:"1"}` (fix P0-2); (3) `album/orquestador.py:57-60,210` + `planificador.py:318-324`: escritura atómica tmp+`os.replace`+`.bak` (fix P0-3); (4) watchdog ~900 s por pista en el llamador de álbumes + límite de cuerpo en Studio (P1) |
| **Módulos afectados** | composer/server.py · studio/jobs.py · studio/server.py · album/orquestador.py · album/planificador.py |
| **Dependencias** | Ninguna nueva |
| **Contratos** | Ninguno cambia (fixes internos) |
| **Pruebas** | Test nuevo del endpoint `/api/harmony/templates` (200 + determinismo por mood+key); job de Studio con `wav=true` tras fix (falla solo si FluidSynth ausente real); test de corte simulado (estado.json truncado → `.bak` restaura); suites completas de regresión: 114 Composer + 13 Studio + 171 dmd + 39 fase8 |
| **Criterios de aceptación** | 0 regresiones; endpoint de plantillas en verde; `estado.json` sobrevive a un kill -9 entre pistas; hijo de Studio hereda PATH |
| **Riesgos** | `album/` es código FASE 8 activo — cambios mínimos y con tests (no protegido, pero sensible) |
| **Qué no tocar** | forge/, contract.py, dark_triphop.py, goldens, semántica de estados |

## Fase 1 — Producción MIDI desde Composer (pista individual)

| Campo | Contenido |
|---|---|
| **Objetivo** | Botón «Producir MIDI» por generación: doc → MIDI real en la Library, con estado y verificación |
| **Cambios** | Nuevo `composer/production.py` + tarea `"produce"` en `dmd_bridge_runner.py` (patrón VERIFIED); endpoint `POST /api/projects/{pid}/generations/{gen}/produce`; traducción del `produccion.instruccion` a llamada real; almacenamiento bajo `DMD_Library/Tracks/<pid>/gen_NNNN/` |
| **Dependencias** | Fase 0 |
| **Contratos** | Entrada/salida del bridge (AUDIT_PRODUCTION_PIPELINE §8): out_dir único, indice=False, verify=sha256 |
| **Pruebas** | Producir 1 pista real en sandbox (TEST01 ya demostró viabilidad) y en Windows; comparar sha con `--verify`; fallo controlado (doc roto → 422 con E105); timeout; cancelación |
| **Criterios de aceptación** | Desde la UI: MIDI listo con sha256 mostrado; reproducibilidad byte-idéntica re-ejecutada; sin escrituras fuera de la Library |
| **Riesgos** | R2 (nombre MIDI = carpeta) — el bridge controla el slug |
| **Qué no tocar** | produce.py (usar su API), Studio |

## Fase 2 — Producción de álbumes (batch 13 pistas)

| Campo | Contenido |
|---|---|
| **Objetivo** | «Producir álbum» completo con progreso por pista, reintentos y recuperación |
| **Cambios** | `export_album_spec()` en albums.py (esquema REAL + hash canónico + espejo docs/); endpoint de producción de álbum como **subproceso** `python -m album producir --out DMD_Library/Albums/<slug>`; polling de `estado.json` → estados por pista en la UI; botones Reintentar (`--regen`) / Cancelar |
| **Dependencias** | Fases 0-1 |
| **Contratos** | AUDIT_ALBUM_AUTOMATION §7 (export spec real; nunca el plan interno) |
| **Pruebas** | Álbum de 13 pistas generado por Composer → producido por orquestador en sandbox; matar el proceso a mitad → resume exacto; 1 doc corrupto → aislado (13-1 ok); drift → `pendiente` sin pérdida |
| **Criterios de aceptación** | 13/13 MIDIs con hashes y manifiesto; reanudación sin regenerar lo aceptado; UI muestra estado real por pista |
| **Riesgos** | Colisión de label `dmd-album/1` (documentada; el export usa el esquema real, no el plan interno) |
| **Qué no tocar** | La semántica del orquestador (resume/drift) |

## Fase 3 — Soundfont Manager + Render WAV + Player

| Campo | Contenido |
|---|---|
| **Objetivo** | Escuchar la música dentro de Composer |
| **Cambios** | `composer/soundfonts.py` (descubrir/registrar/validar referencias; autodetect GeneralUser-GS como master); `composer/audio_render.py` v1 (WAV vía `forge/audio.render_wav` dentro del runner hijo con env corregido); endpoint de descarga streaming whitelisted; vista Player `<audio>` |
| **Dependencias** | Fases 0-2; FluidSynth+sf2 presentes en Windows (VERIFICAR con comandos de AUDIT_AUDIO_RENDERING §6); en sandbox queda limitado (sin FluidSynth) |
| **Contratos** | `render_profile.json` v1 (un SF2 master); `soundfonts.json` referencias |
| **Pruebas** | 1ª ejecución real de FluidSynth en Windows (pasa de PARTIALLY a VERIFIED): duración ≈ MIDI+cola; MP3 320k con ID3; referencias rotas → error explícito |
| **Criterios de aceptación** | Pista y álbum escuchables desde Composer; fallo de audio NO invalida el MIDI (estados separados) |
| **Riesgos** | Rendimiento WAV en Windows (ESTIMACIÓN pendiente); cola de reverb ausente en render (apad en mezcla) |
| **Qué no tocar** | forge/audio.py (usar como librería) |

## Fase 4 — MP3 + master + metadatos

| Campo | Contenido |
|---|---|
| **Objetivo** | Entregable final MP3 por pista/álbum |
| **Cambios** | Extensión de `audio_render.py`: ffmpeg `-b:a 320k` + ID3 (title/artist/album=álbum, track nº) + loudnorm 2 pasadas + alimiter + apad 2 s |
| **Dependencias** | Fase 3; ffmpeg.exe/lame.exe localizados en Windows |
| **Pruebas** | Encode en sandbox ya VERIFIED; repetir sobre WAV real de FluidSynth; clipping/duraciones verificados con ffprobe |
| **Criterios de aceptación** | MP3 −16 LUFS ±1, TP ≤ −1.5 dBFS, sin clip, metadatos correctos |
| **Qué no tocar** | Parámetros por defecto de forge/audio (192k) salvo override del perfil |

## Fase 5 — Project Library completa

| Campo | Contenido |
|---|---|
| **Objetivo** | Historial, recuperación y reproducción de cualquier trabajo anterior |
| **Cambios** | `composer/library.py` (índice de álbumes/trabajos, verificación de hashes, re-vinculación de soundfonts, limpieza de temporales, migraciones por schema_version); vistas Biblioteca (Nivel 4 de la misión) |
| **Dependencias** | Fases 1-4 |
| **Pruebas** | Mover un soundfont → detección rota; importar/liberar álbum antiguo; reproducción de un trabajo anterior sin regenerar |
| **Criterios de aceptación** | Recuperación de sesión completa; 0 duplicados de álbum; hashes verificables |
| **Qué no tocar** | `output/` histórico y goldens |

## Fase 6 (opcional) — Render híbrido SF2/SFZ por instrumento

| Campo | Contenido |
|---|---|
| **Objetivo** | Tabla instrumento→motor→biblioteca (sax→sfizz, resto→SF2) |
| **Cambios** | Stems por canal (v2) + sfizz (v3) según AUDIT_HYBRID_RENDER_ARCHITECTURE |
| **Dependencias** | Fase 3-4 + verificación sfizz en Windows (ruta B1/B2 del documento híbrido) |
| **Criterios de aceptación** | Mezcla final sincronizada; fallback GM si sfizz falla; MIDI fuente intacto (sha) |
| **Qué no tocar** | El MIDI fuente; sin dependencias Python nuevas |

## Orden y dependencias (diagrama)

```
F0 fixes ──► F1 MIDI por pista ──► F2 Álbum batch ──► F3 SF2+WAV+Player ──► F4 MP3 ──► F5 Library ──► F6 híbrido (opcional)
```

Cada fase entrega valor usable por sí misma y ninguna toca motores protegidos ni el contrato rev 3.2.
