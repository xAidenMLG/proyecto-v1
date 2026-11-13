# HARMONY_ARCHITECTURE_AUDIT — Auditoría de los dos modos armónicos de DMD

**Fecha**: 2026-11-09 · **Tipo**: inspección técnica exclusivamente de lectura · **Nada fue modificado**

**Alcance**: `nucleo_engine_project` — contrato dark-director/1 rev 3.2, compilador, motor de
renderizado, biblioteca de familiaridad armónica (FASE 7), sistema de álbumes (FASE 8),
goldens y pruebas. Todos los experimentos se ejecutaron en memoria o en modo `--verify`
(sin escritura); las suites de tests se ejecutaron con su variable de entorno habitual.
Se crearon dos scripts de diagnóstico nuevos bajo `scripts/`
(`audit_armonia_experimento.py`, `sax_diag_bloques.py`) — no tocan ningún archivo existente.

**Convención**: ✅ = hecho comprobado en esta auditoría (código leído, experimento
ejecutado, hash verificado). ⚠️ = hipótesis razonable no probada exhaustivamente.

---

## 0. Resumen ejecutivo

✅ **Existen dos modos armónicos reales y separados**, y la biblioteca de familiaridad
(FASE 7) es una capa adicional estrictamente opcional sobre ellos:

| Modo | Cómo se declara | Fuente de los acordes | Estado |
|---|---|---|---|
| **A — NATIVE HARMONY** | El doc trae `harmony.key` + `harmony.language` y **sin** `progressions` ni `chords` | Receta N1 de la identidad: `dark_triphop.PROGRESIONES[language][type]` instanciada sobre la tónica | ✅ Intacta, determinista, probada |
| **B — GUIDED HARMONY** | El doc trae `harmony.progressions` y/o `structure[].chords` | Esas progresiones explícitas, por precedencia | ✅ Intacta (es como se generó el golden) |
| **FASE 7 (opcional, sobre A o B)** | Side-file/CLI `config['harmony']` con `keyword`/`id`/`progressions` | Biblioteca embebida, reescribe secciones sin material del compositor | ✅ Jamás se activa sola |

✅ El golden de referencia (Nocturno Terminal) se generó en **modo B** (doc con
`harmony.progressions`), no en modo A. La ruta nativa (modo A) está intacta, protegida
por hash y probada. El golden se reproduce **byte-identical hoy** con el código actual
(`VERIFICACION: OK — resultado idéntico`, SHA256 `046c94b1…`).

⚠️ Hallazgo principal de arquitectura (no defecto): el compilador calcula la fuente de
acordes (`explicito | progressions_id | progressions_type | receta_n1`) pero **no la
registra** ni en el proyecto compilado ni en la evidencia — la trazabilidad post-hoc del
modo usado requiere re-compilar. Ver §6 y §8.

---

## 1. Mapa de componentes y funciones responsables

