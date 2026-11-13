"""DMD COMPOSER — dirección de composiciones por restricciones.

Aplicación local independiente que produce documentos ``dark-director/1``
(rev. 3.2) y, desde v1.2, GENERA MIDI con el pipeline existente de DMD
(scripts/produce.py::producir_cancion vía puente aislado), lo persiste con
SHA256 verificado, lo deja descargar, lo reproduce en el navegador (Player
WebAudio original de Forge + events.json) y produce álbumes completos con el
orquestador existente (album/orquestador.py). NO modifica DMD, DMD Studio ni
los motores protegidos: solo los DESCUBRE y los USA.

Reglas de oro de la misión (§2, actualizadas en la misión de integración):
  1. No modificar DMD Studio.
  2. No modificar el contrato público dark-director/1 rev 3.2.
  3. No modificar los motores protegidos (forge/, jazz_engine/, contract.py,
     dark_triphop.py, goldens).
  4. No duplicar el pipeline de generación MIDI: NO hay un segundo motor; el
     núcleo REAL (produce.py::producir_cancion) se usa vía puente subprocess
     aislado — esa es la ruta sancionada (D23, v1.2).
  5. No sustituir la armonía nativa por la biblioteca F7.
  6. No hacer F7 obligatorio.
  7. No cambiar los comportamientos aprobados de ORIGINAL y ENHANCED.
  8. No modificar goldens ni referencias musicales protegidas.
  9. No introducir campos que el validador no admita.
 10. No convertir el proyecto en un generador nota por nota.
 11. (v1.2, D22) Sin render ni conversión de audio en Composer, jamás
     (sin WAV/MP3/FluidSynth/sfizz/SF2/SFZ/soundfonts): el usuario convierte
     MIDI→audio con su aplicación Python externa por lotes.
 12. (v1.2, D24/D25) Reproducción SOLO con el Player WebAudio original de
     Forge reutilizado + events.json (Opción A en produce.py, default OFF).
 13. (v1.2, D27) Álbumes = orquestador EXISTENTE del DMD reutilizado en un
     subprocess aislado; jamás un generador de álbumes paralelo.
"""

__version__ = "1.2.0"

#: Identificador del formato de proyecto propio de Composer (NO es contrato).
PROJECT_FORMAT = "dmd-composer/1"
