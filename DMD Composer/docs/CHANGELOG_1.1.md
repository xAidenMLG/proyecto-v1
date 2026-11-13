# CHANGELOG — DMD COMPOSER 1.1.0 (2026-11-11)

Resolución de las limitaciones, inconsistencias y deficiencias identificadas en
`MANUAL_USUARIO_DMD_COMPOSER.md` (Anexo A, D-01…D-10) y en la auditoría técnica
de la misión v1.1. **Sin tocar DMD Studio, el contrato dark-director/1 rev 3.2,
los motores protegidos, los goldens ni MIDI Forge** (integridad verificada por
hash antes/después y por la batería F).

## F2.1 — Native vs Guided Harmony (definitivo)

* Semántica cerrada y documentada en `builder.py`:
  - **Guiada** = progresiones explícitas por sección; cada sección con decisión
    guiada DEBE tener grados o acordes literales (error si no).
  - **Nativa** = recetas N1 reales del motor; las secciones con grados guiados
    NO viajan y se AVISA (`guiada-ignorada`), nunca conversión silenciosa (D-05).
  - **Sección Nativa dentro de composición Guiada** = usa N1 (capacidad soportada
    por la cadena de precedencia del compilador; el Song Map lo marca).
  - **Guiada sin progresiones** = aviso explícito `armonia-implicita` que NOMBRA
    las secciones y la acción necesaria + `modo_real_del_doc` honesto en build/manifest.
* `harmony_mode` resuelve AUTO con criterio demostrable (hay grados/acordes →
  guided; si no → native) y su log lleva el estado REAL (fixed/auto — D-06).
* `harmony_mode` ya no admite "Libre" ni por API (D-07): es una instrucción de
  construcción del documento, no un campo del contrato.
* Manifest: bloque `armonia` con modo global, modo REAL del doc, secciones
  guiadas/literales/nativas/sin decisión y `fuente_por_seccion` (coherente con
  el Song Map).

## F2.2 — Protagonista instrumental con consecuencias reales (D-01)

* Nuevo `composer/proposal.py`: propuesta de distribución usando SOLO campos
  reales del contrato (`instruments.role/enabled/density`, `structure[].focus`,
  `structure[].active`), con `focus_default` REAL de la receta introspeccionada.
* El usuario la ACEPTA (quedan escritos y editables), la MODIFICA después o la
  RECHAZA (no toca nada); el estado queda en el proyecto y en el manifest
  (`protagonista.propuesta`). NUNCA se aplica sola.
* Auto = LEAD de la receta de la identidad (dato real, no invención).
* `density` propuesta = 0.6 (banda B2 del contrato; evita W403 con
  `mallet_sparse`); NO se propone para bass/drums/pad/strings (W410 real).
* Aviso si hay rol "protagonista" en la tabla sin eje protagonista activo.
* Endpoints: `GET protagonist/proposal`, `POST protagonist/apply`,
  `POST protagonist/reject` + panel en la UI (Setup).

## F2.3 — Groove y BPM

* BPM fijado se conserva EXACTO (test 6); el groove ya no puede confundirse con
  el tempo: su log dice literalmente que NO es campo del contrato ni parámetro
  del motor y que su único efecto real es sesgar la curva de BPM AUTOMÁTICO.
* Con BPM fijado y groove Automático: moderación suave de los extremos
  (pesos, nunca correcciones) y registro del criterio.
* BPM Libre = el motor decide con su receta (BPM_DEFAULT): NO se escribe
  `global.bpm` (corrección QA: antes se calculaba y se escribía sin clasificar).

## F2.4 — Perfil de producción con transmisión verificable

* El perfil ya NO se declara como decisión del doc: bloque dedicado
  `produccion` en el manifest con `estado: "seleccionado_pendiente_de_aplicar"`
  (jamás "aplicado"), origen (usuario/composer) e INSTRUCCIÓN verificable:
  - `instruccion.studio`: qué importar en DMD Studio y con qué Producción/seed/F7.
  - `instruccion.cli`: comando exacto de `scripts/produce.py` (verificado
    end-to-end en esta versión: MIDI real con SHA256).
  - F7 (keyword + variación) viaja en la instrucción como OPCIONAL (nunca en el doc).

## F2.5 — Explicabilidad y manifiesto (D-06, D-08)

* `decisiones = {fijadas, automaticas, libres}` DISJUNTOS por construcción; un
  único estado REAL por eje (test 8 verifica ausencia de duplicados).
* `preferencias_composer` separado: mood/atmosphere/groove/diversity con su
  efecto real y la marca de que NO llegan al doc.
