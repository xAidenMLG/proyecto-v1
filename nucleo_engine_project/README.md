# MIDI Forge

> ## ⭐ NUEVO — DMD STUDIO (aplicación de composición sobre DMD + MIDI Forge)
>
> **DMD STUDIO** es una aplicación web local nueva para diseñar, validar y
> producir composiciones `dark-director/1` sin escribir JSON (con editor JSON
> opcional): editor visual de secciones con timeline, los dos modos armónicos
> reales (NATIVE/GUIDED), los 7 perfiles de producción, biblioteca Fase 7
> opcional, generación con el pipeline real (`scripts/produce.py`, determinismo
> web==CLI byte a byte), historial, evidencias y descargas.
>
> ```bat
> scripts\windows\install_studio.bat   (una vez)
> scripts\windows\start_studio.bat     (cada día → http://127.0.0.1:8899)
> ```
>
> Documentación completa: **`docs/DMD_STUDIO.md`** · API: `/api/docs`.
> El convertidor MIDI original de esta página sigue disponible más abajo.


Generador de MIDI configurable por JSON, con interfaz en el navegador (local). Basado en la lógica de *Neon Rain v2*:
voicings con voice leading, bajo con aproximaciones cromáticas y slides, lead con bends, batería por capas, humanización,
reparación automática de choques de semitono, tape-stop, fades y validación.

- **Sin dependencias**: solo Python 3.8+ (librería estándar). El MIDI se escribe con un escritor propio.
- **Solo local**: el servidor escucha en `127.0.0.1`; no se envía nada a internet.

## Inicio rápido (Windows)

1. Instala Python 3.8+ desde python.org (marca *Add python.exe to PATH*).
2. Doble clic en **`iniciar.bat`** → se abre `http://127.0.0.1:8765`.
3. Pestaña **JSON**: pega tu JSON (o elige un ejemplo) → *Cargar y normalizar* → **Generar** (`Ctrl+Enter`) → **Escuchar** (`Espacio`) → **MIDI**.

Sin interfaz: arrastra un `.json` sobre **`generar.bat`**, o `python app.py --cli entrada.json -o salida.mid`
(`--preset synthwave|triphop`, `--seed N`, `--project-out proyecto.json`).

## La interfaz

| Pestaña | Qué controla |
|---|---|
| JSON | Pegar/abrir JSON, ejemplos, ver el proyecto normalizado, informe de lo que se interpretó |
| Global | BPM, compás, tonalidad, semilla, humanización, tope de velocidad, preset, fade-out y tape-stop |
| Pistas | Por pista: instrumento GM, canal, volumen, pan, reverb, chorus, desafinación, offset/jitter, rango, mute/solo |
| Secciones | Nombre, tipo, compases, acordes (`Dm Bb F:2 C`), velocidad base, cambios de acorde por compás (sus4, splits), reordenar/duplicar |
| Bloques | Matriz **sección × pista**. Cada celda: activo, estilo, desde/hasta compás, velocidad (heredar/fija/rampa), semilla propia, parámetros del estilo y JSON avanzado; copiar a otras secciones |
| Lead | Frases del lead por sección (texto editable) y generador de sugerencias |
| Automatización | Rampas de CC (fade-in, swells, volumen) |
| Informe | Validación: choques, polifonía, voice leading, velocidades por sección, avisos |

Cada pista usa su propio generador de números aleatorios por (pista, sección, semilla del bloque): cambiar un bloque
**no altera** el resto de la canción.

## Formatos JSON aceptados

1. **Spec descriptivo** como `neon_rain_v2_spec.json` o `shadow_corner.json`. Se reconocen (español/inglés):
   `meta`, `global` (`bpm`, `time_signature`, `key_signature`/`key`/`mode`, `ticks_per_beat`, `seed`), `tracks`
   (`name`, `channel` base 0 o 1 autodetectada, `program`/`gm_name`, `range`, `cc7_volume`, `cc10_pan`, `cc91_reverb`,
   `cc93_chorus`, `detune_bend`, `timing_offset_ticks`, `map` y `humanization` de batería), `harmony.progressions` +
   `harmonic_rhythm` ("un acorde cada 2 compases"), `arrangement.sections` (`name`, `bars`, `velocity`,
   `instruments` con "(desde compas N)" y "(compases A-B)", y `notes`/`strings` con "full/bare"),
   `melody.phrases_beats_from_loop_start`, `melody.lead_phrases_by_section`, `melody.bends`, y menciones de
   tape-stop/fade. Lo que no se pueda interpretar usa los valores por defecto del **preset** (synthwave o triphop,
   autodetectado por la descripción) y queda listado en el informe.
2. **Proyecto canónico `midi-forge/1`**: lo que exporta el botón **Proyecto**. Es el formato completo y reproducible
   (mismo JSON + misma semilla = mismo MIDI byte a byte).
3. **Eventos** (`tracks[].notes[{start,duration,pitch,velocity}]`, `pitch_bend`, `controllers`): se reproducen tal cual.
   El botón **Eventos** exporta este formato.

