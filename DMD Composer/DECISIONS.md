# DECISIONS — DMD COMPOSER

Registro de decisiones arquitectónicas con su justificación. Las marcadas
**[MANTENER]** son obligaciones para futuras versiones. Las decisiones
**[SUPERSEDA — ver …]** conservan su texto histórico pero ya NO rigen; manda la
decisión indicada. El roadmap oficial vigente es `IMPLEMENTATION_ROADMAP.md`
(v1.2, 2026-11-11).

## D1 — Stack: Python + FastAPI + uvicorn, UI vanilla **[MANTENER]**

Mismo stack que DMD STUDIO (fastapi==0.115.6, uvicorn==0.34.0), ya instalado y
probado en la máquina del usuario. Cero dependencias nuevas, cero build de
frontend, Windows 10 + Python 3.12 nativo. Se descartó Next.js (violaba
"dependencias mínimas / sin servicios cloud") y Flask (menos validación que
Pydantic sin añadir nada a cambio).

## D2 — Composer NO genera MIDI **[PARCIALMENTE SUPERSEDA por D21/D23]**

> **ACTUALIZACIÓN v1.2 (2026-11-11):** la parte de esta decisión que
> prohibía a Composer generar MIDI quedó SUPERSEDA por **D21** (nuevo
> propósito del producto) y **D23** (generación por el pipeline existente vía
> puente aislado). Lo que SIGUE vigente de D2: Composer no duplica NINGÚN byte
> del motor de generación (no hay segundo generador, no hay imports en
> proceso) y no toca `development`.

Texto histórico (v1.0): regla 4 de la misión. Composer produce documentos;
el pipeline validador → compilador → Forge es el de DMD. Ni un byte de
duplicación: la prueba F4/F5 genera MIDI REAL con `scripts/produce.py` desde
un doc de Composer, demostrando la interconexión sin copiar nada.

## D3 — Puente subprocess aislado, nunca import en proceso **[MANTENER]**

`dmd_bridge_runner.py` se ejecuta como proceso hijo con la ruta del DMD
descubierto en `sys.path` de ESE proceso. Beneficios: un fallo del DMD no
derriba Composer; sin colisiones de paquetes; timeouts por tarea
(60/120 s); argv fijo sin shell. Mismo patrón que `studio.runner`.
Alternativa descartada: import directo (acoplamiento frágil y rutas relativas
rotas al mover carpetas).

## D4 — Catálogos por introspección; instantánea builtin verificable **[MANTENER]**

Los catálogos (8 instrumentos, 7 tipos, escalera drums, 3 identidades, recetas
N1 completas con PROGRESIONES por (language, type), perfiles, keywords F7) se
leen EN VIVO del DMD real y se cachean con fingerprint. La instantánea
`manifests/dmd_manifest_builtin.json` es una DERIVADA (capturada del DMD real
rev 3.2) y el test A8 verifica que coincide con el vivo: si el DMD cambia, la
prueba lo detecta. Nada de listas paralelas desactualizables.

## D5 — El parser de grados romanos es REAL, no superficial **[MANTENER]**

No es "número → acorde por índice". Reglas implementadas y probadas:
raíz por escala del modo; calidad por defecto = tríada diatónica (misión:
III → Em); tokens de calidad absolutos; V = dominante mayor en modos menores
(convención pop: V7 → E7 en A minor); alteraciones b/# → mayor por defecto
(bVI/bVII/bII prestados); cifrado clásico 6/64 y bajo literal; duración por
acorde `Grado:N` → sintaxis real `Chord:bars` del motor; ortografía plana
idéntica a `_NOMBRES_NOTA` del compilador. TODOS los símbolos se verifican
contra `forge/theory.parse_chord` real (test C12).

## D6 — Tonalidad ESTRICTA (a diferencia de parse_key)

`forge/theory.parse_key` cae a C major en silencio ante texto desconocido
("Do menor" se leería como D minor). Composer rechaza tonalidades ambiguas con
error claro ANTES de escribir nada en el JSON: el doc que llega al motor dice
lo mismo que leyó el usuario.

## D7 — Precedencia de acordes §2.8 respetada, no reinventada **[MANTENER]**

