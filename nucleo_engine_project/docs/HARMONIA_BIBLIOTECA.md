# Biblioteca de Familiaridad Armónica — Guía de uso (FASE 7)

> Har­monic Familiarity Engine: progresiones armónicas FAMILIARES (arquetipos
> recurrentes de la música popular) adaptadas a la tonalidad/modo reales de tu
> composición Dark Trip Hop, sin tocar el contrato `dark-director/1` rev 3.2
> ni los perfiles de producción aprobados.

---

## 1. Activación en 10 segundos

```bash
# por keyword (estrategia de búsqueda):
python3 -m jazz_engine doc.json --dark-director --production full --seed 2026 \
    --harmony dark_cinematic --harmony-variacion medium -o tema.mid

# por ID (una progresión concreta de la biblioteca):
python3 -m jazz_engine doc.json --dark-director --harmony-id CINE01 -o tema.mid
```

O por side-file de config (mismo mecanismo que los perfiles; NO se añaden
campos al contrato):

```json
{
  "production": "full",
  "seed": 2026,
  "harmony": {
    "keyword": "melancholic",
    "seed": 77,
    "variacion": "medium",
    "respetar_material": true
  }
}
```

```bash
python3 -m jazz_engine doc.json --dark-director --config config.json -o tema.mid --evidence ev.json
```

Sin la clave `harmony`, el pipeline es **byte a byte** el de FASE 6 (verificado
por tests contra los hashes dorados).

## 2. Keywords disponibles

| Keyword | Busca en | Carácter |
|---|---|---|
| `familiar_pop` | familiaridad_pop | el eje pop y sus rotaciones, doo-wop, ii–V–I |
| `melancholic` | melancolia_nostalgia | andaluza, plagales con iv, descensos |
| `nostalgic` | melancolía + pop | familiaridad alta, tensión baja-media |
| `dark_cinematic` | oscuridad_cinematografica | i–VI–III–VII, frigio, tráiler |
| `dream_pop` | dream_pop_alternative | sus2/sus4, préstamos, estática |
| `alternative` | dream_pop + pop | híbrido abierto |
| `soulful` | soul_rnb | séptimas/9as, turnarounds, amen gospel |
| `emotional_resolution` | cualquier familia con resolución ≥ 0.65 | cierres |
| `tension_release` | estrategia: tensión en builds, resolución en coros | arco |
| `familiarity_auto` | toda la biblioteca, ponderada por el contexto DMD | automático |

`familiarity_auto` puntúa por familiaridad + afinidad de tensión con el
recorrido emocional REAL declarado en DMD (`energy`/`tension` por sección) +
resolución por tipo + transición de raíces entre secciones.

## 3. Niveles de variación

| Nivel | Qué hace |
|---|---|
| `none` | el arquetipo puro, tal cual (máxima familiaridad) |
| `subtle` (default) | extensiones de color según familia (m9, add9, 7sus4…) |
| `medium` | + sus en dominantes, 1 inversión de paso, 1 sustitución diatónica, intercambio modal ocasional, resolución deceptiva en final |
| `rich` | + cola de aproximación a la sección siguiente (V7/x o paso diatónico, a medio compás), intercambio modal frecuente |

Presupuestos congelados por nivel: subtle 0 estructurales/2 extensiones ·
medium 2/3 · rich 3/4. El **primer acorde nunca cambia de raíz** (ancla de
reconocimiento) y la **huella del arquetipo** (movimiento de raíces) se mide y
queda en la evidencia.

## 4. Opciones de la activación

| Clave | Default | Significado |
|---|---|---|
| `keyword` | — | estrategia de búsqueda (uno de keyword o id) |
| `id` | — | progresión concreta (p. ej. `CINE01`; se aplica a todos los tipos) |
| `progressions` | — | pins por tipo: `{"verse": "MEL02", "chorus": "SOUL04"}` |
| `seed` | seed de motores | semilla de la biblioteca (elige variaciones) |
| `variacion` | `subtle` | none \| subtle \| medium \| rich |
| `respetar_material` | `true` | secciones con material escrito del compositor conservan su armonía original |

Errores con mensaje claro: keyword desconocido (lista los válidos), ID
desconocido, claves desconocidas, `production: "original"` + harmony
(el camino ORIGINAL no se modifica nunca).

## 5. La biblioteca (44 progresiones, 6 familias)

`POP01–08` eje pop y clásicos · `MEL01–06` melancolía/nostalgia ·
`CINE01–08` oscuridad cinematográfica · `DREAM01–08` dream pop/alternativo ·
`SOUL01–08` soul/R&B · `BAL01–06` balada cinematográfica.

