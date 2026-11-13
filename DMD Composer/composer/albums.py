"""Modo álbum — planificador de álbumes con diversidad controlada.

Diseño real (misión §8): un álbum es un PLAN de N pistas con identidad común,
restricciones compartidas y diversidad por pista. Cada pista se genera con la
MISMA cadena individual (randomizador → builder → songmap), pero con:

  * semilla INDEPENDIENTE por pista;
  * tonalidad en rotación de tonos relacionados (no claves repetidas seguidas);
  * plantilla estructural distinta por pista (pool por mood);
  * registro de combinaciones usadas (huellas) para evitar duplicados exactos;
  * estado por pista (pendiente/lista) para REANUDAR (re-run no regenera lo
    ya generado salvo --force).

NO duplica el pipeline de producción de álbumes de DMD (album/): Composer
produce los DOCUMENTOS de cada pista; el MIDI de cada doc se genera con el
pipeline existente (Studio / produce.py / modo álbum de DMD). La integración
completa con ``album/`` queda como interfaz explícita en NEXT_MISSION.md.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import manifest as manifest_mod
from . import model, randomizer as R, store

ALBUMS_DIR = store.OUTPUT_DIR / "albumes"


class AlbumError(ValueError):
    pass


def new_album(name: str, tracks: int, base_project: model.ComposerProject,
              shared: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Crea el plan de un álbum a partir de un proyecto base (su identidad,
    sus instrumentos, sus restricciones compartidas)."""
    name = store.safe_name(name)
    if not (2 <= int(tracks) <= 64):
        raise AlbumError("un álbum tiene entre 2 y 64 pistas")
    album_id = store.slugify(name)
    n, k = album_id, 2
    while (ALBUMS_DIR / n).exists():
        n = f"{album_id}_{k}"
        k += 1
    # modo de armonía del álbum: el valor FIJADO del proyecto base; si el base
    # lo tiene en Automático se aplica la MISMA regla del randomizador (hay
    # progresiones/acordes escritos → guided; si no → native).
    hm_base = base_project.fixed_value("harmony_mode")
    if not hm_base:
        hay_guiadas = any(hs.mode == "guided" and (hs.numerals or hs.chords)
                          for hs in base_project.harmony_sections.values())
        hm_base = "guided" if hay_guiadas else "native"
    plan = {
        "formato": "dmd-album/1",
        "album_id": n,
        "name": name,
        "tracks_total": int(tracks),
        "creado": time.time(),
        "compartido": {
            "identity": base_project.fixed_value("identity"),
            "mood": base_project.fixed_value("mood"),
            "protagonist": base_project.fixed_value("protagonist"),
            "harmony_mode": hm_base,
            "spaces": (base_project.decisions.get("spaces") or {}).get("value"),
            "instruments": {k2: v.to_dict() for k2, v in base_project.instruments.items()},
            "diversity": base_project.diversity,
            # M4: la estructura compartida GUARDA las secciones reales del base
            "estructura": "variable",
            "_secciones": [],
            "_harmonias": {},
            **(shared or {}),
        },
        "pistas": [
            {"n": i + 1, "estado": "pendiente", "seed": None, "key": None,
             "bpm": None, "language": None, "plantilla": None, "gen": None}
            for i in range(int(tracks))
        ],
        "huellas": [],
    }
    if base_project.sections:
        plan["compartido"]["estructura"] = "compartida"
        plan["compartido"]["_secciones"] = [s.to_dict() for s in base_project.sections]
        plan["compartido"]["_harmonias"] = {
            sid: h.to_dict() for sid, h in base_project.harmony_sections.items()}
    store.atomic_write_json(ALBUMS_DIR / n / "plan.json", plan)
    return plan


def load_album(album_id: str) -> Optional[Dict[str, Any]]:
    f = ALBUMS_DIR / store.safe_pid(album_id) / "plan.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def save_album(plan: Dict[str, Any]) -> None:
    store.atomic_write_json(ALBUMS_DIR / store.safe_pid(plan["album_id"]) / "plan.json", plan)