## Esquema canónico (resumen)

```jsonc
{ "schema": "midi-forge/1",
  "global": { "bpm": 92, "time_signature": [4,4], "key": "D minor", "ticks_per_beat": 480, "seed": 92,
              "humanize": 1.0, "velocity_cap": 110, "pitch_bend_range": 2, "preset": "synthwave", "repair_clashes": true },
  "tracks": [ { "id": "pad", "role": "pad|strings|bass|arp|lead|drums", "name": "...", "channel": 1, "program": 88,
                "volume": 88, "pan": 64, "reverb": 120, "chorus": 60, "detune": 70, "offset_ticks": 0,
                "jitter_ticks": 6, "vel_jitter": 3, "range": [40,72], "mono": false, "mute": false, "solo": false } ],
  "sections": [ { "id": "coro", "name": "Coro", "kind": "intro|verse|pre|chorus|bridge|break|outro", "bars": 16,
                  "chords": ["Dm9","Am7","Bbmaj7","C(add9)"], "chord_bars": 1, "final": false, "velocity": [78,90],
                  "chord_overrides": [ { "when": {"bar_mod":[4,3],"cycle_parity":"odd"}, "split": [[0,2,"Csus4"],[2,4,"C"]] } ],
                  "blocks": { "<track id>": { "enabled": true, "style": "...", "from_bar": 0, "to_bar": null,
                                              "velocity": 90 /* o [ini,fin] */, "seed": 0, "params": { } } } } ],
  "lead": { "phrases": { "<section id>": [ { "bar": 0, "beat": 0.5, "pitch": "F5", "dur": 2.5, "vel": 90 } ] } },
  "automation": [ { "track": "pad|all|pitched|<id>", "cc": 11, "from": {"section":"intro","bar":0},
                    "to": {"section":"intro","bar":4}, "v0": 35, "v1": 127, "curve": 1 } ],
  "ending": { "fade_out": {"enabled": true, "exponent": 1.5}, "tape_stop": {"enabled": true, "bars": 2, "semitones": -8.4} } }
```

Acordes: `Dm`, `Bb`, `F/A`, `Am7`, `Dm9`, `Bbmaj7`, `C(add9)`, `Csus4`, `Cmaj13`, `G7#9`, `Dm7b5`, `Edim7`, `A+`, `C5`…
`"Dm:2"` = 2 compases (admite fracciones, `"F:0.5"`).

### Estilos de bloque por rol

- **keys** (Rhodes): `hold` (acordes con `restrike_beats`), `broken` (acorde roto suave: `step`, `pattern`, `ring`, `rest_prob`) y `tail`
  (colas que decaen). Voicings `rootless`/`compact` con voice leading global.
- **mallet** (vibráfono): `replies` (responde **en los huecos del lead**: `prob`, `min_gap`, `glint_gap`, `margin`, `fragment`,
  `degrees` 9/6/5, `min_distance` al lead, `max_per_bar`) y `pings` (notas sueltas con cola larga). Nunca pisa ni dobla al lead.
- **pad / strings**: `sustain` (acordes largos; `voicing.profile` = `rootfifth`, `triad`, `full`, `bare`, `shell`, `open4`, `spread`;
  strings admiten `modes`/`modes_by_cycle` para alternar full/bare por ciclo) y `stabs` (`rhythm: [[pos,dur,velΔ],…]`).
  Voice leading global (Viterbi) a lo largo de **toda** la canción. `tension` añade notas de roce intencionales (clusters).
- **bass**: `pattern` (`pattern_set` o `patterns` propios con `R` raíz, `F` quinta, `O` octava, `T` tercera, `S` séptima, `A`
  aproximación cromática; `approach`, `slide_in`, `slide_out`) y `long`.
- **arp**: `arp` (`step`, `pattern`/`pattern_list` con `null` = silencio, `alt_patterns`, `degrees`, `ext_degrees`, `step_changes`)
  y `pings`.
- **lead**: `auto` (frases si existen; si no, generativo), `phrases`, `generative`, `hold`; `bends.scoop` y `bends.fall`.
- **drums**: `pattern` con `preset` o `layers` propias:
  `{"inst":"snare","at":[1,3],"vel":[86,88],"offset":0.05,"prob":1,"when":{"bar_mod":[2,1]}}`; también `grid`, `pick`, `omit`,
  `drag`, `skip_if_open`, `vel:{"v0":..,"v1":..,"over":"steps|when|section"}` y `fills` (`hits`, `rolls`, `mute`).
  La pestaña Bloques tiene *Copiar capas del preset para editarlas*.

Condiciones `when`: `bars`, `not_bars`, `from`, `to`, `last`, `bar_mod:[m,r|[r…]]`, `cycle_parity`, `final`,
`occurrence_min/max` (compás relativo a la sección).

## Specs con notas de implementación (p. ej. `shadow_corner_hybrid.json`)

