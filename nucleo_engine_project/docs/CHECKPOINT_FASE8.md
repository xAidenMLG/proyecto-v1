# CHECKPOINT FASE 8 — ALBUM PRODUCTION SYSTEM

> Documento AUTOCONTENIDO: permite continuar el proyecto en una conversación
> nueva sin depender del historial. Fecha de corte: 2026-11-09.
> Sucesor de CHECKPOINT_FASE7.md. Guía de uso detallada: `docs/ALBUM_PRODUCCION.md`.

---

## 0. Qué es este proyecto (30 segundos)

**Dark Music Director (DMD)** + **MIDI Forge**: sistema para producir álbumes de
Dark Trip Hop para YouTube, reproducibles y deterministas.

```
dark-director/1 JSON ──(DMD)──▶ midi-forge/1
    ──▶ [jazz_engine: harmony opcional + motores OPCIONALES] ──▶ MIDI Forge ──▶ MIDI/WAV ──▶ Suno
        ▲
album.json (dmd-album/1) ──▶ album/ (FASE 8): planifica, orquesta, valida, audita
```

- **MIDI Forge** (`forge/`, PROTEGIDO): el único motor MIDI.
- **DMD** (`dark_director/`): contrato `dark-director/1` rev 3.2 (CONGELADO).
- **jazz_engine**: motores musicales (F5) + perfiles de producción (F6) +
  biblioteca de familiaridad armónica (F7).
