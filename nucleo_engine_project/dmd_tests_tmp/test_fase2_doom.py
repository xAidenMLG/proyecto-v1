"""FASE 2 — Pruebas T1–T24 de RESPUESTA 09 (§7), adaptadas a la implementación.

Traza EXACTA con la lista de pruebas de RESPUESTA 09 (§7). Notas de adaptación:
  - T19 (suite completa en verde) es meta: se ejecuta con
    ``python -m unittest discover -s tests -t .`` (146 pruebas; no es replicable
    dentro de un test).
  - T22/T23/T24 son de ESCUCHA: aquí se implementan sus equivalentes
    estructurales (T22e/T23e/T24e) que verifican en el proyecto compilado y en
    el MIDI generado los marcadores objetivos de cada identidad; la escucha
    humana queda documentada como paso pendiente del compositor (no se ejecutó
    ninguna prueba audible).
"""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dark_director import accesibilidad, compilador, contract, forge_link, recetas  # noqa: E402
from dark_director import identities as _ids  # noqa: E402
from dark_director import inicializacion  # noqa: E402
from dark_director import validador  # noqa: E402

GOLDEN = json.loads((Path(__file__).parent / "golden" / "dark_triphop_balanced.json").read_text(encoding="utf-8"))
CANON_DTH = json.loads((Path(__file__).parent / "golden" / "doom_triphop_balanced.json").read_text(encoding="utf-8"))
CANON_DDJ = json.loads((Path(__file__).parent / "golden" / "doom_dark_jazz_experimental.json").read_text(encoding="utf-8"))

#: sha256 congelado del golden dark_triphop (T18)
GOLDEN_SHA_CONGELADO = "f5dd37b8dc8e70cc0c1fac12e3a3e693bdee00dfb8082c2ee3875bec66a3cadf"


def _doc_base(identity="doom_triphop", access="balanced", language="hybrid"):
    """Documento mínimo con los 7 types para las pruebas de traducción."""
    return {
        "schema": "dark-director/1",
        "direction": {"identity": identity, "accessibility": access},
        "global": {"bpm": 72 if identity == "doom_triphop" else 62, "seed": 11},
        "harmony": {"key": "D minor", "language": language, "harmonic_rhythm_bars": 2},
        "structure": [
            {"id": "intro", "type": "intro", "bars": 8},
            {"id": "verse_1", "type": "verse", "bars": 16},
            {"id": "pre_1", "type": "pre_chorus", "bars": 8},
            {"id": "chorus_1", "type": "chorus", "bars": 16},
            {"id": "bridge_1", "type": "bridge", "bars": 8},
            {"id": "break_1", "type": "break", "bars": 8},
            {"id": "outro", "type": "outro", "bars": 8, "final": True},
        ],
    }


def _secciones(proyecto):
    return {s["id"]: s for s in proyecto["sections"]}


def _por_type(doc):
    """Compila y devuelve {type: sección del proyecto} vía el id de la primera
    sección de cada type en la estructura de ENTRADA (el proyecto de salida no
    lleva 'type': lleva id/kind)."""
    type_de = {s["id"]: s["type"] for s in doc["structure"]}
    out = compilador.compilar(doc)
    por_type = {}
    for s in out["proyecto"]["sections"]:
        t = type_de.get(s["id"])
        if t and t not in por_type:
            por_type[t] = s
    return out, por_type


