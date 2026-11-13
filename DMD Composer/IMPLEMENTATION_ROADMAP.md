# IMPLEMENTATION_ROADMAP — DMD COMPOSER (v1.2)

> **ACTUALIZACIÓN (misión de implementación, 2026-11-11):** las Fases 1–3
> están IMPLEMENTADAS Y VALIDADAS (baterías J y K + E2E; 128/128 tests;
> evidencia en `docs/TEST_REPORT.md`; decisiones D29/D30 en `DECISIONS.md`).
> Las Fases 5–6 (congelación, revisión arquitectónica) siguen PENDIENTES de
> decisión del usuario. La "única excepción" de §10.2 (Opción A) fue
> autorizada y ejecutada por esa misión.

> **Documento AUTORITATIVO de planificación.** Fecha: 2026-11-11 · Misión:
> "Update Official DMD Composer Project Plan — MIDI Generation + MIDI Playback
> + Complete Album Creator". **Esta misión NO implementó ninguna fase, no
> modificó código de producción ni instaló dependencias.**
>
> **Supersede:** el roadmap/backlog de `nucleo_engine_project/docs/audit_central/`
> (misión de auditoría de ecosistema) queda SUPERSEDED por este documento en lo
> relativo a Composer; sus fases de audio (render WAV/MP3, soundfonts, stems)
> quedan **EXCLUIDAS del producto** por la decisión D22
> (`DMD_Composer/DECISIONS.md`). El antiguo `NEXT_MISSION.md` se reordena en
> función de este roadmap.
>
> **Fuente de verdad técnica:** auditorías cerradas y verificadas
> `download/FORGE_MIDI_GENERATION_AUDIT.md`,
> `download/FORGE_MIDI_PLAYBACK_AUDIT.md`,
> `download/COMPOSER_INTEGRATION_ANALYSIS.md` y
> `download/RECOMMENDED_INTEGRATION_ARCHITECTURE.md`.

---

## 0. Ámbito de producto (lectura obligatoria)

### 0.1 Lo que Composer ES (desde v1.2)

DMD Composer es una **aplicación de composición musical y producción MIDI**:

1. Dirección musical y composición (decisiones fijadas/automáticas/libres).
2. Generación de documentos `dark-director/1` (rev 3.2) + Song Map.
3. Configuración de parámetros musicales, armonía y progresiones.
4. **Generación de MIDI a través del pipeline de producción existente**
   (DMD Compiler → Jazz Engine → MIDI Forge), nunca con un segundo motor.
5. **Persistencia y descarga del MIDI** generado.
6. **Reproducción del MIDI dentro de Composer** (Player WebAudio del navegador).
7. **Creación y gestión de álbumes completos** (típicamente 13 pistas).
8. Generación MIDI por lotes con estados, reintentos, cancelación y recuperación.
9. Gestión de diversidad musical y estado de producción con evidencia (SHA256).

### 0.2 Lo que Composer NO ES (exclusión explícita, decisión D22)

Composer **NO es una aplicación de conversión de audio**. Quedan FUERA de su
roadmap, requisitos, arquitectura y backlog:

> MP3 · WAV · FluidSynth · sfizz · SF2/SFZ · soundfonts · masterizado de audio ·
> conversión de audio · workers de render de audio · perfiles de audio-rendering.

El usuario ya posee una **aplicación Python independiente** que convierte MIDI a
audio por lotes. Esa aplicación permanece independiente y no se duplica.

**Flujo externo esperado:** `DMD Composer → ficheros MIDI → convertidor Python
externo del usuario → ficheros de audio`.

### 0.3 Los diez puntos que el plan hace innegociables

Un desarrollador que lea esta documentación debe entender sin ambigüedad:

1. Composer genera **MIDI, no MP3**.
2. Composer reproduce MIDI mediante **WebAudio del navegador**.
3. La generación MIDI usa el **pipeline de producción existente**
   (`scripts/produce.py::producir_cancion`).
