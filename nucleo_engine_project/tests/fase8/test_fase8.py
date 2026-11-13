"""FASE 8 — Suite de pruebas: ALBUM PRODUCTION SYSTEM.

Ejecución:  python3 -m pytest tests/fase8 -q   (desde la raíz del proyecto)

Alcance (misión FASE 8 §CALIDAD):
  A. Esquema y validación de especificaciones de álbum (dmd-album/1).
  B. Planificación: perfiles, semillas derivadas, diversidad PRE, docs rojos.
  C. Orquestación: producción real, reanudación, regen selectiva, --solo,
     fallo parcial sin perder pistas válidas, cambio de especificación.
  D. Diversidad POST: duplicados exactos, similitud sospechosa.
  E. Determinismo: mismo album.json → mismos MIDIs byte a byte.
  F. Integración: núcleo produce.py compatible, rutas armónicas (original
     sin biblioteca / keyword / ID), familiarity_auto nunca inyectada.
  G. Regresión: contrato rev 3.2, perfiles FASE 6, biblioteca FASE 7,
     goldens en disco y regeneración byte-idéntica de un dorado.
"""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract, forge_link  # noqa: E402
import jazz_engine as je  # noqa: E402
from album import esquema as ES  # noqa: E402
from album import planificador as PL  # noqa: E402
from album import diversidad as DV  # noqa: E402
from album import orquestador as OR  # noqa: E402
from album import informe as INF  # noqa: E402

forge_link.import_forge()
from album.esquema import AlbumInvalido  # noqa: E402


# --------------------------------------------------------------- utilidades

def doc_minimo(titulo="Tema", key="D minor", chords=None, bpm=82, seed=11):
    return {
        "schema": "dark-director/1",
        "meta": {"title": titulo},
        "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
        "global": {"bpm": bpm, "seed": seed},
        "harmony": {"key": key, "language": "pop_dream_pop",
                    "harmonic_rhythm_bars": 1,
                    "progressions": {"verse": chords or ["Dm9", "Bbmaj7", "Fmaj9", "C7sus4"]}},
        "structure": [
            {"id": "intro", "type": "intro", "bars": 2, "energy": 0.2, "tension": 0.2,
             "density": 0.2, "focus": ["rhodes"], "drums": "air"},
            {"id": "verse_1", "type": "verse", "bars": 4, "energy": 0.45, "tension": 0.35,
             "density": 0.45, "focus": ["sax_tenor"], "drums": "groove"},
            {"id": "outro", "type": "outro", "bars": 2, "energy": 0.15, "tension": 0.1,
             "density": 0.15, "focus": ["rhodes"], "drums": "air"},
        ],
        "ending": {"fade_out": {"enabled": True, "bars": 2}},
    }


TONS = ["D minor", "G minor", "C minor", "A minor", "F# minor", "E minor",
        "B minor", "F minor", "Eb minor"]


def album_en_disco(tmp, n=5, *, perfiles=None, harmony_map=None, semilla=3100):
    """Crea un álbum de n pistas válidas en tmp. Devuelve ruta album.json."""
    docs = tmp / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    pistas = []
    for i in range(n):
        d = doc_minimo(titulo="Tema %02d" % (i + 1), key=TONS[i % len(TONS)],
                       bpm=78 + i, seed=100 + i)
        (docs / ("p%02d.json" % (i + 1))).write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")
        p = {"id": "t%02d" % (i + 1), "doc": "docs/p%02d.json" % (i + 1)}
        if perfiles and i < len(perfiles) and perfiles[i]:
            p["perfil"] = perfiles[i]
        if harmony_map and i in harmony_map:
            p["harmony"] = harmony_map[i]
        pistas.append(p)
    spec = {"schema": ES.SCHEMA_ALBUM, "album": "Album Test",
            "identidad": "dark_triphop", "semilla_album": semilla,
            "pistas": pistas}
    ruta = tmp / "album.json"
    ruta.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return ruta


