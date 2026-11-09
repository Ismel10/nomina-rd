"""Revisión heurística de una migración Alembic.

Uso:
    python check_migration.py <ruta_migracion.py> [...]

Solo biblioteca estándar. No reemplaza la revisión humana: señala lo que hay que mirar.
Sale con código 1 si encuentra advertencias.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

GLOBAL_TABLES = {"company", "concept", "rate_table", "rate_table_version", "audit_log"}
DESTRUCTIVE = {"drop_table", "drop_column", "drop_constraint", "drop_index", "execute"}
FLOAT_TYPES = {"Float", "REAL", "DOUBLE_PRECISION", "Double"}


def _call_name(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def _first_str(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    return None


def check(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    warnings: list[str] = []
    upgrade = next(
        (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade"), None
    )
    downgrade = next(
        (n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "downgrade"), None
    )
    if downgrade is None or all(isinstance(s, ast.Pass) for s in downgrade.body):
        warnings.append("downgrade() vacío: implementarlo o lanzar NotImplementedError('irreversible: …')")

    for node in ast.walk(upgrade or tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        line = getattr(node, "lineno", "?")
        if name in DESTRUCTIVE:
            label = "SQL crudo" if name == "execute" else "operación destructiva"
            warnings.append(f"L{line}: {label} `{name}`: justificar y verificar que no pierde datos")
        if name in FLOAT_TYPES:
            warnings.append(f"L{line}: tipo `{name}`: usar Numeric(14, 2) para montos")
        if name == "create_table":
            table = _first_str(node) or "?"
            cols = [
                _first_str(a)
                for a in node.args[1:]
                if isinstance(a, ast.Call) and _call_name(a) == "Column"
            ]
            if table not in GLOBAL_TABLES and "company_id" not in cols:
                warnings.append(f"L{line}: create_table('{table}') sin company_id")
        if name == "create_index":
            cols_node = node.args[2] if len(node.args) > 2 else None
            if isinstance(cols_node, ast.List) and cols_node.elts:
                first = cols_node.elts[0]
                if isinstance(first, ast.Constant) and first.value != "company_id":
                    warnings.append(
                        f"L{line}: índice que no empieza por company_id ({first.value!r}): "
                        "confirmar que la tabla es global"
                    )
        if name == "alter_column":
            kws = {k.arg for k in node.keywords}
            if "type_" in kws:
                warnings.append(f"L{line}: alter_column con type_: preferir expand/contract")
            if "new_column_name" in kws:
                warnings.append(f"L{line}: renombre de columna: rompe el código desplegado; usar expand/contract")
    return warnings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    total = 0
    for p in argv[1:]:
        ws = check(Path(p))
        total += len(ws)
        print(f"{p}: {'OK' if not ws else f'{len(ws)} advertencia(s)'}")
        for w in ws:
            print(f"  - {w}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
