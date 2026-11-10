"""Guarda de arquitectura: solo engine/money.py puede redondear (AGENTS.md §3.1, ADR 0001).

Falla si cualquier otro archivo de `nomina.engine` usa `.quantize(`, el `round()` nativo o un
modo de redondeo `ROUND_*` (como nombre, como atributo `decimal.ROUND_*` o importado desde
`decimal`). Se analiza el AST, no el texto, para no confundir `round(` con `round_line(`.
"""

import ast
from pathlib import Path

import pytest

import nomina.engine

ENGINE_DIR = Path(nomina.engine.__file__).parent
ALLOWED = ENGINE_DIR / "money.py"
ENGINE_FILES = sorted(p for p in ENGINE_DIR.rglob("*.py") if p != ALLOWED)


def _rounding_uses(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        # round() nativo: llamada cuyo nombre es exactamente "round" (round_line no coincide).
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "round"
        ):
            found.append(f"L{node.lineno}: round(")
        elif isinstance(node, ast.Attribute) and node.attr == "quantize":
            found.append(f"L{node.lineno}: .quantize(")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("ROUND_"):
            found.append(f"L{node.lineno}: {node.attr}")
        elif isinstance(node, ast.Name) and node.id.startswith("ROUND_"):
            found.append(f"L{node.lineno}: {node.id}")
        elif isinstance(node, ast.ImportFrom):
            found.extend(
                f"L{node.lineno}: import {alias.name}"
                for alias in node.names
                if alias.name.startswith("ROUND_")
            )
    return found


def test_money_py_existe() -> None:
    assert ALLOWED.is_file(), "no se encontró engine/money.py"


@pytest.mark.parametrize("path", ENGINE_FILES, ids=lambda p: p.name)
def test_solo_money_py_redondea(path: Path) -> None:
    uses = _rounding_uses(ast.parse(path.read_text(encoding="utf-8")))
    assert not uses, (
        f"{path.relative_to(ENGINE_DIR)} redondea por su cuenta ({', '.join(uses)}): "
        "usar engine.money.round_line"
    )
