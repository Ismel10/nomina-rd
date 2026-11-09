"""Tests de nomina.engine.money: única fuente de redondeo del sistema (AGENTS.md §3.1).

Tolerancia cero: todas las comparaciones son `Decimal` exactos (sin approx, sin float).
"""

from decimal import ROUND_HALF_UP, Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from nomina.engine.money import CENT, ROUNDING_MODE, is_rounded, round_line, sum_lines, to_decimal

# --------------------------------------------------------------------------- constantes


def test_constantes_del_modulo() -> None:
    assert Decimal("0.01") == CENT
    assert ROUND_HALF_UP == ROUNDING_MODE


# --------------------------------------------------------------------------- to_decimal


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1234.50", Decimal("1234.50")),
        ("0.0287", Decimal("0.0287")),
        ("-15.75", Decimal("-15.75")),
        (30000, Decimal("30000")),
        (Decimal("99.99"), Decimal("99.99")),
    ],
)
def test_to_decimal_acepta_str_int_y_decimal(value: str | int | Decimal, expected: Decimal) -> None:
    result = to_decimal(value)
    assert isinstance(result, Decimal)
    assert result == expected


def test_to_decimal_conserva_la_escala_del_texto() -> None:
    # "1234.50" debe seguir teniendo 2 decimales: no se normaliza a "1234.5".
    assert to_decimal("1234.50").as_tuple().exponent == -2


@pytest.mark.parametrize(
    ("value", "raw"),
    [
        (0.1, "0.1"),
        (2.675, "2.675"),
        (True, "True"),
        (False, "False"),
    ],
)
def test_to_decimal_rechaza_float_y_bool_sin_exponer_el_valor(value: object, raw: str) -> None:
    with pytest.raises(TypeError) as excinfo:
        to_decimal(value)  # type: ignore[arg-type]
    assert raw not in str(excinfo.value)


@pytest.mark.parametrize("raw", ["NaN", "sNaN", "Infinity", "-Infinity", "abc", "", "1,234.50"])
def test_to_decimal_rechaza_no_finitos_y_texto_invalido_sin_exponer_el_valor(raw: str) -> None:
    with pytest.raises(ValueError, match=r".+") as excinfo:
        to_decimal(raw)
    message = str(excinfo.value)
    if raw:  # "" está contenido en cualquier texto; basta con que falle
        assert raw not in message


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_to_decimal_rechaza_decimal_no_finito(value: Decimal) -> None:
    with pytest.raises(ValueError, match=r".+"):
        to_decimal(value)


# --------------------------------------------------------------------------- round_line (a mano)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Medio centavo exacto: HALF_UP sube.
        ("0.005", "0.01"),
        # Por debajo de medio centavo: baja.
        ("0.004", "0.00"),
        # Con float, 2.675 es 2.67499999... y redondearía a 2.67. Con Decimal desde str es
        # exactamente 2.675 y HALF_UP da 2.68.
        ("2.675", "2.68"),
        # Completa a 2 decimales (escala fija), sin cambiar el valor.
        ("1234.5", "1234.50"),
        # Negativos: ROUND_HALF_UP redondea "alejándose de cero" en el empate, así que -0.005
        # va a -0.01 (no a 0.00). Es simétrico respecto de los positivos.
        ("-0.005", "-0.01"),
        ("-2.675", "-2.68"),
        ("-0.004", "0.00"),
    ],
)
def test_round_line_casos_calculados_a_mano(raw: str, expected: str) -> None:
    result = round_line(Decimal(raw))
    assert result == Decimal(expected)
    assert result.as_tuple().exponent == -2


def test_round_line_no_produce_cero_negativo() -> None:
    # Decimal.quantize daría "-0.00", que se vería así en un volante. Se normaliza a "0.00".
    result = round_line(Decimal("-0.004"))
    assert str(result) == "0.00"
    assert not result.is_signed()


def test_round_line_precision_intermedia_completa_y_redondeo_solo_al_final() -> None:
    """Hoja de cálculo manual (tasa FICTICIA, solo ilustra la mecánica):

    Base ................. 1000.00
    Tasa ................. 0.0287
    Producto exacto ...... 28.700000   (Decimal conserva 6 decimales; no se redondea aún)
    round_line ........... 28.70
    """
    product = Decimal("1000.00") * Decimal("0.0287")
    assert product == Decimal("28.700000")
    assert product.as_tuple().exponent == -6  # precisión completa en el intermedio
    assert round_line(product) == Decimal("28.70")


