# AUDIT_PRODUCTION_PIPELINE — Análisis del pipeline de producción real

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11.
> Todas las ejecuciones citadas se realizaron en sandbox con salidas en `/tmp/audit_b/` (cero escrituras en el repo salvo `.pyc` del intérprete, documentado como R5).

---

## 1. Reconstrucción del flujo real (doc.json → MIDI)

```
doc.json (dark-director/1 rev 3.2)
  ├─ A) CLI producción:  python3 scripts/produce.py DOC.json --production PERFIL --seed N --out CARPETA [--verify SHA] [--harmony K --harmony-variacion V]
  │      └─ producir_cancion(doc, *, production, seed, harmony, out_dir, verify, indice=True)   [produce.py:70-71]
  │           ├─ compilador.compilar(doc) → proyecto midi-forge/1 (validación E1xx/E2xx)        [produce.py:92]
  │           ├─ je.render.generate(proj, {production, seed[, harmony]})                        [produce.py:95-98]
  │           │     ├─ production="original" → forge.adapter.normalize + forge.engine.generate  [render.py:37-62]
  │           │     └─ resto → enhance(sax/drums/vibes) → normalize → hooks rhodes/vibes        [render.py:64-148]
  │           ├─ forge.validate.validate(res) + sha256                                          [produce.py:99-100]
  │           └─ 4 artefactos en out_dir (doc.json, config_efectiva.json, <carpeta>.mid, evidencia.json)
  ├─ B) Motor directo:   python3 -m jazz_engine DOC.json --dark-director --production P --seed S -o out.mid   [jazz_engine/__main__.py:33-112]
  └─ C) Studio:          POST /api/projects/{pid}/generate → jobs.start_job() → Popen([python, "-m", "studio.runner", "--spec", job_spec.json], cwd=ROOT) → runner importa produce.py y llama producir_cancion(..., indice=False)   [studio/jobs.py:265-299; studio/runner.py:30-71]
```

## 2. Contrato exacto de `producir_cancion` (VERIFIED, produce.py:70-174)

| Elemento | Detalle |
|---|---|
| Entrada | `doc` (dict dark-director/1 ya cargado), `production` ∈ {original, sax, sax_rhodes, drums, sax_vibes, full, atmospheric} (default `full`), `seed` (default `global.seed` del doc), `harmony` (dict keyword/id/variacion/seed — **prohibido con `original`**), `out_dir`, `verify` (sha256 esperado), `indice` (bool) |
| Pre-chequeos | Validación **antes** de `mkdir` → en fallo **0 artefactos parciales** (comprobado: TEST04) |
| Artefactos | `doc.json` (copia), `config_efectiva.json` (config normalizada real), `<out.name>.mid` (⚠ el MIDI se llama **como la carpeta**), `evidencia.json` (sha midi+doc, versiones, bpm/compases/duración, notas por pista, compliance, actividad de motores, comando `regenerar` literal, hint `fluidsynth_windows`) |
| `verify` ≠ None | **Cero escrituras**: solo compara SHA y devuelve `{ok, sha256, ...}` (produce.py:102-104) — verificado TEST03/TEST03b/TEST10 |
| Efectos laterales | CLI: `INDICE.md` en `out_dir.parent` (produce.py:157-170; Studio lo evita con `indice=False`). Intérprete: `.pyc` salvo `PYTHONDONTWRITEBYTECODE`. **Nada más**: no toca `output/`, `studio_data/`, red ni lanza subprocesos |
| Códigos de retorno CLI | 0 ok · 1 (verify-mismatch, DirectorInvalido, traceback) · 2 (argparse) (produce.py:222-230) |
| Determinismo | mismo (doc, config) → bytes idénticos; TEST02/06/07/09/10 lo reprodujeron |

## 3. Comandos verificados (tabla completa de ejecuciones reales)

Entrada principal: `output/albumes/noches_largas/12_marea_baja/doc.json` (2.340 B, seed 8107).