4. El **Player original de Forge se reutiliza** (no se crea otro sintetizador).
5. **events.json es imprescindible** para reproducir: el Player no lee `.mid`.
6. **No se necesita ninguna librería de conversión de audio** (ni FluidSynth,
   ni sfizz, ni soundfonts) en Composer.
7. La **creación de álbumes es una función nuclear** del producto.
8. La **orquestación de álbum existente se reutiliza** (no se compite con ella).
9. La **congelación funcional precede** a cualquier reestructuración
   arquitectónica.
10. **Esta misión de planificación no autoriza implementación alguna.**

---

## 1. Arquitectura objetivo de la generación MIDI

La ruta es la que Composer ya nombra en su instrucción de producción
(`composer/engine.py::_instruccion_produccion`), ejecutada ahora por el puente
aislado existente (patrón probado en `tests/test_f_integracion.py::F4/F5` y en
`studio/runner.py`):

```
DMD Composer UI (navegador, 127.0.0.1:8898)
│   Output / Álbum
│   ├── [Generar MIDI] ──► POST /api/projects/{pid}/generations/{gen}/midi
│   └── [▶ Escuchar]   ◄── events.json (artefacto del gen) + Player JS
▼
composer/server.py ──► composer/bridge.py::produce(...)
│                       spec JSON ≤ 8 MB · argv fijo · shell=False · timeout 300 s
▼
composer/dmd_bridge_runner.py::task_produce   (intérprete hijo AISLADO,
│                                              cwd/DMD descubierto en sys.path)
▼
scripts/produce.py::producir_cancion(doc, production, seed, harmony, out_dir)
│   dark_director.compilador.compilar → jazz_engine.render.generate
│   → forge (MIDI Forge) → forge.validate
▼
MIDI + evidencia + config_efectiva (subcarpeta del gen) + sha256
```

Reglas invariantes (ya vigentes, se conservan):

* Forge sigue siendo el ÚNICO motor MIDI; DMD Compiler y Jazz Engine siguen
  siendo los componentes de producción existentes.
* Composer **nunca importa** DMD/Forge en su proceso: todo va por subprocess.
* Determinismo: mismo doc + misma seed → MIDI byte a byte idéntico; SHA256
  registrado y verificable (`--verify`).
* Los directorios de generación son **inmutables**: el MIDI se escribe UNA vez
  en el gen que produjo su doc; un "regenerar" crea evidencia nueva con
  verificación SHA, nunca sobrescribe.
* El perfil de producción avanza de `seleccionado_pendiente_de_aplicar` a
  `aplicado` **solo** con el `midi_sha256` real como evidencia (cierra el hueco
  de honestidad que v1.1 dejó abierto deliberadamente).

---

## 2. FASE 1 — Producción MIDI individual

**Objetivo:** un usuario debe poder terminar UNA composición musical
completamente dentro de Composer: del documento validado al MIDI descargado,
con evidencia y estado visibles.

### 2.1 Capacidades requeridas

| # | Capacidad | Cómo |
|---|---|---|
| 1 | Generar un documento musical válido de Composer | ya existe (`engine.compose`) |
| 2 | Validar el documento | ya existe (validador REAL por puente) |
| 3 | Generar MIDI por el pipeline existente | NUEVO: tarea `produce` del puente |
| 4 | Guardar el MIDI en el directorio de generación correcto | NUEVO: `store` persiste la subcarpeta `midi/` |
| 5 | Registrar su SHA256 | NUEVO: bloque `midi` de `generation_manifest.json` |
| 6 | Preservar los metadatos de generación | bloque `midi` (perfil, seed, fecha, rutas) |
| 7 | Descargar el MIDI | NUEVO: whitelist de descargas ampliada |
| 8 | Mostrar estado de generación y errores | NUEVO: estados en UI Output |
| 9 | Reintentos seguros sin sobrescribir generaciones inmutables | nueva generación de evidencia + `--verify` SHA; el doc/gen nunca se reescribe |
| 10 | Conservar evidencia de producción y configuración efectiva | las escribe `producir_cancion` (`evidencia.json`, `config_efectiva.json`) |

