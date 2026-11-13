# DMD COMPOSER — MANUAL DE USUARIO

*Para usar el Studio con cabeza, no con suerte. Versión 1.0.*

> **Nota de planificación v1.2 (2026-11-11):** este manual describe el flujo
> v1.1 vigente ("Composer no genera MIDI; importas el doc en Studio"). El
> ámbito del producto cambió por decisión oficial: Composer **generará MIDI
> por el pipeline existente, lo reproducirá en el navegador y creará álbumes
> completos** — sin conversión de audio (esa es tu aplicación externa).
> Las secciones siguientes describen el comportamiento ACTUAL; el flujo nuevo
> está planificado (no implementado) en `IMPLEMENTATION_ROADMAP.md` y se
> documentará aquí cuando entre en servicio.

---

## ¿Qué es esto?

DMD Composer es el **panel de dirección** de tu música. DMD Studio compone el
MIDI; Composer decide **qué** debe componer: la identidad, los instrumentos,
la estructura de la canción y la armonía de cada parte. Tú fijas lo que quieres,
Composer resuelve lo que falta con coherencia, y todo lo demás se lo deja al
motor de DMD, que es quien sabe tocar.

**Importante:** Composer no genera MIDI ni WAV. Genera un documento JSON
(`dark-director/1`) que **importas en DMD Studio** y ahí generas el MIDI como
siempre. Composer es el arquitecto; Studio es la obra.

### La regla de oro: tres tipos de decisión

En cada pantalla verás un selector con tres opciones:

| Opción | Qué significa | Ejemplo |
|---|---|---|
| **Fijada** | "Lo quiero ASÍ, no cambies" | Identity: Dark Trip Hop |
| **Automática** | "Composer elige una opción buena y la escribe" | BPM → Composer elige 84 y lo anota |
| **Libre** | "Que decida el motor con su receta" | Resolución → el doc ni la menciona |

Automático ≠ Libre: automático significa que Composer TOMÓ una decisión concreta
y la escribió en el JSON (podrás verla en el log). Libre significa que el campo
ni aparece, y el motor DMD usa su receta musical.

---

## Antes de empezar

1. Ejecuta `scripts\install.bat` (una sola vez: crea el entorno e instala las
   dependencias web, las mismas que Studio ya usa).
2. Ejecuta `scripts\check.bat`. Debe decir **CHECK OK** y mostrar los catálogos
   reales de tu DMD (8 instrumentos, 7 tipos de sección, 3 identidades, 7 perfiles).
   Si no encuentra el DMD: crea `composer_data\composer_config.json` con:
   ```json
   {"dmd_path": "C:\\Users\\Homeless\\Documents\\Midi\\nucleo_engine_project"}
   ```
   y vuelve a ejecutar check.bat.
3. Arranca con `scripts\start.bat` y abre **http://127.0.0.1:8898** en el navegador.
   (Studio usa el 8899; Composer usa el 8898: pueden estar abiertos a la vez.)

Arriba a la derecha verás `● DMD: …` en verde: es la integración en vivo.

---

## Vista 1 · Setup (identidad e instrumentos)

**Para qué sirve:** decidir QUIÉ es la canción.

* **Identidad musical** — `dark_triphop` es la identidad activa del ecosistema
  (las doom aparecen marcadas como archivadas). Si la dejas Fijada, todo el
  universo sonoro gira ahí.
* **Mood** — el interruptor del randomizador: Melancólico, Oscuro, Esperanzador,
  Tenso o Neutro. NO fuerza nada: pondera tonalidades, lenguaje, energía y
  atmósfera (una canción melancólica FAVORECE tonos menores, no los impone).
* **Espacios musicales** — "obligatorios" garantiza una sección de aire
  (break con solo algunos instrumentos y batería ligera) aunque uses plantilla
  automática.