Cada entrada declara: ID, nombre, keywords, familia, función armónica, modo,
grados, emociones, familiaridad (0-1), tensión (0-1), resolución (0-1),
estructura compatible, variaciones disponibles, ritmo armónico sugerido,
referencias honestas y `tipo_ref` (`arquetipo_documentado` |
`arquetipo_genero` | `variacion_original`). **No hay melodías, riffs ni
atribuciones dudosas**: solo secuencias de grados funcionales.

Ver el catálogo completo con grados y referencias en
`jazz_engine/harmony_library.py` (es dato, se lee solo).

## 6. Cómo AÑADIR progresiones SIN tocar el motor

1. Crea un JSON (mismo esquema que las entradas de `harmony_library.py`):

```json
{
  "progressiones": [
    {
      "id": "MISM03",
      "nombre": "Mi hallazgo de estudio",
      "keywords": ["melancholic", "mi_sello"],
      "familia": "melancolia_nostalgia",
      "funcion": "descenso de tónica con subdominante menor",
      "modo": "menor",
      "grados": ["i", "VII", "iv", "V7"],
      "emociones": ["hondo", "nocturno"],
      "familiaridad": 0.5,
      "tension": 0.55,
      "resolucion": 0.7,
      "estructura": ["verse", "chorus", "outro"],
      "variaciones": ["extensiones", "sus_flavor", "colas_extra"],
      "ritmo": 1,
      "referencias": "variación propia sobre la cadencia andaluza",
      "tipo_ref": "variacion_original"
    }
  ]
}
```

2. Pásalo con `HL.biblioteca("mi_archivo.json")` en scripts propios, o
   añádelo a `_BIBLIOTECA_BASE` si quieres integrarlo oficialmente (un commit
   de datos, cero cambios de motor).

Reglas del esquema (validadas al cargar, error claro si fallan):
- `id`: `MAYUSCULAS_CON_GUION`, único.
- `grados`: 2–8 tokens `[b#]?NUMERAL[sufijo][/3|/5|/7]`; numerales I–VII en un
  solo caso (mayúscula = intención mayor, minúscula = menor); sufijos válidos:
  `7 9 11 13 6 maj7 maj9 sus4 sus2 add9 add2 dim dim7 m7b5 aug 5 7sus4`.
- `variaciones`: solo del vocabulario cerrado (`VOCABULARIO_VARIACIONES`).
- `estructura`: tipos del contrato (`intro verse pre_chorus chorus bridge break outro`).
- `ritmo`: 1 o 2 (compases por acorde sugeridos).
- Sin melodías: los grados SON la entrada completa.

La calidad real de cada acorde la decide la ESCALA de la composición
(diatonía garantizada; excepciones documentadas: V/VII mayor en menor =
dominante armónica/bVII, y el caso del numeral cuando el modo del arquetipo
coincide con el de la composición).

## 7. Reglas de convivencia (lo que NO cambia)

- Contrato `dark-director/1` rev 3.2: intacto (0 campos nuevos).
- `forge/`, `styles.py`, `dark_triphop.py`, `contract.py`: intactos (verificados por hash).
- Los 7 perfiles de producción sin `harmony`: byte-idénticos (test regenera 01 y 07).
- Secciones con material del compositor (p. ej. versos/coro escritos de
  `calles_de_neon`): su armonía NO se reescribe (el material protegido jamás
  se arriesga); aparece en `evidencia.armonia.respetadas_material`.
- Cuota de recurrencia: máximo 4 progresiones distintas por canción
  (`CUOTA_DISTINTAS`); una canción real vive de 2-4 progresiones.

## 8. Producción reproducible

```bash
python3 scripts/produce.py doc.json --production full --seed 2026 \
    --harmony dark_cinematic --harmony-variacion medium \
    --harmony-seed 77 --out output/produccion/mi_tema
# evidencia.json incluye el bloque "harmonia" (elección, resumen, respetadas)
# regenerar y comparar:
python3 scripts/produce.py doc.json --production full --seed 2026 \
    --harmony dark_cinematic --harmony-variacion medium --harmony-seed 77 \
    --out output/produccion/mi_tema --verify <sha256>
```

## 9. Escucha de los comparativos FASE 7

`output/fase7_comparativos/` — por composición: `A_original` (sin biblioteca,
== FASE 6), `B_familiar_<kw>` (progresión familiar pura), `C_transformado_<kw>`
(la MISMA progresión transformada, rich), y `D_familiarity_auto` en dos
composiciones. Comandos de regeneración exacta dentro de cada
`evidencia_*.json`. En Windows:
`fluidsynth -ni soundfont.sf2 ARCHIVO.mid -F out.wav -r 44100`.

La validación musical te corresponde a ti: ningún test declara calidad musical.
