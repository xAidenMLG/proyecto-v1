#!/usr/bin/env python3
"""Manifiesto SHA256 de archivos protegidos y de todo el arbol de trabajo.

Uso:
    python manifests/hash_protected.py write   -> escribe manifests/protegidos.json
    python manifests/hash_protected.py verify  -> verifica contra el manifiesto y sale 0/1
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Componentes protegidos por la mision (no modificar; vigilar integridad)
PROTEGIDOS = [
    "forge/__init__.py",
    "forge/theory.py",
    "forge/voicing.py",
    "forge/midiwriter.py",
    "forge/engine.py",
    "forge/styles.py",
    "forge/adapter.py",
    "forge/validate.py",
    "forge/audio.py",
    "dark_director/identities/dark_triphop.py",
    "dark_director/contract.py",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_manifest() -> dict:
    files = {}
    for rel in PROTEGIDOS:
        p = ROOT / rel
        if p.exists():
            files[rel] = sha256(p)
        else:
            files[rel] = None
    return {"protegidos": files}


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    mpath = ROOT / "manifests" / "protegidos.json"
    if cmd == "write":
        man = build_manifest()
        mpath.write_text(json.dumps(man, indent=2, sort_keys=True), encoding="utf-8")
        print(f"manifiesto escrito: {mpath}")
        for k, v in man["protegidos"].items():
            print(f"  {v}  {k}" if v else f"  AUSENTE  {k}")
        return 0
    if cmd == "verify":
        if not mpath.exists():
            print("no hay manifiesto previo")
            return 2
        man = json.loads(mpath.read_text(encoding="utf-8"))
        ok = True
        for rel, expected in man["protegidos"].items():
            p = ROOT / rel
            if expected is None:
                state = "AUSENTE (esperado)" if not p.exists() else "ERROR: aparecio"
                if p.exists():
                    ok = False
                print(f"  {state}  {rel}")
                continue
            actual = sha256(p) if p.exists() else None
            if actual == expected:
                print(f"  OK  {rel}")
            else:
                ok = False
                print(f"  MODIFICADO  {rel}")
        print("VERIFICACION:", "OK" if ok else "FALLO")
        return 0 if ok else 1
    print("uso: write|verify")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
