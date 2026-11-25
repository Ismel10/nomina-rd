"""Cálculo de la nómina de un contrato en un periodo: `calculate(inputs, tables, policy)`.

Función pura y determinista (AGENTS.md §4). Salario fijo (`FIXED_SALARY`) con prorrateo (ADR
0002 y 0003), ausencias resueltas en cascada, licencias del art. 54 y validaciones.

Orden:
1. Vigencia de la política y de las tablas en la fecha de pago; `validate_policy`; forma del
   periodo; salario mensual no menor que el mínimo mensual de la categoría.
2. Días calendario con contrato vigente. Sin días: sin líneas (o error si hay novedades o
   `working_days`).
3. Ausencias: no pueden sumar más días que los días calendario con contrato (todos los tipos).
4. `ORDINARY_SALARY` con el método del contrato o, si no tiene, el de la política:
   `CALENDAR_FRACTION` / `COMMERCIAL_30` (ADR 0002); `WORKING_DAYS` (periodo completo = salario del
   periodo; parcial = salario diario x `working_days`) y `NO_PRORATION` (ADR 0003). Después, una
   línea por ausencia (art. 54: días legales por ley al 100 % y exceso por cascada). Cada línea se
   redondea una sola vez con `round_line` (ADR 0001).
5. Si el descuento por ausencias supera el salario ordinario, `ABSENCE_DISCOUNT_CAP` lo devuelve
   hasta dejar el bruto en 0.00 (regla del sistema).
"""

from decimal import Decimal

from nomina.engine.errors import PayrollConfigError, PayrollInputError, PayrollUnsupportedError
from nomina.engine.models import (
    Absence,
    ConceptKind,
    LeaveCategory,
    PayrollInput,
    PayrollLine,
    PayrollPolicy,
    PayrollResult,
    ProrationMethod,
    RateTables,
    RuleSource,
)
from nomina.engine.money import round_line, sum_lines
from nomina.engine.proration import (
    is_full_period,
    period_salary,
    prorated_salary,
    service_days,
    validate_period_shape,
)
from nomina.engine.rules import resolve_absence_ratio, resolve_proration_method, validate_policy

ORDINARY_SALARY = "ORDINARY_SALARY"
ABSENCE_DISCOUNT_CAP = "ABSENCE_DISCOUNT_CAP"
_FULL_PAY = Decimal("1")


def calculate(inputs: PayrollInput, tables: RateTables, policy: PayrollPolicy) -> PayrollResult:
    """Calcula las líneas del volante de un contrato `FIXED_SALARY` en un periodo.

    Raises:
        PayrollConfigError: política o tablas no vigentes en la fecha de pago, política inválida
            contra las tablas, o sin regla para un tipo de ausencia.
        PayrollInputError: forma de periodo inválida, salario menor que el mínimo, novedades sin
            días de servicio, o más días de ausencia que días con contrato.
        PayrollUnsupportedError: licencia cubierta por subsidio (fuera del MVP).
    """
    period, contract = inputs.period, inputs.contract
    _validate(inputs, tables, policy)

    calendar_days = service_days(period, contract, ProrationMethod.CALENDAR_FRACTION)
    if calendar_days == 0:
        if inputs.absences or inputs.working_days is not None:
            raise PayrollInputError(
                f"{contract.contract_id}: hay novedades pero el contrato no tiene días "
                "en el periodo"
            )
        return PayrollResult(contract.contract_id, period, ())

    absence_days = sum((a.days for a in inputs.absences), Decimal(0))
    if absence_days > calendar_days:
        raise PayrollInputError(
            f"{contract.contract_id}: los días de ausencia superan los días con contrato vigente "
            "en el periodo"
        )

    daily_salary = contract.monthly_salary / policy.daily_salary_divisor
    salary = _ordinary_salary(inputs, policy, daily_salary, calendar_days, absence_days)

    absence_lines: list[PayrollLine] = []
    for absence in inputs.absences:
        absence_lines.extend(_absence_lines(absence, inputs, tables, policy, daily_salary))

    lines = [salary, *absence_lines]
    discount = sum_lines(line.amount for line in absence_lines)
    if salary.amount + discount < 0:
        lines.append(
            PayrollLine(
                code=ABSENCE_DISCOUNT_CAP,
                kind=ConceptKind.EARNING,
                quantity=None,
                base=-discount,  # descuento total sin topar
                rate=None,
                amount=-(salary.amount + discount),
                rule_source=RuleSource.SYSTEM,
                policy_version=policy.version,
                table_version=None,
            )
        )
    return PayrollResult(contract.contract_id, period, tuple(lines))