* **Instrumento protagonista** — el que manda. Si eliges Vibraphone, Composer
  prioriza arreglos donde el vibes tiene sitio: focos, densidades y
  acompañamientos compatibles. Solo puede haber UNO (si marcas dos, es conflicto
  y Composer te lo dice).
* **Tabla de instrumentación** — los 8 instrumentos REALES del contrato
  (Sax tenor, Rhodes, Vibraphone, Bass, Drums, Piano, Pad, Strings):
  - **Protagonista** = prioridad funcional.
  - **Acompañante** = presente y soporte.
  - **Off** = apagado explícito (enabled=false).
  - **Auto** = el motor decide con su receta.
  - **Activación** — por defecto "libre"; pon `enabled=true` solo si quieres
    FORZAR un instrumento que no está en el set base de la identidad (por
    ejemplo Piano en dark_triphop). Composer te avisará si algo no va a sonar.
  - **Density** — déjalo vacío salvo que sepas lo que haces; bass/drums/pad/strings
    ni la usan en esta versión (el validador lo avisaría).

**Con qué combinar:** el Mood de aquí alimenta la Vista 4 (Randomizador) y las
plantillas de progresión de la Vista 3.

---

## Vista 2 · Estructura

**Para qué sirve:** dibujar el ESQUELETO de la canción, sección a sección.

* **Añadir sección** — nombre visible libre ("Verse 1", "Preludio", "Estribillo
  grande") + tipo funcional del catálogo real (Intro, Verse, Pre-Chorus, Chorus,
  Bridge, Break/Interlude/Solo, Outro) + compases (duración).
  ¿Por qué dos cosas? El contrato solo entiende los 7 tipos; el nombre bonito
  viaja al Song Map para que escribas letras.
* **Duplicar / ↑ / ↓ / ✕** — copiar una sección, reordenarla, borrarla.
* **Por sección:** energy / tension / density (0–1, déjalos vacíos = libre),
  drums (off → air → light → groove → heavy), "acordes cada N compases" (ritmo
  armónico de ESA sección), y **final** (marca la sección que cierra la canción;
  si marcas varias, aviso).
* **focus (máx 3)** — los instrumentos protagonistas de esa sección (se les da
  más velocidad y presencia).
* **active** — whitelist: SOLO suenan los marcados. Es la herramienta de los
  "espacios": un break con solo Vibraphone + Rhodes + Pad y drums en light.
* **Cronología** — la barra de abajo dibuja la canción con compases totales y
  duración aproximada según el BPM.

**Regla dura:** mínimo 2 secciones (el contrato lo exige). Con cero secciones,
Composer usará una plantilla estructural de tu mood.

---

## Vista 3 · Armonía

**Para qué sirve:** escribir los acordes de cada sección con grados romanos.

* **Tonalidad** — fíjala si quieres armonía guiada (`D minor`, `C major`,
  `A dorian`, `Eb minor`…). Si la dejas automática, el randomizador la elige
  por mood.
* **Modo de armonía:**
  - **Guiada** — tú escribes los grados por sección; Composer los convierte a
    acordes reales con la MISMA gramática que el motor. Para canciones con
    estructura y letras.
  - **Nativa** — la receta N1 de la identidad crea las progresiones. Libertad
    total del motor. (Puedes MEZCLAR: algunas secciones guiadas, otras nativas.)
* **La conversión (¡mirala en vivo!):** la escala fija la raíz y la calidad
  diatónica. En C major, `I - III - vi - V` → `C - Em - Am - G` (III es Em
  porque E-G-B es la tríada del tercer grado). En D minor, `V` da la dominante
  A (convención del pop); si quieres el v menor, escribe `Vm`.
* **Tokens útiles:** `7` (dominante) · `maj7 m7 m9 9 11 13` · `sus4 7sus4 add9` ·
  `dim o + aug m7b5` (disminuidos/aumentados) · `b` `#` antes del grado
  (`bVI`, `#iv0`) · `6` y `64` = inversiones (`vi6` → Am/C) · bajo literal
  (`V7/B`) · `Grado:N` = ese acorde dura N compases (`I:2 - V:1`).