* `descartadas` registradas en TODAS las elecciones ponderadas (peso de cada
  alternativa) y en las curvas de BPM (zonas descartadas).
* seed Libre = el plan es determinista pero el doc NO lleva `global.seed`
  (aviso honesto: reproducibilidad vía `--seed`).
* protagonista fixed "none" = log `fixed` con valor "none" (antes log "free").

## F2.6 — Identidades archivadas (D-03)

* La UI las marca ("ARCHIVADA (histórica)") y lista cuáles son; el manifiesto
  expone `identidad_activa` / `identidades_archivadas`; al componer se emite el
  aviso `identidad-archivada`. Compatibilidad histórica intacta.

## F2.7 — Armonía explícita (editor de acordes literales)

* `HarmonySection.chords`: símbolos literales reales (`G/B - Dm9:2 - Fmaj7`),
  escritos en `structure[].chords` (posición 1 de §2.8: precedencia MÁXIMA con
  cualquier modo global; el Song Map los marca `explicito`).
* Validación con el parser REAL del DMD (nueva tarea de puente `parse_chords`
  sobre `forge/theory.parse_chord`, separando el sufijo `:bars`): un solo motor
  armónico; símbolo inválido → error E113 ANTES de guardar (nada se escribe).
* Prevalidación en vivo en la UI (raíz/bajo/notas/compases por símbolo).
* Se mantuvo el parser de grados romanos sin cambios.

## F2.8 — Modo álbum

* `POST /api/albums/{id}/generate_all`: genera todas las pistas pendientes en
  orden (reanudable; el plan se recarga del disco antes/después de cada pista).
* Informe de diversidad (`informe.json` + endpoint): tonalidades distintas,
  distancias tonales por círculo de quintas (corregido con bemoles), rango BPM,
  lenguajes/grooves/plantillas, combinaciones duplicadas (0 garantizado por
  huellas), SHA256 por pista. Sin MIDI: el productor sigue siendo el pipeline DMD.
* `_harmonias` compartidas: las decisiones armónicas de la base viajan a las
  pistas con estructura compartida (antes quedaban sin progresión).
* Residuo de tests en `projects/` eliminado y los tests G/I ya no ensucian
  datos de usuario (D-10).

## F3 — Otras mejoras y higiene

* D-02: botón **Verificar DMD** en la barra superior (re-introspección inmediata
  con detección de cambio de fingerprint y recarga de catálogos).
* D-04: código muerto eliminado (`LABEL_TYPES`, `type_for_label`,
  `LANG_DEFAULT_RES`, `_ultimo_dir_reservado`).
* D-09: origen del manifiesto distingue "vivo (introspeccionado ahora)" de
  "caché (misma ruta del DMD)".
* Imports duplicados en `server.py` eliminados; `__version__` → 1.1.0.
* Bug de UI corregido: las vistas previas de armonía leen el estado vivo
  (closure obsoleta tras el primer guardado hacía que no se refrescaran).

## QA (Fase 4)

* Batería completa: **114 tests en verde** (A–H, 77 originales + batería I de
  37: las 14 pruebas obligatorias de la misión + regresiones del anexo + QA).
* Las 5 demostraciones siguen **byte-reproducibles** (SHA256 idénticos).
* Recorrido completo demostrado: UI → modelo → doc.json → validador REAL →
  compilador REAL → MIDI real (perfil + F7 de la instrucción) → Song Map → manifest.
* QA independiente (agente externo): 109/109 de su momento, 9/9 motores
  protegidos intactos, 6/6 pruebas destructivas; sus 2 hallazgos medios (bpm/seed
  Libre sin clasificar; círculo de quintas con bemoles) y menores (pid, higiene,
  asertos débiles) quedaron CORREGIDOS en esta versión.
* UI verificada en navegador real (Chromium): propuesta aplicada (6 cambios),
  acordes literales prevalidados (G/B · Dm9:2 · Fmaj7), composición con fuentes
  armónicas por sección, instrucción de producción, álbum 3 pistas con informe.

## LIMITACIONES QUE PERMANECEN (honestidad)

* El modo álbum NO produce MIDI ni sustituye `album/` de DMD (misión §8):
  la integración con el orquestador real sigue siendo la misión futura
  documentada en NEXT_MISSION.md.
* Sin WAV en Composer (Studio lo renderiza); sin marcadores MIDI (limitación
  del contrato); `development` fuera de alcance; F7 solo al producir.
* La calidad musical final la juzga el usuario (los tests prueban validez,
  coherencia y reproducibilidad, nunca "suena bien").
* La UI se verificó en Chromium (único navegador del entorno de prueba).
