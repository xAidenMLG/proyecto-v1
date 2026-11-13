# DMD COMPOSER — ARQUITECTURA

Versión 1.2 · 2026-11-11 · (v1.2 = misión de planificación; nada implementado)

> **Cambio v1.2:** el principio 1 se reformula (Composer ahora SÍ genera MIDI,
> exclusivamente a través del pipeline existente por puente aislado — D21/D23
> de DECISIONS.md) y se añade la exclusión explícita del render de audio
> (D22) y la sección de producción/reproducción MIDI. El resto queda intacto.

## Principios

1. **Composer genera MIDI SOLO por el pipeline existente; nunca lo duplica ni
   renderiza audio.** Composer produce documentos `dark-director/1` (rev 3.2)
   + Song Map, y desde v1.2 **genera el MIDI llamando a
   `scripts/produce.py::producir_cancion` dentro del puente subprocess
   aislado** (DMD Compiler → Jazz Engine → MIDI Forge: el único motor).
   Prohibido: un segundo generador, imports DMD/Forge en el proceso de
   Composer, y CUALQUIER render de audio (MP3/WAV/FluidSynth/sfizz/soundfonts:
   decisión D22 — el usuario convierte MIDI→audio con su aplicación externa).
2. **El árbitro siempre es el validador REAL.** Composer tiene pre-chequeos propios
   para avisar ANTES, pero nada sustituye al `dark_director.validador` del DMD real,
   ejecutado en subprocess aislado.
3. **Los catálogos no se inventan.** Instrumentos, tipos de sección, escalera de
   drums, identidades, recetas N1 y perfiles vienen de la introspección del DMD
   real (manifest). Fallback offline = instantánea derivada verificable por tests.
4. **Tres estados de decisión**: fijada (se escribe tal cual), automática (Composer
   decide y ESCRIBE), libre (NO se escribe: la receta N1 y los motores deciden).
   `auto ≠ free` — la distinción es la columna vertebral del producto.
5. **(v1.2) Reproducción = Player WebAudio original de Forge + events.json.**
   El Player NO lee `.mid`: consume `forge.engine.to_events(res)`. Cada
   generación produce `<nombre>.mid` (descargable) + `events.json`
   (reproducción). La síntesis WebAudio es una PREVIEW, no el render soundfont
   externo (D24/D25).

## Capas

```
composer/
├── model.py            Decisiones fijada/auto/libre, Section, HarmonySection, proyecto
├── harmony.py          Parser de grados romanos → símbolos reales (gramática de theory.parse_chord)
├── structure.py        Editor estructural: validación, timeline, reordenar/duplicar
├── randomizer.py       Módulo D: hard constraints + compatibility rules + weighted preferences
├── builder.py          Documento dark-director/1 + pre-chequeos de conflictos
├── songmap.py          Módulo E: Song Map (JSON/CSV) con precedencia §2.8 y ciclo del motor
├── engine.py           Orquestación: plan → conflictos → doc → mapa → validación real → guardado
├── albums.py           Modo álbum: plan N pistas, diversidad, huellas, reanudación
├── bridge.py           Puente subprocess al DMD real (runner aislado, timeouts, sin shell)
├── dmd_bridge_runner.py Ejecutado en proceso aislado con sys.path del DMD descubierto
├── manifest.py         Manifiesto de capacidades: vivo → caché → instantánea builtin
├── store.py            Persistencia: proyectos, generaciones, escritura atómica, SHA256
├── server.py           FastAPI local (127.0.0.1:8898), sin eval, límites de tamaño
├── jobs.py             (PLAN v1.2 Fase 3) un trabajo activo, reanudación, cancelación
└── static/             UI vanilla JS, tema oscuro coherente con Studio
    └── js/player.js    (PLAN v1.2 Fase 2) Player WebAudio de Forge copiado literal
```

## Flujo de una generación

```
proyecto (decisiones + secciones + armonía)
   │
   ├─► randomizer.resolve(seed)          → plan resuelto + log de explicabilidad
   │      reglas: BPM en rango de receta · dominante mayor en menor ·
   │      doom ≥ 2 compases/acorde · espacios obligatorios ⇒ break de aire
   │
   ├─► builder.conflicts                 → errores / avisos / sugerencias
   │      (si hay errores duros: NO se genera)
   │
   ├─► builder.build                     → doc dark-director/1
   │      solo campos reales del validador; progressions por id de sección (§2.8)
   │
   ├─► songmap.build_song_map            → Song Map + CSV (grid por compás con el
   │      MISMO algoritmo de ciclo de forge/engine.Sec)
   │
   ├─► bridge.validate_doc               → validador REAL (subprocess)
   ├─► bridge.compile_preview            → compilador REAL sin renderizar
   │
   ├─► bridge.produce                    (PLAN v1.2 Fase 1) → task_produce en el
   │      hijo aislado → scripts/produce.py::producir_cancion → MIDI + evidencia
   │      + config_efectiva + sha256 (+ events.json por Opción A con autorización)
   │
   └─► store.save_generation             → gen_NNNN/ (doc, mapa, manifest, SHA256)
          nunca sobrescribe; escritura atómica (tmp + os.replace)
          + subcarpeta midi/<nombre>/ con el MIDI y su evidencia (v1.2)
```