Composer escribe `harmony.progressions[id]` (posición 2). El Song Map calcula
la fuente real de cada sección con la MISMA cadena (section.chords > id > type >
receta N1) y el MISMO algoritmo de ciclo de `forge/engine.Sec`, de modo que el
mapa y el motor no pueden discrepar (test E7 lo comprueba contra el compilado).

## D8 — `auto` escribe, `free` no; fijadas intocables **[MANTENER]**

Semántica de la misión §3. Las decisiones fijadas nunca se "mejoran": BPM 150
en dark_triphop se escribe 150 y se INFORMA el W401. Los conflictos duros
(estructura inválida, dos protagonistas) BLOQUEAN la generación en vez de
produzcan JSON arbitrario.

## D9 — Randomizador condicionado, no dados independientes **[MANTENER]**

Tres capas: hard constraints (fijadas), compatibility rules (rango BPM de
receta al elegir auto, doom ≥ 2 compases/acorde, espacios ⇒ break de aire con
drums light, protagonista único y sonando), weighted preferences (pools por
mood con pesos que el nivel de diversidad aplana). Semilla única
`Random(seed)` consumida en orden fijo → mismo plan bit a bit.

## D10 — Explicabilidad siempre guardada **[MANTENER]**

Cada generación persiste `generation_manifest.json` con: decisiones fijadas/
automáticas/libres, log por eje (qué se decidió, por qué, qué se descartó),
seed, SHA256 del doc, fingerprint del contrato. Es el "por qué" de cada canción.

## D11 — Song Map externo, sin marcadores MIDI

La integración actual no expone escritura de marcadores y modificar Forge solo
para eso está prohibido (misión §7). El Song Map JSON/CSV + grid + bloque de
letras cumple el objetivo (escribir canciones sabiendo qué suena en cada
compás) sin tocar motores.

## D12 — Composer nunca escribe `development` **[MANTENER]**

Frases, motifs e improvisación son dominio del motor (regla 10). Composer
mitiga W404 con `loop_bars` (campo estructural real) y deja el desarrollo
musical a las recetas y guardrails existentes.

## D13 — Modo álbum = planificador con diversidad real

Cumplir §8 sin duplicar el módulo `album/` de DMD: plan compartido + seeds
independientes + rotación de tonalidades + pool de plantillas + huellas contra
duplicados + estado por pista (reanudación). La integración profunda (orquestar
la producción MIDI de las 13 pistas con el orquestador de DMD) está diseñada en
NEXT_MISSION.md, no simulada.

## D14 — UI en español, ids del contrato en inglés

El usuario opera en español; el JSON mantiene la nomenclatura del contrato
(`verse`, `chorus`, `dark_triphop`) para que lo que se ve en Composer sea
exactamente lo que Studio y los motores esperan.

## D15 — Puerto 8898

Studio ocupa 8899. Composer convive con Studio abierto: 8898, solo localhost.

---

# DECISIONS v1.1 (misión de resolución 2026-11-11)

## D16 — Native/Guided: semántica cerrada con avisos explícitos, nunca silencio **[MANTENER]**

* Global **Guiada**: cada sección con decisión guiada exige grados o acordes
  literales (error si no); una sección SIN decisión armónica se resuelve con la
  receta N1 y se emite el aviso `armonia-implicita` (nombra secciones y acción).
* Global **Nativa**: las progresiones guiadas NO viajan y se emite
  `guiada-ignorada` (D-05). Una sección marcada Nativa dentro de una composición
  guiada usa N1 — capacidad soportada por la precedencia del compilador.
* `harmony_mode` es una instrucción de CONSTRUCCIÓN (no un campo del contrato):
  sin modo "Libre" ni por API (D-07); en Automático se resuelve con criterio
  demostrable (hay progresiones/acordes → guiada; si no → nativa).
* El manifest lleva el modo REAL del documento (`modo_real_del_doc`) y la fuente
  armónica por sección — lo que se generó, no lo que se quiso.

## D17 — El protagonista se PROPONE, no se impone **[MANTENER]**

La distribución del protagonista (focus/active/enabled/density) se calcula con
campos reales del contrato y `focus_default` REAL de la receta; el usuario la
acepta (editable), la modifica o la rechaza — nunca se aplica sola. El estado
queda registrado en el proyecto y en el manifest. Auto = LEAD de la receta.
Density propuesta 0.6 (banda B2; evita W403 con mallet_sparse). Sin density
para bass/drums/pad/strings (W410 real).