| # | Prueba | rc | Resultado clave |
|---|---|---|---|
| TEST01 | `python3 .../scripts/produce.py /tmp/audit_b/test01/doc.json --production full --seed 8107 --out /tmp/audit_b/test01/out01` | 0 | **0,174 s, pico 22,3 MiB**; MIDI `out01.mid` 7.645 B, sha256 `873e19fb8602d42860a15255b3f7ccd7193e9f63fa56f6c6abb5fd86008e10f5`; lateral `INDICE.md` |
| TEST02 | idem desde `cwd=/` | 0 | `cmp` → **byte-idéntico** → determinismo VERIFIED |
| TEST03 | idem + `--verify 873e19fb…` | 0 | `VERIFICACION: OK`; carpeta `out03` **no creada** |
| TEST03b | `--verify deadbeef…` | 1 | `VERIFICACION: FALLO` (limpio) |
| TEST04 | doc mutado `bpm:500` | 1 | `DirectorInvalido: … E105: bpm fuera de 20–300: 500`; **sin artefactos** |
| TEST04b/c | JSON truncado / perfil inválido | 1 / 2 | `JSONDecodeError` / argparse `invalid choice` |
| TEST05 | `--production original --seed 8107` | 0 | camino ORIGINAL OK, sha `85764883…` |
| TEST06 | `python3 -m jazz_engine doc.json --dark-director --production full --seed 8107 -o out06_cli.mid` | 0 | **sha `873e19fb…` idéntico a produce.py** |
| TEST07 | runner headless de Studio con job_spec en /tmp | 0 | `## RESULT OK`; `gen_0001/_result.json` con huella FASE 8; MIDI mismo sha |
| TEST08 | `--harmony dark_cinematic --harmony-variacion medium` | 0 | sha `77d5e536…` (F7 opcional VERIFIED) |
| TEST09 | rutas relativas desde /tmp | 0 | mismo sha (resueltas contra CWD) |
| TEST10 | doc histórico `demo_medianoche` + `--seed 3113 --verify 32199acc…` | 0 | **el artefacto histórico reproduce byte a byte** (mecanismo real de reproducibilidad = sha256 + `--verify`) |
| TEST11 | copia del árbol sin flag de bytecode | 0 | 34 `.pyc` creados (7 en `forge/`) → gap R5 |

## 4. Comportamiento en fallo (VERIFIED)

- Validación de contrato falla → excepción `DirectorInvalido` con códigos literales (E1xx/E2xx), rc 1, **sin crear carpeta** (TEST04).
- `StrictBloqueante` solo con `qa.strict` (E301–E303 omitidos sin él) — `compilador.py:221-235`.
- Studio: `_result.json {ok:false, error, traceback}` + job en `error`; timeout duro **900 s** con kill; segunda generación concurrente → **409**; `recover_interrupted()` al arrancar marca `interrupted` (`jobs.py:25,55-67,220-321`).
- Cancelación Studio: `cancel_job → terminate` (`jobs.py:303-321`). CLI: solo kill del SO.

## 5. Studio como caso de estudio del runner (aplicable a Composer)

| Aspecto | Implementación actual | Lección para el Production Bridge de Composer |
|---|---|---|
| Aislamiento | subproceso `python -m studio.runner --spec` con `cwd=ROOT` | Replicar (patrón ya probado) |
| Spec | `{doc, production, seed, harmony, wav, soundfont, indice, out_dir}` | Añadir `verify`/`out_name` explícito (evita R2) |
| Concurrencia | 1 job activo; 2ª petición → 409 | Mantener single-flight para MIDI; cola innecesaria |
| Timeout | 900 s fijo | Parametrizar; añadir watchdog por pista en álbumes |
| ⚠ Env | `{PYTHONIOENCODING, PYTHONUTF8}` **sin heredar `os.environ`** (`jobs.py:265-270`) → sin `PATH` el hijo no encuentra FluidSynth por `shutil.which`; sin `SystemRoot` puede romper sockets/DNS de Windows | **Fix P0-2**: `env={**os.environ, ...}`; añadir `PYTHONDONTWRITEBYTECODE=1` |
| Persistencia | job JSON en `studio_data/jobs/`, `_result.json` en `out_dir.parent` | OK para Composer con su propio almacén |

## 6. Windows (lo que se ejecutará en la máquina del usuario)

- `scripts/windows/install_studio.bat` → `check_studio.bat` → `start_studio.bat`; venv independiente `.venv-studio`; servidor solo en `127.0.0.1:8899`; deps: fastapi/uvicorn. Los motores son 100 % stdlib (VERIFIED leyendo los .bat).
- WAV: `forge/audio.py` busca FluidSynth en `MIDI_FORGE_FLUIDSYNTH` → PATH → `ROOT/tools/` → `C:/tools/fluidsynth/bin` → `C:/Program Files/FluidSynth/bin` (audio.py:16-25) — coincide con la instalación real del usuario.
- Los .bat del usuario: NOT AVAILABLE en sandbox (leídos sus equivalentes del repo).

