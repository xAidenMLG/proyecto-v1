# CHECKPOINT FASE 7 — Harmonic Familiarity Engine

> Documento AUTOCONTENIDO: permite continuar el proyecto en una conversación
> nueva sin depender del historial. Fecha de corte: 2026-11-09.
> Sucesor de CHECKPOINT_FASE6.md.

---

## 0. Qué es este proyecto (30 segundos)

**Dark Music Director (DMD)** + **MIDI Forge**: sistema para producir álbumes de
Dark Trip Hop para YouTube, reproducibles y deterministas.

```
dark-director/1 JSON ──(DMD: dark_director/)──▶ midi-forge/1 JSON
    ──▶ [jazz_engine: harmony (FASE 7) + motores OPCIONALES] ──▶ MIDI Forge ──▶ MIDI/WAV ──▶ Suno
```

- **MIDI Forge** (`forge/`, PROTEGIDO): el único motor MIDI. jazz_engine NO duplica nada.
- **DMD** (`dark_director/`): contrato `dark-director/1` rev 3.2 (CONGELADO), validador, recetas, compilador.
- **jazz_engine**: motores musicales DARK TRIP HOP (FASE 5), perfiles de producción (FASE 6)
  y biblioteca de familiaridad armónica (FASE 7).
- Regla de oro: familiaridad armónica SÍ, pop genérico NO. La progresión es la
  base del recorrido, no una prisión para los instrumentos.

## 1. Estado canónico (corte FASE 7)

| Componente | Estado |
|---|---|
| Contrato `dark-director/1` rev 3.2 | CONGELADO, 0 campos nuevos (harmony viaja en side-config) |
| `forge/` + `styles.py` + `dark_triphop.py` + `contract.py` | PROTEGIDOS, 0 cambios (hash_protected OK) |
| Referencias doradas FASE 5 (8 MIDIs) | INMUTABLES, regeneración byte-idéntica verificada |
| Perfiles de producción FASE 6 (7) | INTACTOS sin `harmony`; compatibles con `harmony` (los 7, menos original que la rechaza con ValueError) |
| Biblioteca de familiaridad | 44 progresiones, 6 familias (`jazz_engine/harmony_library.py`) |
| Tests | **315 passed, 3 skipped** (fase7: 56 · fase6: 18 · fase5+dmd+forge: resto) |
| Comparativos FASE 7 | 17 runs (5 composiciones × A/B/C + 2 auto), 0 fallos compliance, A == golden FASE 6 |
| Validación musical | **PENDIENTE DEL USUARIO** (escucha de `output/fase7_comparativos/`) |

## 2. Qué se construyó (arquitectura)

```
jazz_engine/
  harmony_library.py   DATOS: 44 progresiones en grados funcionales + esquema
                       validado + extensión vía JSON externo (sin tocar motor)
  harmony_select.py    BÚSQUEDA: keyword→familia/estrategia; scoring (familiaridad,
                       tensión REAL de DMD, resolución, variedad, transición de
                       raíces, ritmo); UNA progresión por TIPO de sección;
                       cuota de ≤4 progresiones distintas por canción
  harmony_adapt.py     ADAPTACIÓN: grados→tonalidad/modo reales (calidad DIATÓNICA
                       de la escala; excepciones V/VII mayor en menor; caso del
                       numeral si el modo coincide), transformaciones con presupuesto
                       (extensiones, sus, inversión, sustitución, intercambio modal,
                       deceptiva, colas de aproximación), huella del arquetipo
  harmony.py           ETAPA: reescribe sections[].chords del proyecto compilado
                       ANTES de enhance (todo el pipeline hereda la armonía);
                       respeta material del compositor; evidencia completa
  render.py            (+15 líneas): único punto de enganche, tras normalize_config
```

Integración mínima: `production.py` y `coordinator.py` NO se tocaron (la clave
`harmony` pasa por el mecanismo de config existente).

## 3. Activación (resumen; guía completa en docs/HARMONIA_BIBLIOTECA.md)

```json
{"production": "full", "seed": 2026,
 "harmony": {"keyword": "dark_cinematic", "seed": 77, "variacion": "medium"}}
```

```bash
python3 -m jazz_engine doc.json --dark-director --production full --seed 2026 \
    --harmony dark_cinematic --harmony-variacion medium -o tema.mid --evidence ev.json
python3 scripts/produce.py doc.json --production full --seed 2026 \
    --harmony dark_cinematic --harmony-variacion medium --harmony-seed 77 --out output/produccion/mi_tema
```

Keywords: `familiar_pop melancholic nostalgic dark_cinematic dream_pop
alternative soulful emotional_resolution tension_release familiarity_auto` + ID
concreto (`{"id": "CINE01"}`) + pins por tipo (`{"progressions": {"verse":
"MEL02"}}`). `original` + harmony → ValueError (camino ORIGINAL intacto).

## 4. Reglas musicales congeladas (LEER ANTES DE TOCAR)

