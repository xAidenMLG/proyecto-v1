"""Esquema del side-file de álbum ``dmd-album/1`` — FASE 8.

El álbum NO es un contrato congelado: es un side-file (como la config de
motores). Pero se valida fail-fast con errores claros antes de tocar los
motores. ``validar_album`` REUTILIZA los validadores reales cuando existen:

  - perfiles  → jazz_engine.production.nombres()
  - harmony   → jazz_engine.harmony_select.normalizar_activacion() (que
    valida keywords, IDs de la biblioteca, niveles de variación y pins)
  - identidad → solo la identidad ACTIVA (dark_triphop); las archivadas
    doom se rechazan como base de un álbum (misión FASE 8: no reactivar
    identidades archivadas como defaults).

Regla clave: la biblioteca de familiaridad NO es predeterminada. Una pista
solo lleva ``harmony`` si el spec la declara EXPLÍCITAMENTE. El planificador
jamás la inyecta (ni ``familiarity_auto``). Y ``original`` + harmony es un
error (el camino ORIGINAL es inviolable, coherente con FASE 6/7).
"""
import re

import jazz_engine as je
from jazz_engine import harmony_select as HS

SCHEMA_ALBUM = "dmd-album/1"
SCHEMA_PLAN = "dmd-album-plan/1"
SCHEMA_INFORME = "dmd-album-informe/1"

IDENTIDAD_ALBUM = "dark_triphop"

#: Perfiles que cuentan como "respiro" (texturas tranquilas) en la regla de
#: variedad: al menos uno cada ``respiro_cada`` pistas (PROPUESTA §4).
PERFILES_RESPIRO = ("original", "atmospheric")

#: Rango de referencia de BPM del universo Dark Trip Hop (PROPUESTA §2).
BPM_SANO = (76, 92)

DEFAULTS_RESTRICCIONES = {
    "perfil_frac_max": 0.4,
    "respiro_cada": 5,
    "prohibir_consecutivos_iguales": True,
}

_CLAVES_RAIZ = {"schema", "album", "identidad", "semilla_album", "objetivo",
                "curva_energia", "restricciones", "pistas"}
_CLAVES_PISTA = {"id", "doc", "titulo", "perfil", "seed", "harmony", "rol"}
_CLAVES_OBJETIVO = {"pistas"}
_CLAVES_RESTRICCIONES = set(DEFAULTS_RESTRICCIONES)

_RE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_RE_NOMBRE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,79}$")
MAX_PISTAS = 99


class AlbumInvalido(ValueError):
    """El spec de álbum no es válido. ``.errores`` es la lista de mensajes."""

    def __init__(self, errores):
        super().__init__(" | ".join(str(e) for e in errores))
        self.errores = list(errores)


def _err(errores, msg):
    errores.append(msg)


