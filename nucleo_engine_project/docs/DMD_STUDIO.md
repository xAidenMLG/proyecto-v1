# DMD STUDIO — Aplicación local de composición (Dark Music Director + MIDI Forge)

> **DMD STUDIO** es una aplicación web local para diseñar, configurar, validar,
> producir y administrar composiciones musicales del sistema
> Dark Music Director + MIDI Forge **sin escribir JSON a mano** (con editor
> JSON opcional para control avanzado).
>
> La web es SOLO una capa de control, edición y visualización. La única fuente
> de verdad musical siguen siendo los motores Python existentes:
> `dark_director` (contrato dark-director/1 rev 3.2), `jazz_engine` y
> `forge` (MIDI Forge), orquestados por el pipeline real de
> `scripts/produce.py::producir_cancion()`. **No existe un segundo pipeline.**

- 100 % local: el servidor se vincula SIEMPRE a `127.0.0.1`.
- Motores sin dependencias (librería estándar de Python); solo la capa web
  necesita `fastapi` + `uvicorn` (venv propio, `requirements-studio.txt`).
- Determinismo garantizado: misma entrada + misma seed = mismo MIDI byte a byte
  (verificado web↔web y web↔CLI; ver §7).

---

## 1. Instalación en Windows 10 (resumen)

Requisitos: Windows 10, Python 3.12.x de 64 bits en el PATH, y opcionalmente
FluidSynth + `GeneralUser-GS.sf2` para renderizar WAV.

```
nucleo_engine_project\
├── scripts\windows\install_studio.bat   ← 1) instalar (crea .venv-studio)
├── scripts\windows\check_studio.bat     ← 2) verificar entorno
└── scripts\windows\start_studio.bat     ← 3) arrancar (abre el navegador)
```

1. Doble clic en `scripts\windows\install_studio.bat` (solo la primera vez).
   Crea el entorno virtual independiente `.venv-studio` e instala fastapi+uvicorn.
2. (Opcional) `check_studio.bat` comprueba Python, dependencias, motores y audio.
3. `start_studio.bat` arranca `python -m studio` y abre `http://127.0.0.1:8899`.

### WAV (render de audio)

El estudio renderiza WAV **en la misma generación** si detecta FluidSynth y un
soundfont. Coloca tu soundfont en la raíz del proyecto (o cualquiera de las
rutas típicas) y decláralo en **Production → Audio (WAV)**:

