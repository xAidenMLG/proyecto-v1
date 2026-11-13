# Sax Register Test — análisis de alturas reales del sax por sección

**Documento**: `sax_register_test.json` (dark-director/1, sin biblioteca armónica)  
**Perfil**: `sax` — seed `7351` — BPM 84 — 36 compases — 102.9 s  
**MIDI**: `sax_register_test.mid` — SHA256 `c379c40360b4dc100a896b5fa9c92f32428117e766a2f803447f6ef1daeced16`
**Comando**: `python scripts/produce.py sax_register_test.json --production sax --seed 7351 --out output/experimentos/sax_register_test`

## 1. Configuración efectiva verificada

```json
{
  "engines": {
    "sax": true,
    "rhodes": false,
    "drums": false,
    "vibes": false
  },
  "seed": 7351,
  "production": "sax",
  "density": {
    "sax": 1.0,
    "rhodes": 1.0,
    "vibes": 1.0,
    "drums": 1.0
  }
}
```

Coincide con lo exigido: solo el motor sax activo; rhodes/drums/vibes desactivados; seed 7351; perfil `sax`. Sin `--harmony` (sin biblioteca de progresiones familiares, FASE 7).

## 2. Veredicto sobre las alturas

| Verificación | Resultado |
|---|---|
| Notas especificadas en el JSON | 26 |
| Notas de sax en el MIDI | 30 |
| Alturas spec reproducidas **exactamente** | **26/26** |
| Transposiciones / octavaciones / recortes de registro | **0** |
| Notas extra añadidas por el motor | 4 (compás 32, outro) |
| Rango global real | F4–A5 (65–81) — spec: G4–A5 (67–81) |

**Conclusión**: la expansión progresiva de registro diseñada (medio → agudo) llega íntegra al MIDI. El motor **no alteró ninguna altura** del compositor. Las 4 notas extra provienen del mecanismo documentado de FASE 5 (el motor sax improvisa solo en secciones sin material del compositor); no son un defecto.

## 3. Alturas reales por sección

| Sección | Compases | Notas spec | Notas MIDI | Rango real | Media | Registro |
|---|---|---|---|---|---|---|
| intro | 0-3 | 0 | 0 | — | — | bloque apagado (sin sax diseñado) |
| verse_1 | 4-11 | 6 | 6 | 67–74 (G4–D5) | 70.83 | medio — base del diagnóstico |
| pre_1 | 12-15 | 4 | 4 | 72–77 (C5–F5) | 74.75 | medio-agudo — primer ascenso |
| chorus_1 | 16-23 | 8 | 8 | 76–81 (E5–A5) | 78.5 | agudo — clímax previsto |
| verse_2 | 24-27 | 4 | 4 | 69–76 (A4–E5) | 72.75 | medio — retorno controlado |
| chorus_2 | 28-31 | 4 | 4 | 76–81 (E5–A5) | 78.75 | agudo — clímax final |
| outro | 32-35 | 0 | 4 | 65–79 (F4–G5) | 69.5 | gesto de cierre improvisado por el motor |

## 4. Frase spec vs nota real (nota a nota)

Estados: `exacto` = misma altura; la posición real incluye la humanización del motor (jitter de onset ±0.01–0.07 beat, duración ×0.93 por legato 0.93, velocidad ±4).

### verse_1 (compases 4-11)

| Compás | Beat spec | Pitch spec | Pitch real | Posición real | ΔVel | ΔDur | Estado |
|---|---|---|---|---|---|---|---|
| 4 | 0.5 | 67 (G4) | 67 (G4) | bar 4 beat 0.485 | +4 | -0.09 | exacto |
| 5 | 0.0 | 69 (A4) | 69 (A4) | bar 5 beat 0.015 | -2 | -0.12 | exacto |
| 6 | 1.0 | 72 (C5) | 72 (C5) | bar 6 beat 0.994 | -5 | -0.05 | exacto |
| 7 | 0.5 | 71 (B4) | 71 (B4) | bar 7 beat 0.527 | -3 | -0.15 | exacto |
| 9 | 0.0 | 74 (D5) | 74 (D5) | bar 8 beat 3.994 | +4 | -0.15 | exacto |
| 10 | 1.0 | 72 (C5) | 72 (C5) | bar 10 beat 1.021 | +4 | -0.10 | exacto |

