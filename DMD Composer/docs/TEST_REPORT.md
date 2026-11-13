# TEST REPORT — DMD COMPOSER v1.2 (misión de integración MIDI)

Fecha: 2026-11-11 · Plataforma sandbox: Linux, Python 3.12.16 ·
Destino real: Windows 10, Python 3.12.1, venv de Composer.
Todas las pruebas se ejecutaron contra el núcleo de producción REAL
(`scripts/produce.py::producir_cancion`) y el orquestador de álbumes REAL
(`album/orquestador.py`), vía subprocess aislado. Nada se simuló.

## 1. Resumen de baterías

| Batería | Alcance | Resultado |
|---|---|---|
| A–I (regresión v1.1, 114 tests) | contrato, estructura, armonía, randomizador, song map, integración, álbum (docs), seguridad, QA | **114/114 OK** |
| J (`tests/test_j_produccion.py`, 10 tests) | producción MIDI individual: E2E, idempotencia, determinismo, igualdad con núcleo directo, fallos honestos, traversal/whitelist, jobs, integridad, CLI intacto, sin audio | **10/10 OK** |
| K (`tests/test_k_album_produccion.py`, 4 tests) | álbum: materialización dmd-album/1, lote del orquestador real, descarga+SHA por pista, reanudación sin regenerar, --regen por pista, cancelación, events verificados, sin generador paralelo | **4/4 OK** |
| Forge legacy (`tests/test_forge.py`) | motor MIDI Forge intacto | **36 OK** (2 skips de entorno, preexistentes) |
| Núcleo events (`tests/test_produce_events.py` en el DMD) | Opción A: MIDI byte-idéntico con/sin events; CLI intacto | **4/4 OK** |
| **TOTAL Composer** | | **128/128 OK** |

Comando: `cd DMD_Composer && python -m unittest discover -s tests -v`
(DMD: `python -m unittest tests.test_produce_events tests.test_forge`)

## 2. E2E checklist (roadmap §5, Fase 4)

| # | Verificación | Evidencia |
|---|---|---|
| 1 | Composición → JSON musical → validación real | compose 200, validador real por puente (batería I) |
| 2 | Generación MIDI desde la UI/API (puente aislado) | POST midi 202 → poll → `ok`; hijo aislado `dmd_bridge_runner` |
| 3 | `.mid` válido (no JSON renombrado) | cabecera `MThd`, 16.579 bytes |
| 4 | Descarga por Composer | GET download 200, bytes == archivo en disco |
| 5 | SHA256 triple | `sha256(descarga) == bloque manifest == evidencia.json` (1a8531b0… para el doc de prueba) |
| 6 | Igualdad con el núcleo directo (sin segundo generador) | `producir_cancion` directo con el perfil declarado → MISMO sha |
| 7 | Determinismo (mismo input + seed) | cross-gen byte-idéntico; baseline histórico 32199acc… reproducida |
| 8 | Semilla distinta → resultado distinto | seed 777 → sha distinto (7d505484…) |
| 9 | Errores sin estados falsos | doc/almacenamiento dañado → `error`, sin bloque midi, descarga 4xx |
| 10 | Integridad vigilada | MIDI truncado → `integridad_error` + 409 (nunca éxito) |
| 11 | Path traversal / whitelist | `..%2F` → 4xx; artefactos fuera de whitelist → 400; rutas solo del servidor |
| 12 | Cancelación y recuperación | jobs: JobBusy 409, cancel → `cancelado`, `recover_interrupted` → `interrumpido`; álbum cancelado conserva pistas hechas |
| 13 | Álbum: lote 13-pistas (probado con 2/3) | orquestador real: 2/2 y 3 pistas; `estado.json` crash-safe; plan+informe reales |
| 14 | Reanudación sin regenerar válidas | mtimes de .mid intactos tras re-ejecutar |
| 15 | Regeneración por pista | `--regen track01`: solo esa pista cambia |
| 16 | Reproducción WebAudio | events.json por gen y por pista (verificado contra SHA); ciclo de vida Player (copiado literal); **audio audible: W1 pendiente en la máquina Windows del usuario** |
| 17 | Sin conversión de audio (D22) | barrido automatizado: 0 endpoints/código de WAV/MP3/FluidSynth/sfizz/soundfonts |
| 18 | Protegidos intactos | F6 en verde (hashes de 10 archivos protegidos) |

## 3. Bugs encontrados y corregidos durante la validación

1. `server.py` usaba `hashlib`/`random` sin importarlos (P0 del backlog §9)
   — corregido.
2. `jobs.list()` tapaba el builtin `list` → RecursionError; renombrado a
   `list_jobs()`.
3. Worker de producción usaba acceso por atributo sobre ctx dict → error;
   corregido a acceso por clave.
4. Colisión de layout: el `--out` del orquestador de álbum pisaba el
   plan.json de Composer → producción movida a `produccion/` separada.
5. Patrón de nombre del `.mid` del orquestador (`NN_<id>.mid`, no `<id>.mid`)
   — lectura de `estado.json`/`carpeta` real.
6. `delete_project` durante una producción activa (rmtree vs hijo) → ahora
   409 mientras haya un job activo de ese pid.
7. Semilla de álbum derivada con `hash()` (no determinista entre procesos) →
   sha256(album_id); nombre de álbum normalizado a la regex A103.
8. `shell=True` en docstring disparaba la batería H de seguridad → redacción.

## 4. Limitaciones conocidas / verificación pendiente en Windows (W1–W5)

* **W1** (única pendiente de audio): confirmación audible del Player en el
  navegador del usuario (el sandbox no tiene audio).
* W2–W5 (recomendado en la máquina real): una llamada produce desde el venv
  comparando SHA con Studio; sin `.pyc` nuevos en `forge/`; reanudación tras
  kill; `forge.audio.status()` (entorno, no Composer).
* Los eventos de pista de álbum se generan bajo demanda (primera escucha,
  ~segundos) y quedan en caché verificados.

## 5. Cómo ejecutar

Windows (venv de Composer):
```bat
cd DMD_Composer
.venv\Scripts\python -m unittest discover -s tests -v
scripts\start.bat          % Composer en http://127.0.0.1:8898
```
DMD (raíz del repositorio):
```
python -m unittest tests.test_produce_events tests.test_forge -v
```
