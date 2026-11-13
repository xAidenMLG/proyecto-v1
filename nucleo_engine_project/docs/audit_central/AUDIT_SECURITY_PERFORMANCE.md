# AUDIT_SECURITY_PERFORMANCE — Seguridad, estabilidad y rendimiento

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11 · Hardware objetivo: Ryzen 7 3700X, 16 GB DDR4, RX 580, Windows 10, Python 3.12 · Prioridad: estabilidad local, RAM razonable, sin optimización prematura.
> Auditoría estática + suites de tests existentes ejecutadas (13 studio ✓, 171 dmd ✓, seguridad 15 ✓, álbum+contrato 15 ✓). Cero cambios en el repo.

---

## A. Subprocesos y ejecución

| Hallazgo | Evidencia | Clasificación | Severidad |
|---|---|---|---|
| Todos los lanzamientos usan argv-lista, `shell=False`, con timeouts (60/120 bridge Composer; 300/600/900 audio/Studio) | `composer/bridge.py:57-85`, `studio/jobs.py`, `forge/audio.py:79` | VERIFIED | OK |
| ⚠ El runner hijo de Studio arranca con **entorno mínimo** (`{PYTHONIOENCODING,PYTHONUTF8}` sin `os.environ`): sin `PATH`/`SystemRoot` → `shutil.which('fluidsynth')` falla en Windows; riesgo de hijo degradado | `studio/jobs.py:265-270` + `forge/audio.py:17`; 8 jobs `wav=true` fallidos reales | VERIFIED (lógica) + evidencia | **Alta** (P0-2) |
| ⚠ `composer/bridge.py:72-78` pasa texto por tubería **sin `encoding`** → cp1252 en Windows con rutas/acentos («Composición») | código | VERIFIED | Baja (ya ocurrió un caso DS-O4) |
| Sin `shell=True`, sin `os.system`, sin `eval/exec` en las tres aplicaciones | grep exhaustivo | VERIFIED | OK |
| Huérfanos: Studio hace `terminate`/`kill` en cancel y timeout; el orquestador de álbumes **no** tiene timeout por pista (hijo in-process no cancelable por pistas) | `jobs.py:303-321`; `orquestador.py:138-208` | PARTIALLY VERIFIED | Media |

## B. Validación de entradas y rutas

| Hallazgo | Evidencia | Severidad |
|---|---|---|
| DS-8 CUMPLE en Studio: bind 127.0.0.1, ids por patrón estricto, todo bajo `studio_data/`, sin comandos del cliente, JSON solo `json.loads` | `studio/__main__.py:31`, `projects.py`, tests de traversal | OK |
| Composer: límites de tamaño (512 KB JSON de proyecto / 8 MB), regex de ids anti-traversal, generaciones `mkdir(exist_ok=False)`, escritura atómica | `store.py:32-35,66-78,179-194`, tests H1-H15 (15 ✓) | OK |
| ⚠ Studio **sin límite de tamaño de cuerpo** (doc gigante → RAM/job_spec en disco) | grep 0 resultados de límites en `studio/server.py` | Media |
| ⚠ `delete_project` de Studio no tolera ficheros bloqueados (reproductor/AV) → 500 crudo | `studio/projects.py:187-192` + `server.py:184-192` | Media |
| ⚠ Composer: pid `"albumes"` pasaría `_PID_RE` y `delete_project` borraría `OUTPUT_DIR/albumes` (los planes de álbum) | `store.py:32,165-174`; `albums.py:30` | Media (edge case, no ejecutado para no destruir datos) |

## C. Estabilidad y recuperación