### 2.2 Layout exacto de artefactos (basado en el almacenamiento existente)

`producir_cancion` escribe una **subcarpeta autocontenida** dentro del
directorio de generación (verificado en `scripts/produce.py:70-181`):

```
DMD_Composer/output/<pid>/gen_NNNN/            (inmutable — nunca sobrescribe)
├── doc.json                        (existente — documento dark-director/1)
├── song_map.json                   (existente)
├── song_map.csv                    (existente)
├── generation_manifest.json        (existente — GANA un bloque "midi")
└── midi/<nombre>/                  (NUEVO — escrita por producir_cancion)
    ├── doc.json                    (copia de evidencia: el doc EXACTO consumido)
    ├── config_efectiva.json        (config efectiva: perfil + seed + harmony normalizados)
    ├── <nombre>.mid                (EL MIDI descargable — bytes del pipeline)
    ├── evidencia.json              (sha256_midi, bpm, compases, duración_s,
    │                                compliance, versiones, orden de regeneración)
    └── events.json                 (FASE 2 · Opción A, con autorización)
```

* `<nombre>` lo deriva **el servidor** (del pid/gen o del título saneado);
  jamás del cliente (misma regla de seguridad que el resto de rutas).
* `evidencia.json` incluye el comando de regeneración con `--verify <sha>`,
  que es la base del reintento seguro (capacidad 9).
* `generation_manifest.json` gana el bloque:
  `"midi": {sha256, perfil, seed, generado_utc, rutas, estado}`.
* La whitelist de descarga (`server.py`, hoy `doc.json, song_map.json,
  song_map.csv, generation_manifest.json`) se amplía a los artefactos del
  bloque `midi` **por nombre derivado del manifest** (nunca paths del cliente).

### 2.3 Ficheros que cambian (Fase 1)

| Fichero | Cambio |
|---|---|
| `composer/dmd_bridge_runner.py` | NUEVA tarea `produce` (misma `_run_task`): carga `scripts/produce.py` por ruta (patrón `studio/runner.py::_load_produce_module`), llama `producir_cancion`, devuelve `{ok, sha256, midi, evidencia, perfil, seed, bpm, compases, duracion_s, compliance_fails/warns}` |
| `composer/bridge.py` | NUEVA función `bridge.produce(...)` + entrada `TIMEOUTS["produce"] = 300` (spec ≤ 8 MB, argv fijo, `shell=False`, UTF-8 en tuberías) |
| `composer/store.py` | helpers para la subcarpeta `midi/<nombre>/` + escritura del bloque `midi` del manifest (atómica) |
| `composer/engine.py` | avance del estado de producción del manifest (`pendiente → aplicado` SOLO con `midi_sha256`) |
| `composer/server.py` | endpoint `POST /api/projects/{pid}/generations/{gen}/midi` (+ estados de error 4xx limpios) + whitelist de descargas ampliada |
| `composer/static/js/views.js` | botón **Generar MIDI** + estados/errores/reintentos en Output |
| `composer/static/js/api.js` | cliente del nuevo endpoint |
| `tests/test_j_produccion.py` (NUEVO) | regresión + aceptación (ver §2.4) |
| `composer/__init__.py` | actualización del docstring de reglas (aclarar que "no duplicar pipeline" = "no segundo motor"; usarlo por puente es la ruta sancionada) |

**Con autorización explícita aparte (Opción A, §8):**
`nucleo_engine_project/scripts/produce.py` — parámetro aditivo `events=False`
que persiste `forge.engine.to_events(res)` como `events.json`.

### 2.4 Criterios de aceptación y pruebas (Fase 1)