def list_albums() -> List[Dict[str, Any]]:
    out = []
    if not ALBUMS_DIR.exists():
        return out
    for d in sorted(ALBUMS_DIR.iterdir()):
        f = d / "plan.json"
        if d.is_dir() and f.exists():
            try:
                p = json.loads(f.read_text(encoding="utf-8"))
                out.append({"album_id": d.name, "name": p["name"],
                            "tracks": p["tracks_total"],
                            "listas": sum(1 for t in p["pistas"] if t["estado"] == "lista")})
            except Exception:
                out.append({"album_id": d.name, "error": "plan ilegible"})
    return out


def _pick_key(rng: random.Random, mood: str, used_keys: List[str]) -> str:
    pool = list(R.RELATED_KEYS_MINOR if (mood in ("melancholic", "dark", "tense"))
                else R.RELATED_KEYS_MAJOR)
    rng.shuffle(pool)
    # nunca repetir la tonalidad de la pista anterior (diversidad real)
    if used_keys and pool and used_keys[-1] in pool and len(pool) > 1:
        pool.remove(used_keys[-1])
    return pool[0]


def prepare_track(plan: Dict[str, Any], n: int, rng: Optional[random.Random] = None) -> Dict[str, Any]:
    """Prepara la pista n: seed, key, bpm y plantilla DIVERSIFICADOS.

    Diversidad real (misión §8): no basta con cambiar el seed — se controlan
    tonalidad, armonía, groove, estructura y comportamiento por pista, y las
    huellas evitan combinaciones exactas repetidas.

    Determinismo (auditoría M5): el consumo del RNG NO depende del estado
    previo de la pista (reintentos producen SIEMPRE el mismo resultado con el
    mismo plan inicial).
    """
    n = int(n)
    if not (1 <= n <= plan["tracks_total"]):
        raise AlbumError(f"pista fuera de rango: {n}")
    track = plan["pistas"][n - 1]
    rng = rng or random.Random(f"{plan['album_id']}:{n}".encode().hex()[:16] + str(plan['creado']))
    rng = random.Random(int(int(rng.random() * 1e9) + n * 7919))
    shared = plan["compartido"]
    mood = shared.get("mood") or "neutral"

    if track["estado"] == "lista" and track.get("gen"):
        return track                     # reanudación: no regenerar

    ya_preparada = track["estado"] == "lista"
    # consumo INCONDICIONAL del RNG (el mismo orden siempre)
    seed_v = rng.randrange(0, 1_000_000)
    key_v = _pick_key(rng, mood, [t.get("key") for t in plan["pistas"] if t.get("key")])
    lang_v, _ = R._weighted(rng, R.LANGUAGE_POOLS.get(mood, R.LANGUAGE_POOLS["neutral"]), 0.3)
    groove_v, _ = R._weighted(rng, R.GROOVE_POOLS.get(mood, R.GROOVE_POOLS["neutral"]), 0.3)
    access_v, _ = R._weighted(rng, R.ACCESS_POOLS.get(mood, R.ACCESS_POOLS["neutral"]), 0.3)
    identity = shared.get("identity") or "dark_triphop"
    bpm_lo, bpm_hi = 70, 96
    rec = (manifest_mod.load_builtin() or {}).get("recetas", {}).get(identity)
    if rec:
        bpm_lo, bpm_hi = rec.get("bpm_rango", (70, 96))
    bpm_v = rng.randrange(bpm_lo, bpm_hi + 1)
    tpl_idx = rng.randrange(len(R.STRUCTURE_TEMPLATES.get(mood, R.STRUCTURE_TEMPLATES["neutral"])))

    track["seed"] = seed_v
    track["key"] = key_v
    track["language"] = lang_v
    track["groove"] = groove_v
    track["accessibility"] = access_v
    track["bpm"] = bpm_v
    track["plantilla"] = tpl_idx

    fingerprint = {"key": key_v, "plantilla": tpl_idx, "language": lang_v,
                   "bpm": bpm_v, "groove": groove_v}
    if not ya_preparada and fingerprint in plan["huellas"]:
        # combinación exacta ya usada: variar tono y plantilla (consumos extra)
        track["key"] = _pick_key(rng, mood, [t.get("key") for t in plan["pistas"] if t.get("key")])
        fingerprint["key"] = track["key"]
        pool_len = len(R.STRUCTURE_TEMPLATES.get(mood, ["x"]))
        if fingerprint in plan["huellas"] and pool_len > 1:
            tpl_idx = (tpl_idx + 1) % pool_len
            track["plantilla"] = tpl_idx
            fingerprint["plantilla"] = tpl_idx
    if not ya_preparada:
        plan["huellas"].append(fingerprint)
    return track


