"""I · Fase 2 v1.1 — recorrido completo y las 14 pruebas obligatorias.

Cada prueba de la misión §4 tiene su test. El recorrido demostrado es:
    UI/API → modelo interno → doc.json → validador DMD → compilador → MIDI
    → Song Map → manifest.
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import util
from util import (DMD_PATH, HAS_DMD, MANIFEST, basic_sections, codes_out,
                  compose_project, new_test_project)

from composer import albums as ALB, bridge, engine, manifest as MF, model, proposal as PR, store
from composer import randomizer as R

# MIDI real por el pipeline existente (mismo helper probado de la batería F)
sys.path.insert(0, str(util.PKG / "tests"))
from test_f_integracion import _generar_midi  # noqa: E402

PKG = util.PKG


def _proyecto_melancolico(seed_key="D minor", **kw):
    p = new_test_project(mood="melancholic", **kw)
    p.decisions["key"] = model.decision("fixed", seed_key)
    return p


class TestIHarmonia(unittest.TestCase):
    """1-3: Native/Guided sin ambigüedad (misión §2.1)."""

    def test_1_native_sin_progresiones(self):
        p = _proyecto_melancolico()
        p.decisions["harmony_mode"] = model.decision("fixed", "native")
        p.sections = basic_sections()
        r = compose_project(p, seed=3, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertNotIn("progressions", r["doc"]["harmony"])
        self.assertEqual(r["build"]["nativas_n1"], True)
        self.assertEqual(r["armonia"]["modo_real_del_doc"], "native")
        for row in r["song_map"]["secciones"]:
            self.assertEqual(row["fuente_armonia"], "receta_n1")

    def test_2_guided_con_progresiones_distintas_por_seccion(self):
        p = _proyecto_melancolico()
        p.sections = basic_sections()
        p.harmony_sections = {
            "intro": model.HarmonySection(mode="guided", numerals="i - III"),
            "verso_1": model.HarmonySection(mode="guided", numerals="i - III - VII - VI"),
            "estribillo": model.HarmonySection(mode="guided", numerals="VI - VII - i - V"),
            "puente": model.HarmonySection(mode="guided", numerals="iv - VI - VII - V"),
            "outro": model.HarmonySection(mode="guided", numerals="i - VI"),
        }
        r = compose_project(p, seed=4, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        progs = r["doc"]["harmony"]["progressions"]
        self.assertEqual(len(progs), 5)
        self.assertEqual(len({json.dumps(v) for v in progs.values()}), 5,
                         "las secciones no deben compartir progresión")
        self.assertEqual(r["armonia"]["modo_real_del_doc"], "guided")
        fuentes = r["armonia"]["fuente_por_seccion"]
        for sid in ("intro", "verso_1", "estribillo", "puente", "outro"):
            self.assertEqual(fuentes[sid], "progressions_id")
        self.assertEqual(fuentes["pre"], "receta_n1")   # sin progresión → receta N1

    def test_3_guided_sin_progresiones_aviso_inequivoco(self):
        """Guided sin progresiones: NO conversión silenciosa → aviso explícito
        con las secciones y la acción necesaria + modo real honesto."""
        p = _proyecto_melancolico()
        p.sections = basic_sections()          # sin harmony_sections
        r = compose_project(p, seed=5, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        av = [a for a in r["avisos"] if a["code"] == "armonia-implicita"]
        self.assertEqual(len(av), 1, "el modo guiado sin progresiones debe avisar SIEMPRE")
        msg = av[0]["message"]
        for sid in ("intro", "verso_1", "estribillo", "outro"):
            self.assertIn(sid, msg, "el aviso debe NOMBRAR cada sección sin decisión")
        self.assertIn("receta N1", msg)
        self.assertEqual(sorted(r["build"]["secciones_sin_decision"]),
                         sorted(s.id for s in basic_sections()))
        self.assertEqual(r["armonia"]["modo_real_del_doc"], "native")

    def test_3b_nativa_global_con_guiadas_advierte_que_no_viajan(self):
        """D-05: modo global Nativa + grados guiados → advertencia explícita."""
        p = _proyecto_melancolico()
        p.decisions["harmony_mode"] = model.decision("fixed", "native")
        p.sections = basic_sections()
        p.harmony_sections["verso_1"] = model.HarmonySection(mode="guided",
                                                             numerals="i - VI - III - VII")
        r = compose_project(p, seed=6, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        av = [a for a in r["avisos"] if a["code"] == "guiada-ignorada"]
        self.assertEqual(len(av), 1)
        self.assertIn("verso_1", av[0]["message"])
        self.assertNotIn("progressions", r["doc"]["harmony"])

    def test_3c_nativa_explicita_sin_numeros_no_da_error(self):
        p = _proyecto_melancolico()
        p.sections = basic_sections()
        p.harmony_sections["verso_1"] = model.HarmonySection(mode="native")
        r = compose_project(p, seed=7, validate=False)
        self.assertTrue(r["ok"], r["errores"])


class TestIProtagonista(unittest.TestCase):
    """4-5: protagonista con consecuencias musicales reales (misión §2.2)."""

    def test_4_vibraphone_protagonista_distribucion_verificable(self):
        p = _proyecto_melancolico()
        p.decisions["protagonist"] = model.decision("fixed", "vibraphone")
        p.sections = basic_sections()
        # propuesta SOLO LECTURA
        prop = PR.proponer_distribucion(p, MANIFEST)
        self.assertEqual(prop["protagonista"], "vibraphone")
        self.assertTrue(prop["cambios"])
        focus_props = [c for c in prop["cambios"] if c["campo"] == "focus"]
        self.assertTrue(focus_props, "debe proponer focos por sección")
        for c in focus_props:
            self.assertEqual(c["despues"][0], "vibraphone")
        dens = [c for c in prop["cambios"] if c["campo"] == "density"]
        self.assertTrue(dens, "vibraphone admite density (lead real)")
        self.assertEqual(dens[0]["despues"], PR.DENSITY_PROPUESTA)
        # aplicar → campos reales del contrato
        n = PR.aplicar_propuesta(p, prop)
        self.assertGreater(n, 0)
        self.assertEqual(p.protagonist_proposal["estado"], "aplicada")
        r = compose_project(p, seed=8, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertEqual(r["doc"]["instruments"]["vibraphone"]["density"], PR.DENSITY_PROPUESTA)
        focos_doc = [s for s in r["doc"]["structure"] if "vibraphone" in (s.get("focus") or [])]
        self.assertGreaterEqual(len(focos_doc), len(focus_props),
                                "los focos propuestos deben llegar al doc")
        self.assertEqual(r["protagonista"]["propuesta"]["estado"], "aplicada")
        self.assertEqual(r["protagonista"]["efecto_doc"]["focus_con_protagonista"],
                         [s.id for s in basic_sections()])
        for s in r["doc"]["structure"]:
            self.assertEqual((s.get("focus") or [None])[0], "vibraphone")

    def test_4b_rechazo_no_toca_campos(self):
        p = _proyecto_melancolico()
        p.decisions["protagonist"] = model.decision("fixed", "vibraphone")
        p.sections = basic_sections()
        antes = copy.deepcopy(p.to_dict())
        prop = PR.proponer_distribucion(p, MANIFEST)
        PR.rechazar_propuesta(p, prop)
        despues = p.to_dict()
        for k in ("sections", "instruments"):
            self.assertEqual(antes[k], despues[k], "rechazar NO debe tocar campos")
        self.assertEqual(p.protagonist_proposal["estado"], "descartada")

    def test_5_sax_protagonista(self):
        p = _proyecto_melancolico()
        p.decisions["protagonist"] = model.decision("fixed", "sax_tenor")
        p.sections = basic_sections()
        prop = PR.proponer_distribucion(p, MANIFEST)
        self.assertEqual(prop["protagonista"], "sax_tenor")
        # sax está en el set base de dark_triphop: NO necesita enabled=true
        self.assertFalse([c for c in prop["cambios"]
                          if c["campo"] == "enabled" and c["iid"] == "sax_tenor"])
        n = PR.aplicar_propuesta(p, prop)
        self.assertGreater(n, 0)
        r = compose_project(p, seed=9, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertEqual(r["doc"]["instruments"]["sax_tenor"]["density"], PR.DENSITY_PROPUESTA)
        self.assertTrue(r["protagonista"]["efecto_doc"]["focus_con_protagonista"])
        for s in r["doc"]["structure"]:
            self.assertEqual((s.get("focus") or [None])[0], "sax_tenor")

    def test_5b_protagonista_fuera_del_set_base_garantiza_sonido(self):
        """strings no está en el set base de dark_triphop → enabled=true."""
        p = _proyecto_melancolico()
        p.decisions["protagonist"] = model.decision("fixed", "strings")
        p.sections = basic_sections()
        prop = PR.proponer_distribucion(p, MANIFEST)
        enab = [c for c in prop["cambios"] if c["campo"] == "enabled"]
        self.assertTrue(enab and enab[0]["despues"] is True)
        PR.aplicar_propuesta(p, prop)
        r = compose_project(p, seed=10, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertEqual(r["doc"]["instruments"]["strings"]["enabled"], True)


class TestIGrooveBpm(unittest.TestCase):
    """6: groove Auto con BPM fijado; groove ≠ tempo (misión §2.3)."""

    def test_6_bpm_fijado_se_conserva_exacto_y_groove_no_esta_en_doc(self):
        p = _proyecto_melancolico()
        p.decisions["bpm"] = model.decision("fixed", 85)
        p.decisions["groove"] = model.decision("auto")
        p.sections = basic_sections()
        for seed in range(6):
            r = compose_project(p, seed=seed, validate=False, save=False)
            self.assertTrue(r["ok"], r["errores"])
            self.assertEqual(r["doc"]["global"]["bpm"], 85, "el BPM fijado se conserva EXACTO")
            doc_txt = json.dumps(r["doc"])
            self.assertNotIn("laid_back", doc_txt)
            self.assertNotIn("driving", doc_txt)
            self.assertNotIn("steady", doc_txt)
            glog = [l for l in r["log"] if l["axis"] == "groove"]
            self.assertEqual(len(glog), 1)
            self.assertEqual(glog[0]["estado"], "auto")
            self.assertIn("BPM", glog[0]["razon"], "el log debe explicar la relación con el BPM")
            self.assertIn("NO llega al doc", glog[0]["razon"])

    def test_6b_groove_fijado_no_cambia_el_bpm_fijado(self):
        p = _proyecto_melancolico()
        p.decisions["bpm"] = model.decision("fixed", 85)
        p.decisions["groove"] = model.decision("fixed", "driving")
        p.sections = basic_sections()
        r = compose_project(p, seed=1, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertEqual(r["doc"]["global"]["bpm"], 85)


class TestIProduccionExplicabilidad(unittest.TestCase):
    """7-8: perfil de producción y manifiesto de un solo estado por eje."""

    def test_7_produccion_seleccionada_transmision_correcta(self):
        p = _proyecto_melancolico()
        p.decisions["production"] = model.decision("fixed", "sax_vibes")
        p.production = {"profile": "sax_vibes", "f7_keyword": "melancholic",
                        "f7_variation": "subtle", "wav": False}
        p.sections = basic_sections()
        r = compose_project(p, seed=11, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        pr = r["produccion"]
        self.assertEqual(pr["perfil"], "sax_vibes")
        self.assertEqual(pr["estado"], "seleccionado_pendiente_de_aplicar")
        self.assertFalse(pr["llega_al_doc"])
        self.assertIn("--production sax_vibes", pr["instruccion"]["cli"])
        self.assertIn("--seed", pr["instruccion"]["cli"])
        self.assertIn("--harmony melancholic", pr["instruccion"]["cli"])
        self.assertIn("--harmony-variacion subtle", pr["instruccion"]["cli"])
        self.assertIn("melancholic", pr["instruccion"]["studio"])
        # el perfil ya NO se declara como decisión del doc
        self.assertNotIn("production", r["decisiones"]["fijadas"])
        self.assertNotIn("production", r["decisiones"]["automaticas"])
        self.assertEqual(pr["f7_keyword"], "melancholic")

    def test_8_fixed_auto_free_sin_contradicciones(self):
        p = _proyecto_melancolico()
        p.decisions["bpm"] = model.decision("fixed", 88)
        p.decisions["resolution"] = model.decision("fixed", "tonal")
        p.decisions["spaces"] = model.decision("free")
        p.decisions["protagonist"] = model.decision("free")
        p.sections = basic_sections()
        r = compose_project(p, seed=12, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        dec = r["decisiones"]
        fij, aut, lib = set(dec["fijadas"]), set(dec["automaticas"]), set(dec["libres"])
        self.assertFalse(fij & aut, f"duplicados fijadas/automaticas: {fij & aut}")
        self.assertFalse(fij & lib, f"duplicados fijadas/libres: {fij & lib}")
        self.assertFalse(aut & lib, f"duplicados automaticas/libres: {aut & lib}")
        # cada eje del doc aparece en EXACTAMENTE un estado
        ejes_log = {}
        for l in r["log"]:
            ejes_log.setdefault(l["axis"], set()).add(l["estado"])
        for eje, estados in ejes_log.items():
            self.assertEqual(len(estados), 1, f"{eje} tiene estados {estados}: debe tener UNO")
        # mood/groove/atmosphere NO son decisiones del doc: preferencias
        for pref in ("mood", "groove", "atmosphere"):
            self.assertNotIn(pref, fij | aut | lib, f"'{pref}' no llega al doc")
            self.assertIn(pref, r["preferencias_composer"])
        self.assertEqual(dec["fijadas"]["bpm"], 88)
        self.assertIn("resolution", dec["fijadas"])
        self.assertIn("spaces", dec["libres"])
        self.assertIn("protagonist", dec["libres"])

    def test_8b_harmony_mode_log_con_estado_real(self):
        """D-06: el log de harmony_mode refleja el estado REAL, no siempre fixed."""
        p = _proyecto_melancolico()
        p.decisions["harmony_mode"] = model.decision("auto")
        p.sections = basic_sections()
        r = compose_project(p, seed=13, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        hm = [l for l in r["log"] if l["axis"] == "harmony_mode"]
        self.assertEqual(len(hm), 1)
        self.assertEqual(hm[0]["estado"], "auto")
        self.assertGreater(len(hm[0]["razon"]), 20, "la razón debe explicar el criterio")
        self.assertTrue(hm[0].get("descartadas"), "D-08: registra la alternativa descartada")

    def test_8c_descartadas_ponderadas_no_vacias(self):
        """D-08: las elecciones ponderadas registran las alternativas."""
        p = _proyecto_melancolico()
        for eje in ("identity", "accessibility", "bpm", "key", "language"):
            p.decisions[eje] = model.decision("auto")
        p.sections = basic_sections()
        r = compose_project(p, seed=14, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        for l in r["log"]:
            if l["axis"] in ("key", "language", "accessibility", "ending", "production"):
                self.assertTrue(l.get("descartadas"),
                                f"{l['axis']}: la elección ponderada debe registrar descartadas")

    def test_8d_protagonista_libre_esta_en_libres(self):
        p = _proyecto_melancolico()
        p.decisions["protagonist"] = model.decision("free")
        p.sections = basic_sections()
        r = compose_project(p, seed=15, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertIn("protagonist", r["decisiones"]["libres"])
        prot_log = [l for l in r["log"] if l["axis"] == "protagonist"]
        self.assertEqual(prot_log[0]["estado"], "free")

    def test_8e_protagonista_auto_es_el_lead_de_la_receta(self):
        p = _proyecto_melancolico()
        p.decisions["protagonist"] = model.decision("auto")
        p.sections = basic_sections()
        r = compose_project(p, seed=16, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        lead = MANIFEST["recetas"]["dark_triphop"]["lead"]
        self.assertEqual(r["decisiones"]["automaticas"]["protagonist"], lead)


class TestIReproducibilidad(unittest.TestCase):
    """9-10: seed determinista y diversidad coherente."""

    def test_9_seed_identica_salida_reproducible(self):
        def mk():
            p = _proyecto_melancolico()
            p.decisions["protagonist"] = model.decision("fixed", "vibraphone")
            p.sections = basic_sections()
            return p
        r1 = compose_project(mk(), seed=2026, validate=False, save=False)
        r2 = compose_project(mk(), seed=2026, validate=False, save=False)
        self.assertEqual(r1["doc"], r2["doc"])
        self.assertEqual(r1["log"], r2["log"])
        self.assertEqual(r1["decisiones"], r2["decisiones"])
        self.assertEqual(r1["produccion"]["instruccion"]["cli"],
                         r2["produccion"]["instruccion"]["cli"])

    def test_10_seeds_diferentes_diversidad_coherente(self):
        docs, keys, bpms = set(), set(), set()
        for seed in range(1, 9):
            p = _proyecto_melancolico()
            for eje in ("bpm", "key", "language", "accessibility"):
                p.decisions[eje] = model.decision("auto")
            p.sections = basic_sections()
            r = compose_project(p, seed=seed, validate=False, save=False)
            self.assertTrue(r["ok"], r["errores"])
            docs.add(json.dumps(r["doc"], sort_keys=True))
            keys.add(r["doc"]["harmony"]["key"])
            bpms.add(r["doc"]["global"]["bpm"])
        self.assertGreaterEqual(len(docs), 6, "8 seeds → documentos casi idénticos")
        self.assertGreater(len(keys), 1)
        self.assertGreater(len(bpms), 1)


@unittest.skipUnless(HAS_DMD, "sin DMD real: la validación y el MIDI exigen el pipeline")
class TestIPipelineReal(unittest.TestCase):
    """11-13: Song Map vs compilado real; importación en Studio; MIDI real."""

    def _doc_con_literales(self, seed=21):
        p = _proyecto_melancolico()
        p.decisions["production"] = model.decision("fixed", "full")
        p.sections = basic_sections()
        p.harmony_sections = {
            "verso_1": model.HarmonySection(mode="guided", numerals="i - III - VII - VI"),
            "estribillo": model.HarmonySection(mode="guided", numerals="VI - VII - i - V"),
            "puente": model.HarmonySection(mode="guided", numerals=None,
                                           chords="G/B - Dm9:2 - Fmaj7"),
        }
        r = compose_project(p, seed=seed, validate=True, save=False)
        self.assertTrue(r["ok"], r["errores"])
        return r

    def test_11_song_map_coincidente_con_compilado_real(self):
        from composer import bridge
        r = self._doc_con_literales(seed=2026)
        c = bridge.compile_preview(DMD_PATH, r["doc"])
        self.assertTrue(c.get("ok"), c.get("error"))
        por_id = {s["id"]: s for s in c["secciones"]}
        for row in r["song_map"]["secciones"]:
            comp = por_id[row["id"]]
            self.assertEqual(comp["bars"], row["compases"])
            if row["fuente_armonia"] in ("progressions_id", "explicito"):
                self.assertEqual(comp["chords"], row["progresion"],
                                 f"{row['id']}: mapa vs compilado discrepan")
            elif row["fuente_armonia"] == "receta_n1":
                self.assertEqual(comp["chords"], row["progresion"],
                                 f"{row['id']}: receta N1 mal calculada")
        # la sección con acordes literales queda marcada como 'explicito'
        puente = [row for row in r["song_map"]["secciones"] if row["id"] == "puente"][0]
        self.assertEqual(puente["fuente_armonia"], "explicito")
        self.assertIn("G/B", puente["progresion"])

    def test_12_importacion_en_studio_doc_con_literales(self):
        r = self._doc_con_literales()
        v = bridge.validate_doc(DMD_PATH, r["doc"])
        self.assertTrue(v.get("ok"), v.get("error"))
        self.assertEqual(v["validacion"]["errores"], [],
                         f"el validador REAL rechaza: {v['validacion']['errores']}")

    def test_12b_parser_real_rechaza_simbolos_invalidos(self):
        pc = bridge.parse_chords(DMD_PATH, ["G/B", "Dm9:2", "Fmaj7", "Xq7"])
        self.assertTrue(pc["ok"])
        ok_map = {r["simbolo"]: r["ok"] for r in pc["resultados"]}
        self.assertTrue(ok_map["G/B"] and ok_map["Dm9:2"] and ok_map["Fmaj7"])
        self.assertFalse(ok_map["Xq7"])
        gb = [r for r in pc["resultados"] if r["simbolo"] == "G/B"][0]
        self.assertEqual(gb["raiz"], "G")
        self.assertEqual(gb["bajo"], "B")

    def test_13_midi_real_con_perfil_de_la_instruccion(self):
        with tempfile.TemporaryDirectory(prefix="dmdc_i13_") as td:
            r = self._doc_con_literales(seed=777)
            cli_perfil = r["produccion"]["perfil"]
            out = Path(td) / "gen"
            res = _generar_midi(r["doc"], out, seed=777)
            self.assertTrue(res["ok"], res.get("error"))
            midi = Path(res["midi"])
            self.assertTrue(midi.exists() and midi.stat().st_size > 1000)
            self.assertEqual(cli_perfil, "full")


class TestIRegresionDemos(unittest.TestCase):
    """14: las cinco demostraciones originales siguen byte-reproducibles."""

    def test_14_demos_reproducibles(self):
        cp = subprocess.run([sys.executable, str(PKG / "scripts" / "demostraciones.py"),
                             "--verificar"], capture_output=True, text=True, timeout=300)
        self.assertEqual(cp.returncode, 0, cp.stdout[-500:] + cp.stderr[-300:])
        self.assertEqual(cp.stdout.count("[OK]"), 5, cp.stdout)
        self.assertNotIn("[DIFIERE]", cp.stdout)


class TestIRegresionAuditoria(unittest.TestCase):
    """D-02/D-03/D-07/D-09: resto del anexo del manual 1.0."""

    def test_d07_harmony_mode_libre_rechazado_por_api(self):
        from fastapi.testclient import TestClient
        from composer import server
        client = TestClient(server.app)
        p = client.post("/api/projects", json={"name": "I-d07"}).json()
        r = client.put(f"/api/projects/{p['pid']}", json={
            "decisions": {"harmony_mode": {"mode": "free"}}})
        self.assertEqual(r.status_code, 400)
        client.delete(f"/api/projects/{p['pid']}")

    def test_d03_identidad_archivada_avisa_al_componer(self):
        p = _proyecto_melancolico()
        p.decisions["identity"] = model.decision("fixed", "doom_triphop")
        p.sections = basic_sections()
        r = compose_project(p, seed=17, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        av = [a for a in r["avisos"] if a["code"] == "identidad-archivada"]
        self.assertEqual(len(av), 1)
        self.assertIn("dark_triphop", av[0]["message"])

    def test_d09_origen_del_manifiesto_distingue_vivo_de_cache(self):
        if not DMD_PATH:
            self.skipTest("sin DMD real")
        from composer import store
        m_cache = MF.get_manifest(DMD_PATH, store.DATA_DIR, refresh=False)
        m_vivo = MF.get_manifest(DMD_PATH, store.DATA_DIR, refresh=True)
        self.assertEqual(m_cache.get("origen"), "caché (misma ruta del DMD)")
        self.assertEqual(m_vivo.get("origen"), "vivo (introspeccionado ahora)")
        self.assertIn("identidades_archivadas", MF.catalog(m_cache))

    def test_catalogo_expone_identidad_activa(self):
        cat = MF.catalog(MANIFEST)
        self.assertEqual(cat.get("identidad_activa"), "dark_triphop")
        self.assertIn("doom_triphop", cat.get("identidades_archivadas", []))

    def test_codigo_muerto_eliminado(self):
        """D-04: LABEL_TYPES/LANG_DEFAULT_RES ya no existen (higiene)."""
        from composer import builder as B
        self.assertFalse(hasattr(B, "LANG_DEFAULT_RES"))
        self.assertFalse(hasattr(model, "LABEL_TYPES"))
        self.assertFalse(hasattr(model, "type_for_label"))


class TestIQaV11(unittest.TestCase):
    """Correcciones tras el QA independiente (bpm/seed Libre, protagonista none)."""

    def test_bpm_libre_no_se_escribe_y_se_clasifica(self):
        p = _proyecto_melancolico()
        p.decisions["bpm"] = model.decision("free")
        p.sections = basic_sections()
        r = compose_project(p, seed=18, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertNotIn("bpm", r["doc"].get("global", {}),
                         "bpm Libre: el motor decide (BPM_DEFAULT), nada escrito")
        self.assertIn("bpm", r["decisiones"]["libres"])
        bl = [l for l in r["log"] if l["axis"] == "bpm"]
        self.assertEqual(bl[0]["estado"], "free")

    def test_seed_libre_no_lleva_global_seed(self):
        p = _proyecto_melancolico()
        p.decisions["seed"] = model.decision("free")
        p.sections = basic_sections()
        r = compose_project(p, seed=18, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        self.assertNotIn("seed", r["doc"].get("global", {}),
                         "seed Libre: el doc NO lleva global.seed")
        self.assertIn("seed", r["decisiones"]["libres"])
        self.assertTrue(r["seed_used"] is not None)   # el plan sí es determinista

    def test_protagonista_fixed_none_log_fixed(self):
        p = _proyecto_melancolico()
        p.decisions["protagonist"] = model.decision("fixed", "none")
        p.sections = basic_sections()
        r = compose_project(p, seed=19, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        pl = [l for l in r["log"] if l["axis"] == "protagonist"]
        self.assertEqual(pl[0]["estado"], "fixed")
        self.assertEqual(pl[0]["valor"], "none")
        self.assertEqual(r["decisiones"]["fijadas"].get("protagonist"), "none")

    def test_rol_protagonista_sin_eje_avisa(self):
        p = _proyecto_melancolico()
        p.instruments["vibraphone"] = model.InstrumentDecision(role="protagonist")
        p.sections = basic_sections()
        r = compose_project(p, seed=20, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        av = [a for a in r["avisos"] if a["code"] == "conflicto-suave" and "protagonista" in a["message"]]
        self.assertEqual(len(av), 1, "rol protagonista sin eje debe avisar")


class TestIAlbumV11(unittest.TestCase):
    """Fase 2.8: álbum en lote + informe de diversidad (sin duplicar album/)."""

    def setUp(self):
        self._albums_dir_orig = ALB.ALBUMS_DIR
        self._projects_orig = store.PROJECTS_DIR
        self._output_orig = store.OUTPUT_DIR
        self._tmp = tempfile.mkdtemp(prefix="dmdc_i_alb_")
        ALB.ALBUMS_DIR = Path(self._tmp) / "albumes"
        store.PROJECTS_DIR = Path(self._tmp) / "projects"
        store.OUTPUT_DIR = Path(self._tmp) / "output"
        p = model.new_project("Universo I")
        p.pid = ""
        p.decisions.update({
            "identity": model.decision("fixed", "dark_triphop"),
            "mood": model.decision("fixed", "melancholic"),
            "harmony_mode": model.decision("fixed", "guided"),
            "protagonist": model.decision("fixed", "vibraphone"),
        })
        p.sections = basic_sections()
        p.harmony_sections = {
            "verso_1": model.HarmonySection(mode="guided", numerals="i - III - VII - VI"),
        }
        self.base = p

    def tearDown(self):
        ALB.ALBUMS_DIR = self._albums_dir_orig
        store.PROJECTS_DIR = self._projects_orig
        store.OUTPUT_DIR = self._output_orig
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_armonias_compartidas_llegan_a_las_pistas(self):
        plan = ALB.new_album("Uni", 2, self.base)
        self.assertEqual(plan["compartido"]["_harmonias"].get("verso_1", {}).get("numerals"),
                         "i - III - VII - VI")
        proj = ALB.track_project(plan["album_id"], 1)
        self.assertEqual(proj.harmony_sections["verso_1"].numerals, "i - III - VII - VI")

    def test_circulo_de_quintas_con_bemoles(self):
        """QA M-2: la métrica del círculo es correcta con bemoles."""
        self.assertEqual(ALB._key_distance("C major", "F major"), 1)     # una quinta
        self.assertEqual(ALB._key_distance("A major", "Eb major"), 6)    # tritono
        self.assertEqual(ALB._key_distance("F minor", "B minor"), 6)     # tritono
        self.assertEqual(ALB._key_distance("D minor", "A minor"), 1)
        self.assertIsNone(ALB._key_distance(None, "C major"))

    def test_generate_all_reanudable_e_informe(self):
        plan = ALB.new_album("Lote", 3, self.base)
        res = ALB.generate_all(plan["album_id"], DMD_PATH, MANIFEST)
        self.assertTrue(res["ok"], res["pistas"])
        self.assertEqual(len(res["pistas"]), 3)
        inf1 = res["informe"]
        self.assertEqual(inf1["pistas_listas"], 3)
        self.assertEqual(inf1["combinaciones_duplicadas"], 0)
        # reanudación: segunda pasada NO regenera (misma huella)
        res2 = ALB.generate_all(plan["album_id"], DMD_PATH, MANIFEST)
        estados = {p["estado"] for p in res2["pistas"]}
        self.assertEqual(estados, {"lista (sin regenerar)"})
        # informe persistido
        self.assertTrue((ALB.ALBUMS_DIR / plan["album_id"] / "informe.json").exists())

    def test_informe_diversidad_metricas(self):
        plan = ALB.new_album("Metricas", 4, self.base)
        res = ALB.generate_all(plan["album_id"], DMD_PATH, MANIFEST)
        inf = res["informe"]
        # QA: con 4 pistas y rotación sin repetir la anterior, la diversidad
        # tonal es >= 2 (el plan lo garantiza; no basta con >=1 vacío)
        self.assertGreaterEqual(inf["tonalidades_distintas"], 2,
                                "4 pistas con rotación deben dar >= 2 tonalidades")
        self.assertEqual(len(inf["distancia_tonal_consecutivas"]), 3)
        self.assertTrue(all(0 <= d <= 6 for d in inf["distancia_tonal_consecutivas"]))
        self.assertTrue(inf["bpm_rango"] and inf["bpm_rango"][0] <= inf["bpm_rango"][1])
        self.assertEqual(inf["combinaciones_duplicadas"], 0)
        # los resultados por pista incluyen pid (QA: localizar la generación)
        for p_ in res["pistas"]:
            self.assertIn("pid", p_)


if __name__ == "__main__":
    unittest.main()
