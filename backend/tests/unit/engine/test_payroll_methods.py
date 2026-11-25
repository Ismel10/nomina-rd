"""Tests de calculate con WORKING_DAYS, NO_PRORATION y método por contrato (ADR 0003, #22).

Calendario real de marzo de 2026: el 1 de marzo es domingo. Días laborables: lunes a viernes = 1,
sábado = 0.5, domingo = 0. Datos FICTICIOS: salario mensual RD$30,000.00 (quincena 15,000.00),
divisor 23.83 → salario diario 1,258.917331…

`working_days` = días laborables del tramo con contrato dentro del periodo, SIN restar ausencias.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from nomina.engine.errors import PayrollInputError, PayrollUnsupportedError
from nomina.engine.models import (
    Absence,
    AbsenceRule,
    ContractInput,
    PayFrequency,
    PayPeriod,
    PayrollInput,
    PayrollLine,
    PayrollPolicy,
    PayrollResult,
    ProrationMethod,
    RateTables,
    RuleSource,
)
from nomina.engine.money import round_line
from nomina.engine.payroll import calculate

CAL = ProrationMethod.CALENDAR_FRACTION
COM = ProrationMethod.COMMERCIAL_30
WD = ProrationMethod.WORKING_DAYS
NO = ProrationMethod.NO_PRORATION
DAILY = Decimal("30000.00") / Decimal("23.83")
ANTES = date(2025, 1, 1)
UNJ = "UNJUSTIFIED"

MakePolicy = Callable[..., PayrollPolicy]
MakeContract = Callable[..., ContractInput]
MakeTables = Callable[..., RateTables]


def biweekly(start: date, end: date) -> PayPeriod:
    return PayPeriod(start, end, end, PayFrequency.BIWEEKLY)


def monthly(start: date, end: date) -> PayPeriod:
    return PayPeriod(start, end, end, PayFrequency.MONTHLY)


MAR = monthly(date(2026, 3, 1), date(2026, 3, 31))
MAR_Q1 = biweekly(date(2026, 3, 1), date(2026, 3, 15))
MAR_Q2 = biweekly(date(2026, 3, 16), date(2026, 3, 31))
FEB = monthly(date(2026, 2, 1), date(2026, 2, 28))
FEB_Q2 = biweekly(date(2026, 2, 16), date(2026, 2, 28))


def salary_line(result: PayrollResult) -> PayrollLine:
    found = [ln for ln in result.lines if ln.code == "ORDINARY_SALARY"]
    assert len(found) == 1
    return found[0]


def run(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    period: PayPeriod,
    *,
    policy_method: ProrationMethod = WD,
    contract_method: ProrationMethod | None = None,
    start: date = ANTES,
    end: date | None = None,
    working_days: str | None = None,
    absences: tuple[Absence, ...] = (),
    divisor: str = "23.83",
) -> PayrollResult:
    contract = make_contract(start_date=start, end_date=end, proration_method=contract_method)
    policy = make_policy(
        proration_method=policy_method,
        daily_salary_divisor=Decimal(divisor),
        absence_rules=(AbsenceRule(UNJ, Decimal("0")),),
    )
    days = None if working_days is None else Decimal(working_days)
    inputs = PayrollInput(period, contract, absences, working_days=days)
    return calculate(inputs, make_tables(), policy)


# =========================================================================== WORKING_DAYS


def test_w1_working_days_periodo_completo_paga_el_salario_del_periodo(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """La 1.ª quincena completa tiene 11 días laborables (11 x diario = 13,848.09), pero un periodo
    completo paga el salario del periodo: 15,000.00 (ADR 0003)."""
    salary = salary_line(run(make_policy, make_contract, make_tables, MAR_Q1))
    assert salary.amount == Decimal("15000.00")
    assert salary.quantity is None
    assert salary.base == Decimal("15000.00")
    assert salary.rule_source is RuleSource.COMPANY


@pytest.mark.parametrize(
    ("period", "start", "end", "days", "amount"),
    [
        # W2 · ingreso vie 6: vie 6 = 1, sáb 7 = 0.5, lun 9-vie 13 = 5, sáb 14 = 0.5 → 7
        (MAR_Q1, date(2026, 3, 6), None, "7", "8812.42"),
        # ingreso lun 9: lun 9-vie 13 = 5, sáb 14 = 0.5 → 5.5
        (MAR_Q1, date(2026, 3, 9), None, "5.5", "6924.05"),
        # W3 · salida mar 24: lun 16-vie 20 = 5, sáb 21 = 0.5, lun 23-mar 24 = 2 → 7.5
        (MAR_Q2, ANTES, date(2026, 3, 24), "7.5", "9441.88"),
        # W4 · mensual, ingreso lun 16: lun 16-vie 20 = 5, sáb 21 = 0.5, lun 23-vie 27 = 5,
        #      sáb 28 = 0.5, lun 30-mar 31 = 2 → 13
        (MAR, date(2026, 3, 16), None, "13", "16365.93"),
    ],
    ids=["W2-ingreso-vie-6", "ingreso-lun-9", "W3-salida-mar-24", "W4-mensual-ingreso-lun-16"],
)
def test_working_days_periodo_parcial(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    period: PayPeriod,
    start: date,
    end: date | None,
    days: str,
    amount: str,
) -> None:
    result = run(
        make_policy, make_contract, make_tables, period, start=start, end=end, working_days=days
    )
    salary = salary_line(result)
    assert salary.amount == Decimal(amount)
    assert salary.quantity == Decimal(days)
    assert salary.base == DAILY  # salario diario sin redondear
    assert salary.rule_source is RuleSource.COMPANY


def test_w9_working_days_no_resta_ausencias_la_ausencia_se_descuenta_aparte(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Documenta el significado de `working_days` (ADR 0003): son los días laborables del tramo con
    contrato SIN restar ausencias.

    Ingreso vie 6 (vie 6 = 1, sáb 7 = 0.5, lun 9-vie 13 = 5, sáb 14 = 0.5 → 7). El empleado faltó
    1 día injustificado: `working_days` sigue siendo 7 (no 6), y la falta llega como novedad.
    Salario: 7 x 1,258.917331… = 8,812.42. Ausencia: -1,258.92. Bruto: 7,553.50.
    Si se informara 6 y además la ausencia, la falta se descontaría dos veces (6,294.58).
    """
    result = run(
        make_policy,
        make_contract,
        make_tables,
        MAR_Q1,
        start=date(2026, 3, 6),
        working_days="7",
        absences=(Absence(UNJ, Decimal("1")),),
    )
    assert salary_line(result).amount == Decimal("8812.42")
    assert result.gross == Decimal("7553.50")


