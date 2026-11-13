"""Fase 1 — GOLDEN TEST determinista de principio a fin (instrucción 09, criterio de aceptación).

Ruta completa: JSON dark-director/1 → compilador → proyecto midi-forge/1 →
forge.adapter.normalize → forge.engine.generate → MIDI (bytes) → sha256.

Se afirma:
  1. el proyecto pasa normalize con 0 errores;
  2. el motor genera MIDI y la validación post-generación no introduce fails
     nuevos (compliance con los guardrails emitidos);
  3. DOS ejecuciones completas producen MIDI byte a byte idéntico
     (reproducibilidad determinista);
  4. los avisos del compilador para el golden fixture son EXACTOS (mismo
     CONJUNTO que H.1 del contrato + bridge con improvisación, que no añade);
  5. los 3 ejemplos del contrato revalidan 0 errores con el validador REAL y
     los avisos EXACTOS documentados — extraídos de la rev. 3 (fuente única,
     mismo método de extracción que el QA de rev. 3).
"""
import hashlib
import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import compilador, forge_link, validador

GOLDEN = json.loads((Path(__file__).parent / "golden" / "dark_triphop_balanced.json").read_text(encoding="utf-8"))

REV3 = Path("/home/z/my-project/download/respuesta_03_validacion_final_dark_director.md")


def _ejemplos_rev3():
    """Los 3 JSON del contrato, extraídos de la rev. 3 (fuente única)."""
    texto = REV3.read_text(encoding="utf-8")
    bloques, pat, pos = [], re.compile(r"```json\n(.*?)\n```", re.S), 0
    while True:
        m = pat.search(texto, pos)
        if not m:
            break
        pos = m.end()
        try:
            obj = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("schema") == "dark-director/1":
            bloques.append(obj)
    assert len(bloques) == 3, f"rev. 3 debe contener exactamente 3 ejemplos, hay {len(bloques)}"
    return {b["meta"]["title"]: b for b in bloques}


def _midi_bytes(doc):
    out = compilador.compilar(doc)
    f = forge_link.import_forge()
    p, rep = f.adapter.normalize(out["proyecto"])
    res = f.engine.generate(p)
    return out, p, rep, res


class TestGoldenE2E(unittest.TestCase):
    def test_avisos_exactos_del_golden(self):
        out = compilador.compilar(copy.deepcopy(GOLDEN))
        # el CONJUNTO de avisos es exacto (la rev. 3 documenta conjuntos, no
        # un orden de emisión); bridge con improvisación no añade avisos
        self.assertEqual(sorted(a.split(":")[0] for a in out["avisos"]),
                         ["W403", "W410", "W410", "W421"],
                         msg=out["avisos"])

    def test_normalize_sin_errores(self):
        out = compilador.compilar(copy.deepcopy(GOLDEN))
        f = forge_link.import_forge()
        p, rep = f.adapter.normalize(out["proyecto"])
        errores = [r for r in rep if r["level"] == "error"]
        self.assertEqual(errores, [], msg=rep)
        self.assertEqual(p["schema"], "midi-forge/1")

    def test_midi_reproducible_byte_a_byte(self):
        out, p, rep, res = _midi_bytes(copy.deepcopy(GOLDEN))
        h1 = hashlib.sha256(res.midi).hexdigest()
        out2, p2, rep2, res2 = _midi_bytes(copy.deepcopy(GOLDEN))
        h2 = hashlib.sha256(res2.midi).hexdigest()
        self.assertEqual(h1, h2, msg="el MIDI no es reproducible byte a byte")
        self.assertGreater(len(res.midi), 1000, msg="MIDI sospechosamente pequeño")
        # el proyecto normalizado también es idéntico
        self.assertEqual(json.dumps(p, sort_keys=True, ensure_ascii=False),
                         json.dumps(p2, sort_keys=True, ensure_ascii=False))

    def test_val_post_generacion_y_compliance(self):
        f = forge_link.import_forge()
        out = compilador.compilar(copy.deepcopy(GOLDEN))
        p, rep = f.adapter.normalize(out["proyecto"])
        res = f.engine.generate(p)
        val = f.validate.validate(res)
        comp = f.validate.compliance(res)
        # ninguna comprobación pedida (requested) termina en fail
        fails = [c["id"] for c in comp if c["status"] == "fail" and c.get("requested")]
        self.assertEqual(fails, [], msg=[(c["id"], c["detail"]) for c in comp if c.get("requested")])
        self.assertGreater(val["bars"], 0)
        # notas generadas en todas las pistas activas
        conteo = {b.track["id"]: len(b.notes) for b in res.bufs}
        for tid in ("sax_tenor", "rhodes", "vibraphone", "bass", "drums", "pad"):
            self.assertGreater(conteo[tid], 0, msg=f"pista {tid} sin notas")

    def test_ruta_desde_string_json(self):
        texto = json.dumps(GOLDEN, ensure_ascii=False)
        out = compilador.compilar(texto)
        self.assertEqual(out["proyecto"]["schema"], "midi-forge/1")

    def test_json_malformado_es_E101(self):
        with self.assertRaises(compilador.DirectorInvalido) as cm:
            compilador.compilar("{ esto no es json")
        self.assertIn("E101", [c for c, _m in cm.exception.resultado["errores"]])


class TestRegresionDocumental3Ejemplos(unittest.TestCase):
    """Los 3 JSON de rev. 3 (fuente única, extraídos del documento) revalidan
    con el validador REAL: 0 errores y los avisos EXACTOS documentados (§5.1–§5.3)."""

    def _ejemplo(self, titulo):
        return _ejemplos_rev3()[titulo]

    def _avisos(self, doc):
        return sorted(c for c, _m in validador.validar(doc)["avisos"])

    def test_H1_midnight_tape(self):
        doc = self._ejemplo("Midnight Tape")
        res = validador.validar(doc)
        self.assertEqual(res["errores"], [], msg=res["errores"])
        self.assertEqual(self._avisos(doc), ["W403", "W410", "W410", "W421"])

    def test_H2_iron_lung(self):
        doc = self._ejemplo("Iron Lung")
        res = validador.validar(doc)
        self.assertEqual(res["errores"], [], msg=res["errores"])
        self.assertEqual(self._avisos(doc), ["W403", "W414", "W414"])

    def test_H3_cold_harbor(self):
        doc = self._ejemplo("Cold Harbor")
        res = validador.validar(doc)
        self.assertEqual(res["errores"], [], msg=res["errores"])
        self.assertEqual(self._avisos(doc), ["W418"])
        # ADAPTADO (Fase 2, RESPUESTA 09): en Fase 1 W403 era no verificable
        # (sin receta doom_dark_jazz → no_verificados). Con la receta
        # registrada, W403 ES computable: d_efectiva = 0.2 + (d_secc − D_receta)
        # ≤ 0.17 en las 5 secciones → banda B1 → W403 no dispara y ya no hay
        # ningún no_verificado por W403.
        self.assertFalse(any("W403" in m for m in res["no_verificados"]),
                         msg=res["no_verificados"])
        self.assertFalse(any("W403" in c for c, _m in res["avisos"]))


if __name__ == "__main__":
    unittest.main()
