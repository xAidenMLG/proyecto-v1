# ALBUM PRODUCTION SYSTEM — Guía de uso (FASE 8)

> Capa de planificación, orquestación, diversidad, validación y
> reproducibilidad para producir álbumes completos de Dark Trip Hop.
> El álbum ORGANIZA composiciones; NO compone. Los documentos los escribe
> el compositor; esta guía describe cómo especificarlos y ejecutarlos.

---

## 1. El side-file `album.json` (esquema `dmd-album/1`)

Es un side-file (como la config de motores): NO es contrato, no toca
`dark-director/1`. Ejemplo real: `albumes/noches_largas/album.json`.

```json
{
  "schema": "dmd-album/1",
  "album": "Noches Largas",
  "identidad": "dark_triphop",
  "semilla_album": 3100,
  "objetivo": {"pistas": 13},
  "curva_energia": [0.48, 0.59],
  "restricciones": {
    "perfil_frac_max": 0.4,
    "respiro_cada": 5,
    "prohibir_consecutivos_iguales": true
  },
  "pistas": [
    {
      "id": "viaducto_sur",
      "doc": "docs/viaducto_sur.json",
      "titulo": "Viaducto Sur",
      "rol": "clímax 1 — tape_stop final",
      "perfil": "full",
      "seed": 3807,
      "harmony": {
        "id": "CINE01",
        "variacion": "medium",
        "seed": 77
      }
    }
  ]
}
```

Campos por pista: `id` (único, seguro como carpeta), `doc` (dark-director/1,
relativo a album.json), `titulo`/`rol` opcionales (etiqueta narrativa ≤60),
`perfil` (opcional → lo asigna el planificador), `seed` (opcional →
`semilla_album + 101*(índice+1)`), `harmony` (OPCIONAL y EXPLÍCITA:
`id` | `keyword` | `progressions` + `variacion` subtle/medium/rich + `seed`).

Reglas duras del esquema:

1. `identidad` debe ser `dark_triphop` (las doom archivadas se rechazan como
   base de un álbum).
2. `harmony` **nunca** se inyecta: solo viaja si el spec la declara. Y
   `perfil: "original"` + `harmony` es un ERROR (el camino ORIGINAL es
   inviolable). `familiarity_auto` solo funciona como declaración explícita
   del compositor (el sistema avisa W-A3 cuando aparece).
3. Falla rápido (códigos A1xx) con TODOS los errores acumulados, reutilizando
   los validadores reales (`production.nombres()`,
   `harmony_select.normalizar_activacion`, `harmony_library.por_id`).

## 2. Planificación (plan.json, `dmd-album-plan/1`)

`python3 -m album plan <album.json> --out <dir>` — valida, compila cada doc
en seco (detecta documentos inválidos ANTES de producir), extrae un digest
técnico (BPM, tonalidad, compases, secciones, energías), asigna perfiles y
semillas donde faltan, ejecuta los chequeos de diversidad PRE y escribe
`<dir>/plan.json` (contrato de ejecución). Determinista: mismo album.json →
mismo plan.

- Semilla derivada: `seed = semilla_album + 101*(índice+1)` (documentada).
- Asignación de perfil: greedy determinista (no repetir consecutivo, menor
  uso, orden canónico) bajo `perfil_frac_max` y la ventana de respiro. Las
  decisiones explícitas del compositor SIEMPRE ganan; si violan restricciones
  → aviso (W-A4), no error.

Chequeos PRE (avisos, no bloqueos): exceso de perfil (W-A4), ventana sin
respiro (W-A5), consecutivas con perfil+tonalidad+BPM idénticos o perfil
repetido (W-A6), BPM fuera de 76–92 (W-A7), desviación >0.15 de
`curva_energia` (W-A8), documentos con error (W-A9).

## 3. Producción y recuperación

```bash
# plan + producir TODO + informe
python3 -m album producir albumes/noches_largas/album.json \
        --out output/albumes/noches_largas

# reanudar (salta las pistas ok con la misma especificación) — idempotente
python3 -m album producir ... --out ...

# regenerar selectivamente (ids o índices "3", "03")
python3 -m album producir ... --out ... --regen viaducto_sur,10

# producir solo un bloque (no toca el resto del estado)
python3 -m album producir ... --out ... --solo 1,2,3

# regenerarlo TODO
python3 -m album producir ... --out ... --forzar
```