def test_round_line_redondear_intermedios_cambia_el_resultado() -> None:
    """Por qué se redondea una sola vez, al final de la línea.

    Exacto:              10.005 x 3 = 30.015  -> round_line -> 30.02  (correcto)
    Redondeo intermedio: round(10.005) = 10.01; 10.01 x 3 = 30.03     (1 centavo de más)
    """
    base = Decimal("10.005")
    assert round_line(base * 3) == Decimal("30.02")
    assert round_line(round_line(base) * 3) == Decimal("30.03")


def test_round_line_rechaza_float_sin_exponer_el_valor() -> None:
    with pytest.raises(TypeError) as excinfo:
        round_line(2.675)  # type: ignore[arg-type]
    assert "2.675" not in str(excinfo.value)


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity")])
def test_round_line_rechaza_no_finitos(value: Decimal) -> None:
    with pytest.raises(ValueError, match=r".+"):
        round_line(value)


# --------------------------------------------------------------------------- is_rounded


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10.00", True),
        ("-0.01", True),
        ("0.00", True),
        ("10.0", False),
        ("10", False),
        ("10.001", False),
        ("NaN", False),
        ("Infinity", False),
    ],
)
def test_is_rounded(raw: str, expected: bool) -> None:
    assert is_rounded(Decimal(raw)) is expected


# --------------------------------------------------------------------------- sum_lines


def test_sum_lines_suma_exacta_sin_redondear() -> None:
    lines = [Decimal("15000.00"), Decimal("-430.50"), Decimal("-456.00"), Decimal("0.01")]
    result = sum_lines(lines)
    assert result == Decimal("14113.51")
    assert result.as_tuple().exponent == -2


def test_sum_lines_vacio_es_cero_con_dos_decimales() -> None:
    result = sum_lines([])
    assert result == Decimal("0.00")
    assert is_rounded(result)


def test_sum_lines_acepta_un_generador() -> None:
    assert sum_lines(Decimal(f"{n}.00") for n in range(1, 4)) == Decimal("6.00")


@pytest.mark.parametrize("raw", ["10.005", "10.0", "10"])
def test_sum_lines_rechaza_montos_no_redondeados_sin_exponer_el_valor(raw: str) -> None:
    with pytest.raises(ValueError, match=r".+") as excinfo:
        sum_lines([Decimal("1.00"), Decimal(raw)])
    assert raw not in str(excinfo.value)


def test_sum_lines_rechaza_float() -> None:
    with pytest.raises(TypeError):
        sum_lines([Decimal("1.00"), 2.5])  # type: ignore[list-item]


# --------------------------------------------------------------------------- property-based

# Rango realista de una línea de nómina en DOP (±100 millones), con hasta 8 decimales en el
# intermedio (monto NUMERIC(14,2) x tasa NUMERIC(9,6)).
LIMIT = Decimal("100000000")
raw_amounts = st.decimals(
    min_value=-LIMIT, max_value=LIMIT, places=8, allow_nan=False, allow_infinity=False
)
rounded_amounts = st.decimals(
    min_value=-LIMIT, max_value=LIMIT, places=2, allow_nan=False, allow_infinity=False
).map(lambda d: d.quantize(Decimal("0.01")))


@given(raw_amounts)
def test_prop_round_line_siempre_tiene_exponente_menos_dos(x: Decimal) -> None:
    result = round_line(x)
    assert result.as_tuple().exponent == -2
    assert is_rounded(result)


@given(raw_amounts)
def test_prop_round_line_error_maximo_medio_centavo(x: Decimal) -> None:
    assert abs(round_line(x) - x) <= Decimal("0.005")


@given(raw_amounts)
def test_prop_round_line_es_idempotente(x: Decimal) -> None:
    once = round_line(x)
    assert round_line(once) == once


@given(st.lists(rounded_amounts, max_size=50))
def test_prop_sum_lines_es_la_suma_exacta_y_queda_redondeada(xs: list[Decimal]) -> None:
    result = sum_lines(xs)
    assert result == sum(xs, Decimal("0.00"))
    assert is_rounded(result)
