# DMD COMPOSER — LIMITACIONES (honestidad de ingeniería)

Documentadas para no simular capacidades que no existen (misión §15).

> **Actualización v1.2 (2026-11-11, misión de planificación):** las
> limitaciones 8 y 9 quedan REENMARCADAS por las decisiones D21/D22/D27
> (ver DECISIONS.md): el "modo álbum compone, no produce" y el "sin WAV"
> dejan de ser limitaciones permanentes para pasar a ser (a) trabajo
> planificado (Fases 1–3 del `IMPLEMENTATION_ROADMAP.md`: producción MIDI,
> reproducción y álbumes con producción por lotes) y (b) DECISIÓN de ámbito
> permanente (el render de audio NUNCA estará en Composer). El texto original
> de cada punto se conserva como registro histórico de la v1.1.

## Limitaciones del CONTRATO (no de Composer; no se resuelven tocando el contrato)

1. **Dos acordes dentro de un compás no existe.** `chord_bars` es entero 1–8
   (compases POR acorde). La "distribución definida por el usuario" se logra con
   `Grado:N` (ENTEROS de 1 a 64: `I:2 - V:1`) y ciclos, nunca con subdivisiones
   de compás — el parser rechaza fraccionarios con error claro.
2. **Métrica fija 4/4.** El contrato no admite compás musical configurable; la
   duración se calcula `compases × 4 × 60/BPM`. Song Map usa esa fórmula.
3. **Máximo 3 instrumentos en focus** y whitelist `active` por sección, pero sin
   jerarquía de "protagonista por sección": el protagonista es una decisión
   GLOBAL de Composer que se expresa con focus y densidades.
4. **Sin marcadores MIDI de sección.** La integración actual
   dark-director/1 → compilador → Forge no expone escritura de meta-eventos de
   marcador, y modificar Forge solo para conseguirlo está prohibido (misión §7:
   "conserva el Song Map externo"). El Song Map (JSON/CSV + grid por compás +
   bloque `[Sección]` para letras) es la representación estructural.
5. **`development` fuera de alcance.** Frases, motifs, transposiciones y
   improvisación NO los escribe Composer: son libertad del motor (regla 10).
   Consecuencia: `W404` (commercial sin hook) se mitiga con `loop_bars` en
   chorus (campo estructural real), no con material melódico.
6. **W414 informativo.** Si fijas progresiones con calidades fuera del
   vocabulario del language (p. ej. dominantes 7 en `pop_dream_pop`), el motor
   las respeta por precedencia pero avisa. Composer muestra el mismo aviso
   ANTES de generar y ofrece cambiar el language o los tokens.
7. **Rango 1–8 para `harmonic_rhythm_bars` y `chord_bars`.**

## Limitaciones de COMPOSER en esta versión

8. **El modo álbum compone, no produce.** *(Reenmarcado v1.2: la producción
   MIDI por pista y por lotes está PLANIFICADA en la Fase 3 del roadmap;
   reutilizará el orquestador existente de `album/`.)* Composer genera el plan
   y los documentos de cada pista con diversidad real (tonalidad, estructura,
   groove, seeds, huellas). El MIDI de cada pista se produce con el pipeline
   DMD.
9. **Sin WAV en Composer.** *(Reenmarcado v1.2: ya no es una "limitación
   pendiente" sino una DECISIÓN de producto — D22. El render de audio queda
   EXCLUIDO permanentemente; la conversión MIDI→audio es una aplicación
   Python externa del usuario.)* El WAV dependía de FluidSynth + soundfont
   (Studio). Composer valida y compila; no renderiza audio (no duplica
   pipeline).
10. **Validación en vivo requiere DMD descubierto.** Sin DMD, Composer trabaja
    con la instantánea incluida (catálogos y recetas N1 congeladas de rev 3.2)
    y marca las generaciones como "sin validación en vivo".
11. **La calidad MUSICAL final la juzga el usuario.** Los tests técnicos prueban
    validez, coherencia y reproducibilidad, nunca "suena bien" (misión §14).
12. **Las plantillas de progresión son gustos, no verdades.** Las pool por mood
    (melancholic/dark/hopeful/tense/neutral) son preferencias ponderadas,
    editables y siempre visibles antes de aceptar (vista previa en vivo).
13. **Un solo idioma de UI**: español. El contrato y los ids permanecen en su
    inglés original del sistema.
14. **Song Map nativo depende de la receta introspeccionada.** Si una identidad
    futura no expusiera `PROGRESIONES` en su receta, esas secciones nativas
    aparecerían sin progresión en el mapa (se marca `fuente_armonia`).

## Decisiones que pueden parecer limitaciones y no lo son

15. **`auto` escribe; `free` no.** Si esperabas que "automático" dejara el campo
    vacío, es al revés por diseño (misión §3): automático = Composer elige y
    escribe; libre = el motor decide con su receta.
16. **Las decisiones fijadas nunca se tocan para "mejorarlas".** Si fijas
    BPM 150 en dark_triphop, el doc lleva 150 y el validador emite W401.
    El conflicto se informa, no se silencia ni se corrige en silencio.
17. **Inversiones con cifrado clásico.** `I6` es primera inversión (C/E), no
    "I con sexta añadida" (para eso: `Iadd6`). Documentado en la vista Armonía.
18. **Cuatro ejes no admiten "Libre"**: identity, accessibility, key y language
    son obligatorios en todo documento (E103 del contrato). La UI los marca y
    la API los rechaza; si un proyecto antiguo los trae libres, se degradan a
    automáticos con nota en el log.

## Limitaciones v1.2 (nuevas, por las decisiones de reproducción)

19. **La reproducción WebAudio es una PREVIEW, no el render final.** El Player
    del navegador sintetiza con osciladores por rol (D24/D25): el sonido NO es
    necesariamente idéntico al que el usuario obtiene al convertir el MIDI con
    su soundfont/convertidor externo. Esta advertencia se mostrará junto al
    reproductor cuando la Fase 2 se implemente.
20. **El Player no lee ficheros `.mid` arbitrarios.** Solo consume el formato
    `to_events` (`events.json` de la generación). Un gen sin `events.json` no
    es reproducible hasta que se genere; no existe parser de MIDI en el
    navegador y no se escribirá uno.
21. **La Opción A (events.json) requiere autorización explícita.** Mientras no
    se autorice el parámetro aditivo en `scripts/produce.py` (D26), la
    reproducción planificada de la Fase 2 no tiene fuente de datos; la
    alternativa (Opción B, doble generación) está documentada y DESCARTADA.

## Resultado de la auditoría independiente (misión §12.H)

Auditoría externa sobre el código real (sin depender de las explicaciones del
constructor): 2 críticos + 7 medios + 7 menores. TODOS corregidos y verificados
con sondas que replican cada hallazgo (bpm/seed/hr como texto desde la UI,
"libre" en ejes obligatorios, propagación de chord_bars/resolution por sección,
alineación de los pre-chequeos con `suena()` real del validador, protagonista
inventado/contradicho, estructura compartida del álbum, reintentos del álbum
deterministas, validación de entrada en la API, reserva exclusiva de
generaciones). La batería completa sigue en verde (77 tests) y las 5
demostraciones reproducibles con sus SHA256.
