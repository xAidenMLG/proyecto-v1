#!/usr/bin/env python3
"""FASE 6 — ETAPA C/D: Generalización musical + detección de sobreajuste.

Ejecuta una matriz de composiciones × perfiles de producción (preset FASE 6)
y verifica comportamientos ESTRUCTURALES/TÉCNICOS (no musicales):

  - compliance de forge (guardrails) sin fails;
  - límites de sección/compás (notas dentro del proyecto);
  - coherencia armónica del lead (% de notas en tonos de acorde/escala);
  - Rhodes: registro subordinado, no pisa al sax, cuota de interacción;
  - vibes: registro del eco, presupuesto, ecos solo donde hay frase del sax;
  - batería: fills solo en secciones build;
  - coordinador: distribución de protagonismo (no todo simultáneo);
  - determinismo (misma seed → bytes idénticos) y variación con seed distinta.

Salida: output/generalizacion_fase6/  (doc.json, config, MIDI, evidencia por
run + RESUMEN.md + CHECKS.md + sobreajuste.{json,md}). Las referencias doradas
(output/fase5_comparativos/) NO se tocan.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dark_director import compilador, forge_link  # noqa: E402
import jazz_engine as je  # noqa: E402
from jazz_engine import coordinator as CO, profiles as P  # noqa: E402

forge_link.import_forge()
from forge import adapter as A  # noqa: E402
from forge import engine as E  # noqa: E402
from forge import validate as V  # noqa: E402

OUT = ROOT / 'output' / 'generalizacion_fase6'

# ---------------------------------------------------------------------------
# Matriz de composiciones (todas dark_triphop, todas válidas rev 3.2)
# ---------------------------------------------------------------------------
NOCTURNO = json.loads((ROOT / 'output' / 'fase5_comparativos' / 'doc.json').read_text(encoding='utf-8'))

COMPOSICIONES = {
    "nocturno_terminal": {
        "doc": NOCTURNO, "seed": 2026,
        "porque": "Referencia FASE 5 (52 compases, D minor, 86 BPM): baseline de "
                  "comparación directa contra las referencias doradas.",
        "perfiles": ["original", "sax", "sax_rhodes", "drums", "full", "atmospheric",
                     "sax_vibes"],
    },
    "medianoche_puerto_nuevo": {
        "seed": 3113,
        "porque": "F# minor, 78 BPM, 60 compases, ritmo armónico 2 compases, secciones "
                  "largas y energía baja: groove lento, mucho espacio, presupuestos de "
                  "intervención en estructuras largas.",
        "perfiles": ["original", "sax", "sax_rhodes", "drums", "full", "atmospheric"],
        "doc": {
            "schema": "dark-director/1",
            "meta": {"title": "Medianoche en Puerto Nuevo",
                     "notes": "FASE 6 — generalización: groove lento, F# minor, mucho espacio."},
            "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
            "global": {"bpm": 78, "seed": 3113},
            "harmony": {"key": "F# minor", "language": "pop_dream_pop",
                        "harmonic_rhythm_bars": 2,
                        "progressions": {
                            "verse": ["F#m9", "Dmaj9", "Amaj9", "E7sus4"],
                            "chorus": ["Dmaj9", "Amaj9", "Bm9", "C#7sus4"]}},
            "structure": [
                {"id": "intro", "type": "intro", "bars": 4, "energy": 0.2, "tension": 0.2,
                 "density": 0.2, "focus": ["rhodes", "pad"], "drums": "air"},
                {"id": "verse_1", "type": "verse", "bars": 8, "energy": 0.4, "tension": 0.3,
                 "density": 0.4, "focus": ["sax_tenor"], "drums": "groove"},
                {"id": "verse_2", "type": "verse", "bars": 8, "energy": 0.45, "tension": 0.35,
                 "density": 0.45, "focus": ["rhodes"], "drums": "groove"},
                {"id": "pre_1", "type": "pre_chorus", "bars": 4, "energy": 0.55, "tension": 0.5,
                 "density": 0.5, "focus": ["pad", "vibraphone"], "drums": "light"},
                {"id": "chorus_1", "type": "chorus", "bars": 8, "energy": 0.75, "tension": 0.5,
                 "density": 0.6, "focus": ["sax_tenor", "bass"], "drums": "heavy"},
                {"id": "bridge_1", "type": "bridge", "bars": 8, "energy": 0.5, "tension": 0.65,
                 "density": 0.5, "focus": ["rhodes", "vibraphone"], "drums": "light"},
                {"id": "chorus_2", "type": "chorus", "bars": 12, "energy": 0.8, "tension": 0.55,
                 "density": 0.65, "focus": ["sax_tenor", "drums"], "drums": "heavy", "final": True},
                {"id": "outro", "type": "outro", "bars": 8, "energy": 0.15, "tension": 0.15,
                 "density": 0.2, "focus": ["rhodes"], "drums": "air"},
            ],
            "ending": {"fade_out": {"enabled": True, "bars": 4}},
        },
    },
    "calles_de_neon": {
        "seed": 9021,
        "porque": "A minor, 92 BPM, 36 compases, hybrid: material melódico ESCRITO denso "
                  "en 3 secciones (respeto al compositor), estructura corta, tempo rápido.",
        "perfiles": ["original", "sax", "sax_rhodes", "drums", "full", "atmospheric"],
        "doc": {
            "schema": "dark-director/1",
            "meta": {"title": "Calles de Neón",
                     "notes": "FASE 6 — generalización: material escrito denso, corto y rápido."},
            "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
            "global": {"bpm": 92, "seed": 9021},
            "harmony": {"key": "A minor", "language": "hybrid", "harmonic_rhythm_bars": 1,
                        "progressions": {
                            "verse": ["Am9", "Fmaj7", "Cmaj9", "G7sus4"],
                            "chorus": ["Fmaj9", "Cmaj9", "Dm9", "Em9"]}},
            "structure": [
                {"id": "intro", "type": "intro", "bars": 4, "energy": 0.25, "tension": 0.25,
                 "density": 0.25, "focus": ["rhodes", "pad"], "drums": "air"},
                {"id": "verse_1", "type": "verse", "bars": 8, "energy": 0.5, "tension": 0.4,
                 "density": 0.5, "focus": ["sax_tenor", "drums"], "drums": "groove"},
                {"id": "chorus_1", "type": "chorus", "bars": 8, "energy": 0.8, "tension": 0.5,
                 "density": 0.65, "focus": ["sax_tenor", "bass"], "drums": "heavy"},
                {"id": "verse_2", "type": "verse", "bars": 8, "energy": 0.55, "tension": 0.45,
                 "density": 0.55, "focus": ["sax_tenor"], "drums": "groove"},
                {"id": "chorus_2", "type": "chorus", "bars": 8, "energy": 0.85, "tension": 0.55,
                 "density": 0.7, "focus": ["sax_tenor", "drums"], "drums": "heavy", "final": True},
            ],
            "development": {"melody": {"phrases": {
                "verse_1": [
                    {"bar": 0, "beat": 0.5, "pitch": 69, "dur": 1.5, "vel": 72},
                    {"bar": 0, "beat": 2.5, "pitch": 72, "dur": 1.0, "vel": 70},
                    {"bar": 1, "beat": 0.0, "pitch": 76, "dur": 2.0, "vel": 74},
                    {"bar": 2, "beat": 1.0, "pitch": 74, "dur": 0.75, "vel": 66},
                    {"bar": 2, "beat": 2.0, "pitch": 72, "dur": 1.5, "vel": 68},
                    {"bar": 4, "beat": 0.5, "pitch": 69, "dur": 1.5, "vel": 70},
                    {"bar": 5, "beat": 0.0, "pitch": 67, "dur": 2.0, "vel": 66},
                    {"bar": 6, "beat": 2.0, "pitch": 64, "dur": 2.5, "vel": 62}],
                "chorus_1": [
                    {"bar": 0, "beat": 0.0, "pitch": 72, "dur": 1.0, "vel": 82},
                    {"bar": 0, "beat": 1.5, "pitch": 76, "dur": 0.75, "vel": 80},
                    {"bar": 0, "beat": 2.5, "pitch": 79, "dur": 1.25, "vel": 84},
                    {"bar": 1, "beat": 0.5, "pitch": 76, "dur": 2.0, "vel": 78},
                    {"bar": 2, "beat": 0.0, "pitch": 74, "dur": 1.5, "vel": 74},
                    {"bar": 3, "beat": 0.5, "pitch": 72, "dur": 2.5, "vel": 76},
                    {"bar": 5, "beat": 0.0, "pitch": 69, "dur": 1.5, "vel": 70},
                    {"bar": 5, "beat": 2.0, "pitch": 71, "dur": 1.0, "vel": 72},
                    {"bar": 6, "beat": 0.0, "pitch": 72, "dur": 3.0, "vel": 78}],
                "verse_2": [
                    {"bar": 0, "beat": 1.0, "pitch": 64, "dur": 1.5, "vel": 66},
                    {"bar": 1, "beat": 0.0, "pitch": 67, "dur": 2.0, "vel": 68},
                    {"bar": 2, "beat": 0.5, "pitch": 69, "dur": 1.0, "vel": 70},
                    {"bar": 2, "beat": 2.0, "pitch": 72, "dur": 2.0, "vel": 72},
                    {"bar": 4, "beat": 0.0, "pitch": 74, "dur": 2.5, "vel": 74},
                    {"bar": 5, "beat": 1.5, "pitch": 72, "dur": 1.0, "vel": 68},
                    {"bar": 6, "beat": 0.0, "pitch": 69, "dur": 3.5, "vel": 64}],
            }}},
            "ending": {"fade_out": {"enabled": True, "bars": 3}},
        },
    },
    "habitacion_314": {
        "seed": 4104,
        "porque": "G minor, 80 BPM, 64 compases, 10 secciones, tensión alta (B3 en "
                  "pre/bridge), break con active limitado y tape_stop: forma larga, "
                  "arco de tensión, rupturas.",
        "perfiles": ["original", "sax", "sax_rhodes", "drums", "full", "atmospheric"],
        "doc": {
            "schema": "dark-director/1",
            "meta": {"title": "Habitación 314",
                     "notes": "FASE 6 — generalización: forma larga, tensión, tape_stop."},
            "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
            "global": {"bpm": 80, "seed": 4104},
            "harmony": {"key": "G minor", "language": "pop_dream_pop",
                        "harmonic_rhythm_bars": 1,
                        "progressions": {
                            "verse": ["Gm9", "Ebmaj7", "Bbmaj9", "F7sus4"],
                            "chorus": ["Ebmaj9", "Bbmaj9", "Cm9", "D7sus4"]}},
            "structure": [
                {"id": "intro", "type": "intro", "bars": 4, "energy": 0.2, "tension": 0.3,
                 "density": 0.2, "focus": ["rhodes", "pad"], "drums": "air"},
                {"id": "verse_1", "type": "verse", "bars": 8, "energy": 0.45, "tension": 0.4,
                 "density": 0.45, "focus": ["sax_tenor"], "drums": "groove"},
                {"id": "verse_2", "type": "verse", "bars": 8, "energy": 0.5, "tension": 0.45,
                 "density": 0.5, "focus": ["rhodes", "drums"], "drums": "groove"},
                {"id": "pre_1", "type": "pre_chorus", "bars": 4, "energy": 0.6, "tension": 0.7,
                 "density": 0.55, "focus": ["pad", "vibraphone"], "drums": "light"},
                {"id": "chorus_1", "type": "chorus", "bars": 8, "energy": 0.8, "tension": 0.55,
                 "density": 0.65, "focus": ["sax_tenor", "bass"], "drums": "heavy"},
                {"id": "break_1", "type": "break", "bars": 4, "energy": 0.3, "tension": 0.7,
                 "density": 0.3, "focus": ["vibraphone"], "drums": "light",
                 "active": ["vibraphone", "rhodes", "pad"]},
                {"id": "bridge_1", "type": "bridge", "bars": 8, "energy": 0.5, "tension": 0.7,
                 "density": 0.55, "focus": ["rhodes", "vibraphone"], "drums": "light"},
                {"id": "verse_3", "type": "verse", "bars": 8, "energy": 0.55, "tension": 0.5,
                 "density": 0.55, "focus": ["sax_tenor"], "drums": "groove"},
                {"id": "chorus_2", "type": "chorus", "bars": 8, "energy": 0.85, "tension": 0.6,
                 "density": 0.7, "focus": ["sax_tenor", "drums"], "drums": "heavy", "final": True},
                {"id": "outro", "type": "outro", "bars": 4, "energy": 0.2, "tension": 0.25,
                 "density": 0.2, "focus": ["rhodes"], "drums": "air"},
            ],
            "ending": {"tape_stop": {"enabled": True, "bars": 2, "semitones": 8}},
        },
    },
    "casa_de_espejos": {
        "seed": 5150,
        "porque": "C minor, 84 BPM, 44 compases, sax NUNCA en focus (Rhodes/vibraphone/"
                  "pad protagonistas), bridge y break: el coordinador debe repartir "
                  "protagonismo sin apoyarse en el sax.",
        "perfiles": ["original", "sax", "sax_rhodes", "drums", "full", "atmospheric",
                     "sax_vibes"],
        "doc": {
            "schema": "dark-director/1",
            "meta": {"title": "Casa de Espejos",
                     "notes": "FASE 6 — generalización: protagonismo sin sax en focus."},
            "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
            "global": {"bpm": 84, "seed": 5150},
            "harmony": {"key": "C minor", "language": "pop_dream_pop",
                        "resolution": "deceptive", "harmonic_rhythm_bars": 1,
                        "progressions": {
                            "verse": ["Cm9", "Abmaj7", "Ebmaj9", "Bb7sus4"],
                            "chorus": ["Abmaj9", "Ebmaj9", "Fm9", "G7sus4"]}},
            "structure": [
                {"id": "intro", "type": "intro", "bars": 4, "energy": 0.2, "tension": 0.2,
                 "density": 0.2, "focus": ["rhodes", "pad"], "drums": "air"},
                {"id": "verse_1", "type": "verse", "bars": 8, "energy": 0.4, "tension": 0.35,
                 "density": 0.4, "focus": ["rhodes", "bass"], "drums": "groove"},
                {"id": "pre_1", "type": "pre_chorus", "bars": 4, "energy": 0.55, "tension": 0.5,
                 "density": 0.5, "focus": ["vibraphone", "pad"], "drums": "light"},
                {"id": "chorus_1", "type": "chorus", "bars": 8, "energy": 0.75, "tension": 0.5,
                 "density": 0.6, "focus": ["rhodes", "bass", "vibraphone"], "drums": "heavy"},
                {"id": "break_1", "type": "break", "bars": 4, "energy": 0.3, "tension": 0.6,
                 "density": 0.3, "focus": ["vibraphone"], "drums": "light",
                 "active": ["vibraphone", "rhodes", "pad"]},
                {"id": "bridge_1", "type": "bridge", "bars": 4, "energy": 0.5, "tension": 0.6,
                 "density": 0.5, "focus": ["rhodes"], "drums": "light"},
                {"id": "chorus_2", "type": "chorus", "bars": 8, "energy": 0.8, "tension": 0.55,
                 "density": 0.65, "focus": ["rhodes", "vibraphone"], "drums": "heavy", "final": True},
                {"id": "outro", "type": "outro", "bars": 4, "energy": 0.15, "tension": 0.15,
                 "density": 0.2, "focus": ["rhodes"], "drums": "air"},
            ],
            "ending": {"fade_out": {"enabled": True, "bars": 3}},
        },
    },
}

MATRIZ_BASE = ["original", "sax", "sax_rhodes", "drums", "full", "atmospheric"]


# ---------------------------------------------------------------------------
# helpers de verificación
# ---------------------------------------------------------------------------
def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _secciones_abs(proj):
    """[(id, t0, t1, bars)] absolutos en beats."""
    g = proj.get('global') or {}
    ts = g.get('time_signature') or [4, 4]
    bb = int(ts[0]) * 4.0 / int(ts[1])
    out, t = [], 0.0
    for s in proj.get('sections', []):
        dur = int(s['bars']) * bb
        out.append((s['id'], t, t + dur, int(s['bars'])))
        t += dur
    return out, bb


def _notas_role(res, role):
    out = []
    for b in res.bufs:
        if b.role == role:
            for n in b.notes:
                out.append((n.t, n.t + n.d, n.p))
    return sorted(out)


def _checks_run(comp_id, perfil, proj_norm, res, val, seed):
    """Checks estructurales/técnicos de un run. Devuelve dict + lista de fallos."""
    c = {}
    fallos = []
    secs, bb = _secciones_abs(proj_norm)
    total = secs[-1][2] if secs else 0.0

    # 1) compliance/guardrails
    fails = [x['id'] for x in val['compliance'] if x['status'] == 'fail']
    c['compliance_fails'] = fails
    if fails:
        fallos.append("compliance fail: %s" % fails)

    # 2) límites: ninguna nota ARRANCA fuera del proyecto (contrato forge:
    #    section_bounds vigila el inicio; una cola de release de la última nota
    #    que se extiende tras el final es comportamiento preexistente de forge,
    #    se registra como informativo, no como fallo)
    fuera_ini, fuera_fin = 0, 0
    for b in res.bufs:
        for n in b.notes:
            if n.t < -1e-6 or n.t > total + 1e-6:
                fuera_ini += 1
            elif n.t + n.d > total + 1e-6:
                fuera_fin += 1
    c['notas_arranque_fuera'] = fuera_ini
    c['notas_cola_final'] = fuera_fin
    if fuera_ini:
        fallos.append("%d notas ARRANCAN fuera de los límites del proyecto" % fuera_ini)

    if perfil == 'original':
        return c, fallos

    profile = P.resolve_profile('dark_triphop')
    contexts = je.context.build_contexts(proj_norm, profile)
    # armonía por (sección, compás)
    def tonos(sid, kbar):
        for sc in contexts:
            if sc.id == sid:
                bh = sc.harmony_at_bar(kbar)
                return set(bh.chord_tone_pcs) | set(sc.scale_pcs)
        return set()

    # 3) coherencia armónica del lead (sax engine o material del compositor)
    lead = _notas_role(res, 'lead')
    if lead and perfil in ('sax', 'sax_rhodes', 'sax_vibes', 'full', 'atmospheric'):
        coherentes, tot = 0, 0
        for t0, t1, p in lead:
            sid = next((s[0] for s in secs if s[1] - 1e-6 <= t0 < s[2]), None)
            if sid is None:
                continue
            kbar = int((t0 - next(s[1] for s in secs if s[0] == sid)) // bb)
            ton = tonos(sid, kbar)
            tot += 1
            if p % 12 in ton:
                coherentes += 1
        c['lead_coherencia_armonica'] = round(coherentes / tot, 3) if tot else None
        if tot and coherentes / tot < 0.70:
            fallos.append("coherencia armónica del lead < 70%%: %.0f%%"
                          % (100.0 * coherentes / tot))

    # 4) Rhodes: registro, no pisa al sax, cuota de interacción
    ev = getattr(res, 'evidence', {}) or {}
    rh = [nt for nt in (ev.get('rhodes', {}).get('evidencia') or [])]
    c['rhodes_secciones_melodicas'] = [r['seccion'] for r in rh if r.get('notas', 0) > 0]
    mods = {}
    for r in rh:
        mods[r['modo']] = mods.get(r['modo'], 0) + 1
    c['rhodes_modos'] = mods
    if mods.get('interaction', 0) > 1:
        fallos.append("más de una sección con interacción Rhodes (cuota = 1)")
    rnotes = [(nt['t'], nt['t'] + nt['dur'], nt['pitch'])
              for nt in (ev.get('rhodes', {}).get('notas') or [])]
    lo_r, hi_r = profile.rhodes['register']
    fuera_reg = sum(1 for _a, _b, p in rnotes if not (lo_r <= p <= hi_r))
    c['rhodes_fuera_registro'] = fuera_reg
    if fuera_reg:
        fallos.append("%d notas de Rhodes fuera de registro (%s)" % (fuera_reg, (lo_r, hi_r)))
    pisa = 0
    for t0, t1, p in rnotes:
        for a, b2, pl in lead:
            if min(b2, t1) - max(a, t0) > 0.2 and abs(p - pl) < 2:
                pisa += 1
                break
    c['rhodes_pisa_sax'] = pisa
    if pisa:
        fallos.append("Rhodes pisa al sax en %d notas (<2 st con solape)" % pisa)

    # 5) vibes: registro del eco + ecos solo donde hay frase del sax + presupuesto
    eco = ev.get('vibes_eco', {}) or {}
    lo_e, hi_e = profile.vibes['echo_register']
    enotes = [(nt['t'], nt['t'] + nt['dur'], nt['pitch'])
              for nt in (eco.get('notas') or [])]
    fuera_reg_e = sum(1 for _a, _b, p in enotes if not (lo_e <= p <= hi_e))
    c['vibes_eco_fuera_registro'] = fuera_reg_e
    if fuera_reg_e:
        fallos.append("%d ecos del vibes fuera de registro %s" % (fuera_reg_e, (lo_e, hi_e)))
    plan = getattr(res, 'plan', {}) or {}
    frases_sax = set((plan.get('sax_phrases') or {}).keys())
    mal_eco = [e['seccion'] for e in (eco.get('evidencia') or [])
               if e.get('ecos', 0) > 0 and e['seccion'] not in frases_sax]
    c['vibes_ecos_en_secciones_sin_sax'] = mal_eco
    if mal_eco:
        fallos.append("ecos del vibes en secciones sin frase del sax: %s" % mal_eco)
    # el comping del compilador usa su propio registro → solo el ECO está
    # garantizado en echo_register (verificado arriba via evidencia)
    c['vibes_presupuesto'] = plan.get('vibes_budget')
    c['vibes_usadas'] = plan.get('vibes_usadas')
    if plan.get('vibes_usadas', 0) > plan.get('vibes_budget', 99):
        fallos.append("vibes usadas > presupuesto")

    # 6) batería: fills solo en build + actitudes del plan
    fills_en = []
    for d in (ev.get('drums', {}).get('secciones') or []):
        if 'fill_transicion' in (d.get('cambios') or []):
            fills_en.append((d['seccion'], d['actitud']))
    malos = [s for s, a in fills_en if a != 'build']
    c['drums_fills'] = fills_en
    if malos:
        fallos.append("fills fuera de secciones build: %s" % malos)
    c['drums_actitudes'] = {sid: dec.get('drums_attitude')
                            for sid, dec in (plan.get('sections') or {}).items()}

    # 7) coordinador: secciones con los 3 motores melódicos activos a la vez
    sax_secs = set()
    for t0, _t1, _p in lead:
        sid = next((s[0] for s in secs if s[1] - 1e-6 <= t0 < s[2]), None)
        if sid:
            sax_secs.add(sid)
    rh_secs = set(c['rhodes_secciones_melodicas'])
    ec_secs = set(e['seccion'] for e in (eco.get('evidencia') or []) if e.get('ecos', 0) > 0)
    triple = sorted(sax_secs & rh_secs & ec_secs)
    c['secciones_triple_melodia'] = triple
    c['sax_share'] = round(len(sax_secs) / max(1, len(secs)), 2)
    if len(sax_secs) > 0.85 * len(secs):
        fallos.append("el sax monopoliza: %.0f%% de las secciones"
                      % (100 * len(sax_secs) / len(secs)))
    return c, fallos


# ---------------------------------------------------------------------------
# ejecución de la matriz
# ---------------------------------------------------------------------------
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    resumen, runs = [], []
    sax_material = {}          # comp_id → [(intervalos, onsets)] de frases del sax
    for comp_id, espec in COMPOSICIONES.items():
        cdir = OUT / comp_id
        cdir.mkdir(parents=True, exist_ok=True)
        doc = espec['doc']
        seed = espec['seed']
        (cdir / 'doc.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                                       encoding='utf-8')
        (cdir / 'PORQUE.txt').write_text(espec['porque'] + '\n', encoding='utf-8')
        r = compilador.compilar(copy.deepcopy(doc))
        proj = r['proyecto']
        print("== %s (%d secciones, seed %d)" % (comp_id, len(doc['structure']), seed))
        for perfil in espec['perfiles']:
            cfg = {"production": perfil, "seed": seed}
            config = CO.normalize_config(cfg)
            res = je.render.generate(copy.deepcopy(proj), cfg)
            val = V.validate(res)
            # determinismo: segunda pasada
            res2 = je.render.generate(copy.deepcopy(proj), dict(cfg))
            det = _sha(res.midi) == _sha(res2.midi)
            (cdir / ('%s.mid' % perfil)).write_bytes(res.midi)
            proj_norm = res.ctx.project if hasattr(res, 'ctx') else proj
            if perfil == 'original':
                pn, _rep = A.normalize(copy.deepcopy(proj), None)
                proj_norm = pn
            chk, fallos = _checks_run(comp_id, perfil, proj_norm, res, val, seed)
            chk['determinismo'] = det
            if not det:
                fallos.append("no determinista (2 pasadas difieren)")
            m = je.render.metrics(res) if perfil != 'original' else None
            ev_run = {
                "composicion": comp_id, "perfil": perfil, "seed": seed,
                "sha256": _sha(res.midi), "bytes": len(res.midi),
                "bpm": res.ctx.bpm, "compases": res.ctx.total_bars,
                "duracion_s": round(res.ctx.total_beats * 60.0 / res.ctx.bpm, 1),
                "notas_por_pista": {b.track['id']: len(b.notes) for b in res.bufs},
                "checks": chk, "fallos": fallos,
            }
            if m:
                ev_run["frases_sax"] = len(m.get('sax_frases_activas', []))
                ev_run["rhodes_melodico"] = m.get('rhodes_melodico_por_seccion')
                ev_run["vibes_eco"] = m.get('vibes_eco_por_seccion')
            # variación con seed distinta: solo si hay motor consumiendo la seed
            # (sax/rhodes/vibes); el drums engine es transformación pura del
            # proyecto (sin azar propio) → seed no le afecta (F6-O3)
            if perfil != 'original' and any(
                    (config or {}).get('engines', {}).get(k)
                    for k in ('sax', 'rhodes', 'vibes')):
                res3 = je.render.generate(copy.deepcopy(proj), dict(cfg, seed=seed + 1))
                ev_run["seed_distinta_cambia"] = _sha(res3.midi) != _sha(res.midi)
                if not ev_run["seed_distinta_cambia"]:
                    fallos.append("seed distinta produce el MISMO MIDI (sin variación)")
            (cdir / ('evidencia_%s.json' % perfil)).write_text(
                json.dumps(ev_run, ensure_ascii=False, indent=2), encoding='utf-8')
            (cdir / ('config_%s.json' % perfil)).write_text(
                json.dumps(CO.normalize_config(cfg), ensure_ascii=False, indent=2),
                encoding='utf-8')
            runs.append(ev_run)
            # material del sax para el análisis de sobreajuste (frases del
            # perfil completo de la composición)
            if perfil in ('sax', 'full'):
                frases = ((getattr(res, 'plan', {}) or {}).get('sax_phrases') or {})
                if frases:
                    seqs = []
                    for sid in sorted(frases):
                        ns = sorted(frases[sid], key=lambda f: (f['bar'], f['beat']))
                        iv = tuple(ns[i + 1]['pitch'] - ns[i]['pitch']
                                   for i in range(len(ns) - 1))
                        onsets = tuple(round(f['bar'] * 4.0 + f['beat'], 2) for f in ns)
                        seqs.append({"seccion": sid, "intervalos": list(iv),
                                     "onsets": list(onsets), "notas": len(ns)})
                    sax_material.setdefault(comp_id, {})[perfil] = seqs
            resumen.append({
                "composicion": comp_id, "perfil": perfil, "sha": _sha(res.midi)[:12],
                "duracion": ev_run["duracion_s"],
                "notas": ev_run["notas_por_pista"],
                "frases_sax": ev_run.get("frases_sax"),
                "fallos": fallos,
            })
            print("  %-12s %s  fails=%s  det=%s" % (
                perfil, _sha(res.midi)[:12], fallos or 'ninguno', det))
    # variación de seed ya queda por run; el análisis de sobreajuste va aparte
    _analisis_sobreajuste(runs, sax_material)
    _escribir_resumen(resumen)
    print("\nSalida en", OUT)


def _escribir_resumen(resumen):
    lineas = ["# FASE 6 — Matriz de generalización (composición × perfil)", "",
              "| Composición | Perfil | SHA256(12) | dur s | sax | rhodes | vibes | drums | frases sax | fallos |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in resumen:
        n = r['notas']
        lineas.append("| %s | %s | %s | %.1f | %s | %s | %s | %s | %s | %s |" % (
            r['composicion'], r['perfil'], r['sha'], r['duracion'],
            n.get('sax_tenor', 0), n.get('rhodes', 0), n.get('vibraphone', 0),
            n.get('drums', 0), r.get('frases_sax', '-'),
            r['fallos'] or 'ninguno'))
    (OUT / 'RESUMEN.md').write_text('\n'.join(lineas) + '\n', encoding='utf-8')


def _analisis_sobreajuste(runs, sax_material):
    """ETAPA D: señales de sobreajuste entre composiciones.

    Compara material del sax (secuencias de intervalos) entre composiciones,
    modos del Rhodes, actitudes de batería, tasa de eco del vibes y escalado
    de presupuestos. La identidad DEBE ser consistente; lo que se busca son
    FÓRMULAS repetidas idénticas o presupuestos que solo funcionan en 52 compases.
    """
    notas = []
    # 1) sax: fórmulas idénticas entre composiciones distintas
    formulas = {}
    for comp, perfiles in sorted(sax_material.items()):
        for perf, seqs in sorted(perfiles.items()):
            for s in seqs:
                key = tuple(s['intervalos'])
                formulas.setdefault(key, []).append("%s/%s/%s" % (comp, perf, s['seccion']))
    repetidas = {str(k): v for k, v in formulas.items() if len(v) > 1}
    n_seq = sum(len(v) for v in formulas.values())
    print("[sobreajuste] frases sax analizadas: %d; secuencias de intervalos "
          "idénticas entre frases distintas: %d" % (n_seq, len(repetidas)))
    if repetidas:
        notas.append("F6-D1: %d secuencia(s) de intervalos del sax idénticas entre "
                     "frases distintas: %s" % (len(repetidas), list(repetidas.values())))
    # diversidad por composición (¿suena igual el sax en todas las canciones?)
    diversidad = {comp: {perf: len({tuple(s['intervalos']) for s in seqs}) / max(1, len(seqs))
                         for perf, seqs in perfiles.items()}
                  for comp, perfiles in sax_material.items()}
    # 2) rhodes: ¿misma secuencia de modos en todas las composiciones?
    modos = {}
    for run in runs:
        if run['perfil'] != 'full':
            continue
        mods = run['checks'].get('rhodes_modos') or {}
        actitudes = run['checks'].get('drums_actitudes') or {}
        modos[run['composicion']] = {"rhodes": mods, "fills": len(run['checks'].get('drums_fills') or [])}
    # 3) presupuestos del vibes: ¿escalan con el nº de secciones?
    presup = {"%s/%s" % (r['composicion'], r['perfil']):
              {"budget": r['checks'].get('vibes_presupuesto'),
               "usadas": r['checks'].get('vibes_usadas'),
               "secciones": r['compases'] // 4}
              for r in runs if r['perfil'] in ('full', 'sax_vibes')}
    analisis = {
        "frases_sax_analizadas": n_seq,
        "secuencias_intervalos_repetidas": repetidas,
        "diversidad_sax_por_composicion": diversidad,
        "rhodes_y_fills_full": modos,
        "presupuestos_vibes": presup,
        "notas": notas,
    }
    (OUT / 'sobreajuste.json').write_text(
        json.dumps(analisis, ensure_ascii=False, indent=2), encoding='utf-8')
    # resumen md
    l = ["# FASE 6 — Detección de sobreajuste (ETAPA D)", "",
         "Material analizado: %d frases del sax (secuencias de intervalos), " % n_seq,
         "modos del Rhodes y actitudes de batería (perfil full), presupuestos del vibes.", "",
         "## Señales", ""]
    if repetidas:
        l.append("- **Secuencias de intervalos idénticas**: %s" % repetidas)
    else:
        l.append("- Ninguna secuencia de intervalos del sax se repite EXACTAMENTE entre "
                 "frases distintas (fórmulas congeladas: no detectadas).")
    l.append("")
    l.append("- Diversidad de material por composición (frases distintas / totales, "
             "1.0 = todas distintas): %s" % json.dumps(diversidad, ensure_ascii=False))
    l.append("")
    l.append("- Rhodes y fills (perfil full): %s" % json.dumps(modos, ensure_ascii=False))
    l.append("")
    l.append("- Presupuestos del vibes (escalan con secciones): %s" % json.dumps(presup, ensure_ascii=False))
    l.append("")
    for n in notas:
        l.append("- **%s**" % n)
    (OUT / 'sobreajuste.md').write_text('\n'.join(l) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
