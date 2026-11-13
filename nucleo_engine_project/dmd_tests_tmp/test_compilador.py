"""Fase 1 — compilador mínimo dark-director/1 → midi-forge/1 (instrucción 09).

Verifica la traducción de los 7 tipos de sección, la escalera de precedencia
§2.3, meta.director, ending, guardrails §2.11, motifs (W407/W413 en emisión),
improvisación y la omisión de E3xx sin strict.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import compilador, contract, recetas
from dark_director.identities import dark_triphop as R

GOLDEN = json.loads((Path(__file__).parent / "golden" / "dark_triphop_balanced.json").read_text(encoding="utf-8"))


def _salida(doc=None):
    return compilador.compilar(copy.deepcopy(GOLDEN) if doc is None else doc)


def _proy(doc=None):
    return _salida(doc)["proyecto"]


class TestSchemaYMeta(unittest.TestCase):
    def test_schema_y_versiones(self):
        p = _proy()
        self.assertEqual(p["schema"], "midi-forge/1")
        d = p["meta"]["director"]
        self.assertEqual(d["contract"], "dark-director/1")
        self.assertEqual(d["contract_rev"], "3.2")
        self.assertEqual(d["compiler_version"], "0.1.0")
        self.assertEqual(d["compiler_stage"], "fase1")
        self.assertEqual(d["target_schema"], "midi-forge/1")
        self.assertEqual(d["source_schema"], "dark-director/1")

    def test_original_y_x_fields_viajan_en_meta_director(self):
        p = _proy()
        d = p["meta"]["director"]
        self.assertEqual(d["original"]["direction"]["identity"], "dark_triphop")
        self.assertEqual(d["x_mood"], "nocturnal")           # raíz → nombre plano
        self.assertEqual(d["original"]["x_mood"], "nocturnal")

    def test_x_anidado_lleva_prefijo_de_ruta(self):
        doc = copy.deepcopy(GOLDEN)
        doc["global"] = dict(doc["global"]); doc["global"]["x_gain"] = 1.5
        d = _proy(doc)["meta"]["director"]
        self.assertEqual(d["anidados"]["global.x_gain"], 1.5)


class TestTracks(unittest.TestCase):
    def test_set_base_y_programas_del_catalogo(self):
        p = _proy()
        por_id = {t["id"]: t for t in p["tracks"]}
        self.assertEqual(sorted(por_id), sorted(R.SET_BASE))
        self.assertEqual(por_id["sax_tenor"]["program"], 66)
        self.assertEqual(por_id["rhodes"]["program"], 4)
        self.assertEqual(por_id["vibraphone"]["program"], 11)
        self.assertEqual(por_id["bass"]["program"], 38)
        self.assertEqual(por_id["pad"]["program"], 91)
        self.assertEqual(por_id["drums"]["role"], "drums")
        self.assertIsNone(por_id["drums"].get("program"))

    def test_enabled_true_fuera_de_base_inicializa_por_251(self):
        doc = copy.deepcopy(GOLDEN)
        doc["instruments"] = dict(doc["instruments"]); doc["instruments"]["piano"] = {"enabled": True}
        p = _proy(doc)
        por_id = {t["id"]: t for t in p["tracks"]}
        self.assertIn("piano", por_id)
        self.assertEqual(por_id["piano"]["program"], 0)
        # bloque §2.5.1: hold con voicing full en la sección que suena
        bloques = {s["id"]: s["blocks"].get("piano") for s in p["sections"]}
        for sid, b in bloques.items():
            if b is None:
                continue
            if sid == "break_1":
                self.assertFalse(b["enabled"])  # whitelist lo excluye
            else:
                self.assertTrue(b["enabled"])
                self.assertEqual(b["style"], "hold")
                self.assertEqual(b["params"]["voicing"]["profile"], "full")


class TestTraduccion7Types(unittest.TestCase):
    """Un caso por cada uno de los 7 types del contrato (§2.6.x)."""

    def setUp(self):
        self.p = _proy()
        self.secs = {s["id"]: s for s in self.p["sections"]}
        self.assertEqual(set(self.secs),
                         {"intro", "verse_1", "pre_1", "chorus_1", "verse_2", "chorus_2",
                          "bridge_1", "break_1", "outro"})
        self.assertEqual([s["kind"] for s in self.p["sections"]],
                         ["intro", "verse", "pre", "chorus", "verse", "chorus",
                          "bridge", "break", "outro"])  # pre_chorus → pre (mapeo motor)

    def test_energy_solo_rampa_seccion(self):
        # §2.6.2: energy → SOLO section.velocity [v0, v1]
        self.assertEqual(self.secs["intro"]["velocity"], [55, 65])     # 0.25 ≤ 0.25
        self.assertEqual(self.secs["verse_1"]["velocity"], [68, 80])   # 0.45
        self.assertEqual(self.secs["chorus_2"]["velocity"], [98, 110]) # 0.85 > 0.75
        self.assertEqual(self.secs["outro"]["velocity"], [55, 65])     # 0.2

    def test_drums_por_nivel_y_vel_scale(self):
        b_intro = self.secs["intro"]["blocks"]["drums"]
        self.assertEqual(b_intro["params"]["preset"], "intro_air")   # air
        self.assertEqual(b_intro["params"]["vel_scale"], 0.85)
        b_verse = self.secs["verse_1"]["blocks"]["drums"]
        self.assertEqual(b_verse["params"]["preset"], "trip_verse")  # groove
        # focus 2º (drums en posición 1) → +0.03 → 1.03
        self.assertEqual(b_verse["params"]["vel_scale"], 1.03)
        b_chorus = self.secs["chorus_1"]["blocks"]["drums"]
        self.assertEqual(b_chorus["params"]["preset"], "trip_chorus")  # heavy
        self.assertEqual(b_chorus["params"]["vel_scale"], 1.13)        # 1.1 + 0.03 (2º)
        self.assertIn("fills", b_chorus["params"])                      # heavy = beat denso + fills
        b_pre = self.secs["pre_1"]["blocks"]["drums"]
        self.assertEqual(b_pre["params"]["preset"], "trip_bridge")     # light (sin improvisación)
        self.assertEqual(b_pre["params"]["vel_scale"], 0.95)
        # break_1 silencia drums por whitelist (active) → bloque none sin preset
        self.assertFalse(self.secs["break_1"]["blocks"]["drums"]["enabled"])
        # bridge_1 declara light PERO tiene improvisación de sax → drums baja un nivel → air
        b_bridge = self.secs["bridge_1"]["blocks"]["drums"]
        self.assertEqual(b_bridge["params"]["preset"], "intro_air")
        self.assertEqual(b_bridge["params"]["vel_scale"], 0.85)

    def test_bass_patrones_y_resolucion_tonal(self):
        b_intro = self.secs["intro"]["blocks"]["bass"]
        self.assertFalse(b_intro["enabled"])            # receta: intro sin bajo
        b_verse = self.secs["verse_1"]["blocks"]["bass"]
        self.assertTrue(b_verse["enabled"])
        self.assertEqual(b_verse["params"]["patterns"], R.BASS_PATRONES["verse"])
        # resolución heredada tonal (pop) → approach clavado en el compás final
        self.assertEqual(b_verse["params"]["approach"],
                         {"enabled": True, "every": 2, "offset": (16 - 1) % 2})
        self.assertEqual(b_verse["velocity"], 70)
        # break_1 → outro: bass inactivo en break_1 → gesto omitido (W421 avisado)
        b_break = self.secs["break_1"]["blocks"]["bass"]
        self.assertFalse(b_break["enabled"])

    def test_keys_voicing_por_bandas_de_tension_y_density(self):
        # tension intro 0.2 → B1 → full; verse 0.35 → B2 → shell; chorus 0.5 → B2
        self.assertEqual(self.secs["intro"]["blocks"]["rhodes"]["params"]["voicing"]["profile"], "full")
        self.assertEqual(self.secs["verse_1"]["blocks"]["rhodes"]["params"]["voicing"]["profile"], "shell")
        self.assertEqual(self.secs["verse_1"]["blocks"]["rhodes"]["style"], "broken")
        # density efectiva rhodes verse: sin D_inst → 0.45 → B2 → rest_prob 0.25
        self.assertEqual(self.secs["verse_1"]["blocks"]["rhodes"]["params"]["rest_prob"], 0.25)
        # pre_chorus hold: D_receta 0.55 → B2 → restrike_beats 4 (tabla §2.6.5)
        self.assertEqual(self.secs["pre_1"]["blocks"]["rhodes"]["params"]["restrike_beats"], 4)
        # outro tail: density 0.2 → B1 → notes_per_chord 1
        self.assertEqual(self.secs["outro"]["blocks"]["rhodes"]["params"]["notes_per_chord"], 1)

    def test_vibraphone_replies_por_banda_y_pings_en_intro(self):
        # verse: sin D_inst → 0.45 → B2 → prob 0.45, max_per_bar 2
        b = self.secs["verse_1"]["blocks"]["vibraphone"]
        self.assertEqual(b["style"], "replies")
        self.assertEqual((b["params"]["prob"], b["params"]["max_per_bar"]), (0.45, 2))
        self.assertEqual(b["params"]["respond_to"], "sax_tenor")
        # chorus_2: 0.7 → B3 → prob 0.60
        self.assertEqual(self.secs["chorus_2"]["blocks"]["vibraphone"]["params"]["prob"], 0.60)
        # intro pings: 0.25 → B1 → count 1
        b_intro = self.secs["intro"]["blocks"]["vibraphone"]
        self.assertEqual(b_intro["style"], "pings")
        self.assertEqual(b_intro["params"]["count"], 1)

    def test_pad_clusters_solo_en_B3(self):
        self.assertNotIn("tension", self.secs["intro"]["blocks"]["pad"]["params"])     # 0.2 B1
        # chorus_2 tension 0.55 → B2 → sin clusters; break_1 0.6 → B2 → sin clusters
        self.assertNotIn("tension", self.secs["break_1"]["blocks"]["pad"]["params"])
        self.assertEqual(self.secs["intro"]["blocks"]["pad"]["style"], "sustain")
        # caso B3 dedicado
        doc = copy.deepcopy(GOLDEN)
        doc["structure"][7]["tension"] = 0.75
        p2 = _proy(doc)
        sec2 = {s["id"]: s for s in p2["sections"]}
        self.assertIn("tension", sec2["break_1"]["blocks"]["pad"]["params"])
        cluster = sec2["break_1"]["blocks"]["pad"]["params"]["tension"][0]
        self.assertEqual(cluster, R.PAD_TENSION_CLUSTER)

    def test_lead_bloques_por_type(self):
        # intro: sin lead (receta)
        self.assertFalse(self.secs["intro"]["blocks"]["sax_tenor"]["enabled"])
        # chorus_1: material escrito (frases) → auto SIN density
        b1 = self.secs["chorus_1"]["blocks"]["sax_tenor"]
        self.assertEqual(b1["style"], "auto")
        self.assertNotIn("density", b1["params"])
        # chorus_2: destino de motif → auto con loop_bars 8
        b2 = self.secs["chorus_2"]["blocks"]["sax_tenor"]
        self.assertEqual(b2["params"]["loop_bars"], 8)
        self.assertNotIn("density", b2["params"])
        # verse_1: generativo → density por banda §2.6.5 (0.45 + (0.45−0.45) = 0.45 → B2 → 0.40)
        bv = self.secs["verse_1"]["blocks"]["sax_tenor"]
        self.assertEqual(bv["params"]["density"], 0.40)
        self.assertEqual(bv["params"]["long_prob"], 0.9)
        self.assertEqual(bv["params"]["range"], [60, 84])
        # bridge_1: improvisación → generative explícito (drums baja un nivel)
        bb = self.secs["bridge_1"]["blocks"]["sax_tenor"]
        self.assertEqual(bb["style"], "generative")
        # drums de bridge_1: light → air (improvisación baja un nivel)
        self.assertEqual(self.secs["bridge_1"]["blocks"]["drums"]["params"]["preset"], "intro_air")
        # outro: hold
        self.assertEqual(self.secs["outro"]["blocks"]["sax_tenor"]["style"], "hold")

    def test_focus_deltas_de_velocity(self):
        # verse_1 focus [sax_tenor, drums]: sax +8 → 68+8=76 ; drums vel_scale +0.06→(ya probado)
        self.assertEqual(self.secs["verse_1"]["blocks"]["sax_tenor"]["velocity"], 76)
        # chorus_1 focus [sax(1º +8), drums(2º), bass(3º +2)] → bass 86+2=88
        self.assertEqual(self.secs["chorus_1"]["blocks"]["bass"]["velocity"], 88)
        # intro focus [rhodes(+8), pad(+4)]
        self.assertEqual(self.secs["intro"]["blocks"]["rhodes"]["velocity"], 58)
        self.assertEqual(self.secs["intro"]["blocks"]["pad"]["velocity"], 49)

    def test_whitelist_active_apaga_bloques(self):
        b = self.secs["break_1"]["blocks"]
        self.assertTrue(b["vibraphone"]["enabled"])
        self.assertTrue(b["rhodes"]["enabled"])
        self.assertFalse(b["sax_tenor"]["enabled"])
        self.assertFalse(b["bass"]["enabled"])
        self.assertFalse(b["drums"]["enabled"])

    def test_los_7_types_tienen_progresion(self):
        for sid, sec in self.secs.items():
            self.assertTrue(sec["chords"], msg=f"{sid} sin acordes (§2.8: siempre hay)")
        # verse/chorus por progressions del compositor; resto por receta N1
        self.assertEqual(self.secs["verse_1"]["chords"], ["Dm9", "Bbmaj7", "Fmaj9", "C7sus4"])
        self.assertEqual(self.secs["chorus_1"]["chords"], ["Bbmaj9", "Fmaj9", "Gm9", "A7sus4"])
        for sid in ("intro", "pre_1", "bridge_1", "break_1", "outro"):
            for acorde in self.secs[sid]["chords"]:
                self.assertRegex(acorde, r"^[A-G][#b]?")


class TestMotifsYPhrases(unittest.TestCase):
    def test_phrases_passthrough_y_copia_de_motif(self):
        p = _proy()
        ph = p["lead"]["phrases"]
        self.assertEqual(len(ph["chorus_1"]), 5)
        self.assertEqual(len(ph["chorus_2"]), 5)      # copia completa (cabe en 16)
        self.assertEqual(ph["chorus_2"][0]["pitch"], 69)  # A4 → MIDI 69 (pitches absolutos)

    def test_truncado_y_transposicion_en_emision(self):
        doc = copy.deepcopy(GOLDEN)
        doc["development"]["melody"]["phrases"]["bridge_1"] = [
            {"bar": 7, "beat": 3.0, "pitch": "C5", "dur": 1.0},   # cabe en bridge (8 bars)
        ]
        doc["development"]["motifs"]["hook_a"]["sections"] = ["chorus_2", "bridge_1"]
        doc["development"]["motifs"]["hook_a"]["transpose_st"] = 12
        out = _salida(doc)
        ph = out["proyecto"]["lead"]["phrases"]
        # chorus_2 (16 bars): 5 notas de chorus_1 (el motif copia SOLO desde from_section)
        self.assertEqual(len(ph["chorus_2"]), 5)
        # bridge_1 (8 bars): su propia nota "C5" (passthrough 1:1) + 5 copiadas
        self.assertEqual(len(ph["bridge_1"]), 6)
        self.assertEqual(ph["bridge_1"][0]["pitch"], "C5")
        self.assertEqual(ph["bridge_1"][1]["pitch"], 81)   # A4 (69) + 12 (transpose_st)
        # outro no recibe nada
        self.assertNotIn("outro", ph)


class TestEndingGuardrailsQA(unittest.TestCase):
    def test_fade_out_start_calculado(self):
        e = _proy()["ending"]["fade_out"]
        self.assertTrue(e["enabled"])
        self.assertEqual(e["start"], {"section": "outro", "bar": 2})  # 8 − 6
        self.assertEqual(e["cc"], 11)

    def test_guardrails_balanced_y_override_qa(self):
        g = _proy()["guardrails"]
        self.assertTrue(g["motif_repeat"])       # balanced derivado ON (loop_bars=8: sin W408)
        self.assertTrue(g["lead_coverage"])      # override explícito del compositor
        self.assertTrue(g["mallet_sparse"])
        self.assertTrue(g["four_on_floor"])

    def test_motif_repeat_derivado_se_apaga_con_loop_8_distinto(self):
        doc = copy.deepcopy(GOLDEN)
        doc["development"]["motifs"]["hook_a"]["loop_bars"] = 16
        g = _proy(doc)["guardrails"]
        self.assertFalse(g["motif_repeat"])      # §2.11: derivado → OFF + W408
        avisos = _salida(doc)["avisos"]
        self.assertTrue(any(a.startswith("W408") for a in avisos))


class TestE3xxYStrict(unittest.TestCase):
    def test_e301_se_omite_sin_strict_y_bloquea_con_strict(self):
        doc = copy.deepcopy(GOLDEN)
        # chorus_2 no declara active (sin contradicción E203): la entrada es
        # E301 pura (capacidad) → se omite sin strict, bloquea con strict
        doc["development"]["improvisation"] = [{"section": "chorus_2", "instrument": "piano"}]
        out = _salida(doc)
        self.assertTrue(any(a.startswith("E301") for a in out["e3xx_omitidos"]))
        # la entrada omitida NO convierte el lead de chorus_2 en generativo
        sec = {s["id"]: s for s in out["proyecto"]["sections"]}
        self.assertNotEqual(sec["chorus_2"]["blocks"]["sax_tenor"]["style"], "generative")
        doc2 = copy.deepcopy(doc); doc2["qa"] = {"strict": True}
        with self.assertRaises(compilador.StrictBloqueante):
            _salida(doc2)

    def test_e1xx_bloquea_siempre(self):
        doc = copy.deepcopy(GOLDEN)
        doc["structure"][0]["bars"] = 0
        with self.assertRaises(compilador.DirectorInvalido) as cm:
            _salida(doc)
        self.assertIn("E105", [c for c, _m in cm.exception.resultado["errores"]])

    def test_receta_ausente_para_doom(self):
        # ADAPTADO (Fase 2, RESPUESTA 09): en Fase 1 afirmaba RecetaNoDefinida
        # para doom_triphop; desde el registro de las recetas doom, el golden
        # reencaminado a doom_triphop COMPILA (el changeling hereda structure/
        # harmony del golden y la receta doom_triphop traduce sus 7 types).
        doc = copy.deepcopy(GOLDEN)
        doc["direction"]["identity"] = "doom_triphop"
        out = _salida(doc)
        self.assertEqual(out["proyecto"]["schema"], "midi-forge/1")
        # y una identidad FUERA del contrato sigue sin receta (nunca se inventa)
        doc2 = copy.deepcopy(GOLDEN)
        doc2["direction"]["identity"] = "synthwave"
        # el validador bloquea antes (E105 identity fuera del enum)
        with self.assertRaises(compilador.DirectorInvalido):
            _salida(doc2)


class TestDeterminismoDelProyecto(unittest.TestCase):
    def test_dos_compilaciones_identicas(self):
        a = json.dumps(_proy(), sort_keys=True, ensure_ascii=False)
        b = json.dumps(_proy(), sort_keys=True, ensure_ascii=False)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
