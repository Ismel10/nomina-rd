"""Tests de nomina.engine.rules: resolución en cascada y validación de la política.

Cascada (plan aprobado del paso 2): contrato → grupo del contrato → empresa → error.
Datos ficticios.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest

from nomina.engine.errors import PayrollConfigError
from nomina.engine.models import (
    AbsenceRule,
    ContractInput,
    EmployeeGroup,
    LaborLimitsTable,
    PayrollPolicy,
    RateTables,
    RuleSource,
)
from nomina.engine.rules import resolve_absence_ratio, validate_policy

UNJUSTIFIED = "UNJUSTIFIED"

COMPANY_RULE = AbsenceRule(UNJUSTIFIED, Decimal("0"))  # la empresa descuenta completa
GROUP_RULE = AbsenceRule(UNJUSTIFIED, Decimal("0.5"))  # Operativo: paga la mitad
CONTRACT_RULE = AbsenceRule(UNJUSTIFIED, Decimal("1"))  # excepción del contrato: paga completa
OPERATIVO = EmployeeGroup("OPERATIVO", "Operativo", (GROUP_RULE,))
GERENCIA = EmployeeGroup("GERENCIA", "Gerencia")  # sin regla propia


# --------------------------------------------------------------------------- cascada


def test_cascada_a_sin_grupo_usa_la_regla_de_la_empresa(
    make_policy: Callable[..., PayrollPolicy], make_contract: Callable[..., ContractInput]
) -> None:
    policy = make_policy(absence_rules=(COMPANY_RULE,), groups=(OPERATIVO,))
    resolved = resolve_absence_ratio(UNJUSTIFIED, make_contract(), policy)
    assert resolved.pay_ratio == Decimal("0")
    assert resolved.source is RuleSource.COMPANY


def test_cascada_b_grupo_con_regla_propia_usa_la_del_grupo(
    make_policy: Callable[..., PayrollPolicy], make_contract: Callable[..., ContractInput]
) -> None:
    policy = make_policy(absence_rules=(COMPANY_RULE,), groups=(OPERATIVO,))
    resolved = resolve_absence_ratio(UNJUSTIFIED, make_contract(group_code="OPERATIVO"), policy)
    assert resolved.pay_ratio == Decimal("0.5")
    assert resolved.source is RuleSource.GROUP


def test_cascada_c_excepcion_del_contrato_gana_sobre_grupo_y_empresa(
    make_policy: Callable[..., PayrollPolicy], make_contract: Callable[..., ContractInput]
) -> None:
    policy = make_policy(absence_rules=(COMPANY_RULE,), groups=(OPERATIVO,))
    contract = make_contract(group_code="OPERATIVO", absence_rules=(CONTRACT_RULE,))
    resolved = resolve_absence_ratio(UNJUSTIFIED, contract, policy)
    assert resolved.pay_ratio == Decimal("1")
    assert resolved.source is RuleSource.CONTRACT


def test_cascada_d_sin_ninguna_regla_es_error_y_nombra_el_tipo(
    make_policy: Callable[..., PayrollPolicy], make_contract: Callable[..., ContractInput]
) -> None:
    policy = make_policy(absence_rules=(), groups=(OPERATIVO, GERENCIA))
    with pytest.raises(PayrollConfigError, match=UNJUSTIFIED):
        resolve_absence_ratio(UNJUSTIFIED, make_contract(group_code="GERENCIA"), policy)


def test_cascada_grupo_sin_regla_para_el_tipo_cae_a_la_empresa(
    make_policy: Callable[..., PayrollPolicy], make_contract: Callable[..., ContractInput]
) -> None:
    policy = make_policy(absence_rules=(COMPANY_RULE,), groups=(GERENCIA,))
    resolved = resolve_absence_ratio(UNJUSTIFIED, make_contract(group_code="GERENCIA"), policy)
    assert resolved.source is RuleSource.COMPANY


def test_cascada_regla_del_contrato_para_otro_tipo_no_aplica(
    make_policy: Callable[..., PayrollPolicy], make_contract: Callable[..., ContractInput]
) -> None:
    policy = make_policy(absence_rules=(COMPANY_RULE,))
    contract = make_contract(absence_rules=(AbsenceRule("MEDICAL", Decimal("1")),))
    resolved = resolve_absence_ratio(UNJUSTIFIED, contract, policy)
    assert resolved.source is RuleSource.COMPANY


def test_cascada_grupo_inexistente_es_error_de_configuracion(
    make_policy: Callable[..., PayrollPolicy], make_contract: Callable[..., ContractInput]
) -> None:
    policy = make_policy(absence_rules=(COMPANY_RULE,), groups=(OPERATIVO,))
    with pytest.raises(PayrollConfigError, match="NO_EXISTE"):
        resolve_absence_ratio(UNJUSTIFIED, make_contract(group_code="NO_EXISTE"), policy)


# --------------------------------------------------------------------------- validate_policy


def test_validate_policy_acepta_una_politica_valida(
    make_policy: Callable[..., PayrollPolicy], make_tables: Callable[..., RateTables]
) -> None:
    validate_policy(make_policy(workday_hours=Decimal("8")), make_tables())


def test_validate_policy_rechaza_jornada_mayor_al_maximo_legal(
    make_policy: Callable[..., PayrollPolicy], make_tables: Callable[..., RateTables]
) -> None:
    # Máximo diario de la tabla: 8 h (Ley 16-92 art. 147, fuentes.md#jornada).
    with pytest.raises(PayrollConfigError):
        validate_policy(make_policy(workday_hours=Decimal("8.5")), make_tables())


def test_validate_policy_usa_el_maximo_de_la_tabla_recibida(
    make_policy: Callable[..., PayrollPolicy], make_tables: Callable[..., RateTables]
) -> None:
    # Con otra tabla (FICTICIA) el límite cambia: el motor no tiene el 8 escrito en el código.
    limits = LaborLimitsTable("LL-FICTICIA", date(2000, 1, 1), None, Decimal("9"), Decimal("44"))
    validate_policy(make_policy(workday_hours=Decimal("8.5")), make_tables(labor_limits=limits))


def test_validate_policy_rechaza_categoria_de_minimo_inexistente(
    make_policy: Callable[..., PayrollPolicy], make_tables: Callable[..., RateTables]
) -> None:
    with pytest.raises(PayrollConfigError, match="ZONAS_FRANCAS"):
        validate_policy(make_policy(minimum_wage_category="ZONAS_FRANCAS"), make_tables())