Además de los campos básicos, el adaptador entiende (inglés/español):

- `midi_implementation_notes`: `beat_indexing` "1-based" (los beats de las frases se desplazan −1) y `channels` "zero-based".
- `harmonic_rhythm` en inglés ("One chord every 2 bars").
- Roles por nombre/GM: sax → lead, Rhodes → keys, vibráfono → mallet (la descripción larga de `role` **no** se usa para clasificar;
  solo aporta pistas de ataque/release → CC73/CC72).
- Instrumentos de sección con **modificadores**: `vibraphone_sparse`, `vibraphone_selective`, `pad_wider`/`pad_widest`,
  `drums_sparse`/`drums_fuller`/`drums_fade`, `bass_sparse`/`bass_fading`, `rhodes_tail`, `vibraphone_tail`, `tenor_sax_hook`…
- `melody.bends` en texto ("-0.2 semitone … 100-140 ticks only on selected phrase entries" → semitonos, duración y **probabilidad**).
- `humanization.hats` ("irregular low-velocity 16ths; jitter +-10 ticks; omit 25-35%; occasional late hat").
- `rhythm.bass` ("One long note every 2 bars", "One long root note per bar").
- `dynamics.range` ("chorus peaks around 88-90" → tope de velocidad global, incluida la batería).
- `mp3_render` → **Render FX**; `claude_generation_brief` / `validation` → comprobaciones activadas (ver Informe).
- Lo que no se puede cumplir en MIDI (gain por pista, ancho estéreo, LUFS en el navegador, soundfont) se **lista como límite** en
  el informe en lugar de ignorarse en silencio.

### Render FX (`project.render`)

`{"enabled":true,"lowpass_hz":8500,"loudness_lufs":-18,"fade_out_seconds":20,"fade_curve":"exp","noise":{"hiss":{"level":0.0012,"profile":{"intro":1,"outro":1,"default":0.25}},"crackle":{"per_second":3,"level":0.03,"profile":{...}}}}`.
Con FFmpeg en el servidor se aplica todo (hiss, crackle, lowpass, loudnorm en 2 pasadas, fade). El MP3 del navegador aplica lowpass,
ruido, fade y normaliza el pico. Editable en **Global → Render FX**.

### Cumplimiento automático (pestaña Informe)

BPM/compás/compases/duración declarados, pistas y programas GM, canal dedicado por pista, lead monofónico y en rango, silencios del lead,
vibráfono escaso y sin pisar/doblar al lead, bajo vs bombo, sin four-on-the-floor, notas dentro de su sección, repetición rítmica del motivo del coro,
sin intensidad máxima constante. No puntúa "atractivo" (requiere escucha humana).

## MP3

El botón **⬇ MP3** (cabecera) descarga la canción en MP3 y funciona en cualquier instalación:

- **auto** (por defecto): si el servidor tiene FluidSynth + soundfont `.sf2` + `ffmpeg` o `lame`, genera el MP3 con
  **instrumentos reales** (192 kbps). Si no, usa el navegador automáticamente.
- **navegador**: renderiza con el sintetizador de la vista previa (WebAudio `OfflineAudioContext`) y codifica con
  **lamejs** (incluido en `web/lame.min.js`, no necesita internet). Una canción de ~4 min puede tardar de decenas de
  segundos a un par de minutos según tu PC; la página sigue respondiendo y muestra los segundos transcurridos.

También por línea de comandos: `python app.py --cli entrada.json -o salida.mid --mp3 salida.mp3` (camino del servidor).
`ffmpeg.exe` o `lame.exe` pueden estar en el PATH, en `tools\` o definirse con `MIDI_FORGE_FFMPEG` / `MIDI_FORGE_LAME`.

## WAV opcional

El preview del navegador es un sintetizador sencillo (WebAudio). Para un WAV con instrumentos reales: instala FluidSynth
(`fluidsynth.exe` en el PATH o en `tools\`) y copia un soundfont `.sf2` a `soundfonts\` (o define `MIDI_FORGE_FLUIDSYNTH` /
`MIDI_FORGE_SF2`). El botón **WAV** se activa solo si los encuentra.

## Pruebas

`python -m unittest discover -s tests -v` (25 pruebas: teoría, MIDI, voice leading, adaptadores, motor, robustez, API).

## Notas y límites

- La interpretación de texto libre (p. ej. "full en el 1er loop") usa heurísticas; el informe muestra cada decisión.
- En proyectos de **eventos** no hay intención guardada: la validación puede contar como choque notas disonantes que eran intencionales.
- Reparación de choques: mueve de octava o quita notas de pad/strings/arpegio que chocan por semitono (o 9ª menor) con
  otra pista; el lead y el bajo se protegen. Se puede desactivar en Global.

## Licencias de terceros

`web/lame.min.js` es **lamejs 1.2.1** (puerto a JavaScript del codificador LAME), licencia LGPL-3.0, incluido sin modificar
(https://github.com/zhuker/lamejs). Todo lo demás es código propio sin dependencias.