## D18 — Groove ≠ tempo; el perfil de producción es una INSTRUCCIÓN **[MANTENER]**

* El groove NO es campo del contrato ni parámetro del motor: su único efecto
  real es sesgar la curva de BPM automático. El log lo dice textualmente.
  BPM fijado se conserva EXACTO; BPM Libre no escribe `global.bpm`.
* El perfil de producción no se declara aplicado jamás: bloque `produccion`
  con `estado: "seleccionado_pendiente_de_aplicar"` + instrucción Studio/CLI
  verificable (probada end-to-end: MIDI real con SHA256).

## D19 — Explicabilidad de un solo estado por eje **[MANTENER]**

`decisiones = {fijadas, automaticas, libres}` disjuntos por construcción;
mood/atmosphere/groove/diversity son `preferencias_composer` (no llegan al doc);
las elecciones ponderadas registran sus alternativas descartadas con peso;
seed Libre no escribe `global.seed` (avisa). Verificado por test y por fuzz del
QA independiente.

## D20 — Acordes literales por el puente, no por un segundo parser **[MANTENER]**

`HarmonySection.chords` se valida con el parser REAL del DMD (tarea de puente
`parse_chords` sobre `forge/theory.parse_chord`, particionando el sufijo
`:bars`); símbolo inválido = error E113 antes de guardar. Se escriben en
`structure[].chords` (posición 1 de §2.8: precedencia máxima con cualquier modo).
El parser de grados romanos permanece intacto. Un solo motor armónico.

---

# DECISIONS v1.2 (misión de planificación 2026-11-11)

> Fuente: decisión del usuario tras la auditoría completada
> "FORGE → DMD COMPOSER MIDI GENERATION & PLAYBACK INTEGRATION"
> (`download/FORGE_MIDI_*.md`, `COMPOSER_INTEGRATION_ANALYSIS.md`,
> `RECOMMENDED_INTEGRATION_ARCHITECTURE.md`). Roadmap oficial:
> `IMPLEMENTATION_ROADMAP.md`. **Ninguna de estas decisiones autoriza por sí
> misma una implementación.**

## D21 — Propósito real de Composer: composición Y producción MIDI **[MANTENER — SUPERSEDA en parte a D2]**

DMD Composer es una **aplicación de composición musical y producción MIDI**.
Sus responsabilidades: dirección musical y composición; generación de
documentos `dark-director/1`; configuración de parámetros musicales y de
armonía/progresiones; **generación de MIDI por el pipeline de producción
existente DMD/Forge**; **persistencia y descarga del MIDI**; **reproducción
del MIDI dentro de Composer**; **creación y gestión de álbumes completos**;
**generación MIDI por lotes**; gestión de diversidad y del estado de
producción. Composer **NO es una aplicación de conversión de audio**.

## D22 — Exclusión explícita del renderizado de audio **[MANTENER — SUPERSEDA a "WAV desde Composer" de NEXT_MISSION y a las fases de audio de audit_central]**

Quedan **FUERA** del roadmap, requisitos, arquitectura y backlog de Composer:
MP3 · WAV · FluidSynth · sfizz · SF2/SFZ · gestión de soundfonts ·
masterizado de audio · conversión de audio · workers de render de audio ·
perfiles de audio-rendering.

**Motivo (enunciado canónico del usuario):**
*"The user already has a separate Python batch MIDI-to-audio application.
DMD Composer is responsible for musical composition, MIDI generation, MIDI
playback preview and album management. Audio conversion remains external."*
(El usuario ya posee una aplicación Python independiente que convierte MIDI a
audio por lotes. Composer es responsable de la composición musical, la
generación de MIDI, la pre-escucha de MIDI y la gestión de álbumes. La
conversión de audio permanece externa.)

Flujo externo: `DMD Composer → ficheros MIDI → convertidor Python externo →
ficheros de audio`. **No duplicar esa funcionalidad; no proponer reintegrarla a
Composer salvo cambio explícito del usuario.** Deja sin efecto el antiguo
punto 2 de NEXT_MISSION ("WAV desde Composer vía Studio") y las tareas B-15 a
B-18 y B-21 del backlog antiguo.

