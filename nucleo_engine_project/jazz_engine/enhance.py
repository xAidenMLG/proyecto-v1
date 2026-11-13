"""Enriquecimiento del proyecto compilado — FASE 5.

Un único punto que aplica, en orden, los motores que trabajan a nivel de
PROYECTO (transformación pura, salida sigue siendo midi-forge/1):

  1. improvisación del sax  → project['lead']['phrases'] (+ bends del lead);
  2. drums engine           → params de batería (layers/fills/light_bars);
  3. vibes engine           → params de mallet (replies/pings).

Los motores a nivel de BUFFER (Rhodes melódico, eco del vibráfono) viven en
``render.py`` porque necesitan escuchar al sax ya generado.

Devuelve (proyecto_enriquecido, plan, evidencia). Nunca muta la entrada.
Si TODOS los motores están apagados devuelve el proyecto idéntico (deepcopy).
"""
import copy

from . import coordinator, drums_engine, improv, profiles as P, vibes_engine


def _identidad_de_proyecto(project):
    meta = ((project.get('meta') or {}).get('director') or {})
    original = meta.get('original') or {}
    return (original.get('direction') or {}).get('identity') or 'dark_triphop'


def resolver_profile(project, cfg):
    nombre = cfg.get('profile') or 'auto'
    if nombre == 'auto':
        nombre = _identidad_de_proyecto(project)
    if nombre not in P.PROFILES:
        nombre = P.ACTIVE_IDENTITY
    return P.resolve_profile(nombre)


def enhance(project, config=None):
    """Pipeline de enriquecimiento. (proyecto, plan, evidencia)."""
    cfg = coordinator.normalize_config(config)
    profile = resolver_profile(project, cfg)
    from .context import build_contexts
    contexts = build_contexts(project, profile)
    plan = coordinator.build_plan(project, contexts, profile, cfg)
    seed = int(cfg.get('seed', 0))
    ev = {"profile": profile.name, "identity_proyecto": _identidad_de_proyecto(project),
          "engines": dict(cfg['engines']), "seed": seed, "variation": cfg.get('variation')}
    proj = copy.deepcopy(project)

    if cfg['engines'].get('sax'):
        # material del COMPOSITOR (protegido: jamás se silencia ni se sustituye)
        material_compositor = set((project.get('lead') or {}).get('phrases', {}).keys())
        phrases, ev_sax = improv.sax_plan(contexts, plan, profile, seed)
        # el material del compositor JAMÁS se sustituye: mis frases solo entran
        # en secciones sin material escrito
        phrases = {sid: n for sid, n in phrases.items() if sid not in material_compositor}
        ev_sax = dict(ev_sax, respetadas_material_compositor=sorted(material_compositor))
        if phrases:
            lead = proj.setdefault('lead', {}).setdefault('phrases', {})
            for sid, notas in phrases.items():
                lead[sid] = list(notas)
            # bends del lead (mecanismo nativo: params.bends del bloque lead)
            for sec in proj.get('sections', []):
                blk = (sec.get('blocks') or {}).get('sax_tenor')
                if blk and blk.get('enabled', True) and blk.get('style') in ('auto', 'phrases', 'generative'):
                    blk.setdefault('params', {})['bends'] = copy.deepcopy(profile.sax.get('bends'))
        # silencio = decisión musical: donde el scheduler calla y NO hay material
        # del compositor, el bloque lead se apaga (si no, el generativo nativo
        # del motor llenaría esos huecos — improvisación constante prohibida)
        calladas = 0
        for sec in proj.get('sections', []):
            sid = sec['id']
            blk = (sec.get('blocks') or {}).get('sax_tenor')
            if not blk or sid in material_compositor or sid in phrases:
                continue
            if blk.get('enabled', True) and blk.get('style') != 'none':
                blk['enabled'] = False
                blk['style'] = 'none'
                calladas += 1
        ev_sax = dict(ev_sax, secciones_silenciadas=calladas)
        plan['sax_phrases'] = phrases
        ev['sax'] = ev_sax
    else:
        plan['sax_phrases'] = {}
        ev['sax'] = {"desactivado": True}

    if cfg['engines'].get('drums'):
        proj, ev_dr = drums_engine.aplicar(proj, contexts, plan, profile, seed)
        ev['drums'] = ev_dr
    else:
        ev['drums'] = {"desactivado": True}

    if cfg['engines'].get('vibes'):
        proj, ev_vb = vibes_engine.aplicar_params(proj, contexts, plan, profile, seed)
        ev['vibes_params'] = ev_vb
    else:
        ev['vibes_params'] = {"desactivado": True}

    return proj, plan, ev
