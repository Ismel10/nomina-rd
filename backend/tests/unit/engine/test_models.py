"""Tests de nomina.engine.models: invariantes de los datos que recibe y devuelve el motor.

Datos ficticios. Los mensajes de error nunca deben incluir montos (AGENTS.md §3.6).
"""

import dataclasses
from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest

from nomina.engine.errors import PayrollConfigError, PayrollInputError
from nomina.engine.models import (
    Absence,
    AbsenceRule,
    ConceptKind,
    ContractInput,
    EmployeeGroup,
    LaborLimitsTable,
    LeaveCategory,
    LegalLeave,
    LegalLeaveTable,
    MinimumWage,
    MinimumWageTable,
    PayFrequency,
    PayPeriod,
    PayrollInput,
    PayrollLine,
    PayrollPolicy,
    PayrollResult,
    RateTables,
)

# --------------------------------------------------------------------------- errores


def test_errores_del_motor_son_value_error() -> None:
    assert issubclass(PayrollConfigError, ValueError)
    assert issubclass(PayrollInputError, ValueError)


# --------------------------------------------------------------------------- AbsenceRule


@pytest.mark.parametrize("ratio", ["0", "0.5", "1", "0.0", "1.00"])
def test_absence_rule_acepta_ratio_entre_0_y_1(ratio: str) -> None:
    rule = AbsenceRule("UNJUSTIFIED", Decimal(ratio))
    assert rule.pay_ratio == Decimal(ratio)


@pytest.mark.parametrize("ratio", ["-0.01", "1.01", "2", "NaN", "Infinity"])
def test_absence_rule_rechaza_ratio_fuera_de_rango(ratio: str) -> None:
    with pytest.raises(PayrollConfigError):
        AbsenceRule("UNJUSTIFIED", Decimal(ratio))


def test_absence_rule_rechaza_ratio_float() -> None:
    with pytest.raises(TypeError):
        AbsenceRule("UNJUSTIFIED", 0.5)  # type: ignore[arg-type]


@pytest.mark.parametrize("code", ["", "   "])
def test_absence_rule_rechaza_tipo_vacio(code: str) -> None:
    with pytest.raises(PayrollConfigError):
        AbsenceRule(code, Decimal("1"))


# --------------------------------------------------------------------------- Absence (novedad)


@pytest.mark.parametrize("days", ["1", "0.5", "3"])
def test_absence_acepta_dias_positivos(days: str) -> None:
    assert Absence("UNJUSTIFIED", Decimal(days)).days == Decimal(days)


@pytest.mark.parametrize("days", ["0", "-1", "NaN"])
def test_absence_rechaza_dias_no_positivos(days: str) -> None:
    with pytest.raises(PayrollInputError):
        Absence("UNJUSTIFIED", Decimal(days))


def test_absence_rechaza_tipo_vacio() -> None:
    with pytest.raises(PayrollInputError):
        Absence("", Decimal("1"))


# --------------------------------------------------------------------------- PayPeriod


def test_pay_period_rechaza_fin_antes_del_inicio() -> None:
    with pytest.raises(PayrollInputError):
        PayPeriod(date(2026, 1, 15), date(2026, 1, 1), date(2026, 1, 15), PayFrequency.BIWEEKLY)


def test_pay_period_de_un_dia_es_valido() -> None:
    period = PayPeriod(date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 1), PayFrequency.MONTHLY)
    assert period.start == period.end


# --------------------------------------------------------------------------- ContractInput


@pytest.mark.parametrize("salary", ["0", "-1.00", "NaN"])
def test_contract_rechaza_salario_no_positivo_sin_exponer_el_monto(
    make_contract: Callable[..., ContractInput], salary: str
) -> None:
    with pytest.raises(PayrollInputError) as excinfo:
        make_contract(monthly_salary=Decimal(salary))
    if salary != "0":
        assert salary not in str(excinfo.value)


