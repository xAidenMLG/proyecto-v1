# PROJECT STATE — DMD COMPOSER

Estado: **1.2 — INTEGRACIÓN MIDI IMPLEMENTADA Y VALIDADA** (2026-11-11, misión de implementación; 128 tests en verde)

v1.0 (misión completada) + v1.1 (auditoría → causa raíz → correcciones → QA)
+ **v1.2 (planificación oficial: MIDI + reproducción + álbumes; sin
implementación)**.

## Ámbito de producto vigente (v1.2 — manda `IMPLEMENTATION_ROADMAP.md`)

DMD Composer es una **aplicación de composición musical y producción MIDI**:
genera documentos `dark-director/1`, **genera MIDI por el pipeline existente**
(`scripts/produce.py::producir_cancion` vía puente aislado), lo persiste con
SHA256, lo deja descargar, **lo reproduce en el navegador** (Player WebAudio
de Forge reutilizado + `events.json`) y **crea/gestiona álbumes completos**
(13 pistas) con generación por lotes.

**Composer NO es una aplicación de conversión de audio** (decisión D22): MP3,
WAV, FluidSynth, sfizz, SF2/SFZ, soundfonts, masterizado y workers de audio
están EXCLUIDOS del producto. El usuario convierte MIDI→audio con su
aplicación Python externa por lotes. Este ámbito SUPERSEDE la lectura v1.0/1.1
de "Composer no genera MIDI" (D2, ver DECISIONS.md D21–D28).

## Qué existe y funciona HOY (v1.1 — sin tocar por esta misión)

| Módulo | Estado | Prueba |
|---|---|---|
| Módulo A — Musical Identity Designer | completo + PROPUESTA de distribución del protagonista (focus/active/enabled/density, campos reales; aceptar/modificar/rechazar) y identidades archivadas marcadas | UI Setup + tests D/I |
| Módulo B — Structural Composer | completo (sin cambios funcionales en 1.1) | tests B |
| Módulo C — Harmonic Composer | completo + semántica definitiva Native/Guided (sin conversión silenciosa, avisos explícitos, modo real en manifest/Song Map) + editor de ACORDES LITERALES por sección prevalidados con `forge/theory` real | tests A/C/I |
| Módulo D — Coherent Randomizer | completo + estados reales por eje, descartadas registradas, groove≠tempo documentado, protagonista auto=LEAD de receta | tests D/I |
| Módulo E — Song Map | completo + fuente armónica por sección coherente con el compilador real (incluye acordes literales) | tests E/I |
| Salida | doc validado por el validador REAL + compilado por el compilador REAL + manifest v1.1 (decisiones disjuntas fijadas/automáticas/libres + preferencias + producción como instrucción pendiente) | tests F/H/I |
| Modo álbum | planificador + generate_all reanudable + informe de diversidad (círculo de quintas corregido); la producción MIDI sigue siendo del pipeline DMD | tests G/I |
| UI 6 pantallas | + botón Verificar DMD, propuesta de protagonista, acordes literales con prevalidación real, instrucción de producción en Output, álbum en lote | evidencia UI v1.1 |
| Seguridad | solo 127.0.0.1, sin eval/exec/shell, path traversal bloqueado, límites, escritura atómica | tests H |

## Qué se IMPLEMENTÓ en la misión de integración (v1.2)