class Fase8Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fase8_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


# ------------------------------------------------------ A. Esquema (A1xx)

class TestEsquema(Fase8Base):
    def test_valido(self):
        ruta = album_en_disco(self.tmp, 3)
        spec, avisos = ES.cargar_album(ruta)
        self.assertEqual(spec["album"], "Album Test")
        self.assertEqual(avisos, [])

    def test_schema_malo(self):
        with self.assertRaises(AlbumInvalido) as ctx:
            ES.validar_album({"schema": "otro/1", "album": "X", "semilla_album": 1,
                              "pistas": []})
        self.assertTrue(any("A102" in e for e in ctx.exception.errores))

    def test_identidad_archivada_rechazada(self):
        with self.assertRaises(AlbumInvalido) as ctx:
            ES.validar_album({"schema": ES.SCHEMA_ALBUM, "album": "X",
                              "identidad": "doom_triphop", "semilla_album": 1,
                              "pistas": [{"id": "a", "doc": "d.json"}]})
        self.assertTrue(any("A104" in e for e in ctx.exception.errores))

    def test_original_con_harmony_rechazado(self):
        with self.assertRaises(AlbumInvalido) as ctx:
            ES.validar_album({"schema": ES.SCHEMA_ALBUM, "album": "X",
                              "semilla_album": 1,
                              "pistas": [{"id": "a", "doc": "d.json",
                                          "perfil": "original",
                                          "harmony": {"keyword": "soulful"}}]})
        self.assertTrue(any("A113" in e for e in ctx.exception.errores))

    def test_harmony_keyword_desconocida(self):
        with self.assertRaises(AlbumInvalido) as ctx:
            ES.validar_album({"schema": ES.SCHEMA_ALBUM, "album": "X",
                              "semilla_album": 1,
                              "pistas": [{"id": "a", "doc": "d.json",
                                          "harmony": {"keyword": "no_existe"}}]})
        self.assertTrue(any("A113" in e for e in ctx.exception.errores))

    def test_harmony_id_inexistente(self):
        with self.assertRaises(AlbumInvalido) as ctx:
            ES.validar_album({"schema": ES.SCHEMA_ALBUM, "album": "X",
                              "semilla_album": 1,
                              "pistas": [{"id": "a", "doc": "d.json",
                                          "harmony": {"id": "NOPE01"}}]})
        self.assertTrue(any("A113" in e for e in ctx.exception.errores))

    def test_ids_duplicados_y_campo_desconocido(self):
        with self.assertRaises(AlbumInvalido) as ctx:
            ES.validar_album({"schema": ES.SCHEMA_ALBUM, "album": "X",
                              "semilla_album": 1,
                              "pistas": [{"id": "a", "doc": "d.json", "foo": 1},
                                         {"id": "a", "doc": "d.json"}]})
        errs = " ".join(ctx.exception.errores)
        self.assertIn("A110", errs)
        self.assertIn("A109", errs)

    def test_curva_energia_longitud(self):
        with self.assertRaises(AlbumInvalido) as ctx:
            ES.validar_album({"schema": ES.SCHEMA_ALBUM, "album": "X",
                              "semilla_album": 1, "curva_energia": [0.5, 0.6],
                              "pistas": [{"id": "a", "doc": "d.json"}]})
        self.assertTrue(any("A107" in e for e in ctx.exception.errores))

    def test_perfil_desconocido(self):
        with self.assertRaises(AlbumInvalido) as ctx:
            ES.validar_album({"schema": ES.SCHEMA_ALBUM, "album": "X",
                              "semilla_album": 1,
                              "pistas": [{"id": "a", "doc": "d.json",
                                          "perfil": "mega_full"}]})
        self.assertTrue(any("A112" in e for e in ctx.exception.errores))


# ------------------------------------------------- B. Planificación (A2xx)

