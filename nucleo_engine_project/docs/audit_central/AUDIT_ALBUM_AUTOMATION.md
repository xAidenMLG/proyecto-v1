# AUDIT_ALBUM_AUTOMATION — Orquestador de álbumes DMD e integración con Composer

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11 · Evidencia VERIFIED (código + álbum demo «Noches Largas» + CLI), salvo marcas.

---

## 1. El esquema REAL `dmd-album/1` (album/esquema.py) — VERIFIED

**Raíz** (`_CLAVES_RAIZ` :43-44; MAX_PISTAS=99 :51):
- `schema`="dmd-album/1" (req, A102) · `album` str `^[A-Za-z0-9][A-Za-z0-9 _-]{0,79}$` (req, A103) · `identidad` default "dark_triphop", único admitido (A104) · `semilla_album` int≥0 no-bool (req, A105) · `objetivo.pistas` opt (mismatch → W-A1) · `curva_energia` list[float 0–1] len==nº pistas (A107) · `restricciones` opt: `perfil_frac_max` 0–1 (def 0.4), `respiro_cada` ≥2 (def 5), `prohibir_consecutivos_iguales` bool (def true) · `pistas` list 1–99 (req, A106). Claves desconocidas → A109. Errores acumulados → `AlbumInvalido.errores`. Carga: A114 (no existe), A115 (JSON/UTF-8).
- **Pista** (:45): `id` req `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` único (A110) · `doc` req no-vacío + `.json` (A111), relativo al album.json o absoluto · `titulo`/`rol` (≤60) opt · `perfil` opt ∈ 7 perfiles (A112) · `seed` opt int≥0 · `harmony` opt dict `{keyword|id|progressions, variacion, seed}` — **prohibido con perfil `original`** (A113), validado contra `harmony_library.por_id`.
- Códigos: A101–A115 esquema · A201 doc no existe · A202 JSON · A203 schema≠dark-director/1 · A204 identidad doc≠álbum · A205 no compila/strict (planificador :168-225) · W-A4…W-A8 avisos. ⚠ «W-A9» aparece solo en docs, no existe en código.

## 2. Ciclo de vida de una pista (orquestador.py:36-40,142-208) — VERIFIED

Estados: `ok | fallo | pendiente(razon: cambio_especificacion|error_plan) | no_ejecutada` (implícito: sin registro).

```
ausente → ok|fallo            (al producir; intentos+1)
ausente → fallo(error_plan)   (doc roto detectado en planificación — F8-5: no aborta el álbum)
ok → ok SALTADA               (misma especificación; mtime intacto)
ok → pendiente                (drift: cambian sha256_doc/perfil/seed/harmony; el resultado aceptado se PRESERVA esa corrida — F8-6)
ok → ok (--regen/--forzar)    (regeneración explícita)
fallo|pendiente|ausente → se produce   (reintento automático en la siguiente corrida)
```
⚠ Matiz VERIFIED: `pendiente` NO bloquea para siempre — en la siguiente corrida sin `--regen` se regenera igual (:158 falla porque estado≠ok → :176 produce). `estado.json` se escribe **tras cada pista** (crash-friendly :207-208) pero **sin escritura atómica** (:57-60).

## 3. Mecanismos clave — VERIFIED

| Mecanismo | Detalle | Evidencia |
|---|---|---|
| Llamada a producción | **In-process** (`import produce` insertando `scripts/` en sys.path) → `producir_cancion(doc, production, seed, harmony, out_dir=NN_<id>, indice=False)` | orquestador.py:125-128,183-186 |
| Planificación | `planificador.planificar(spec, raiz)` SIEMPRE se re-ejecuta al producir (reescribe plan.json, idempotente); compila en seco cada doc ANTES de producir (A2xx); semillas derivadas `semilla_album+101*(i+1)` (demo ✓ 3504/3706/…); asignación greedy de perfiles (no consecutivos, respiro, menor uso; lo explícito SIEMPRE gana → solo W-A4); `sha256_doc` = hash **CANÓNICO** `json.dumps(sort_keys)` (:41-42,239) | planificador.py |
| Diversidad | PRE sobre docs (exceso perfil, ventanas respiro, consecutivos, tonalidades pegadas, BPM 76–92, curva energía) + POST sobre MIDIs (duplicados SHA256; huellas rol+paso16avos+altura, Jaccard ≥0.85) — todo aviso, nunca bloquea. Demo: 78 pares, 0 duplicados | diversidad.py, produce.py:49-67 |
| Informe/manifiesto | config_efectiva por pista, hashes doc/MIDI, comandos `produce.py … --verify <sha>` | informe.py:117-157 |
| CLI (VERIFIED por `--help`) | `plan | producir(--out,--regen,--solo,--forzar,--sin-informe) | informe | estado`; `album plan` exit 1 si hay errores de documentos | __main__.py:80-86 |
| Demo real | 13/13 ok, ~27,8 min, intentos 2 (corrida + re-verificación determinismo); sin fallo real registrado (solo tests) | output/albumes/noches_largas/ |
| Timeouts/paralelismo | **Ninguno** — secuencial en orden del spec | orquestador.py:138-208 |

