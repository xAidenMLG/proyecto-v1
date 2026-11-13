# DMD COMPOSER — COMPATIBILIDAD

Versión auditada: **dark-director/1 rev 3.2** · compilador 0.1.0 · jazz_engine 7.0.0

> **Actualización v1.2 (2026-11-11):** se añade al final la sección "Ruta de
> producción MIDI (planificada)". Nada del texto existente cambia.

## Fuente de verdad

La compatibilidad NO se declara: se VERIFICA. Cada documento que Composer
emite pasa por:

1. **Validador real** (`dark_director.validador.validar`) vía subprocess aislado.
   Test A2 de la batería: cero E109 (ningún campo inventado, en ningún nivel).
2. **Compilador real** (`dark_director.compilador.compilar`) sin renderizar.
   Test F2: el documento compila y emite `midi-forge/1`.
3. **Pipeline real de MIDI** (`scripts/produce.py::producir_cancion`).
   Test F4/F5: MIDI real + reproducibilidad byte a byte con la misma seed.

## Superficie del contrato usada por Composer

| Bloque | Campos | Límites respetados |
|---|---|---|
| `schema` | literal `dark-director/1` | E102 |
| `meta` | title, notes | E109 |
| `direction` | identity, accessibility | catálogos de 3+3 |
| `global` | bpm (20–300), seed (int ≥ 0) | E105 |
| `harmony` | key, language, resolution, harmonic_rhythm_bars (1–8), progressions | E103/E105/E107/E113 |
| `instruments` | enabled, register, density, mix, type (solo bass) | E110/E105 |
| `structure[]` | id, type (7), bars (≥1), energy/tension/density (0–1), focus (≤3), active, drums (escalera 5), chords, chord_bars (1–8), resolution, final, loop_bars (1–32) | E105/E106/E110 |
| `ending` | fade_out {enabled, bars, exponent}, tape_stop {enabled, bars, semitones} | E112 |
| `qa` | strict, guardrails (los 8 reales) | E109 |

Composer **nunca** escribe: `development.*` (frases/motifs/improvisación son
libertad del motor; regla 10: no generador nota por nota), `x_*` (no necesita
extensiones), ni ningún campo que el validador no admita.

## Claves de `harmony.progressions`

El validador acepta **id de sección** o **tipo funcional** (E107). Composer usa
ids (precedencia máxima §2.8 tras `section.chords`), de modo que dos secciones
del mismo tipo pueden llevar progresiones distintas.

## Gramática de acordes

Todos los símbolos que Composer emite son parseables por
`forge/theory.parse_chord` (la misma que aplica E113) — verificado por el test
C12 con 7 familias tonales. Ortografía: plana con bemoles, idéntica a
`_NOMBRES_NOTA` del compilador y a `FLAT_NAMES` de Forge (bVI → Ab, #iv° → Gbdim).

## Armonía F7 (biblioteca de familiaridad)

* Es **opcional siempre** (regla 6). Composer no la aplica por defecto.
* Se elige al generar (en Studio, campo `--harmony`), no en el documento:
  el doc nunca contiene keywords F7 (test A6).
* La lista de keywords mostrada por la UI viene de la introspección en vivo de
  `jazz_engine.harmony_library`.

## Perfiles de producción

Los 7 perfiles reales (`original, sax, sax_rhodes, drums, sax_vibes, full,
atmospheric`) se leen del manifiesto. Viajan en el PROYECTO de Composer (para
recordar cómo generar en Studio), **no** en el doc del contrato.

## Detección de discrepancias

`composer_data/dmd_manifest.json` guarda el fingerprint del DMD introspeccionado
(contract/rev/compiler/jazz_engine + recetas + catálogos). Si el DMD del usuario
cambia (otra rev, otra receta), la UI marca la discrepancia y
`POST /api/integration/refresh` recalcula. Mientras el fingerprint no coincida,
Composer advierte antes de generar. Sin DMD descubierto, funciona con la
instantánea incluida (`manifests/dmd_manifest_builtin.json`) pero SIN validación
en vivo (se marca con honestidad; test A8 verifica que la instantánea coincide
con el vivo cuando existe).

## DMD Studio

Los documentos se importan en Studio con su editor JSON avanzado (pegar doc.json
y guardar el proyecto) y se compilan con la vista GENERATION (perfil + seed).
Composer no escribe en `studio_data/` ni en ninguna carpeta de DMD/Studio
(test F6: hashes de 10 archivos protegidos antes/después de la batería completa).

## Ruta de producción MIDI (PLANIFICADA v1.2 — no implementada)

Composer consumirá el mismo pipeline que Studio y el modo álbum de DMD, por el
puente subprocess aislado (patrón ya probado por tests F4/F5 y por
`studio/runner.py`):

| Elemento | Valor exacto |
|---|---|
| Función reutilizada | `scripts/produce.py::producir_cancion(doc, *, production="full", seed=None, harmony=None, out_dir, verify=None, indice=True)` |
| Cadena interna | `dark_director.compilador.compilar` → `jazz_engine.render.generate` → `forge.validate` → bytes MIDI |
| Artefactos que escribe en `out_dir` | `doc.json` · `config_efectiva.json` · `<out.name>.mid` · `evidencia.json` (con `sha256_midi`, duración, compliance, orden de regeneración `--verify`) |
| Determinismo | mismo doc + misma seed → MIDI byte a byte idéntico; SHA256 registrado en `evidencia.json` y en el bloque `midi` del manifest de Composer |
| events.json (reproducción) | Opción A: parámetro aditivo `events=False` en `producir_cancion` que persistiría `forge.engine.to_events(res)` — **requiere autorización explícita (D26); NO implementado** |
| Audio | NO cambia: Composer sigue sin renderizar audio; el convertidor MIDI→audio del usuario permanece externo (D22) |

Los 7 perfiles de producción (`original, sax, sax_rhodes, drums, sax_vibes,
full, atmospheric`) seguirán viniendo del manifiesto introspeccionado; con la
Fase 1 pasarán de ser una instrucción pendiente a un perfil REALMENTE aplicado,
con `midi_sha256` como evidencia. Las keywords F7 siguen sin viajar nunca en el
doc (test A6) y siguen siendo opcionales en la ruta de producción
(`harmony=None` por defecto).
