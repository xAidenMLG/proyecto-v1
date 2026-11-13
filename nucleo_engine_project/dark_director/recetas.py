"""Recetas de identidad — nivel N1 de la escalera de precedencia (§2.3 rev. 3.1).

ESTADO FASE 0 — esqueleto deliberadamente sin datos:
  - Ninguna receta existe todavía como código. ``load_receta()`` lanza
    :class:`RecetaNoDefinida` para las 3 identidades (estado documentado por la
    suite de pruebas).
  - En Fase 1 se registrará ``dark_director/identities/<id>.py`` con los
    defaults REALES (N1): pistas base, BPM default, capas de batería por nivel
    drums, sets de bajo, voicings y velocity base por tipo de sección, focus
    por defecto y ``D_receta`` (density base por tipo de sección, §2.6.5).
  - PROHIBIDO inventar cifras de receta aquí (contrato §5.0: los supuestos son
    provisionales y etiquetados; §2.6.5: los fixtures de test no fijan
    ``D_receta`` con valores inventados).

El mecanismo de fail-fast de §2.6.5 (obligaciones de implementación) sí está
activo: registrar una receta incompleta o fuera de rango detiene la carga.

FASE 2 (RESPUESTA 09 §6.3, delta C5): además del fail-fast de D_receta, las
recetas que declaran una tabla ``BLOQUES`` (bloques por type × instrumento)
se verifican al registrarlas: completitud para todo el set base × los 7 types,
estilos dentro del vocabulario REAL del motor, y from_bar/to_bar/seed/velocity
con tipos válidos. Una receta incoherente NO se registra (la carga se detiene).
"""

from . import contract
from . import inicializacion

#: types para los que la receta DEBE declarar D_receta (§2.6.5: los 7 del contrato)
REQUIRED_TYPES = contract.SECTION_TYPES

#: identidades con receta prevista en v1 (§2.1)
IDENTITIES = contract.IDENTITIES

#: registro de recetas reales; Fase 0 lo mantiene VACÍO (estado documentado)
RECETAS_REGISTRADAS = {}


class RecetaError(RuntimeError):
    """Problema de receta (fallo interno de receta, no es código E/W del contrato)."""


class RecetaNoDefinida(RecetaError):
    """La identidad aún no tiene receta registrada (estado normal en Fase 0)."""


def verificar_completitud(tabla):
    """Verifica la completitud de una tabla ``D_receta`` (§2.6.5):
    exactamente los 7 types del contrato, cada uno numérico (no bool) en [0, 1].
    Devuelve una tupla de problemas (vacía si la tabla es completa y válida)."""
    problemas = []
    for t in REQUIRED_TYPES:
        if t not in tabla:
            problemas.append(f"falta D_receta para el type '{t}'")
    for t, v in tabla.items():
        if t not in REQUIRED_TYPES:
            problemas.append(f"type fuera del contrato: '{t}'")
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            problemas.append(f"D_receta['{t}'] no es numérico: {v!r}")
        elif not (0.0 <= float(v) <= 1.0):
            problemas.append(f"D_receta['{t}'] fuera de [0, 1]: {v!r}")
    return tuple(problemas)


def registrar_receta(identity, tabla_d_receta):
    """Punto de registro para Fase 1 (fail-fast de §2.6.5): una receta incompleta
    o fuera de rango NO se registra (la carga se detiene; es fallo interno de
    receta, nunca un código E/W — las recetas no son entrada del compositor)."""
    if identity not in IDENTITIES:
        raise RecetaError(f"identidad fuera del contrato: {identity!r}")
    problemas = verificar_completitud(tabla_d_receta)
    if problemas:
        raise RecetaError("receta incompleta o fuera de rango: " + "; ".join(problemas))
    RECETAS_REGISTRADAS[identity] = dict(tabla_d_receta)
    return RECETAS_REGISTRADAS[identity]


def load_receta(identity):
    """Carga la receta N1 de una identidad. En Fase 0 lanza RecetaNoDefinida
    para las 3 identidades (ninguna receta existe todavía como código)."""
    if identity not in IDENTITIES:
        raise RecetaError(f"identidad fuera del contrato: {identity!r}")
    if identity not in RECETAS_REGISTRADAS:
        raise RecetaNoDefinida(
            f"la receta de '{identity}' no está registrada todavía "
            "(Fase 0: esqueleto; Fase 1: registrar dark_director/identities/<id>.py "
            "con los defaults reales N1)"
        )
    return RECETAS_REGISTRADAS[identity]


