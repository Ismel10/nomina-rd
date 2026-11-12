"""Forma del periodo y prorrateo del salario fijo (ADR 0002).

Funciones puras. El prorrateo devuelve el monto a **precisión completa**: el redondeo se hace una
sola vez en la línea del salario, dentro de `calculate` (ADR 0001).

- `CALENDAR_FRACTION`: salario del periodo x días calendario de servicio ÷ días calendario del
  periodo.
- `COMMERCIAL_30`: mes de 30 días y quincenas de 15. Cada fecha tiene un índice comercial igual a
  su día del mes, salvo el último día del mes y el día 31, que valen 30. Los días de servicio son
  `índice(último día) - índice(primer día) + 1`.
"""

from datetime import date, timedelta
from decimal import Decimal

from nomina.engine.errors import PayrollInputError
from nomina.engine.models import ContractInput, PayFrequency, PayPeriod, ProrationMethod

_COMMERCIAL_MONTH = 30
_COMMERCIAL_FORTNIGHT = 15


def _last_day_of_month(day: date) -> date:
    first_of_next = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first_of_next - timedelta(days=1)


def validate_period_shape(period: PayPeriod) -> None:
    """Exige periodos estándar: quincenal 1-15 o 16-último día del mes; mensual 1-último día.

    `COMMERCIAL_30` necesita periodos de 15 o 30 días comerciales, y un periodo con otra forma
    suele ser un error de carga.

    Raises:
        PayrollInputError: si el periodo no tiene una forma estándar.
    """
    start, end = period.start, period.end
    last = _last_day_of_month(start)
    same_month = (start.year, start.month) == (end.year, end.month)
    if period.frequency is PayFrequency.MONTHLY:
        valid = same_month and start.day == 1 and end == last
    else:
        first_half = start.day == 1 and end.day == _COMMERCIAL_FORTNIGHT
        second_half = start.day == _COMMERCIAL_FORTNIGHT + 1 and end == last
        valid = same_month and (first_half or second_half)
    if not valid:
        raise PayrollInputError(
            f"PayPeriod {start}..{end}: forma inválida para {period.frequency.value} "
            "(quincenal 1-15 o 16-fin de mes; mensual 1-fin de mes)"
        )


def _commercial_index(day: date) -> int:
    if day == _last_day_of_month(day):
        return _COMMERCIAL_MONTH
    return min(day.day, _COMMERCIAL_MONTH)


def period_days(period: PayPeriod, method: ProrationMethod) -> int:
    """Días del periodo según el método: calendario, o 30 (mensual) / 15 (quincenal)."""
    validate_period_shape(period)
    if method is ProrationMethod.CALENDAR_FRACTION:
        return (period.end - period.start).days + 1
    if period.frequency is PayFrequency.MONTHLY:
        return _COMMERCIAL_MONTH
    return _COMMERCIAL_FORTNIGHT


def service_days(period: PayPeriod, contract: ContractInput, method: ProrationMethod) -> int:
    """Días con contrato vigente dentro del periodo, contados según el método. 0 si el contrato
    no se superpone con el periodo."""
    validate_period_shape(period)
    first = max(period.start, contract.start_date)
    last = period.end if contract.end_date is None else min(period.end, contract.end_date)
    if last < first:
        return 0
    if method is ProrationMethod.CALENDAR_FRACTION:
        return (last - first).days + 1
    return _commercial_index(last) - _commercial_index(first) + 1


def period_salary(period: PayPeriod, contract: ContractInput) -> Decimal:
    """Salario del periodo completo: el mensual, o el mensual ÷ 2 en quincenal."""
    if period.frequency is PayFrequency.MONTHLY:
        return contract.monthly_salary
    return contract.monthly_salary / 2


def prorated_salary(period: PayPeriod, contract: ContractInput, method: ProrationMethod) -> Decimal:
    """Salario del periodo x días de servicio ÷ días del periodo, a precisión completa."""
    salary = period_salary(period, contract)
    return salary * service_days(period, contract, method) / period_days(period, method)
