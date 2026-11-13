#!/usr/bin/env python3
"""Verificación de integridad de las REFERENCIAS DORADAS (FASE 5, congeladas en FASE 6).

Uso:
    python3 manifests/verificar_golden.py            # verificar contra el manifiesto
    python3 manifests/verificar_golden.py --rebuild  # regenerar el manifiesto (solo si
                                                     # se congelan NUEVAS referencias)
El manifiesto (`manifests/golden_fase5.json`) guarda SHA256 de cada archivo de
`output/fase5_comparativos/`. Cualquier diferencia = la referencia fue alterada.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / 'output' / 'fase5_comparativos'
MANIFEST = ROOT / 'manifests' / 'golden_fase5.json'


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    files = sorted(p for p in DIR.rglob('*') if p.is_file())
    man = {
        "descripcion": "Referencias doradas FASE 5 (Nocturno Terminal, 8 escenarios "
                       "aprobados por el usuario). INMUTABLES.",
        "directorio": "output/fase5_comparativos",
        "archivos": {str(p.relative_to(DIR)): _sha(p) for p in files},
    }
    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print("manifiesto regenerado: %s (%d archivos)" % (MANIFEST, len(files)))


def verify():
    man = json.loads(MANIFEST.read_text(encoding='utf-8'))
    ok = True
    n = 0
    for rel, want in sorted(man['archivos'].items()):
        p = DIR / rel
        if not p.is_file():
            print("  FALTA  %s" % rel)
            ok = False
            continue
        n += 1
        got = _sha(p)
        if got != want:
            print("  CAMBIADO %s\n    esperado %s\n    actual   %s" % (rel, want, got))
            ok = False
    extra = [str(p.relative_to(DIR)) for p in DIR.rglob('*') if p.is_file()
             and str(p.relative_to(DIR)) not in man['archivos']]
    for e in extra:
        print("  NUEVO (no congelado)  %s" % e)
    print("VERIFICACION GOLDEN: %s (%d archivos congelados verificados)"
          % ("OK" if ok else "FALLOS", n))
    return 0 if ok else 1


if __name__ == '__main__':
    if '--rebuild' in sys.argv:
        build()
    else:
        sys.exit(verify())