class TestPlanificador(Fase8Base):
    def plan(self, n=5, **kw):
        ruta = album_en_disco(self.tmp, n, **kw)
        spec, _ = ES.cargar_album(ruta)
        plan, _av = PL.planificar(spec, ruta.parent)
        return plan

    def test_determinista(self):
        p1 = self.plan(5)
        p2 = self.plan(5)
        for a, b in zip(p1["pistas"], p2["pistas"]):
            self.assertEqual(a["perfil"], b["perfil"])
            self.assertEqual(a["seed"], b["seed"])
            self.assertEqual(a["sha256_doc"], b["sha256_doc"])

    def test_semillas_derivadas(self):
        plan = self.plan(3)
        for i, t in enumerate(plan["pistas"]):
            self.assertEqual(t["seed"], 3100 + 101 * (i + 1))
            self.assertEqual(t["origen_seed"], "derivada")

    def test_semillas_explícitas_ganan(self):
        ruta = album_en_disco(self.tmp, 2)
        spec = json.loads(ruta.read_text(encoding="utf-8"))
        spec["pistas"][0]["seed"] = 4242
        ruta.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        spec, _ = ES.cargar_album(ruta)
        plan, _ = PL.planificar(spec, ruta.parent)
        self.assertEqual(plan["pistas"][0]["seed"], 4242)
        self.assertEqual(plan["pistas"][0]["origen_seed"], "especificado")

    def test_frac_max_respetado_en_asignacion(self):
        plan = self.plan(13)
        perfiles = {}
        for t in plan["pistas"]:
            perfiles[t["perfil"]] = perfiles.get(t["perfil"], 0) + 1
        n = len(plan["pistas"])
        for nombre, cuenta in perfiles.items():
            self.assertLessEqual(cuenta, 0.4 * n + 1e-9,
                                 "perfil %s excede la fracción: %s" % (nombre, perfiles))

    def test_respiro_cada_5(self):
        plan = self.plan(13)
        perfiles = [t["perfil"] for t in plan["pistas"]]
        for i in range(0, len(perfiles) - 5 + 1):
            ventana = perfiles[i:i + 5]
            self.assertTrue(any(p in ES.PERFILES_RESPIRO for p in ventana),
                            "ventana %d sin respiro: %s" % (i, ventana))

    def test_sin_harmony_no_se_inyecta(self):
        plan = self.plan(5)
        for t in plan["pistas"]:
            self.assertIsNone(t["harmony"])

    def test_harmony_solo_eco_del_spec(self):
        ruta = album_en_disco(self.tmp, 2, harmony_map={1: {"id": "CINE01",
                                                            "variacion": "medium"}})
        spec, _ = ES.cargar_album(ruta)
        plan, _ = PL.planificar(spec, ruta.parent)
        self.assertIsNone(plan["pistas"][0]["harmony"])
        self.assertEqual(plan["pistas"][1]["harmony"]["id"], "CINE01")

    def test_doc_invalido_no_aborta_el_album(self):
        ruta = album_en_disco(self.tmp, 3)
        # romper el doc 2
        d = json.loads((ruta.parent / "docs" / "p02.json").read_text(encoding="utf-8"))
        d["structure"] = [{"id": "s", "type": "no_existe", "bars": 4}]
        (ruta.parent / "docs" / "p02.json").write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")
        spec, _ = ES.cargar_album(ruta)
        plan, _ = PL.planificar(spec, ruta.parent)
        self.assertEqual(len(plan["errores_documentos"]), 1)
        rotas = [t for t in plan["pistas"] if t.get("error_plan")]
        self.assertEqual([t["id"] for t in rotas], ["t02"])
        # las otras dos pistas conservan digest completo
        for t in plan["pistas"]:
            if not t.get("error_plan"):
                self.assertIsNotNone(t["digest"])

    def test_doc_inexistente_detectado(self):
        ruta = album_en_disco(self.tmp, 1)
        spec = json.loads(ruta.read_text(encoding="utf-8"))
        spec["pistas"][0]["doc"] = "docs/falta.json"
        plan, _ = PL.planificar(spec, ruta.parent)
        self.assertTrue(plan["errores_documentos"])
        self.assertIn("A201", plan["errores_documentos"][0])

    def test_identidad_distinta_rechazada(self):
        ruta = album_en_disco(self.tmp, 1)
        d = json.loads((ruta.parent / "docs" / "p01.json").read_text(encoding="utf-8"))
        d["direction"]["identity"] = "doom_triphop"
        (ruta.parent / "docs" / "p01.json").write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")
        spec, _ = ES.cargar_album(ruta)
        plan, _ = PL.planificar(spec, ruta.parent)
        self.assertIn("A204", plan["errores_documentos"][0])


