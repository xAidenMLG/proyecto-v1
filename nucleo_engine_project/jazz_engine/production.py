"""Production Profiles — FASE 6.

Presets de producción reproducibles dentro del universo DARK TRIP HOP. NO son
identidades musicales nuevas: cada perfil es una CONFIGURACIÓN EXACTA de los
motores existentes (jazz_engine) que reproduce uno de los comportamientos
aprobados en FASE 5 (escucha del usuario, composición «Nocturno Terminal»).

Fuente de cada preset: la configuración exacta del comparativo FASE 5
(``output/fase5_comparativos/config_*.json``). Regla de oro (misión §5):

  - ``original``  : camino ORIGINAL — sin jazz_engine (delegación byte a byte
    a forge). Nunca depende de los motores mejorados.
  - el resto      : preset de motores sobre la arquitectura existente.

API:
  - ``nombres()``                 → tupla ordenada de nombres válidos.
  - ``resolver(nombre)``          → dict de config (copia profunda) o KeyError.
  - ``aplicar(config)``           → fusiona preset como BASE bajo la config del
    usuario (la config explícita siempre gana). Valida y lanza ValueError con
    mensaje claro ante nombres desconocidos.

Este módulo es puro dato + funciones puras; el mecanismo de fusión vive en
``coordinator.normalize_config`` (único punto de normalización de config).
"""

#: Perfiles oficiales de producción (nombres aprobados en la misión FASE 6 §5).
#: ``None`` = camino ORIGINAL: render sin motores (config None → forge puro).
PRODUCTION_PROFILES = {
    "original":    None,
    "sax":         {"engines": {"sax": True, "rhodes": False, "drums": False, "vibes": False}},
    "sax_rhodes":  {"engines": {"sax": True, "rhodes": True, "drums": False, "vibes": False}},
    "drums":       {"engines": {"sax": False, "rhodes": False, "drums": True, "vibes": False}},
    "sax_vibes":   {"engines": {"sax": True, "rhodes": False, "drums": False, "vibes": True}},
    "full":        {"engines": {"sax": True, "rhodes": True, "drums": True, "vibes": True}},
    "atmospheric": {"engines": {"sax": True, "rhodes": True, "drums": True, "vibes": True},
                    "variation": "atmospheric"},
}

#: Perfil por defecto cuando no se declara ninguno (paridad con FASE 5: config
#: sin ``production`` → todos los motores, variación balanced).
DEFAULT_PROFILE = "full"


def nombres():
    """Nombres válidos, en orden canónico."""
    return tuple(PRODUCTION_PROFILES)


def es_original(nombre):
    """True si el perfil exige el camino ORIGINAL (sin jazz_engine)."""
    return nombre == "original" and PRODUCTION_PROFILES.get("original", "x") is None


def resolver(nombre):
    """Config base del perfil (copia profunda; los presets son inmutables en la
    práctica). KeyError con mensaje claro si el nombre es desconocido."""
    if nombre not in PRODUCTION_PROFILES:
        raise KeyError("perfil de producción desconocido: %r (válidos: %s)"
                       % (nombre, ", ".join(nombres())))
    preset = PRODUCTION_PROFILES[nombre]
    import copy
    return copy.deepcopy(preset)


def aplicar(config):
    """Fusiona el preset del perfil como BASE bajo ``config`` del usuario.

    Devuelve (nombre_perfil, config_fusionada). La config explícita del usuario
    gana sobre el preset (misma clave → valor del usuario). Si ``config`` no
    declara ``production`` se asume DEFAULT_PROFILE. Ante un nombre desconocido
    lanza ValueError con la lista de válidos (error claro, misión §5.6).
    """
    nombre = (config or {}).get("production") or DEFAULT_PROFILE
    if nombre not in PRODUCTION_PROFILES:
        raise ValueError("perfil de producción desconocido: %r (válidos: %s)"
                         % (nombre, ", ".join(nombres())))
    preset = resolver(nombre) or {}
    fusionada = dict(preset)
    for k, v in (config or {}).items():
        if k == "production":
            continue
        if k == "engines" and isinstance(v, dict) and isinstance(fusionada.get("engines"), dict):
            fusionada["engines"] = dict(fusionada["engines"], **v)
        else:
            fusionada[k] = v
    return nombre, fusionada
