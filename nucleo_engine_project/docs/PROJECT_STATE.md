# PROJECT_STATE — Dark Music Director + MIDI Forge

> Estado del proyecto tras **FASE 8 — Album Production System** (capa de
> planificación/orquestación de álbumes; FASE 7 completa, FASE 6 completa y
> escuchada, FASE 5 completa y aprobada).
> Fecha: 2026-11-09 · Árbol: `nucleo_engine_project/`

---

## 1. Pipeline general

```
dark-director/1 JSON (rev 3.2, CONGELADO)
    ↓  dark_director.compilador
midi-forge/1 JSON (proyecto)
    ↓  [path ORIGINAL]  forge.adapter.normalize → forge.engine.generate
    ↓  [path MEJORADO]  jazz_engine.enhance → forge.adapter.normalize
                        → jazz_engine.render.generate (hooks Rhodes/vibes)
MIDI / WAV → Suno
```

## 2. Identidad musical activa

| Estado | Identidad | Dónde |
|---|---|---|
| **ACTIVA** | `dark_triphop` | receta congelada `dark_director/identities/dark_triphop.py` + perfil `jazz_engine/profiles.py::DARK_TRIPHOP` |
| ARCHIVADA | `doom_triphop` | receta registrada (compatibilidad); perfil `DOOM_TRIPHOP` reproducible |
| ARCHIVADA | `doom_dark_jazz` | receta registrada (compatibilidad); perfil `DOOM_DARK_JAZZ` reproducible |

Metadatos: `dark_director/identities/__init__.py` → `IDENTIDAD_ACTIVA`, `IDENTIDADES_ARCHIVADAS`,
`estado_identidad()`, `es_activa()`. El contrato rev 3.2 NO cambió (doom sigue aceptado;
archivado ≠ roto).

## 3. Módulos y responsabilidades

### dark_director/ (capa de dirección — sin cambios salvo metadata de unificación)
| Módulo | Rol |
|---|---|
| `contract.py` | Contrato rev 3.2 (PROTEGIDO, intocable) |
| `validador.py` | E1xx/E2xx/E3xx/W4xx |
| `compilador.py` | dark-director/1 → midi-forge/1 |
| `recetas.py` | Registro fail-fast de recetas N1 |
| `identities/dark_triphop.py` | Receta congelada (PROTEGIDA) |
| `identities/doom_*.py` | Recetas archivadas (intactas) |
| `identities/__init__.py` | Registro + **metadata FASE 5** (activa/archivadas) |
| `forge_link.py` | Import perezoso de forge sin modificarlo |

### forge/ (MIDI Forge — PROTEGIDO, 0 cambios)
`theory · voicing · styles · engine · adapter · validate · midiwriter · audio`.

### jazz_engine/ (FASE 5 — nuevo, sin dependencias fuera de forge/stdlib)
| Módulo | Responsabilidad |
|---|---|
| `context.py` | Context Analyzer: armonía por compás (guías/tensiones), energy/tension/focus (lee `meta.director.original`), reutiliza `forge.theory` |
| `profiles.py` | Perfiles de identidad como DATO: `DARK_TRIPHOP` (activo), `DOOM_TRIPHOP`, `DOOM_DARK_JAZZ` (archivados) |
| `motif.py` | Motif Generator + Motif Development: celdas rítmicas, objetivos armónicos, aproximaciones, transformaciones (reharmonize/fragment/displace/invert/vary_ending/register_shift) |
| `improv.py` | Phrase Scheduler + Phrase Generator (sax via `lead.phrases` nativo) + Rhodes Engine (behaviors SUPPORT/RESPONSE/COUNTERPOINT/INDEPENDENT/INTERACTION) |
| `drums_engine.py` | Groove: ghost notes, acentos de kick fuera del patrón de bajo, variación de hats, fills SOLO en secciones build, ruptura/reconstrucción. Transformación pura de proyecto (midi-forge/1 válido) |
| `vibes_engine.py` | Params de replies/pings por sección + ECO motivico en huecos reales del sax (render-time) |
| `coordinator.py` | Plan por sección: protagonismo, densidad, modo Rhodes, actitud de batería, presupuesto vibes; presets de variación (balanced/melodic/atmospheric/groove/sparse). FASE 6: integración de perfiles de producción en `normalize_config` |
| `production.py` | **FASE 6** — Perfiles de PRODUCCIÓN como dato: `original/sax/sax_rhodes/drums/sax_vibes/full/atmospheric`; presets reproducibles de motores; API `nombres/resolver/aplicar` |
| `enhance.py` | Punto único de enriquecimiento puro (sax+drums+vibes params). Protege material del compositor |
| `render.py` | Orquestación: delegación OFF==forge byte a byte; hooks de buffer Rhodes/vibes pre-reparación; normaliza con el adaptador oficial. FASE 6: `production=original` = camino ORIGINAL oficial (normalize+generate); notas de motor en evidencia |
| `__main__.py` | CLI JSON-first: `--config`, `--production PERFIL`, `--seed` (FASE 6) |

