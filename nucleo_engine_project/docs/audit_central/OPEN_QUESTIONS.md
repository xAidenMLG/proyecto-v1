# OPEN_QUESTIONS — Preguntas realmente abiertas tras la investigación

> Misión: DMD Composer como centro de producción musical · Fecha: 2026-11-11 · Regla de la misión: aquí SOLO van preguntas que no pudieron resolverse inspeccionando el código o ejecutando una prueba segura. Cada una incluye la forma concreta de resolverla.

| # | Pregunta | Por qué sigue abierta | Cómo se resuelve |
|---|---|---|---|
| 1 | ¿Qué ejecutables y CLI real tiene sfizz en `C:\tools\sfizz` (¿render offline de MIDI?, ¿versión?) | sfizz no existe en el sandbox y tiene cero referencias en el repo; la misión prohíbe presuponer su CLI | En Windows: `dir C:\tools\sfizz` + `<exe> --help` sobre cada ejecutable; pegar la salida (decide ruta B1/B2 del render híbrido) |
| 2 | ¿Está ffmpeg.exe o lame.exe instalado en Windows y en qué ruta? | El código ya lo busca (`forge/audio.py:39-58`) pero ninguna evidencia del repo confirma su presencia | `where ffmpeg lame` + `ffmpeg -version \| findstr libmp3lame` |
| 3 | ¿Qué calidad/tiempo/estabilidad tiene el render real de FluidSynth en el hardware del usuario (gain, reverb tails, RAM)? | 8 jobs fallaron por el bug de entorno (P0-2) → nunca hubo 1 render exitoso registrado | Tras B-02: producir 1 WAV real y medir (duración, tiempo, RAM, picos); pasa de PARTIALLY a VERIFIED |
| 4 | Integridad y tamaños reales de los 5 soundfonts del usuario (¿completos?, ¿licencia de uso?) | Los ficheros no están en el repo/sandbox | `dir` + hashes sha256 en Windows y registro en `soundfonts.json` (Soundfont Manager) |
| 5 | ¿Dónde quiere el usuario `DMD_Library/` (unidad, carpeta) y dónde residirán los soundfonts de forma permanente? | Decisión de configuración personal (espacio en disco, backups) | Decidir al implementar Fase 1; hacerla configurable |
| 6 | ¿Se distribuirá alguna vez un binario externo junto al proyecto (ffmpeg/sfizz) o todo queda instalado localmente? | Afecta licencias: ffmpeg build GPL + LAME LGPL solo importan si se redistribuye el .exe | Decisión del usuario; mientras sea local-first sin redistribución, sin impacto |
| 7 | ¿Se conserva DMD Studio como herramienta de diagnóstico indefinidamente, o se busca paridad total en Composer y se congela Studio? | Condiciona si los fixes de `studio/` (B-02/B-05/B-06) se hacen ahora o se postergan | Decisión del usuario |
| 8 | F6-L1 (density.sax/rhodes inertes) sigue congelada pendiente de escucha — ¿se descongela antes de las fases de audio? | Decisión musical con riesgo de romper dorados aprobados | Escucha del usuario + decisión documentada en DECISIONS.md |
| 9 | ¿Paralelismo deseado para renders WAV (N=2) o estrictamente secuencial? | Compromiso estabilidad/velocidad en 16 GB (estimación, no medido en Windows) | Medir tras la primera renderización real; decidir el default del perfil |
| 10 | ¿El sax debe salir por sfizz/SFZ (TenorSaxophone.sfz) desde la primera versión de audio, o basta GM66 de FluidSynth inicialmente? | Depende de la respuesta a #1 y del criterio musical del usuario | Probe sfizz + escucha comparativa GM66 vs SFZ |
| 11 | ¿Reservar un puerto fijo para la futura capa Library/runner (p. ej. 8897) o todo por el 8898 de Composer? | Convención a fijar antes de Fase 1 | Decisión menor del usuario |
| 12 | Política de retención: ¿cuántas generaciones (`gen_NNNN`) por proyecto y cuántas corridas de álbum conservar antes de archivar? | Depende del disco y del flujo de trabajo del usuario | Decidir en Fase 5 (Library); mecanismo de archivado propuesto |

### Preguntas descartadas deliberadamente (ya respondidas por la auditoría)
Todas las preguntas sobre: capacidades del pipeline (VERIFIED TEST01-11), esquema de álbum real (VERIFIED), estructura real del MIDI (VERIFIED 27 SMF), seguridad de Composer/Studio (VERIFIED por tests y lectura), puerto libre (8898/8899), dependencias necesarias (ninguna nueva), y modelo de ejecución (proceso por álbum) — están respondidas con evidencia en `VERIFICATION_MATRIX.md` y no se repiten aquí.