## 4. El «album planner» de DMD Composer HOY (VERIFIED en código, sin ejecutar)

`DMD_Composer/composer/albums.py`:
- Plan en `output/albumes/<album_id>/plan.json` con **`"formato": "dmd-album/1"` (:58) — colisión de nombre, estructura distinta** (raíz `compartido{identity,mood,harmony_mode,instruments,diversidad,estructura,_secciones,_harmonias}` + `pistas[{n,estado pendiente|lista,seed,key,bpm,language,plantilla,gen,pid,doc_sha256}]`).
- `prepare_track` determinista de `(album_id, n, creado)` asigna seed/key/language/groove/bpm/plantilla + huella `{key,plantilla,language,bpm,groove}` anti-duplicados compositivos (:146-190).
- `generate_all` reanudable (recarga el plan por pista, :292-300), compone vía `engine.compose` con validador/compilador REALES por subprocess, persiste `output/<pid>/gen_NNNN/doc.json` (gens jamás sobrescritas, store.py:179-194) y guarda `{pid, gen, doc_sha256}` por pista (:303-306).
- Informe de diversidad con distancias en círculo de quintas (con bemoles corregidos, :244-272).
- **Lo que NO es**: no produce MIDI, no exporta un spec `dmd-album/1` consumible (su plan no pasa `validar_album`), sin perfil/seed/harmony de producción por pista (solo «instrucción pendiente»), sin estado/resume de producción, sin manifiesto de reproducibilidad, sin diversidad POST sobre MIDIs. `generate_all` es **una petición HTTP síncrona secuencial** (sin job asíncrono ni progreso).

## 5. Separación de responsabilidades (respuesta a la misión §3.F)

| Capa | Responsabilidad | NO debe |
|---|---|---|
| **Composer** | Dirección musical: docs `dark-director/1`, diversidad compositiva, y **exportar** un `album.json` REAL (esquema §1) apuntando a sus generaciones elegidas + estados compositivos | No duplica orquestador, no produce MIDI |
| **Orquestador DMD (`album/`)** | Validar spec, planificar (semillas/perfiles greedly), producir batch vía `producir_cancion`, estado/resume/drift, diversidad POST, informe/manifiesto | No compone ni modifica docs fuente |
| **Renderer (forge/audio + capa futura)** | WAV/MP3/stems desde los MIDI | No toca el MIDI fuente |
| **Project Library** | Almacenar/recuperar álbumes, historial, hashes, estados | No decide nada musical |

## 6. Respuestas directas (1–12)