1. **Regresión de determinismo:** con el nuevo parámetro de events DESACTIVADO
   (o antes de la Opción A), mismo doc + seed → MIDI **byte a byte idéntico**
   (extiende F5).
2. **Igualdad SHA256 triple:** `sha256(res.midi)` == MIDI escrito en disco ==
   `evidencia.json.sha256_midi` == valor del bloque `midi` del manifest.
3. F4 (MIDI real desde doc de Composer), F5 (reproducibilidad) y F6 (hashes de
   10 archivos protegidos intactos) siguen en verde.
4. Imposible sobrescribir: segunda petición de MIDI para el mismo gen → o
   idempotente (mismo SHA) o 409; nunca reescritura.
5. Path traversal: ids/`<nombre>` validados con las regex existentes
   (`safe_pid`/`safe_gen`); pruebas de nombres malignos.
6. Error de pipeline (doc inválido, perfil inexistente) → 4xx con mensaje del
   validador/motor, sin artefactos parciales huérfanos (limpieza).
7. La batería completa (114 tests) sigue en verde.

---

## 3. FASE 2 — Reproducción MIDI dentro de Composer

**Objetivo:** escuchar las composiciones generadas dentro de Composer.

### 3.1 Decisión de diseño (D24/D25)

Se **reutiliza la clase `Player` original de Forge** (`web/app.js:442-522`,
~80 líneas) copiada **literalmente** como módulo propio. Es un sintetizador
WebAudio del navegador: sin dependencias Python, sin procesos, sin FluidSynth,
sin soundfonts, sin paquetes externos.

**Distinción crítica (documentada en la especificación de producto):**
el Player **NO lee ficheros `.mid` arbitrarios**. Consume la representación de
eventos musicales que genera `forge.engine.to_events(res)`. Por eso cada
generación produce **dos artefactos asociados**:

* `<nombre>.mid` — el MIDI real descargable (para el convertidor externo).
* `events.json` — los datos de reproducción del navegador.

Y otra distinción de honestidad de producto: **el sonido WebAudio es una
PREVIEW de síntesis** (osciladores por rol), no necesariamente idéntica al
render que el usuario obtiene con su soundfont/convertidor externo. Esta
advertencia se mostrará junto al reproductor.

### 3.2 Cierre de dependencias del Player (auditado; lo que SÍ y NO requiere)

| SÍ requiere (verificado en auditoría de reproducción) | NO requiere |
|---|---|
| Formato `to_events`: `bpm, total_beats, bar_beats, tracks[{id, role, notes[[beat,dur,pitch,vel]], bends, expr, volume, pan, gain}], sections` + mapa global `hidden` de pistas visibles | Estado global de la app de Forge |
| `start(startBeat)` / `stop()` con **cierre determinista del AudioContext** | Funciones MP3/WAV de Forge (`renderOffline`, lamejs, `/api/mp3`, `/api/wav`) |
| Bomba de programación 120 ms con horizonte 1.2 s + reloj `requestAnimationFrame` | FluidSynth · sfizz · SF2/SFZ · soundfonts |
| Guardia anti-solapamiento (una sola sesión: variable global + guard de `togglePlay`) | pygame · mido · python-rtmidi · winsound · MCI de Windows |
| Reanudación desde `seekBeat` tras stop manual (solo el fin natural resetea) | Paquetes JS externos · build step |
| Tolerancia a nota fallida (try/catch por nota) | Procesos/subprocess/hilos de Python |
| Mensaje explícito si no hay WebAudio ("Este navegador no soporta WebAudio.") | — |

### 3.3 Capacidades requeridas