| Componente | Función armónica | Referencia exacta |
|---|---|---|
| `dark_director/contract.py` | Enum de lenguajes: `LANGUAGES = ("pop_dream_pop", "hybrid", "experimental")`; `SECTION_TYPES` (7 types); rev 3.2 | `contract.py:64`, `contract.py:60` |
| `dark_director/validador.py` | Exige `harmony` + `key` + `language` (E103/E105); valida `progressions` (E107 claves, E113 símbolos) y `structure[].chords`; W414 avisa vocabulario fuera de language | `validador.py:212–233`, `:346`, `:350–359`, `:694–704` |
| `dark_director/identities/dark_triphop.py` | **Tabla nativa `PROGRESIONES`** por language × type (pares offset-semitonos + calidad) | `dark_triphop.py:201–240` (hash protegido verificado) |
| `dark_director/identities/doom_triphop.py`, `doom_dark_jazz.py` | Tablas nativas propias (identidades no-predeterminadas) | `doom_triphop.py:394`, `doom_dark_jazz.py:372` |
| `dark_director/compilador.py` | **Único punto de resolución de acordes del doc**: escalera de precedencia §2.8 + `_instanciar_simbolo()` | `compilador.py:380–392`, `:129–131`, `:267–268` |
| `jazz_engine/harmony_library.py` | Biblioteca F7 **embebida en código** (`_BIBLIOTECA_BASE`) + carga opcional externa | `harmony_library.py:491–519` |
| `jazz_engine/harmony_select.py` | `normalizar_activacion()` (valida activación; `None` si no se declara) y `seleccionar()` (keyword/id/progressiones→IDs de biblioteca) | `harmony_select.py:58–…`, `:259–294` |
| `jazz_engine/harmony_adapt.py` | `adaptar()` — adapta la entrada de biblioteca a tónica/modo/chord_bars | llamado desde `harmony.py:108` |
| `jazz_engine/harmony.py` | `aplicar()` — **único escritor de `sections[].chords` post-compilación**; respeta material del compositor | `harmony.py:69–128` (escritura en `:123`) |
| `jazz_engine/render.py` | Punto de activación: solo si `config['harmony'] is not None`; rechaza `original`+harmony | `render.py:45–52` |
| `jazz_engine/coordinator.py` | `normalize_config` — **cero referencias a harmony** (no inyecta nada) | grep: 0 resultados |
| `forge/adapter.py`, `forge/engine.py` | Consumen los acordes ya resueltos (`sections[].chords`); nunca los eligen | hash protegido verificado |
| `album/esquema.py` (FASE 8) | `harmony` por pista solo si el spec la declara; nunca inyecta ni `familiarity_auto`; A113 prohíbe `original`+harmony | `esquema.py:15–16`, `:184–213` |
| `scripts/produce.py` | CLI FASE 6/8: F7 solo con `--harmony*` explícitos | `produce.py:191–217` |
| `jazz_engine/__main__.py` | CLI directo: F7 solo con `--harmony*` o `--config` con `"harmony"`; bloquea conflicto | `__main__.py:76–90` |

---

## 2. Flujo de resolución armónica (orden real de ejecución)

```
Documento dark-director/1 (JSON)
        │
        ▼
[1] validador.validar()                        (validador.py)
    harmony obligatorio: key + language (E103/E105)
    progressions/chords opcionales, validados si presentes
        │
        ▼
[2] compilador.compilar()  ── ESCALERA §2.8 ── (compilador.py:380–392)
    por cada sección, elige la FUENTE de acordes:
      1) structure[].chords            → "explicito"
      2) harmony.progressions[sid]     → "progressions_id"
      3) harmony.progressions[type]    → "progressions_type"
      4) else: receta nativa           → "receta_n1"
         dark_triphop.PROGRESIONES[language][type]
         → _instanciar_simbolo(tonic_pc, offset, calidad)  [:129]
    (la variable fuente_acordes NO se registra en el proyecto ni en el informe)
        │
        ▼
[3] render.generate(proyecto, config)          (render.py:28–97)
    ┌─ config['harmony'] is None ──► NO se toca la armonía. Fin de la historia.
    └─ config['harmony'] presente:
         production='original' → ValueError (ORIGINAL no admite biblioteca)
         si no: normalizar_activacion() → harmony.aplicar()
                reescribe sections[].chords SOLO en secciones SIN material
                del compositor (respetar_material=True por defecto)   (harmony.py:96–99)
        │
        ▼
[4] forge (adapter/engine) ──► MIDI
    consume chords ya resueltos; parsea símbolos; no decide nada armónico
```

✅ Verificado experimentalmente (`scripts/audit_armonia_experimento.py`, todo en memoria):
- **Caso A (nativo)**: doc con `key: "A minor"`, `language: "hybrid"`, sin `progressions`
  ni `chords` → `verse = [Am9, Fmaj7, Cm7b5, E9]`, `chorus = [Am9, Gm9, F13, E7sus4]`,
  `intro = [Am9]`, `outro = [Am9]` — coincidencia exacta con la tabla nativa instanciada.
  Determinista (sin RNG en esta etapa).