# ------------------------------------------------------- C. Orquestación

class TestOrquestador(Fase8Base):
    def test_produce_y_artefactos(self):
        ruta = album_en_disco(self.tmp, 3)
        out = self.tmp / "out"
        cod = OR.ejecutar(ruta, out, verbose=False)
        self.assertEqual(cod, 0)
        estado = json.loads((out / "estado.json").read_text(encoding="utf-8"))
        for t in estado["pistas"].values():
            self.assertEqual(t["estado"], "ok")
            self.assertTrue(t["sha256_midi"])
        for carpeta in sorted(out.iterdir()):
            if carpeta.is_dir():
                self.assertTrue((carpeta / "doc.json").is_file())
                self.assertTrue((carpeta / "config_efectiva.json").is_file())
                self.assertTrue((carpeta / "evidencia.json").is_file())
                self.assertTrue(list(carpeta.glob("*.mid")))
        self.assertTrue((out / "informe_album.json").is_file())
        self.assertTrue((out / "informe_album.md").is_file())
        self.assertTrue((out / "manifiesto.json").is_file())
        self.assertTrue((out / "huellas.json").is_file())

    def test_reanudacion_salta(self):
        ruta = album_en_disco(self.tmp, 3)
        out = self.tmp / "out"
        OR.ejecutar(ruta, out, verbose=False)
        mid = next((out / "01_t01").glob("*.mid"))
        antes = mid.read_bytes()
        import os
        mtime = os.stat(mid).st_mtime_ns
        cod = OR.ejecutar(ruta, out, verbose=False)
        self.assertEqual(cod, 0)
        self.assertEqual(os.stat(mid).st_mtime_ns, mtime)  # no se tocó
        self.assertEqual(mid.read_bytes(), antes)

    def test_fallo_parcial_preserva_validas(self):
        ruta = album_en_disco(self.tmp, 3)
        d = json.loads((ruta.parent / "docs" / "p02.json").read_text(encoding="utf-8"))
        d["structure"] = [{"id": "s", "type": "no_existe", "bars": 4}]
        (ruta.parent / "docs" / "p02.json").write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")
        out = self.tmp / "out"
        cod = OR.ejecutar(ruta, out, verbose=False)
        self.assertEqual(cod, 1)  # hubo fallo
        estado = json.loads((out / "estado.json").read_text(encoding="utf-8"))
        self.assertEqual(estado["pistas"]["t01"]["estado"], "ok")
        self.assertEqual(estado["pistas"]["t03"]["estado"], "ok")
        self.assertEqual(estado["pistas"]["t02"]["estado"], "fallo")
        self.assertIn("A205", estado["pistas"]["t02"]["error"])

    def test_regen_selectiva(self):
        ruta = album_en_disco(self.tmp, 3)
        out = self.tmp / "out"
        OR.ejecutar(ruta, out, verbose=False)
        import os
        m1 = os.stat(out / "01_t01" / "01_t01.mid").st_mtime_ns
        m3 = os.stat(out / "03_t03" / "03_t03.mid").st_mtime_ns
        cod = OR.ejecutar(ruta, out, regen=["t03"], verbose=False)
        self.assertEqual(cod, 0)
        self.assertEqual(os.stat(out / "01_t01" / "01_t01.mid").st_mtime_ns, m1)
        self.assertGreater(os.stat(out / "03_t03" / "03_t03.mid").st_mtime_ns, m3)

    def test_solo_subconjunto(self):
        ruta = album_en_disco(self.tmp, 3)
        out = self.tmp / "out"
        cod = OR.ejecutar(ruta, out, solo=["1", "3"], verbose=False)
        self.assertEqual(cod, 0)
        estado = json.loads((out / "estado.json").read_text(encoding="utf-8"))
        self.assertEqual(estado["pistas"]["t01"]["estado"], "ok")
        self.assertEqual(estado["pistas"]["t03"]["estado"], "ok")
        self.assertNotIn("t02", estado["pistas"])

    def test_cambio_especificacion_preserva_resultado(self):
        ruta = album_en_disco(self.tmp, 2)
        out = self.tmp / "out"
        OR.ejecutar(ruta, out, verbose=False)
        sha_antes = json.loads((out / "estado.json").read_text(encoding="utf-8")
                               )["pistas"]["t01"]["sha256_midi"]
        # cambiar el doc de t01 (drift)
        p = ruta.parent / "docs" / "p01.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        d["global"]["bpm"] = 90
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        cod = OR.ejecutar(ruta, out, verbose=False)
        self.assertEqual(cod, 0)  # no es un fallo: es una decisión pendiente
        estado = json.loads((out / "estado.json").read_text(encoding="utf-8"))
        self.assertEqual(estado["pistas"]["t01"]["estado"], "pendiente")
        self.assertEqual(estado["pistas"]["t01"]["razon"], OR.RAZON_ESPEC_CAMBIO)
        # el resultado aceptado sigue en disco con el mismo sha
        self.assertEqual(estado["pistas"]["t01"].get("sha256_midi"), sha_antes)
        # --regen lo resuelve
        cod = OR.ejecutar(ruta, out, regen=["t01"], verbose=False)
        self.assertEqual(cod, 0)
        estado = json.loads((out / "estado.json").read_text(encoding="utf-8"))
        self.assertEqual(estado["pistas"]["t01"]["estado"], "ok")

    def test_rutas_armonicas_por_pista(self):
        # t01: original SIN biblioteca; t02: keyword; t03: ID concreto
        ruta = album_en_disco(self.tmp, 3, perfiles=["original", "sax", "sax"],
                              harmony_map={1: {"keyword": "dark_cinematic"},
                                           2: {"id": "CINE01", "variacion": "medium"}})
        out = self.tmp / "out"
        cod = OR.ejecutar(ruta, out, verbose=False)
        self.assertEqual(cod, 0)
        plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
        self.assertIsNone(plan["pistas"][0]["harmony"])
        self.assertEqual(plan["pistas"][1]["harmony"]["keyword"], "dark_cinematic")
        ev1 = json.loads((out / "01_t01" / "evidencia.json").read_text(encoding="utf-8"))
        self.assertNotIn("harmonia", ev1)  # ORIGINAL sin biblioteca
        ev2 = json.loads((out / "02_t02" / "evidencia.json").read_text(encoding="utf-8"))
        self.assertIn("harmonia", ev2)
        self.assertIn("keyword", ev2["harmonia"]["activacion"])