def test_w11_working_days_con_divisor_30(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """ "/30" de los Excel: WORKING_DAYS con divisor 30. Diario 1,000.00; ingreso vie 6 → 7 días
    (vie 6 = 1, sáb 7 = 0.5, lun 9-vie 13 = 5, sáb 14 = 0.5) → 7,000.00."""
    result = run(
        make_policy,
        make_contract,
        make_tables,
        MAR_Q1,
        start=date(2026, 3, 6),
        working_days="7",
        divisor="30",
    )
    assert salary_line(result).amount == Decimal("7000.00")


def test_w5_periodo_parcial_sin_working_days_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    with pytest.raises(PayrollInputError):
        run(make_policy, make_contract, make_tables, MAR_Q1, start=date(2026, 3, 6))


def test_w7_working_days_mayor_que_los_dias_calendario_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Ingreso sáb 14: 2 días calendario con contrato (14 y 15); 3 días laborables es imposible.
    El dato correcto sería 0.5 (sáb 14 = 0.5, dom 15 = 0)."""
    with pytest.raises(PayrollInputError):
        run(
            make_policy,
            make_contract,
            make_tables,
            MAR_Q1,
            start=date(2026, 3, 14),
            working_days="3",
        )


def test_w8_working_days_que_superan_el_salario_del_periodo_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Ingreso lun 2 con 12 días: 12 x 1,258.917331… = 15,107.01 > 15,000.00 → error de carga.
    El dato correcto sería 11 (lun 2-vie 6 = 5, sáb 7 = 0.5, lun 9-vie 13 = 5, sáb 14 = 0.5)."""
    with pytest.raises(PayrollInputError):
        run(
            make_policy,
            make_contract,
            make_tables,
            MAR_Q1,
            start=date(2026, 3, 2),
            working_days="12",
        )


def test_w10_working_days_en_periodo_completo_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    with pytest.raises(PayrollInputError):
        run(make_policy, make_contract, make_tables, MAR_Q1, working_days="11")


@pytest.mark.parametrize("method", [CAL, COM])
@pytest.mark.parametrize(
    "start",
    [date(2026, 3, 6), ANTES],
    ids=["parcial-ingreso-vie-6", "periodo-completo"],
)
def test_working_days_con_metodos_que_cuentan_dias_es_error(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    method: ProrationMethod,
    start: date,
) -> None:
    """CALENDAR_FRACTION y COMMERCIAL_30 cuentan los días por su cuenta: un `working_days`
    informado no se usaría, y un dato que no se usa no se ignora en silencio (mismo criterio
    que W10; ADR 0003)."""
    with pytest.raises(PayrollInputError, match="working_days"):
        run(
            make_policy,
            make_contract,
            make_tables,
            MAR_Q1,
            policy_method=method,
            start=start,
            working_days="7",
        )


@pytest.mark.parametrize(
    "start",
    [date(2026, 3, 10), ANTES],
    ids=["parcial-ingreso-mar-10", "periodo-completo"],
)
def test_working_days_con_no_proration_es_error(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    start: date,
) -> None:
    """NO_PRORATION paga el periodo completo sin usar `working_days`: el dato no se ignora en
    silencio (regla única: solo WORKING_DAYS en periodo parcial; ADR 0003)."""
    with pytest.raises(PayrollInputError, match="working_days"):
        run(
            make_policy,
            make_contract,
            make_tables,
            MAR_Q1,
            policy_method=NO,
            start=start,
            working_days="4",
        )


def test_ausencias_que_superan_los_working_days_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Ingreso lun 9: 7 días calendario (pasa el límite general) pero 5.5 días laborables
    (lun 9-vie 13 = 5, sáb 14 = 0.5). 6 días de ausencia > 5.5 → error."""
    with pytest.raises(PayrollInputError):
        run(
            make_policy,
            make_contract,
            make_tables,
            MAR_Q1,
            start=date(2026, 3, 9),
            working_days="5.5",
            absences=(Absence(UNJ, Decimal("6")),),
        )


def test_working_days_sin_dias_de_servicio_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Contrato que terminó el 28 de febrero: un `working_days` para marzo es un dato sin días de
    servicio, como una novedad (mismo criterio que el #19)."""
    with pytest.raises(PayrollInputError):
        run(
            make_policy,
            make_contract,
            make_tables,
            MAR_Q1,
            end=date(2026, 2, 28),
            working_days="2",
        )


# =========================================================================== NO_PRORATION


@pytest.mark.parametrize(
    ("period", "start", "amount"),
    [
        (MAR_Q1, date(2026, 3, 10), "15000.00"),  # N1 · ingreso mar 10
        (FEB, date(2026, 2, 20), "30000.00"),  # N2 · febrero mensual, ingreso vie 20
    ],
    ids=["N1-ingreso-mar-10", "N2-febrero-ingreso-20"],
)
def test_no_proration_paga_el_periodo_completo_con_ingreso_a_mitad(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    period: PayPeriod,
    start: date,
    amount: str,
) -> None:
    result = run(make_policy, make_contract, make_tables, period, policy_method=NO, start=start)
    salary = salary_line(result)
    assert salary.amount == Decimal(amount)
    assert salary.quantity is None
    assert salary.rule_source is RuleSource.COMPANY


def test_n3_no_proration_con_salida_a_mitad_no_soportada(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Pendiente con la firma (#27): no se paga de más sin una regla confirmada (ADR 0003)."""
    with pytest.raises(PayrollUnsupportedError):
        run(
            make_policy,
            make_contract,
            make_tables,
            MAR_Q1,
            policy_method=NO,
            end=date(2026, 3, 10),
        )


def test_no_proration_con_salida_el_ultimo_dia_del_periodo_paga_completo(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    result = run(
        make_policy, make_contract, make_tables, MAR_Q1, policy_method=NO, end=date(2026, 3, 15)
    )
    assert salary_line(result).amount == Decimal("15000.00")


def test_n4_no_proration_fuera_del_periodo_no_genera_lineas(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    result = run(
        make_policy, make_contract, make_tables, MAR_Q1, policy_method=NO, end=date(2026, 2, 28)
    )
    assert result.lines == ()


def test_n5_no_proration_con_ausencia(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Ingreso mar 10 sin prorrateo: 15,000.00 - 1,258.92 (1 día injustificado) = 13,741.08."""
    result = run(
        make_policy,
        make_contract,
        make_tables,
        MAR_Q1,
        policy_method=NO,
        start=date(2026, 3, 10),
        absences=(Absence(UNJ, Decimal("1")),),
    )
    assert result.gross == Decimal("13741.08")


def test_n6_no_proration_ausencias_mayores_que_los_dias_calendario_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Ingreso mar 10: 6 días calendario con contrato (10 al 15); 7 días de ausencia → error."""
    with pytest.raises(PayrollInputError):
        run(
            make_policy,
            make_contract,
            make_tables,
            MAR_Q1,
            policy_method=NO,
            start=date(2026, 3, 10),
            absences=(Absence(UNJ, Decimal("7")),),
        )


# =========================================================================== método por contrato


def test_c1_contrato_working_days_sobre_politica_calendar(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Ingreso vie 6, 7 días laborables (vie 6 = 1, sáb 7 = 0.5, lun 9-vie 13 = 5, sáb 14 = 0.5)."""
    result = run(
        make_policy,
        make_contract,
        make_tables,
        MAR_Q1,
        policy_method=CAL,
        contract_method=WD,
        start=date(2026, 3, 6),
        working_days="7",
    )
    salary = salary_line(result)
    assert salary.amount == Decimal("8812.42")
    assert salary.rule_source is RuleSource.CONTRACT


@pytest.mark.parametrize(
    ("contract_method", "amount", "source"),
    [
        (NO, "15000.00", RuleSource.CONTRACT),  # C3 · contrato sin prorrateo
        (None, "7000.00", RuleSource.COMPANY),  # misma política COM: índices 24..30 = 7 → 7/15
    ],
)
def test_c3_politica_commercial_y_contrato_sin_prorrateo(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    contract_method: ProrationMethod | None,
    amount: str,
    source: RuleSource,
) -> None:
    result = run(
        make_policy,
        make_contract,
        make_tables,
        MAR_Q2,
        policy_method=COM,
        contract_method=contract_method,
        start=date(2026, 3, 24),
    )
    salary = salary_line(result)
    assert salary.amount == Decimal(amount)
    assert salary.rule_source is source


def test_c4_dos_contratos_de_la_misma_empresa_con_metodos_distintos(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Misma empresa (política CAL), ingreso mar 10: el contrato sin prorrateo cobra 15,000.00; el
    prorrateado, 15,000 x 6/15 = 6,000.00 (como en la firma)."""
    start = date(2026, 3, 10)
    sin_prorrateo = run(
        make_policy,
        make_contract,
        make_tables,
        MAR_Q1,
        policy_method=CAL,
        contract_method=NO,
        start=start,
    )
    prorrateado = run(
        make_policy, make_contract, make_tables, MAR_Q1, policy_method=CAL, start=start
    )
    assert salary_line(sin_prorrateo).amount == Decimal("15000.00")
    assert salary_line(prorrateado).amount == Decimal("6000.00")


# =========================================================================== properties

_FIXTURES_OK = settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
salaries = st.decimals(min_value=Decimal("29988.00"), max_value=Decimal("1000000.00"), places=2)


@_FIXTURES_OK
@given(
    salary=salaries,
    period=st.sampled_from([MAR, MAR_Q1, MAR_Q2, FEB, FEB_Q2]),
    method=st.sampled_from([CAL, COM, WD, NO]),
)
def test_prop_periodo_completo_paga_el_salario_del_periodo_con_cualquier_metodo(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    salary: Decimal,
    period: PayPeriod,
    method: ProrationMethod,
) -> None:
    contract = make_contract(monthly_salary=salary)
    policy = make_policy(proration_method=method)
    result = calculate(PayrollInput(period, contract), make_tables(), policy)
    expected = salary if period.frequency is PayFrequency.MONTHLY else salary / 2
    assert salary_line(result).amount == round_line(expected)


@_FIXTURES_OK
@given(day=st.integers(min_value=1, max_value=15))
def test_prop_no_proration_paga_la_quincena_con_cualquier_dia_de_ingreso(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables, day: int
) -> None:
    result = run(
        make_policy, make_contract, make_tables, MAR_Q1, policy_method=NO, start=date(2026, 3, day)
    )
    assert salary_line(result).amount == Decimal("15000.00")


@_FIXTURES_OK
@given(day=st.integers(min_value=2, max_value=15), halves=st.integers(min_value=1, max_value=28))
def test_prop_working_days_parcial_es_diario_por_dias_y_no_supera_la_quincena(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    day: int,
    halves: int,
) -> None:
    days = Decimal(halves) / 2
    calendar_days = 15 - day + 1
    assume(days <= calendar_days and DAILY * days <= Decimal("15000.00"))
    result = run(
        make_policy,
        make_contract,
        make_tables,
        MAR_Q1,
        start=date(2026, 3, day),
        working_days=str(days),
    )
    amount = salary_line(result).amount
    assert amount == round_line(DAILY * days)
    assert amount <= Decimal("15000.00")