- **Caso B (guiado)**: `harmony.progressions['verse'] = [Am9, Em7, Fmaj7, G7sus4]` →
  verse usa lo declarado; intro/chorus/outro siguen la receta nativa (mezcla por sección).
- **Caso C (precedencia)**: `structure[].chords` gana sobre `harmony.progressions`.
- **Caso D**: `enhance` sin `config['harmony']` → evidencia sin clave `harmony`, acordes
  nativos intactos. **FASE 7 no se activa sola**.
- **Caso E**: F7 con `keyword: dark_cinematic` reescribe las 4 secciones sin material
  (`CINE01/02/03/07`, adaptadas a A menor); con material escrito las habría respetado.

---

## 3. Campos necesarios para cada modo

### Obligatorios siempre (rev 3.2) ✅
- `schema: "dark-director/1"` (E102), `direction.identity` + `direction.accessibility`
  (E103/E105), `structure` ≥ 2 secciones con `id/type/bars` y `type` ∈ 7 types (E105/E106),
  **`harmony.key`** (E103/E105) y **`harmony.language`** (E103/E105).

### MODO A — NATIVE HARMONY (mínimo)
```json
{
  "schema": "dark-director/1",
  "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
  "global": {"bpm": 84, "seed": 100},
  "harmony": {"key": "A minor", "language": "hybrid"},
  "structure": [ {"id": "intro", "type": "intro", "bars": 4}, … ]
}
```
- ✅ `harmony.progressions` **ausente**, `structure[].chords` **ausente**.
- ✅ No hay que desactivar nada más: la biblioteca F7 es inerte si no se invoca.
- El resto del bloque `harmony` (`resolution`, `harmonic_rhythm_bars`) sigue opcional
  (defaults por language: pop→tonal, hybrid→modal, experimental→chromatic;
  `harmonic_rhythm_bars` → receta `HARMONIC_RHYTHM_BARS`).

### MODO B — GUIDED HARMONY (mínimo)
- Añadir `harmony.progressions` (claves = id de sección o type, valores = símbolos
  parseables por `theory.parse_chord`, E107/E113) **y/o** `structure[].chords` por sección.
- W414: acordes fuera del vocabulario del language se **avisan pero se respetan**.

### FASE 7 (capa opcional sobre A o B) — nunca vía el doc
- Solo por side-file/CLI: `config["harmony"] = {"keyword"|"id"|"progressions"(IDs de
  biblioteca), "seed"?, "variacion"?, "respetar_material"?}`.
- ✅ El doc dark-director/1 **no tiene ningún campo** para activar F7; la activación
  vive fuera del contrato (mecanismo lateral) — el contrato no se modifica.

---

## 4. Comandos exactos

### MODO A — NATIVE (doc sin progressions/chords)
```bash
# camino ORIGINAL puro (delegación 1:1 al motor, sin motores opcionales):
python3 -m jazz_engine docs/mi_tema.json --dark-director -o salida.mid

# camino ORIGINAL explícito vía produce.py (equivalente byte a byte, comprobado):
python3 scripts/produce.py docs/mi_tema.json --production original --seed 2026 --out output/produccion/mi_tema

# con motores opcionales pero armonía NATIVA (sin --harmony):
python3 scripts/produce.py docs/mi_tema.json --production sax --seed 7351 --out output/produccion/mi_tema
```

### MODO B — GUIDED (doc con progressions/chords)
```bash
# mismos comandos que MODO A: la armonía la trae el propio doc (JSON de datos)
python3 scripts/produce.py output/generalizacion_fase6/nocturno_terminal/doc.json \
    --production original --seed 2026 --out output/produccion/nocturno --verify 046c94b1…
```

