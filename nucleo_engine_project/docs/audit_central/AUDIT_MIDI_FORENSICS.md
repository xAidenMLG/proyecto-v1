# AUDIT_MIDI_FORENSICS — Análisis forense de los MIDI reales generados por DMD

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11.
> Método: parser SMF propio (stdlib `struct`; mido NO instalado) ejecutado sobre **27 SMF reales**; script y JSON crudos en `scripts/audit_c/` (`midi_forensics.py`, `results/*.forensics.json`, `_aggregate.json`).
> Validación cruzada: SHA256, BPM, duración y **144/144 recuentos de `notas_por_pista`** coinciden exactamente con los `evidencia.json` del pipeline → parser VERIFIED contra el pipeline.

---

## 1. Plantilla instrumental invariante (VERIFIED en los 27 ficheros)

| Track (orden) | Nombre meta | Canal | Program Change | GM | Rol | Notas clave |
|---|---|---|---|---|---|---|
| 0 | Conductor | — | — | — | Tempo/TS/markers | 1 PC en track 0 no percusional según parser → PC efectivos en tracks 1-5 |
| 1 | `sax_tenor` | **ch0** | 66 | Tenor Sax | lead | PB RPN0 ±2 st, slides |
| 2 | `rhodes` | **ch1** | 4 | Electric Piano 1 (Rhodes) | armonía/comping | CC7 bajo (76) |
| 3 | `vibraphone` | **ch2** | 11 | Vibraphone | eco | presencia ≤40% secciones |
| 4 | `bass` | **ch3** | 38 | Synth Bass 1 | bajo | slides −8191→0 |
| 5 | `drums` | **ch9** | (sin PC) | kit GM canal 10 | percusión | 8 pitches GM: 36,37,39,40,42,46,49,53 |
| 6 | `pad` | **ch5** | 91 | Pad 2 (warm) | atmósfera | CC7 88 |
| (vacío) | — | ch4 | — | — | — | Canal 4 reservado sin uso |

- **Biyección track↔canal**: 1 canal por track, nunca compartido (matriz track×canal limpia en los 27 ficheros). *No confundir track MIDI con canal MIDI: aquí la relación es 1:1 estable.*
- GM puro: PC fijos en tick 0, **sin bank select ni cambios de timbre**, sin SysEx, sin aftertouch, sin keyswitches, sin notas colgadas.

## 2. Inventario de eventos (agregado)

| Categoría | Hallazgo |
|---|---|
| Tempo | 1 evento tempo por fichero (BPM del doc); sin cambios de tempo salvo `tape_stop` cuando el doc lo trae |
| Time signature | 4/4 en tick 0 |
| Markers | `FF 06` en Conductor con **nombres DMD idénticos a las secciones del doc** (únicos vestigios del doc en el MIDI) |
| CC presentes | **CC7** (volumen, valores fijos por rol), **CC10** (pan), **CC11** (fade-out trazable 1:1 con `doc.ending.fade_out`, ausente en los 2 ficheros con `fade_out: null`), **CC91/93** (reverb/chorus por canal) |
| Pitch bend | present en los 5 tracks melódicos; RPN0 declarado (CC101/100/6/38) con rango ±2 semitonos; slides de bass −8191→0 |
| Velocity | melódicos respetan `velocity_cap` del doc (≤103 observado); **drums alcanza 112–118** en los 27 ficheros (bug menor del pipeline, doc dice cap 110) |
| Duplicados pitch+tick | 34 grupos cross-track (p.ej. bass pitch 36 = kick; rhodes/pad pitch 57) + 4 intra-track (kick apilado) — sin conflicto para stems por canal; riesgo solo si se rutea por altura |

## 3. Lo que se pierde / conserva al compilar (VERIFIED)

| Se pierde (no viaja al MIDI) | Se conserva |
|---|---|
| perfil de producción, identidad, seed, transforms de sax, separación material-original vs motor, compliance | eventos completos (notas, PB, CC), mezcla por canal (CC7/10/91/93), fade-out (CC11), markers de sección con nombres DMD, PPQ/tempos/duración |

**Conclusión**: el MIDI es **auto-suficiente para render** (mezcla incluida) pero **no para reconstruir decisiones** — esas viven en `doc.json`/`evidencia.json`/Song Map; la cadena de trazabilidad debe conservar esos ficheros junto al MIDI (lo hace `producir_cancion`).

