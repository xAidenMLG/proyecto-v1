"""Runner de generación de DMD STUDIO — proceso hijo aislado.

Ejecuta el MISMO núcleo que el CLI (``scripts/produce.py::producir_cancion``)
en un proceso separado: la interfaz nunca bloquea y un fallo del pipeline no
derriba el servidor. No duplica ninguna lógica musical.

Uso:
    python -m studio.runner --spec <ruta_del_spec.json>

Spec (escrito por el padre):
    {doc, production, seed, harmony, out_dir, wav, soundfont, fluidsynth, indice}

Progreso por stdout (líneas "## <paso>"); resultado final en
``<out_dir>/../_result.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_produce_module():
    """Importa ``scripts/produce.py`` como módulo (no hay paquete scripts)."""
    p = ROOT / "scripts" / "produce.py"
    spec = importlib.util.spec_from_file_location("produce", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["produce"] = mod
    spec.loader.exec_module(mod)
    return mod


def step(msg: str) -> None:
    print(f"## {msg}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    out_dir = Path(spec["out_dir"])
    result_path = out_dir.parent / "_result.json"

    def finish(res: dict) -> int:
        result_path.write_text(json.dumps(res, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print("## RESULT " + ("OK" if res.get("ok") else "ERROR"), flush=True)
        return 0 if res.get("ok") else 1

    try:
        produce = _load_produce_module()
        step("Importando motores (dark_director + jazz_engine + forge)")
        doc = spec["doc"]
        production = spec.get("production") or "full"
        seed = spec.get("seed")
        seed = int(seed) if seed is not None else None
        harmony = spec.get("harmony") or None

        step(f"Compilando documento y renderizando (perfil={production}, seed={seed if seed is not None else 'global.seed'})")
        r = produce.producir_cancion(
            doc, production=production, seed=seed, harmony=harmony,
            out_dir=str(out_dir), indice=bool(spec.get("indice", False)))
        if not r.get("ok"):
            return finish({"ok": False, "error": r.get("error", "producción fallida")})

        res = {"ok": True, "produccion": r}

        # ---- WAV (opcional; requiere fluidsynth + soundfont en el sistema) --
        if spec.get("wav"):
            sf = spec.get("soundfont") or None
            try:
                from forge import audio as fa
                step("Renderizando WAV con FluidSynth")
                midi_path = Path(r["midi"])
                wav_bytes = fa.render_wav(midi_path.read_bytes(), soundfont=sf)
                wav_path = out_dir / (out_dir.name + ".wav")
                wav_path.write_bytes(wav_bytes)
                res["wav"] = {"path": str(wav_path),
                              "sha256": hashlib.sha256(wav_bytes).hexdigest(),
                              "bytes": len(wav_bytes)}
            except Exception as e:  # el MIDI ya está generado: el WAV es opcional
                res["wav"] = {"error": f"{type(e).__name__}: {e}"}
                step(f"WAV no disponible: {e}")

        step("Generación completada")
        return finish(res)
    except Exception as e:
        tb = traceback.format_exc(limit=12)
        print(tb, file=sys.stderr, flush=True)
        try:
            return finish({"ok": False,
                           "error": f"{type(e).__name__}: {e}",
                           "traceback": tb})
        except Exception:
            print("## RESULT ERROR", flush=True)
            return 1


if __name__ == "__main__":
    sys.exit(main())
