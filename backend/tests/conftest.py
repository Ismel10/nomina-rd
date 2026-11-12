"""Configuración global de pytest y fábricas compartidas de datos del motor.

Fábricas (skill payroll-calculation-tests): todos los datos de empleados y contratos son
FICTICIOS. Las tablas legales usan valores de docs/normativa/fuentes.md (#jornada,
#salario-minimo, #licencias); los tests no deben depender de que sean "los actuales": cada test
pasa explícitamente las tablas que usa.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from hypothesis import settings

from nomina.engine.models import (
    ContractInput,
    LaborLimitsTable,
    LeaveCategory,
    LegalLeave,
    LegalLeaveTable,
    MinimumWage,
    MinimumWageTable,
    PayrollPolicy,
    PayScheme,
    ProrationMethod,
    RateTables,
)

# Perfil por defecto rápido; `pytest --hypothesis-profile=ci` para más ejemplos.
settings.register_profile("default", max_examples=200)
settings.register_profile("ci", max_examples=2000, deadline=None)
settings.load_profile("default")


@pytest.fixture
def make_policy() -> Callable[..., PayrollPolicy]:
    def _make(**overrides: Any) -> PayrollPolicy:
        fields: dict[str, Any] = {
            "version": "POL-TEST-1",
            "valid_from": date(2026, 1, 1),
            "valid_to": None,
            "daily_salary_divisor": Decimal("23.83"),
            "workday_hours": Decimal("8"),
            "proration_method": ProrationMethod.CALENDAR_FRACTION,
            "minimum_wage_category": "NO_SECTORIZADO_GRANDE",
            "absence_rules": (),
            "groups": (),
        }
        fields.update(overrides)
        return PayrollPolicy(**fields)

    return _make


@pytest.fixture
def make_contract() -> Callable[..., ContractInput]:
    def _make(**overrides: Any) -> ContractInput:
        fields: dict[str, Any] = {
            "contract_id": "CTR-FICTICIO-001",
            "scheme": PayScheme.FIXED_SALARY,
            "monthly_salary": Decimal("30000.00"),
            "start_date": date(2025, 1, 1),
            "end_date": None,
            "group_code": None,
            "absence_rules": (),
        }
        fields.update(overrides)
        return ContractInput(**fields)

    return _make


# Fecha FICTICIA de inicio de vigencia para las tablas de la Ley 16-92 en tests (fuentes.md no
# registra la fecha de promulgación; no hace falta para probar el motor).
_LEY_16_92_DESDE = date(2000, 1, 1)


@pytest.fixture
def make_tables() -> Callable[..., RateTables]:
    def _make(**overrides: Any) -> RateTables:
        fields: dict[str, Any] = {
            "minimum_wages": MinimumWageTable(
                version="CNS-01-2025-2026-02",
                valid_from=date(2026, 2, 1),
                valid_to=None,
                minimums=(MinimumWage("NO_SECTORIZADO_GRANDE", Decimal("29988.00")),),
            ),
            "labor_limits": LaborLimitsTable(
                version="LEY-16-92-ART-147",
                valid_from=_LEY_16_92_DESDE,
                valid_to=None,
                max_daily_hours=Decimal("8"),
                max_weekly_hours=Decimal("44"),
            ),
            "legal_leaves": LegalLeaveTable(
                version="LEY-16-92-ART-54",
                valid_from=_LEY_16_92_DESDE,
                valid_to=None,
                leaves=(
                    LegalLeave("MARRIAGE_LEAVE", LeaveCategory.EMPLOYER_PAID, Decimal("5")),
                    LegalLeave("MATERNITY_LEAVE", LeaveCategory.SUBSIDIZED, None),
                ),
            ),
        }
        fields.update(overrides)
        return RateTables(**fields)

    return _make