| # | Capacidad |
|---|---|
| 1 | Reutilizar la clase Player original (copia literal, cierre de dependencias verificado) |
| 2 | Añadir el módulo JS mínimo a Composer (`player.js`); NO copiar la app de Forge entera |
| 3 | Generar y persistir `events.json` (Opción A, §8) |
| 4 | Cargar `events.json` de la generación correspondiente |
| 5 | Controles Reproducir y Parar |
| 6 | Pausa/stop y reanudación coherentes con el Player original |
| 7 | Prevenir sesiones de reproducción solapadas |
| 8 | Limpiar AudioContext y eventos programados |
| 9 | Manejar datos de eventos inválidos (validación de forma antes de `start`) |
| 10 | Degradir con gracia si no hay soporte WebAudio |
| 11 | Reproducir distintas generaciones (carga del events.json del gen seleccionado) |

### 3.4 Ficheros que cambian (Fase 2)

| Fichero | Cambio |
|---|---|
| `composer/static/js/player.js` (NUEVO) | clase Player copiada literal de `web/app.js:442-522` + patrón guard de `togglePlay` (`app.js:523-534`); autocontenida |
| `composer/static/js/views.js` | controles ▶ Escuchar / ■ Parar en Output (y por pista de álbum en Fase 3); carga de events.json por gen; visibilidad de pistas (`hidden`); manejo de errores (events ausente/inválido, WebAudio ausente) |
| `composer/server.py` | servir `events.json` y `.mid` desde el gen (whitelist ya ampliada en Fase 1); Content-Type correcto |
| `scripts/produce.py` (solo Opción A) | parámetro `events` (ver §8) |

### 3.5 Criterios de aceptación (Fase 2)

1. El Player reproduce el events.json de cualquier generación listada.
2. Solapamiento imposible: doble clic → una sola sesión y un solo estado de botón.
3. Stop → reanudación desde la posición retenida; fin natural → reset a 0.
4. Tras stop no quedan timers ni AudioContext abiertos.
5. events.json ausente/corrupto → mensaje claro, sin excepción en consola.
6. Navegador sin WebAudio → mensaje explícito y UI utilizable.
7. **L4 (verificación Windows): confirmación audible en el navegador del
   usuario** (en sandbox solo se verificó el ciclo de vida, no el audio real).

---

## 4. FASE 3 — Creador de álbumes completos (función nuclear)

**Objetivo:** crear y gestionar álbumes completos (normalmente 13 pistas) con
configuración a nivel álbum, configuración por pista, generación individual y
por lotes, y estados por pista.

**REGLA:** inspeccionar el planificador y orquestador existentes ANTES de
diseñar; **reutilizar el orquestador de producción de 13 pistas existente**
(`nucleo_engine_project/album/orquestador.py` + `planificador.py` +
`diversidad.py`, SOLO LECTURA). Composer se convierte en la interfaz central de
este flujo; **prohibido crear un motor de generación de álbumes competidor**.

### 4.1 Configuración a nivel álbum

Nombre y metadatos del álbum · dirección musical · género e identidad estilística
principal · preferencias y rangos de tempo · atmósfera musical · estrategia
armónica · preferencias de progresión · preferencias de instrumentación · perfil
de producción · restricciones de diversidad · seed y reproducibilidad.

### 4.2 Configuración de armonía (conservar lo existente)

* Se conservan los modos **Native y Guided** existentes con su semántica v1.1
  (D16: sin conversión silenciosa, avisos explícitos, modo real en manifest).
* El usuario puede: elegir progresiones familiares donde esté soportado ·
  configurar preferencias de progresión · elegir direcciones armónicas
  DISTINTAS por pista · conservar la ruta de generación original sin
  biblioteca de progresiones forzada.
* **Las progresiones familiares (F7) son un recurso musical OPCIONAL, nunca un
  default obligatorio** (regla 5/6 vigentes; el doc NUNCA lleva keywords F7 —
  test A6). No se impone una única progresión a todo el álbum salvo petición
  explícita.
* Se usa el parser teórico REAL de Forge/DMD y la arquitectura armónica de
  Composer (`harmony.py` + `forge/theory.parse_chord` vía puente).
  **Prohibido inventar otro parser de acordes.**

### 4.3 Configuración por pista