* **Repetición automática:** una progresión de 4 acordes en una sección de 16
  compases se repite en ciclo hasta llenar (comportamiento real del motor).
* **Botón "Aplicar plantilla del mood"** — rellena SOLO las secciones guiadas
  que aún no tienen progresión, con plantillas coherentes con tu mood.
* **F7 (biblioteca de familiaridad)** — SIEMPRE opcional: se elige al generar en
  Studio, no aquí. Composer nunca la mezcla por su cuenta.

**Limitación honesta:** dos acordes dentro del MISMO compás no existe en este
contrato (mínimo 1 compás por acorde). Todo lo demás (un acorde por compás,
dos compases por acorde, distribución a medida) sí es representable.

---

## Vista 4 · Randomizador

**Para qué sirve:** ver y controlar qué decide Composer.

* **Seed** — la semilla del randomizador. Misma seed + mismas decisiones =
  MISMA composición, bit a bit. Fija una (p. ej. 2026) cuando tengas algo bueno
  y quieras poder volver a él exacto.
* **Botón "Resolver plan y mostrar conflictos (sin guardar)"** — ensayo general:
  resuelve todo y muestra:
  - **Errores** (bloquean): estructura inválida, dos protagonistas, progresión
    imposible…
  - **Avisos** (no bloquean): BPM fuera del rango típico de la identidad (W401),
    doom 1:1 (W402), acordes fuera del vocabulario (W414)…
  - **El plan completo**: qué FIJASTE tú, qué decidió Composer (con el porqué),
    y qué quedó LIBRE para el motor.
* **Diversidad** (en Vista 1, módulo D): Contenida = gustos marcados; Equilibrada
  = balance; Aventurada = explora más opciones no obvias, siempre coherentes.

**Las tres clases de reglas que aplican (automáticamente):**
1. *Duras*: tus decisiones fijadas se respetan al pie de la letra.
2. *Compatibilidad*: BPM dentro del rango de la identidad al elegir automático,
   doom nunca 1 acorde por compás, protagonista sonando, espacios ⇒ sección de aire.
3. *Ponderadas*: el mood inclina tonalidades/lenguaje/energía sin repetir fórmula.

---

## Vista 5 · Preview

**Para qué sirve:** revisión final antes de producir. Tabla de estructura con
parámetros fijados, tabla armónica por sección, y el log de explicabilidad
(qué se descartó y por qué). Los conflictos se recalculan en cada ensayo
(vista 4) y en cada composición (vista 6).

---

## Vista 6 · Output

**Para qué sirve:** producir el documento y llevarlo a Studio.

* **Componer y validar** — genera el doc + Song Map y los valida con el
  VALIDADOR REAL de tu DMD y los compila con el COMPILADOR REAL. Verás:
  - `✓ Documento válido para dark-director/1 · seed N · compilado (X compases, midi-forge/1)`
  - Avisos W4xx honestos (no bloquean).
  - **Song Map**: tabla con compás inicial–final, progresión real y fuente
    (tu progresión guiada / receta N1), más un bloque listo para tu letra:
    ```
    [Intro]  (1–4, 4 compases · Dm - F)
    [Verse 1]  (5–20, 16 compases · Dm - F - C - Bb)
    ...
    ```
  - **Descargas**: `doc.json`, `song_map.json`, `song_map.csv`,
    `generation_manifest.json` (incluye SHA256, decisiones y explicabilidad).
* **Historial** — cada composición se guarda en `output/<proyecto>/gen_NNNN/`.
  NUNCA se sobrescribe: cada clic crea una generación nueva.

### Importar en DMD STUDIO (paso a paso)

1. Descarga `doc.json` desde la Vista 6.
2. Abre Studio (`http://127.0.0.1:8899`) → **PROJECTS** → crea un proyecto nuevo
   con el mismo nombre de la obra.