# ------------------------------------------------------------------ T1–T3
class TContratoYRecetas(unittest.TestCase):
    def test_T1_registro_failfast_de_las_tres(self):
        self.assertEqual(tuple(recetas.RECETAS_REGISTRADAS.keys()),
                         ("dark_triphop", "doom_triphop", "doom_dark_jazz"))
        for mod in (_ids.dark_triphop, _ids.doom_triphop, _ids.doom_dark_jazz):
            tabla = recetas.load_receta(mod.IDENTITY)
            self.assertEqual(recetas.verificar_completitud(tabla), ())
        # una D_receta incompleta NO se registra (fail-fast §2.6.5)
        tabla_mala = {t: 0.5 for t in contract.SECTION_TYPES if t != "break"}
        with self.assertRaises(recetas.RecetaError):
            recetas.registrar_receta("dark_triphop", tabla_mala)

    def test_T2_coherencia_c5_tablas_bloques(self):
        for mod in (_ids.doom_triphop, _ids.doom_dark_jazz):
            problemas = recetas.verificar_tabla_bloques(mod)
            self.assertEqual(problemas, (), msg=f"{mod.IDENTITY}: {problemas}")
            base = set(mod.SET_BASE)
            for t in contract.SECTION_TYPES:
                fila = mod.BLOQUES[t]
                self.assertTrue(base <= set(fila),
                                msg=f"{mod.IDENTITY}/{t}: faltan {base - set(fila)}")

    def test_T3_e114_doctrina_con_los_nuevos_sets(self):
        # vibráfono inicializado sin lead sigue bloqueando (doctrina §2.5.1)
        estado, _d = inicializacion.estado_inicializacion(
            "vibraphone", en_base=False, existe_lead=False)
        self.assertEqual(estado, "E114")
        # bass/drums sin datos de receta siguen E114
        for iid in ("bass", "drums"):
            estado, _d = inicializacion.estado_inicializacion(
                iid, en_base=False, existe_lead=True, receta_da_datos=False)
            self.assertEqual(estado, "E114")
        # con los sets doom, vibraphone/bass/drums son BASE → ok-base sin error
        for mod in (_ids.doom_triphop, _ids.doom_dark_jazz):
            for iid in mod.SET_BASE:
                estado, _d = inicializacion.estado_inicializacion(
                    iid, en_base=True, existe_lead=False, receta_da_datos=False)
                self.assertEqual(estado, "ok-base")
        # y el pad puede inicializarse fuera de base en doom_dark_jazz (C4 intacto)
        estado, _d = inicializacion.estado_inicializacion(
            "pad", en_base=False, existe_lead=True, receta_da_datos=True)
        self.assertEqual(estado, "ok")


# ------------------------------------------------------------------ T4–T9
class TValidadorConRecetasDoom(unittest.TestCase):
    def test_T4_W401_rangos_reales_por_identidad(self):
        for identity, bpm_fuera, bpm_dentro in (
                ("doom_triphop", 95, 72), ("doom_dark_jazz", 90, 62)):
            d = _doc_base(identity); d["global"]["bpm"] = bpm_fuera
            self.assertIn("W401", [c for c, _m in validador.validar(d)["avisos"]])
            d["global"]["bpm"] = bpm_dentro
            self.assertNotIn("W401", [c for c, _m in validador.validar(d)["avisos"]])

    def test_T5_W402_ritmo_armonico(self):
        d = _doc_base("doom_dark_jazz")
        d["harmony"]["harmonic_rhythm_bars"] = 1
        self.assertIn("W402", [c for c, _m in validador.validar(d)["avisos"]])
        d["harmony"]["harmonic_rhythm_bars"] = 2
        self.assertNotIn("W402", [c for c, _m in validador.validar(d)["avisos"]])

    def test_T6_W405_velocity_cap_doom(self):
        d = _doc_base("doom_triphop"); d["global"]["velocity_cap"] = 120
        self.assertIn("W405", [c for c, _m in validador.validar(d)["avisos"]])
        d2 = _doc_base("dark_triphop"); d2["global"]["velocity_cap"] = 120
        self.assertNotIn("W405", [c for c, _m in validador.validar(d2)["avisos"]])

    def test_T7_W409_tension_b3_sin_pad_ni_strings(self):
        d = _doc_base("doom_dark_jazz")
        d["structure"][4]["tension"] = 0.75           # bridge
        d["structure"][4]["active"] = ["sax_tenor", "rhodes", "bass", "piano"]
        self.assertIn("W409", [c for c, _m in validador.validar(d)["avisos"]])
        del d["structure"][4]["active"]
        self.assertNotIn("W409", [c for c, _m in validador.validar(d)["avisos"]])

    def test_T8_W411_y_W418_con_recetas_doom(self):
        d = _doc_base("doom_dark_jazz", access="commercial")
        self.assertIn("W411", [c for c, _m in validador.validar(d)["avisos"]])
        # improvisación en bridge (default doom_dark_jazz: drums off) → W418
        d2 = _doc_base("doom_dark_jazz")
        d2["development"] = {"improvisation": [{"section": "bridge_1",
                                                "instrument": "sax_tenor"}]}
        self.assertIn("W418", [c for c, _m in validador.validar(d2)["avisos"]])
        # improvisación en break (default doom_dark_jazz: air ≥ air) → sin W418
        d3 = _doc_base("doom_dark_jazz")
        d3["development"] = {"improvisation": [{"section": "break_1",
                                                "instrument": "sax_tenor"}]}
        self.assertNotIn("W418", [c for c, _m in validador.validar(d3)["avisos"]])

    def test_T9_formula_coexistencia_con_nuevas_d_receta(self):
        for mod in (_ids.doom_triphop, _ids.doom_dark_jazz):
            for t, d_r in mod.D_RECETA.items():
                # propiedad 1 (cancelación): sección declara → efectiva == d_secc
                e1 = contract.density_efectiva(None, 0.5, d_r)
                self.assertEqual(e1, 0.5)
                # propiedad 3 (ambas): evolución conservada sobre la base
                e2 = contract.density_efectiva(0.45, 0.55, d_r)
                self.assertAlmostEqual(e2, 0.45 + (0.55 - d_r), places=12)
                # dominio
                self.assertTrue(0.0 <= contract.density_efectiva(None, None, d_r) <= 1.0)


