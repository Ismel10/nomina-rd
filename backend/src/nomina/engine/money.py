"""Utilidades de dinero del motor de nómina: única fuente de redondeo del sistema.

Por qué existe este módulo (AGENTS.md §3.1):

- **Nunca `float`.** Un float no puede representar exactamente valores como 0.1 o 2.675, y los
  errores se acumulan en sumas de muchas líneas. Todo monto es `decimal.Decimal` construido desde
  `str` o `int`.
- **Precisión completa en los pasos intermedios.** Base x tasa, prorrateos, etc. se calculan sin
  redondear (`Decimal` conserva todos los decimales del producto). Redondear antes de terminar la
  línea introduce errores de un centavo que luego no cuadran contra un cálculo hecho a mano.
- **Redondeo una sola vez, por línea de concepto,** con `round_line`. Ningún otro módulo redondea
  por su cuenta: así el criterio está en un único lugar y se puede cambiar o auditar.
- **Los totales son la suma de líneas ya redondeadas** (`sum_lines`), nunca se redondean aparte;
  así el volante siempre cuadra: la suma de lo que se imprime es igual al total impreso.

Los mensajes de error **nunca incluyen el monto** (dato sensible, AGENTS.md §3.6).

TODO(verificar-normativa): confirmar el criterio de redondeo de DGII y TSS (modo HALF_UP a 2
decimales y si se aplica por línea o sobre la base). No cambiar el criterio sin esa confirmación.
"""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Final

CENT: Final = Decimal("0.01")
"""Unidad mínima de la moneda (centavo de DOP). Todo monto final tiene exactamente 2 decimales."""

ROUNDING_MODE: Final = ROUND_HALF_UP
"""Modo de redondeo de las líneas. En el empate (medio centavo exacto) se aleja de cero:
0.005 -> 0.01 y -0.005 -> -0.01. TODO(verificar-normativa): confirmar con DGII/TSS."""

_ZERO: Final = Decimal("0.00")


def to_decimal(value: str | int | Decimal) -> Decimal:
    """Convierte una entrada externa (texto de la API o BD, entero o Decimal) a `Decimal` finito.

    Se rechaza `float` porque el valor ya llegó con error de representación: convertirlo
    "arreglaría" en apariencia un dato que no es exacto. Se rechaza `bool` porque en Python es
    subclase de `int` y `True` se colaría como 1. El texto conserva su escala ("1234.50" sigue
    teniendo 2 decimales).

    Raises:
        TypeError: si `value` es `float`, `bool` o cualquier tipo no soportado.
        ValueError: si el valor es NaN, infinito o un texto que no es un número decimal.
    """
    # bool va antes que int porque isinstance(True, int) es True.
    if isinstance(value, bool) or not isinstance(value, str | int | Decimal):
        raise TypeError(
            f"to_decimal: tipo no soportado ({type(value).__name__}); usar str, int o Decimal"
        )
    if isinstance(value, Decimal):
        result = value
    else:
        try:
            result = Decimal(value)
        except InvalidOperation:
            # `from None`: no encadenar la excepción original para no arrastrar la entrada.
            raise ValueError("to_decimal: el texto no es un número decimal válido") from None
    if not result.is_finite():
        raise ValueError("to_decimal: el valor debe ser un número finito")
    return result


def round_line(amount: Decimal) -> Decimal:
    """Redondea el monto de **una línea de concepto** a centavos con `ROUNDING_MODE`.

    Es la única función de redondeo del sistema. Se aplica una sola vez, al final del cálculo de
    cada línea; los intermedios deben llegar aquí con su precisión completa. El resultado siempre
    tiene exponente -2 ("1234.5" -> "1234.50") y nunca es un cero negativo ("-0.00"), para que
    los volantes y archivos no muestren "-0.00".

    Raises:
        TypeError: si `amount` no es `Decimal` (p. ej. un float).
        ValueError: si `amount` es NaN o infinito.
    """
    if not isinstance(amount, Decimal):
        raise TypeError(
            f"round_line: se esperaba Decimal, no {type(amount).__name__}; usar to_decimal"
        )
    if not amount.is_finite():
        raise ValueError("round_line: el monto debe ser un número finito")
    rounded = amount.quantize(CENT, rounding=ROUNDING_MODE)
    return _ZERO if rounded.is_zero() else rounded


def is_rounded(amount: Decimal) -> bool:
    """Indica si `amount` ya está a centavos: finito y con exactamente 2 decimales.

    "10.00" sí; "10.0", "10" y "10.001" no. Se exige la escala exacta (no solo el valor) porque
    eso es lo que garantiza `round_line`, y lo que permite detectar montos que se saltaron el
    redondeo de línea.
    """
    return (
        isinstance(amount, Decimal)
        and amount.is_finite()
        and amount.as_tuple().exponent == CENT.as_tuple().exponent
    )


def sum_lines(amounts: Iterable[Decimal]) -> Decimal:
    """Suma montos de líneas **ya redondeadas**, sin volver a redondear.

    Un total nunca se redondea por separado: es la suma exacta de lo que se imprime en cada línea,
    para que el volante cuadre al centavo. Si llega un monto sin redondear, es un error de
    programación (una línea se saltó `round_line`) y se rechaza en vez de corregirlo en silencio.
    El total de una lista vacía es "0.00".

    Raises:
        TypeError: si algún elemento no es `Decimal`.
        ValueError: si algún monto no tiene exactamente 2 decimales (se indica su posición, no
            su valor).
    """
    total = _ZERO
    for index, amount in enumerate(amounts):
        if not isinstance(amount, Decimal):
            raise TypeError(
                f"sum_lines: el elemento en la posición {index} no es Decimal "
                f"({type(amount).__name__})"
            )
        if not is_rounded(amount):
            raise ValueError(
                f"sum_lines: el monto en la posición {index} no está redondeado a 2 decimales; "
                "aplicar round_line a la línea antes de sumar"
            )
        total += amount
    return total