### pre_1 (compases 12-15)

| Compás | Beat spec | Pitch spec | Pitch real | Posición real | ΔVel | ΔDur | Estado |
|---|---|---|---|---|---|---|---|
| 12 | 0.0 | 72 (C5) | 72 (C5) | bar 12 beat 0.01 | -2 | -0.07 | exacto |
| 13 | 0.5 | 74 (D5) | 74 (D5) | bar 13 beat 0.562 | +2 | -0.11 | exacto |
| 14 | 0.0 | 76 (E5) | 76 (E5) | bar 14 beat 0.035 | +2 | -0.14 | exacto |
| 15 | 1.0 | 77 (F5) | 77 (F5) | bar 15 beat 1.025 | -2 | -0.10 | exacto |

### chorus_1 (compases 16-23)

| Compás | Beat spec | Pitch spec | Pitch real | Posición real | ΔVel | ΔDur | Estado |
|---|---|---|---|---|---|---|---|
| 16 | 0.0 | 76 (E5) | 76 (E5) | bar 16 beat 0.023 | -5 | -0.09 | exacto |
| 16 | 1.5 | 79 (G5) | 79 (G5) | bar 16 beat 1.527 | -1 | -0.12 | exacto |
| 17 | 0.0 | 81 (A5) | 81 (A5) | bar 17 beat 0.008 | +5 | -0.14 | exacto |
| 18 | 0.5 | 79 (G5) | 79 (G5) | bar 18 beat 0.473 | -4 | -0.04 | exacto |
| 19 | 0.0 | 77 (F5) | 77 (F5) | bar 19 beat 0.015 | -5 | -0.16 | exacto |
| 21 | 0.0 | 81 (A5) | 81 (A5) | bar 21 beat 0.044 | +0 | -0.17 | exacto |
| 22 | 0.5 | 79 (G5) | 79 (G5) | bar 22 beat 0.554 | -4 | -0.14 | exacto |
| 23 | 0.0 | 76 (E5) | 76 (E5) | bar 23 beat 0.027 | +5 | -0.17 | exacto |

### verse_2 (compases 24-27)

| Compás | Beat spec | Pitch spec | Pitch real | Posición real | ΔVel | ΔDur | Estado |
|---|---|---|---|---|---|---|---|
| 24 | 0.5 | 69 (A4) | 69 (A4) | bar 24 beat 0.5 | +4 | -0.11 | exacto |
| 25 | 0.0 | 72 (C5) | 72 (C5) | bar 25 beat 0.05 | +4 | -0.17 | exacto |
| 26 | 0.5 | 74 (D5) | 74 (D5) | bar 26 beat 0.504 | -2 | -0.11 | exacto |
| 27 | 0.0 | 76 (E5) | 76 (E5) | bar 27 beat 0.027 | +2 | -0.17 | exacto |

### chorus_2 (compases 28-31)

| Compás | Beat spec | Pitch spec | Pitch real | Posición real | ΔVel | ΔDur | Estado |
|---|---|---|---|---|---|---|---|
| 28 | 0.0 | 79 (G5) | 79 (G5) | bar 28 beat 0.071 | +5 | -0.13 | exacto |
| 29 | 0.5 | 81 (A5) | 81 (A5) | bar 29 beat 0.565 | -3 | -0.16 | exacto |
| 30 | 0.0 | 79 (G5) | 79 (G5) | bar 30 beat 0.069 | +0 | -0.15 | exacto |
| 31 | 0.5 | 76 (E5) | 76 (E5) | bar 31 beat 0.562 | +5 | -0.19 | exacto |