def track_project(album_id: str, n: int) -> model.ComposerProject:
    """Construye el proyecto Composer de UNA pista del álbum (mismas cadenas
    que el modo individual: nada de JSON arbitrario)."""
    plan = load_album(album_id)
    if not plan:
        raise AlbumError("álbum no encontrado")
    track = prepare_track(plan, n)
    save_album(plan)
    shared = plan["compartido"]
    proj = model.new_project(f"{plan['name']} · Track {n:02d}")
    proj.pid = store.slugify(f"{plan['album_id']}_track_{n:02d}")[:48]
    while (store.PROJECTS_DIR / proj.pid).exists():
        proj.pid = proj.pid + "_x"
    proj.decisions["identity"] = model.decision(model.FIXED, shared.get("identity") or "dark_triphop")
    proj.decisions["mood"] = model.decision(model.FIXED, shared.get("mood") or "neutral")
    proj.decisions["key"] = model.decision(model.FIXED, track["key"])
    proj.decisions["bpm"] = model.decision(model.FIXED, track["bpm"])
    proj.decisions["language"] = model.decision(model.FIXED, track["language"])
    proj.decisions["accessibility"] = model.decision(model.FIXED, track["accessibility"])
    proj.decisions["groove"] = model.decision(model.FIXED, track["groove"])
    proj.decisions["harmony_mode"] = model.decision(model.FIXED, shared.get("harmony_mode") or "guided")
    proj.decisions["seed"] = model.decision(model.FIXED, track["seed"])
    if shared.get("protagonist"):
        proj.decisions["protagonist"] = model.decision(model.FIXED, shared["protagonist"])
    if shared.get("spaces"):
        proj.decisions["spaces"] = model.decision(model.FIXED, shared["spaces"])
    for iid, conf in (shared.get("instruments") or {}).items():
        proj.instruments[iid] = model.InstrumentDecision(**conf)
    # estructura: variable → el randomizador decide; compartida → copiar la base
    if shared.get("estructura") == "compartida" and shared.get("_secciones"):
        proj.sections = [model.Section(**{k: v for k, v in s.items()
                                          if k in model.Section.__dataclass_fields__})
                         for s in shared["_secciones"]]
        # v1.1: las decisiones armónicas de la base viajan con la estructura
        # compartida (coherencia musical del álbum; sin esto, una composición
        # guiada compartida dejaría TODAS las secciones sin progresión).
        for sid, h in (shared.get("_harmonias") or {}).items():
            proj.harmony_sections[str(sid)] = model.HarmonySection(
                mode=str(h.get("mode") or "native"), numerals=h.get("numerals"),
                chords=h.get("chords"), chord_bars=h.get("chord_bars"),
                resolution=h.get("resolution"))
    proj.album = {"album_id": plan["album_id"], "track": int(n)}
    store.save_project(proj)
    return proj


# ---------------------------------------------------------------- producción en lote

