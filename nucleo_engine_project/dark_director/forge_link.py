"""Enlace de importación a MIDI Forge SIN modificarlo (alcance C de Fase 0;
instrucción 09: protección de importación y ruta de auditoría).

Principios:
  - ``forge/`` es un módulo externo y solo-lectura para Dark Music Director.
    Este módulo localiza el motor, lo importa y verifica que expone las
    capacidades que el contrato y la auditoría citan. Nunca escribe en su árbol.
  - PROTECCIÓN DE IMPORTACIÓN SIN EFECTO PERMANENTE (instrucción 09.1): todos
    los imports del motor ocurren dentro del context manager
    :func:`sin_bytecode`, que fija ``sys.dont_write_bytecode = True`` SOLO
    durante la importación y RESTAURA el valor previo al salir. Motivo real:
    importar con la configuración por defecto crearía ``.pyc`` nuevos dentro de
    ``forge/__pycache__`` (p. ej. Python 3.12 sobre el ``__pycache__`` 3.11 de
    la auditoría) y eso YA sería modificar ``forge/``. El intérprete queda
    exactamente como estaba: la protección es de ámbito, nunca un estado global
    permanente del proceso (Fase 0 la fijaba de forma permanente; corregido).
  - La importación de forge es perezosa: ``import dark_director`` no toca el
    motor hasta que alguien llama a :func:`import_forge`.

Resolución de la raíz de ``forge/`` (en orden):
  1. variable de entorno ``DARK_DIRECTOR_FORGE_ROOT`` (ruta del paquete forge);
  2. ``forge/`` hermano del paquete (layout final dentro del proyecto MIDI Forge;
     es la única vía en producción);
  3. copia auditada del sandbox — EXCLUSIVAMENTE en modo auditoría
     (``DARK_DIRECTOR_AUDIT_MODE=1``, instrucción 09.2): es una herramienta de
     auditoría y de la suite de pruebas, NUNCA una dependencia de producción.
     Sin esa variable, un despliegue real jamás resolverá al sandbox.
"""

import importlib
import inspect
import os
import sys
import types
from contextlib import contextmanager
from pathlib import Path

# Copia auditada (auditoría rev. 1: lectura completa + ejecución; no se modificó).
# SOLO alcanzable con DARK_DIRECTOR_AUDIT_MODE=1 (ver resolve_forge_root).
_RUTA_AUDITADA = Path("/home/z/my-project/audit/midi_forge/forge")

VAR_MODO_AUDITORIA = "DARK_DIRECTOR_AUDIT_MODE"

#: módulos del motor que el contrato/auditoría citan
FORGE_MODULES = ("theory", "voicing", "styles", "engine", "validate", "adapter", "midiwriter", "audio")

#: símbolos que la auditoría (§1, §3) y el contrato (§2.5.1, §2.6.x) citan por nombre
REQUIRED_SYMBOLS = {
    "styles": ("ROLES", "KINDS", "PRESETS", "ROLE_DEFAULTS", "ROLE_VEL_OFFSET", "ROLE_PRIORITY",
               "ARP_PATTERNS", "BASS_SETS", "DRUM_PRESETS", "STYLE_SCHEMA", "style_defaults",
               "default_block", "apply_modifiers"),
    "voicing": ("PROFILES", "resolve_profile"),
    "adapter": ("normalize", "finalize_project", "from_spec"),
    "validate": ("compliance", "validate"),
    "engine": ("generate", "generate_phrase"),
    "theory": ("parse_chord", "parse_key", "resolve_program"),
    "midiwriter": ("build_midi",),
    "audio": ("status",),
}

#: perfiles de voicing que el contrato nombra en §2.6.5 / §2.6.6 / §2.5.1
VOICING_PROFILES_CONTRACTO = ("full", "triad", "shell", "bare", "open4", "rootless")

#: guardrails dark que el contrato cita (§2.5 catálogo, §2.11) y la auditoría (validate.py:83-134)
GUARDRAILS_CONTRACTO = ("lead_mono_range", "lead_coverage", "lead_mallet_overlap",
                        "mallet_sparse", "bass_kick", "motif_repeat", "four_on_floor")

#: presets existentes según auditoría (styles.py:7) — el contrato NO añade presets
PRESETS_EXISTENTES = ("synthwave", "triphop")


class ForgeNoEncontrado(RuntimeError):
    """No se pudo localizar una copia de ``forge/`` importable."""