def validar_album(spec):
    """Valida un spec ``dmd-album/1`` (dict YA cargado del JSON).

    Devuelve la lista de avisos (el spec puede ser válido pero sospechoso).
    Lanza AlbumInvalido con todos los errores acumulados si hay alguno.
    """
    if not isinstance(spec, dict):
        raise AlbumInvalido(["A101: la raíz del álbum debe ser un objeto JSON"])
    errores = []
    avisos = []

    if spec.get("schema") != SCHEMA_ALBUM:
        _err(errores, "A102: schema ausente o != '%s': %r" % (SCHEMA_ALBUM, spec.get("schema")))
    desconocidas = set(spec) - _CLAVES_RAIZ
    if desconocidas:
        _err(errores, "A109: campos desconocidos en la raíz: %s (válidos: %s)"
             % (", ".join(sorted(desconocidas)), ", ".join(sorted(_CLAVES_RAIZ))))

    nombre = spec.get("album")
    if not isinstance(nombre, str) or not _RE_NOMBRE.match(nombre or ""):
        _err(errores, "A103: 'album' debe ser un nombre corto (letras/dígitos/espacio/_/-): %r"
             % (nombre,))

    identidad = spec.get("identidad", IDENTIDAD_ALBUM)
    if identidad != IDENTIDAD_ALBUM:
        _err(errores, "A104: identidad de álbum debe ser la identidad ACTIVA '%s' "
             "(no se reactivan identidades archivadas doom como defaults): %r"
             % (IDENTIDAD_ALBUM, identidad))

    if "semilla_album" not in spec:
        _err(errores, "A105: falta 'semilla_album' (entero ≥ 0; base de las semillas "
             "derivadas por pista — reproducibilidad)")
    else:
        sa = spec["semilla_album"]
        if not isinstance(sa, int) or isinstance(sa, bool) or sa < 0:
            _err(errores, "A105: 'semilla_album' debe ser entero ≥ 0: %r" % (sa,))

    pistas = spec.get("pistas")
    if not isinstance(pistas, list) or not pistas:
        _err(errores, "A106: 'pistas' debe ser una lista con 1–%d entradas" % MAX_PISTAS)
        pistas = []
    elif len(pistas) > MAX_PISTAS:
        _err(errores, "A106: 'pistas' excede el máximo de %d entradas (%d)"
             % (MAX_PISTAS, len(pistas)))

    objetivo = spec.get("objetivo")
    if objetivo is not None:
        if not isinstance(objetivo, dict) or set(objetivo) - _CLAVES_OBJETIVO:
            _err(errores, "A109: 'objetivo' debe ser objeto con claves %s"
                 % ", ".join(sorted(_CLAVES_OBJETIVO)))
        elif isinstance(objetivo.get("pistas"), int) and not isinstance(objetivo.get("pistas"), bool):
            if pistas and objetivo["pistas"] != len(pistas):
                avisos.append("W-A1: objetivo.pistas=%d pero el spec declara %d pistas"
                              % (objetivo["pistas"], len(pistas)))

    curva = spec.get("curva_energia")
    if curva is not None:
        if (not isinstance(curva, list) or not curva or
                not all(isinstance(x, (int, float)) and not isinstance(x, bool)
                        and 0.0 <= float(x) <= 1.0 for x in curva)):
            _err(errores, "A107: 'curva_energia' debe ser una lista de números 0–1")
        elif pistas and len(curva) != len(pistas):
            _err(errores, "A107: 'curva_energia' tiene %d valores pero hay %d pistas "
                 "(debe haber uno por pista)" % (len(curva), len(pistas)))

    restr = spec.get("restricciones")
    if restr is not None:
        if not isinstance(restr, dict):
            _err(errores, "A104: 'restricciones' debe ser un objeto")
        else:
            desc = set(restr) - _CLAVES_RESTRICCIONES
            if desc:
                _err(errores, "A109: claves desconocidas en 'restricciones': %s (válidas: %s)"
                     % (", ".join(sorted(desc)), ", ".join(sorted(_CLAVES_RESTRICCIONES))))
            fmax = restr.get("perfil_frac_max")
            if fmax is not None and (not isinstance(fmax, (int, float)) or isinstance(fmax, bool)
                                     or not 0.0 < float(fmax) <= 1.0):
                _err(errores, "A107: restricciones.perfil_frac_max debe ser 0–1: %r" % (fmax,))
            rc = restr.get("respiro_cada")
            if rc is not None and (not isinstance(rc, int) or isinstance(rc, bool) or rc < 2):
                _err(errores, "A107: restricciones.respiro_cada debe ser entero ≥ 2: %r" % (rc,))

    perfiles_validos = je.production.nombres()
    ids_vistos = set()
    for i, p in enumerate(pistas):
        pref = "pistas[%d]" % (i + 1)
        if not isinstance(p, dict):
            _err(errores, "A104: %s debe ser un objeto" % pref)
            continue
        desc = set(p) - _CLAVES_PISTA
        if desc:
            _err(errores, "A109: campos desconocidos en %s: %s (válidos: %s)"
                 % (pref, ", ".join(sorted(desc)), ", ".join(sorted(_CLAVES_PISTA))))
        pid = p.get("id")
        if not isinstance(pid, str) or not _RE_ID.match(pid or ""):
            _err(errores, "A110: %s.id inválido (letras/dígitos/_/-; empieza por alfanumérico): %r"
                 % (pref, pid))
        elif pid in ids_vistos:
            _err(errores, "A110: id de pista duplicado: %r" % pid)
        else:
            ids_vistos.add(pid)
        doc_ref = p.get("doc")
        if not isinstance(doc_ref, str) or not doc_ref.strip():
            _err(errores, "A111: %s.doc requerido (ruta del documento dark-director/1, "
                 "relativa a album.json o absoluta)" % pref)
        elif not doc_ref.lower().endswith(".json"):
            _err(errores, "A111: %s.doc debe apuntar a un .json: %r" % (pref, doc_ref))
        if "titulo" in p and not isinstance(p.get("titulo"), str):
            _err(errores, "A104: %s.titulo debe ser texto" % pref)
        if "rol" in p and (not isinstance(p.get("rol"), str) or len(p["rol"]) > 60):
            _err(errores, "A104: %s.rol debe ser texto ≤ 60 caracteres (etiqueta narrativa)" % pref)
        if "seed" in p:
            s = p["seed"]
            if not isinstance(s, int) or isinstance(s, bool) or s < 0:
                _err(errores, "A105: %s.seed debe ser entero ≥ 0: %r" % (pref, s))
        if "perfil" in p and p["perfil"] not in perfiles_validos:
            _err(errores, "A112: %s.perfil desconocido: %r (válidos: %s)"
                 % (pref, p.get("perfil"), ", ".join(perfiles_validos)))
        if "harmony" in p:
            if p.get("perfil") == "original":
                _err(errores, "A113: %s declara perfil 'original' + harmony: el camino "
                     "ORIGINAL es sin biblioteca (usa otro perfil o quita harmony)" % pref)
            har = p["harmony"]
            if not isinstance(har, dict):
                _err(errores, "A113: %s.harmony debe ser un objeto {'keyword'|'id'|"
                     "'progressions', 'seed'?, 'variacion'?}" % pref)
            else:
                try:
                    HS.normalizar_activacion(har, seed_base=0)
                except ValueError as e:
                    _err(errores, "A113: %s.harmony inválida: %s" % (pref, e))
                    continue
                # el validador del motor no comprueba la EXISTENCIA del ID:
                # la comprobamos aquí contra la biblioteca real
                if "id" in har:
                    from jazz_engine import harmony_library as _HL
                    try:
                        _HL.por_id(_HL.biblioteca(), str(har["id"]))
                    except KeyError as e:
                        _err(errores, "A113: %s.harmony: %s" % (pref, e))
                if "progressions" in har:
                    from jazz_engine import harmony_library as _HL
                    bib = _HL.biblioteca()
                    for _tipo, _pid in (har.get("progressions") or {}).items():
                        try:
                            _HL.por_id(bib, str(_pid))
                        except KeyError as e:
                            _err(errores, "A113: %s.harmony.progressions: %s"
                                 % (pref, e))

    # Aviso de rendimiento: pistas original no admiten overrides; nada que hacer
    # aquí — solo recordatorio informativo si TODO el álbum es original.
    if pistas and all(p.get("perfil") == "original" for p in pistas if isinstance(p, dict)):
        avisos.append("W-A2: todas las pistas declaran perfil 'original' — el álbum "
                      "no usará los motores mejorados (decisión legítima del compositor)")

    if errores:
        raise AlbumInvalido(errores)
    return avisos


def cargar_album(ruta):
    """Carga y valida un album.json desde disco. Devuelve (spec, avisos).

    ``ruta`` es la ruta del album.json; las rutas de docs se resuelven contra
    su directorio (raíz del álbum) en el planificador.
    """
    import json
    from pathlib import Path
    ruta = Path(ruta)
    if not ruta.is_file():
        raise AlbumInvalido(["A114: no existe el album.json: %s" % ruta])
    try:
        spec = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise AlbumInvalido(["A115: album.json no es JSON UTF-8 válido: %s" % e])
    avisos = validar_album(spec)
    return spec, avisos