Cada pista vive en `NN_<id>/` con los artefactos oficiales de FASE 6
(`doc.json`, `config_efectiva.json`, `<id>.mid`, `evidencia.json`) generados
por el MISMO núcleo que `scripts/produce.py` (`producir_cancion()`). Fallo de
una pista ≠ fallo del álbum: se registra y se continúa (exit 1 si hubo
fallos).

Estado (`estado.json`, actualizado tras CADA pista):

| Estado | Significado | Comportamiento al reejecutar |
|---|---|---|
| `ok` | producida | SE SALTA (misma especificación) |
| `fallo` | error registrado (con traceback) | se reintenta |
| `pendiente` (razón `cambio_especificacion`) | el doc/perfil/seed/harmony cambió | NO se toca: el resultado aceptado se conserva; hace falta `--regen` |

Archivos del álbum: `plan.json` · `estado.json` · `huellas.json` (huellas
técnicas para similitud) · `informe_album.json/.md` · `manifiesto.json`.

## 4. Informe y manifiesto

`informe_album.md` / `.json`: resultado por pista (perfil, seed, tonalidad,
BPM, duración, SHA256, compliance), diversidad POST (duplicados exactos por
SHA256; similitud material por Jaccard de huellas ≥ 0.85 = «sospechoso»),
coherencia (identidad, tonalidades, BPM de referencia 76–92), curva de
energía objetivo vs real, avisos de planificación, y la separación explícita
**técnico vs musical** (lo medido nunca sustituye la escucha humana).

`manifiesto.json` (`dmd-album-manifiesto/1`): versiones, `semilla_album`,
por pista la config efectiva + hashes doc/MIDI + el comando exacto de
regeneración con `--verify <sha>`; comando de regeneración completa del
álbum. Regla de oro: **mismo album.json → mismos MIDIs byte a byte**
(verificado en la suite FASE 8 y en la producción real de 13 pistas).

## 5. Arquitectura (módulos)

```
album/
  esquema.py      dmd-album/1 + validación fail-fast (A1xx)
  planificador.py plan determinista: digests, perfiles, semillas, PRE (A2xx)
  diversidad.py   métricas PRE (docs) y POST (huellas MIDI), umbrales
  orquestador.py  ejecución por pista vía produce.producir_cancion,
                  estado.json, resume/regen/solo, aislamiento de fallos
  informe.py      informe_album.json/.md + manifiesto.json
  __main__.py     CLI: plan | producir | informe | estado
scripts/produce.py núcleo expuesto como producir_cancion() (CLI idéntico)
scripts/fase8_componer_album.py  flujo compositivo del álbum demo (13 docs)
tests/fase8/     39 pruebas (esquema, plan, orquestación, diversidad,
                 determinismo, integración, regresión)
manifests/tree_fase8.json  snapshot de árbol de la fase
```

Dependencia en una sola dirección: `album/` → `dark_director` + `jazz_engine`
+ `scripts/produce.py`. `forge/`, `styles.py`, `dark_triphop.py`,
`contract.py`: SIN cambios (verificados por `manifests/hash_protected.py`).

## 6. Limitaciones honestas

1. **Sin escucha**: el sandbox no tiene FluidSynth ni soundfonts. Todo
   juicio musical del álbum está PENDIENTE de escucha del usuario (la
   sección «Técnico vs musical» del informe lo lista).
2. La similitud Jaccard es una métrica TÉCNICA de material (rejilla+pista+
   clase de altura): 0.85+ indica «misma música casi segura», no mide
   calidad.
3. El orden de reproducción es el del spec (las pistas se ejecutan en orden);
   la naturalidad de las transiciones es un juicio de escucha.
4. El álbum no genera documentos: si falta o rompe un doc, esa pista queda
   en fallo y el resto se produce (W-A9 lo señala en el plan).