# ------------------------------------------------------------------ T10–T15
class TTraduccionCompilador(unittest.TestCase):
    def test_T10_traduccion_7_types_doom_triphop(self):
        _out, sec = _por_type(_doc_base("doom_triphop"))
        # cadena de transformación en los bloques (tabla §3.4)
        self.assertEqual(sec["intro"]["blocks"]["drums"]["params"]["preset"], "intro_air")
        self.assertEqual(sec["verse"]["blocks"]["drums"]["params"]["preset"], "trip_verse")
        self.assertFalse(sec["break"]["blocks"]["drums"].get("enabled", True))   # ruptura = silencio
        self.assertEqual(sec["bridge"]["blocks"]["drums"]["params"]["preset"], "trip_bridge")
        # 1.1 de tabla + delta de focus (drums en focus pos 1 → +0.03)
        self.assertEqual(sec["chorus"]["blocks"]["drums"]["params"]["vel_scale"], 1.13)
        self.assertFalse(sec["intro"]["blocks"]["sax_tenor"].get("enabled", True))
        self.assertEqual(sec["verse"]["blocks"]["sax_tenor"]["style"], "auto")
        self.assertEqual(sec["pre_chorus"]["blocks"]["sax_tenor"]["params"]["contour"], "rising")
        self.assertEqual(sec["break"]["blocks"]["sax_tenor"]["style"], "hold")
        self.assertEqual(sec["break"]["blocks"]["sax_tenor"]["params"]["legato"], 1.0)
        self.assertEqual(sec["bridge"]["blocks"]["bass"]["params"].get("fifth_at"), 4)
        self.assertEqual(sec["break"]["blocks"]["bass"]["params"].get("fifth_at"), 0)
        self.assertEqual(sec["verse"]["blocks"]["strings"]["params"]["voicing"]["profile"], "bare")
        self.assertEqual(sec["chorus"]["blocks"]["strings"]["params"]["voicing"]["profile"], "spread")
        self.assertEqual(sec["break"]["blocks"]["strings"]["params"]["voicing"]["profile"], "rootoctave")
        # clusters B3: bridge/break tension default ≥ 0.67 → cluster adjunto
        self.assertTrue(sec["break"]["blocks"]["pad"]["params"].get("tension"))
        self.assertTrue(sec["bridge"]["blocks"]["pad"]["params"].get("tension"))
        self.assertFalse(sec["verse"]["blocks"]["pad"]["params"].get("tension"))

    def test_T10_traduccion_7_types_doom_dark_jazz(self):
        _out, sec = _por_type(_doc_base("doom_dark_jazz"))
        # sin pad en el set base; piano y strings base (D-02)
        ids_pistas = {t["id"] for t in _por_type(_doc_base("doom_dark_jazz"))[0]["proyecto"]["tracks"]}
        self.assertNotIn("pad", ids_pistas)
        self.assertIn("piano", ids_pistas)
        self.assertIn("strings", ids_pistas)
        # estados: DOOM (intro/bridge/outro) vs DJ (verse/pre/chorus/break)
        self.assertFalse(sec["bridge"]["blocks"]["drums"].get("enabled", True))
        self.assertEqual(sec["intro"]["blocks"]["drums"]["params"]["preset"], "intro_air")
        self.assertEqual(sec["verse"]["blocks"]["drums"]["params"].get("vel_scale"), 0.9)
        self.assertIn("ride", [l["inst"] for l in sec["verse"]["blocks"]["drums"]["params"]["layers"]])
        self.assertIn("shaker", [l["inst"] for l in sec["break"]["blocks"]["drums"]["params"]["layers"]])
        self.assertEqual(sec["verse"]["blocks"]["rhodes"]["params"]["voicing"]["profile"], "rootless")
        self.assertEqual(sec["intro"]["blocks"]["rhodes"]["params"]["voicing"]["profile"], "compact")
        self.assertEqual(sec["verse"]["blocks"]["piano"]["params"]["voicing"]["profile"], "bare")
        self.assertEqual(sec["bridge"]["blocks"]["strings"]["params"].get("modes"), ["bare", "full"])
        self.assertTrue(sec["bridge"]["blocks"]["strings"]["params"].get("tension"))  # clusters sin pad
        self.assertEqual(sec["break"]["blocks"]["sax_tenor"]["style"], "generative")

    def test_T11_approach_por_resolution_ambas_recetas(self):
        for identity in ("doom_triphop", "doom_dark_jazz"):
            for res, esperado in (("tonal", True), ("chromatic", True),
                                  ("modal", False), ("deceptive", False), ("open", False)):
                d = _doc_base(identity)
                d["harmony"]["resolution"] = res
                _out, sec = _por_type(d)
                ap = sec["verse"]["blocks"]["bass"]["params"]["approach"]["enabled"]
                self.assertEqual(ap, esperado,
                                 msg=f"{identity}/{res}: approach={ap}")

    def test_T12_active_focus_y_E110(self):
        # deltas de focus §2.6.4 sobre la tabla: intro focus [pad, strings]
        # → pad (pos 0) +8 = 48, strings (pos 1) +4 = 42
        out = compilador.compilar(_doc_base("doom_triphop"))
        sec = _secciones(out["proyecto"])
        self.assertEqual(sec["intro"]["blocks"]["pad"]["velocity"], 48)
        self.assertEqual(sec["intro"]["blocks"]["strings"]["velocity"], 42)
        # active recorta (whitelist §2.6.1) y el focus que no suena → W406
        d = _doc_base("doom_triphop")
        d["structure"][1]["focus"] = ["sax_tenor"]
        d["structure"][1]["active"] = ["rhodes", "bass", "drums", "pad", "strings"]
        res = validador.validar(d)
        self.assertIn("W406", [c for c, _m in res["avisos"]])
        out2 = compilador.compilar(d)
        sec2 = _secciones(out2["proyecto"])
        self.assertFalse(sec2["verse_1"]["blocks"]["sax_tenor"].get("enabled", True))
        # E110 en active con id fuera del catálogo
        d2 = _doc_base("doom_triphop")
        d2["structure"][1]["active"] = ["theremin"]
        self.assertIn("E110", [c for c, _m in validador.validar(d2)["errores"]])

    def test_T13_x_preservados_y_E109(self):
        d = _doc_base("doom_dark_jazz")
        d["x_doom"] = {"cadena": "alternancia"}
        d["structure"][1]["x_estado"] = "dark_jazz"
        out = compilador.compilar(d)
        meta = out["proyecto"]["meta"]["director"]
        self.assertEqual(meta["x_doom"], {"cadena": "alternancia"})
        self.assertEqual(meta["anidados"]["structure.x_estado"], "dark_jazz")
        # clave sin prefijo x_ → E109
        d2 = _doc_base("doom_dark_jazz")
        d2["campo_prohibido"] = 1
        self.assertIn("E109", [c for c, _m in validador.validar(d2)["errores"]])

    def test_T14_ending_improv_motifs(self):
        d = _doc_base("doom_triphop")
        d["ending"] = {"tape_stop": {"enabled": True, "bars": 3}}
        d["development"] = {
            "improvisation": [{"section": "break_1", "instrument": "sax_tenor"}],
            "melody": {"phrases": {"verse_1": [
                {"bar": 0, "beat": 0.0, "pitch": 74, "dur": 1.5},
                {"bar": 1, "beat": 0.5, "pitch": 72, "dur": 1.0}]}},
            "motifs": {"m1": {"from_section": "verse_1", "sections": ["chorus_1"],
                              "transpose_st": 1}},
        }
        out = compilador.compilar(d)
        p = out["proyecto"]
        self.assertTrue(p["ending"]["tape_stop"]["enabled"])
        self.assertEqual(p["ending"]["tape_stop"]["bars"], 3)
        sec = _secciones(p)
        # improvisación → generativo explícito + drums bajados un nivel
        # (break default off → sigue off; nivel nivel−1 = off)
        self.assertEqual(sec["break_1"]["blocks"]["sax_tenor"]["style"], "generative")
        self.assertFalse(sec["break_1"]["blocks"]["drums"].get("enabled", True))
        # motif copiado a chorus_1 con transpose +1
        self.assertEqual(sec["chorus_1"]["blocks"]["sax_tenor"]["style"], "auto")
        frases = p["lead"]["phrases"]["chorus_1"]
        self.assertEqual(frases[0]["pitch"], 75)          # 74 + 1
        # frases también siguen en verse_1 (material escrito)
        self.assertEqual(sec["verse_1"]["blocks"]["sax_tenor"]["style"], "auto")

    def test_T15_pre_final_occurrence(self):
        d = _doc_base("doom_triphop")
        out = compilador.compilar(d)
        sec = _secciones(out["proyecto"])
        self.assertEqual(sec["pre_1"]["kind"], "pre")
        self.assertTrue(sec["outro"]["final"])
        self.assertFalse(any(s["final"] for sid, s in sec.items() if sid != "outro"))
        # W415: dos final → gana la última
        d2 = _doc_base("doom_triphop")
        d2["structure"][1]["final"] = True
        self.assertIn("W415", [c for c, _m in validador.validar(d2)["avisos"]])