# ----------------------------------------------------- D. Diversidad POST

class TestDiversidad(Fase8Base):
    def test_duplicados_y_sospechosos(self):
        # dos pistas con EL MISMO doc, misma seed y mismo perfil → huella idéntica
        ruta = album_en_disco(self.tmp, 2, perfiles=["sax", "sax"])
        spec = json.loads(ruta.read_text(encoding="utf-8"))
        spec["pistas"][1]["doc"] = spec["pistas"][0]["doc"]
        spec["pistas"][0]["seed"] = 555
        spec["pistas"][1]["seed"] = 555
        ruta.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        out = self.tmp / "out"
        cod = OR.ejecutar(ruta, out, verbose=False)
        self.assertEqual(cod, 0)  # técnicamente produce, pero debe FLAGARSE
        inf = json.loads((out / "informe_album.json").read_text(encoding="utf-8"))
        self.assertEqual(len(inf["diversidad"]["post"]["duplicados_exactos"]), 1)
        sos = inf["diversidad"]["post"]["similares_sospechosos"]
        self.assertTrue(sos and sos[0]["similitud"] >= DV.SIMILITUD_SOSPECHOSA)

    def test_album_variado_sin_alertas_post(self):
        ruta = album_en_disco(self.tmp, 4)
        out = self.tmp / "out"
        OR.ejecutar(ruta, out, verbose=False)
        inf = json.loads((out / "informe_album.json").read_text(encoding="utf-8"))
        self.assertEqual(inf["diversidad"]["post"]["duplicados_exactos"], [])
        self.assertEqual(inf["diversidad"]["post"]["similares_sospechosos"], [])

    def test_consecutivos_iguales_pre(self):
        pistas = [{"id": "a", "perfil": "full", "digest": {"tonalidad": "D minor", "bpm": 80}},
                  {"id": "b", "perfil": "full", "digest": {"tonalidad": "D minor", "bpm": 80}}]
        r = DV.analizar_pre(pistas, {})
        self.assertEqual(len(r["consecutivos_iguales"]), 1)
        self.assertEqual(r["consecutivos_iguales"][0]["motivo"],
                         "perfil+tonalidad+bpm idénticos")

    def test_similitud_jaccard(self):
        h1 = [1, 2, 3, 4]
        h2 = [3, 4, 5, 6]
        self.assertEqual(DV.similitud(h1, h2), round(2 / 6, 4))
        self.assertEqual(DV.similitud(h1, h1), 1.0)
        self.assertEqual(DV.similitud([], []), 0.0)