### FASE 7 opcional (solo si se pide, sobre MODO A o B)
```bash
python3 -m jazz_engine docs/mi_tema.json --dark-director --production full --seed 2026 \
    --harmony dark_cinematic --harmony-variacion medium -o salida.mid
python3 -m jazz_engine docs/mi_tema.json --dark-director --harmony-id CINE01 -o salida.mid
python3 scripts/produce.py docs/mi_tema.json --production sax --seed 2026 \
    --harmony melancholic --harmony-variacion subtle --out output/produccion/mi_tema
# o vía --config config.json con {"harmony": {...}} (bloquea conflicto con --harmony*)
```

### Reglas de protección ✅
- `production='original'` + harmony → **rechazo explícito** (`render.py:46–49`,
  `esquema.py A113`, `harmony_select` exige dict no vacío).
- `produce.py` sin `--harmony` → `config['harmony']` nunca existe → F7 inerte.

---

## 5. Respuestas a las 12 preguntas (hechos vs hipótesis)

1. **¿Dónde está el comportamiento nativo?** ✅ Tabla `PROGRESIONES` de la receta N1 de
   la identidad (`dark_triphop.py:201`; también `doom_triphop.py:394`,
   `doom_dark_jazz.py:372`) + instanciación en `compilador.py` (`_instanciar_simbolo`,
   rama `receta_n1` de la escalera §2.8).
2. **¿Qué genera acordes sin progresiones?** ✅ La receta N1: pares (offset, calidad) por
   `(language, type)` instanciados sobre la tónica de `harmony.key`. Determinista; el
   mismo `type` recibe siempre la misma progresión (p. ej. verse_1 y verse_2 comparten
   progresión si ambos son type verse).
3. **¿Campos armónicos obligatorios?** ✅ `harmony.key` y `harmony.language` (E103);
   `harmony` ausente → E103. Opcionales: `resolution`, `harmonic_rhythm_bars`,
   `progressions`; `structure[].chords`/`chord_bars` también opcionales.
4. **¿Se pueden omitir progressions y chords?** ✅ Sí, sin error. La ausencia **no**
   significa ausencia de armonía: cae a `receta_n1` (comprobado en el experimento A).
5. **¿Qué sucede internamente sin esos campos?** ✅ Rama `else` de la escalera
   (`compilador.py:391`): acordes = receta nativa instanciada; `chord_bars` =
   `section.chord_bars` o `harmony.harmonic_rhythm_bars` o receta (línea 393).
6. **¿Precedencia real?** ✅ `structure[].chords` > `progressions[sid]` >
   `progressions[type]` > receta N1. Posteriormente F7 puede reescribir (solo secciones
   sin material, solo si se activa). Único escritor post-compilación:
   `harmony.py:123`. W414 respeta acordes fuera de vocabulario.
7. **¿F7 accidental?** ✅ No, por 4 vías independientes: `normalizar_activacion(None)→None`
   y exige dict explícito; `render.generate` solo entra si `config['harmony'] is not None`;
   `coordinator.normalize_config` no menciona harmony (0 referencias); `album/esquema.py`
   jamás inyecta harmony ni `familiarity_auto`. ⚠️ El único escenario hipotético de
   activación involuntaria sería un `--config` JSON que ya traiga `"harmony"` dentro —
   eso sigue siendo una declaración explícita del usuario.
8. **¿Nativo idéntico a Golden Path?** ✅ La **ruta nativa** está intacta:
   `dark_triphop.py` con hash verificado (protegido), tabla completa probada
   (`test_receta_n1.py`), escalera sin cambios. ⚠️ **Matiz histórico comprobado**: el
   golden Nocturno Terminal se generó en modo **B** (su doc trae
   `harmony.progressions`, language pop_dream_pop, key D minor) — "Golden Path = modo
   nativo" es una hipótesis incorrecta según el doc conservado; el Golden Path demuestra
   la ruta guiada, y la ruta nativa coexiste intacta desde Fase 1.
9. **¿Comandos de cada modo?** ✅ §4. La armonía la decide **el doc** (A: sin
   progressions; B: con ellas); F7 siempre con flag/config explícito.