# ------------------------------------------------------------------ T16–T18
class TGoldenDeterminismo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = forge_link.import_forge()

    def _midi_sha(self, doc):
        out = compilador.compilar(copy.deepcopy(doc))
        p, rep = self.f.adapter.normalize(out["proyecto"])
        errores = [r for r in rep if r["level"] == "error"]
        self.assertEqual(errores, [], msg=rep)
        res = self.f.engine.generate(p)
        return hashlib.sha256(res.midi).hexdigest(), p

    def test_T16_golden_doom_triphop_reproducible(self):
        h1, _p = self._midi_sha(CANON_DTH)
        h2, _p2 = self._midi_sha(CANON_DTH)
        self.assertEqual(h1, h2)
        self.assertEqual(h1, "cf3255299f024db8eb4576499a51bdfb7a1df231e0d344e8e8049128d7425df0")

    def test_T16_golden_doom_dark_jazz_reproducible(self):
        h1, _p = self._midi_sha(CANON_DDJ)
        h2, _p2 = self._midi_sha(CANON_DDJ)
        self.assertEqual(h1, h2)
        self.assertEqual(h1, "42bff7bc3fd90b93a53cc5fd49c74931c2d874cfd8a6c4b84be9e7e2e732aa62")

    def test_T17_independencia_de_bloques(self):
        out = compilador.compilar(copy.deepcopy(CANON_DTH))
        p, _rep = self.f.adapter.normalize(out["proyecto"])
        res1 = self.f.engine.generate(copy.deepcopy(p))
        p2 = copy.deepcopy(p)
        # cambiar la seed del bloque de vibráfono del break NO altera el resto
        p2["sections"][3]["blocks"]["vibraphone"]["seed"] = 999
        res2 = self.f.engine.generate(p2)

        def firma(res, tid):
            b = [x for x in res.bufs if x.track["id"] == tid][0]
            return [(round(n.t, 3), n.p, round(n.d, 3), n.v) for n in b.notes]

        for tid in ("drums", "bass", "sax_tenor", "rhodes", "pad", "strings"):
            self.assertEqual(firma(res1, tid), firma(res2, tid),
                             msg=f"la seed del bloque alteró la pista {tid}")

    def test_T18_golden_dark_triphop_byte_identico(self):
        h, _p = self._midi_sha(GOLDEN)
        self.assertEqual(h, GOLDEN_SHA_CONGELADO)