- `GeneralUser-GS.sf2` en la raíz de `nucleo_engine_project\` → autodetectado.
- O escribe la ruta completa al `.sf2` y (si hace falta) al ejecutable
  `fluidsynth.exe` y pulsa *Guardar rutas*.

Sin FluidSynth la aplicación funciona igual (solo MIDI): el intento de WAV
devuelve un error claro en el log y en Results, nunca rompe la generación.

Puerto: 8899 por defecto (`studio_data/studio_settings.json` → `"port"`), o
`python -m studio --port 3000`.

---

## 2. Áreas de la interfaz

| Área | Qué hace |
|---|---|
| **PROJECTS** | Crear, abrir, guardar, guardar como, duplicar, eliminar, exportar JSON. Historial de generaciones por proyecto. |
| **COMPOSITION** | Título/notas, identidad × accesibilidad (27 combinaciones válidas), BPM/seed/humanize/velocity_cap, **timeline visual** (ancho ∝ compases, colores por tipo), editor de secciones (añadir/eliminar/reordenar/duplicar; id, tipo, compases, energy/tension/density, focus, active, drums, final; avanzado: chords, chord_bars, resolution, loop_bars) e instrumentos del catálogo cerrado de 8 (enabled, register, density, mix). |
| **HARMONY** | Los dos modos reales: **NATIVE** (receta N1 de la identidad; no se inserta nada) y **GUIDED** (`harmony.progressions` con clave id o type + `chords` por sección; precedencia real chords > progressions.id > progressions.type). Parámetros armónicos (key, language, resolution, harmonic_rhythm_bars 1–8). **Biblioteca Fase 7** como opción adicional INACTIVA por defecto (keyword, id, variación, semilla). |
| **PRODUCTION** | Los 7 perfiles oficiales (`original`, `sax`, `sax_rhodes`, `drums`, `sax_vibes`, `full`, `atmospheric`) con nombres comprensibles y su matriz de motores SAX/RHODES/DRUMS/VIBES. Configuración de audio WAV (soundfont/fluidsynth). |
| **GENERATION** | Seed reproducible, nombre de salida, validación previa (contrato + compilador), generador MIDI y WAV, **configuración efectiva visible + comando CLI equivalente**, log en vivo, cancelación, errores y avisos. |
| **JSON** | Editor completo del documento: validar (validador REAL del motor), aplicar (valida siempre), formatear, cargar JSON externo, descargar. Los campos válidos desconocidos para la UI (incluidos `x_*`) **nunca se pierden** al alternar visual ↔ JSON. |
| **RESULTS** | Cada generación: perfil, seed, duración, SHA256 (copiable), compliance, evidencia, **reproductor de audio** cuando hay WAV/MP3, descargas individuales (MIDI, WAV, doc.json, config_efectiva.json, evidencia.json, job.log) y el comando de reproducción exacta con `--verify`. |

Atajos: `Ctrl+S` guarda. Punto ámbar ● en la barra superior = cambios sin guardar.

---

## 3. Arquitectura

```
DMD STUDIO (SPA estática, sin build: HTML/CSS/JS propio)
      │  fetch /api/*
      ▼
FastAPI local (studio/server.py) — solo 127.0.0.1
      │  validación estricta de entradas
      │  projects.py  → studio_data/projects/<pid>/project.json (doc + production + historial)
      │  jobs.py      → UNA generación a la vez (single-flight), estado persistido
      ▼
subproceso aislado: python -m studio.runner --spec job_spec.json
      │  importa scripts/produce.py (el MISMO núcleo que el CLI)
      ▼
dark_director.compilador → jazz_engine.render → forge (MIDI Forge) → MIDI
      │  (opcional) forge.audio.render_wav (FluidSynth + .sf2)
      ▼
studio_data/projects/<pid>/generations/<gen>/<salida>/
      doc.json · config_efectiva.json · <salida>.mid · evidencia.json · [wav]
```

Decisiones clave (ver `docs/DECISIONS.md` §I):

- **Reutilización, no reimplementación**: la generación ejecuta
  `producir_cancion()` de `scripts/produce.py` en un subproceso; el resultado
  es byte a byte el mismo que el CLI con el mismo doc/perfil/seed.
- **La UI no inventa campos**: los catálogos, perfiles, keywords Fase 7 y
  rangos que muestra se leen EN VIVO de los módulos de los motores
  (`studio/capabilities.py`); la validación final es SIEMPRE
  `dark_director.validador.validar` + `compilador.compilar`.
- **Sin base de datos**: proyectos = carpetas con JSON + artefactos. Escritura
  atómica (`project.json.tmp → replace`). Un corte durante una generación
  deja el trabajo como `interrupted` al reiniciar y el proyecto íntegro.

## 4. API local (referencia breve)

La documentación interactiva vive en `/api/docs` (OpenAPI/Swagger).

| Método y ruta | Descripción |
|---|---|
| `GET /api/capabilities` | Contrato, catálogos, 7 perfiles, field_specs, keywords F7, biblioteca, estado de audio. |
| `GET /api/system` · `GET/PUT /api/settings` | Estado y ajustes (soundfont, fluidsynth, puerto). |
| `GET/POST /api/projects` · `GET/PUT/DELETE /api/projects/{pid}` | CRUD de proyectos. |
| `POST /api/projects/{pid}/duplicate` · `GET /api/projects/{pid}/export` | Duplicar · descargar doc.json. |
| `POST /api/validate` | Validación con `dark_director.validador` (errores/e3xx/avisos/no_verificados). |
| `POST /api/compile-preview` | Compila sin renderizar (avisos del compilador real). |
| `POST /api/projects/{pid}/generate` | Lanza generación `{production, seed, harmony, wav, out_name, doc?, validate_first}` → job. 409 si ya hay una. 422 si la validación previa falla. |
| `GET /api/jobs/{jid}` · `POST /api/jobs/{jid}/cancel` · `GET /api/jobs?pid=` | Estado + log_tail, cancelar, listar. |
| `GET /api/projects/{pid}/generations/{gen}` | Artefactos (JSON parseados + tamaños). |
| `GET /api/projects/{pid}/generations/{gen}/logfile` | job.log (texto). |
| `GET /api/projects/{pid}/audio/{gen}/{out}/{file}` | Streaming de .mid/.wav/.mp3/.json (patrón estricto). |

### Seguridad

- Bind exclusivo a `127.0.0.1`; sin expuesta a la red.
- El navegador nunca ejecuta comandos: el único proceso lanzado es
  `python -m studio.runner` con un spec JSON validado por el backend.
- Nada del cliente decide rutas de disco: ids contra patrones estrictos
  (`[a-z0-9][a-z0-9_-]*`, `gen_\d+`, slug para carpetas de salida) y todas las
  escrituras bajo `studio_data/`. Probado contra traversal (§7).
- El JSON del editor solo se parsea (`json.loads`) y valida con el motor;
  nunca se `eval`.
- Concurrencia: una sola generación activa; segunda petición → `409`.
- Timeout duro de 15 min por generación.

## 5. Persistencia

```
studio_data\
├── studio_settings.json         ajustes (soundfont, puerto)
├── projects\<pid>\project.json  doc dark-director/1 + production + history[]
│  └── generations\gen_NNNN\
│       ├── job_spec.json        spec exacto ejecutado
│       ├── job.log              log completo del pipeline
│       └── <salida>\            doc.json · config_efectiva.json · <salida>.mid
│                               evidencia.json (hashes, versión, reproducción) · [wav]
└── jobs\<jid>.json              estado persistido de cada trabajo
```

`project.json` guarda el documento y la configuración de producción; el
historial (máx. 100 entradas) se actualiza solo al terminar cada generación.

## 6. Comandos equivalentes CLI

Generación web con perfil P y seed S equivale a:

```
python scripts/produce.py doc.json --production P --seed S --out <carpeta> \
    [--harmony KEYWORD] [--harmony-id ID] [--harmony-variacion none|subtle|medium|rich] \
    [--harmony-seed N] [--verify SHA256]
```

Results muestra el comando exacto de reproducción (con `--verify <sha>`) que
escribe `evidencia.json`. La única diferencia deliberada: las generaciones del
estudio no añaden línea al índice `output/produccion/INDICE.md` (viven en
`studio_data/`; no afecta al MIDI).

## 7. Validación integral (FASE 6) — resultados

Ejecutada contra el servidor real (`scripts/e2e_studio.py`): **36/36 OK**.
Suite pytest del estudio (`python -m pytest tests/studio -v`): **13/13 OK**.
Regresión de motores (`python -m pytest tests/dmd -q`): **171 OK** (sin cambios).

Cobertura: creación desde cero · 7 perfiles · NATIVE vs GUIDED · Fase 7
(keyword/id/variación/semilla, evidencia registrada) · edición JSON con `x_*`
preservado tras guardar/reabrir · duplicar/eliminar/reabrir · WAV con error
claro sin FluidSynth · perfil inválido 400 · keyword desconocida 400 ·
traversal nunca 200 · E102/E105/E109/E203 detectados por el validador real ·
422 en generación con doc inválido · **determinismo web×2 idéntico y
web == CLI byte a byte** (mismo doc, perfil `full`, seed 7).

Verificación de interfaz con navegador real (agent-browser): Projects,
Composition (timeline + editor), Harmony (modo guiado detectado), Production
(7 tarjetas), Generation (generación completa desde la UI, config efectiva y
CLI equivalente visibles), JSON (validación en vivo: `E105 · bpm fuera de
20–300: 999`), Results (evidencia + descargas + comando de reproducción),
Guardar → recargar → proyecto restaurado.

## 8. Limitaciones conocidas

| # | Limitación | Detalle |
|---|---|---|
| L1 | **WAV requiere FluidSynth + .sf2 instalados** | En el sandbox de desarrollo no hay FluidSynth: la ruta WAV está probada hasta el error controlado; el render real se verifica en Windows (la evidencia.json ya genera el comando). |
| L2 | La calidad musical NO la declara el estudio | El estudio verifica estructura, determinismo y compliance técnico. La calidad musical se evalúa escuchando, como siempre. |
| L3 | Los parámetros de `development` (phrases/motifs/responses/improvisation) se editan vía JSON | Son campos válidos del contrato y se preservan; el editor visual detallado queda como evolución futura. |
| L4 | Un servidor = un proyecto abierto por pestaña | Suficiente para uso local de escritorio; el estado del proyecto activo vive en `localStorage`. |
| L5 | El convertidor antiguo (`app.py` + `web/`) no participa | DMD STUDIO es una aplicación nueva; el convertidor sigue disponible como herramienta separada (`python app.py`, puerto 8765). |
