"""Tests de nomina.engine.payroll.calculate: salario fijo, ausencias, art. 54 y validaciones.

Casos calculados a mano (plan aprobado del 2a-2, issue #19). Datos FICTICIOS: salario mensual
RD$30,000.00 (quincena RD$15,000.00), divisor 23.83 → salario diario 1,258.917331…
Tablas de las fixtures (tests/conftest.py): mínimo NO_SECTORIZADO_GRANDE RD$29,988.00 desde
2026-02-01; jornada máxima 8 h; MARRIAGE_LEAVE (art. 54, 5 días) y MATERNITY_LEAVE (subsidio).
Tolerancia cero: igualdad exacta de Decimal.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from nomina.engine.errors import PayrollConfigError, PayrollInputError, PayrollUnsupportedError
from nomina.engine.models import (
    Absence,
    AbsenceRule,
    ConceptKind,
    ContractInput,
    EmployeeGroup,
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
DAILY = Decimal("30000.00") / Decimal("23.83")  # salario diario exacto, sin redondear
ANTES = date(2025, 1, 1)
UNJ = "UNJUSTIFIED"


def biweekly(start: date, end: date) -> PayPeriod:
    return PayPeriod(start, end, end, PayFrequency.BIWEEKLY)


def monthly(start: date, end: date) -> PayPeriod:
    return PayPeriod(start, end, end, PayFrequency.MONTHLY)


MAR = monthly(date(2026, 3, 1), date(2026, 3, 31))
MAR_Q1 = biweekly(date(2026, 3, 1), date(2026, 3, 15))
MAR_Q2 = biweekly(date(2026, 3, 16), date(2026, 3, 31))
FEB = monthly(date(2026, 2, 1), date(2026, 2, 28))
FEB_Q2 = biweekly(date(2026, 2, 16), date(2026, 2, 28))

MakePolicy = Callable[..., PayrollPolicy]
MakeContract = Callable[..., ContractInput]
MakeTables = Callable[..., RateTables]


def line(result: PayrollResult, code: str) -> PayrollLine:
    found = [ln for ln in result.lines if ln.code == code]
    assert len(found) == 1, f"se esperaba una línea {code}, hay {len(found)}"
    return found[0]


def unj(ratio: str) -> AbsenceRule:
    return AbsenceRule(UNJ, Decimal(ratio))


# =========================================================================== salario ordinario


@pytest.mark.parametrize(
    ("period", "start", "method", "days", "amount"),
    [
        (MAR, ANTES, CAL, 31, "30000.00"),
        (MAR, ANTES, COM, 30, "30000.00"),
        (MAR_Q2, date(2026, 3, 24), CAL, 8, "7500.00"),
        (MAR_Q2, date(2026, 3, 24), COM, 7, "7000.00"),
        (FEB, date(2026, 2, 15), CAL, 14, "15000.00"),
        (FEB, date(2026, 2, 15), COM, 16, "16000.00"),
        (FEB_Q2, date(2026, 2, 20), CAL, 9, "10384.62"),
        (FEB_Q2, date(2026, 2, 20), COM, 11, "11000.00"),
    ],
)
def test_salario_ordinario_con_prorrateo(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    period: PayPeriod,
    start: date,
    method: ProrationMethod,
    days: int,
    amount: str,
) -> None:
    result = calculate(
        PayrollInput(period, make_contract(start_date=start)),
        make_tables(),
        make_policy(proration_method=method),
    )
    salary = line(result, "ORDINARY_SALARY")
    assert salary.kind is ConceptKind.EARNING
    assert salary.quantity == days
    assert salary.base == (
        Decimal("30000.00") if period.frequency is PayFrequency.MONTHLY else Decimal("15000.00")
    )
    assert salary.amount == Decimal(amount)
    assert salary.rule_source is RuleSource.COMPANY
    assert salary.policy_version == "POL-TEST-1"
    assert result.lines == (salary,)
    assert result.gross == Decimal(amount)


def test_contrato_fuera_del_periodo_no_genera_lineas(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    contract = make_contract(end_date=date(2026, 2, 28))
    result = calculate(PayrollInput(MAR_Q1, contract), make_tables(), make_policy())
    assert result.lines == ()
    assert result.gross == Decimal("0.00")


def test_novedades_sin_dias_de_servicio_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    contract = make_contract(end_date=date(2026, 2, 28))
    inputs = PayrollInput(MAR_Q1, contract, (Absence(UNJ, Decimal("1")),))
    with pytest.raises(PayrollInputError):
        calculate(inputs, make_tables(), make_policy(absence_rules=(unj("0"),)))


# =========================================================================== ausencias


@pytest.mark.parametrize(
    ("ratio", "amount", "gross"),
    [
        ("0", "-1258.92", "13741.08"),  # -1 x 1,258.917331... x (1 - 0)
        ("0.5", "-629.46", "14370.54"),  # -1 x 1,258.917331... x 0.5 = -629.458665...
        ("1", "0.00", "15000.00"),  # se paga completa: línea en 0.00 (se incluye)
    ],
)
def test_ausencia_injustificada_segun_la_politica(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    ratio: str,
    amount: str,
    gross: str,
) -> None:
    inputs = PayrollInput(MAR_Q1, make_contract(), (Absence(UNJ, Decimal("1")),))
    result = calculate(inputs, make_tables(), make_policy(absence_rules=(unj(ratio),)))
    absence = line(result, "ABSENCE_UNJUSTIFIED")
    assert absence.kind is ConceptKind.EARNING
    assert absence.quantity == Decimal("1")
    assert absence.base == DAILY  # sin redondear
    assert absence.rate == 1 - Decimal(ratio)
    assert absence.amount == Decimal(amount)
    assert absence.rule_source is RuleSource.COMPANY
    assert result.gross == Decimal(gross)


OPERATIVO = EmployeeGroup("OPERATIVO", "Operativo", (unj("0.5"),))
GERENCIA = EmployeeGroup("GERENCIA", "Gerencia")


@pytest.mark.parametrize(
    ("group_code", "contract_rules", "amount", "source"),
    [
        (None, (), "-1258.92", RuleSource.COMPANY),  # a) sin grupo → empresa (0)
        ("OPERATIVO", (), "-629.46", RuleSource.GROUP),  # b) grupo con regla (0.5)
        ("OPERATIVO", (unj("1"),), "0.00", RuleSource.CONTRACT),  # c) excepción del contrato (1)
    ],
)
def test_cascada_en_el_calculo(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    group_code: str | None,
    contract_rules: tuple[AbsenceRule, ...],
    amount: str,
    source: RuleSource,
) -> None:
    contract = make_contract(group_code=group_code, absence_rules=contract_rules)
    policy = make_policy(absence_rules=(unj("0"),), groups=(OPERATIVO, GERENCIA))
    inputs = PayrollInput(MAR_Q1, contract, (Absence(UNJ, Decimal("1")),))
    absence = line(calculate(inputs, make_tables(), policy), "ABSENCE_UNJUSTIFIED")
    assert absence.amount == Decimal(amount)
    assert absence.rule_source is source


def test_cascada_d_sin_regla_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    inputs = PayrollInput(
        MAR_Q1, make_contract(group_code="GERENCIA"), (Absence(UNJ, Decimal("1")),)
    )
    with pytest.raises(PayrollConfigError, match=UNJ):
        calculate(inputs, make_tables(), make_policy(groups=(GERENCIA,)))


# =========================================================================== art. 54 y licencias


def test_art_54_dentro_del_maximo_legal_se_paga_por_ley_sin_regla_de_empresa(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    inputs = PayrollInput(MAR_Q1, make_contract(), (Absence("MARRIAGE_LEAVE", Decimal("3")),))
    result = calculate(inputs, make_tables(), make_policy(absence_rules=()))
    leave = line(result, "ABSENCE_MARRIAGE_LEAVE")
    assert leave.quantity == Decimal("3")
    assert leave.rate == Decimal("0")
    assert leave.amount == Decimal("0.00")
    assert leave.rule_source is RuleSource.LAW
    assert leave.table_version == "LEY-16-92-ART-54"
    assert result.gross == Decimal("15000.00")


def test_art_54_exceso_usa_la_cascada(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """7 días de matrimonio, máximo legal 5: 5 por ley (0.00) + 2 de exceso con la regla de la
    empresa (ratio 0): -2 x 1,258.917331... = -2,517.834662... → -2,517.83. Bruto 12,482.17."""
    policy = make_policy(absence_rules=(AbsenceRule("MARRIAGE_LEAVE", Decimal("0")),))
    inputs = PayrollInput(MAR_Q1, make_contract(), (Absence("MARRIAGE_LEAVE", Decimal("7")),))
    result = calculate(inputs, make_tables(), policy)
    legal = line(result, "ABSENCE_MARRIAGE_LEAVE")
    excess = line(result, "ABSENCE_MARRIAGE_LEAVE_EXCESS")
    assert (legal.quantity, legal.amount, legal.rule_source) == (
        Decimal("5"),
        Decimal("0.00"),
        RuleSource.LAW,
    )
    assert (excess.quantity, excess.amount, excess.rule_source) == (
        Decimal("2"),
        Decimal("-2517.83"),
        RuleSource.COMPANY,
    )
    assert result.gross == Decimal("12482.17")


def test_art_54_exceso_sin_regla_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    inputs = PayrollInput(MAR_Q1, make_contract(), (Absence("MARRIAGE_LEAVE", Decimal("7")),))
    with pytest.raises(PayrollConfigError, match="MARRIAGE_LEAVE"):
        calculate(inputs, make_tables(), make_policy(absence_rules=()))


def test_licencia_subsidiada_no_soportada(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    inputs = PayrollInput(MAR_Q1, make_contract(), (Absence("MATERNITY_LEAVE", Decimal("5")),))
    with pytest.raises(PayrollUnsupportedError, match="MATERNITY_LEAVE"):
        calculate(inputs, make_tables(), make_policy())


def test_no_soportado_es_un_error_de_entrada() -> None:
    assert issubclass(PayrollUnsupportedError, PayrollInputError)


# =========================================================================== límite de ausencias


def test_ausencias_mayores_que_el_salario_se_topan_en_cero(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """12 días injustificados (ratio 0) en una quincena completa: -12 x 1,258.917331... =
    -15,107.007973... → -15,107.01. Supera el salario (15,000.00): tope +107.01, bruto 0.00."""
    inputs = PayrollInput(MAR_Q1, make_contract(), (Absence(UNJ, Decimal("12")),))
    result = calculate(inputs, make_tables(), make_policy(absence_rules=(unj("0"),)))
    assert line(result, "ABSENCE_UNJUSTIFIED").amount == Decimal("-15107.01")
    cap = line(result, "ABSENCE_DISCOUNT_CAP")
    assert cap.kind is ConceptKind.EARNING
    assert cap.base == Decimal("15107.01")  # descuento total sin topar
    assert cap.amount == Decimal("107.01")
    assert cap.rule_source is RuleSource.SYSTEM
    assert result.gross == Decimal("0.00")


def test_sin_tope_no_hay_linea_de_tope(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    inputs = PayrollInput(MAR_Q1, make_contract(), (Absence(UNJ, Decimal("1")),))
    result = calculate(inputs, make_tables(), make_policy(absence_rules=(unj("0"),)))
    assert all(ln.code != "ABSENCE_DISCOUNT_CAP" for ln in result.lines)


def test_mas_dias_de_ausencia_que_dias_con_contrato_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """Ingreso el 14 en la quincena 1-15: 2 días calendario con contrato; 5 de ausencia → error."""
    contract = make_contract(start_date=date(2026, 3, 14))
    inputs = PayrollInput(MAR_Q1, contract, (Absence(UNJ, Decimal("5")),))
    with pytest.raises(PayrollInputError):
        calculate(inputs, make_tables(), make_policy(absence_rules=(unj("0"),)))


def test_el_limite_suma_todos_los_tipos_incluido_el_art_54(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """10 injustificados + 6 de matrimonio = 16 > 15 días calendario de la quincena → error."""
    absences = (Absence(UNJ, Decimal("10")), Absence("MARRIAGE_LEAVE", Decimal("6")))
    policy = make_policy(absence_rules=(unj("0"), AbsenceRule("MARRIAGE_LEAVE", Decimal("0"))))
    with pytest.raises(PayrollInputError):
        calculate(PayrollInput(MAR_Q1, make_contract(), absences), make_tables(), policy)


def test_ausencia_igual_a_los_dias_con_contrato_es_valida(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    inputs = PayrollInput(MAR_Q1, make_contract(), (Absence(UNJ, Decimal("15")),))
    result = calculate(inputs, make_tables(), make_policy(absence_rules=(unj("0"),)))
    assert result.gross == Decimal("0.00")


def test_el_limite_usa_dias_calendario_aunque_el_metodo_sea_commercial_30(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    """2.ª quincena de marzo: 16 días calendario (15 comerciales).

    16 días de ausencia son válidos: el límite usa días calendario sea cual sea el método."""
    inputs = PayrollInput(MAR_Q2, make_contract(), (Absence(UNJ, Decimal("16")),))
    policy = make_policy(proration_method=COM, absence_rules=(unj("0"),))
    assert calculate(inputs, make_tables(), policy).gross == Decimal("0.00")


# =========================================================================== validaciones previas


def test_salario_menor_que_el_minimo_es_error_sin_exponer_el_monto(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    contract = make_contract(monthly_salary=Decimal("29000.00"))
    with pytest.raises(PayrollInputError) as excinfo:
        calculate(PayrollInput(MAR_Q1, contract), make_tables(), make_policy())
    assert "29000" not in str(excinfo.value)
    assert "29988" not in str(excinfo.value)


def test_salario_igual_al_minimo_es_valido(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    contract = make_contract(monthly_salary=Decimal("29988.00"))
    result = calculate(PayrollInput(MAR_Q1, contract), make_tables(), make_policy())
    assert result.gross == Decimal("14994.00")


def test_forma_de_periodo_invalida_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    period = biweekly(date(2026, 3, 2), date(2026, 3, 16))
    with pytest.raises(PayrollInputError):
        calculate(PayrollInput(period, make_contract()), make_tables(), make_policy())


def test_politica_invalida_contra_las_tablas_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    with pytest.raises(PayrollConfigError):
        calculate(
            PayrollInput(MAR_Q1, make_contract()),
            make_tables(),
            make_policy(workday_hours=Decimal("9")),
        )


# =========================================================================== vigencia

V1 = {"version": "POL-V1", "valid_from": date(2026, 1, 1), "valid_to": date(2026, 6, 30)}
V2 = {"version": "POL-V2", "valid_from": date(2026, 7, 1), "valid_to": None}
JUN_Q1 = biweekly(date(2026, 6, 1), date(2026, 6, 15))
JUL_Q1 = biweekly(date(2026, 7, 1), date(2026, 7, 15))


def test_vigencia_misma_nomina_con_dos_versiones_de_politica(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    v1 = make_policy(**V1, absence_rules=(unj("0"),))
    v2 = make_policy(**V2, absence_rules=(unj("1"),))
    absence = (Absence(UNJ, Decimal("1")),)
    june = calculate(PayrollInput(JUN_Q1, make_contract(), absence), make_tables(), v1)
    july = calculate(PayrollInput(JUL_Q1, make_contract(), absence), make_tables(), v2)
    assert line(june, "ABSENCE_UNJUSTIFIED").amount == Decimal("-1258.92")
    assert line(june, "ABSENCE_UNJUSTIFIED").policy_version == "POL-V1"
    assert line(july, "ABSENCE_UNJUSTIFIED").amount == Decimal("0.00")
    assert line(july, "ABSENCE_UNJUSTIFIED").policy_version == "POL-V2"
    # Reproducible: recalcular junio con su política da exactamente lo mismo.
    assert calculate(PayrollInput(JUN_Q1, make_contract(), absence), make_tables(), v1) == june


def test_politica_no_vigente_en_la_fecha_de_pago_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    v1 = make_policy(**V1, absence_rules=(unj("0"),))
    with pytest.raises(PayrollConfigError, match="POL-V1"):
        calculate(PayrollInput(JUL_Q1, make_contract()), make_tables(), v1)


def test_tablas_no_vigentes_en_la_fecha_de_pago_es_error(
    make_policy: MakePolicy, make_contract: MakeContract, make_tables: MakeTables
) -> None:
    # La tabla de mínimos de las fixtures empieza el 2026-02-01.
    january = biweekly(date(2026, 1, 1), date(2026, 1, 15))
    with pytest.raises(PayrollConfigError):
        calculate(PayrollInput(january, make_contract()), make_tables(), make_policy())


# =========================================================================== properties

_FIXTURES_OK = settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
salaries = st.decimals(min_value=Decimal("29988.00"), max_value=Decimal("1000000.00"), places=2)
ratios = st.decimals(min_value=Decimal("0"), max_value=Decimal("1"), places=2)
half_days = st.integers(min_value=1, max_value=30).map(lambda n: Decimal(n) / 2)  # 0.5 .. 15
methods = st.sampled_from([CAL, COM])


@_FIXTURES_OK
@given(salary=salaries, days=half_days, ratio=ratios, method=methods)
def test_prop_salario_ordinario_y_bruto_nunca_negativos(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    salary: Decimal,
    days: Decimal,
    ratio: Decimal,
    method: ProrationMethod,
) -> None:
    inputs = PayrollInput(MAR_Q1, make_contract(monthly_salary=salary), (Absence(UNJ, days),))
    policy = make_policy(proration_method=method, absence_rules=(AbsenceRule(UNJ, ratio),))
    result = calculate(inputs, make_tables(), policy)
    ordinary = line(result, "ORDINARY_SALARY").amount
    # Cota: la quincena completa ya redondeada (salary / 2 puede tener 3 decimales).
    assert Decimal("0") <= ordinary <= round_line(salary / 2)
    assert result.gross >= 0


@_FIXTURES_OK
@given(salary=salaries, days=half_days, method=methods)
def test_prop_con_ratio_1_las_ausencias_no_cambian_el_bruto(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    salary: Decimal,
    days: Decimal,
    method: ProrationMethod,
) -> None:
    contract = make_contract(monthly_salary=salary)
    policy = make_policy(proration_method=method, absence_rules=(unj("1"),))
    with_absence = calculate(
        PayrollInput(MAR_Q1, contract, (Absence(UNJ, days),)), make_tables(), policy
    )
    without = calculate(PayrollInput(MAR_Q1, contract), make_tables(), policy)
    assert with_absence.gross == without.gross


@_FIXTURES_OK
@given(salary=salaries, period=st.sampled_from([MAR, MAR_Q1, MAR_Q2, FEB, FEB_Q2]))
def test_prop_periodos_completos_dan_lo_mismo_con_ambos_metodos(
    make_policy: MakePolicy,
    make_contract: MakeContract,
    make_tables: MakeTables,
    salary: Decimal,
    period: PayPeriod,
) -> None:
    contract = make_contract(monthly_salary=salary)
    cal = calculate(
        PayrollInput(period, contract), make_tables(), make_policy(proration_method=CAL)
    )
    com = calculate(
        PayrollInput(period, contract), make_tables(), make_policy(proration_method=COM)
    )
    assert cal.gross == com.gross
