"""C · Armonía — parser de grados romanos REAL y compatibilidad con el motor."""
import sys
import unittest
from pathlib import Path

from util import DMD_PATH, HAS_DMD, basic_sections, compose_project, new_test_project

from composer import harmony as H, model

REAL_THEORY = None
if DMD_PATH:
    p = str(Path(DMD_PATH))
    if p not in sys.path:
        sys.path.insert(0, p)
    try:
        from forge import theory as REAL_THEORY  # noqa: N813
    except Exception:
        REAL_THEORY = None


class TestCArmonia(unittest.TestCase):

    # ---- tonalidades -------------------------------------------------------
    def test_c1_mayores_y_menores(self):
        for lbl, tonic, mode in [("C major", 0, "ionian"), ("Eb major", 3, "ionian"),
                                 ("A minor", 9, "aeolian"), ("F# minor", 6, "aeolian"),
                                 ("Bb minor", 10, "aeolian")]:
            k = H.parse_key(lbl)
            self.assertEqual((k.tonic, k.mode), (tonic, mode), lbl)

    def test_c2_tonalidad_ambigua_es_error_no_silencio(self):
        for bad in ["Do menor", "Sol major", "C joven", ""]:
            with self.assertRaises(H.HarmonyError):
                H.parse_key(bad)

    def test_c3_modos_eclesiasticos(self):
        k = H.parse_key("A dorian")
        self.assertEqual((k.tonic, k.mode), (9, "dorian"))
        k2 = H.parse_key("E phrygian")
        self.assertEqual(k2.mode, "phrygian")
        k3 = H.parse_key("D harmonic minor")
        self.assertEqual(k3.mode, "harmonic_minor")

    # ---- grados romanos ----------------------------------------------------
    def test_c4_tabla_completa_de_la_mision(self):
        k = H.parse_key("C major")
        tabla = {"I": "C", "iii": "Em", "vi": "Am", "V": "G", "IV": "F",
                 "ii": "Dm", "vii": "Bdim"}
        for rom, esperado in tabla.items():
            self.assertEqual(H.resolve_progression(rom, k)[0].symbol, esperado, rom)

    def test_c5_alteraciones(self):
        k = H.parse_key("C major")
        self.assertEqual(H.resolve_progression("bVI", k)[0].symbol, "Ab")
        self.assertEqual(H.resolve_progression("bVII", k)[0].symbol, "Bb")
        # ortografía con bemoles: la MISMA del compilador real (_NOMBRES_NOTA)
        self.assertEqual(H.resolve_progression("#iv0", k)[0].symbol, "Gbdim")

    def test_c6_dominante_en_menor(self):
        """V en menor = dominante mayor (convención estándar del pop)."""
        k = H.parse_key("A minor")
        self.assertEqual(H.resolve_progression("V", k)[0].symbol, "E")
        self.assertEqual(H.resolve_progression("V7", k)[0].symbol, "E7")
        self.assertEqual(H.resolve_progression("Vm", k)[0].symbol, "Em")

    def test_c7_inversiones(self):
        k = H.parse_key("C major")
        self.assertEqual(H.resolve_progression("vi6", k)[0].symbol, "Am/C")
        self.assertEqual(H.resolve_progression("ii64", k)[0].symbol, "Dm/A")
        self.assertEqual(H.resolve_progression("V7/B", k)[0].symbol, "G7/B")

    def test_c8_ritmo_armonico_por_acorde(self):
        k = H.parse_key("C major")
        ch = H.resolve_progression("I:2 - V:1 - vi - IV:4", k)
        self.assertEqual([c.bars for c in ch], [2.0, 1.0, None, 4.0])
        self.assertEqual(ch[0].symbol, "C:2")

    def test_c9_progresiones_de_distinta_longitud(self):
        k = H.parse_key("D minor")
        for n in (1, 2, 3, 4, 5, 6, 8):
            prog = " - ".join(["i", "III", "VI", "VII", "iv", "v", "i", "VII"][:n])
            self.assertEqual(len(H.resolve_progression(prog, k)), n)

    def test_c10_progresion_invalida_con_mensaje_posicional(self):
        k = H.parse_key("C major")
        with self.assertRaises(H.HarmonyError) as ctx:
            H.resolve_progression("I - IX - V", k)
        self.assertIn("posición 2", str(ctx.exception))

    def test_c11_progresion_ambigua_grado_inventado(self):
        k = H.parse_key("C major")
        with self.assertRaises(H.HarmonyError):
            H.resolve_progression("X - Y - Z", k)
        # 'i0' ya es válido (0 = disminuido, cortesía de sintaxis); una
        # combinación imposible como 'i09' sigue siendo error con mensaje
        self.assertEqual(H.resolve_progression("i0", k)[0].symbol, "Cdim")
        with self.assertRaises(H.HarmonyError):
            H.resolve_progression("i09", k)

    # ---- compatibilidad con la gramática REAL del motor ---------------------
    def test_c12_todos_los_simbolos_parsean_con_theory_real(self):
        if not REAL_THEORY:
            self.skipTest("sin forge/theory accesible")
        casos = [
            ("C major", "I - ii - iii - IV - V - vi - vii"),
            ("A minor", "i - iio - III - iv - v - VI - VII"),
            ("D minor", "i7 - iv9 - V7 - bVImaj7 - viio7 - iim7b5"),
            ("Eb major", "I6 - ii64 - iii - IVmaj9 - V7sus4 - vi"),
            ("F# minor", "i - III+ - ivm6 - V7b9 - bIImaj7"),
            ("G dorian", "i - IV - bVII - iim7b5 - v9 - Imaj"),
        ]
        for kt, prog in casos:
            k = H.parse_key(kt)
            for c in H.resolve_progression(prog, k):
                sym = c.symbol.split(":")[0]
                try:
                    REAL_THEORY.parse_chord(sym)
                except ValueError as e:
                    self.fail(f"{sym} ({c.roman} en {kt}) no parsea en el motor: {e}")

    def test_c13_vocabulario_por_lenguaje_w414(self):
        k = H.parse_key("A minor")
        ch = H.resolve_progression("i - V7 - iim7b5", k)
        avisos = H.tier_warnings(ch, "pop_dream_pop")
        self.assertEqual(len(avisos), 2)     # E7 y m7b5 son hybrid, no pop
        avisos_h = H.tier_warnings(ch, "hybrid")
        self.assertEqual(avisos_h, [])

    # ---- integración con el compilador real ---------------------------------
    @unittest.skipUnless(HAS_DMD, "sin DMD real")
    def test_c14_el_compilador_real_acepta_las_progresiones(self):
        from composer import bridge
        p = new_test_project(mood="dark")
        p.decisions["key"] = model.decision("fixed", "C minor")
        p.decisions["language"] = model.decision("fixed", "hybrid")
        p.decisions["harmonic_rhythm_bars"] = model.decision("fixed", 2)
        p.sections = [
            model.Section(id="intro", label="Intro", type="intro", bars=8),
            model.Section(id="verso", label="Verse", type="verse", bars=16),
            model.Section(id="outro", label="Outro", type="outro", bars=8, final=True),
        ]
        p.harmony_sections = {
            "intro": model.HarmonySection(mode="guided", numerals="i - iim7b5 - bVI - V7"),
            "verso": model.HarmonySection(mode="guided", numerals="i - i - bVI - bVII - i - i - bVI - V7:2"),
            "outro": model.HarmonySection(mode="guided", numerals="i - V7"),
        }
        r = compose_project(p, seed=21, validate=False)
        self.assertTrue(r["ok"], r["errores"])
        c = bridge.compile_preview(DMD_PATH, r["doc"])
        self.assertTrue(c.get("ok"), c.get("error"))
        # los acordes compilados = los que Composer escribió (id por sección)
        por_id = {s["id"]: s for s in c["secciones"]}
        self.assertEqual(por_id["verso"]["chords"], r["doc"]["harmony"]["progressions"]["verso"])
        self.assertEqual(por_id["verso"]["chord_bars"], 2)


if __name__ == "__main__":
    unittest.main()