# ------------------------------------------------------- E. Determinismo

class TestDeterminismo(Fase8Base):
    def test_album_byte_a_byte(self):
        ruta = album_en_disco(self.tmp, 3, perfiles=["sax", "full", "original"],
                              harmony_map={1: {"keyword": "melancholic"}})
        out1, out2 = self.tmp / "o1", self.tmp / "o2"
        self.assertEqual(OR.ejecutar(ruta, out1, verbose=False), 0)
        self.assertEqual(OR.ejecutar(ruta, out2, verbose=False), 0)
        for d in ("01_t01", "02_t02", "03_t03"):
            m1 = next((out1 / d).glob("*.mid")).read_bytes()
            m2 = next((out2 / d).glob("*.mid")).read_bytes()
            self.assertEqual(hashlib.sha256(m1).hexdigest(),
                             hashlib.sha256(m2).hexdigest(), d)

    def test_regeneracion_idempotente(self):
        ruta = album_en_disco(self.tmp, 2)
        out = self.tmp / "out"
        OR.ejecutar(ruta, out, verbose=False)
        shas1 = {t: v["sha256_midi"] for t, v in
                 json.loads((out / "estado.json").read_text(encoding="utf-8")
                            )["pistas"].items()}
        OR.ejecutar(ruta, out, forzar=True, verbose=False)
        shas2 = {t: v["sha256_midi"] for t, v in
                 json.loads((out / "estado.json").read_text(encoding="utf-8")
                            )["pistas"].items()}
        self.assertEqual(shas1, shas2)


# --------------------------------------------- F. Integración con motores

