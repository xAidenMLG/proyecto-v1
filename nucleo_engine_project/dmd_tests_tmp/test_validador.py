"""Fase 1 — validador de entrada E1xx/E2xx/E3xx + W4xx (rev. 3 §2.10, rev. 3.2).

Cada caso cita la regla contractual que dispara el código. Incluye los checks
que el QA documental de rev. 3 no necesitaba (E203/E204/E114) y la doctrina de
honestidad: W401/W403 sin receta real van a ``no_verificados``, nunca se inventa
un rango o una tabla.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract, validador


def _base_doc():
    return {
        "schema": "dark-director/1",
        "direction": {"identity": "dark_triphop", "accessibility": "balanced"},
        "global": {"bpm": 86, "seed": 11},
        "harmony": {"key": "D minor", "language": "pop_dream_pop"},
        "structure": [
            {"id": "a", "type": "intro", "bars": 8, "drums": "air"},
            {"id": "b", "type": "verse", "bars": 16, "drums": "groove"},
        ],
    }


def _codigos(res):
    return [c for c, _m in res["errores"]]


def _avisos(res):
    return [c for c, _m in res["avisos"]]


class TestE1xx(unittest.TestCase):
    def test_E101_raiz_no_objeto(self):
        res = validador.validar([1, 2, 3])
        self.assertIn("E101", _codigos(res))

    def test_E102_schema(self):
        d = _base_doc(); d["schema"] = "dark-director/2"
        self.assertIn("E102", _codigos(validador.validar(d)))
        d2 = _base_doc(); del d2["schema"]
        self.assertIn("E102", _codigos(validador.validar(d2)))

    def test_E103_requeridos(self):
        d = _base_doc(); del d["direction"]
        self.assertIn("E103", _codigos(validador.validar(d)))
        d2 = _base_doc(); del d2["harmony"]["key"]
        self.assertIn("E103", _codigos(validador.validar(d2)))
        d3 = _base_doc(); del d3["harmony"]["language"]
        self.assertIn("E103", _codigos(validador.validar(d3)))

    def test_E105_enums_y_rangos(self):
        d = _base_doc(); d["direction"]["identity"] = "synthwave"
        self.assertIn("E105", _codigos(validador.validar(d)))
        d2 = _base_doc(); d2["global"]["bpm"] = 500
        self.assertIn("E105", _codigos(validador.validar(d2)))
        d3 = _base_doc(); d3["structure"][0]["drums"] = "medio"
        self.assertIn("E105", _codigos(validador.validar(d3)))
        d4 = _base_doc(); d4["structure"][1]["focus"] = ["sax_tenor", "drums", "bass", "pad"]
        self.assertIn("E105", _codigos(validador.validar(d4)))
        d5 = _base_doc(); d5["harmony"]["key"] = 123
        self.assertIn("E105", _codigos(validador.validar(d5)))
        # la gramática REAL de parse_key es tolerante con strings (fallback a
        # defaults del motor), así que un string siempre «parsea»: la condición
        # real de E105-key es el no-string (comportamiento del motor verificado)

    def test_E106_structure(self):
        d = _base_doc(); d["structure"] = [{"id": "a", "type": "intro", "bars": 4}]
        self.assertIn("E106", _codigos(validador.validar(d)))
        d2 = _base_doc(); d2["structure"][1]["id"] = "a"
        self.assertIn("E106", _codigos(validador.validar(d2)))

    def test_E107_referencias_rotas(self):
        # una clave de progressions que NO es id ni type → E107 ('chorus' sí es type: no dispara)
        d = _base_doc()
        d["harmony"]["progressions"] = {"chorus": ["Dm9"]}
        self.assertNotIn("E107", _codigos(validador.validar(d)))
        d2 = _base_doc()
        d2["harmony"]["progressions"] = {"seccion_fantasma": ["Dm9"]}
        self.assertIn("E107", _codigos(validador.validar(d2)))
        d3 = _base_doc()
        d3["development"] = {"improvisation": [{"section": "fantasma", "instrument": "sax_tenor"}]}
        self.assertIn("E107", _codigos(validador.validar(d3)))
        d4 = _base_doc()
        d4["development"] = {"melody": {"phrases": {"fantasma": []}}}
        self.assertIn("E107", _codigos(validador.validar(d4)))

    def test_E108_motif_sin_frases_y_frases_vacias(self):
        d = _base_doc()
        d["development"] = {"motifs": {"m": {"from_section": "a", "sections": ["b"]}}}
        self.assertIn("E108", _codigos(validador.validar(d)))
        d2 = _base_doc()
        d2["development"] = {"melody": {"phrases": {"a": []}},
                             "motifs": {"m": {"from_section": "a", "sections": ["b"]}}}
        self.assertIn("E108", _codigos(validador.validar(d2)))

    def test_E109_campo_desconocido_y_x_extensión(self):
        d = _base_doc(); d["swing"] = 0.5
        self.assertIn("E109", _codigos(validador.validar(d)))
        d2 = _base_doc(); d2["x_mood"] = "nocturnal"
        self.assertNotIn("E109", _codigos(validador.validar(d2)))
        d3 = _base_doc(); d3["x_"] = 1  # 'x_' a secas NO es extensión
        self.assertIn("E109", _codigos(validador.validar(d3)))
        d4 = _base_doc(); d4["qa"] = {"guardrails": {"no_existe": True}}
        self.assertIn("E109", _codigos(validador.validar(d4)))

    def test_E110_fuera_del_catalogo(self):
        d = _base_doc(); d["instruments"] = {"theremin": {"enabled": True}}
        self.assertIn("E110", _codigos(validador.validar(d)))
        d2 = _base_doc(); d2["structure"][0]["focus"] = ["theremin"]
        self.assertIn("E110", _codigos(validador.validar(d2)))
        # responses sobre id del catálogo que NO es mallet → E303 (capacidad)
        d3 = _base_doc(); d3["development"] = {"responses": {"piano": {"responds_to": "sax_tenor"}}}
        res = validador.validar(d3)
        self.assertIn("E303", [c for c, _m in res["e3xx"]])

    def test_E111_notas_de_frase(self):
        d = _base_doc()
        d["development"] = {"melody": {"phrases": {"b": [
            {"bar": 16, "beat": 0.0, "pitch": "C4", "dur": 1.0},   # bar fuera (bars=16 → máx 15)
            {"bar": 0, "beat": 4.0, "pitch": "C4", "dur": 1.0},    # beat fuera de [0,4)
            {"bar": 15, "beat": 3.5, "pitch": "C4", "dur": 1.0},   # sobrepasa el final (64.5 > 64)
            {"bar": 0, "beat": 0.0, "pitch": "H4", "dur": 1.0},    # pitch no parsea
            {"bar": 0, "beat": 0.0, "pitch": "C4", "dur": 0.0},    # dur <= 0
        ]}}}
        res = validador.validar(d)
        self.assertEqual(_codigos(res).count("E111"), 5, msg=_codigos(res))

    def test_E112_ending(self):
        d = _base_doc()
        d["ending"] = {"fade_out": {"enabled": True, "bars": 9}}  # > bars de 'b' (16)? 9 ≤ 16 → OK
        self.assertNotIn("E112", _codigos(validador.validar(d)))
        d2 = _base_doc()
        d2["ending"] = {"fade_out": {"enabled": True, "bars": 20}}  # > 16 → E112
        self.assertIn("E112", _codigos(validador.validar(d2)))
        d3 = _base_doc()
        d3["ending"] = {"tape_stop": {"enabled": True, "bars": 0}}
        self.assertIn("E112", _codigos(validador.validar(d3)))

    def test_E113_acorde_no_parseable(self):
        d = _base_doc()
        d["harmony"]["progressions"] = {"verse": ["Dm9", "Xq7"]}
        self.assertIn("E113", _codigos(validador.validar(d)))
        d2 = _base_doc()
        d2["structure"][1]["chords"] = ["Cm77baz"]
        self.assertIn("E113", _codigos(validador.validar(d2)))

    def test_E114_inicializacion_insegura(self):
        # E114 a nivel DOCUMENTO es inalcanzable con las 3 identidades v1
        # (vibes/bass/drums son base en todas; piano/strings/pad inicializan
        # siempre seguro — §2.5.1), como la propia rev. 3.1 documentó para el
        # motor. La decisión pura E114 se prueba en test_inicializacion.py y
        # el compilador la re-verifica defensivamente.
        d = _base_doc()
        d["instruments"] = {"piano": {"enabled": True}, "strings": {"enabled": True}}
        res = validador.validar(d)
        self.assertNotIn("E114", _codigos(res))

    def test_E203_y_E204(self):
        d = _base_doc()
        d["structure"][1]["active"] = ["rhodes", "bass", "drums", "pad"]  # excluye al sax
        d["development"] = {"improvisation": [{"section": "b", "instrument": "sax_tenor"}]}
        self.assertIn("E203", _codigos(validador.validar(d)))
        d2 = _base_doc()
        d2["development"] = {"melody": {"phrases": {"b": [{"bar": 0, "beat": 0.0, "pitch": "C4", "dur": 1.0}]}}}
        d2["instruments"] = {"sax_tenor": {"enabled": False}}
        self.assertIn("E204", _codigos(validador.validar(d2)))
        d3 = _base_doc()
        d3["development"] = {"motifs": {"m": {"from_section": "a", "sections": ["b"]}},
                             "melody": {"phrases": {"a": [{"bar": 0, "beat": 0.0, "pitch": "C4", "dur": 1.0}]}}}
        d3["structure"][1]["active"] = ["rhodes", "bass", "drums", "pad"]
        self.assertIn("E204", _codigos(validador.validar(d3)))


class TestE3xx(unittest.TestCase):
    def test_E301_E302_separados_de_errores(self):
        d = _base_doc()
        d["development"] = {"improvisation": [{"section": "b", "instrument": "piano"}]}
        res = validador.validar(d)
        self.assertEqual(_codigos(res), [])
        self.assertIn("E301", [c for c, _m in res["e3xx"]])
        d2 = _base_doc()
        d2["development"] = {"responses": {"vibraphone": {"responds_to": "bass"}}}
        res2 = validador.validar(d2)
        self.assertEqual(_codigos(res2), [])
        self.assertIn("E302", [c for c, _m in res2["e3xx"]])


class TestW4xx(unittest.TestCase):
    def test_W411_pares_atipicos(self):
        d = _base_doc()
        d["direction"] = {"identity": "doom_dark_jazz", "accessibility": "commercial"}
        self.assertIn("W411", _avisos(validador.validar(d)))
        d2 = _base_doc()
        d2["direction"] = {"identity": "dark_triphop", "accessibility": "balanced"}
        self.assertNotIn("W411", _avisos(validador.validar(d2)))

    def test_W401_solo_con_receta_y_rango_real(self):
        # ADAPTADO (Fase 2): antes doom_triphop no tenía receta → W401 en
        # no_verificados; desde el registro, W401 usa el rango REAL de la
        # receta (RESPUESTA 09 T4: fuera de (58,90) avisa, dentro no).
        d = _base_doc(); d["global"]["bpm"] = 140
        res = validador.validar(d)
        self.assertIn("W401", _avisos(res))          # dark_triphop [70, 96]
        d2 = _base_doc()
        d2["direction"] = {"identity": "doom_triphop", "accessibility": "balanced"}
        d2["global"]["bpm"] = 140
        res2 = validador.validar(d2)
        self.assertIn("W401", _avisos(res2))         # doom_triphop [58, 90]
        d3 = _base_doc()
        d3["direction"] = {"identity": "doom_triphop", "accessibility": "balanced"}
        d3["global"]["bpm"] = 80
        self.assertNotIn("W401", _avisos(validador.validar(d3)))
        d4 = _base_doc()
        d4["direction"] = {"identity": "doom_dark_jazz", "accessibility": "balanced"}
        d4["global"]["bpm"] = 62
        self.assertNotIn("W401", _avisos(validador.validar(d4)))
        d5 = _base_doc()
        d5["direction"] = {"identity": "doom_dark_jazz", "accessibility": "balanced"}
        d5["global"]["bpm"] = 90
        self.assertIn("W401", _avisos(validador.validar(d5)))   # doom_dark_jazz [50, 74]

    def test_W403_banda_B3_rev32_y_cancelacion(self):
        d = _base_doc()
        d["structure"][1]["density"] = 0.7
        self.assertIn("W403", _avisos(validador.validar(d)))
        d2 = _base_doc(); d2["structure"][1]["density"] = 0.67
        self.assertIn("W403", _avisos(validador.validar(d2)))     # >= 0.67 → B3 (rev. 3.2)
        d3 = _base_doc(); d3["structure"][1]["density"] = 0.669999
        self.assertNotIn("W403", _avisos(validador.validar(d3)))  # < 0.67 → B2

    def test_W409_tension_B3_sin_pad_ni_strings(self):
        d = _base_doc()
        d["structure"][1]["tension"] = 0.7
        d["structure"][1]["active"] = ["sax_tenor", "rhodes", "vibraphone", "bass", "drums"]
        self.assertIn("W409", _avisos(validador.validar(d)))

    def test_W414_vocabulario(self):
        d = _base_doc()
        d["harmony"]["progressions"] = {"verse": ["Dm9", "A7b9"]}   # 7b9 → experimental
        self.assertIn("W414", _avisos(validador.validar(d)))
        d2 = _base_doc()
        d2["harmony"]["language"] = "experimental"
        d2["harmony"]["progressions"] = {"verse": ["A7b9"]}
        self.assertNotIn("W414", _avisos(validador.validar(d2)))

    def test_W412_W420_W421_transiciones(self):
        d = _base_doc()
        d["structure"][1]["resolution"] = "tonal"   # última sección explícita
        self.assertIn("W412", _avisos(validador.validar(d)))
        d2 = _base_doc()
        d2["structure"][0]["bars"] = 1
        d2["structure"][0]["resolution"] = "tonal"
        self.assertIn("W420", _avisos(validador.validar(d2)))
        d3 = _base_doc()
        d3["structure"][0]["active"] = ["rhodes", "vibraphone", "pad", "drums"]  # sin bass
        self.assertIn("W421", _avisos(validador.validar(d3)))   # resolution heredada tonal (pop)

    def test_W415_W416_W417_W418(self):
        d = _base_doc()
        d["structure"][0]["final"] = True
        d["structure"][1]["final"] = True
        self.assertIn("W415", _avisos(validador.validar(d)))
        d2 = _base_doc()
        d2["ending"] = {"fade_out": True, "tape_stop": True}
        self.assertIn("W416", _avisos(validador.validar(d2)))
        d3 = _base_doc(); d3["harmony"]["harmonic_rhythm_bars"] = 2
        d3["structure"][1]["bars"] = 15
        self.assertIn("W417", _avisos(validador.validar(d3)))
        d4 = _base_doc()
        d4["development"] = {"improvisation": [{"section": "a", "instrument": "sax_tenor"}]}
        d4["structure"][0]["drums"] = "off"
        self.assertIn("W418", _avisos(validador.validar(d4)))

    def test_W404_y_W405(self):
        d = _base_doc()
        d["direction"]["accessibility"] = "commercial"
        self.assertIn("W404", _avisos(validador.validar(d)))
        d2 = _base_doc(); d2["global"]["velocity_cap"] = 120
        d2["direction"]["identity"] = "doom_triphop"
        self.assertIn("W405", _avisos(validador.validar(d2)))

    def test_W406_entrada_ignorada(self):
        d = _base_doc()
        d["structure"][1]["focus"] = ["sax_tenor"]
        d["structure"][1]["active"] = ["rhodes", "bass", "drums", "pad"]
        self.assertIn("W406", _avisos(validador.validar(d)))

    def test_W407_W413_W419_motifs(self):
        d = _base_doc()
        d["development"] = {
            "melody": {"phrases": {"a": [
                {"bar": 9, "beat": 0.0, "pitch": "C6", "dur": 1.0},   # bar 9 >= bars de 'b' tras el ajuste
                {"bar": 0, "beat": 0.0, "pitch": "C4", "dur": 1.0},
            ]}},
            "motifs": {"m": {"from_section": "a", "sections": ["b"], "loop_bars": 20}},
        }
        d["structure"][1]["bars"] = 8
        res = validador.validar(d)
        self.assertIn("W407", _avisos(res))   # bar 9 >= 8 → truncada
        self.assertIn("W419", _avisos(res))   # loop_bars 20 > 8
        d2 = _base_doc()
        d2["development"] = {
            "melody": {"phrases": {"a": [{"bar": 0, "beat": 0.0, "pitch": "C4", "dur": 1.0}]}},
            "motifs": {"m": {"from_section": "a", "sections": ["b"], "transpose_st": -24}},
        }
        d2["instruments"] = {"sax_tenor": {"register": [60, 84]}}
        self.assertIn("W413", _avisos(validador.validar(d2)))   # 36 fuera de [60, 84]

    def test_W408_regla_motif_repeat(self):
        d = _base_doc()
        d["development"] = {
            "melody": {"phrases": {"a": [{"bar": 0, "beat": 0.0, "pitch": "C4", "dur": 1.0}]}},
            "motifs": {"m": {"from_section": "a", "sections": ["b"], "loop_bars": 16}},
        }
        res = validador.validar(d)
        self.assertIn("W408", _avisos(res))   # balanced → derivado ON → OFF + W408
        d2 = _base_doc()
        d2["direction"]["accessibility"] = "experimental"
        self.assertNotIn("W408", _avisos(validador.validar(d2)))  # derivado OFF → sin aviso

    def test_W410_density_sin_traduccion(self):
        d = _base_doc()
        d["instruments"] = {"bass": {"density": 0.4}}
        self.assertIn("W410", _avisos(validador.validar(d)))
        # density de sección NUNCA emite W410 (§2.6.5)
        d2 = _base_doc(); d2["structure"][0]["density"] = 0.8
        self.assertNotIn("W410", _avisos(validador.validar(d2)))


if __name__ == "__main__":
    unittest.main()