def test_contract_rechaza_salario_float(make_contract: Callable[..., ContractInput]) -> None:
    with pytest.raises(TypeError):
        make_contract(monthly_salary=30000.0)


def test_contract_rechaza_salida_antes_del_ingreso(
    make_contract: Callable[..., ContractInput],
) -> None:
    with pytest.raises(PayrollInputError):
        make_contract(start_date=date(2026, 2, 1), end_date=date(2026, 1, 31))


def test_contract_rechaza_reglas_duplicadas(make_contract: Callable[..., ContractInput]) -> None:
    rules = (AbsenceRule("UNJUSTIFIED", Decimal("1")), AbsenceRule("UNJUSTIFIED", Decimal("0")))
    with pytest.raises(PayrollConfigError):
        make_contract(absence_rules=rules)


def test_contract_guarda_las_reglas_como_tupla(
    make_contract: Callable[..., ContractInput],
) -> None:
    contract = make_contract(absence_rules=[AbsenceRule("UNJUSTIFIED", Decimal("1"))])
    assert isinstance(contract.absence_rules, tuple)


def test_los_modelos_son_inmutables(make_contract: Callable[..., ContractInput]) -> None:
    contract = make_contract()
    with pytest.raises(dataclasses.FrozenInstanceError):
        contract.monthly_salary = Decimal("1.00")  # type: ignore[misc]


# --------------------------------------------------------------------------- PayrollInput


def test_payroll_input_rechaza_novedades_duplicadas_por_tipo(
    make_contract: Callable[..., ContractInput],
) -> None:
    period = PayPeriod(
        date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 15), PayFrequency.BIWEEKLY
    )
    absences = (Absence("UNJUSTIFIED", Decimal("1")), Absence("UNJUSTIFIED", Decimal("2")))
    with pytest.raises(PayrollInputError):
        PayrollInput(period, make_contract(), absences)


# --------------------------------------------------------------------------- vigencia


def test_vigencia_rechaza_fin_antes_del_inicio(make_policy: Callable[..., PayrollPolicy]) -> None:
    with pytest.raises(PayrollConfigError):
        make_policy(valid_from=date(2026, 2, 1), valid_to=date(2026, 1, 31))


@pytest.mark.parametrize(
    ("on", "expected"),
    [
        (date(2025, 12, 31), False),  # un día antes del inicio
        (date(2026, 1, 1), True),  # inicio incluido
        (date(2026, 6, 30), True),  # fin incluido
        (date(2026, 7, 1), False),  # un día después del fin
    ],
)
def test_vigencia_incluye_ambos_extremos(
    make_policy: Callable[..., PayrollPolicy], on: date, expected: bool
) -> None:
    policy = make_policy(valid_from=date(2026, 1, 1), valid_to=date(2026, 6, 30))
    assert policy.covers(on) is expected


def test_vigencia_sin_fin_es_abierta(make_policy: Callable[..., PayrollPolicy]) -> None:
    assert make_policy(valid_to=None).covers(date(2099, 12, 31))


# --------------------------------------------------------------------------- PayrollPolicy


@pytest.mark.parametrize("field", ["daily_salary_divisor", "workday_hours"])
@pytest.mark.parametrize("value", ["0", "-1"])
def test_policy_rechaza_divisor_y_jornada_no_positivos(
    make_policy: Callable[..., PayrollPolicy], field: str, value: str
) -> None:
    with pytest.raises(PayrollConfigError):
        make_policy(**{field: Decimal(value)})


def test_policy_rechaza_reglas_duplicadas(make_policy: Callable[..., PayrollPolicy]) -> None:
    rules = (AbsenceRule("UNJUSTIFIED", Decimal("1")), AbsenceRule("UNJUSTIFIED", Decimal("0")))
    with pytest.raises(PayrollConfigError):
        make_policy(absence_rules=rules)