1. **Composer**: componer docs + diversidad compositiva + exportar spec de producción.
2. **Orquestador DMD**: validar/planificar/producir batch + estado + resume + informe.
3. **Entrega**: un `album.json` dmd-album/1 con `pistas[].doc` → rutas a los docs ya generados (+ perfil/seed/harmony opcionales por pista).
4. **¿Consume docs pre-generados sin replanificar?** SÍ en la práctica: el orquestador nunca genera docs, los lee/copia a `NN_<id>`; el plan se recalcula siempre (idempotente) pero **no regenera los docs de Composer**. Importar un plan externo sin replanificar: NO existe mecanismo (no hackear; sería un cambio en `album/` → tarea aparte con autorización).
5. **Individual: SÍ** (`--solo`, test :337-345).
6. **Álbum completo: SÍ** (demo 13/13).
7. **Diversidad de Composer**: la musical viaja dentro del doc y jamás se altera (solo se audita); la de producción se conserva si Composer fija perfil/seed/harmony en el spec; los huecos los decide el greedy determinista del orquestador; las huellas compositivas de Composer no son importables (distinto criterio: círculo de quintas vs huellas técnicas).
8. **No-sobrescritura**: nunca escribe el doc origen; firma `especificacion{sha256_doc canónico, perfil, seed, harmony}` → drift → `pendiente` preservando el MIDI aceptado (F8-6, test :347-369).
9. **Fallo de pista**: aislado (error+traceback+exit 1), continúa el resto, reintento automático.
10. **Resume**: `estado.json` tras cada pista; salta `ok` con misma especificación (test :297-308).
11. **Contrato de integración propuesto** (§7).
12. **Riesgos** (§8).

## 7. Contrato de integración Composer → orquestador (propuesta concreta)

1. Composer genera/completa el álbum compositivo (plan interno, estados `lista` con `{pid, gen, doc_sha256}`).
2. Al «producir álbum», Composer **exporta**: `DMD_Library/Albums/<slug>/album.json` con el esquema REAL (pistas: `id` = `NN_slug`, `doc` = ruta ABSOLUTA o espejo `docs/NN_slug.json`, `perfil`/`seed`/`harmony` desde la instrucción de producción de cada pista) + **espejo `docs/`** de las generaciones elegidas (evita A201 si el usuario borra/renombra el proyecto después).
3. Composer lanza **subproceso** `python -m album producir <album.json> --out DMD_Library/Albums/<slug>` con CWD=raíz DMD, rutas absolutas, timeout del llamador, y le la salida estructurada (`estado.json`/`informe_album.json`/`manifiesto.json` + exit code).
4. Estados de pista reflejados en la UI: `ok→MIDI_READY`, `fallo→MIDI_FAILED(error)`, `pendiente→PENDING_DRIFT`.
5. Las semillas de **composición** (doc.global.seed) y de **producción** (`seed` del spec) son distintas y válidas a la vez — documentarlas por separado en el manifest.

## 8. Riesgos de integración y mitigaciones

| # | Riesgo | Severidad | Mitigación |
|---|---|---|---|
| 1 | **Colisión de nombre** `dmd-album/1` (plan interno Composer ≠ esquema real) | ALTA | El export crea un documento NUEVO con el esquema real; nunca se envía el plan interno. Renombrar a futuro el label interno (`dmd-composer-album-plan/1`) — requiere tocar Composer (autorizado en su repo) |
| 2 | Dos semánticas de hash: Composer guarda `doc_sha256` de **fichero** en su plan vs canónico `sort_keys` del orquestador | ALTA | El export debe calcular el hash canónico (o usar `generation_manifest.doc_sha256`, que sí coincide — engine.py:307) |
| 3 | Rutas relativas persistidas (dependencia de CWD) | MEDIA | Rutas absolutas en el export + espejo docs/ |
| 4 | `estado.json`/`huellas.json`/`plan.json` **sin escritura atómica** | ALTA (escenario nº1 de fallo) | Fix: tmp+`os.replace` (+`.bak`) en orquestador.py:57-60,210 y planificador.py:318-324 |
| 5 | Sin timeouts por pista ni locks | MEDIA | Watchdog ~900 s/pista en el llamador (Composer) + single-flight |
| 6 | `pendiente` regenera en la siguiente corrida sin `--regen` (matiz) | MEDIA (comportamiento) | Documentarlo y hacer que Composer muestre la razón; cambio de semántica solo con autorización |
| 7 | Dos medidas tonales distintas (círculo de quintas Composer vs PRE del planificador) | BAJA | Conviven; el informe las separa |
| 8 | `python3` vs `python` en Windows | BAJA | El export usa `sys.executable` |

## 9. Veredicto

**No duplicar el orquestador**: `album/` ya resuelve exactamente lo que la misión pide para batch (plan determinista, aislamiento de fallos, resume, diversidad, informe, reproducibilidad con `--verify`). La integración correcta es **Composer como productor de specs**, orquestador como ejecutor — con los 4 fixes de robustez de §8 como prerrequisito (Fase 0).
