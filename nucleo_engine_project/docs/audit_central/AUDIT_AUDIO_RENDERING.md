# AUDIT_AUDIO_RENDERING — FluidSynth, sfizz, soundfonts y MP3

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11.
> Sandbox: **sin** FluidSynth/sfizz/lame/sox/timidity; **con** ffmpeg 7.1.5-0+deb13u1 (libmp3lame + libshine), numpy 2.1.3, soundfile 0.13.1.
> Máquina objetivo: Windows 10 con `C:\tools\FluidSynth\bin\fluidsynth.exe`, `C:\tools\sfizz` y 5 soundfonts declarados (UNVERIFIED desde aquí).

---

## 1. El código de render existente en el repo (la evidencia más valiosa) — PARTIALLY VERIFIED (leído íntegro; no ejecutable aquí)

`forge/audio.py` (259 líneas, PROTEGIDO — solo lectura):

| Función | Detalle verificado |
|---|---|
| `find_fluidsynth()` (:16-25) | orden: env `MIDI_FORGE_FLUIDSYNTH` → `shutil.which` → `ROOT/tools/` → `ROOT/tools/fluidsynth/bin` → **`C:/tools/fluidsynth/bin`** → `C:/Program Files/FluidSynth/bin` |
| `find_soundfont(explicit)` (:28-36) | explicit → env `MIDI_FORGE_SF2` → `ROOT/soundfonts/` → `/usr/share/sounds/sf2` → **`C:/soundfonts`** → `~/soundfonts` (globs `*.sf2`+`*.sf3`) |
| `find_ffmpeg()` / `find_lame()` (:39-58) | env → which → `ROOT/tools`, `C:/ffmpeg/bin`, `C:/tools/ffmpeg/bin`, `C:/lame`, `C:/tools/lame` |
| `status()` (:61-65) | `{available: fs&&sf, fluidsynth, soundfont, mp3: fs&&sf&&(ff||lm), ffmpeg, lame}` — en sandbox `available: false` |
| `render_wav(midi_bytes, soundfont, gain=0.5, rate=44100)` (:68-83) | comando **literal**: `[fs, '-ni', '-g', str(gain), '-F', wav, '-r', str(rate), sf, mid]` con `timeout=300`; validación = `returncode==0 && isfile(wav)` (**sin chequeo de duración** — gap) |
| MP3 (:90+) | ffmpeg `[-y,-loglevel,error,-i,…,-codec:a libmp3lame,-b:a Nk]` (default **192**) o lame `[--silent,-b N]` |
| `master()` | hiss/crackle generados en Python → lowpass → **loudnorm 2 pasadas** (`I=LUFS:TP=-1.5:LRA=11`, `print_format=json`, `linear=true`) → `afade` exp/tri |

Studio (`studio/settings.py`) autodetecta además **GeneralUser-GS.sf2** por lista de nombres con validación `size>1024` (`_SF2_NAMES`). **Restricción estructural**: un único SF2 para todo el MIDI; **`.sfz` NO soportado** por el código actual → `TenorSaxophone-20200717.sfz` es inutilizable sin una capa nueva (sfizz).

## 2. Evidencia de ejecución histórica (decisiva)

- **8 jobs de Studio con `wav=true` terminaron `state=done` con `"wav": {"error": "RuntimeError: FluidSynth no encontrado…"}`** — registros reales en `studio_data/jobs/` (VERIFIED). El error handling funciona (WAV opcional), pero **no existe ni un WAV/MP3 renderizado en la historia del repo**.
- **Causa raíz identificada**: el runner hijo se arranca con `{PYTHONIOENCODING, PYTHONUTF8}` **sin heredar `os.environ`** → sin `PATH`, `shutil.which('fluidsynth')` devuelve None dentro del job (`studio/jobs.py:265-270` + `forge/audio.py:17`). Fix P0-2 del roadmap.
- **sfizz: CERO referencias en todo el árbol** (grep exhaustivo; su única aparición es el brief de la misión). Sin binarios `.exe/.dll/.sf2/.sf3/.sfz` en el árbol ni dentro de los 4 zips (`unzip -l` verificado).
- Fallback MP3 en navegador VERIFIED en código: `web/lame.min.js` (lamejs 156 KB) + OfflineAudioContext del convertidor legado; renderiza `music+3 s` de cola — cola que el render FluidSynth NO tiene (incoherencia documentada en §5).

## 3. MP3 en el sandbox — VERIFIED end-to-end (ejecución real)

WAV de prueba generado con numpy+soundfile (30 s, 44100 Hz, estéreo PCM16, 5.292.044 B) → ffmpeg:

| Variante | Tamaño | Tiempo encode | ffprobe |
|---|---|---|---|
| CBR `-b:a 192k` | 705 KiB (13,6 %) | 0,508 s (~59× realtime) | 192.000 bps, 44100 Hz, 30,041 s |
| CBR `-b:a 320k` | 1.175 KiB (22,7 %) | 0,486 s | 320.000 bps |
| VBR `-q:a 2` | 546 KiB (10,6 %) | 0,446 s | ~149 kbps promedio (contenido simple; música densa irá más alto) |