def _ordinary_salary(
    inputs: PayrollInput,
    policy: PayrollPolicy,
    daily_salary: Decimal,
    calendar_days: int,
    absence_days: Decimal,
) -> PayrollLine:
    """Línea `ORDINARY_SALARY` según el método resuelto (contrato → empresa; ADR 0002 y 0003)."""
    period, contract = inputs.period, inputs.contract
    resolved = resolve_proration_method(contract, policy)
    method = resolved.method
    full_salary = period_salary(period, contract)
    full = is_full_period(period, contract)
    uses_working_days = method is ProrationMethod.WORKING_DAYS and not full

    # Regla única (ADR 0003): working_days solo es válido con WORKING_DAYS en un periodo parcial.
    # En cualquier otro caso (otro método o periodo completo) el dato no se usaría, y un dato que
    # no se usa no se ignora en silencio. Un método nuevo queda cubierto automáticamente.
    if inputs.working_days is not None and not uses_working_days:
        raise PayrollInputError(
            f"{contract.contract_id}: working_days solo aplica con WORKING_DAYS en un periodo "
            f"parcial (método {method.name}, periodo {'completo' if full else 'parcial'})"
        )

    quantity: Decimal | None
    if method in (ProrationMethod.CALENDAR_FRACTION, ProrationMethod.COMMERCIAL_30):
        quantity = Decimal(service_days(period, contract, method))
        base, exact = full_salary, prorated_salary(period, contract, method)
    elif method is ProrationMethod.NO_PRORATION:
        if contract.end_date is not None and contract.end_date < period.end:
            raise PayrollUnsupportedError(
                f"{contract.contract_id}: salida a mitad de periodo con NO_PRORATION; regla "
                "pendiente de confirmar con la firma (#27, ADR 0003)"
            )
        quantity, base, exact = None, full_salary, full_salary
    elif full:  # WORKING_DAYS en periodo completo: salario del periodo
        quantity, base, exact = None, full_salary, full_salary
    else:  # WORKING_DAYS en periodo parcial: salario diario x días laborables
        days = _partial_working_days(inputs, calendar_days, absence_days)
        exact = daily_salary * days
        if exact > full_salary:
            raise PayrollInputError(
                f"{contract.contract_id}: los días laborables informados superan el salario "
                "del periodo"
            )
        quantity, base = days, daily_salary

    return PayrollLine(
        code=ORDINARY_SALARY,
        kind=ConceptKind.EARNING,
        quantity=quantity,
        base=base,
        rate=None,
        amount=round_line(exact),
        rule_source=resolved.source,
        policy_version=policy.version,
        table_version=None,
    )


def _partial_working_days(
    inputs: PayrollInput, calendar_days: int, absence_days: Decimal
) -> Decimal:
    """Valida `working_days` en un periodo parcial con `WORKING_DAYS` (ADR 0003)."""
    contract_id = inputs.contract.contract_id
    days = inputs.working_days
    if days is None:
        raise PayrollInputError(
            f"{contract_id}: falta working_days para un periodo parcial con WORKING_DAYS"
        )
    if days > calendar_days:
        raise PayrollInputError(
            f"{contract_id}: working_days supera los días calendario con contrato en el periodo"
        )
    if absence_days > days:
        raise PayrollInputError(f"{contract_id}: los días de ausencia superan working_days")
    return days


def _validate(inputs: PayrollInput, tables: RateTables, policy: PayrollPolicy) -> None:
    pay_date = inputs.period.pay_date
    if not policy.covers(pay_date):
        raise PayrollConfigError(f"la política {policy.version} no está vigente el {pay_date}")
    if not tables.covers(pay_date):
        raise PayrollConfigError(f"las tablas legales no están todas vigentes el {pay_date}")
    validate_policy(policy, tables)
    validate_period_shape(inputs.period)
    minimum = tables.minimum_wages.monthly_minimum(policy.minimum_wage_category)
    if minimum is not None and inputs.contract.monthly_salary < minimum:
        raise PayrollInputError(
            f"{inputs.contract.contract_id}: el salario mensual es menor que el mínimo de la "
            f"categoría '{policy.minimum_wage_category}' ({tables.minimum_wages.version})"
        )


def _absence_lines(
    absence: Absence,
    inputs: PayrollInput,
    tables: RateTables,
    policy: PayrollPolicy,
    daily_salary: Decimal,
) -> list[PayrollLine]:
    code = f"ABSENCE_{absence.absence_type}"
    legal = tables.legal_leaves.leave(absence.absence_type)
    if legal is not None and legal.category is LeaveCategory.SUBSIDIZED:
        raise PayrollUnsupportedError(
            f"la licencia '{absence.absence_type}' está cubierta por subsidio y no la "
            "soporta el MVP"
        )

    lines: list[PayrollLine] = []
    remaining = absence.days
    if legal is not None and legal.max_days is not None:
        legal_days = min(absence.days, legal.max_days)
        lines.append(
            _absence_line(
                code,
                legal_days,
                daily_salary,
                _FULL_PAY,
                RuleSource.LAW,
                policy,
                tables.legal_leaves.version,
            )
        )
        remaining = absence.days - legal_days
        code = f"{code}_EXCESS"

    if remaining > 0:
        resolved = resolve_absence_ratio(absence.absence_type, inputs.contract, policy)
        lines.append(
            _absence_line(
                code, remaining, daily_salary, resolved.pay_ratio, resolved.source, policy, None
            )
        )
    return lines


def _absence_line(
    code: str,
    days: Decimal,
    daily_salary: Decimal,
    pay_ratio: Decimal,
    source: RuleSource,
    policy: PayrollPolicy,
    table_version: str | None,
) -> PayrollLine:
    unpaid = 1 - pay_ratio
    return PayrollLine(
        code=code,
        kind=ConceptKind.EARNING,
        quantity=days,
        base=daily_salary,  # sin redondear: solo `amount` pasa por round_line (ADR 0001)
        rate=unpaid,
        amount=round_line(-(days * daily_salary * unpaid)),
        rule_source=source,
        policy_version=policy.version,
        table_version=table_version,
    )