## D23 — Generación MIDI = `producir_cancion` por el puente aislado **[MANTENER]**

Composer genera MIDI **exclusivamente** con el pipeline de producción
existente: `scripts/produce.py::producir_cancion` (verificado por la auditoría
como la ruta correcta, porque Composer crea documentos `dark-director/1`, no
JSON de preset de Forge). Diseño:

```
composer/bridge.py → dmd_bridge_runner.py → intérprete hijo aislado
→ scripts/produce.py::producir_cancion → DMD Compiler / Jazz Engine / MIDI Forge
→ fichero MIDI
```

Prohibido: crear un segundo generador MIDI; importar los motores DMD/Forge
directamente en el proceso del servidor de Composer (regla D3 intacta).
Se preservan la generación determinista (mismo doc + seed → MIDI byte a byte
idéntico) y la verificación SHA256 existente.

## D24 — Reproducción = Player WebAudio original de Forge **[MANTENER]**

La implementación de reproducción de Forge es `class Player` en
`nucleo_engine_project/web/app.js` (líneas 442-522): sintetizador WebAudio del
navegador que consume el formato `to_events()`, soporta start/stop, reanuda
desde la posición retenida, tiene protección anti-solapamiento, cierra el
AudioContext en la limpieza y **no requiere dependencias Python nuevas** (ni
FluidSynth ni soundfonts). Composer **reutiliza** esa clase (copia literal con
cierre de dependencias verificado). Prohibido para la implementación inicial:
crear otro sintetizador; introducir pygame, mido, python-rtmidi, winsound o el
MCI de Windows.

## D25 — Artefactos asociados `song.mid` + `events.json`; la preview no es el render **[MANTENER]**

El Player **NO lee ficheros `.mid` arbitrarios**: consume la representación de
eventos generada por `forge.engine.to_events(res)`. Por tanto cada generación
de Composer produce dos artefactos asociados: `<nombre>.mid` (el MIDI real
descargable) y `events.json` (datos de reproducción del navegador).
**Distinción de producto documentada:** el sonido WebAudio es una **síntesis
de pre-escucha**, no necesariamente idéntica al render que el usuario obtiene
con su soundfont/convertidor externo.

## D26 — events.json por la Opción A (parámetro aditivo en produce.py) **[SELECCIONADA — REQUIERE AUTORIZACIÓN, NO IMPLEMENTAR AÚN]**

Se selecciona la **Opción A**: parámetro **opcional y desactivado por defecto**
(p. ej. `events=False`) en `scripts/produce.py::producir_cancion` que, cuando
esté activo, persista `forge.engine.to_events(res)` como `events.json` en
`out_dir` mientras el resultado de generación ya está en memoria. Ventajas:
una sola generación, sin cómputo musical duplicado, eventos directamente
correspondientes al MIDI generado, cambio aditivo mínimo. La Opción B
(re-derivar eventos con una segunda pasada determinista, sin tocar
`produce.py`) queda **documentada y descartada**: duplica la generación,
gasta tiempo de proceso y añade complejidad innecesaria — no se selecciona en
silencio. Condiciones obligatorias cuando se autorice: registrar el cambio
explícitamente; mantenerlo opcional y desactivado por defecto; preservar el
comportamiento del CLI existente; tests de regresión con MIDI **byte-idéntico**
sin la opción; igualdad SHA256 entre el MIDI escrito y el representado por el
resultado capturado. **Esta planificación NO implementa el cambio y NO
constituye autorización:** queda marcado como una modificación pequeña e
identificada del script de producción que requiere autorización previa.

## D27 — El creador de álbumes completos es función nuclear de Composer **[MANTENER]**

Crear y gestionar álbumes completos (típicamente 13 pistas) es una
responsabilidad central, no un extra futuro: configuración a nivel álbum
(identidad, dirección, tempo, atmósfera, estrategia armónica, instrumentación,
perfil, diversidad, seed), configuración por pista (dirección individual, JSON
opcional, elecciones armónicas, protagonista, previsualización), generación
individual y por lotes con estados por pista, reintentos, cancelación y
recuperación. Se conservan los modos armónicos **Native y Guided** existentes;
las progresiones familiares (F7) son un recurso opcional, nunca un default, y
no se impone una única progresión al álbum salvo petición explícita. Se
**reutiliza el orquestador de producción de 13 pistas existente**
(`album/orquestador.py` + `planificador.py` + `diversidad.py`, SOLO LECTURA);
prohibido crear un motor de álbumes competidor. Composer pasa a ser la
interfaz central de este flujo.

