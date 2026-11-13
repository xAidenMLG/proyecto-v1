"""Módulo D — randomizador coherente.

NO tira dados independientes por cada lista: aplica TRES clases de reglas
sobre un generador determinista (``random.Random(seed)``):

  1. Hard Constraints   — decisiones fijadas se respetan EXACTO.
  2. Compatibility Rules — evitan combinaciones contradictorias (rango BPM de
     la identidad, dominante mayor en menor, doom con ritmo armónico ≥ 2,
     protagonista sonando, atmósfera coherente con la densidad...).
  3. Weighted Preferences — preferencias probabilísticas por mood/groove/
     atmósfera (una composición melancólica FAVORECE ciertas curvas, no las
     impone).

Salida: ``ResolvedPlan`` con el valor concreto de cada eje automático, las
decisiones libres y un LOG de explicabilidad (qué decidió el usuario, qué
Composer, qué se dejó libre, qué reglas aplicaron y qué opciones se
descartaron). Mismo seed + mismas decisiones → mismo plan, bit a bit.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import model
from .harmony import parse_key, HarmonyError

# --------------------------------------------------------------------------
# Pesos por mood (Weighted Preferences). No son verdad absoluta: son gustos
# ponderados que el nivel de diversidad afloja o endurece.
# --------------------------------------------------------------------------

MOODS = ("melancholic", "dark", "hopeful", "tense", "neutral")

#: Tonalidades candidatas por mood: (etiqueta, peso).
KEY_POOLS = {
    "melancholic": [("A minor", 3), ("D minor", 3), ("E minor", 2), ("C minor", 2),
                    ("F minor", 1), ("B minor", 1), ("G minor", 2)],
    "dark": [("D minor", 2), ("C minor", 3), ("F minor", 2), ("G minor", 2),
             ("Bb minor", 1), ("A minor", 1), ("Eb minor", 1)],
    "hopeful": [("C major", 3), ("G major", 3), ("D major", 2), ("A major", 2),
                ("F major", 2), ("Eb major", 1)],
    "tense": [("D minor", 2), ("Eb minor", 1), ("F# minor", 1), ("C minor", 2),
              ("A minor", 1), ("D dorian", 1), ("E phrygian", 1)],
    "neutral": [("A minor", 2), ("C major", 2), ("D minor", 2), ("F major", 1),
                ("G major", 1), ("E minor", 1)],
}

#: Lenguaje armónico por mood: {valor: peso}.
LANGUAGE_POOLS = {
    "melancholic": {"pop_dream_pop": 6, "hybrid": 3, "experimental": 0.5},
    "dark": {"hybrid": 6, "pop_dream_pop": 2, "experimental": 2},
    "hopeful": {"pop_dream_pop": 8, "hybrid": 1, "experimental": 0},
    "tense": {"hybrid": 5, "experimental": 4, "pop_dream_pop": 1},
    "neutral": {"pop_dream_pop": 3, "hybrid": 3, "experimental": 1},
}

#: Accesibilidad por mood.
ACCESS_POOLS = {
    "melancholic": {"balanced": 6, "commercial": 3, "experimental": 1},
    "dark": {"balanced": 5, "experimental": 4, "commercial": 1},
    "hopeful": {"commercial": 6, "balanced": 4, "experimental": 0.5},
    "tense": {"balanced": 4, "experimental": 5, "commercial": 1},
    "neutral": {"balanced": 7, "commercial": 2, "experimental": 1},
}

#: Atmósfera por mood.
ATMOS_POOLS = {
    "melancholic": {"spacious": 5, "medium": 4, "dense": 1},
    "dark": {"dense": 3, "medium": 4, "spacious": 3},
    "hopeful": {"medium": 4, "spacious": 3, "dense": 3},
    "tense": {"dense": 4, "medium": 4, "spacious": 2},
    "neutral": {"medium": 5, "spacious": 3, "dense": 2},
}

#: Groove por mood.
GROOVE_POOLS = {
    "melancholic": {"laid_back": 5, "steady": 4, "driving": 1},
    "dark": {"steady": 4, "driving": 3, "laid_back": 3},
    "hopeful": {"driving": 4, "steady": 4, "laid_back": 2},
    "tense": {"driving": 4, "steady": 3, "laid_back": 3},
    "neutral": {"steady": 5, "laid_back": 3, "driving": 2},
}

#: Perfiles de producción por atmósfera (opción de Studio, no del doc).
PROD_POOLS = {
    "spacious": {"atmospheric": 5, "full": 3, "sax_rhodes": 2, "sax_vibes": 2},
    "medium": {"full": 5, "sax_rhodes": 3, "sax_vibes": 2, "atmospheric": 2, "drums": 1},
    "dense": {"full": 6, "drums": 2, "sax_rhodes": 2, "atmospheric": 1},
}

#: Identidades (la identidad activa del ecosistema pesa más).
IDENTITY_POOLS = {"dark_triphop": 8, "doom_triphop": 2, "doom_dark_jazz": 1}

#: Plantillas estructurales por mood (modo structure=auto). Bars con jitter ±.
STRUCTURE_TEMPLATES = {
    "melancholic": [
        [("intro", 4), ("verse", 16), ("pre_chorus", 8), ("chorus", 16), ("verse", 16),
         ("chorus", 16), ("break", 8), ("outro", 8)],
        [("intro", 8), ("verse", 16), ("chorus", 16), ("verse", 16), ("chorus", 16),
         ("bridge", 8), ("chorus", 8), ("outro", 8)],
    ],
    "dark": [
        [("intro", 8), ("verse", 16), ("pre_chorus", 8), ("chorus", 16), ("break", 8),
         ("verse", 16), ("chorus", 16), ("outro", 8)],
        [("intro", 4), ("verse", 12), ("chorus", 16), ("bridge", 8), ("chorus", 12), ("outro", 8)],
    ],
    "hopeful": [
        [("intro", 4), ("verse", 16), ("pre_chorus", 8), ("chorus", 16), ("verse", 16),
         ("pre_chorus", 8), ("chorus", 16), ("outro", 8)],
        [("intro", 8), ("verse", 16), ("chorus", 16), ("bridge", 8), ("chorus", 16), ("outro", 4)],
    ],
    "tense": [
        [("intro", 8), ("verse", 16), ("break", 8), ("chorus", 16), ("bridge", 8),
         ("chorus", 16), ("outro", 8)],
    ],
    "neutral": [
        [("intro", 8), ("verse", 16), ("chorus", 16), ("verse", 16), ("chorus", 16), ("outro", 8)],
    ],
}

#: Plantillas de progresión guiada por mood y función de sección (numerales).
#: Se resuelven con la tonalidad elegida (dominante mayor incluida).
PROG_TEMPLATES = {
    "melancholic": {
        "intro": ["i", "i - III", "VI"],
        "verse": ["i - III - VII - VI", "i - VII - III - VI", "i - iv - VII - III"],
        "pre_chorus": ["iv - VII", "iv - VII - III - VI", "VI - VII"],
        "chorus": ["VI - VII - i - i", "III - VII - VI - VII", "VI - IV - i - V", "bVI - bVII - i - i"],
        "bridge": ["iv - VI", "ii0 - V - i", "iv - VI - VII - V"],
        "break": ["i - VI", "VI - III"],
        "outro": ["i - VI", "VI - i", "i"],
    },
    "dark": {
        "intro": ["i", "i - bVI", "i - bII"],
        "verse": ["i - i - bVI - bVII", "i - bVI - i - bVII", "i - iim7b5 - bVI - V7"],
        "pre_chorus": ["bVI - bVII", "iv - V7"],
        "chorus": ["bVI - bVII - i - i", "bIII - bVII - bVI - V7", "i - bVII - bVI - V7"],
        "bridge": ["iv - bVII", "iim7b5 - V7", "bII - bVII"],
        "break": ["i - bVI", "i"],
        "outro": ["i - bVI", "i", "i - bVII - i"],
    },
    "hopeful": {
        "intro": ["I", "I - V"],
        "verse": ["I - V - vi - IV", "I - vi - IV - V", "vi - IV - I - V"],
        "pre_chorus": ["IV - V", "ii - IV - V"],
        "chorus": ["IV - I - V - vi", "I - IV - vi - V", "vi - IV - I - V"],
        "bridge": ["iii - IV - I - IV", "ii - V", "IV - V - I"],
        "break": ["IV - I", "I - IV"],
        "outro": ["I - IV", "I", "I - V - I"],
    },
    "tense": {
        "intro": ["i", "i - bII"],
        "verse": ["i - iim7b5 - i - V7", "i - bII - i - bVII", "i - #iv0 - bII - V7"],
        "pre_chorus": ["bII - V7", "iv - V7"],
        "chorus": ["bII - i - bVII - V7", "i - bII - i - V7", "bVI - V7 - i - i"],
        "bridge": ["iim7b5 - V7", "bII - bIII - bII - i"],
        "break": ["i - iim7b5"],
        "outro": ["i - V7", "i"],
    },
    "neutral": {
        "intro": ["i", "I"],
        "verse": ["i - III - VII - VI", "I - V - vi - IV"],
        "pre_chorus": ["IV - V", "iv - VII"],
        "chorus": ["VI - VII - i - i", "IV - I - V - vi"],
        "bridge": ["iv - VI", "ii - V"],
        "break": ["i - VI"],
        "outro": ["i - VI", "I"],
    },
}

#: Tonos relativos para modo álbum (rotación de tonalidades relacionadas).
RELATED_KEYS_MINOR = ["A minor", "D minor", "E minor", "G minor", "C minor", "F minor", "B minor"]
RELATED_KEYS_MAJOR = ["C major", "G major", "D major", "A major", "F major", "Eb major", "Bb major"]


@dataclass
class ResolvedPlan:
    """Plan resuelto: valor concreto por eje + log de explicabilidad."""
    values: Dict[str, Any] = field(default_factory=dict)
    free_axes: List[str] = field(default_factory=list)
    log: List[dict] = field(default_factory=list)
    seed_used: Optional[int] = None

    def to_dict(self) -> dict:
        return {"seed_used": self.seed_used, "values": self.values,
                "free_axes": self.free_axes, "log": self.log}


def _weighted(rng: random.Random, pool: Dict[str, float], flatten: float) -> Tuple[Any, List[str]]:
    """Elección ponderada; ``flatten`` (0–1) aplana pesos (diversidad alta).

    Devuelve ``(valor_elegido, descartadas)``: la lista de alternativas con su
    peso original (orden de la pool), para el registro de explicabilidad
    (D-08 del manual: "qué se descartó y por qué" = peso menor o sorteo).
    Consume EXACTAMENTE un ``rng.random()`` (el plan es función del seed).
    """
    items = [(k, max(0.01, float(v)) ** (1.0 - flatten)) for k, v in pool.items() if float(v) > 0]
    if not items:
        return None, []
    total = sum(w for _, w in items)
    r = rng.random() * total
    acc = 0.0
    elegido = items[-1][0]
    for k, w in items:
        acc += w
        if r <= acc:
            elegido = k
            break
    descartadas = [f"{k} (peso {float(pool.get(k, 0)):g})" for k, _ in items if k != elegido]
    return elegido, descartadas


def _log_entry(plan: ResolvedPlan, axis: str, state: str, value: Any,
               reason: str, discarded: Optional[List[str]] = None, rules: Optional[List[str]] = None):
    plan.log.append({"axis": axis, "estado": state, "valor": value,
                     "razon": reason, "descartadas": discarded or [],
                     "reglas": rules or []})


def resolve(project: model.ComposerProject, manifest: Optional[dict] = None,
            seed_override: Optional[int] = None) -> ResolvedPlan:
    """Resuelve el plan completo de decisiones de un proyecto.

    Nunca modifica una decisión fijada. Si una decisión fijada choca con una
    regla de compatibilidad, se respeta el valor fijado y se deja una entrada
    de conflicto en el log (los conflictos duros los enumera builder.py).
    """
    rng = random.Random(seed_override)
    plan = ResolvedPlan()
    dec = project.decisions

    def state_of(eje: str) -> str:
        d = dec.get(eje) or model.decision(model.FREE)
        return d.get("mode", model.FREE)

    flatten = {"restrained": 0.0, "balanced": 0.45, "adventurous": 0.8}.get(project.diversity, 0.45)

    # --- seed ----------------------------------------------------------------
    # La semilla INTERNA del plan siempre existe (el randomizador necesita una
    # fuente determinista). Libre = el doc NO lleva global.seed: el motor usa
    # la suya (la reproducibilidad doc a doc pasa a depender del --seed de
    # Studio/produce.py: se avisa con honestidad).
    seed_val = project.fixed_value("seed")
    if seed_val is not None:
        _log_entry(plan, "seed", "fixed", seed_val, "decisión del usuario")
    else:
        seed_val = seed_override if seed_override is not None else rng.randrange(0, 1_000_000)
        if state_of("seed") == model.FREE:
            plan.free_axes.append("seed")
            _log_entry(plan, "seed", "free", seed_val,
                       "semilla INTERNA del plan de Composer (el doc NO lleva global.seed: "
                       "el motor usará la suya; para reproducir, pasa --seed a Studio/produce.py)")
        else:
            _log_entry(plan, "seed", "auto", seed_val,
                       "semilla generada deterministamente (guardada en global.seed para reproducir)")
    plan.seed_used = int(seed_val)
    # rng principal de decisiones: SIEMPRE se recrea desde seed_used para que
    # el plan completo sea función exacta de (decisiones, seed_used).
    rng = random.Random(int(plan.seed_used))
    mood_dec = dec.get("mood") or model.decision(model.FIXED, "neutral")
    mood_estado = mood_dec.get("mode", model.FIXED)
    if mood_estado == model.FIXED and mood_dec.get("value"):
        mood = str(mood_dec.get("value"))
        _log_entry(plan, "mood", "fixed", mood,
                   "decisión del usuario · NO va al doc: define las preferencias ponderadas "
                   "(tonalidades, lenguaje, atmósfera…) con las que Composer elige")
    else:
        mood = "neutral"
        if mood_estado == model.AUTO:
            _log_entry(plan, "mood", "auto", "neutral",
                       "Composer usa el mood neutro por defecto (es la llave de las pools: "
                       "sin preferencia del usuario no se sesga nada)")
        else:
            _log_entry(plan, "mood", "free", None,
                       "sin mood: pools neutras · NO va al doc (preferencia interna de Composer)")

    # Ejes que el contrato EXIGE en el documento (E103): 'free' no existe para
    # ellos. Si un proyecto antiguo/API directa los trae libres, se degradan a
    # auto con nota honesta en el log (C2 de la auditoría).
    for eje_oblig in ("identity", "accessibility", "language"):
        if (dec.get(eje_oblig) or {}).get("mode") == model.FREE:
            dec[eje_oblig] = model.decision(model.AUTO)
            _log_entry(plan, eje_oblig, "auto", None,
                       f"'free' no existe para '{eje_oblig}' (el contrato lo exige): "
                       "degradado a automático")

    # --- identity --------------------------------------------------------------
    identity = project.fixed_value("identity")
    if identity:
        _log_entry(plan, "identity", "fixed", identity, "decisión del usuario")
    else:
        identity, desc_ident = _weighted(rng, IDENTITY_POOLS, flatten * 0.5)
        plan.values["identity"] = identity
        _log_entry(plan, "identity", "auto", identity,
                   "identidad ponderada (dark_triphop es la identidad activa del ecosistema)",
                   discarded=desc_ident)
    receta = ((manifest or {}).get("recetas") or {}).get(identity) or {}
    bpm_lo, bpm_hi = receta.get("bpm_rango", (70, 96))

    # --- mood dependientes ------------------------------------------------------
    plan.values["mood"] = mood          # preferencia (nunca en el doc; visible en manifest)
    bpm_fijo = project.fixed_value("bpm")
    for eje, pool_by_mood in (("accessibility", ACCESS_POOLS), ("language", LANGUAGE_POOLS),
                              ("atmosphere", ATMOS_POOLS), ("groove", GROOVE_POOLS)):
        st = state_of(eje)
        if st == model.FIXED:
            plan.values[eje] = project.fixed_value(eje)
            extra = ""
            if eje == "groove":
                extra = (" · el groove NO es un campo del contrato: no altera el BPM fijado "
                         "ni llega al motor como parámetro; su único efecto real aquí es el "
                         "sesgo de la curva de BPM automático (inactivo: BPM fijado)")
            elif eje == "mood":
                extra = ""
            _log_entry(plan, eje, "fixed", plan.values[eje], "decisión del usuario" + extra)
        elif st == model.AUTO:
            pool = pool_by_mood.get(mood, pool_by_mood["neutral"])
            nota_pool = f"preferencia ponderada por mood '{mood}'"
            if eje == "groove" and bpm_fijo is not None:
                # compatibilidad con el TEMPO FIJADO (regla suave, nunca corrección):
                # el groove no toca el BPM; solo se moderan los extremos poco
                # habituales para ese tempo (pesos, no imposiciones).
                pool = dict(pool)
                if bpm_lo <= bpm_fijo <= bpm_hi:
                    zona = (bpm_fijo - bpm_lo) / max(1, (bpm_hi - bpm_lo))
                    if zona < 0.34:
                        pool["driving"] = float(pool.get("driving", 0)) * 0.35
                    elif zona > 0.67:
                        pool["laid_back"] = float(pool.get("laid_back", 0)) * 0.5
                nota_pool = (f"preferencia ponderada por mood '{mood}' moderada por el BPM "
                             f"FIJADO ({bpm_fijo}): el groove no cambia el tempo")
            elif eje == "groove":
                nota_pool = ("preferencia ponderada por mood '" + mood + "' · si el BPM fuera "
                             "automático, este groove sesgaría su curva (el groove no es tempo)")
            v, desc = _weighted(rng, pool, flatten)
            plan.values[eje] = v
            _log_entry(plan, eje, "auto", v, nota_pool +
                       (" · NO llega al doc" if eje in ("groove", "atmosphere") else ""),
                       discarded=desc)
        else:
            if eje == "atmosphere":
                _log_entry(plan, eje, "free", None,
                           "sin preferencia de atmósfera · NO es un campo del doc: solo sesga "
                           "el perfil de producción y los avisos de coherencia")
            elif eje == "groove":
                _log_entry(plan, eje, "free", None,
                           "sin preferencia de groove · NO es un campo del doc ni parámetro del motor")
            else:
                plan.free_axes.append(eje)
                _log_entry(plan, eje, "free", None,
                           "el motor DMD decide (no se escribe el campo)")

    # --- bpm ---------------------------------------------------------------------
    # Libre = el motor decide con su receta (BPM_DEFAULT): NO se escribe
    # global.bpm. Fijado se respeta EXACTO; automático usa la curva del mood.
    bpm_mode = (dec.get("bpm") or {}).get("mode")
    bpm = project.fixed_value("bpm")
    if bpm_mode == model.FREE and bpm is None:
        plan.free_axes.append("bpm")
        _log_entry(plan, "bpm", "free", None,
                   "el motor DMD decide el tempo con su receta (BPM_DEFAULT): "
                   "no se escribe global.bpm")
    elif bpm is not None:
        in_range = bpm_lo <= bpm <= bpm_hi
        _log_entry(plan, "bpm", "fixed", bpm,
                   "decisión del usuario" + ("" if in_range else
                   f" — FUERA del rango típico de {identity} [{bpm_lo}, {bpm_hi}] (W401); "
                   "se respeta: el usuario manda"))
        plan.values["bpm"] = int(bpm)
    else:
        # curva por mood/groove: melancólico abajo, driving arriba
        lo, hi = bpm_lo, bpm_hi
        g = plan.values.get("groove") or "steady"
        if mood in ("melancholic", "dark"):
            bpm_v = rng.randrange(lo, lo + max(1, (hi - lo) // 2))
            zona_elegida = "zona baja (melancólico/oscuro)"
            zonas_desc = ["zona media", "zona alta (driving/esperanzador)"]
        elif g == "driving" or mood == "hopeful":
            bpm_v = rng.randrange((lo + hi) // 2, hi + 1)
            zona_elegida = "zona alta (driving/esperanzador)"
            zonas_desc = ["zona baja (melancólico/oscuro)", "zona media"]
        else:
            bpm_v = rng.randrange(lo + (hi - lo) // 4, lo + (3 * (hi - lo)) // 4 + 1)
            zona_elegida = "zona media"
            zonas_desc = ["zona baja (melancólico/oscuro)", "zona alta (driving/esperanzador)"]
        plan.values["bpm"] = int(bpm_v)
        _log_entry(plan, "bpm", "auto", bpm_v,
                   f"curva por mood '{mood}' dentro del rango típico de {identity} [{bpm_lo}, {bpm_hi}] "
                   f"({zona_elegida}; groove '{g}' sesga la zona)", discarded=zonas_desc)

    # --- key ---------------------------------------------------------------------
    # El contrato EXIGE harmony.key (E103): 'free' no es posible. Si el proyecto
    # llega con free (proyectos antiguos o API directa), se degrada a auto con
    # nota honesta en el log.
    key_lbl = project.fixed_value("key")
    key_mode = (dec.get("key") or {}).get("mode")
    if key_mode == model.FREE:
        _log_entry(plan, "key", "auto", None,
                   "'free' no existe para la tonalidad (el contrato la exige): "
                   "se degrada a automática")
        key_lbl = None
    if key_lbl:
        try:
            keyinfo = parse_key(str(key_lbl))
            key_lbl = keyinfo.label
        except HarmonyError as e:
            _log_entry(plan, "key", "fixed", key_lbl, f"ERROR: {e}")
            raise
        _log_entry(plan, "key", "fixed", key_lbl, "decisión del usuario")
    else:
        key_lbl, desc_key = _weighted(rng, dict(KEY_POOLS.get(mood, KEY_POOLS["neutral"])), flatten)
        plan.values["key"] = key_lbl
        _log_entry(plan, "key", "auto", key_lbl,
                   f"tonalidad favorecida por mood '{mood}' (reglas de compatibilidad: "
                   "menor para oscuro/melancólico, mayor para esperanzador)",
                   discarded=desc_key)
    keyinfo = parse_key(key_lbl)
    plan.values["key"] = key_lbl

    # --- resolución (free por defecto: la receta/el lenguaje deciden) -------------
    st = state_of("resolution")
    if st == model.FIXED:
        plan.values["resolution"] = project.fixed_value("resolution")
        _log_entry(plan, "resolution", "fixed", plan.values["resolution"], "decisión del usuario")
    elif st == model.AUTO:
        # coherente con el mood: modal para híbridos, tonal para pop, cromático experimental
        lang_v = plan.values.get("language") or "hybrid"
        pool = {"pop_dream_pop": {"tonal": 7, "modal": 2, "deceptive": 1},
                "hybrid": {"modal": 5, "tonal": 3, "deceptive": 2},
                "experimental": {"chromatic": 5, "open": 3, "deceptive": 2}}[lang_v]
        v, desc_res = _weighted(rng, pool, flatten)
        plan.values["resolution"] = v
        _log_entry(plan, "resolution", "auto", v, f"coherente con el lenguaje '{lang_v}'",
                   discarded=desc_res)
    else:
        plan.free_axes.append("resolution")
        _log_entry(plan, "resolution", "free", None, "default del lenguaje (sin campo)")

    # --- ritmo armónico global (compatibilidad: doom ≥ 2 evita W402) --------------
    hr = project.fixed_value("harmonic_rhythm_bars")
    hr_default = receta.get("harmonic_rhythm_bars", 1)
    if hr is not None:
        _log_entry(plan, "harmonic_rhythm_bars", "fixed", hr,
                   "decisión del usuario" + (" (W402 probable: menor que el default de la receta)"
                                             if hr < hr_default else ""))
        plan.values["harmonic_rhythm_bars"] = int(hr)
    else:
        # regla de compatibilidad dura: en identidades doom NUNCA se elige 1:1
        pool = {hr_default: 7, min(8, hr_default + 1): 2}
        if not str(identity).startswith("doom") and hr_default > 1:
            pool[max(1, hr_default - 1)] = 1
        v, desc_hr = _weighted(rng, pool, flatten * 0.5)
        plan.values["harmonic_rhythm_bars"] = int(v)
        _log_entry(plan, "harmonic_rhythm_bars", "auto", int(v),
                   f"default de la receta {identity} ({hr_default}) con jitter; "
                   "regla de compatibilidad: nunca menor que la receta en identidades doom",
                   discarded=desc_hr)

    # --- protagonist ------------------------------------------------------------
    # Auto = LEAD de la receta de la identidad (dato REAL introspeccionado,
    # no invención); Free = nada se escribe ni se propone; Fixed "none" = sin
    # protagonista (decisión EXPLÍCITA del usuario, log con estado fixed).
    prot_mode = state_of("protagonist")
    prot = project.fixed_value("protagonist")
    if prot_mode == model.FIXED:
        if prot in (None, "", "none"):
            prot = None
            plan.values["protagonist"] = None
            _log_entry(plan, "protagonist", "fixed", "none",
                       "decisión explícita del usuario: sin protagonista")
        else:
            plan.values["protagonist"] = prot
            _log_entry(plan, "protagonist", "fixed", prot,
                       "decisión del usuario · llega al doc vía instruments.enabled (si está "
                       "fuera del set base) y focus/active por sección (propuesta aceptada o edición manual)")
    elif prot_mode == model.AUTO:
        prot = receta.get("lead") or "sax_tenor"
        _log_entry(plan, "protagonist", "auto", prot,
                   f"LEAD declarado en la receta de {identity} (prioridad funcional)",
                   discarded=[f"{i} (no es el LEAD de la receta)" for i in
                              ((manifest or {}).get("catalogos") or {}).get("instruments", [])
                              if i != prot])
        plan.values["protagonist"] = prot
    else:
        plan.free_axes.append("protagonist")
        _log_entry(plan, "protagonist", "free", None,
                   "sin protagonista: ni enabled ni focos propuestos (libertad total del motor)")
        prot = None
        plan.values["protagonist"] = None

    # --- harmony_mode ---------------------------------------------------------------
    # Instrucción de CONSTRUCCIÓN del documento (no es un campo del contrato):
    #   native  → no se escriben progressions; recetas N1 del motor.
    #   guided  → progresiones explícitas por sección (las secciones marcadas
    #             nativa DENTRO de una composición guiada sí usan N1).
    # 'free' no tiene sentido aquí (no hay campo que omitir): se degrada a auto.
    hm_mode = state_of("harmony_mode")
    if hm_mode == model.FIXED:
        hm = project.fixed_value("harmony_mode") or "guided"
        _log_entry(plan, "harmony_mode", "fixed", hm,
                   "native = recetas N1 del motor · guided = progresiones explícitas por sección")
    else:
        if hm_mode == model.FREE:
            _log_entry(plan, "harmony_mode", "auto", None,
                       "'free' no aplica al modo de armonía (no es un campo del doc): "
                       "degradado a automático")
        hay_guiadas = any(hs.mode == "guided" and (hs.numerals or hs.chords)
                          for hs in project.harmony_sections.values())
        hay_chords = any(hs.chords for hs in project.harmony_sections.values())
        if hay_guiadas:
            hm = "guided"
            razon = ("automático: hay secciones con grados romanos guiados → se respetan "
                     "(el resto puede quedar en receta N1)")
            desc_hm = ["native (se descarta: hay progresiones guiadas escritas)"]
        elif hay_chords:
            hm = "guided"
            razon = ("automático: hay acordes literales por sección (precedencia §2.8, "
                     "posición 1) → modo guiado para el resto de decisiones armónicas")
            desc_hm = ["native (se descarta: hay acordes literales explícitos)"]
        else:
            hm = "native"
            razon = ("automático: sin progresiones ni acordes escritos → recetas N1 del motor "
                     "(guided sin progresiones no tiene efecto)")
            desc_hm = ["guided (se descarta: no hay progresiones que escribir)"]
        _log_entry(plan, "harmony_mode", "auto", hm, razon, discarded=desc_hm)
    plan.values["harmony_mode"] = hm

    # --- spaces ----------------------------------------------------------------------
    # Influencia ESTRUCTURAL, no campo del doc: con estructura automática inserta/
    # ajusta breaks (drums light + active); con estructura propia solo avisa.
    sp = dec.get("spaces") or model.decision(model.FREE)
    if sp.get("mode") == model.FIXED:
        plan.values["spaces"] = sp.get("value")
        _log_entry(plan, "spaces", "fixed", sp.get("value"),
                   "obligatorios → el plan favorece densidades bajas y secciones de aire · "
                   "no es un campo del doc: actúa sobre la estructura automática y los avisos")
    else:
        st_sp = sp.get("mode")
        if st_sp == model.AUTO:
            v = "suggested" if mood in ("melancholic", "dark") else "free"
            plan.values["spaces"] = v
            _log_entry(plan, "spaces", "auto", v, f"coherente con mood '{mood}' · no es un campo del doc")
        else:
            plan.free_axes.append("spaces")
            _log_entry(plan, "spaces", "free", None, "sin preferencia")

    # --- producción (instrucción para Studio/DMD; NUNCA va en el doc) -----------------
    prod = project.fixed_value("production")
    prod_estado = state_of("production")
    prod_nota = ("perfil de producción de STUDIO: NO llega al doc ni al validador; "
                 "se transmite como INSTRUCCIÓN al producir MIDI")
    if prod:
        _log_entry(plan, "production", "fixed", prod, "decisión del usuario · " + prod_nota)
        plan.values["production"] = prod
    elif prod_estado == model.FREE:
        plan.values["production"] = None
        _log_entry(plan, "production", "free", None,
                   "sin perfil: Studio aplicará su default (full) · " + prod_nota)
    else:
        atm = plan.values.get("atmosphere") or "medium"
        v, desc_prod = _weighted(rng, PROD_POOLS.get(atm, PROD_POOLS["medium"]), flatten)
        plan.values["production"] = v
        _log_entry(plan, "production", "auto", v, f"perfil coherente con atmósfera '{atm}' · " + prod_nota,
                   discarded=desc_prod)

    # --- ending --------------------------------------------------------------------------
    end = dec.get("ending") or model.decision(model.AUTO)
    if end.get("mode") == model.FIXED and end.get("value") not in (None, "auto"):
        plan.values["ending"] = end.get("value")
        _log_entry(plan, "ending", "fixed", end.get("value"), "decisión del usuario")
    else:
        v, desc_end = _weighted(rng, {"fade_out": 7, "tape_stop": 2 if mood in ("dark", "tense") else 1,
                                      "none": 1}, flatten)
        plan.values["ending"] = v
        _log_entry(plan, "ending", "auto", v, f"cierre coherente con mood '{mood}'", discarded=desc_end)

    return plan


def resolve_auto_structure(project: model.ComposerProject, plan: ResolvedPlan,
                           rng: Optional[random.Random] = None) -> List[model.Section]:
    """Estructura automática (módulo B, modo auto): plantilla por mood + jitter.

    Si el usuario YA construyó secciones, se devuelven tal cual (fixed manda).
    """
    if project.sections:
        return project.sections
    rng = rng or random.Random(plan.seed_used or 0)
    mood = project.fixed_value("mood") or "neutral"
    templates = STRUCTURE_TEMPLATES.get(mood, STRUCTURE_TEMPLATES["neutral"])
    tpl = templates[rng.randrange(len(templates))]
    spaces = plan.values.get("spaces") or "free"
    sections: List[model.Section] = []
    counters: Dict[str, int] = {}
    for ttype, bars in tpl:
        counters[ttype] = counters.get(ttype, 0) + 1
        jitter = rng.choice([0, 0, 0, -4, 4]) if bars >= 12 else 0
        bars_v = max(4, bars + jitter)
        label = {"pre_chorus": "Pre-Chorus", "verse": "Verse", "chorus": "Chorus",
                 "break": "Break", "bridge": "Bridge", "intro": "Intro", "outro": "Outro"}[ttype]
        if counters[ttype] > 1:
            label += f" {counters[ttype]}"
        sid = f"{ttype}" if counters[ttype] == 1 else f"{ttype}_{counters[ttype]}"
        sections.append(model.Section(id=sid, label=label, type=ttype, bars=bars_v))
    # espacios sugeridos/obligatorios: la plantilla DEBE tener una sección de
    # aire (break); si no la trae, se inserta una antes del cierre.
    if spaces in ("suggested", "mandatory"):
        tiene_break = any(s.type == "break" for s in sections)
        if not tiene_break and len(sections) >= 2:
            brk = model.Section(id="break", label="Break", type="break", bars=8)
            # id único
            if any(s.id == "break" for s in sections):
                brk.id = "break_auto"
            sections.insert(len(sections) - 1, brk)
            plan.log.append({"axis": "structure", "estado": "auto",
                             "valor": "break insertado",
                             "razon": f"espacios musicales '{spaces}': la plantilla no traía "
                                      "sección de aire y se añadió antes del cierre",
                             "descartadas": [], "reglas": ["compatibilidad espacios"]})
        for s in sections:
            if s.type == "break":
                s.active = ["vibraphone", "rhodes", "pad"]
                s.drums = "light"
                break
    _log_entry(plan, "structure", "auto",
               [f"{s.type}:{s.bars}" for s in sections],
               f"plantilla estructural de mood '{mood}' (plantilla #{templates.index(tpl) + 1})")
    return sections