1. **Calidad diatónica**: la escala de la composición decide la calidad de cada
   grado cuando la clase modal del arquetipo NO coincide con la de la
   composición; si coincide, manda el caso del numeral (intercambio modal del
   arquetipo, p. ej. VImaj7 dórico). Excepción V/VII mayor en menor.
2. **Ancla**: el primer acorde del ciclo nunca cambia de raíz.
3. **Presupuestos**: subtle 0 estructurales/2 ext · medium 2/3 · rich 3/4.
4. **Huella**: movimiento de raíces medido; umbrales 1.0/0.95/0.6/0.5 por nivel.
5. **Cuota**: ≤4 progresiones distintas por canción (reasignación determinista).
6. **Cadencia**: el ciclo nunca se trunca a ciegas — se compacta (ancla+cadencia)
   o se completa con giro (turnaround IV–V7 o iv–V7).
7. **Material del compositor**: secciones con `lead.phrases` del compilado
   conservan su armonía (`respetar_material: true` por defecto).
8. **Transiciones**: colas de aproximación (rich) usan el PRIMER acorde REAL
   (ya adaptado) de la sección siguiente; adaptación en orden inverso.

## 5. Comparativos FASE 7 (output/fase7_comparativos/)

| Composición | Keyword | A (regresión) | B (familiar) | C (transformada) |
|---|---|---|---|---|
| nocturno_terminal (Dm) | dark_cinematic | == golden 07 | 7205165cbaedf22a | 336846d323a89024 |
| medianoche_puerto_nuevo (F#m) | dream_pop | == golden C1 | 72595ddb7c65e207 | 16160b5a42f521bf |
| casa_de_espejos (Cm) | soulful | == golden full | aeafe7b5b7397491 | 717f02a6cc8b1e73 |
| habitacion_314 (Gm) | melancholic | == golden full | a19cc9fa6b45d2e2 | 7433a0f98558d322 |
| calles_de_neon (Am, material respetado) | familiar_pop | == golden full | 988ee7783915e8be | c0ac40acd9c195d6 |

(+ `D_familiarity_auto` en nocturno y casa_de_espejos.) Los 5 A son
byte-idénticos a los `full.mid` de FASE 6 — la biblioteca no contamina el
camino base. Elección de arquetipos: nocturno→CINE01/02/04/05,
medianoche→DREAM07, casa→SOUL05/06, habitación→MEL02,
calles→POP01/02 (solo secciones sin material).

## 6. Cómo reproducir todo desde cero

```bash
cd nucleo_engine_project
python3 -m pytest tests/fase7 tests/fase6 tests/fase5 tests/dmd tests/test_forge.py -q  # 315 passed
python3 manifests/hash_protected.py verify && python3 manifests/verificar_golden.py
python3 scripts/fase7_comparativos.py     # regenera los 17 runs (A debe dar == golden)
python3 /home/z/my-project/scripts/check_biblioteca.py   # 11.264 acordes, 0 fallos
```

## 7. Hallazgos FASE 7 (ver DECISIONS.md para el detalle)

| # | Hallazgo | Estado |
|---|---|---|
| F7-L1 | La calidad por caso del numeral rompe la diatonía si el modo se relaja (p. ej. Fm7 fuera de escala en Am) | RESUELTO: regla diatónica §4.1 |
| F7-L2 | Selección greedy puede repartir 6-7 progresiones en una canción | RESUELTO: cuota 4 + reasignación |
| F7-O1 | El bass de forge sigue RAÍCES: las inversiones `/` colorean voicing de pad/keys, no la línea de bajo (groove estable por diseño) | Documentado |
| F7-O2 | `harmony` en config side-file pasa como clave opaca; `production.py`/`coordinator.py` sin cambios | Por diseño |
| F7-O3 | Familiaridad dentro del tipo garantizada (verse_1==verse_2 en arquetipo); entre repeticiones la seed puede variar el color (extensiones) — es la «variación de repetición» clásica | Por diseño |

## 8. Qué NO debe modificarse (reglas duras heredadas + nuevas)

1-7. Todas las reglas de CHECKPOINT_FASE6 §8 siguen en pie (forge, dorados,
   contrato, perfiles aprobados, doom como default prohibido…).
8. No añadir campos al activador `harmony` sin test + doc.
9. No subir la cuota `CUOTA_DISTINTAS` sin evidencia de escucha.
10. No conectar `harmony` al camino `original` (diseño: ORIGINAL es inviolable).

## 9. Próxima misión recomendada

1. **Escucha del paquete FASE 7** (`output/fase7_comparativos/`) → decidir si
   la biblioteca entra en producción y con qué niveles de variación.
2. Decisión pendiente F6-L1 (density.sax/rhodes) — ver CHECKPOINT_FASE6 §7.
3. **FASE 8** — Producción de álbum según `docs/PROPUESTA_VARIACION_ALBUM.md`
   (album.json side-file + produce.py + chequeos de variedad), ya con la
   biblioteca de familiaridad como recurso de composición. Después: stems/mixdown.
