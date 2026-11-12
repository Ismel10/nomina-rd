"""Tests de nomina.engine.proration: forma del periodo y prorrateo del salario fijo (ADR 0002).

Salario mensual FICTICIO RD$30,000.00 (quincena RD$15,000.00). Los montos esperados se calcularon
a mano (plan aprobado del 2a-2) y se comparan con `round_line` del valor exacto: el prorrateo no
redondea, eso lo hace la línea en `calculate`.

CAL = CALENDAR_FRACTION (días calendario); COM = COMMERCIAL_30 (el 31 y el último día del mes = 30).
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest

from nomina.engine.errors import PayrollInputError
from nomina.engine.models import ContractInput, PayFrequency, PayPeriod, ProrationMethod
from nomina.engine.money import round_line
from nomina.engine.proration import (
    period_days,
    period_salary,
    prorated_salary,
    service_days,
    validate_period_shape,
)

CAL = ProrationMethod.CALENDAR_FRACTION
COM = ProrationMethod.COMMERCIAL_30


def biweekly(start: date, end: date) -> PayPeriod:
    return PayPeriod(start, end, end, PayFrequency.BIWEEKLY)


def monthly(start: date, end: date) -> PayPeriod:
    return PayPeriod(start, end, end, PayFrequency.MONTHLY)


MAR = monthly(date(2026, 3, 1), date(2026, 3, 31))
MAR_Q1 = biweekly(date(2026, 3, 1), date(2026, 3, 15))
MAR_Q2 = biweekly(date(2026, 3, 16), date(2026, 3, 31))
FEB = monthly(date(2026, 2, 1), date(2026, 2, 28))
FEB_Q2 = biweekly(date(2026, 2, 16), date(2026, 2, 28))
FEB_Q2_BISIESTO = biweekly(date(2028, 2, 16), date(2028, 2, 29))

ANTES = date(2025, 1, 1)  # ingreso anterior a todos los periodos

# --------------------------------------------------------------------------- forma del periodo


@pytest.mark.parametrize(
    "period",
    [
        biweekly(date(2026, 3, 1), date(2026, 3, 15)),
        biweekly(date(2026, 3, 16), date(2026, 3, 31)),
        biweekly(date(2026, 4, 16), date(2026, 4, 30)),
        biweekly(date(2026, 2, 16), date(2026, 2, 28)),
        biweekly(date(2028, 2, 16), date(2028, 2, 29)),
        monthly(date(2026, 3, 1), date(2026, 3, 31)),
        monthly(date(2026, 2, 1), date(2026, 2, 28)),
        monthly(date(2026, 4, 1), date(2026, 4, 30)),
    ],
    ids=lambda p: f"{p.frequency.value}-{p.start}-{p.end}",
)
def test_forma_de_periodo_valida(period: PayPeriod) -> None:
    validate_period_shape(period)


@pytest.mark.parametrize(
    "period",
    [
        biweekly(date(2026, 3, 2), date(2026, 3, 16)),  # no empieza el 1 ni el 16
        biweekly(date(2026, 3, 1), date(2026, 3, 14)),  # primera quincena incompleta
        biweekly(date(2026, 3, 16), date(2026, 3, 30)),  # marzo termina el 31
        biweekly(date(2028, 2, 16), date(2028, 2, 28)),  # febrero bisiesto termina el 29
        biweekly(date(2026, 3, 16), date(2026, 4, 15)),  # cruza de mes
        monthly(date(2026, 3, 1), date(2026, 3, 30)),  # mes incompleto
        monthly(date(2026, 3, 1), date(2026, 3, 15)),  # quincena declarada como mensual
        monthly(date(2026, 3, 1), date(2026, 4, 30)),  # dos meses
    ],
    ids=lambda p: f"{p.frequency.value}-{p.start}-{p.end}",
)
def test_forma_de_periodo_invalida_es_error(period: PayPeriod) -> None:
    with pytest.raises(PayrollInputError):
        validate_period_shape(period)


def test_service_days_valida_la_forma_del_periodo(
    make_contract: Callable[..., ContractInput],
) -> None:
    with pytest.raises(PayrollInputError):
        service_days(biweekly(date(2026, 3, 2), date(2026, 3, 16)), make_contract(), CAL)


# --------------------------------------------------------------------------- días del periodo


@pytest.mark.parametrize(
    ("period", "method", "expected"),
    [
        (MAR, CAL, 31),
        (MAR, COM, 30),
        (MAR_Q1, CAL, 15),
        (MAR_Q1, COM, 15),
        (MAR_Q2, CAL, 16),
        (MAR_Q2, COM, 15),
        (FEB, CAL, 28),
        (FEB, COM, 30),
        (FEB_Q2, CAL, 13),
        (FEB_Q2, COM, 15),
        (FEB_Q2_BISIESTO, CAL, 14),
        (FEB_Q2_BISIESTO, COM, 15),
    ],
)
def test_period_days(period: PayPeriod, method: ProrationMethod, expected: int) -> None:
    assert period_days(period, method) == expected


# --------------------------------------------------------------------------- salario del periodo


def test_period_salary_mensual_y_quincenal(make_contract: Callable[..., ContractInput]) -> None:
    contract = make_contract(monthly_salary=Decimal("30000.00"))
    assert period_salary(MAR, contract) == Decimal("30000.00")
    assert period_salary(MAR_Q1, contract) == Decimal("15000.00")


# --------------------------------------------------------------------------- casos a mano

# (id, periodo, ingreso, salida, método, días de servicio, monto esperado tras round_line)
HAND_CASES = [
    ("1-marzo-completo", MAR, ANTES, None, CAL, 31, "30000.00"),
    ("1-marzo-completo", MAR, ANTES, None, COM, 30, "30000.00"),
    ("2-q1-completa", MAR_Q1, ANTES, None, CAL, 15, "15000.00"),
    ("2-q1-completa", MAR_Q1, ANTES, None, COM, 15, "15000.00"),
    ("3-ingreso-6", MAR_Q1, date(2026, 3, 6), None, CAL, 10, "10000.00"),
    ("3-ingreso-6", MAR_Q1, date(2026, 3, 6), None, COM, 10, "10000.00"),
    ("4-salida-10", MAR_Q1, ANTES, date(2026, 3, 10), CAL, 10, "10000.00"),
    ("4-salida-10", MAR_Q1, ANTES, date(2026, 3, 10), COM, 10, "10000.00"),
    ("5-ingreso-3-salida-12", MAR_Q1, date(2026, 3, 3), date(2026, 3, 12), CAL, 10, "10000.00"),
    ("5-ingreso-3-salida-12", MAR_Q1, date(2026, 3, 3), date(2026, 3, 12), COM, 10, "10000.00"),
    ("6-salio-28-feb", MAR_Q1, ANTES, date(2026, 2, 28), CAL, 0, "0.00"),
    ("6-salio-28-feb", MAR_Q1, ANTES, date(2026, 2, 28), COM, 0, "0.00"),
    ("7-q2-marzo-completa", MAR_Q2, ANTES, None, CAL, 16, "15000.00"),
    ("7-q2-marzo-completa", MAR_Q2, ANTES, None, COM, 15, "15000.00"),
    ("8-q2-marzo-ingreso-24", MAR_Q2, date(2026, 3, 24), None, CAL, 8, "7500.00"),
    ("8-q2-marzo-ingreso-24", MAR_Q2, date(2026, 3, 24), None, COM, 7, "7000.00"),
    ("9-q2-marzo-salida-30", MAR_Q2, ANTES, date(2026, 3, 30), CAL, 15, "14062.50"),
    ("9-q2-marzo-salida-30", MAR_Q2, ANTES, date(2026, 3, 30), COM, 15, "15000.00"),
    ("10-febrero-ingreso-15", FEB, date(2026, 2, 15), None, CAL, 14, "15000.00"),
    ("10-febrero-ingreso-15", FEB, date(2026, 2, 15), None, COM, 16, "16000.00"),
    ("11-q2-febrero-ingreso-20", FEB_Q2, date(2026, 2, 20), None, CAL, 9, "10384.62"),
    ("11-q2-febrero-ingreso-20", FEB_Q2, date(2026, 2, 20), None, COM, 11, "11000.00"),
    ("12-q2-febrero-completa", FEB_Q2, ANTES, None, CAL, 13, "15000.00"),
    ("12-q2-febrero-completa", FEB_Q2, ANTES, None, COM, 15, "15000.00"),
]


@pytest.mark.parametrize(
    ("case", "period", "start", "end", "method", "days", "amount"),
    HAND_CASES,
    ids=[f"{c[0]}-{c[4].name}" for c in HAND_CASES],
)
def test_casos_a_mano(
    make_contract: Callable[..., ContractInput],
    case: str,
    period: PayPeriod,
    start: date,
    end: date | None,
    method: ProrationMethod,
    days: int,
    amount: str,
) -> None:
    contract = make_contract(start_date=start, end_date=end)
    assert service_days(period, contract, method) == days
    assert round_line(prorated_salary(period, contract, method)) == Decimal(amount)


def test_prorrateo_no_redondea(make_contract: Callable[..., ContractInput]) -> None:
    """Caso 11 CAL: 15,000.00 x 9/13 = 10,384.615384... se devuelve exacto, sin redondear."""
    contract = make_contract(start_date=date(2026, 2, 20))
    assert prorated_salary(FEB_Q2, contract, CAL) == Decimal("15000.00") * 9 / 13


# --------------------------------------------------------------------------- bordes


@pytest.mark.parametrize(
    ("method", "days", "amount"),
    [
        (CAL, 1, "1071.43"),  # 15,000 x 1/14 = 1,071.428571...
        (COM, 1, "1000.00"),  # 29-feb (último día) vale 30: 30..30 = 1 día; 15,000 x 1/15
    ],
)
def test_bisiesto_ingreso_el_29_de_febrero(
    make_contract: Callable[..., ContractInput], method: ProrationMethod, days: int, amount: str
) -> None:
    contract = make_contract(start_date=date(2028, 2, 29))
    assert service_days(FEB_Q2_BISIESTO, contract, method) == days
    assert round_line(prorated_salary(FEB_Q2_BISIESTO, contract, method)) == Decimal(amount)


@pytest.mark.parametrize(
    ("method", "days", "amount"),
    [
        (CAL, 1, "937.50"),  # 15,000 x 1/16
        (COM, 1, "1000.00"),  # el 31 vale 30: 30..30 = 1 día
    ],
)
def test_ingreso_el_31(
    make_contract: Callable[..., ContractInput], method: ProrationMethod, days: int, amount: str
) -> None:
    contract = make_contract(start_date=date(2026, 3, 31))
    assert service_days(MAR_Q2, contract, method) == days
    assert round_line(prorated_salary(MAR_Q2, contract, method)) == Decimal(amount)


@pytest.mark.parametrize(
    ("end", "days", "amount"),
    [
        (date(2026, 2, 27), 12, "12000.00"),  # índices 16..27 = 12 días; 15,000 x 12/15
        (date(2026, 2, 28), 15, "15000.00"),  # el 28 es el último día del mes y vale 30: 16..30
    ],
)
def test_commercial_30_salto_de_febrero_al_salir_el_ultimo_dia(
    make_contract: Callable[..., ContractInput], end: date, days: int, amount: str
) -> None:
    """Salto conocido de COMMERCIAL_30 (ADR 0002, sección Consecuencias): en febrero, salir el
    día 27 paga 12/15 y salir el 28 (último día) paga 15/15, porque el último día del mes vale 30.
    Es propio de la convención aprobada, no un error."""
    contract = make_contract(end_date=end)
    assert service_days(FEB_Q2, contract, COM) == days
    assert round_line(prorated_salary(FEB_Q2, contract, COM)) == Decimal(amount)


@pytest.mark.parametrize("method", [CAL, COM])
def test_contrato_que_empieza_despues_del_periodo_no_tiene_dias(
    make_contract: Callable[..., ContractInput], method: ProrationMethod
) -> None:
    contract = make_contract(start_date=date(2026, 4, 1))
    assert service_days(MAR_Q2, contract, method) == 0
    assert prorated_salary(MAR_Q2, contract, method) == 0


@pytest.mark.parametrize("method", [CAL, COM])
def test_salida_el_primer_dia_del_periodo_cuenta_un_dia(
    make_contract: Callable[..., ContractInput], method: ProrationMethod
) -> None:
    contract = make_contract(end_date=date(2026, 3, 16))
    assert service_days(MAR_Q2, contract, method) == 1
