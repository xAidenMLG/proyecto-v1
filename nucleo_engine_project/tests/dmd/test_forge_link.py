"""Alcances A/C/H de Fase 0 + instrucción 09: importación de MIDI Forge sin modificarlo.

Verifica (solo-lectura) que:
  - ``forge/`` se localiza e importa (8 módulos) sin escribir bytecode en su árbol;
  - la protección de importación es DE ÁMBITO: no altera permanentemente el
    comportamiento del intérprete (instrucción 09.1);
  - la copia auditada del sandbox solo es alcanzable en modo auditoría
    (``DARK_DIRECTOR_AUDIT_MODE=1``, instrucción 09.2);
  - el motor expone los símbolos que el contrato y la auditoría citan por nombre;
  - los perfiles de voicing y guardrails dark citados por el contrato existen;
  - ``app.run_generate`` sigue siendo el punto de orquestación único;
  - ``PRESETS`` no crece (el contrato no añade presets — decisión 1 de la auditoría).
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dark_director import contract, forge_link


def listar_forge(root):
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


class TestLocalizacionEImportacion(unittest.TestCase):
    def test_resolve_forge_root_devuelve_paquete_real(self):
        root = forge_link.resolve_forge_root()
        self.assertTrue((root / "__init__.py").is_file())
        self.assertEqual(root.name, "forge")

    def test_import_de_los_8_modulos(self):
        f = forge_link.import_forge()
        for name in forge_link.FORGE_MODULES:
            self.assertTrue(hasattr(f, name), msg=f"módulo forge.{name} ausente")

    def test_importacion_no_escribe_bytecode_en_forge(self):
        root = forge_link.resolve_forge_root()
        antes = listar_forge(root)
        forge_link.import_forge()
        forge_link.import_forge_app()
        despues = listar_forge(root)
        self.assertEqual(antes, despues,
                         msg="la importación creó/eliminó archivos dentro de forge/ (p. ej. .pyc nuevos)")

    def test_proteccion_bytecode_es_de_ambito_y_se_restaura(self):
        # instrucción 09.1: la protección de .pyc es de ÁMBITO (context manager),
        # nunca un estado permanente del intérprete como en Fase 0.
        import sys as _sys
        previo = _sys.dont_write_bytecode
        with forge_link.sin_bytecode():
            self.assertTrue(_sys.dont_write_bytecode)
        self.assertEqual(_sys.dont_write_bytecode, previo,
                         msg="sin_bytecode debe restaurar el estado previo del intérprete")
        # importar forge no deja el flag permanente:
        forge_link.import_forge()
        forge_link.import_forge_app()
        self.assertEqual(_sys.dont_write_bytecode, previo,
                         msg="import_forge no debe alterar permanentemente el intérprete (09.1)")

    def test_importacion_no_deja_estado_global_permanente(self):
        # doble import (cacheada) tampoco altera el intérprete
        import sys as _sys
        previo = _sys.dont_write_bytecode
        forge_link.import_forge()
        forge_link.import_forge()
        self.assertEqual(_sys.dont_write_bytecode, previo)


class TestRutaDeAuditoriaSoloHerramienta(unittest.TestCase):
    """Instrucción 09.2: el sandbox es exclusivamente herramienta de auditoría."""

    def test_modo_auditoria_activado_en_tests(self):
        # la suite vive fuera del proyecto MIDI Forge: usa la copia auditada
        # SOLO porque los tests la activan explícitamente
        self.assertEqual(os.environ.get(forge_link.VAR_MODO_AUDITORIA), "1")
        self.assertTrue(forge_link.en_modo_auditoria())

    def test_sin_modo_auditoria_el_sandbox_es_inalcanzable(self):
        # FASE 5 (adaptado): en el layout FINAL dark_director/ y forge/ son
        # hermanos, así que resolve_forge_root() SIEMPRE encuentra el motor sin
        # modo auditoría. La garantía real es que el sandbox auditado jamás se
        # resuelve sin DARK_DIRECTOR_AUDIT_MODE=1: se verifica apuntando el env
        # a una ruta inexistente (producción degradada) y comprobando que el
        # resultado sigue siendo el forge hermano (nunca la copia auditada).
        import dark_director.forge_link as fl
        previo = os.environ.pop(fl.VAR_MODO_AUDITORIA, None)
        try:
            self.assertFalse(fl.en_modo_auditoria())
            root_env = os.environ.pop("DARK_DIRECTOR_FORGE_ROOT", None)
            try:
                resuelto = fl.resolve_forge_root()
                self.assertEqual(resuelto, fl.Path(__file__).resolve().parent.parent.parent / "forge")
            finally:
                if root_env is not None:
                    os.environ["DARK_DIRECTOR_FORGE_ROOT"] = root_env
        finally:
            if previo is not None:
                os.environ[fl.VAR_MODO_AUDITORIA] = previo


class TestCapacidadesCitadas(unittest.TestCase):
    def test_todos_los_simbolos_citados_existen(self):
        informe = forge_link.verify_forge_capabilities()
        faltantes = []
        for mod_name, symbols in forge_link.REQUIRED_SYMBOLS.items():
            for sym, ok in informe[mod_name].items():
                if not ok:
                    faltantes.append(f"{mod_name}.{sym}")
        self.assertEqual(faltantes, [], msg=f"símbolos citados por el contrato ausentes: {faltantes}")

    def test_perfiles_de_voicing_del_contrato(self):
        informe = forge_link.verify_forge_capabilities()
        faltantes = [p for p, ok in informe["voicing.perfiles_contrato"].items() if not ok]
        self.assertEqual(faltantes, [], msg=f"perfiles citados por §2.6.5/§2.6.6 ausentes: {faltantes}")

    def test_guardrails_dark_en_validate(self):
        informe = forge_link.verify_forge_capabilities()
        faltantes = [g for g, ok in informe["validate.guardrails_en_fuente"].items() if not ok]
        self.assertEqual(faltantes, [], msg=f"guardrails citados ausentes en validate.py: {faltantes}")

    def test_presets_sin_crecer(self):
        informe = forge_link.verify_forge_capabilities()
        self.assertEqual(informe["presets_existentes"], ("synthwave", "triphop"))

    def test_run_generate_es_punto_de_orquestacion(self):
        informe = forge_link.verify_forge_capabilities()
        self.assertTrue(informe["app.run_generate"])
        import inspect
        app = forge_link.import_forge_app()
        sig = inspect.signature(app.run_generate)
        self.assertEqual(list(sig.parameters), ["project", "preset"])

    def test_defaults_de_rol_cubren_register_y_mix_del_contrato(self):
        # §2.5.1: register y mix (volume/pan/reverb/chorus) salen de styles.ROLE_DEFAULTS.
        # OBSERVACIÓN documentada: el motor expone el registro como clave `range`.
        f = forge_link.import_forge()
        for rol, d in f.styles.ROLE_DEFAULTS.items():
            for clave in ("volume", "pan", "reverb", "chorus", "range"):
                self.assertIn(clave, d, msg=f"ROLE_DEFAULTS[{rol}] sin clave {clave}")
            self.assertIn(rol, f.styles.ROLE_VEL_OFFSET, msg=f"ROLE_VEL_OFFSET sin rol {rol}")

    def test_roles_del_motor_cubren_los_roles_del_contrato(self):
        # contrato §2.5: lead, keys, mallet, bass, drums, pad, strings (+ piano = rol keys)
        f = forge_link.import_forge()
        roles_motor = set(f.styles.ROLES)
        for rol in ("lead", "keys", "mallet", "bass", "drums", "pad", "strings"):
            self.assertIn(rol, roles_motor)


if __name__ == "__main__":
    unittest.main()
