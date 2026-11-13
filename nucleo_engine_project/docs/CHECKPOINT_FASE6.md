# CHECKPOINT FASE 6 — Production Profiles & Musical Generalization

> Documento AUTOCONTENIDO: permite continuar el proyecto en una conversación nueva
> sin depender del historial. Fecha de corte: 2026-11-09. Sucesor de CHECKPOINT_FASE5.md.

---

## 0. Qué es este proyecto (30 segundos)

**Dark Music Director (DMD)** + **MIDI Forge**: sistema para producir álbumes de Dark Trip Hop
para YouTube, reproducibles y deterministas.

```
dark-director/1 JSON ──(DMD: dark_director/)──▶ midi-forge/1 JSON ──▶ [jazz_engine: motores OPCIONALES] ──▶ MIDI Forge (forge/) ──▶ MIDI/WAV ──▶ Suno
```

- **MIDI Forge** (`forge/`, PROTEGIDO): el único motor MIDI. jazz_engine NO duplica nada.
- **DMD** (`dark_director/`): contrato `dark-director/1` rev 3.2 (CONGELADO), validador, recetas, compilador.
- **jazz_engine/** (FASE 5/6): motores musicales del universo DARK TRIP HOP (única identidad activa;
  doom archivado) + perfiles de producción.
- Objetivo: biblioteca musical de YouTube con identidad consistente y diversidad de composición.

## 1. Estado canónico (corte FASE 6)

| Componente | Estado |
|---|---|
| Contrato `dark-director/1` rev 3.2 | CONGELADO, intacto (`manifests/protegidos.json`) |
| `forge/` completo + `styles.py` | PROTEGIDOS, 0 cambios |
| `dark_director/identities/dark_triphop.py` | CONGELADA (golden FASE 1) |
| Identidad activa | `dark_triphop` (doom_* ARCHIVADAS, operables) |
| Referencias doradas FASE 5 | 8 MIDIs INMUTABLES, hashes verificados (`GOLDEN.md`, `manifests/golden_fase5.json`) |
| Perfiles de producción | 7 (`jazz_engine/production.py`), regeneran los 8 dorados byte-idénticos |
| Matriz de generalización | 5 composiciones × 6 perfiles (+2 sax_vibes) = 32 runs, 0 fallos, deterministas |
| Tests | **259 passed, 3 skipped** (`tests/fase6 tests/fase5 tests/dmd tests/test_forge.py`) |
| Validación musical | **PENDIENTE DEL USUARIO** (paquete auditivo listo) |

## 2. Mapa de archivos (raíz = `nucleo_engine_project/`)

```
forge/                     # MIDI Forge (PROTEGIDO — no editar)
dark_director/             # DMD (contrato/validador/compilador/recetas/identidades)
jazz_engine/               # motores musicales + perfiles
  context.py               #   armonía/energía/tensión por sección
  profiles.py              #   perfiles de IDENTIDAD (DTH activo; doom archivados)
  production.py            #   FASE 6: perfiles de PRODUCCIÓN (presets de config)
  motif.py / improv.py     #   motivos, frases sax (lead.phrases), Rhodes (behaviors A–E)
  drums_engine.py          #   groove batería (transformación pura del proyecto)
  vibes_engine.py          #   vibráfono (params + ecos en huecos del sax)
  coordinator.py           #   plan por sección + presets de variación + normalize_config
  enhance.py / render.py   #   enriquecimiento puro + orquestación con hooks de buffer
  __main__.py              #   CLI (--dark-director, --config, --production, --seed)
tests/fase6/               # 18 tests FASE 6 (golden, perfiles, generalización, regresión)
tests/fase5/ tests/dmd/ tests/test_forge.py
scripts/
  fase6_generalizacion.py  # regenera la matriz + sobreajuste
  fase6_paquete_auditivo.py# reensambla el paquete de escucha
  produce.py               # CLI de producción (generar + evidencia + --verify)
  fase5_comparativos.py    # regenera los 8 comparativos (NO tocar los existentes)
output/
  fase5_comparativos/      # REFERENCIAS DORADAS (INMUTABLES) + GOLDEN.md
  generalizacion_fase6/    # matriz 5×6 + evidencia + checks + sobreajuste
  fase6_paquete_auditivo/  # 9 MIDIs + README (guía de escucha) + hashes.json
  produccion/              # salidas de scripts/produce.py + INDICE.md
manifests/
  protegidos.json          # hashes de código congelado (hash_protected.py verify)
  golden_fase5.json        # hashes de referencias doradas (verificar_golden.py)
  tree_fase6.json          # SHA256 del árbol completo post-FASE 6
backups/                   # originales de archivos modificados (convención *.faseN_original.py)
docs/                      # PROJECT_STATE, DECISIONS, NEXT_MISSION, CHECKPOINT_FASE6, PROPUESTA_VARIACION_ALBUM
```

## 3. Perfiles de producción (FASE 6)

| Perfil | Motores | Reproduce | Uso |
|---|---|---|---|
| `original` | NINGUNO (normalize+generate) | 01_original | la base aprobada; nunca depende de motores |
| `sax` | sax | 02_sax | lead con personalidad |
| `sax_rhodes` | sax+rhodes | 03_sax_rhodes | diálogo |
| `drums` | drums | 04_drums | groove (seed no le afecta: transformación pura) |
| `sax_vibes` | sax+vibes | 06_sax_vibes | sax + destellos |
| `full` | todos | 07_full | protagonismo distribuido |
| `atmospheric` | todos + variation atmospheric | 08_variation_atmospheric | libertad controlada, breakdowns |

```bash
# CLI directa
python3 -m jazz_engine doc.json --dark-director --production full --seed 2026 -o tema.mid --evidence ev.json
# producción reproducible con evidencia completa
python3 scripts/produce.py doc.json --production full --seed 2026 --out output/produccion/mi_tema
# regenerar y comparar contra un resultado anterior
python3 scripts/produce.py doc.json --production full --seed 2026 --out output/produccion/mi_tema --verify <sha256>
```

En config JSON: `{"production": "full", "seed": 2026}` — el preset es BASE y la config
explícita gana clave a clave. Perfil desconocido → ValueError con lista de válidos.
`original` + overrides de motores → ValueError.

## 4. Comandos esenciales

```bash
cd nucleo_engine_project
python3 -m pytest tests/fase6 tests/fase5 tests/dmd tests/test_forge.py -q   # suite completa
python3 manifests/hash_protected.py verify      # código congelado
python3 manifests/verificar_golden.py           # referencias doradas
python3 scripts/fase6_generalizacion.py         # regenera matriz (escribe SOLO en generalizacion_fase6)
python3 scripts/fase6_paquete_auditivo.py       # reensambla paquete de escucha
python3 scripts/produce.py ...                  # producción
```

## 5. Referencias doradas (hashes completos en GOLDEN.md / manifests/golden_fase5.json)

01_original `046c94b1…` · 02_sax `ecebb36d…` · 03_sax_rhodes `25a6f223…` · 04_drums `cf4ebc9d…` ·
05_sax_rhodes_drums `04fb03b8…` · 06_sax_vibes `98dd0b57…` · 07_full `3930cadc…` ·
08_variation_atmospheric `864b9302…` — todas APROBADAS por el usuario (escucha FASE 5).
Regeneración byte-idéntica verificada vía perfiles de producción (seed 2026, doc.json del directorio).

## 6. Generalización (qué se probó)

5 composiciones dark_triphop válidas (`output/generalizacion_fase6/<id>/doc.json`, `PORQUE.txt`):
- **nocturno_terminal** (Dm, 86, 52c) — baseline contra dorados.
- **medianoche_puerto_nuevo** (F#m, 78, 60c, chord_bars 2) — groove lento, espacio, forma larga.
- **calles_de_neon** (Am, 92, 36c, hybrid) — material ESCRITO denso en 3 secciones (respetado),
  estructura corta, tempo rápido.
- **habitacion_314** (Gm, 80, 64c, 10 secciones) — tensión alta, break limitado, tape_stop (semitones ENTERO 1–12).
- **casa_de_espejos** (Cm, 84, 44c, resolución deceptive) — sax NUNCA en focus (protagonismo Rhodes/vibes).

Verificaciones por run (checks en `evidencia_<perfil>.json`): compliance sin fails, notas dentro
de límites (arranques), coherencia armónica del lead ≥70% en tonos/escala, Rhodes en registro y
sin pisar al sax, ecos del vibes solo tras frases del sax y en registro, fills de batería solo en
build, cuota de interacción Rhodes ≤1, sin triple-melodía salvo clímax, determinismo, y variación
con seed+1 (sax/rhodes/vibes). **Resultado: 32/32 sin fallos.** Sobreajuste: sin fórmulas
congeladas entre composiciones (`sobreajuste.md`).

## 7. Hallazgos congelados / limitaciones (LEER ANTES DE TOCAR)

1. **F6-L1**: `density.sax`/`density.rhodes` NO afectan a la actividad de esos motores
   (solo drums/vibes consumen density). CONGELADO porque 02/03/07/08 dorados dependen de ese
   comportamiento. Si algún día se conecta: regenerar comparativos + nueva escucha.
   Test que lo fija: `tests/fase6 ... test_18_f6l1_density_sax_congelado`.
2. **F6-O1**: cola de release final del lead generativo (forge protegido) puede pasar ~1–2 beats
   del fin en estructuras cortas; el validador de forge lo acepta. Sin acción.
3. **F6-O3**: perfil `drums` no cambia con la seed (el azar de layers lo pone forge vía proyecto).
4. Eco del vibes solo donde hay frase del sax (diseño). Presupuesto vibes = ≤40% de secciones
   (se satura por diseño; el echo_prob sigue gateando notas).
5. Sin FluidSynth/soundfonts en el sandbox → sin WAV; validación musical = usuario.
6. `jazz_engine` fue reconstruido en sandbox en FASE 5 (ver CHECKPOINT_FASE5 §Reconciliación).

## 8. Qué NO debe modificarse (reglas duras)

1. No editar `forge/`, `styles.py`, `dark_triphop.py`, `contract.py` (verificar con hash_protected).
2. No modificar `output/fase5_comparativos/` (verificar con verificar_golden tras cualquier
   experimento); resultados nuevos SIEMPRE a ubicaciones experimentales.
3. No añadir campos al JSON de entrada (E109); la config de motores vive en side-file/CLI.
4. No introducir un segundo sistema de configuración (production.py + coordinator son el único).
5. No usar perfiles doom como defaults ni como recomendaciones.
6. No cambiar los perfiles de producción aprobados sin evidencia técnica + plan de escucha.
7. No afirmar calidad musical sin escucha humana.

## 9. Cómo reproducir todo desde cero (nueva máquina)

```bash
cd nucleo_engine_project
python3 -m pytest tests/fase6 tests/fase5 tests/dmd tests/test_forge.py -q   # 259 passed
python3 manifests/hash_protected.py verify && python3 manifests/verificar_golden.py
python3 -m jazz_engine output/fase5_comparativos/doc.json --dark-director \
    --production full --seed 2026 -o /tmp/regen.mid
# sha256(/tmp/regen.mid) debe ser 3930cadc34ec3bcb4dc2cab9788122aa64fdbec2adf10b17b807366e70d7f228
python3 scripts/fase6_generalizacion.py      # regenera la matriz completa
```

## 10. Escucha pendiente (el usuario decide)

Paquete: `output/fase6_paquete_auditivo/README.md` — 9 MIDIs (4 referencias doradas verificadas
+ 5 nuevos en composiciones distintas) con qué comprobar en cada uno.
En Windows: `fluidsynth -ni soundfont.sf2 ARCHIVO.mid -F out.wav -r 44100` o DAW.

## 11. Próxima misión recomendada

FASE 7 — Producción de álbum según `docs/PROPUESTA_VARIACION_ALBUM.md` (album.json side-file +
comando fino sobre produce.py + chequeos de variedad), PREVIA escucha del paquete auditivo y
decisión sobre F6-L1. Después: stems/mixdown para Suno.