## Producción y reproducción MIDI (v1.2 — PLANIFICADA, nada implementado)

* **Generación (Fase 1):** nueva tarea `produce` en `dmd_bridge_runner.py` +
  `bridge.produce()` (timeout 300 s). `producir_cancion` escribe una subcarpeta
  autocontenida `gen_NNNN/midi/<nombre>/` con `doc.json`, `config_efectiva.json`,
  `<nombre>.mid`, `evidencia.json` (sha256_midi, compliance, orden de
  regeneración con `--verify`). El manifest gana el bloque `midi`; la whitelist
  de descargas se amplía con nombres derivados del servidor. Immutabilidad:
  el MIDI se escribe UNA vez; reintentos = nueva evidencia verificada por SHA.
* **Reproducción (Fase 2):** `static/js/player.js` = clase `Player` de
  `web/app.js:442-522` copiada LITERAL (cierre de dependencias verificado:
  sin estado de Forge, sin MP3/WAV, sin FluidSynth/soundfonts, sin paquetes).
  Controles ▶ Escuchar / ■ Parar; guard anti-solapamiento; reanudación desde
  `seekBeat`; cierre determinista del AudioContext; mensaje explícito sin
  WebAudio; datos inválidos → error claro. Fuente de datos: `events.json` del
  gen (Opción A: parámetro aditivo `events=False` en `produce.py` — REQUIERE
  AUTORIZACIÓN; Opción B descartada).
* **Excluido para siempre (D22):** MP3/WAV/FluidSynth/sfizz/SF2/SFZ/soundfonts/
  masterizado/workers de audio. El convertidor MIDI→audio del usuario permanece
  externo: `Composer → MIDI → convertidor externo → audio`.

## Integración con el DMD real (misión §10)

* **Descubrimiento**: ruta configurada (`composer_data/composer_config.json`) →
  carpetas hermanas → cwd. Se exige `dark_director/contract.py`. Sin rutas fijas.
* **Aislamiento**: Composer NUNCA importa DMD en su proceso. Todo va por
  subprocess con argv fijo (`dmd_bridge_runner.py --spec … --out …`), timeouts
  (60/120 s) y spec JSON ≤ 8 MB. Mismo patrón que `studio.runner`.
* **Discrepancias**: el manifiesto guarda fingerprint (contrato, rev, versiones,
  recetas). Si el DMD cambia, `POST /api/integration/refresh` lo detecta y la UI
  lo muestra — Composer no genera documentos incompatibles sin avisar.

## Precedencia de acordes (respetada, no reinventada)

Compilador §2.8: `section.chords` > `harmony.progressions[id]` >
`harmony.progressions[type]` > receta N1. Composer usa la posición 2 (guiada por
id); el Song Map calcula cada fuente con la MISMA cadena, incluida la
instanciación N1 (pares offset/calidad de la receta introspeccionada + tónica,
ortografía plana idéntica a `_NOMBRES_NOTA`).

## Reglas del parser de grados romanos

| Entrada | C major | D minor |
|---|---|---|
| `I - III - vi - V` | C - Em - Am - G | — |
| `i - III - vi - V` | — | Dm - F - Bb - A |
| `V7` (en menor) | — | A7 (dominante) |
| `bVI` | Ab (prestado, mayor) | — |
| `#iv0` | Gbdim (ortografía plana del compilador) | — |
| `vi6` / `ii64` | Am/C · Dm/A | — |
| `I:2 - V:1` | ciclo con duraciones propias | — |

Calidad por defecto = tríada diatónica de la escala (misión §5: III → Em);
tokens explícitos (`7 maj7 m7 9 m9 sus4 7sus4 add9 dim aug m7b5 …`) sustituyen;
en menor, V = dominante mayor (convención estándar del pop); alteraciones (b/#)
→ tríada mayor por defecto (bVI/bVII/bII prestados). Todo símbolo emitido pasa
los tests contra `forge/theory.parse_chord` real.

## Modo álbum

Plan (`dmd-album/1`) con identidad y restricciones compartidas; cada pista recibe
seed/tonalidad/estructura/groove/lenguaje diversificados con registro de huellas
(sin combinaciones exactas repetidas) y estado por pista para reanudación.
**v1.2 (D27):** el creador de álbumes completos pasa a función nuclear —
configuración a nivel álbum y por pista, generación MIDI individual y por lotes,
estados, reintentos, cancelación y recuperación, **reutilizando el orquestador
existente de 13 pistas** (`album/orquestador.py` + `planificador.py` +
`diversidad.py`, SOLO LECTURA; sin motor de álbumes competidor). Detalle:
`IMPLEMENTATION_ROADMAP.md` Fase 3.

## Seguridad

* Bind exclusivo `127.0.0.1:8898` (Studio usa 8899; conviven).
* Ids con regex estricta (`^[a-z0-9][a-z0-9_-]{0,47}$`), nombres saneados,
  sin path traversal posible en ninguna ruta de disco.
* Sin `eval`/`exec`/`shell=True` en todo el paquete (verificado por test H6).
* Límites: 512 KB por petición API, 8 MB por spec de bridge, 512 KB por proyecto.
* Generaciones nunca sobrescritas; escritura atómica en todo el disco.
* El bridge ejecuta UN script fijo del paquete: la UI no lanza comandos.
