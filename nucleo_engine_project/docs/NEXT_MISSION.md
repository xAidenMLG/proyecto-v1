# NEXT_MISSION — Estado y continuación

> Actualizado al cierre de FASE 8 (2026-11-09).

---

## 1. Estado de la misión FASE 8

| Etapa | Estado |
|---|---|
| A — Auditoría del repositorio y APIs reales | ✅ docs + produce.py + production/render/harmony + contratos; propuesta de álbum leída y usada como base (no copiada a ciegas: el esquema evolucionó respecto a la propuesta) |
| B — Esquema del álbum (`dmd-album/1`) | ✅ side-file validado fail-fast; perfiles/semillas/harmony por pista; A1xx acumulados |
| C — Planificador determinista | ✅ digests de docs, compilación en seco, semillas derivadas, asignación de perfiles, diversidad PRE |
| D — Orquestador | ✅ produce por pista vía `producir_cancion()`; estado.json; resume/--regen/--solo/--forzar; fallos aislados |
| E — Diversidad y coherencia | ✅ PRE (docs) + POST (huellas Jaccard, duplicados SHA256); informe separa técnico vs musical |
| F — Reproducibilidad | ✅ plan.json + manifiesto.json (config efectiva, hashes, comandos --verify); determinismo completo verificado |
| G — Álbum real de 13 pistas | ✅ «Noches Largas»: 13/13 OK, 0 compliance fails, ~27.8 min |
| H — Pruebas y regresión | ✅ 354 passed, 3 skipped, 18 subtests; protegidos OK; 34 goldens OK |
| I — Documentación | ✅ CHECKPOINT_FASE8 + ALBUM_PRODUCCION + PROJECT_STATE + DECISIONS + NEXT_MISSION + tree_fase8.json |

## 2. Trabajo completado (resumen)

- Paquete `album/` (esquema, planificador, diversidad, orquestador, informe, CLI).
- `scripts/produce.py`: núcleo expuesto como `producir_cancion()` (CLI idéntico;
  fix de evidencia F7-O2); huella técnica para diversidad.
- `scripts/fase8_componer_album.py`: composición del álbum demo (8 docs nuevos
  + 5 reutilizados + album.json), re-ejecutable.
- Álbum «Noches Largas»: `albumes/noches_largas/` (spec) →
  `output/albumes/noches_largas/` (13 pistas + plan + estado + informe + manifiesto).
- Tests `tests/fase8/` (39). Snapshot `manifests/tree_fase8.json`.
- Docs: `docs/CHECKPOINT_FASE8.md` (autocontenido) y `docs/ALBUM_PRODUCCION.md` (guía).

## 3. Pendiente (validación del usuario)

1. **ESCUCHA del álbum** `output/albumes/noches_largas/` — orden del informe
   (`informe_album.md`); evaluar identidad, fatiga de densidad, transiciones
   entre pistas y las progresiones familiares activadas (8 pistas con
   keyword/ID; 5 en ruta ORIGINAL).
2. Decidir F6-L1 (density.sax/rhodes) — sigue congelada.
3. Veredicto sobre la escucha de los comparativos FASE 7 (sigue abierto del
   ciclo anterior) — el álbum usa 9/10 keywords y puede servir de muestra.

## 4. Riesgos abiertos

| Riesgo | Mitigación |
|---|---|
| La diversidad técnica (Jaccard, perfiles) no garantiza variedad audible | La escucha humana decide; el informe lo separa explícitamente |
| F6-L1 puede enmascarar la intención de los presets melodic/sparse | Documentado (DECISIONS F6-2); fix diferido con re-validación |
| Sin FluidSynth en el sandbox: no hay WAV/escucha automática | Artefactos preparados para FluidSynth local (comandos en evidencia.json) |

## 5. Próximas prioridades sugeridas

1. Escucha del álbum (28 min) → veredicto por pista.
2. Si aprueba: **stems/mixdown para Suno** + plantilla de metadatos de YouTube
   alimentada por `manifiesto.json` del álbum.
3. Opcional: extensión de la biblioteca armónica (nuevos arquetipos) solo con
   evidencia de escucha (regla CHECKPOINT_FASE7 §8.9).

## 6. Instrucciones para continuar (nueva conversación)

Abrir `docs/CHECKPOINT_FASE8.md` — autocontenido: arquitectura, esquema
album.json, CLI, álbum de referencia con hashes, comandos de reproducción,
tests, limitaciones y qué NO debe modificarse. Guía de uso:
`docs/ALBUM_PRODUCCION.md`.
