"""Ejemplo de property-based tests para el redondeo de montos.

Copiar a backend/tests/unit/engine/test_properties_money.py cuando exista engine/money.py.
"""

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

# from nomina.engine.money import round_line

amounts = st.decimals(
    min_value=Decimal("-1000000000"),
    max_value=Decimal("1000000000"),
    places=6,
    allow_nan=False,
    allow_infinity=False,
)


@given(amounts)
def test_round_line_tiene_dos_decimales(x: Decimal) -> None:
    r = round_line(x)  # type: ignore[name-defined]  # noqa: F821
    assert r.as_tuple().exponent == -2


@given(amounts)
def test_round_line_error_maximo_medio_centavo(x: Decimal) -> None:
    r = round_line(x)  # type: ignore[name-defined]  # noqa: F821
    assert abs(r - x) <= Decimal("0.005")


@given(amounts)
def test_round_line_es_idempotente(x: Decimal) -> None:
    r = round_line(x)  # type: ignore[name-defined]  # noqa: F821
    assert round_line(r) == r  # type: ignore[name-defined]  # noqa: F821