## D28 — Congelación funcional antes de la reestructuración arquitectónica **[MANTENER]**

Una vez que la generación individual, la reproducción y la producción de
álbumes funcionen de forma fiable, se **congelan** contratos, estructura de
artefactos, flujos de usuario y tests de regresión, y se establecen goldens
MIDI y tests de aceptación de álbum. Solo DESPUÉS de esa congelación (Fase 5)
se evaluará la reestructuración arquitectónica / Plan B (Fase 6, contingencia;
no se inicia ninguna reescritura).

## D29 — Implementación de la integración MIDI (misión de implementación) **[VIGENTE]**

La misión "INTEGRATE FORGE MIDI ENGINE INTO DMD COMPOSER — IMPLEMENTATION AND
FULL VALIDATION" AUTORIZÓ Y EJECUTÓ la implementación de las Fases 1–3 del
roadmap v1.2. Decisiones técnicas concretas tomadas y documentadas:

1. **Puente produce cancelable** (`composer/bridge.py`): `produce_start()`
   lanza el núcleo real en un hijo aislado con `BridgeProcess` (poll/wait/
   cancel; Windows `taskkill /F /T` + CREATE_NEW_PROCESS_GROUP, POSIX
   `killpg`; UTF-8 explícito en tuberías, fix P0 absorbido). `produce()`
   síncrono para tests. Timeout `produce: 300`.
2. **Opción A implementada** (autorizada por esa misión, §6): parámetro
   aditivo `events=False` en `producir_cancion` + CLI `--events` (default
   OFF). Regresión byte-idéntica probada (tests/test_produce_events.py en el
   DMD; sha histórico 32199acc… preservado). SUPERSEDE el "requiere
   autorización" de D26: la misión de implementación la concedió.
3. **Estados honestos**: el bloque `midi` del generation_manifest se escribe
   SOLO tras verificación en disco (existe, MThd, SHA256 == registrado) y el
   estado de producción avanza a `aplicado` únicamente con ese `midi_sha256`
   (engine.registrar_produccion). Idempotencia: gen con MIDI íntegro → 200
   idempotente, JAMÁS reescritura; integridad_error → 409.
4. **Jobs** (`composer/jobs.py`, nuevo): disciplina studio/jobs.py adaptada a
   hilos (sin fork): un activo por scope, estado persistente
   `jobs/<jid>.json`, timeout duro, cancelación cooperativa con proceso
   registrado, `recover_interrupted()` al arrancar. El DELETE de un proyecto
   con producción activa → 409 (evita rmtree-vs-hijo).
5. **Álbum = orquestador EXISTENTE reutilizado** (§7/D27, decisión de §10.3.3
   del roadmap): Composer MATERIALIZA un spec `dmd-album/1` (esquema real de
   `album/esquema.py`) con los docs de cada pista y delega el lote a
   `python -m album producir` en subprocess aislado y cancelable
   (`bridge.album_start`). Estados por pista del `estado.json` crash-safe del
   orquestador (con fallback a la evidencia real de cada pista); reintentos
   con `--regen`; reanudación re-ejecutando; producción en subcarpeta
   separada `output/albumes/<id>/produccion/` para que el orquestador nunca
   pise el plan de Composer. NO hay generador de álbumes paralelo.
6. **Reproducción**: `player.js` = copia literal de `web/app.js:442-522` con
   un único cambio (`hidden` por `opts`); wrapper `ComposerPlayback` con
   guard anti-solape y validación de forma. events.json por pista de álbum:
   regeneración determinista on-demand VERIFICADA contra el sha del
   orquestador (mismo núcleo; no es un segundo generador).
7. **Sin audio (D22 intacto)**: batería J11 automatizada lo vigila.

## D30 — Player WebAudio: vista previa, no render **[MANTENER]**

El sonido del navegador es una PREVISUALIZACIÓN por osciladores (rol por
voz). NO equivale al render con el soundfont del usuario; el disclaimer está
en la UI junto a cada reproductor. La equivalencia audible se verifica en la
máquina real (W1 del roadmap §11).