# --------------------------------------------------------------------------- C5
#: Vocabulario de estilos REALES por rol (fuente: ``audit/midi_forge/forge/styles.py``,
#: STYLE_SCHEMA, verificado línea a línea en la auditoría de RESPUESTA 09 §1/§2;
#: copia estática para que el registro fail-fast NO importe el motor —
#: independencia DMD↔Forge, restricción R6). Solo lectura, nunca se amplía aquí.
ESTILOS_POR_ROL = {
    "pad": ("sustain", "none"),
    "strings": ("sustain", "stabs", "none"),
    "bass": ("pattern", "long", "none"),
    "keys": ("hold", "broken", "tail", "none"),
    "mallet": ("replies", "pings", "none"),
    "lead": ("auto", "phrases", "generative", "hold", "none"),
    "drums": ("pattern", "none"),
}


def verificar_tabla_bloques(mod):
    """Delta C5 (RESPUESTA 09 §6.3): coherencia estructural de la tabla
    ``BLOQUES[type][instrumento]`` de una receta (módulo-dato). Devuelve una
    tupla de problemas (vacía si la tabla es coherente o si la receta no declara
    tabla — estilo dark_triphop). Verifica:
      - fila para TODO instrumento del SET_BASE en cada uno de los 7 types;
      - ningún id fuera del catálogo de 8 ni fuera del SET_BASE;
      - estilo existente para el rol del instrumento (vocabulario del motor);
      - velocity escalar positiva o par [v0, v1] (rampa del motor);
      - from_bar int ≥ 0; to_bar None o int > from_bar; seed None o int ≥ 0.
    Los PARÁMETROS internos de cada bloque no se validan aquí (se validan en
    tiempo de compilación por el adaptador/motor: estilo inválido → warn y
    default del motor); C5 garantiza la ESTRUCTURA, no cada valor musical."""
    problemas = []
    tabla = getattr(mod, "BLOQUES", None)
    if tabla is None:
        return tuple(problemas)          # receta sin tabla (estilo dark_triphop)
    if not isinstance(tabla, dict):
        return ("BLOQUES debe ser un dict type → {instrumento: bloque}",)
    base = tuple(getattr(mod, "SET_BASE", ()))

    def _es_num(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    # completitud: TODOS los 7 types del contrato (un type ausente es un error)
    for t in REQUIRED_TYPES:
        if t not in tabla:
            problemas.append(f"BLOQUES sin fila para el type '{t}'")
    for t, fila in tabla.items():
        if t not in REQUIRED_TYPES:
            problemas.append(f"BLOQUES type fuera del contrato: '{t}'")
            continue
        if not isinstance(fila, dict):
            problemas.append(f"BLOQUES['{t}'] debe ser un dict instrumento → bloque")
            continue
        for iid in base:
            if iid not in fila:
                problemas.append(f"BLOQUES['{t}'] sin fila para el instrumento base '{iid}'")
        for iid, b in fila.items():
            if iid not in contract.INSTRUMENT_IDS:
                problemas.append(f"BLOQUES['{t}']['{iid}'] fuera del catálogo de 8")
                continue
            if iid not in base:
                problemas.append(f"BLOQUES['{t}'] fila para '{iid}' fuera del SET_BASE (no se aplicaría)")
                continue
            if not isinstance(b, dict):
                problemas.append(f"BLOQUES['{t}']['{iid}'] debe ser un dict")
                continue
            rol = inicializacion.INIT_CATALOG[iid]["rol"]
            estilo = b.get("style")
            if estilo not in ESTILOS_POR_ROL.get(rol, ()):
                problemas.append(f"BLOQUES['{t}']['{iid}'] estilo {estilo!r} no existe para el rol '{rol}'")
            enabled = b.get("enabled", True)
            if not isinstance(enabled, bool):
                problemas.append(f"BLOQUES['{t}']['{iid}'] 'enabled' debe ser bool")
            vel = b.get("velocity")
            if vel is not None:
                escalar = _es_num(vel) and vel > 0
                rampa = (isinstance(vel, (list, tuple)) and len(vel) == 2
                         and all(_es_num(x) and x > 0 for x in vel))
                if not (escalar or rampa):
                    problemas.append(f"BLOQUES['{t}']['{iid}'] velocity inválida: {vel!r} "
                                     "(se espera escalar > 0 o par [v0, v1])")
            fb = b.get("from_bar", 0)
            if not isinstance(fb, int) or isinstance(fb, bool) or fb < 0:
                problemas.append(f"BLOQUES['{t}']['{iid}'] from_bar debe ser int ≥ 0: {fb!r}")
            tb = b.get("to_bar")
            if tb is not None and (not isinstance(tb, int) or isinstance(tb, bool) or tb <= fb):
                problemas.append(f"BLOQUES['{t}']['{iid}'] to_bar debe ser None o int > from_bar: {tb!r}")
            seed = b.get("seed")
            if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool) or seed < 0):
                problemas.append(f"BLOQUES['{t}']['{iid}'] seed debe ser None o int ≥ 0: {seed!r}")
    return tuple(problemas)