| Fase | Implementación | Prueba |
|---|---|---|
| 1 — Producción MIDI individual | COMPLETA: tarea `produce` del puente (hijo aislado cancelable), persistencia `midi/<nombre>/`, bloque `midi` del manifest, estado `aplicado` solo con SHA256 verificado, descarga con whitelist, idempotencia, jobs con cancelación/recuperación | batería J (10 tests) + E2E hito 1 24/24 |
| 2 — Reproducción | COMPLETA: `player.js` (copia literal del Player de Forge), controles ▶/■, events.json (Opción A, default OFF en el núcleo), disclaimer WebAudio≠soundfont | batería J + verificación audible pendiente en Windows (W1) |
| 3 — Álbumes completos | COMPLETA: materialización dmd-album/1 + orquestador REAL del DMD en subprocess aislado, estados por pista (estado.json), reanudación, --regen por pista, cancelación, descarga y events verificados por pista | batería K (4 tests) + E2E álbum 19/19 |
| 4 — Validación E2E | COMPLETA (parte Composer): baterías J+K con servidor real HTTP + núcleo real | docs/TEST_REPORT.md |
| 5/6 | NO INICIADAS (congelación y revisión arquitectónica: requieren decisión aparte) | — |

Regresión: 128/128 tests (A–I 114 + J 10 + K 4) + 36 tests de Forge + 4 de
regresión events del núcleo. F6 (hashes de protegidos) en verde.

## Qué se PLANIFICÓ en v1.2 (historial de planificación)

| Fase | Objetivo | Estado |
|---|---|---|
| 1 — Producción MIDI individual | del doc validado al MIDI descargado con SHA256 y evidencia, vía tarea `produce` del puente | PLANIFICADA (requiere autorización del hito 1) |
| 2 — Reproducción MIDI | Player WebAudio original de Forge + `events.json` (Opción A con autorización) | PLANIFICADA |
| 3 — Creador de álbumes completos | config de álbum/pista, lote 13 pistas, reanudación/cancelación; reutiliza `album/` | PLANIFICADA |
| 4 — Validación end-to-end | cadena completa sin el convertidor externo | PLANIFICADA |
| 5 — Congelación funcional | contratos, artefactos, goldens MIDI | PLANIFICADA |
| 6 — Revisión arquitectónica / Plan B | contingencia; no se inicia reescritura | PRESERVADA |

Detalle completo: `IMPLEMENTATION_ROADMAP.md` (ficheros exactos por fase,
artefactos, criterios de aceptación, backlog C-01…C-13).

## Números clave (v1.1, siguen vigentes)

* **114 tests** (A–H + batería I) en verde, incluidos MIDI real y reproducibilidad
  byte a byte.
* **5 demostraciones** reproducibles (SHA256 idénticos a 1.0: los docs no cambiaron).
* **0 campos inventados** (test A2 contra el validador real; el QA lo re-verificó
  dinámicamente: 0 E109).
* **10 archivos protegidos** de DMD/Studio/forge/golden con hash intacto (F6 + QA).

## Decisiones que hay que MANTENER (ver DECISIONS.md)

1. Composer produce documentos `dark-director/1` y **desde v1.2 genera MIDI
   SOLO por el pipeline existente vía puente aislado** (D21/D23; sustituye a
   la antigua regla "Composer no genera MIDI").
2. Puente por subprocess aislado; nunca importar DMD en el proceso de Composer.
3. Catálogos desde introspección viva; la instantánea builtin es fallback
   verificable, no fuente paralela.
4. Precedencia de acordes §2.8 respetada (ahora también section.chords literales);
   progressions por id de sección.
5. `auto` escribe; `free` no. Las fijadas nunca se corrigen en silencio.
6. (v1.1) Un estado REAL por eje en el manifest; el perfil de producción es una
   INSTRUCCIÓN pendiente de aplicar, nunca un valor "aplicado" (pasará a
   "aplicado" solo con `midi_sha256` real como evidencia).
7. (v1.2) **Sin render de audio en Composer, jamás** (D22); reproducción solo
   con el Player WebAudio original + `events.json` (D24/D25); álbumes =
   función nuclear reutilizando el orquestador existente (D27); congelación
   funcional antes de reestructuración (D28).

## Próximos pasos

Ver `IMPLEMENTATION_ROADMAP.md` (oficial) y `NEXT_MISSION.md` (hito 1 a
autorizar). El antiguo punto "WAV opcional vía Studio" quedó SUPERSEDED por
D22: la conversión de audio es y sigue siendo externa.