Adicionalmente VERIFIED: padding de frame +40,8 ms (normal); tags ID3 (`-metadata title/artist/album -id3v2_version 3`); `loudnorm` 2 pasadas y `alimiter=limit=0.891` disponibles. **Licencia** (VERIFIED): ffmpeg 7.1.5 build Debian `--enable-gpl --enable-libmp3lame --enable-libshine`; LAME es librería LGPL — invocar ffmpeg por subproceso **no contamina** la licencia de DMD; solo importa si se redistribuye el .exe.

**Conclusión**: este entorno genera MP3 con calidad y metadatos; en Windows falta solo localizar `ffmpeg.exe` o `lame.exe` (el código ya busca en `C:/ffmpeg/bin` y `C:/tools/ffmpeg/bin`).

## 4. MIDI→WAV en el sandbox

`command -v fluidsynth|sfizz|lame|sox|timidity` → rc=1 (todos NOT AVAILABLE); apt candidata fluidsynth 2.4.4 **no instalada** (la misión prohíbe instalar). Estado: **NOT AVAILABLE aquí** / **PARTIALLY VERIFIED en Windows** (código completo + ruta del exe conocida; 0 renders exitosos en evidencia → requiere 1ª ejecución real para pasar a VERIFIED).

## 5. Recomendaciones de render (RECOMENDACIÓN — separadas de lo VERIFICADO)

1. **Rate 44100** mantener (si entra sfizz, mismo rate en ambos renders). 2. **WAV 16-bit** para distribución. 3. **gain `-g 0.5–0.7`** máx (los sf2 orquestales tienen picos altos). 4. **Reverb ON moderado (CC91), chorus OFF/≤20 (CC93)** para dark jazz/triphop; **no introducir** `-R/-C` — reverb/chorus ya viajan dentro del MIDI como CC. 5. **loudnorm I=−16 LUFS** para streaming (TP=−1.5 ya fijado en código). 6. **alimiter=limit=0.891** como red anti-clip al mezclar stems (VERIFIED disponible). 7. **Añadir cola ≥2 s** (`apad` o bloque fantasma): hoy el render se corta sin cola de reverb — incoherencia con el fallback de navegador. 8. Stems = renders por canal (o perfiles de producción con misma seed) + `amix`. 9. **Tags ID3** (gap actual del repo). 10. **320 kbps CBR** para entrega con graves densos; 192 solo si pesa. 11. Validar duración/pico del WAV tras render (gap de robustez en audio.py).

## 6. Verificación pendiente en Windows (comandos listos para el usuario)

```bat
:: FluidSynth
C:\tools\FluidSynth\bin\fluidsynth.exe --version
dir C:\tools\FluidSynth\bin
:: sfizz (¿existe CLI de render?)
dir C:\tools\sfizz
C:\tools\sfizz\*.exe --help
:: MP3
where ffmpeg lame
ffmpeg -version | findstr libmp3lame
:: Soundfonts (tamaño + fecha; integridad básica = cabezas RIFF)
dir "C:\soundfonts" "C:\Users\Homeless\soundfonts" 2>nul
for %f in ("1.Timbres_of_Heaven.sf2" "Sonatina_Symphonic_Orchestra.sf2" "FluidR3 GM2-2.SF2" "2.GeneralUser-GS.sf2" "TenorSaxophone-20200717.sfz") do @if exist %f (echo %f OK) else (echo %f FALTA)
```

## 7. Tabla final de capacidades

| Capacidad | Estado sandbox | Estado esperado Windows | Evidencia |
|---|---|---|---|
| WAV→MP3 (192/320/VBR + ID3) | **VERIFIED** | Probable — falta ffmpeg.exe/lame.exe (UNVERIFIED) | `/tmp/audit_d/out_*.mp3` + ffprobe |
| loudnorm 2p / alimiter / fade / ID3 | **VERIFIED** | Igual con ffmpeg.exe | logs de encode |
| Render MIDI→WAV FluidSynth | **NOT AVAILABLE** (8/8 jobs fallidos controlados) | **PARTIALLY VERIFIED** (forge/audio.py + `C:\tools\FluidSynth`; 0 WAV en repo) | studio_data/jobs/ (8), PROJECT_STATE §8.1 |
| Elección sf2 (sf2/sf3) | NOT AVAILABLE (sin sf2) | PARTIALLY VERIFIED (GeneralUser autodetect; **no .sfz**) | settings.py, audio.py |
| sfizz / .sfz (sax tenor) | **NOT AVAILABLE** | **UNVERIFIED** (ni el repo lo referencia) | solo el brief de la misión |
| lame / sox / timidity | NOT AVAILABLE | UNVERIFIED | command -v rc=1 |
| Master FX (hiss/crackle/lowpass/fade) | PARTIALLY VERIFIED (código; piezas ffmpeg ejecutadas por separado) | Igual con ffmpeg.exe | audio.py::master |
| MP3 navegador (lamejs) | n/a | PARTIALLY VERIFIED (código legado `web/`) | lame.min.js 156 KB |