## 4. Contratos de comportamiento (verificados por tests)

1. **OFF == original**: `render.generate(p, None)` ≡ `E.generate(p)` byte a byte;
   con todos los motores OFF también.
2. **Determinismo**: misma (proyecto, config) → MIDI idéntico (5 semillas testeado).
3. **Silencio con función**: secciones sin frase del sax → bloque lead apagado
   (el generativo nativo no rellena), salvo material del compositor.
4. **Material del compositor protegido**: frases escritas jamás se sustituyen ni silencian.
5. **Guardrails**: lead_mono_range, lead_coverage, mallet_sparse, lead_mallet_overlap,
   bass_kick, four_on_floor, section_bounds, no_constant_max — verdes en todos los escenarios.

## 5. Config de motores (side-file JSON, NO es contrato)

```json
{
  "production": "full",
  "engines": {"sax": true, "rhodes": true, "drums": true, "vibes": true},
  "profile": "auto",
  "seed": 2026,
  "density": {"sax": 1.0, "rhodes": 1.0, "vibes": 1.0, "drums": 1.0},
  "variation": "balanced"
}
```

FASE 6: `production` (perfiles de producción) es la forma recomendada de
seleccionar la configuración; el preset actúa como BASE y la config explícita
gana clave a clave (`production: "original"` = camino ORIGINAL sin motores;
no admite overrides de motores).

## 6. Tests

| Suite | Estado |
|---|---|
| `tests/test_forge.py` (34) | OK (2 skips = audio) |
| `tests/dmd/` (171) | OK, 18 subtests |
| `tests/fase5/` (37) | OK, 1 skip |
| `tests/fase6/` (18) | OK (FASE 6) |
| `tests/fase7/` (56) | OK (FASE 7) |
| `tests/fase8/` (39) | OK (FASE 8) |
| Total | **354 passed, 3 skipped, 18 subtests** |

## 7. Rutas importantes

- Referencias doradas (INMUTABLES): `output/fase5_comparativos/` + `GOLDEN.md`;
  manifiesto `manifests/golden_fase5.json`; verificar: `python3 manifests/verificar_golden.py`
- Matriz de generalización FASE 6: `output/generalizacion_fase6/` (5 composiciones × perfiles,
  evidencia, checks, RESUMEN.md, sobreajuste.{json,md})
- Comparativos FASE 7: `output/fase7_comparativos/` (A/B/C, 17 runs)
- **FASE 8 — Álbum demo «Noches Largas»**: spec `albumes/noches_largas/album.json`,
  resultados `output/albumes/noches_largas/` (13 pistas + plan + estado + informe + manifiesto)
- Sistema de álbumes: paquete `album/` (CLI `python3 -m album`); guía `docs/ALBUM_PRODUCCION.md`
- CLI de producción: `scripts/produce.py` (núcleo `producir_cancion()`); índice: `output/produccion/INDICE.md`
- Manifiestos: `manifests/protegidos.json`, `manifests/golden_fase5.json`, `manifests/tree_fase8.json`
- Backups: `backups/`
- Docs: `docs/PROJECT_STATE.md`, `docs/DECISIONS.md`, `docs/NEXT_MISSION.md`,
  `docs/CHECKPOINT_FASE6.md`, `docs/CHECKPOINT_FASE7.md`, `docs/CHECKPOINT_FASE8.md`,
  `docs/ALBUM_PRODUCCION.md`, `docs/HARMONIA_BIBLIOTECA.md`, `docs/PROPUESTA_VARIACION_ALBUM.md`

## 8. Limitaciones conocidas

1. **Sin escucha**: el sandbox no tiene FluidSynth ni soundfonts (`audio.status()` disponible=false).
   Toda valoración musical pendiente de validación auditiva del usuario.
2. `jazz_engine` fue **reconstruido en este entorno** (el código Fase 3/4 no estaba en el árbol
   de trabajo); ver `CHECKPOINT_FASE5.md` §Reconciliación.
3. El eco del vibes requiere frases del sax (por diseño); con lead generativo denso no hay huecos.
4. Los perfiles doom están operables pero NO son la dirección del proyecto.
5. GM/soundfont: growl/subtone/expresión profesional de sax no reproducibles (techo GM, nivel 3).
6. **F6-L1**: `density.sax`/`density.rhodes` no afectan a las decisiones de actividad de sus
   motores (solo drums/vibes consumen density). CONGELADO para no alterar los perfiles aprobados;
   ver DECISIONS.md F6-L1 y test_18 de la suite fase6.
7. **F6-O1** (upstream forge, protegido): en estructuras cortas con chorus final, la última nota
   del lead generativo puede extender su release ~1–2 beats tras el fin del proyecto. El
   validador de forge lo acepta (section_bounds vigila inicios); sin efecto audible relevante;
   sin acción (forge no se toca).


---

## FASE 7 — Harmonic Familiarity Engine (2026-11-09)

Biblioteca de progresiones armónicas familiares + motor de selección + motor
de adaptación, activables por keyword/ID vía side-config o CLI:

- `jazz_engine/harmony_library.py` (44 progresiones, 6 familias, esquema validado,
  extensible por JSON externo sin tocar el motor) · `harmony_select.py` (keyword,
  scoring por contexto DMD, una progresión por tipo, cuota ≤4 por canción) ·
  `harmony_adapt.py` (grados→tonalidad real, diatonía garantizada, transformaciones
  con presupuesto, huella del arquetipo) · `harmony.py` (etapa de integración).
- Integración: única enganche en `render.generate`; `harmony` viaja en la
  side-config (contrato intacto; `original`+harmony → ValueError).
- Garantías verificadas por tests: sin `harmony` el pipeline es byte a byte el
  de FASE 6 (dorados regenerados idénticos); 7 perfiles compatibles; material
  del compositor respetado; determinismo; diatonía 11.264 acordes sin fallos.
- Comparativos A/B/C en `output/fase7_comparativos/` (17 runs, 0 fallos).
- Guía: `docs/HARMONIA_BIBLIOTECA.md` · Checkpoint: `docs/CHECKPOINT_FASE7.md`.
- En FASE 8 la biblioteca se usa por pista en álbumes SOLO con declaración
  explícita del compositor (ver sección FASE 8).

---

## FASE 8 — ALBUM PRODUCTION SYSTEM (2026-11-09)

Capa de planificación, orquestación, diversidad, validación y
reproducibilidad para álbumes completos (referencia: 13 pistas, sin límite
duro). El álbum ORGANIZA composiciones; NO compone ni genera MIDI:

- Paquete `album/` (nuevo): `esquema.py` (dmd-album/1, fail-fast A1xx),
  `planificador.py` (plan determinista dmd-album-plan/1; semillas derivadas
  `semilla_album + 101*(i+1)`; asignación greedy de perfiles; compilación en
  seco de docs), `diversidad.py` (PRE docs + POST huellas; duplicados SHA256;
  Jaccard ≥0.85), `orquestador.py` (estado.json, resume/--regen/--solo/
  --forzar, aislamiento de fallos), `informe.py` (informe_album.json/.md +
  manifiesto.json), `__main__.py` (CLI `python3 -m album`).
- `scripts/produce.py`: núcleo expuesto como `producir_cancion()` (CLI y
  artefactos IDÉNTICOS; añade huella técnica FASE 8 al resultado).
- Armonía por pista SOLO EXPLÍCITA (`harmony` en el spec); `original`
  + harmony → error; familiarity_auto jamás automática (W-A3 si aparece).
- Álbum demo «Noches Largas»: 13/13 OK (~27.8 min), 0 compliance fails,
  diversidad limpia, determinismo completo verificado; spec en
  `albumes/noches_largas/album.json`, resultados en `output/albumes/noches_largas/`.
- Tests: 39 nuevos (tests/fase8). Total **354 passed, 3 skipped, 18 subtests**.
- Documentación: `docs/CHECKPOINT_FASE8.md` (autocontenido) +
  `docs/ALBUM_PRODUCCION.md` (guía) + DECISIONS.md (F8-1..F8-8) +
  `manifests/tree_fase8.json` (snapshot).
- Pendiente: escucha del usuario del álbum + decisión F6-L1.

---

## 12. DMD STUDIO (FASE 9 — aplicación local de composición, 2026-11-10)

Nueva aplicación desde cero (NO es el convertidor `app.py`): capa de control,
edición y visualización sobre los motores, que siguen siendo la única fuente de
verdad musical. Documentación completa: **`docs/DMD_STUDIO.md`**.

- **Código**: `studio/` (server.py FastAPI, projects.py, jobs.py, runner.py,
  capabilities.py, settings.py) + `studio/static/` (SPA sin build: 7 áreas —
  Projects, Composition, Harmony, Production, Generation, JSON, Results).
- **Pipeline**: la generación ejecuta `scripts/produce.py::producir_cancion()`
  en subproceso aislado. Sin segundo pipeline. Determinismo web==CLI byte a
  byte verificado (mismo doc, perfil, seed).
- **Estado**: `studio_data/` (proyectos, generaciones, jobs, ajustes). No toca
  `output/`, `forge/`, `styles.py`, `dark_director/` ni los goldens.
- **Pruebas**: `tests/studio/` (13 pytest) + `scripts/e2e_studio.py` (matriz
  integral 36/36) + regresión `tests/dmd` 171 OK.
- **Windows**: `scripts/windows/install_studio.bat` → `check_studio.bat` →
  `start_studio.bat`; `requirements-studio.txt` (fastapi, uvicorn); venv
  independiente `.venv-studio`; servidor solo en 127.0.0.1:8899.
- **Fase 7 sigue siendo opcional**: la biblioteca de familiaridad se activa
  solo si el usuario lo decide (Production/Harmony → INACTIVA por defecto).
- Intocables respetados: `forge/`, `styles.py`,
  `dark_director/identities/dark_triphop.py`, `contract.py` (regresión 171 OK).
