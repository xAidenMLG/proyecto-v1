# CHECKPOINT FASE 5 — Dark Trip Hop Unification & Musical Engine Expansion

> Documento AUTOCONTENIDO: permite continuar el proyecto en una conversación nueva
> sin depender del historial de Claude/ChatGPT. Fecha de corte: 2026-11-09.

---

## 0. Qué es este proyecto (30 segundos)

**Dark Music Director (DMD)** + **MIDI Forge**: sistema para producir álbumes de Dark Trip Hop
para YouTube, reproducibles y deterministas.

```
dark-director/1 JSON  ──(DMD: dark_director/)──▶  midi-forge/1 JSON  ──(MIDI Forge: forge/)──▶  MIDI/WAV ──▶ Suno
```

- **MIDI Forge** (`forge/`, PROTEGIDO): el único motor. Generadores por rol, voice-leading
  Viterbi, batería por capas, guardrails, writer MIDI.
- **DMD** (`dark_director/`): contrato rev 3.2 (congelado), validador E/W, recetas N1, compilador.
- **jazz_engine/** (FASE 5): motores musicales especializados del universo DARK TRIP HOP
  (única identidad activa; doom archivado).

## 1. Estado canónico

| Componente | Estado |
|---|---|
| Contrato `dark-director/1` rev 3.2 | CONGELADO, intacto (hash en `manifests/protegidos.json`) |
| `dark_director/identities/dark_triphop.py` | CONGELADA (golden de referencia) |
| `forge/` completo + `styles.py` | PROTEGIDOS, 0 cambios (hashes verificados) |
| Identidad ACTIVA | `dark_triphop` |
| Identidades ARCHIVADAS | `doom_triphop`, `doom_dark_jazz` (operables, no recomendadas) |
| Tests | 241 passed, 3 skipped (`pytest tests/fase5 tests/dmd tests/test_forge.py -q`) |
| Comparativos | `output/fase5_comparativos/` — 8 MIDIs + evidencias + RESUMEN.md |

## 2. Mapa de archivos (árbol raíz = `nucleo_engine_project/`)

```
forge/                     # MIDI Forge (PROTEGIDO — no editar)
dark_director/             # DMD
  identities/__init__.py   #   + metadata FASE 5 (IDENTIDAD_ACTIVA / ARCHIVADAS)
jazz_engine/               # FASE 5
  context.py               # Context Analyzer (armonía/drama por sección)
  profiles.py              # Perfiles de identidad (DTH activo; doom archivados)
  motif.py                 # Motif Generator + Development
  improv.py                # Scheduler/Phrase Generator sax + Rhodes behaviors
  drums_engine.py          # Groove batería (transformación pura de proyecto)
  vibes_engine.py          # Vibráfono (params + ecos)
  coordinator.py           # Plan por sección + presets de variación
  enhance.py               # Enriquecimiento puro (sax/drums/vibes)
  render.py                # Orquestación con hooks (OFF == forge byte a byte)
  __main__.py              # CLI JSON-first
tests/
  test_forge.py            # suite forge (34)
  dmd/                     # suite DMD (171)
  fase5/                   # suite FASE 5 (37)
scripts/
  fase5_comparativos.py    # regenera los 8 comparativos
output/fase5_comparativos/ # MIDIs + evidencia
manifests/
  protegidos.json          # SHA256 de congelados (verificar: python manifests/hash_protected.py verify)
  tree_fase5.json          # SHA256 del árbol completo post-FASE 5
backups/                   # originales de archivos modificados
docs/                      # PROJECT_STATE / DECISIONS / NEXT_MISSION / este checkpoint
```

## 3. Comandos esenciales

```bash
cd nucleo_engine_project

# suites completas
python3 -m pytest tests/fase5 tests/dmd tests/test_forge.py -q

# generar MIDI mejorado desde un documento dark-director/1
python3 -m jazz_engine doc.json --dark-director --config config.json -o salida.mid --evidence ev.json

# regenerar los 8 comparativos
python3 scripts/fase5_comparativos.py

# integridad de congelados
python3 manifests/hash_protected.py verify
```

### config.json (side-file; NO es parte del contrato)
```json
{
  "engines": {"sax": true, "rhodes": true, "drums": true, "vibes": true},
  "profile": "auto",
  "seed": 2026,
  "density": {"sax": 1.0, "rhodes": 1.0, "vibes": 1.0, "drums": 1.0},
  "variation": "balanced"
}
```
`variation` ∈ balanced | melodic | atmospheric | groove | sparse.

## 4. API Python (equivalente al CLI)

```python
from dark_director import compilador
import jazz_engine as je

proyecto = compilador.compilar(doc)["proyecto"]
res = je.render.generate(proyecto, config)      # config=None → path ORIGINAL (byte-idéntico a forge)
res.midi                                        # bytes MIDI
res.plan / res.evidence                         # decisiones y evidencia de los motores
```

## 5. Reproducción en Windows (escucha)

1. **MIDI Forge local**: abrir `iniciar.bat` → «Cargar y normalizar» con
   `proyecto_XX.json` (en `output/fase5_comparativos/`) → «Generar».
2. **FluidSynth directo**:
   `fluidsynth -ni "C:\ruta\soundfont.sf2" 07_full.mid -F 07_full.wav -r 44100`
   (los programas GM ya van embebidos: sax 66, rhodes 4, vibes 11, bass 38, pad 91).
3. Cualquier DAW/reproductor MIDI (Windows Media Player no renderiza MIDI bien: usar DAW o FluidSynth).

## 6. Reconciliación con una instalación local (IMPORTANTE)

**Contexto**: este árbol fue trabajado en un sandbox; el código de Fase 3/4
(`jazz_engine/walking_bass.py`, `swing.py`, `render.py`, `improv.py`) NO estaba
presente en el entorno de trabajo, por lo que `jazz_engine` fue RECONSTRUIDO aquí
siguiendo el diseño documentado (respuesta_11 + especificación FASE 4/5).
El resto del árbol (forge/, dark_director/) ES el estado real del usuario.

**Dos caminos válidos:**

- **Camino A (recomendado si el motor local no está modificado a mano):** copiar
  este árbol COMPLETO sobre `nucleo_engine_project/` (conservando `soundfonts/`
  y WAVs locales). Todo es coherente y testeado en conjunto (241 tests).
- **Camino B (si el improv.py local de Fase 4 debe conservarse):** portar solo
  los módulos NUEVOS (`context.py`, `profiles.py`, `motif.py`, `drums_engine.py`,
  `vibes_engine.py`, `coordinator.py`, `enhance.py`, `__main__.py`) y las
  decisiones de `DECISIONS.md` B4–B10 al render local. El perfil DTH
  (`profiles.py::DARK_TRIPHOP`) es puro dato y portable tal cual.

En ambos casos: ejecutar la suite completa y `manifests/hash_protected.py verify`.

## 7. Verificación de integridad (corte FASE 5)

- Congelados: `forge/*`, `dark_triphop.py`, `contract.py` — SIN CAMBIOS (verificado con
  `manifests/protegidos.json`, escrito ANTES de la primera modificación).
- Backups en `backups/`: `identities__init__.fase2_original.py` (único archivo
  preexistente modificado).
- Comparativos: ver `output/fase5_comparativos/RESUMEN.md` (SHA256 de cada MIDI).

## 8. Qué NO hacer (reglas duras del proyecto)

1. No editar `forge/`, `styles.py`, `dark_triphop.py`, `contract.py`.
2. No introducir campos nuevos en el JSON de entrada (E109); los params de motores
   viven en `config.json` (side-file) o en vocabulario midi-forge/1 existente.
3. No generar MIDI fuera de forge (jazz_engine solo emite vocabulario/hooks).
4. No usar perfiles doom como defaults ni recomendaciones.
5. No afirmar calidad musical sin escucha humana.