### outro (compases 32–35) — sin frase del compositor, frase inyectada por el motor

El JSON no trae frase para el outro (focus: rhodes). El motor sax de FASE 5 improvisa un gesto de cierre en secciones sin material del compositor (`improv.sax_plan`, acción `final`, transformación `vary_ending`):

| Compás | Beat | Pitch | Nota | Dur real | Vel real |
|---|---|---|---|---|---|
| 32 | 0.03 | 67 | G4 | 0.47 | 65 |
| 32 | 0.56 | 65 | F4 | 0.44 | 48 |
| 32 | 1.02 | 67 | G4 | 0.99 | 52 |
| 32 | 2.48 | 79 | G5 | 0.51 | 56 |

Estas 4 notas explican la diferencia 30 vs 26 y el mínimo global F4 (65). Velocidades bajas (48–65) y duraciones cortas: gesto de cierre fading, coherente con el `fade_out` de 2 compases.

## 5. Controles del motor verificados (sin corregir nada)

1. **Protección del compositor**: `enhance.py` filtra las frases del motor en secciones con material escrito — verse_1, chorus_1 y verse_2 recibieron propuestas del motor (statement/develop/displace) que fueron **descartadas**; las 26 notas spec llegaron intactas.
2. **Silencio musical**: el intro (focus rhodes+pad) queda sin sax por diseño (acción `silencio`, bloque lead apagado).
3. **Evidencia `frases_sax: 4`** = entradas del PLAN del motor con acción activa (verse_1, chorus_1, verse_2, outro); solo la del outro llegó al MIDI al tener las otras material del compositor. No significa 4 frases nuevas audibles.
4. **Humanización** (`forge/engine.py`, `Buf.add`): onset gaussiano (jitter ±5 ticks), duración × legato 0.93, velocidad ±4. El pitch pasa sin modificación por `int(pitch)`.
5. **Compliance**: 0 fallos; 1 aviso (`motif_repeat`) — esperado: verse_2 repite deliberadamente material de verse_1 (es un test de registro, no de novedad temática). Aviso del compilador W403 sobre vibraphone (banda B3, `mallet_sparse` en chorus_2) — no afecta al sax.

## 6. Lectura musical del diagnóstico

- **verse_1 (G4–D5)**: el motor reproduce el registro medio pedido sin empujar la frase hacia arriba — base estable.
- **pre_1 (C5–F5)**: ascenso limpio (+3.9 st de media vs verse_1); el clímax de velocidad llega en la F5 (vel 80).
- **chorus_1 (E5–A5)**: el pico A5 (81) se emite dos veces (bars 17 y 21) con las velocidades más altas del MIDI (91 y 86) — clímax real de registro e intensidad, tal como se diseñó.
- **verse_2 (A4–E5)**: descenso controlado (-5.75 st vs chorus_1) sin caer al registro grave — retorno correcto.
- **chorus_2 (E5–A5)**: clímax final equivalente al primer coro; vel 85–89 en el pico.
- **Programa GM 66** (0-indexed) = Tenor Sax 1-indexed — nombre de pista y timbre consistentes.

## 7. Reproducción

```bash
# regeneración exacta (verificación por hash):
python3 scripts/produce.py output/experimentos/sax_register_test/doc.json \
  --production sax --seed 7351 \
  --out output/experimentos/sax_register_test \
  --verify c379c40360b4dc100a896b5fa9c92f32428117e766a2f803447f6ef1daeced16
```

Renderizado auditivo local (Windows, si hay FluidSynth + soundfont):
```bash
fluidsynth -ni soundfont.sf2 sax_register_test.mid -F sax_register_test.wav -r 44100
```

*Este análisis es técnico (alturas MIDI). El juicio musical de registro (si el tenor suena forzado sobre A5, etc.) requiere escucha humana con soundfont — no se simuló en este entorno.*