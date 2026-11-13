"""Coordinador instrumental — FASE 5.

Decide (por sección y determinísticamente): protagonismo, actividad de cada
motor, comportamiento del Rhodes, actitud de la batería y presupuesto del
vibráfono. NO genera notas: emite un PLAN que consumen los demás motores.

Entrada: proyecto compilado + contexts + config. Salida: plan dict.
El plan es puro: mismo proyecto + misma config → mismo plan (testeado).
"""


def _clamp(x, a, b):
    return max(a, min(b, x))


DEFAULT_CONFIG = {
    "engines": {"sax": True, "rhodes": True, "drums": True, "vibes": True},
    "profile": "auto",                    # auto → identidad del proyecto; o nombre explícito
    "seed": 0,
    "density": {"sax": 1.0, "rhodes": 1.0, "vibes": 1.0, "drums": 1.0},   # multiplicadores
    "variation": "balanced",              # balanced | melodic | atmospheric | groove | sparse
}


VARIACIONES = {
    # presets §12: direcciones musicales comprensibles (no identidades nuevas)
    "balanced": {},
    "melodic": {"density": {"sax": 1.25, "rhodes": 1.2, "vibes": 1.1, "drums": 0.9}},
    "atmospheric": {"density": {"sax": 0.75, "rhodes": 0.8, "vibes": 1.0, "drums": 0.75}},
    "groove": {"density": {"sax": 0.9, "rhodes": 0.7, "vibes": 0.6, "drums": 1.3}},
    "sparse": {"density": {"sax": 0.6, "rhodes": 0.55, "vibes": 0.5, "drums": 0.7}},
}


def _aplicar_variacion(cfg):
    """Multiplica el preset de variación en ``cfg['density']`` (in place).

    Igual que el path estándar: se aplica en CADA normalización (``enhance``
    re-normaliza la config; el comportamiento resultante es el congelado en
    FASE 5 y NO se cambia en FASE 6 — ver DECISIONS F6-2).
    """
    var = VARIACIONES.get(cfg.get("variation") or "balanced", {})
    if var:
        dens = dict(cfg["density"])
        for k, v in var.get("density", {}).items():
            dens[k] = _clamp(dens.get(k, 1.0) * v, 0.0, 1.5)
        cfg["density"] = dens
    return cfg


def normalize_config(config):
    """Fusiona la config del usuario con defaults + preset de variación.
    Devuelve config normalizada (copia). Nunca muta la entrada.

    FASE 6: si ``config`` declara ``production`` (perfil de producción), el
    preset correspondiente se usa como BASE y la config explícita del usuario
    gana (misma clave). El nombre del perfil viaja en la config normalizada
    para que la re-normalización de ``enhance`` resuelva el MISMO perfil.

    ``production="original"`` → camino ORIGINAL sin motores: ``engines`` vacío
    hace que ``render.generate`` delegue byte a byte en forge. No admite
    overrides de motores (contradicción → ValueError, misión §5.2/§5.6).
    """
    if config and config.get("production") is not None:
        from . import production as PR
        nombre, fusionada = PR.aplicar(config)
        if nombre == "original":
            extra = sorted(k for k, v in config.items()
                           if k in ("engines", "density", "variation", "profile")
                           and not (isinstance(v, dict) and not v))
            if extra:
                raise ValueError(
                    "production='original' no admite overrides de motores (%s): "
                    "el camino ORIGINAL es sin jazz_engine; usa otro perfil o "
                    "quita el override" % ", ".join(extra))
            return {"production": "original", "engines": {},
                    "seed": int(fusionada.get("seed", 0) or 0)}
        cfg = dict(fusionada)
        cfg["production"] = nombre                     # sobrevive re-normalización
        dens = dict(DEFAULT_CONFIG["density"])
        dens.update({k: _clamp(float(v), 0.0, 1.5)
                     for k, v in (config or {}).get("density", {}).items()})
        cfg["density"] = dens
        cfg.setdefault("seed", DEFAULT_CONFIG["seed"])
        return _aplicar_variacion(cfg)
    cfg = {}
    cfg.update(DEFAULT_CONFIG)
    if config:
        for k, v in config.items():
            if k == "density" and isinstance(v, dict):
                base = dict(DEFAULT_CONFIG["density"])
                base.update({kk: _clamp(float(vv), 0.0, 1.5) for kk, vv in v.items()})
                cfg["density"] = base
            else:
                cfg[k] = v
    cfg = _aplicar_variacion(cfg)
    cfg["engines"] = dict(DEFAULT_CONFIG["engines"], **(config or {}).get("engines", {}))
    return cfg


def build_plan(project, contexts, profile, cfg):
    """Plan por sección. Determinista (sin azar: los dados los tiran los motores
    con sus semillas; el coordinador decide por reglas + datos)."""
    dens = cfg["density"]
    secciones = {}
    n = len(contexts)
    # presupuesto global del vibráfono (compartido con el comping del compilador
    # se controla en vibes_engine; aquí se decide INTERVENCIÓN propia)
    vibes_budget = max(1, int(round(n * profile.vibes.get("max_present_share", 0.4))))
    vibes_usadas = 0
    # narrativa: protagonista por sección (focus del compositor tiene prioridad)
    for sc in contexts:
        focus = sc.focus
        protagonista = None
        for cand in ("sax_tenor", "rhodes", "vibraphone"):
            if cand in focus:
                protagonista = cand
                break
        sax_d = _clamp(dens["sax"] * (1.0 if sc.energy >= 0.35 else 0.8), 0.0, 1.5)
        rhodes_beh = profile.rhodes["behavior"].get(sc.type, "support")
        # interacción: solo en una sección de clímax (primera chorus o break con
        # energía alta); máximo una por composición (cuota abajo)
        secciones[sc.id] = {
            "type": sc.type,
            "energy": sc.energy,
            "tension": sc.tension,
            "focus": list(focus),
            "protagonista": protagonista,
            "sax_density": sax_d,
            "rhodes_mode": rhodes_beh,
            "vibes_interviene": False,          # se decide en la segunda pasada
            "drums_attitude": _actitud_drums(sc, profile),
        }
    # segunda pasada: cuotas de interacción Rhodes y de vibráfono
    interaccion_asignada = False
    for sc in contexts:
        dec = secciones[sc.id]
        if not interaccion_asignada and dec["rhodes_mode"] == "interaction" and sc.energy >= 0.4:
            interaccion_asignada = True          # ya es interaction de perfil
        elif dec["rhodes_mode"] == "interaction":
            dec["rhodes_mode"] = "response"      # sin segunda interacción
        if vibes_usadas < vibes_budget and dec["type"] in ("verse", "pre_chorus", "chorus", "break"):
            if dec["protagonista"] != "sax_tenor" or dec["type"] != "verse":
                dec["vibes_interviene"] = True
                vibes_usadas += 1
    return {
        "sections": secciones,
        "identity": profile.name,
        "profile_active": profile.active,
        "seed_used": cfg["seed"],
        "engines": dict(cfg["engines"]),
        "density": dict(cfg["density"]),
        "variation": cfg.get("variation", "balanced"),
        "vibes_budget": vibes_budget,
        "vibes_usadas": vibes_usadas,
    }


def _actitud_drums(sc, profile):
    """Actitud de batería por sección: keep | vary | build | drop | recover."""
    dr = profile.drums
    t = sc.type
    if t in dr.get("rupture", {}).get("types", ()):
        return "drop" if sc.tension >= 0.55 else "recover"
    if t in dr.get("build_types", ()):
        return "build"
    if t in ("verse", "chorus"):
        return "vary"
    return "keep"
