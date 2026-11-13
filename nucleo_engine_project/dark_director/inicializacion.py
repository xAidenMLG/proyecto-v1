"""Inicialización de pistas ``enabled=true`` fuera del set base (§2.5.1 rev. 3.1).

Fase 0: el catálogo §2.5.1 vive aquí como DATO y la decisión de seguridad como
función pura. La EMISIÓN del bloque inicializado (escribir el bloque con sus
parámetros en cada sección) es trabajo del compilador (Fase 1): este módulo no
emite bloques ni traduce música.

Fuentes exclusivamente existentes en MIDI Forge (§2.5.1, principio): roles y
programas del catálogo, perfiles de ``voicing.py``, ``styles.ROLE_DEFAULTS`` y
``styles.ROLE_VEL_OFFSET``, y los defaults que ``adapter.finalize_project``
aplica a todo bloque. El compilador no inventa ningún valor.
"""

from . import contract

#: catálogo §2.5.1 (dato de contrato; el orden de las claves replica la tabla)
INIT_CATALOG = {
    "sax_tenor": {"rol": "lead", "programa": (66,), "programa_inicializacion": 66,
                  "bloque": "generative", "requiere_lead": False, "depende_receta": False},
    "rhodes": {"rol": "keys", "programa": (4,), "programa_inicializacion": 4,
               "bloque": "hold", "requiere_lead": False, "depende_receta": False},
    "piano": {"rol": "keys", "programa": (0,), "programa_inicializacion": 0,
              "bloque": "hold", "requiere_lead": False, "depende_receta": False},
    # §2.5.1: de los dos programas pad del catálogo (91/89) la inicialización fija 91
    "pad": {"rol": "pad", "programa": (91, 89), "programa_inicializacion": 91,
            "bloque": "sustain", "requiere_lead": False, "depende_receta": False},
    "strings": {"rol": "strings", "programa": (50,), "programa_inicializacion": 50,
                "bloque": "sustain", "requiere_lead": False, "depende_receta": False},
    # §2.5.1: requiere una pista lead existente (base o enabled=true); sin lead → E114
    "vibraphone": {"rol": "mallet", "programa": (11,), "programa_inicializacion": 11,
                   "bloque": "replies", "requiere_lead": True, "depende_receta": False},
    # §2.5.1: bass/drums son base en las 3 identidades v1 → rama inalcanzable;
    # una receta futura sin set de bajo / capas de batería → E114
    "bass": {"rol": "bass", "programa": (38, 32), "programa_inicializacion": None,
             "bloque": "pattern", "requiere_lead": False, "depende_receta": True},
    "drums": {"rol": "drums", "programa": ("ch10",), "programa_inicializacion": None,
              "bloque": "capas por nivel", "requiere_lead": False, "depende_receta": True},
}

#: doctrina E114 (rev. 3.1 §2.5.1): bloquea siempre, nunca bloque incompleto
E114_DOCTRINA = "bloquea siempre: no se emite pista parcial ni bloque incompleto"


def estado_inicializacion(inst_id, en_base, existe_lead, receta_da_datos=True):
    """Decisión de seguridad de §2.5.1 (función pura; no emite bloque).

    Devuelve (estado, detalle):
      ("E110", …)     id fuera del catálogo de 8 (sigue siendo E110, no E114)
      ("ok-base", …)  la pista ya es base: ``enabled=true`` no tiene efecto
                      adicional — sin error ni aviso (§2.5.1)
      ("E114", …)     inicialización insegura (vibráfono sin lead; bass/drums
                      sin datos de receta) — bloquea siempre
      ("ok", …)       inicializable de forma determinista con el catálogo
    """
    if inst_id not in contract.INSTRUMENT_IDS:
        return ("E110", f"id fuera del catálogo de 8: {inst_id!r}")
    if en_base:
        return ("ok-base", "pista base gobernada por la receta N1; enabled=true sin efecto adicional (§2.5.1)")
    spec = INIT_CATALOG[inst_id]
    if spec["requiere_lead"] and not existe_lead:
        return ("E114", f"vibráfono inicializado sin pista lead existente en el proyecto; {E114_DOCTRINA}")
    if spec["depende_receta"] and not receta_da_datos:
        return ("E114", f"receta sin datos para {inst_id} (set de bajo / capas de batería); {E114_DOCTRINA}")
    return ("ok", f"inicialización determinista: rol={spec['rol']}, bloque={spec['bloque']}")