class TestIntegracion(Fase8Base):
    def test_nucleo_produce_compat(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import produce as PD
        self.tmp = Path(tempfile.mkdtemp(prefix="fase8p_"))
        out = self.tmp / "pista"
        r = PD.producir_cancion(doc_minimo(), production="full", seed=5,
                                out_dir=out)
        self.assertTrue(r["ok"])
        self.assertTrue((out / "evidencia.json").is_file())
        ev = json.loads((out / "evidencia.json").read_text(encoding="utf-8"))
        for k in ("sha256_midi", "perfil_produccion", "seed", "reproduccion",
                  "compliance_fails", "versiones"):
            self.assertIn(k, ev)
        # verify path: no escribe nada y compara
        out2 = self.tmp / "pista2"
        r2 = PD.producir_cancion(doc_minimo(), production="full", seed=5,
                                 out_dir=out2, verify=r["sha256"])
        self.assertTrue(r2["ok"])
        self.assertFalse(out2.exists())

    def test_huella_sensible_al_material(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import produce as PD
        r1 = PD.producir_cancion(doc_minimo(), production="sax", seed=5,
                                 out_dir=self.tmp / "a", indice=False)
        r2 = PD.producir_cancion(doc_minimo(chords=["Am9", "Fmaj7", "Cmaj7", "G6"],
                                            key="A minor"),
                                 production="sax", seed=5,
                                 out_dir=self.tmp / "b", indice=False)
        s = DV.similitud(r1["huella"], r2["huella"])
        self.assertLess(s, DV.SIMILITUD_SOSPECHOSA,
                        "materiales distintos no deben parecerse ≥ umbral")

    def test_restricciones_de_arquitectura(self):
        # contrato congelado, perfiles FASE 6, biblioteca FASE 7
        self.assertEqual(contract.CONTRACT_ID, "dark-director/1")
        self.assertEqual(contract.CONTRACT_REV, "3.2")
        self.assertEqual(je.production.nombres(),
                         ("original", "sax", "sax_rhodes", "drums", "sax_vibes",
                          "full", "atmospheric"))
        from jazz_engine import harmony_library as HL
        self.assertEqual(len(HL.biblioteca()), 44)

    def test_album_package_no_toca_protegidos(self):
        # el paquete album/ no debe importar forge ni mutar protected modules
        import album
        import album.planificador
        import album.orquestador
        self.assertFalse(hasattr(album, "generate"))


# ---------------------------------------------------------- G. Regresión

class TestRegresion(Fase8Base):
    def test_goldens_en_disco(self):
        import subprocess
        r1 = subprocess.run([sys.executable, "manifests/verificar_golden.py"],
                            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        r2 = subprocess.run([sys.executable, "manifests/hash_protected.py", "verify"],
                            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

    def test_dorado_regenera_byte_identico(self):
        # 07_full del comparativo FASE 5 (referencia dorada), regenerado ahora
        sys.path.insert(0, str(ROOT / "scripts"))
        import produce as PD
        doc = json.loads(
            (ROOT / "output" / "generalizacion_fase6" / "nocturno_terminal" / "doc.json"
             ).read_text(encoding="utf-8"))
        r = PD.producir_cancion(doc, production="full", seed=2026,
                                out_dir=self.tmp / "g", indice=False)
        esperado = "3930cadc34ec3bcb4dc2cab9788122aa64fdbec2adf10b17b807366e70d7f228"
        self.assertEqual(r["sha256"], esperado)

    def test_informe_separa_tecnico_de_musical(self):
        ruta = album_en_disco(self.tmp, 2)
        out = self.tmp / "out"
        OR.ejecutar(ruta, out, verbose=False)
        inf = json.loads((out / "informe_album.json").read_text(encoding="utf-8"))
        self.assertTrue(inf["tecnico_vs_musical"]["metricas_tecnicas"])
        self.assertTrue(inf["tecnico_vs_musical"]["pendiente_escucha"])
        md = (out / "informe_album.md").read_text(encoding="utf-8")
        self.assertIn("Técnico vs musical", md)
        self.assertIn("escucha humana", md)


if __name__ == "__main__":
    unittest.main()