#: Posición en el círculo de quintas por SEMITONO (pc = 7·quintas mod 12):
#: correcta también con bemoles (Eb→9, Ab→8, Db→1…). La distancia tonal es la
#: mínima en el círculo (0–6): C↔F = 1 quinta, A↔Eb = 6 (tritono).
_PC_FIFTHS = {0: 0, 7: 1, 2: 2, 9: 3, 4: 4, 11: 5, 6: 6, 1: 7, 8: 8, 3: 9, 10: 10, 5: 11}
_PC_NAME = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _key_distance(k1: Optional[str], k2: Optional[str]) -> Optional[int]:
    """Distancia tonal mínima en el círculo de quintas (0–6)."""
    if not k1 or not k2:
        return None
    t1, t2 = k1.split()[0], k2.split()[0]

    def _pc(name: str) -> Optional[int]:
        if not name:
            return None
        pc = _PC_NAME.get(name[0].upper())
        if pc is None:
            return None
        rest = name[1:].lower()
        if rest.startswith("#"):
            pc += 1
        elif rest.startswith("b"):
            pc -= 1
        return pc % 12

    a, b = _pc(t1), _pc(t2)
    if a is None or b is None:
        return None
    f1, f2 = _PC_FIFTHS[a], _PC_FIFTHS[b]
    d = abs(f1 - f2)
    return min(d, 12 - d)


def generate_all(album_id: str, dmd_path: Optional[str], manifest: dict) -> Dict[str, Any]:
    """Genera todas las pistas PENDIENTES en orden (reanuda: las 'lista' no
    se regeneran). Determinista con el plan inicial. NO produce MIDI: cada
    doc queda listo para el pipeline DMD (misión §8; sin duplicar album/).

    El plan se RECARGA del disco antes y después de cada pista: track_project
    y engine.compose escriben estado nuevo; trabajar sobre una copia vieja
    lo pisaría (bug detectado por la batería I del modo álbum).
    """
    from . import engine
    plan = load_album(album_id)
    if not plan:
        raise AlbumError("álbum no encontrado")
    resultados = []
    ok_todas = True
    for t_ref in list(plan["pistas"]):
        n = int(t_ref["n"])
        plan = load_album(album_id)              # estado fresco
        t = plan["pistas"][n - 1]
        if t["estado"] == "lista" and t.get("gen"):
            resultados.append({"pista": n, "estado": "lista (sin regenerar)",
                               "gen": t.get("gen"), "sha256": t.get("doc_sha256")})
            continue
        proj = track_project(album_id, n)        # prepara la pista y guarda
        r = engine.compose(proj, dmd_path, manifest, save=True)
        plan = load_album(album_id)              # recargar tras la preparación
        t = plan["pistas"][n - 1]
        if r.get("ok"):
            t["estado"] = "lista"
            t["gen"] = r["generation"]["gen_id"]
            t["pid"] = proj.pid
            t["doc_sha256"] = r["generation"]["sha256_doc"]
            save_album(plan)
            resultados.append({"pista": n, "estado": "lista",
                               "gen": t["gen"], "pid": proj.pid, "seed": t.get("seed"),
                               "key": t.get("key"), "sha256": t["doc_sha256"],
                               "avisos": len(r.get("avisos", []))})
        else:
            ok_todas = False
            resultados.append({"pista": n, "estado": "error",
                               "errores": r.get("errores", [])})
    informe = informe_album(album_id, save=True)
    return {"ok": ok_todas, "album_id": album_id,
            "pistas": resultados, "informe": informe}


# ---------------------------------------------------------------- producción MIDI
#
# La producción MIDI del álbum la ejecuta el ORQUESTADOR EXISTENTE del DMD
# (album/orquestador.py + planificador.py + diversidad.py, SOLO LECTURA):
# Composer MATERIALIZA un spec dmd-album/1 válido (esquema real de
# nucleo_engine_project/album/esquema.py) a partir de su plan y los docs de
# cada pista, y el orquestador hace el lote con su semántica probada
# (estado.json crash-safe, reanudación, --regen, diversidad de producción).
# Composer NO duplica ninguna lógica de orquestación (misión §7/D27).

def production_dir(album_id: str) -> Path:
    """Carpeta de PRODUCCIÓN del álbum (orquestador del DMD): separada del
    plan.json de Composer para que el orquestador (que escribe su propio
    plan.json/estado.json/NN_<id>/ en --out) nunca pise el plan de Composer."""
    return ALBUMS_DIR / store.safe_pid(album_id) / "produccion"