Dirección musical individual · importación opcional de JSON personalizado ·
elecciones armónicas individuales · tempo y parámetros estructurales individuales
donde soportado · decisiones de protagonista e instrumentación · **previsualización
de la configuración musical antes de generar**.

### 4.4 Generación de álbum

Generar todos los documentos de pista · generar MIDI de pistas individuales ·
generar MIDI por lotes · estados individuales de documento y de MIDI por pista ·
preservar la diversidad musical (huellas, rotación de tonalidades, seeds
independientes — lo ya construido en `albums.py`) · reintentos por pista ·
cancelación · recuperación tras interrupción · **no regenerar innecesariamente
pistas válidas** · preservar manifests y hashes.

### 4.5 Ficheros que cambian (Fase 3)

| Fichero | Cambio |
|---|---|
| `composer/albums.py` | configuración de álbum (§4.1) y por pista (§4.3) sobre el planificador existente (`dmd-album/1` + huellas + reanudación, ya construidos) |
| `composer/jobs.py` (NUEVO) | disciplina de `studio/jobs.py`: UN trabajo activo (2ª petición → 409), estado persistido `jobs/<jid>.json` + log vivo, timeout duro, `recover_interrupted()` al arranque, cancelación |
| `composer/server.py` | endpoints: `POST /api/albums/{id}/tracks/{n}/midi` · `POST /api/albums/{id}/produce_all` · cancelar · reintentar pista; estados por pista |
| `composer/bridge.py` + `composer/dmd_bridge_runner.py` | lote reutilizando la tarea `produce` (y/o subproceso `python -m album producir` para el orquestador completo — decisión a tomar, ver §10) |
| `composer/static/js/views.js` | vista Álbum: editor de config de álbum, config por pista, previsualización, columna de estado MIDI por pista, reintentos, cancelación, progreso |
| `composer/static/js/player.js` | reproducción de pistas del álbum (mismo Player) |
| `composer/model.py` | campos de configuración de álbum si el modelo actual no los cubre |
| `tests/test_k_album_produccion.py` (NUEVO) | lote 13 pistas, reanudación, cancelación, aislado de pista fallida, no-regeneración de pistas válidas |
| **SOLO LECTURA (no modificar):** `album/orquestador.py`, `album/planificador.py`, `album/diversidad.py` | orquestador existente REUTILIZADO |

---

## 5. FASE 4 — Validación end-to-end

Cadena completa a validar, sin el convertidor de audio externo:

```
Composición → JSON musical → Validación → Generación MIDI → Almacenamiento
→ Reproducción → Generación de álbum → Producción MIDI por lotes
→ Recuperación y exportación
```

Checklist E2E documentado en `docs/TEST_REPORT.md` (sección nueva) +
pruebas automatizadas de las fases 1–3 ejecutadas juntas sobre un proyecto real
(1 canción completa + 1 álbum de 13 pistas, con kill/reanudación simulada y
exportación/verificación de todos los artefactos y SHA256).

---

## 6. FASE 5 — Congelación funcional

Solo cuando la generación individual, la reproducción y la producción de
álbumes funcionen de forma fiable:

1. Congelar contratos (API de Composer, formato de `generation_manifest.json`
   y del bloque `midi`, layout de artefactos).
2. Congelar estructura de artefactos (§2.2) y flujos de usuario.
3. Preservar tests de regresión como obligación (114 + J + K).
4. Documentar interfaces estables.
5. Establecer **referencias MIDI doradas** (goldens de Composer: doc+seed →
   SHA256 MIDI) en `composer_data/golden/`.
6. Establecer tests de aceptación de producción de álbumes.

Solo DESPUÉS de esta fase se evaluará una reestructuración arquitectónica.

## 7. FASE 6 — Revisión arquitectónica / Plan B

Se PRESERVA la opción de rediseñar Forge, Studio y Composer en una aplicación
más integrada. Es una **contingencia arquitectónica, no trabajo actual**: no se
inicia ninguna reescritura. Este roadmap no la especifica.

