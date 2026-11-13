# INFORME DE AUDITORÍA — MANUAL TÉCNICO Y OPERATIVO DE DMD COMPOSER

Fecha: 2026-11-11 · Misión exclusivamente de **documentación y auditoría informativa**.
**No se modificó ningún archivo de código, lógica, interfaz, configuración, contrato ni archivo funcional** de DMD Composer, DMD Studio, DMD o MIDI Forge.

## 1. Entregable

`docs/MANUAL_USUARIO_DMD_COMPOSER.md` — 1.315 líneas (~113 KB), con las 14 secciones exigidas (Introducción y arquitectura → Glosario) + Anexo A de auditoría. Incluye 6 capturas de pantalla reales (`docs/img/01_setup.png` … `06_output.png`) tomadas sobre la aplicación en ejecución con el DMD real descubierto.

## 2. Archivos inspeccionados

- **Backend completo** (14 módulos Python, leídos íntegros): `model.py`, `engine.py`, `builder.py`, `structure.py`, `harmony.py`, `randomizer.py`, `songmap.py`, `albums.py`, `manifest.py`, `bridge.py`, `dmd_bridge_runner.py`, `store.py`, `server.py`, `__main__.py`, `__init__.py`.
- **Frontend completo**: `index.html`, `app.js`, `state.js`, `views.js`, `api.js`, `composer.css`.
- **Scripts**: `install.bat`, `check.bat`, `start.bat`, `demostraciones.py`.
- **Tests**: las 8 baterías A–H + util (leídas y ejecutadas).
- **Datos**: `composer_data/dmd_manifest.json` y `manifests/dmd_manifest_builtin.json` (1.752 líneas cada uno), las 5 demostraciones de `profiles/` completas, `projects/`.
- **Documentación contrastada**: USER_MANUAL, ARCHITECTURE, COMPATIBILITY, LIMITATIONS, TEST_REPORT, DECISIONS (D1–D15), PROJECT_STATE, NEXT_MISSION.
- **DMD real (contraste)**: `dark_director/contract.py` (introspección en vivo: catálogos + 40 códigos EW + versiones), `studio/runner.py` y `studio/server.py` (semántica de seed al generar MIDI).

## 3. Controles y opciones documentados

- **16 ejes de decisión** (fixed/auto/free; 4 obligatorios sin Libre) + tabla de verdad de qué llega realmente a `doc.json`.
- **≈120 controles de interfaz** (contando repetidos por instrumento/sección/pista) y **≈90 valores enumerados** de catálogo.
- **6 pantallas** con paneles, placeholders y textos de ayuda citados literalmente del código.
- **40+ mensajes** documentados con texto exacto: 15+ errores duros (E-codes y conflictos), 12+ avisos (W-codes y conflicto-suave), 13 errores de aplicación/API.

## 4. Pruebas utilizadas para verificar el comportamiento

1. Batería A–H ejecutada: **77/77 tests OK** (0 fallos, 0 errores, ~3,2 s) — coincide con TEST_REPORT.md.
2. Reproducibilidad: `demostraciones.py --verificar` → las 5 SHA256 de los docs coinciden (`3a27d440…`, `d387bb66…`, `c2156800…`, `04421175…`, `946a5b05…`).
3. Introspección en vivo del contrato real rev 3.2 (catálogos, EW_CODES, fingerprint) — coherente con manifiesto cacheado y instantánea builtin.
4. Aplicación en vivo: servidor `python -m composer` + `/api/system` con `dmd_descubierto` y fingerprint correcto; 6 pantallas renderizadas y capturadas en Chromium sin errores de consola.
5. Verificación cruzada de código: alcance real del protagonista, semántica de mezcla Native/Guided, uso de `global.seed` por Studio, determinismo del álbum, constantes muertas (`rg`).

## 5. Discrepancias detectadas (registradas, NO corregidas)

| # | Resumen | Gravedad |
|---|---|---|
| D-01 | USER_MANUAL/UI prometen para el protagonista "prioridad funcional" en focos y densidades; el código solo garantiza sonido (`enabled=true` fuera del set base) + conflictos + log | Media |
| D-02 | COMPATIBILITY.md promete detección de DMD cambiado "y la UI lo muestra"; no hay botón de refresh en UI y el arranque reutiliza el manifiesto cacheado si la ruta coincide | Media |
| D-03 | USER_MANUAL dice que las identidades doom se muestran "marcadas como archivadas"; la UI las muestra planas | Baja |
| D-04 | Código muerto sin uso: `model.LABEL_TYPES`/`type_for_label`, `builder.LANG_DEFAULT_RES` | Baja |
| D-05 | "Puedes mezclar por sección" sin advertir que con modo global Nativa los numerales por sección se ignoran en silencio | Media |
| D-06 | El log marca siempre `harmony_mode` como `fixed` aunque esté Auto/Libre | Baja |
| D-07 | UI bloquea Libre en `harmony_mode`; la API lo acepta (y actúa como guided) | Baja |
| D-08 | El campo `descartadas` del log de explicabilidad llega vacío en las elecciones ponderadas | Baja |
| D-09 | El manifiesto cacheado se etiqueta como origen "vivo" | Baja |
| D-10 | La batería de tests G deja proyectos residuales en `projects/` | Baja |

Detalle completo con evidencia de código: Anexo A.4 del manual.

## 6. Funcionalidades que no pudieron verificarse (y qué se verificó en su lugar)

| Punto | Motivo | Cobertura alternativa |
|---|---|---|
| Instalación Windows real (.bat) | Sandbox Linux | Lectura íntegra de los 3 scripts |
| Importación end-to-end en Studio UI | Fuera de la misión / modificaría datos de Studio | Validador+compilador reales ejecutados sobre docs de Composer (tests A/F) + lectura de `studio/runner.py` |
| WAV (FluidSynth + soundfont) | Fuera de alcance de Composer | Documentado como flujo de Studio |
| Efecto auditivo de F7 / perfiles | Motores de Studio | Superficie introspeccionada real (10 keywords, 4 niveles, 43 recetas); doc nunca los contiene (test A6) |
| Otros navegadores | Solo Chromium disponible | UI vanilla JS simple |
| Reanudación multi-sesión del álbum | Requiere uso prolongado | Test G4 + escritura atómica |

## 7. Integridad de la misión

- Archivos creados: `docs/MANUAL_USUARIO_DMD_COMPOSER.md`, `docs/img/*.png` (6 capturas), este informe.
- Efectos colaterales de la verificación revertidos (proyectos `*_x` creados por tests G eliminados; sin generaciones nuevas; servidor de capturas detenido).
- Criterio de aceptación: el manual permite operar cada opción sabiendo qué decide el usuario, qué decide Composer y qué decide el motor DMD, sin adivinar.