def en_modo_auditoria():
    """True solo si ``DARK_DIRECTOR_AUDIT_MODE=1`` (herramienta de auditoría/QA).
    La copia del sandbox y la importación del motor jamás se usan de forma
    implícita en producción (instrucción 09.2)."""
    return os.environ.get(VAR_MODO_AUDITORIA) == "1"


def resolve_forge_root():
    """Localiza el paquete ``forge`` (directorio que contiene ``__init__.py``)."""
    env = os.environ.get("DARK_DIRECTOR_FORGE_ROOT")
    candidatos = []
    if env:
        candidatos.append(Path(env))
    # layout final: dark_director/ vive en la raíz del proyecto MIDI Forge
    candidatos.append(Path(__file__).resolve().parent.parent / "forge")
    # fallback sandbox: SOLO en modo auditoría (instrucción 09.2)
    if en_modo_auditoria():
        candidatos.append(_RUTA_AUDITADA)
    for c in candidatos:
        if (c / "__init__.py").is_file():
            return c.resolve()
    raise ForgeNoEncontrado(
        "no se encontró forge/; define DARK_DIRECTOR_FORGE_ROOT (ruta del paquete forge). "
        "La copia auditada del sandbox solo se usa con DARK_DIRECTOR_AUDIT_MODE=1. "
        f"Candidatos probados: {[str(c) for c in candidatos]}"
    )


def forge_project_root():
    """Raíz del proyecto MIDI Forge (padre de ``forge/``; ahí vive ``app.py``)."""
    return resolve_forge_root().parent


_CACHE = {}


@contextmanager
def sin_bytecode():
    """Protección de importación de ámbito (instrucción 09.1): desactiva la
    escritura de ``.pyc`` DURANTE el bloque y RESTAURA el estado previo del
    intérprete al salir. Nunca deja un estado global permanente."""
    previo = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        yield
    finally:
        sys.dont_write_bytecode = previo


def import_forge():
    """Importa los módulos citados del motor y devuelve un namespace.
    Importación perezosa y cacheada; solo-lectura; sin escribir ``.pyc`` en
    ``forge/`` (protección de ámbito, restaurada al terminar)."""
    if "ns" in _CACHE:
        return _CACHE["ns"]
    root = resolve_forge_root()
    parent = str(root.parent)
    with sin_bytecode():
        if parent not in sys.path:
            sys.path.insert(0, parent)
        mods = {name: importlib.import_module(f"forge.{name}") for name in FORGE_MODULES}
    ns = types.SimpleNamespace(**mods)
    ns._root = root
    _CACHE["ns"] = ns
    return ns


def import_forge_app():
    """Importa ``app.py`` del proyecto MIDI Forge (módulo, sin ejecutar el servidor:
    ``serve()``/``cli()`` solo corren bajo ``if __name__ == '__main__'``).
    Se carga por ruta de archivo para no depender del nombre 'app' en sys.path."""
    if "app" in _CACHE:
        return _CACHE["app"]
    import_forge()  # garantiza sys.path del proyecto (la protección .pyc es de ámbito)
    root = forge_project_root()
    with sin_bytecode():
        spec = importlib.util.spec_from_file_location("midi_forge_app", root / "app.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    _CACHE["app"] = mod
    return mod


def verify_forge_capabilities():
    """Verifica (nivel existencia, solo-lectura) que el motor expone los símbolos
    citados por el contrato/auditoría. Devuelve un informe dict:
      {modulo: {simbolo: bool}}, más claves especiales:
      - "voicing.perfiles_contrato": {perfil: bool}
      - "validate.guardrails_en_fuente": {nombre: bool}  (inspect.getsource, solo-lectura)
      - "app.run_generate": bool
      - "presets_existentes": lista real (debe ser ('synthwave','triphop'))
    """
    f = import_forge()
    informe = {}
    for mod_name, symbols in REQUIRED_SYMBOLS.items():
        mod = getattr(f, mod_name)
        informe[mod_name] = {s: hasattr(mod, s) for s in symbols}
    # perfiles de voicing citados por el contrato
    informe["voicing.perfiles_contrato"] = {
        p: (p in f.voicing.PROFILES) for p in VOICING_PROFILES_CONTRACTO
    }
    # guardrails dark citados: presencia en la FUENTE de validate.py (solo-lectura)
    src = inspect.getsource(f.validate)
    informe["validate.guardrails_en_fuente"] = {g: (g in src) for g in GUARDRAILS_CONTRACTO}
    # punto de orquestación único de la auditoría: app.run_generate
    app = import_forge_app()
    informe["app.run_generate"] = callable(getattr(app, "run_generate", None))
    informe["presets_existentes"] = tuple(f.styles.PRESETS)
    return informe
