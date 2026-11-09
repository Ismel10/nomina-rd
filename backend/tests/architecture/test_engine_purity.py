"""Guardas de arquitectura: el motor de cálculo es puro y no usa float (AGENTS.md §3 y §4)."""

import ast
from pathlib import Path

import pytest

import nomina.engine

ENGINE_DIR = Path(nomina.engine.__file__).parent
ENGINE_FILES = sorted(ENGINE_DIR.rglob("*.py"))

ALLOWED_STDLIB = {
    "__future__",
    "dataclasses",
    "datetime",
    "decimal",
    "enum",
    "functools",
    "itertools",
    "collections",
    "typing",
    "abc",
}


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module)
    return roots


def test_hay_archivos_del_motor() -> None:
    assert ENGINE_FILES, "no se encontró el paquete nomina.engine"


@pytest.mark.parametrize("path", ENGINE_FILES, ids=lambda p: p.name)
def test_motor_solo_importa_stdlib_permitida(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for module in _imported_roots(tree):
        top = module.split(".")[0]
        ok = top in ALLOWED_STDLIB or module.startswith("nomina.engine")
        assert ok, f"{path.name} importa '{module}': el motor debe ser puro (sin I/O ni frameworks)"


@pytest.mark.parametrize("path", ENGINE_FILES, ids=lambda p: p.name)
def test_motor_no_usa_float(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            pytest.fail(f"{path.name}:{node.lineno} literal float {node.value!r}: usar Decimal")
        if isinstance(node, ast.Name) and node.id == "float":
            pytest.fail(f"{path.name}:{node.lineno} uso de 'float': usar Decimal")