- **album/** (FASE 8, NUEVO): ALBUM PRODUCTION SYSTEM — capa de PLANIFICACIÓN
  y ORQUESTACIÓN. Organiza composiciones individuales; NO compone, NO genera
  MIDI, NO duplica motores.

## 1. Estado canónico (corte FASE 8)

| Componente | Estado |
|---|---|
| Contrato `dark-director/1` rev 3.2 | CONGELADO, 0 campos nuevos |
| `forge/` + `styles.py` + `dark_triphop.py` + `contract.py` | PROTEGIDOS, 0 cambios (`hash_protected.py verify` OK) |
| Referencias doradas FASE 5 (8 MIDIs) | INMUTABLES, `verificar_golden.py` OK (34 archivos) |
| Perfiles de producción FASE 6 (7) | INTACTOS (nombres y presets sin cambios) |
| Biblioteca de familiaridad FASE 7 (44) | INTACTA; en álbumes SOLO por declaración explícita por pista |
| **ALBUM PRODUCTION SYSTEM** | `album/` (6 módulos) + `produce.producir_cancion()` + CLI `python3 -m album` |
| Álbum demo «Noches Largas» | 13/13 pistas OK, ~27.8 min, compliance 0 fails, determinista |
| Tests | **354 passed, 3 skipped, 18 subtests** (fase8: 39 · fase7: 56 · heredados: resto) |
| Validación musical | PENDIENTE DEL USUARIO (escucha de `output/albumes/noches_largas/`) |

## 2. Arquitectura FASE 8

```
album/
  esquema.py      Esquema dmd-album/1. Validación fail-fast (códigos A1xx)
                  REUTILIZANDO validadores reales (production.nombres(),
                  harmony_select.normalizar_activacion, harmony_library.por_id).
                  Regla: harmony solo EXPLÍCITA; original+harmony → A113.
  planificador.py Plan determinista (dmd-album-plan/1): compila cada doc en
                  seco (A2xx por doc), digest técnico, semillas derivadas
                  (semilla_album + 101*(i+1)), asignación greedy de perfiles
                  (frac_max, respiro cada N, no consecutivos), diversidad PRE.
                  Un doc roto NO aborta el álbum: queda como error_plan (A2xx/W-A9).
  diversidad.py   PRE: distribución/frac de perfiles, ventanas de respiro,
                  consecutivas (perfil+tonalidad+BPM), BPM 76–92, distancias
                  tonales, curva de energía. POST: duplicados exactos (SHA256)
                  y similitud Jaccard de huellas ≥ 0.85 («sospechoso»).
  orquestador.py  Ejecución por pista vía scripts/produce.py::producir_cancion
                  (MISMO núcleo que el CLI F6). estado.json tras cada pista
                  (crash-safe); resume / --regen / --solo / --forzar; fallo
                  por pista aislado; drift de especificación → pendiente.
  informe.py      informe_album.json/.md + manifiesto.json
                  (dmd-album-manifiesto/1: config efectiva + hashes + comandos
                  de regeneración --verify por pista).
  __main__.py     CLI: plan | producir | informe | estado
scripts/produce.py  núcleo expuesto como producir_cancion(); añade huella
                  técnica (FASE 8) al resultado; CLI y artefactos IDÉNTICOS.
```

Dependencia en una dirección: `album/` → `dark_director` + `jazz_engine` +
`scripts/produce.py`. NADA importa `album/`.

## 3. Uso esencial

```bash
# álbum completo (planifica + produce + informe)
python3 -m album producir albumes/noches_largas/album.json --out output/albumes/noches_largas
# reanudar / regenerar selectivamente / solo un bloque / todo
python3 -m album producir ... --out ...                    # idempotente
python3 -m album producir ... --out ... --regen 7,viaducto_sur
python3 -m album producir ... --out ... --solo 1,2,3
python3 -m album producir ... --out ... --forzar
# plan solo / informe / estado
python3 -m album plan albumes/noches_largas/album.json --out DIR
python3 -m album informe DIR ; python3 -m album estado DIR
```

Side-file `album.json` (esquema `dmd-album/1`): identidad, semilla_album,
curva_energia opcional, restricciones opcionales (defaults: perfil_frac_max
0.4, respiro_cada 5, prohibir_consecutivos_iguales true) y pistas con
id/doc/perfil?/seed?/harmony?. **La biblioteca de familiaridad NO es
predeterminada y familiarity_auto nunca se activa sola** (si aparece en el
spec → aviso W-A3). Detalles: `docs/ALBUM_PRODUCCION.md`.

## 4. Álbum demo «Noches Largas» (13 pistas, producción REAL)

Spec: `albumes/noches_largas/album.json` · Resultados:
`output/albumes/noches_largas/` · Docs: 5 reutilizados de FASE 6 +
8 nuevos (`scripts/fase8_componer_album.py`, re-ejecutable).

| # | Pista | Perfil | Seed | Armonía | Tonalidad | BPM | SHA256(16) |
|---|---|---|---|---|---|---|---|
| 1 | medianoche_puerto | sax | 2026 | — | F#m | 78 | 41058bc61dd40c03 |
| 2 | calles_de_neon | full | 2026 | familiar_pop | Am | 92 | 07b97c86a1e00cd3 |
| 3 | habitacion_314 | atmospheric | 2026 | melancholic | Gm | 80 | 7252a5953f2a2993 |
| 4 | bruma_dorada | original | 3504 | — | Bbm | 80 | 7573247183da19c1 |
| 5 | casa_de_espejos | sax_rhodes | 2026 | soulful | Cm | 84 | 75cb88be775105d0 |
| 6 | neblina_alta | drums | 3706 | tension_release | Em | 76 | c44c010b2665b1eb |
| 7 | viaducto_sur | full | 3807 | CINE01 | Dm | 90 | bd123097c269dec9 |
| 8 | habitacion_vacia | atmospheric | 3908 | dream_pop | Fm | 82 | 15e9399ba5783030 |
| 9 | asfalto_humedo | sax_vibes | 4009 | alternative | Am | 86 | 2366c75942dca0c1 |
| 10 | portico_sur | original | 4110 | — | Dm | 79 | 6797453d959b0636 |
| 11 | nocturno_terminal | full | 2026 | dark_cinematic | Dm | 86 | cd3c7303db17d662 |
| 12 | marea_baja | sax | 4312 | emotional_resolution | Fm | 84 | bd2208f4460e715b |
| 13 | ultimo_metro | atmospheric | 4413 | familiarity_auto (explícita) | Cm | 76 | 9ccab4118229e2e7 |

Verificado: 13/13 ok · 0 compliance fails · sin duplicados ni similares ·
sin exceso de perfil · ventanas de respiro OK · desviación de curva ≤0.01 ·
9/10 keywords FASE 7 usados · 5 pistas en ruta ORIGINAL · determinismo del
álbum completo verificado (dos ejecuciones → 13/13 MIDIs idénticos).
Regeneración verificada: `produce.py ... --verify <sha>` → «resultado
idéntico».

## 5. Pruebas y regresión

```bash
python3 -m pytest tests/ -q          # 354 passed, 3 skipped, 18 subtests
python3 manifests/hash_protected.py verify   # protegidos OK
python3 manifests/verificar_golden.py        # 34 dorados OK
python3 -m album producir albumes/noches_largas/album.json \
        --out output/albumes/noches_largas --forzar   # determinismo completo
```

Suite fase8 (39): esquema A1xx (8) · planificador (9) · orquestación (6:
produce+resume+fallo parcial+regen+solo+drift) · diversidad (4) ·
determinismo (2) · integración (4: núcleo produce, huellas, arquitectura,
paquete) · regresión (4: goldens, dorado regenerado, técnico-vs-musical,
contrato/perfiles/biblioteca).

## 6. Decisiones FASE 8 (resumen; detalle en DECISIONS.md)

F8-1 side-file dmd-album/1 (no contrato) · F8-2 reutilización del núcleo de
produce.py (refactor expuesto, CLI idéntico) · F8-3 semillas derivadas
documentadas · F8-4 asignación de perfiles como sugerencia (explícito gana) ·
F8-5 un doc roto no aborta el álbum · F8-6 drift de especificación preserva
el resultado aceptado (--regen explícito) · F8-7 huella técnica Jaccard 0.85
(métrica, no veredicto) · F8-8 album/ no importa nada hacia atrás.

## 7. Qué NO debe modificarse (reglas duras heredadas + nuevas)

1–10. Todas las reglas de CHECKPOINT_FASE7 §8 siguen en pie (forge y
   protegidos, dorados, contrato rev 3.2, perfiles aprobados, doom NO como
   default, harmony jamás en `original`, cuota F7 sin evidencia de escucha).
11. No dar valor predeterminado a `harmony` en el álbum: solo spec explícito.
12. No convertir avisos de diversidad (W-A4..A8) en errores: el compositor
    manda; el sistema sugiere.
13. No regenerar los goldens FASE 5/6/7 en sitio; fixtures nuevos aparte.
14. No duplicar generación MIDI/render en album/ (usa producir_cancion).

## 8. Próxima misión recomendada

1. **Escucha del álbum** `output/albumes/noches_largas/` (orden del informe)
   → veredicto por pista y del conjunto (identidad, fatiga, transiciones).
2. Decisión pendiente F6-L1 (density.sax/rhodes) — sigue congelada.
3. Si la escucha aprueba: pipeline Suno (stems/mixdown) y plantilla de
   metadatos de YouTube sobre el manifiesto del álbum.