10. **¿Diferencias directa vs produce.py?** ✅ Mismo `compilador.compilar` + mismo
    `render.generate`; la resolución armónica es idéntica. Diferencias de empaquetado:
    produce.py exige `--out` y escribe paquete completo (doc.json, config_efectiva,
    evidencia, índice) y su `--production` por defecto es `full` (no original); el CLI
    directo sin flags delega 1:1 en el motor (`render.generate(proyecto, None)`). Con
    `--production original`, produce.py reproduce el camino ORIGINAL byte-identical
    (comprobado con `--verify`).
11. **¿Qué evidencias verifican la conservación?** ✅ §7: manifiestos de hashes (11/11
    protegidos, 34/34 golden), reproducción byte-identical con código actual, 321 tests
    OK (incl. test_receta_n1 de la tabla nativa, test_golden byte a byte, 56 de FASE 7).
12. **¿Álbum con progresión distinta por canción sin tocar el contrato?** ✅ Sí — es
    puro dato JSON: cada doc de pista declara sus propias `harmony.progressions` o
    `structure[].chords` (precedencia resuelta por doc). El sistema FASE 8 ya lo hace:
    `albumes/noches_largas/docs/*.json` traen progressions propias por pista y el spec
    activa F7 solo donde se pide (`armonia`/`harmony` por pista; nunca inyectada).
    El contrato rev 3.2 no necesita ningún cambio.

---

## 6. Riesgos de regresión (identificados, NO corregidos)

| # | Riesgo | Naturaleza | Mitigación actual |
|---|---|---|---|
| R1 | `fuente_acordes` no se registra en proyecto ni evidencia | Observabilidad | Ninguna post-hoc; requiere re-compilar para diagnosticar el modo usado |
| R2 | Biblioteca F7 embebida en `harmony_library.py` (código) | Integridad | No está en `protegidos.json`; un cambio ahí altera salidas F7 (no afecta al modo A/B del doc) |
| R3 | Nuevo `type` de sección futuro sin fila en `PROGRESIONES` de una receta | Robustez | rompería la ruta nativa para ese type (KeyError); hoy los 7 types están cubiertos y lo garantiza `test_receta_n1.py` |
| R4 | Doc que mezcla: material del compositor + F7 con `respetar_material=false` | Musical | Comportamiento documentado (reescribiría secciones con material); es opt-in explícito |
| R5 | Fallo ambiental del test dmd si se corre sin `DARK_DIRECTOR_AUDIT_MODE=1` | Pruebas | 1 test de `test_forge_link.py` exige la variable; con la variable todo pasa (321 OK) |
| R6 | W414/W403 no bloquean salidas (solo avisan) | Musical | Intencional (precedencia respeta lo declarado); `qa.strict` solo agrava E3xx |
| R7 | Perfiles con motores (sax…) generan frases propias en secciones sin material | Musical | Documentado (Fase 5/6); no altera acordes, solo melodía; el modo A/B queda intacto |

---

## 7. Estado de conservación de Golden Path y evidencias

### Hashes verificados en esta auditoría (cálculo directo, hoy)
- **Protegidos (`manifests/protegidos.json`)**: **11/11 intactos** —
  `dark_director/contract.py` (`77fe4168…`), `dark_director/identities/dark_triphop.py`
  (`6bec25ad…`), los 9 módulos de `forge/` (adapter, engine, styles, theory, validate,
  voicing, audio, midiwriter, `__init__`). Sin divergencias.
- **Goldens FASE 5 (`manifests/golden_fase5.json`)**: **34/34 archivos intactos**,
  incluidos `01_original.mid` = `046c94b1599e34fe…76271f`,
  `07_full.mid` = `3930cadc34ec3bcb…0d7f228`.
- **Reproducción con el código actual**: `produce.py … --production original --seed 2026
  --verify 046c94b1…` → `VERIFICACION: OK — resultado idéntico` (modo verify no escribe
  nada; carpeta de salida quedó vacía). El doc usado es el conservado de FASE 6
  (`output/generalizacion_fase6/nocturno_terminal/doc.json`, cuyo propio original de FASE 6
  ya llevaba el mismo hash del golden).