## 7. Riesgos identificados en el pipeline

| ID | Riesgo | Evidencia | Mitigación propuesta |
|---|---|---|---|
| R1 | `INDICE.md` escapa de `out_dir` (escribe en el padre) | produce.py:157-170 | Llamar siempre con `indice=False` desde bridges (Studio ya lo hace) |
| R2 | Nombre del MIDI = nombre de la carpeta | produce.py:112 | El bridge elige `out_dir` con slug controlado (id de pista) |
| R4 | Env del hijo sin PATH/SystemRoot (rompe WAV y utilidades) | jobs.py:265-270 | Heredar `os.environ` + overrides |
| R5 | `.pyc` de `forge/` se escriben fuera del modo sin-bytecode (`forge_link` importa con bytecode activo) | jazz_engine/__init__.py:36 + forge_link.py:112-140 (TEST11: 34 .pyc) | `PYTHONDONTWRITEBYTECODE=1` en todos los hijos; evaluar `sys.dont_write_bytecode` en forge_link (requiere autorización: toca zona sensible) |
| R6 | Timeout 900 s fijo en Studio; orquestador de álbumes **sin timeout por pista** | jobs.py:25; orquestador.py:138-208 | Watchdog parametrizable ~900 s/pista |
| R7 | `evidencia.json` registra versión de engine que puede divergir sin cambiar bytes | produce.py:123-126 | La reproducibilidad real es sha256 + `--verify` (documentado; no ocultar) |

## 8. Contrato recomendado para el «Production Bridge» de Composer

- **Entrada**: `{doc (dark-director/1), production (7 perfiles, default full), seed (int≥0, default global.seed), harmony?, out_dir (absoluto, único), indice:false, verify?}`.
- **Salida estructurada**: `{ok, sha256, out_dir, midi, evidencia, perfil, seed, bpm, compases, duracion_s, compliance_fails/warns, harmonia, huella}` + 4 ficheros en disco.
- **Errores mapeados**: `DirectorInvalido` → 422 (códigos E1xx/E2xx literales) · `StrictBloqueante` → 422 E3xx · perfil/override inválido → 400 · JSON/fichero → 400/404 · verify → rc 1 con sha real vs esperado · timeout → 504 · cancelación → 499 · segunda concurrente → 409.
- **Garantías**: determinismo byte-idéntico (doc+seed), `--verify` sin efectos, evidencia con comando `regenerar` literal, `out_dir` nuevo por intento.

## 9. Respuestas directas a la misión (§3.B, 1–13)

1. Comando exacto: ver §1-A/B/C (los tres VERIFIED con salida real).
2. Argumentos: ver §2 (tabla de entrada).
3. Consume/genera: consume 1 fichero (`doc.json`); genera 4 artefactos (+INDICE lateral en CLI, +job files en Studio, +`.pyc`).
4. Condiciones previas: doc válido rev 3.2, perfil ∈ 7, escritura en out_dir (y padre para CLI), Python ≥3.12 stdlib; WAV requiere FluidSynth+sf2.
5. Al fallar: rc 1 con mensaje real, **0 artefactos parciales**; Studio: job `error` + traceback.
6. Sin Studio: **SÍ** (TEST01/06/07).
7. Desde cualquier directorio: **SÍ** (TEST02/09); los `-m` requieren CWD=ROOT o PYTHONPATH.
8. Env global: ninguna obligatoria para MIDI; opcionales `DARK_DIRECTOR_FORGE_ROOT`, `MIDI_FORGE_FLUIDSYNTH|SF2|FFMPEG|LAME`.
9. Canción independiente: **SÍ** (autocontenida, deepcopy, determinista).
10. Batch: un proceso por canción (Studio) o bucle secuencial in-process (álbum); ambos VERIFIED.
11. Cancelación/recuperación: Studio sí (terminate + recover_interrupted); CLI nada propio; álbum: resume por `estado.json`.
12. Composer debe controlar: exclusión mutua, ciclo de vida/timeout, slugs únicos de out_dir, semillas, validación previa, sha+`--verify`, archivado, reintentos, provisión de FluidSynth si quiere WAV.
13. Efectos laterales completos: 4 ficheros en out_dir + INDICE (si indice) + .pyc; nada más.