3. Ve a **ADVANCED JSON EDITOR**, pega el contenido de `doc.json` y guarda el
   proyecto. Botón **Validar**: Studio usará SU validador real (el mismo motor)
   y debe decir `✓ válido para dark-director/1`.
4. **GENERATION** → elige perfil de producción (el que fijaste en Composer o
   "full") → seed (la misma de Composer si quieres exactitud) → **Generar MIDI**.
5. (Opcional) **Harmony**: si quieres F7 (melancholic, dark_cinematic…),
   selecciónalo aquí. Es independiente y voluntaria.

### Modo álbum

En la misma Vista 6: nombre + número de pistas + "Crear álbum desde este
proyecto". Composer comparte identidad/instrumentos/restricciones y DIVERSIFICA
cada pista (tonalidad, BPM, estructura, groove, seeds) con registro de huellas
para no repetir combinaciones. Genera pista a pista con "generar" (y puedes
reanudar otro día: lo ya generado no se regenera). El MIDI de cada pista se
produce en Studio/Con el pipeline de DMD.

---

## Las 5 demostraciones (carpeta `profiles/`)

| Carpeta | Qué demuestra |
|---|---|
| `demo_1_totalmente_automatica` | Solo el mood fijado; Composer decide TODO lo demás |
| `demo_2_solo_vibraphone` | Vibraphone protagonista + espacios obligatorios (misión §3) |
| `demo_3_sax_rhodes_espacios` | Sax protagonista, Rhodes acompañante, vibráfono fuera |
| `demo_4_estructura_personalizada` | 10 secciones con nombres propios + las progresiones I-III-vi-V de la misión (→ C-Em-Am-G) |
| `demo_5_restricciones_parciales` | Solo 4 decisiones fijadas, resto automático |

Cada carpeta trae `proyecto.json` (ábrelo como proyecto copiándolo a
`projects/<pid>/project.json` o recreándolo en la UI), `doc.json` ya validado
por el validador real, `song_map.json/csv` y `generacion.json` con la SHA256
de verificación. Regenerables siempre con `python scripts\demostraciones.py`.

---

## Recetario rápido

* **Quiero una canción melancólica con vibes y sin pensar más:** Setup → mood
  Melancólico, espacios Obligatorios, protagonista Vibraphone → Vista 4 →
  resolver plan → si te gusta → Vista 6 → Componer (seed fija 2026).
* **Quiero una canción PARA LETRAS:** Vista 2 dibuja Intro/Verse/Pre/Chorus/
  Bridge/Outro con nombres bonitos → Vista 3 progresiones por sección (o
  plantilla del mood) → Vista 6 → copia el bloque `[Sección]` sobre tu letra.
* **Quiero el hook pegadizo comercial:** accesibilidad `commercial` + marca
  loop_bars (o deja que el aviso W404 te lo recuerde).
* **Quiero experimentar:** mood Tenso, diversidad Aventurada, lenguaje
  experimental, y seed distinta en cada intento.
* **Algo suena raro:** mira los avisos W4xx del resultado; cada uno dice qué
  decisión cambiar. El validador real nunca miente.

## Preguntas frecuentes

**¿Puedo tocar los JSON a mano?** Sí: es tu máquina. Pero Composer los valida
contra el contrato; si metes un campo inventado, el validador real te lo dirá
(E109). Las extensiones `x_*` son el único mecanismo de extensión del contrato.

**¿Composer cambia mis decisiones?** Nunca. Las fijadas van tal cual; los
conflictos se INFORMAN con la decisión que hay que cambiar.

**¿Dónde están mis datos?** `projects/` (proyectos), `output/` (generaciones),
`composer_data/` (config y manifiesto). Todo local, todo tuyo.

**¿Puedo tener Studio y Composer abiertos?** Sí: puertos distintos (8899/8898).