def test_policy_rechaza_grupos_duplicados(make_policy: Callable[..., PayrollPolicy]) -> None:
    groups = (EmployeeGroup("OPERATIVO", "Operativo"), EmployeeGroup("OPERATIVO", "Otro"))
    with pytest.raises(PayrollConfigError):
        make_policy(groups=groups)


def test_policy_busca_grupo_por_codigo(make_policy: Callable[..., PayrollPolicy]) -> None:
    gerencia = EmployeeGroup("GERENCIA", "Gerencia")
    policy = make_policy(groups=(gerencia, EmployeeGroup("OPERATIVO", "Operativo")))
    assert policy.group("GERENCIA") is gerencia
    assert policy.group("NO_EXISTE") is None


def test_policy_rechaza_categoria_de_minimo_vacia(
    make_policy: Callable[..., PayrollPolicy],
) -> None:
    with pytest.raises(PayrollConfigError):
        make_policy(minimum_wage_category="")


def test_group_rechaza_reglas_duplicadas() -> None:
    rules = (AbsenceRule("UNJUSTIFIED", Decimal("1")), AbsenceRule("UNJUSTIFIED", Decimal("0")))
    with pytest.raises(PayrollConfigError):
        EmployeeGroup("OPERATIVO", "Operativo", rules)


def test_group_rechaza_codigo_vacio() -> None:
    with pytest.raises(PayrollConfigError):
        EmployeeGroup("", "Sin código")


# --------------------------------------------------------------------------- tablas legales


def test_minimum_wage_table_busca_el_minimo_mensual_por_categoria() -> None:
    table = MinimumWageTable(
        "MW-TEST",
        date(2026, 2, 1),
        None,
        (MinimumWage("A", Decimal("100.00")), MinimumWage("B", Decimal("200.00"))),
    )
    assert table.monthly_minimum("B") == Decimal("200.00")
    assert table.monthly_minimum("C") is None


def test_minimum_wage_table_rechaza_categorias_duplicadas() -> None:
    minimums = (MinimumWage("A", Decimal("100.00")), MinimumWage("A", Decimal("200.00")))
    with pytest.raises(PayrollConfigError):
        MinimumWageTable("MW-TEST", date(2026, 2, 1), None, minimums)


@pytest.mark.parametrize("amount", ["0", "-100.00"])
def test_minimum_wage_rechaza_monto_no_positivo(amount: str) -> None:
    with pytest.raises(PayrollConfigError):
        MinimumWage("A", Decimal(amount))


@pytest.mark.parametrize("field", ["max_daily_hours", "max_weekly_hours"])
def test_labor_limits_rechaza_horas_no_positivas(field: str) -> None:
    values = {"max_daily_hours": Decimal("8"), "max_weekly_hours": Decimal("44")}
    values[field] = Decimal("0")
    with pytest.raises(PayrollConfigError):
        LaborLimitsTable("LL-TEST", date(2026, 1, 1), None, **values)


def test_licencia_pagada_por_el_empleador_exige_maximo_de_dias() -> None:
    with pytest.raises(PayrollConfigError):
        LegalLeave("MARRIAGE_LEAVE", LeaveCategory.EMPLOYER_PAID, None)


@pytest.mark.parametrize("max_days", ["0", "-1"])
def test_legal_leave_rechaza_max_days_no_positivo(max_days: str) -> None:
    with pytest.raises(PayrollConfigError):
        LegalLeave("MARRIAGE_LEAVE", LeaveCategory.EMPLOYER_PAID, Decimal(max_days))


def test_legal_leave_rechaza_max_days_float() -> None:
    with pytest.raises(TypeError):
        LegalLeave("MARRIAGE_LEAVE", LeaveCategory.EMPLOYER_PAID, 5.0)  # type: ignore[arg-type]


@pytest.mark.parametrize("code", ["", "   "])
def test_legal_leave_rechaza_codigo_vacio(code: str) -> None:
    with pytest.raises(PayrollConfigError):
        LegalLeave(code, LeaveCategory.SUBSIDIZED, None)