# ------------------------------------------------------------------ T20–T21
class TMotorIntactoYCompliance(unittest.TestCase):
    """T20: forge/ sin cambios (hashes congelados, sin .pyc nuevos).
    T21: compliance del motor sobre los 2 canónicos doom."""

    HASHES_FORGE = {
        "__init__.py": "4edaf220ae17daa7b92875556e519c37871fc892c9c835688e6ca59b8281a19c",
        "adapter.py": "2259b81b41f8230ee99ff60ac3f5a00288abf5c8ead5081e06124cc68f27c3ed",
        "audio.py": "084337f718a40cf97ceb7210dced79635fc2652a94fcbb214b017dce88926455",
        "engine.py": "7bdf0381dd86458efb7a1061a06c2045ab1defc6316d40fadba9d7c537476dd7",
        "midiwriter.py": "db078799d0d6b47a21400b9bedbbf898337ab2bb37f5978c97153e94ab52bb9e",
        "styles.py": "1c632bfadbe9142d93ec02baa40d14967625262f35b90b1fec67d6c44f579976",
        "theory.py": "138e0675e8ae9ff98decf9db022ac9ba8bcdb7c1435fff0426552b647e21d502",
        "validate.py": "bfc186a6e79dfa9883391cf342c376eb2267cc51a3095530bec5c42038273234",
        "voicing.py": "12845686a7810e025a3ad97cc0cecfec277b2ea6af6f014441c0bab83e9d4ab0",
    }

    def test_T20_forge_sin_cambios(self):
        root = Path("/home/z/my-project/audit/midi_forge/forge")
        for nombre, hash_congelado in self.HASHES_FORGE.items():
            ruta = root / nombre
            self.assertTrue(ruta.is_file(), msg=f"falta forge/{nombre}")
            self.assertEqual(
                hashlib.sha256(ruta.read_bytes()).hexdigest(), hash_congelado,
                msg=f"forge/{nombre} CAMBIÓ (archivo congelado, restricción R2)")
        pycs = sorted(p.name for p in (root / "__pycache__").glob("*.pyc"))
        self.assertEqual(len(pycs), 9,
                         msg="hay .pyc nuevos en forge/__pycache__ (protección rota): "
                             f"{pycs}")

    def test_T21_compliance_canonicos_doom(self):
        f = self.f if hasattr(self, "f") else forge_link.import_forge()
        for doc in (CANON_DTH, CANON_DDJ):
            with self.subTest(titulo=doc["meta"]["title"]):
                out = compilador.compilar(copy.deepcopy(doc))
                p, rep = f.adapter.normalize(out["proyecto"])
                self.assertEqual([r for r in rep if r["level"] == "error"], [], msg=rep)
                res = f.engine.generate(p)
                comp = f.validate.compliance(res)
                fallos = [c for c in comp if c["status"] == "fail" and c.get("requested")]
                self.assertEqual(fallos, [],
                                 msg=[(c["id"], c["detail"]) for c in fallos])
                # los guardrails siempre-ON pedidos por el contrato no fallan
                ids_pedidos = {c["id"] for c in comp if c.get("requested")}
                self.assertTrue({"lead_mono_range", "mallet_sparse", "lead_mallet_overlap",
                                 "bass_kick", "four_on_floor"} <= ids_pedidos)