---

## 8. events.json — Opción A seleccionada (no implementada; requiere autorización)

**Decisión (D26):** se selecciona la **Opción A** como arquitectura preferida:

> Añadir a `scripts/produce.py::producir_cancion` un parámetro **opcional y
> desactivado por defecto** (p. ej. `events=False`) que, cuando sea verdadero,
> persista `forge.engine.to_events(res)` como `events.json` en `out_dir` y añada
> la ruta a su dict de retorno (~4 líneas). El resultado de generación ya está
> en memoria en ese punto.

| | Opción A (SELECCIONADA) | Opción B (descartada, no en silencio) |
|---|---|---|
| Cambio | parámetro aditivo en `produce.py` (fuera de la lista de protegidos, pero es código de producción) | ninguna modificación de `produce.py` |
| Cómputo | UNA generación | DOS generaciones deterministas (re-derivar eventos re-ejecutando compilador+render en el hijo) |
| Correspondencia | eventos == MIDI generado (mismo `res`) | igualdad verificada en-tarea (sha256(res.midi) == sha256(.mid)) |
| Coste | mínimo y controlado | tiempo extra (~segundos por pista) + complejidad innecesaria |

Condiciones OBLIGATORIAS cuando se autorice su implementación:

1. Registrar el cambio explícitamente (CHANGELOG + decisión D26).
2. Mantenerlo opcional y **desactivado por defecto**; el comportamiento del CLI
   existente queda intacto.
3. Tests de regresión que prueben **MIDI byte-idéntico** con y sin la opción.
4. Igualdad SHA256 entre el MIDI escrito y el MIDI representado por el
   resultado capturado.
5. **NO se implementa en esta misión.** Queda marcada como una modificación
   pequeña, identificada explícitamente, del script de producción, que
   **requiere autorización antes de implementarse**.

---

## 9. Backlog priorizado (reemplaza al de audit_central para Composer)

| ID | Fase | Tarea | Ficheros | Prioridad |
|---|---|---|---|---|
| C-01 | 1 | Tarea `produce` del runner + `bridge.produce()` + timeout 300 | `dmd_bridge_runner.py`, `bridge.py` | **P0** |
| C-02 | 1 | Persistencia `midi/<nombre>/` + bloque manifest `midi` + avance honesto de estado | `store.py`, `engine.py` | **P0** |
| C-03 | 1 | Endpoint `/generations/{gen}/midi` + whitelist + estados/errores UI | `server.py`, `views.js`, `api.js` | **P0** |
| C-04 | 1 | Batería J: regresión determinismo/SHA/immutabilidad/traversal | `tests/test_j_produccion.py` | **P0** |
| C-05 | 1 | Opción A en `produce.py` (CON autorización previa) | `scripts/produce.py` | P0 (bloqueada por autorización) |
| C-06 | 2 | `player.js` (copia literal) + controles + errores + multi-gen | `player.js`, `views.js` | **P0** |
| C-07 | 3 | Config de álbum y por pista + previsualización | `albums.py`, `model.py`, `views.js` | P1 |
| C-08 | 3 | `composer/jobs.py` (single-active, reanudación, cancelación) | `jobs.py` | P1 |
| C-09 | 3 | Lotes y estados por pista en API/UI | `server.py`, `views.js` | P1 |
| C-10 | 3 | Batería K de álbum | `tests/test_k_album_produccion.py` | P1 |
| C-11 | 4 | Checklist E2E + ejecución conjunta | `docs/TEST_REPORT.md` | P1 |
| C-12 | 5 | Goldens MIDI de Composer + tests de aceptación de álbum | `composer_data/golden/`, tests | P2 |
| C-13 | 5 | Documentación de interfaces estables | docs | P2 |

