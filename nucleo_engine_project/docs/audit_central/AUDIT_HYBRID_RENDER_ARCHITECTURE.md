# AUDIT_HYBRID_RENDER_ARCHITECTURE — Diseño de la solución SF2/SFZ híbrida por instrumento

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11 · Este documento es un **diseño** basado exclusivamente en capacidades VERIFIED; nada de él presupone capacidades de sfizz sin verificar.
> Ejemplo objetivo (misión): Sax→sfizz/TenorSaxophone.sfz · Rhodes→FluidSynth/GeneralUser-GS · Vibraphone→FluidSynth/Timbres_of_Heaven · Bass→FluidSynth/GeneralUser-GS · Drums→FluidSynth/FluidR3.

---

## 0. Principios no negociables

1. **El MIDI fuente jamás se modifica** (ni bytes ni metadatos). Toda copia filtrada es **temporal** (`TemporaryDirectory`), **verificable** (sha256 registrado) y **nunca sustituye la fuente**.
2. **Un único generador MIDI**: el render consume los MIDI de `producir_cancion`; la capa de audio es solo renderización.
3. **Fail-soft**: un instrumento sin asignación → fallback al SF2 master (GM); una asignación rota → error explícito ANTES de renderizar, nunca silencio.
4. Sincronización garantizada por construcción: todos los stems se generan del **mismo MIDI** (mismo PPQ, mismos tempos) al **mismo sample rate**.
5. Progresión por fases: **v1 = 1 SF2 para todo el MIDI** (hoy posible), **v2 = stems por canal SF2**, **v3 = SFZ/sfizz**. Cada fase es útil por sí misma.

## 1. Identificación de instrumentos en el MIDI (VERIFIED por forense de 27 SMF)

| Clave de identificación | Fiabilidad | Uso |
|---|---|---|
| **Canal MIDI** | Máxima — biyección track↔canal estable (sax ch0, rhodes ch1, vibes ch2, bass ch3, ch4 vacío, drums ch9, pad ch5) | Clave primaria del mapa de asignación |
| Track name (`sax_tenor`, `rhodes`, …) | Alta — nombres DMD fijos | Clave secundaria/humana |
| Program Change GM (66/4/11/38/91; drums sin PC) | Alta — PC fijos en tick 0, sin bank select | Validación cruzada + presets |
| Percusión | canal 9 (ch10 humano) — kit GM con 8 pitches (36,37,39,40,42,46,49,53) | Kit específico o kit GM |

La plantilla es **invariante** → un solo mapa por defecto sirve para toda la producción, con override por canción si se desea.

## 2. Perfil de render (`render_profile.json`) — esquema propuesto

```json
{
  "schema": "dmd-render-profile/1",
  "version": 1,
  "midi_source": {"path": "Track_01.mid", "sha256": "…"},
  "master": {"engine": "fluidsynth", "rate": 44100, "gain": 0.5,
             "fallback_sf2": {"name": "2.GeneralUser-GS.sf2", "path": "…", "sha256": "…"}},
  "assignments": [
    {"channel": 0, "role": "lead",    "engine": "sfizz",      "library": {"name": "TenorSaxophone-20200717.sfz", "path": "…", "sha256": "…"}, "phase": 3},
    {"channel": 1, "role": "keys",    "engine": "fluidsynth", "library": {"name": "2.GeneralUser-GS.sf2", "path": "…", "sha256": "…"}, "program": 4},
    {"channel": 2, "role": "mallets", "engine": "fluidsynth", "library": {"name": "1.Timbres_of_Heaven.sf2", "path": "…", "sha256": "…"}, "program": 11},
    {"channel": 3, "role": "bass",    "engine": "fluidsynth", "library": {"name": "2.GeneralUser-GS.sf2", "path": "…", "sha256": "…"}, "program": 38},
    {"channel": 5, "role": "pad",     "engine": "fluidsynth", "library": {"name": "1.Timbres_of_Heaven.sf2", "path": "…", "sha256": "…"}, "program": 91},
    {"channel": 9, "role": "drums",   "engine": "fluidsynth", "library": {"name": "FluidR3 GM2-2.SF2", "path": "…", "sha256": "…"}}
  ],
  "unassigned": "fallback_master",
  "mix": {"target_lufs": -16, "true_peak": -1.5, "limiter": 0.891, "reverb_tail_s": 2.0, "mp3": {"mode": "cbr", "bitrate_k": 320}},
  "validation": {"require_exists": true, "require_readable": true, "fail_on_broken_ref": true}
}
```

**Bibliotecas por REFERENCIA** (`name+path+sha256+size`), nunca copiadas al álbum. Si una referencia se rompe → error explícito con el campo culpable (requisito de la misión).

## 3. Motor A — FluidSynth (v1 y v2) — comando VERIFIED en código

`forge/audio.py:78` ejecuta `[fs, '-ni', '-g', gain, '-F', wav, '-r', rate, sf, mid]`, timeout 300 s. Para stems (v2): mismo comando sobre un **MIDI filtrado por canal**:

- Filtro por canal = copia temporal del SMF descartando los eventos de canales ajenos (el parser forense demuestra que el filtrado por canal es limpio: biyección track↔canal). Los meta de Conductor (tempo/TS/markers) **se conservan siempre** → sincronía garantizada.
- ⚠ **La mezcla viaja en el MIDI** (CC7/10/91/93 por canal): al renderizar un stem aislado esos CC aplican su volumen/pan/reverb del canal — correcto por construcción (es la mezcla pensada por DMD). Si se desea stem «crudo», el perfil puede indicar `strip_channel_cc: true` para neutralizar CC7/10 en el stem y mezclar a niveles propios.

## 4. Motor B — sfizz (v3, condicionado a verificación en Windows)

**Estado de evidencia**: NOT AVAILABLE en sandbox; cero referencias en el repo; ejecutables/CLI UNVERIFIED. La misión prohíbe presuponer una CLI funcional → el diseño v3 define **dos rutas** y elija la verificación:

| Ruta | Requisito | Riesgo |
|---|---|---|
| B1 — CLI de render offline (si existe, p. ej. `sfizz_render/render_midi` en `C:\tools\sfizz`) | Probe en Windows: `dir C:\tools\sfizz` + `*.exe --help` | Si no existe → ruta B2 |
| B2 — Wrapper local mínimo (proceso propio de la capa de audio que use la librería de sfizz) | Compilar/instalar algo nuevo → **requiere autorización explícita del usuario** (misión: no instalar sin autorización) | Complejidad; mantener como dependencia aislada |

Integración: igual que v2 (stem del canal 0 con el MIDI filtrado → sfizz con `TenorSaxophone.sfz`), luego mezcla común. **Limitación honesta**: el MIDI actual **no contiene keyswitches/aftertouch/SysEx** (VERIFIED) → SFZ dará su capa velocity + pitch bend (RPN0 ±2 st ya presente) y articulaciones por CC si el instrumento las mapea a CC existentes; no se puede «inventar» articulación que el MIDI no dispara. Ampliación futura de articulaciones = añadir CC/eventos en el doc (contrato) — no tarea de esta capa.

## 5. Mezcla de stems (VERIFIED: ffmpeg disponible)

```
ffmpeg -i stem_ch0.wav -i stem_ch1.wav … -filter_complex \
  "[0][1][2][3][4]amix=inputs=5:normalize=0,alimiter=limit=0.891,apad=pad_dur=2,loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json" \
  out.wav   →  (2ª pasada loudnorm linear=true)  →  mp3 -b:a 320k + ID3
```

- `amix normalize=0` preserva los niveles CC7 del MIDI; el limiter es red anti-clip; `apad` añade la cola de reverb que el render individual no tiene; loudnorm a −16 LUFS.
- Duraciones de stems idénticas por construcción (mismo MIDI+rate); la verificación post-mix compara muestras de borde.

## 6. Casos especiales resueltos por el diseño

| Caso | Solución |
|---|---|
| Tracks que comparten canal | No ocurre (biyección VERIFIED); si algún día ocurriera, el mapa agrupa por canal y el stem incluye ambos tracks |
| Notas duplicadas bass/kick (pitch 36) | Irrelevantes por canal: cada nota vive en su canal; solo serían problema en ruteo por pitch (no adoptado) |
| Percusión | Canal 9 → kit dedicado opcional (FluidR3) o kit GM del SF2 master; nunca mezclar ambos |
| Instrumento sin biblioteca | `fallback_master` (GM del SF2 master) — el render nunca se detiene por falta de asignación |
| Asignación incompatible (canal inexistente, sfz ilegible, ruta rota) | Validación previa del perfil → error explícito con campo culpable, antes de renderizar |
| Duplicación de notas entre motores | Imposible: cada canal sale exactamente por un motor (el mapa es función total y disyuntiva por canal) |
| MIDI fuente intacto | Todas las copias filtradas viven en `TemporaryDirectory` con sha256 registrado en el log del render |

## 7. Plan por fases (criterios de aceptación)

| Fase | Alcance | Criterio de aceptación |
|---|---|---|
| v1 | 1 SF2 master (GeneralUser-GS autodetect) para todo el MIDI | WAV por pista con duración ≈ MIDI + cola ≥2 s; MP3 320k con ID3; sha256 del MIDI fuente sin cambios |
| v2 | Stems por canal SF2 + mezcla ffmpeg | 5 stems + mezcla; sincronía exacta (mismo origen); validación de perfiles; limiter sin clip |
| v3 | SFZ del sax vía sfizz (ruta B1/B2) | Probe de sfizz VERIFIED en Windows; stem del canal 0 con SFZ; mezcla final; fallback GM si sfizz falla (fail-soft configurable) |

**Qué NO hacer**: no construir un renderizador propio de síntesis; no editar el MIDI fuente para «ayudar» al SFZ; no introducir dependencias Python de audio (todo vía binarios externos + ffmpeg, ya buscados por el código).
