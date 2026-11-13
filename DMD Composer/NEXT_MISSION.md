# NEXT MISSION — DMD COMPOSER

> **Actualizado v1.2 (2026-11-11, misión de planificación):** el roadmap
> oficial es ahora `IMPLEMENTATION_ROADMAP.md` (fases 1–6 con ficheros exactos
> y criterios de aceptación). Este documento señala el PRÓXIMO HITO a
> autorizar; no implementa nada.

## HITO 1 A AUTORIZAR — Fase 1 del roadmap: producción MIDI individual

Del documento validado al MIDI descargado, todo dentro de Composer:

* Tarea `produce` en `composer/dmd_bridge_runner.py` + `bridge.produce()`
  (timeout 300 s, spec JSON ≤ 8 MB, argv fijo, `shell=False`).
* Persistencia `output/<pid>/gen_NNNN/midi/<nombre>/` (doc, config_efectiva,
  `<nombre>.mid`, evidencia.json) + bloque `midi` del manifest con SHA256.
* Endpoint `POST /api/projects/{pid}/generations/{gen}/midi` + whitelist de
  descargas ampliada + estados/errores/reintentos en la UI Output.
* Batería de tests J: determinismo byte-idéntico, igualdad SHA256 triple,
  immutabilidad, path traversal; batería v1.1 (114) sigue en verde.

Opción A (events.json en `produce.py`) es un cambio separado que requiere
autorización EXPLÍCITA propia — no forma parte del hito 1 por defecto.

**Estado:** PLANIFICADO. Ninguna línea de esta fase está implementada.

---

## Trabajo futuro (reordenado por el roadmap v1.2)

1. **Fase 2 — Reproducción MIDI** (roadmap §3): `player.js` (clase Player de
   Forge copiada literal) + controles + `events.json` por generación.
2. **Fase 3 — Creador de álbumes completos** (roadmap §4; absorbe el antiguo
   punto 1 "integración profunda del modo álbum"): config de álbum/pista,
   lote de 13 pistas con estados/reintentos/cancelación/recuperación,
   reutilizando el orquestador existente de `album/` (SOLO LECTURA).
   Antiguo punto 1 de esta lista — reordenado; lo ya construido
   (planificador, huellas, reanudación, informe de diversidad) sigue vigente
   y se conserva.
3. **Fase 4 — Validación end-to-end** (roadmap §5).
4. **Fase 5 — Congelación funcional** (roadmap §6) · **Fase 6 — Plan B**
   (roadmap §7, contingencia).

## SUPERSEDED — WAV desde Composer (antiguo punto 2)

> **SUPERSEDED por la decisión D22 (DECISIONS.md, 2026-11-11).** La
> conversión de audio (WAV/MP3/FluidSynth/soundfonts) quedó EXCLUIDA del
> producto: el usuario ya posee una aplicación Python externa de conversión
> MIDI→audio por lotes. Texto histórico: "un botón opcional en Output que
> invoque el runner de Studio (o `forge.audio.render_wav` vía bridge)...".

## Backlog estacionado (sin fecha, no bloquea)

* **Improvisación guiada opcional** (existe el modelo del contrato; falta el
  toggle por sección; recomendado DESACTIVADO por defecto).
* **Plantillas de proyecto y estilo** (la persistencia ya soporta copiar
  proyecto; falta el selector en la UI).
* **Internacionalización de la UI** (D14: español hoy; `state.js` centraliza
  etiquetas si se quiere inglés).

---

### Guardas permanentes (no negociables, v1.2 incluidas)

1. No modificar DMD Studio.
2. No modificar el contrato dark-director/1 rev 3.2.
3. No modificar los motores protegidos ni los goldens.
4. No duplicar el pipeline MIDI (usarlo vía puente aislado = sancionado; un
   segundo motor = prohibido).
5. F7 opcional siempre.
6. Sin campos que el validador no admita.
7. Sin generador nota por nota.
8. **(v1.2) Sin render de audio en Composer: jamás (D22).**
9. **(v1.2) La congelación funcional precede a cualquier reestructuración
   arquitectónica (D28).**