Tareas del backlog antiguo que **conservan valor** y no contradicen este
roadmap: los fixes de robustez P0/P1 (hashlib/random en `server.py`, env UTF-8
en tuberías del bridge, escritura atómica de `album/`) se absorben como
prerrequisitos dentro de la Fase 1. Tareas **excluidas** por D22: B-15
(Soundfont Manager), B-16 (render WAV), B-17 (Player `<audio>` de ficheros),
B-18 (MP3/loudnorm), B-21 (stems SF2+ffmpeg) y toda la antigua Fase 3 de audio.

---

## 10. Reglas arquitectónicas preservadas y decisiones aún no autorizadas

### 10.1 Preservadas (fuente: auditoría de integración completada)

* Puente subprocess aislado de Composer · Forge como único motor MIDI ·
  DMD Compiler y Jazz Engine como componentes de producción existentes ·
  contrato `dark-director/1` rev 3.2 · generación determinista · verificación
  SHA256 · persistencia atómica · directorios de generación inmutables ·
  reglas de seguridad existentes (127.0.0.1, sin eval/exec/shell, límites,
  regex de ids) · almacenamiento de proyecto existente · decisiones de diseño
  de Composer v1.1 · orquestación de álbum existente donde funcione.

### 10.2 No se modifica (protegidos)

`forge/` (todo) · `styles.py` · `dark_director/identities/dark_triphop.py` ·
`contract.py` · DMD Studio · motores musicales protegidos · goldens y
referencias protegidas · `dark-director/1` rev 3.2.

**Única excepción PLANIFICADA (requiere autorización explícita y no equivale a
autorización):** el parámetro aditivo opcional de events en
`scripts/produce.py` (Opción A, §8).

### 10.3 Decisiones que aún requieren aprobación explícita del usuario

1. **Arrancar la Fase 1** (hito de implementación nº 1).
2. **Opción A**: modificación aditiva de `scripts/produce.py` (`events=False`).
3. (Fase 3) Modo de reutilización del orquestador: tarea `produce` por pista
   vs subproceso `python -m album producir` (o híbrido).
4. (Fase 5) Congelación de contratos y goldens.
5. (Fase 6) Cualquier evaluación de reestructuración arquitectónica.

---

## 11. Riesgos técnicos y verificación específica de Windows

| Riesgo | Mitigación |
|---|---|
| `produce.py` es código de producción compartido por Studio/CLI/álbum | Opción A aditiva + default OFF + regresión byte-idéntica + ventana de revisión |
| Timeout de producción en pistas largas (13 pistas en lote) | timeout `produce: 300` + disciplina single-job (C-08) + watchdog por pista |
| Codificaciones Windows (tuberías/rutas con acentos) | UTF-8 explícito en tuberías del bridge (absorbido del fix P0), JSON como transporte de spec |
| Preview WebAudio ≠ render soundfont del usuario | disclaimer visible junto al Player (§3.1) |
| Audio audible no verificable en sandbox | verificación L4 en Windows (Fase 2) |
| `.pyc` en árboles protegidos al importar en el hijo | reutilizar `forge_link.import_forge()` (protegido sin bytecode) + re-verificación de hashes estilo F6 |
| Procesos de lote interrumpidos (Windows) | `recover_interrupted()` al arranque + estado persistido por pista |

**Verificación requerida en la máquina real del usuario (Windows 10 + Python
3.12.1):** (W1) confirmación audible L4 del Player en el navegador; (W2) una
llamada `produce` real desde el venv de Composer comparando `midi_sha256` con
la salida de Studio para el mismo doc+seed; (W3) sin `.pyc` nuevos en `forge/`
tras producir (hashes F6); (W4) reanudación del lote tras kill forzado;
(W5) re-ejecución del test pendiente de `forge.audio.status()` que quedó de la
verificación de audio de Windows (test de entorno, no de Composer).

---

*Fin del roadmap v1.2. Próxima acción esperada: autorización del hito 1
(Fase 1). Ninguna fase está implementada.*
