# REGISTRO DE PRUEBAS — DMD STUDIO (2026-11-10)

## 1. Matriz integral E2E por HTTP contra el servidor real (`scripts/e2e_studio.py`)

Resultado: **36/36 OK**. Salida completa:

```
== 1. CREAR COMPOSICIÓN DESDE CERO ==
  ✓ capabilities 200
  ✓ crear proyecto 200
  ✓ guardar doc golden
== 2-10. LOS 7 PERFILES ==
  ✓ perfil original
  ✓ perfil sax
  ✓ perfil sax_rhodes
  ✓ perfil drums
  ✓ perfil sax_vibes
  ✓ perfil full
  ✓ perfil atmospheric
== 11-12. MODOS ARMÓNICOS ==
  ✓ native harmony (sin progresiones)
  ✓ validador acepta guided
  ✓ doc guided guardado
  ✓ guided harmony (progressions+chords)
== 13. FAMILIARIDAD FASE 7 (OPCIONAL) ==
  ✓ keyword dark_cinematic
  ✓ id CINE01 + variacion medium + harmony-seed
  ✓ F7 keyword ≠ id (transformaciones distintas)
== 14-15. JSON DIRECTO + PERSISTENCIA ==
  ✓ x_* aceptado por el validador real
  ✓ campo x_* preservado tras guardar/reabrir
  ✓ duplicar proyecto
  ✓ eliminar duplicado
== 16. WAV (ruta controlada sin FluidSynth) ==
  ✓ WAV sin fluidsynth → MIDI OK + wav.error claro
== 17-18. ENTRADAS INVÁLIDAS Y ERRORES BACKEND ==
  ✓ perfil inexistente → 400
  ✓ keyword desconocida → 400
  ✓ traversal en pid → nunca 200
  ✓ pid con '..' → 400
  ✓ audio con traversal → nunca 200
  ✓ proyecto inexistente → 404
  ✓ E102 schema incorrecto detectado
  ✓ E109 campo desconocido detectado (sugerencia del validador)
  ✓ generate con doc inválido → 422 validación previa
  ✓ E203 contradicción detectada
== 19. DETERMINISMO WEB×2 Y WEB vs CLI ==
  ✓ web repetida byte a byte
  ✓ web == CLI byte a byte (mismo doc, perfil, seed)
  ✓ evidencia.json expone reproducción exacta
  ✓ sha256 de evidencia == sha256 del historial

===== RESULTADO: 36 OK / 0 FALLO =====

```

## 2. Suite pytest del estudio (`tests/studio/`)

Resultado: **13/13 OK**. Resumen:

```
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
```

Casos: capabilities refleja el contrato real (rev 3.2, 7 perfiles, keywords F7,
biblioteca) · ciclo completo de proyecto (crear/guardar/duplicar/eliminar) ·
pid con traversal rechazado · nombres con caracteres de ruta rechazados ·
validador real E102/E109 · golden aceptado · generate con doc inválido → 422 ·
generación real + determinismo web×2 (misma seed → mismo sha256) · los 7
perfiles ejecutan · guided ≠ native y Fase 7 con evidencia · concurrencia
single-flight · recover_interrupted · WAV sin FluidSynth → MIDI OK + error claro.

## 3. Regresión de motores (`tests/dmd/`)

**171 passed, 18 subtests** — los motores protegidos (`forge/`, `styles.py`,
`dark_director/identities/dark_triphop.py`, `contract.py`) no fueron tocados.

## 4. Verificación de interfaz (navegador real, agent-browser)

- Projects: tabla de proyectos, crear proyecto desde modal → abre Composition.
- Composition: timeline con 9 secciones del golden coloreadas por tipo; editor
  de secciones completo; panel de instrumentos con mix avanzado.
- Harmony: modo GUIDED detectado automáticamente (el golden trae progresiones).
- Production: 7 tarjetas con matriz de motores; `full · default` seleccionado.
- Generation: generación completa desde la UI (perfil full, seed 2026),
  configuración efectiva y comando CLI equivalente visibles, estado y log.
- JSON: validación en vivo con el motor real («✓ válido…» y
  «E105 · bpm fuera de 20–300: 999»), gutter de líneas corregido.
- Results: gen_0001 con perfil/seed/duración/compliance, sha256 copiable,
  evidencia, comando de reproducción exacta con --verify, descargas
  (MIDI, doc.json, config_efectiva.json, evidencia.json, job.log).
- Guardar → recargar → proyecto restaurado (persistencia OK).

## 5. Determinismo web vs CLI (evidencia clave)

Mismo documento (golden + progresiones guiadas), perfil `full`, seed 7:

- Web (2 ejecuciones): `2da704e8c1cd1870896d9805cc6aa6e6bbbba0a38f3409a62a8d3b38628f8b86`
- CLI `scripts/produce.py` (misma entrada): idéntico byte a byte.