def _track_doc_source(plan: dict, t: dict) -> Path:
    """doc.json YA generado de la pista (pid+gen del plan)."""
    pid, gen = t.get("pid"), t.get("gen")
    if not pid or not gen:
        raise AlbumError(f"la pista {t['n']} no tiene documento generado "
                         "(genera los documentos antes de producir MIDI)")
    d = store.OUTPUT_DIR / store.safe_pid(pid) / store.safe_gen(gen) / "doc.json"
    if not d.is_file():
        raise AlbumError(f"el doc.json de la pista {t['n']} no está en {d}")
    return d


def track_id(plan: dict, n: int) -> str:
    """Id estable de pista para el spec/orquestador (regex A110 del esquema)."""
    if not (1 <= int(n) <= plan["tracks_total"]):
        raise AlbumError(f"pista fuera de rango: {n}")
    return f"track{int(n):02d}"


def _nombre_spec(name: str) -> str:
    """Nombre de álbum conforme a la regex A103 del esquema real
    (^[A-Za-z0-9][A-Za-z0-9 _-]{0,79}$): sin acentos ni otros signos."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(name or "Album"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9 _-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not s or not re.match(r"^[A-Za-z0-9]", s):
        s = "Album " + s
    return s[:80]


def _semilla_album(album_id: str) -> int:
    """Semilla de álbum DETERMINISTA (hash() de Python no lo es entre
    procesos: PYTHONHASHSEED). Derivada por sha256 del album_id."""
    h = hashlib.sha256(f"dmd-composer-album:{album_id}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 1_000_000


def materializar_spec(album_id: str) -> Dict[str, Any]:
    """Materializa ``album.json`` (dmd-album/1) + ``docs/<id>.json`` para el
    orquestador EXISTENTE. Idempotente: mismo plan + mismos docs → mismo
    spec (los docs se copian de las generaciones, con sha verificado)."""
    plan = load_album(album_id)
    if not plan:
        raise AlbumError("álbum no encontrado")
    d = production_dir(album_id)
    docs_dir = d / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    pistas = []
    for t in plan["pistas"]:
        n = int(t["n"])
        src = _track_doc_source(plan, t)
        tid = track_id(plan, n)
        dst = docs_dir / f"{tid}.json"
        raw = src.read_bytes()
        dst.write_bytes(raw)
        pista = {"id": tid, "doc": f"docs/{tid}.json",
                 "titulo": str(t.get("title") or f"Track {n:02d}")[:80],
                 "seed": int(t.get("seed") or 0)}
        perfil = _perfil_pista(plan, t)
        if perfil:
            pista["perfil"] = perfil
        pistas.append(pista)
    semilla = int(plan.get("compartido", {}).get("semilla_album") or _semilla_album(album_id))
    # identidad del álbum (A204): la que REALMENTE llevan los docs (un álbum
    # es un solo universo musical); Composer siempre fija identity en las
    # pistas, así que la del primer doc es la del álbum completo.
    identidad = plan.get("compartido", {}).get("identity")
    if not identidad:
        try:
            d0 = json.loads((docs_dir / f"{track_id(plan, 1)}.json").read_text(encoding="utf-8"))
            identidad = (d0.get("direction") or {}).get("identity") or "dark_triphop"
        except Exception:
            identidad = "dark_triphop"
    spec = {
        "schema": "dmd-album/1",
        "album": _nombre_spec(plan["name"]),
        "identidad": identidad,
        "semilla_album": semilla,
        "objetivo": {"pistas": len(pistas)},
        "pistas": pistas,
    }
    store.atomic_write_json(d / "album.json", spec)
    return spec


def _perfil_pista(plan: dict, t: dict) -> Optional[str]:
    """Perfil declarado por la generación de la pista (si lo hay)."""
    pid, gen = t.get("pid"), t.get("gen")
    if not pid or not gen:
        return None
    try:
        f = store.OUTPUT_DIR / store.safe_pid(pid) / store.safe_gen(gen) / "generation_manifest.json"
        m = json.loads(f.read_text(encoding="utf-8"))
        return (m.get("produccion") or {}).get("perfil") or None
    except Exception:
        return None


def estado_produccion(album_id: str) -> Dict[str, Any]:
    """Estado de producción por pista leyendo el estado.json REAL del
    orquestador (crash-safe) + el plan de Composer. Sin inventar estados:
    lo que no está en estado.json es 'pendiente'."""
    plan = load_album(album_id)
    if not plan:
        raise AlbumError("álbum no encontrado")
    d = production_dir(album_id)
    estado_f = d / "estado.json"
    est: Dict[str, Any] = {}
    if estado_f.is_file():
        try:
            e = json.loads(estado_f.read_text(encoding="utf-8"))
            est = e.get("pistas") or {}
        except Exception:
            est = {}
    pistas = []
    for t in plan["pistas"]:
        n = int(t["n"])
        tid = track_id(plan, n)
        ep = est.get(tid) or {}
        # el orquestador escribe la carpeta real en estado.json; fallback al
        # patrón canónico NN_<id>/<NN_id>.mid (producir_cancion nombra el .mid
        # como la carpeta que lo contiene)
        carpeta = ep.get("carpeta")
        mid = (Path(carpeta) / f"{n:02d}_{tid}.mid") if carpeta else \
              (d / f"{n:02d}_{tid}" / f"{n:02d}_{tid}.mid")
        sha = ep.get("sha256")
        if not sha and mid.is_file():
            # evidencia REAL de la pista (escrita por producir_cancion): el
            # orquestador puede reescribir estado.json en una reanudación sin
            # repetir el sha; la evidencia de la carpeta nunca miente.
            try:
                ev = json.loads((mid.parent / "evidencia.json").read_text(encoding="utf-8"))
                sha = ev.get("sha256_midi")
            except Exception:
                sha = None
        pistas.append({
            "n": n, "id": tid, "estado_doc": t.get("estado"),
            "estado_midi": ep.get("estado") or "pendiente",
            "sha256_midi": sha,
            "error": ep.get("error"),
            "perfil": ep.get("perfil") or _perfil_pista(plan, t),
            "seed": t.get("seed"),
            "midi_existe": mid.is_file(),
            "midi_ruta": str(mid) if mid.is_file() else None,
        })
    ok_n = sum(1 for p in pistas if p["estado_midi"] == "ok")
    return {"album_id": album_id, "pistas": pistas, "ok": ok_n,
            "total": len(pistas),
            "orquestador": "album/orquestador.py (dmd-album/1, subprocess aislado)"}


def ruta_midi_pista(album_id: str, n: int) -> Optional[Path]:
    """Ruta REAL del MIDI de la pista según el estado.json del orquestador
    (carpeta NN_<id>/, archivo <NN_id>.mid); None si no existe. Contención
    estricta en la carpeta de producción del álbum."""
    plan = load_album(album_id)
    if not plan:
        raise AlbumError("álbum no encontrado")
    d = production_dir(album_id)
    tid = track_id(plan, int(n))
    est = {}
    estado_f = d / "estado.json"
    if estado_f.is_file():
        try:
            est = (json.loads(estado_f.read_text(encoding="utf-8")).get("pistas") or {}).get(tid) or {}
        except Exception:
            est = {}
    carpeta = est.get("carpeta")
    p = (Path(carpeta) / f"{int(n):02d}_{tid}.mid") if carpeta else \
        (d / f"{int(n):02d}_{tid}" / f"{int(n):02d}_{tid}.mid")
    try:
        rp, rb = p.resolve(), d.resolve()
        rp.relative_to(rb)
    except (OSError, ValueError):
        return None
    return p if p.is_file() else None


def generar_events_pista(album_id: str, n: int, dmd_path: str) -> Optional[Path]:
    """events.json de UNA pista de álbum, bajo demanda y VERIFICADO.

    El Player WebAudio no lee .mid: necesita el formato to_events. Para las
    pistas del álbum (producidas por el orquestador, que no escribe events)
    se regenera DETERMINISTAMENTE con el MISMO núcleo (producir_cancion via
    puente, mismo doc del orquestador + mismo perfil + misma seed de
    estado.json) y se EXIGE sha256(MIDI regenerado) == sha256 registrado.
    Resultado en caché en produccion/playback/<id>/events.json. No es un
    segundo generador: es el mismo pipeline, verificado contra la evidencia.
    """
    plan = load_album(album_id)
    if not plan:
        raise AlbumError("álbum no encontrado")
    d = production_dir(album_id)
    tid = track_id(plan, int(n))
    carpeta = d / f"{int(n):02d}_{tid}"
    ev_f = carpeta / "evidencia.json"
    if not ev_f.is_file():
        raise AlbumError(f"la pista {n} no tiene evidencia del orquestador")
    ev = json.loads(ev_f.read_text(encoding="utf-8"))
    sha_objetivo = ev.get("sha256_midi")
    perfil = ev.get("perfil_produccion") or "full"
    seed = ev.get("seed")
    doc_f = carpeta / "doc.json"
    if not doc_f.is_file():
        raise AlbumError(f"la pista {n} no tiene doc.json del orquestador")
    doc = json.loads(doc_f.read_text(encoding="utf-8"))
    pb = d / "playback" / tid
    if not (pb / "events.json").is_file() or not (pb / ".sha").is_file():
        import shutil as _sh
        if pb.exists():
            _sh.rmtree(pb)
        pb.mkdir(parents=True)
        from . import bridge as _bridge
        r = _bridge.produce(dmd_path, doc, str(pb), production=perfil,
                            seed=seed, events=True, timeout=300)
        if not r.get("ok"):
            raise AlbumError(f"regeneración de eventos falló: {r.get('error')}")
        if sha_objetivo and r.get("sha256") != sha_objetivo:
            raise AlbumError(
                f"el MIDI regenerado para events ({str(r.get('sha256'))[:12]}…) no coincide "
                f"con el producido por el orquestador ({str(sha_objetivo)[:12]}…): no se "
                "reproducen datos de otra generación")
        (pb / ".sha").write_text(r.get("sha256") or "", encoding="utf-8")
    return pb / "events.json"


def informe_album(album_id: str, save: bool = False) -> Dict[str, Any]:
    """Informe de diversidad del álbum (NEXT_MISSION §7 de 1.0).

    Métricas REALMENTE medibles con las huellas ya registradas: tonalidades
    distintas y distancia tonal entre pistas consecutivas (círculo de
    quintas), rango de BPM, lenguajes/grooves/plantillas distintos y
    combinaciones duplicadas (debe ser 0: las huellas lo garantizan).
    """
    plan = load_album(album_id)
    if not plan:
        raise AlbumError("álbum no encontrado")
    pistas = plan["pistas"]
    keys = [t.get("key") for t in pistas if t.get("key")]
    bpms = [t.get("bpm") for t in pistas if t.get("bpm")]
    distancias = [_key_distance(a.get("key"), b.get("key"))
                  for a, b in zip(pistas, pistas[1:])
                  if a.get("key") and b.get("key")]
    huellas = [h for h in plan.get("huellas", [])]
    duplicadas = len(huellas) - len({json.dumps(h, sort_keys=True) for h in huellas})
    informe = {
        "album_id": album_id,
        "pistas_total": plan["tracks_total"],
        "pistas_listas": sum(1 for t in pistas if t["estado"] == "lista"),
        "tonalidades_distintas": len(set(keys)),
        "distancia_tonal_consecutivas": distancias,
        "bpm_rango": [min(bpms), max(bpms)] if bpms else None,
        "lenguajes": sorted({t.get("language") for t in pistas if t.get("language")}),
        "grooves": sorted({t.get("groove") for t in pistas if t.get("groove")}),
        "plantillas_usadas": sorted({t.get("plantilla") for t in pistas if t.get("plantilla") is not None}),
        "combinaciones_duplicadas": duplicadas,
        "huellas_registradas": len(huellas),
        "docs": {str(t["n"]): t.get("doc_sha256") for t in pistas if t.get("doc_sha256")},
    }
    if save:
        store.atomic_write_json(ALBUMS_DIR / store.safe_pid(album_id) / "informe.json", informe)
    return informe