- **Fuente del golden (modo armónico)**: language `pop_dream_pop`, key `D minor`,
  `harmony.progressions: SÍ` (9 secciones, 0 `structure[].chords`) → golden generado en
  modo B/guiado.

### Pruebas ejecutadas en esta auditoría (lectura; ninguna modificación)
| Suite | Resultado |
|---|---|
| `tests/dmd` (compilador, validador, receta N1, golden, doom, versiones…) | **171 OK** (con `DARK_DIRECTOR_AUDIT_MODE=1`) |
| `tests/fase5` | **37 OK** (skipped=1, preexistente) |
| `tests/fase6` | **18 OK** |
| `tests/fase7` (biblioteca, activación, respeto de material) | **56 OK** |
| `tests/fase8` (álbum) | **39 OK** |
| **Total** | **321 OK, 0 fallos** |

Tests clave para esta auditoría: `test_receta_n1.py::test_progresiones_por_language_y_type_en_vocabulario`
(tabla nativa completa y parseable en los 3 lenguajes × 7 types),
`test_golden.py::test_midi_reproducible_byte_a_byte`,
`tests/fase7/*` (activación explícita y respeto de material).

### Evidencia adicional disponible
- `output/experimentos/sax_register_test/` (entrega previa): config efectiva verificada
  sin `--harmony` → evidencia sin clave `harmony` (F7 inerte con perfil de motores).
- `manifests/tree_fase5/6/7/8.json`, `manifests/verificar_golden.py`,
  `manifests/hash_protected.py`: herramientas de verificación existentes.

---

## 8. Recomendación de arquitectura (sin implementar)

1. **Conservar los dos modos exactamente como están** — la escalera §2.8 ya los
   implementa con separación limpia por precedencia y sin campos nuevos. La coexistencia
   A/B es segura porque ambos se resuelven en la MISMA etapa (compilador) y F7 es una
   capa posterior opt-in.
2. **Cerrar la laguna de trazabilidad (R1)** en una fase futura: registrar la fuente de
   acordes por sección (p. ej. en `meta.director` del proyecto compilado o en la
   evidencia de produce.py) — permitiría verificar post-hoc qué modo usó cada pista de un
   álbum sin re-compilar. Es una adición de *diagnóstico*, no de comportamiento; si se
   hace, debe documentarse en DECISIONS.md y no tocar el contrato público rev 3.2
   (p. ej. vía meta del proyecto midi-forge o evidencia lateral).
3. **Proteger por hash `jazz_engine/harmony_library.py`** (R2): añadirlo a
   `protegidos.json` blindaría la biblioteca frente a ediciones accidentales.
4. **Convención de álbum recomendada**: declarar explícitamente en el spec del álbum qué
   pistas van en modo A (docs sin progressions) y cuáles en modo B (docs con sus
   progresiones), usando F7 solo donde se pida — hoy ya es posible sin ningún cambio;
   la trazabilidad de R1 facilitaría auditarlo.
5. **No introducir un tercer modo**: cualquier necesidad nueva (curva armónica de álbum)
   se resuelve con datos JSON por pista (modo B) o activación F7 por pista, nunca con
   campos nuevos del contrato ni motores adicionales.

---

## 9. Conclusión

✅ El sistema ya tiene los dos modos armónicos independientes que la misión quiere
conservar, **sin que haya que construir nada**: MODO A nativo (receta N1 de la identidad,
protegida por hash y probada), MODO B guiado (progresiones declaradas en el doc, como el
golden), FASE 7 estrictamente opt-in y jamás accidental. El Golden Path se reproduce hoy
byte-identical con el código actual. El único hallazgo relevante es de **observabilidad**
(R1: la fuente de acordes no queda registrada), recomendado como mejora futura — sin
implementar, conforme a las restricciones de esta auditoría.

*Fin del informe — ninguna corrección fue implementada, conforme al encargo.*