@pytest.mark.parametrize("category", ["", "   "])
def test_minimum_wage_rechaza_categoria_vacia(category: str) -> None:
    with pytest.raises(PayrollConfigError):
        MinimumWage(category, Decimal("100.00"))


@pytest.mark.parametrize("version", ["", "   "])
def test_vigencia_rechaza_version_vacia(
    make_policy: Callable[..., PayrollPolicy], version: str
) -> None:
    with pytest.raises(PayrollConfigError):
        make_policy(version=version)


@pytest.mark.parametrize("name", ["", "   "])
def test_group_rechaza_nombre_vacio(name: str) -> None:
    with pytest.raises(PayrollConfigError):
        EmployeeGroup("OPERATIVO", name)


def test_legal_leave_table_busca_por_codigo_y_rechaza_duplicados() -> None:
    marriage = LegalLeave("MARRIAGE_LEAVE", LeaveCategory.EMPLOYER_PAID, Decimal("5"))
    table = LegalLeaveTable("LV-TEST", date(2026, 1, 1), None, (marriage,))
    assert table.leave("MARRIAGE_LEAVE") is marriage
    assert table.leave("UNJUSTIFIED") is None
    with pytest.raises(PayrollConfigError):
        LegalLeaveTable("LV-TEST", date(2026, 1, 1), None, (marriage, marriage))


def test_rate_tables_cubre_una_fecha_solo_si_todas_sus_tablas_la_cubren(
    make_tables: Callable[..., RateTables],
) -> None:
    tables = make_tables()  # salario mínimo vigente desde 2026-02-01
    assert tables.covers(date(2026, 2, 1))
    assert not tables.covers(date(2026, 1, 31))


# --------------------------------------------------------------------------- PayrollLine / Result


def _line(code: str, kind: ConceptKind, amount: str) -> PayrollLine:
    return PayrollLine(
        code=code,
        kind=kind,
        quantity=None,
        base=Decimal(amount),
        rate=None,
        amount=Decimal(amount),
        rule_source=None,
        policy_version="POL-TEST-1",
        table_version=None,
    )


@pytest.mark.parametrize("amount", ["15000.0", "15000", "15000.005"])
def test_linea_exige_monto_redondeado(amount: str) -> None:
    with pytest.raises(ValueError, match=r".+"):
        _line("ORDINARY_SALARY", ConceptKind.EARNING, amount)


def test_resultado_calcula_totales_con_las_lineas() -> None:
    """Bruto = ingresos (incluida la ausencia negativa); neto = bruto - descuentos.

    Ingresos: 15,000.00 - 500.00 = 14,500.00
    Descuentos: 100.00
    Neto: 14,500.00 - 100.00 = 14,400.00
    El aporte patronal (50.00) no afecta ni el bruto ni el neto.
    """
    period = PayPeriod(
        date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 15), PayFrequency.BIWEEKLY
    )
    result = PayrollResult(
        contract_id="CTR-FICTICIO-001",
        period=period,
        lines=(
            _line("ORDINARY_SALARY", ConceptKind.EARNING, "15000.00"),
            _line("ABSENCE_UNJUSTIFIED", ConceptKind.EARNING, "-500.00"),
            _line("LOAN", ConceptKind.DEDUCTION, "100.00"),
            _line("EMPLOYER_X", ConceptKind.EMPLOYER_CONTRIBUTION, "50.00"),
        ),
    )
    assert result.gross == Decimal("14500.00")
    assert result.deductions == Decimal("100.00")
    assert result.net == Decimal("14400.00")
    assert result.employer_contributions == Decimal("50.00")


def test_resultado_sin_lineas_tiene_totales_en_cero() -> None:
    period = PayPeriod(
        date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 15), PayFrequency.BIWEEKLY
    )
    result = PayrollResult("CTR-FICTICIO-001", period, ())
    assert (result.gross, result.deductions, result.net) == (
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("0.00"),
    )
    assert str(result.net) == "0.00"
