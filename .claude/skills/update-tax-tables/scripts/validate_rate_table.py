"""Valida un archivo JSON de tabla de tasas con vigencia.

Uso:
    python validate_rate_table.py <nueva.json> [<anterior.json>]

Solo biblioteca estándar. Sale con código 1 si hay errores.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

CENT = Decimal("0.01")


def _dec(value: Any, where: str, errors: list[str]) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{where}: debe ser string decimal, no {type(value).__name__} ({value!r})")
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        errors.append(f"{where}: decimal inválido {value!r}")
        return None


def _date(value: Any, where: str, errors: list[str]) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        errors.append(f"{where}: fecha ISO inválida {value!r}")
        return None


def validate(data: dict[str, Any], previous: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    for key in ("table_code", "version", "valid_from", "source"):
        if not data.get(key):
            errors.append(f"falta campo obligatorio '{key}'")

    valid_from = _date(data.get("valid_from"), "valid_from", errors)
    valid_to = _date(data.get("valid_to"), "valid_to", errors)
    if valid_from and valid_to and valid_to < valid_from:
        errors.append("valid_to es anterior a valid_from")
    if "TODO(verificar-normativa)" in str(data.get("source", "")):
        errors.append("source contiene TODO(verificar-normativa): falta la fuente oficial")

    for name, raw in (data.get("rates") or {}).items():
        rate = _dec(raw, f"rates.{name}", errors)
        if rate is not None and not (Decimal(0) <= rate <= Decimal(1)):
            errors.append(f"rates.{name}: tasa fuera de [0, 1]: {rate}")

    brackets = data.get("brackets") or []
    prev_upper: Decimal | None = None
    for i, b in enumerate(brackets):
        where = f"brackets[{i}]"
        lower = _dec(b.get("lower"), f"{where}.lower", errors)
        upper = _dec(b.get("upper"), f"{where}.upper", errors)
        rate = _dec(b.get("rate"), f"{where}.rate", errors)
        _dec(b.get("fixed", "0"), f"{where}.fixed", errors)
        if rate is not None and not (Decimal(0) <= rate <= Decimal(1)):
            errors.append(f"{where}.rate fuera de [0, 1]: {rate}")
        if lower is not None and upper is not None and upper <= lower:
            errors.append(f"{where}: upper <= lower")
        if upper is None and i != len(brackets) - 1:
            errors.append(f"{where}: solo el último tramo puede tener upper=null")
        if i == 0 and lower is not None and lower != 0:
            errors.append(f"{where}: el primer tramo debe empezar en 0")
        if prev_upper is not None and lower is not None and lower != prev_upper + CENT:
            errors.append(
                f"{where}: tramo no contiguo (lower={lower}, se esperaba {prev_upper + CENT})"
            )
        prev_upper = upper

    if previous is not None:
        if previous.get("table_code") != data.get("table_code"):
            errors.append("table_code distinto al de la versión anterior")
        prev_from = _date(previous.get("valid_from"), "anterior.valid_from", errors)
        if prev_from and valid_from and valid_from <= prev_from:
            errors.append("valid_from debe ser posterior al valid_from de la versión anterior")
        if previous.get("version") == data.get("version"):
            errors.append("la versión nueva repite el identificador de la anterior")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    previous = json.loads(Path(argv[2]).read_text(encoding="utf-8")) if len(argv) == 3 else None
    errors = validate(data, previous)
    if errors:
        print("ERRORES:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