# ------------------------------------------------------------------ T22–T24e
class TEvidenciaEstructuralIdentidades(unittest.TestCase):
    """Equivalentes ESTRUCTURALES de las pruebas de escucha T22–T24. La escucha
    humana (la escucha manda sobre las métricas) NO se ejecutó: queda como paso
    pendiente documentado en la respuesta."""

    @classmethod
    def setUpClass(cls):
        cls.f = forge_link.import_forge()

    def _compilar_y_generar(self, doc):
        out = compilador.compilar(copy.deepcopy(doc))
        p, rep = self.f.adapter.normalize(out["proyecto"])
        res = self.f.engine.generate(p)
        return out, p, res

    def _notas_por_seccion(self, p, res, tid):
        """Notas por sección usando el tiempo NOMINAL de cada nota (no el
        ejecutado): el jitter gaussiano del motor desplaza n.t ±0.03 beats y
        puede cruzar fronteras; n.nominal conserva la atribución exacta."""
        t0 = 0
        conteo = {}
        for s in p["sections"]:
            t1 = t0 + s["bars"] * 4
            b = [x for x in res.bufs if x.track["id"] == tid][0]
            conteo[s["id"]] = sum(1 for n in b.notes if t0 <= n.nom < t1)
            t0 = t1
        return conteo

    def test_T22e_doom_triphop_marcadores_de_transformacion(self):
        out, p, res = self._compilar_y_generar(CANON_DTH)
        sec = _secciones(p)
        # 1. el groove DESAPARECE: drums OFF en el break (ruptura I); cero notas
        # de drums generadas por el break (interior de la sección)
        self.assertFalse(sec["break_1"]["blocks"]["drums"].get("enabled", True))
        self.assertEqual(self._notas_por_seccion(p, res, "drums")["break_1"], 0)
        # 2. el groove REGRESA TRANSFORMADO: chorus heavy + fills + armonía hybrid
        # (1.1 de la tabla + delta de focus §2.6.4: drums en focus pos 1 → +0.03)
        self.assertEqual(sec["chorus_1"]["blocks"]["drums"]["params"]["vel_scale"], 1.13)
        self.assertIn("layers", sec["chorus_1"]["blocks"]["drums"]["params"])
        # 3. sax: ausente (intro) → motivo (verses/chorus) → planos (break/bridge/outro)
        self.assertFalse(sec["intro"]["blocks"]["sax_tenor"].get("enabled", True))
        self.assertEqual(sec["break_1"]["blocks"]["sax_tenor"]["style"], "hold")
        frases_v1 = p["lead"]["phrases"]["verse_1"]
        frases_c1 = p["lead"]["phrases"]["chorus_1"]
        self.assertEqual([n["pitch"] for n in frases_c1],
                         [n["pitch"] + 1 for n in frases_v1])   # transposición
        # 4. clusters B3 en el break (deformación armónica)
        self.assertTrue(sec["break_1"]["blocks"]["pad"]["params"].get("tension"))
        # 5. bajo: en la ruptura el patrón se disuelve en un drone (long)
        self.assertEqual(sec["break_1"]["blocks"]["bass"]["style"], "long")
        self.assertEqual(sec["break_1"]["blocks"]["bass"]["params"].get("fifth_at"), 0)
        # 6. automatización de receta presente (swell CC11)
        self.assertTrue(p["automation"])
        self.assertTrue(all(a["cc"] == 11 for a in p["automation"]))

    def test_T23e_doom_dark_jazz_marcadores_de_alternancia(self):
        out, p, res = self._compilar_y_generar(CANON_DDJ)
        sec = _secciones(p)
        conteo = {tid: self._notas_por_seccion(p, res, tid)
                  for tid in ("drums", "strings", "sax_tenor", "vibraphone", "piano")}
        # 1. sin pad; strings SIEMPRE presentes (estrato Doom que respira)
        self.assertNotIn("pad", {t["id"] for t in p["tracks"]})
        for sid in sec:
            self.assertTrue(sec[sid]["blocks"]["strings"].get("enabled", True))
            self.assertGreater(conteo["strings"][sid], 0)
        # 2. alternancia de estados: bridge = DOOM puro (drums off, sax hold)
        self.assertFalse(sec["bridge_1"]["blocks"]["drums"].get("enabled", True))
        self.assertEqual(conteo["drums"]["bridge_1"], 0)
        self.assertEqual(sec["bridge_1"]["blocks"]["sax_tenor"]["style"], "hold")
        # 3. el jazz NO desaparece en Doom: sax hold suena (presente, subordinado)
        self.assertGreater(conteo["sax_tenor"]["bridge_1"], 0)
        # 4. DJ: rhodes rootless + ride en verse; interacción sax↔vibráfono
        self.assertEqual(sec["theme_a"]["blocks"]["rhodes"]["params"]["voicing"]["profile"],
                         "rootless")
        self.assertGreater(conteo["vibraphone"]["break_1"], 1)   # dúo cámara real
        # 5. clusters B3 SIN pad → sobre strings (mecanismo gen_chordal)
        self.assertTrue(sec["bridge_1"]["blocks"]["strings"]["params"].get("tension"))
        # 6. bajo upright
        b = [t for t in p["tracks"] if t["id"] == "bass"][0]
        self.assertEqual(b["program"], 32)

    def test_T24e_ninguna_sona_a_dark_triphop_estructura(self):
        # comparación estructural A/B de las TRES recetas (la escucha A/B queda
        # pendiente; aquí se demuestra que las identidades SON distintas por datos)
        mods = (_ids.dark_triphop, _ids.doom_triphop, _ids.doom_dark_jazz)
        sets = [tuple(m.SET_BASE) for m in mods]
        self.assertEqual(len(set(sets)), 3)                       # sets base distintos
        self.assertEqual(mods[0].BPM_RANGO_TIPICO, (70, 96))
        self.assertEqual(mods[1].BPM_RANGO_TIPICO, (58, 90))
        self.assertEqual(mods[2].BPM_RANGO_TIPICO, (50, 74))
        self.assertNotEqual(mods[0].DRUMS_NIVEL["break"],
                            mods[1].DRUMS_NIVEL["break"])         # light vs off
        self.assertFalse(hasattr(mods[0], "BLOQUES"))             # tabla solo en doom
        self.assertTrue(hasattr(mods[1], "BLOQUES"))
        self.assertTrue(hasattr(mods[2], "BLOQUES"))
        self.assertNotEqual(mods[1].BLOQUES["break"], mods[2].BLOQUES["break"])
        # progresiones distintas para el mismo (language, type)
        self.assertNotEqual(mods[0].PROGRESIONES["hybrid"]["verse"],
                            mods[1].PROGRESIONES["hybrid"]["verse"])
        self.assertNotEqual(mods[1].PROGRESIONES["hybrid"]["verse"],
                            mods[2].PROGRESIONES["hybrid"]["verse"])


if __name__ == "__main__":
    unittest.main()