| Hallazgo | Evidencia | Severidad |
|---|---|---|
| Escrituras atómicas en Composer (proyectos) y Studio (jobs/settings) | tests ✓ | OK |
| ⚠ **`estado.json`/`huellas.json`/`plan.json` del orquestador SIN atomicidad** → corte a mitad de álbum trunca el estado → `_cargar_estado` reinicia a vacío → pérdida de reanudación y re-escritura de pistas aceptadas | `orquestador.py:47-60,210`; `planificador.py:318-324` | **Alta — escenario principal de fallo del sistema** |
| Studio: single-flight (2ª → 409), timeout duro 900 s + kill, `recover_interrupted()` al arrancar (marca `interrupted`) | `jobs.py:25,55-67,220-321` | OK |
| Sin framework de logging en Studio/Composer (solo consola + `job.log`) | grep logging=0 | Baja |
| Cancelación: Studio sí; CLI: kill del SO; orquestador: ninguna por pista | — | Media |

## D. Recursos (mediciones + estimaciones claramente separadas)

| Métrica | Valor | Tipo |
|---|---|---|
| Producción MIDI de una pista (full, 4:30 min) | **0,174 s · pico 22,3 MiB** | **MEDIDO** (TEST01, `/usr/bin/time -v`) |
| MIDI por pista | ~7,6–10 KB | MEDIDO |
| WAV 44.1k estéreo 16-bit, 4:30 min | ~33 MB | ESTIMACIÓN |
| RAM en render WAV (FluidSynth) | ~100–250 MB por proceso | ESTIMACIÓN |
| Álbum 13 pistas MIDI | segundos (sub-minuto) | MEDIDO por pista (0,174 s ×13 ≈ 2,3 s CPU) |
| Álbum 13 pistas con WAV+MP3 | minutos (WAV dominante) | ESTIMACIÓN |
| Con 16 GB | N=2–3 renders en paralelo sobrado; recomendado secuencial para estabilidad | ESTIMACIÓN |

## E. Modelo de ejecución recomendado (decisión única)

**RECOMENDACIÓN: un proceso por álbum** — `python -m album producir` como subproceso de Composer, secuencial por pista, in-process produce (diseño actual del orquestador), con **3 refuerzos**:
1. **Atomicidad** de `estado.json`/`huellas.json`/`plan.json` (tmp + `os.replace` + `.bak`).
2. **Watchdog ~900 s por pista** en el llamador (Composer) con registro y fallo limpio de la pista (no del álbum).
3. **Single-flight** en Composer (una producción activa; 2ª petición → 409), mismo contrato que Studio.

Descartadas: cola de trabajos con worker persistente (complejidad sin beneficio en escritorio monousuario), un proceso por canción desde Composer para álbumes (duplicaría el bucle de estados del orquestador), paralelismo N>1 para MIDI (innecesario: 0,17 s/pista). Paralelismo opcional **solo en WAV** a posteriori (N=2).

## F. Escenario principal de fallo del sistema + mitigación

**Escenario**: corte de luz / cierre forzado a mitad de producción de un álbum → `estado.json` truncado → reanudación perdida → pistas aceptadas regeneradas (o el usuario cree que sí).
**Mitigación** (ordenada): (1) atomicidad del estado (fix P0-3); (2) `estado.json` tras cada pista (ya existe); (3) watchdog por pista para no dejar hijos colgados; (4) verificación post-corrida con `manifiesto.json --verify`; (5) regla de oro ya vigente: **un resultado aceptado nunca se regenera sin `--regen` explícito** (F8-6).

## G. Extras operativos

| Tema | Veredicto |
|---|---|
| Puertos | Composer **8898**, Studio **8899** — sin colisión (legado 8765-8774 sin uso). Reservar 8897 para futura capa Library si se quiere | 
| FluidSynth ×2 en paralelo | **Seguro** (procesos independientes de archivo→WAV) |
| Ficheros bloqueados (Windows) | Manejo explícito en delete/render con mensajes claros (mejora pendiente) |
| Antivirus | Evitar escaneo en tiempo real de `DMD_Library/` (recomendación de configuración local) |
| `.pyc` del repo | R5: lanzar hijos con `PYTHONDONTWRITEBYTECODE=1` (y evitar mutar `forge/__pycache__`) |
| `.env` en la raíz del repo | Contiene solo `DATABASE_URL` (infra del sandbox); sin secretos del proyecto; sin relación con DMD — sin acción |
