# REFERENCIAS DORADAS — FASE 5 (congeladas en FASE 6)

> Composición: **Nocturno Terminal** · D minor · 86 BPM · 52 compases · 145.1 s · seed 2026.
> Escuchadas y **APROBADAS por el usuario** durante FASE 5 (validación auditiva en Windows).
> Estas referencias son INMUTABLES: ningún experimento puede modificarlas.
> Los nuevos resultados se escriben en `output/generalizacion_fase6/` u otras ubicaciones experimentales.
> Verificación: `python3 manifests/verificar_golden.py` (manifiesto `manifests/golden_fase5.json`).

| # | Escenario | Perfil FASE 6 | SHA256 completo | Estado |
|---|---|---|---|---|
| 01 | 01_original | `original` | `046c94b1599e34fed228e6dd997611a27ac46835bc4946632a8cebb96d76271f` | APROBADO (usuario) |
| 02 | 02_sax | `sax` | `ecebb36d94a4499b8f50e8ddc7a2f291402a09f4372247568e9989119ce621fe` | APROBADO (usuario) |
| 03 | 03_sax_rhodes | `sax_rhodes` | `25a6f2234cab102eed50b71fde0d14e86e8a1318a0ac4f493a62598767e5ce47` | APROBADO (usuario) |
| 04 | 04_drums | `drums` | `cf4ebc9db2cd8b8a976b64a0861bdb4d149936266201e6dfc2fda465eb3eee89` | APROBADO (usuario) |
| 05 | 05_sax_rhodes_drums | (`full` − vibes) | `04fb03b87ab4314b74e78ffad8d008bfba10a326fe56e2d4de1a102ff991a383` | referencia técnica intermedia |
| 06 | 06_sax_vibes | `sax_vibes` | `98dd0b576b2466cf9a529960af379a6aa7f0ff4bcdd35526b2656faf5e824355` | APROBADO (usuario) |
| 07 | 07_full | `full` | `3930cadc34ec3bcb4dc2cab9788122aa64fdbec2adf10b17b807366e70d7f228` | APROBADO (usuario) |
| 08 | 08_variation_atmospheric | `atmospheric` | `864b9302591f2655fdcdee6f3128a9b5f82464cea5b143959eb4e1e62fd18d57` | APROBADO (usuario) |

## Descripción del comportamiento validado (evaluación del usuario, FASE 5)

- **01_original** — «Excelente composición. Los músicos parecen libres, todo se complementa, tiene
  mood, emoción y personalidad. No se percibe mecánica ni sobrecarga.» Además: **4 iteraciones
  satisfactorias en Suno** a partir de esta referencia. Es la referencia fundamental.
- **02_sax** — «Sax lead natural, con frases memorables, respiración y desarrollo. No parece forzado.»
- **03_sax_rhodes** — «El sax lidera y el Rhodes responde. Diálogo musical, arreglos, escaladas
  melódicas sutiles y complementariedad.»
- **04_drums** — «Batería con presencia y redobles. Colabora con la melodía sin convertirse en
  protagonista permanente. Desarrollo controlado, sin improvisación excesiva.»
- **05_sax_rhodes_drums** — referencia técnica intermedia para combinaciones de motores.
- **06_sax_vibes** — «Mantiene el universo. Parecido a sax; el sax cuenta la historia con mayor
  personalidad.»
- **07_full** — «Todos los instrumentos toman protagonismo en distintos momentos. No son capas
  ordenadas por volumen: músicos que comparten escenario con roles propios. Resultado aprobado.»
- **08_variation_atmospheric** — «Comportamiento diferente. Más desarrollo instrumental, breakdowns
  y libertad. Freestyle / improvisación controlada que conserva el universo musical. Aprobado.»

## Dos comportamientos musicales dentro de Dark Trip Hop (NO dos identidades)

- **MOOD** (01–07): continuidad emocional, complementariedad, desarrollo orgánico, intervenciones
  contenidas. La música lleva al oyente.
- **ATMOSPHERIC** (08): mayor libertad instrumental, desarrollo individual, breakdown y variación
  estructural, improvisación controlada — sin perder identidad, groove ni continuidad.

## Archivos por escenario (mismo directorio)

`<escenario>.mid` · `proyecto_<escenario>.json` (proyecto compilado) · `config_<escenario>.json`
(config exacta de motores; 01 no tiene: camino ORIGINAL) · `evidencia_<escenario>.json`
(hash, métricas, evidencia de motores, compliance) · `doc.json` (documento dark-director/1 común,
seed 2026) · `RESUMEN.md` (tabla comparativa).

## Regeneración byte-idéntica (verificada en FASE 6)

```bash
python3 -m jazz_engine output/fase5_comparativos/doc.json --dark-director \
    --production <perfil> --seed 2026 -o /tmp/regen.mid
# SHA256(/tmp/regen.mid) == hash de la tabla (para 05: --production full --config con vibes:false)
```