## 4. Respuestas a la misión (§3.C)

1. **¿Cómo se asignan los instrumentos?** Por plantilla fija del compilador/forge: rol → (track, canal, PC GM) con la tabla de §1. No hay negociación dinámica.
2. **¿Relación estable tracks/canales/instrumentos?** Sí, invariante en 27/27 ficheros: misma plantilla con independencia de identidad/perfil/seed.
3. **¿Nombres DMD en tracks?** Sí: `sax_tenor`, `rhodes`, `vibraphone`, `bass`, `drums`, `pad` + markers con nombres de sección.
4. ¿Exclusivamente GM? **Sí** (PC GM 4/11/38/66/91; drums sin PC en ch9).
5. ¿Eventos suficientes para SFZ? **Parcial**: velocity (con capas) + pitch bend RPN0 ±2 st + CC11/7; **sin keyswitches/aftertouch/SysEx** → las articulaciones SFZ avanzadas no tendrán datos que las disparen.
6. ¿Qué se pierde? Perfil/seed/identidad/compliance/transformaciones (solo sobreviven markers); ver §3.
7. ¿Qué conserva? Ver §3 (columna derecha).
8. **Limitaciones para render multi-motor**: (a) biyección track→canal permite **stems por canal sin ambigüedad**; (b) la mezcla CC7/10/91/93 incrustada se duplicaría si se renderizan stems → filtrar/normalizar en el stem o aceptarla; (c) drums ch9 usa kit GM — un SFZ de batería necesitaría mapa de pitches; (d) los 2 programas sin banco (no bank select) simplifican la selección de presets.

## 5. Capa de asignación de soundfonts sin tocar el MIDI (especificación mínima)

```yaml
# render_profile.json (propuesta)
midi_source: {path: "Track_01.mid", sha256: "..."}
version: 1
master: {engine: fluidsynth, rate: 44100, gain: 0.5, fallback_sf2: "2.GeneralUser-GS.sf2"}
assignments:
  - {channel: 9,  role: drums,      engine: fluidsynth, library: "FluidR3 GM2-2.SF2",   program: null}   # kit
  - {channel: 0,  role: lead,       engine: sfizz,      library: "TenorSaxophone-20200717.sfz"}          # v3
  - {channel: 1,  role: keys,       engine: fluidsynth, library: "2.GeneralUser-GS.sf2", program: 4}
  - {channel: 2,  role: mallets,    engine: fluidsynth, library: "1.Timbres_of_Heaven.sf2", program: 11}
  - {channel: 3,  role: bass,       engine: fluidsynth, library: "2.GeneralUser-GS.sf2", program: 38}
  - {channel: 5,  role: pad,        engine: fluidsynth, library: "1.Timbres_of_Heaven.sf2", program: 91}
unassigned: fallback_master   # nunca fallo duro; fallback al SF2 master (GM)
validation: {require_exists: true, require_readable: true, fail_on_broken_ref: true}
```

Reglas derivadas de la evidencia: claves fiables = **canal** (estable) y, secundariamente, (track name, PC GM); el MIDI fuente nunca se modifica; las copias filtradas por canal son **temporales, verificables (sha256) y nunca sustituyen la fuente**.

## 6. Detalle por fichero representativo

| Fichero | BPM | Duración | Notas | Particularidad |
|---|---|---|---|---|
| `fase5_comparativos/01_original.mid` | 82 | ~2:35 | mínimas (comping+pad) | camino ORIGINAL |
| `fase5_comparativos/02_sax.mid` | 82 | ~2:35 | +sax frases | CC11 fade en final |
| `fase5_comparativos/07_full.mid` | 82 | ~2:35 | máxima actividad | mezcla CC7 completa |
| `fase6…/nocturno_terminal/full.mid` | 84 | — | — | hat variation, fills |
| `albumes/noches_largas/01…` y `13…` | 78–92 | 1:57–2:40 | — | plantilla idéntica en álbum completo |
| `golden_path_demo.mid` (Studio) | — | — | — | misma plantilla (Studio==CLI) |

(Datos completos por fichero en `scripts/audit_c/results/*.forensics.json`.)
