"""Resolución de reglas configurables y validación de la política contra las tablas legales.

La cascada busca la regla más específica (plan aprobado del paso 2):
contrato → grupo del contrato → empresa → error. Nunca se usa un valor por defecto inventado.
"""

from dataclasses import dataclass
from decimal import Decimal

from nomina.engine.errors import PayrollConfigError
from nomina.engine.models import ContractInput, PayrollPolicy, RateTables, RuleSource


@dataclass(frozen=True)
class ResolvedRule:
    """Regla resuelta y el nivel del que salió (para la trazabilidad de la línea)."""

    pay_ratio: Decimal
    source: RuleSource


def resolve_absence_ratio(
    absence_type: str, contract: ContractInput, policy: PayrollPolicy
) -> ResolvedRule:
    """Porcentaje de pago de `absence_type` para este contrato según la cascada.

    Raises:
        PayrollConfigError: si el contrato apunta a un grupo que no existe en la política, o si
            ningún nivel tiene regla para el tipo de ausencia.
    """
    contract_rule = contract.absence_rule(absence_type)
    if contract_rule is not None:
        return ResolvedRule(contract_rule.pay_ratio, RuleSource.CONTRACT)

    if contract.group_code is not None:
        group = policy.group(contract.group_code)
        if group is None:
            raise PayrollConfigError(
                f"{contract.contract_id}: el grupo '{contract.group_code}' no existe en la "
                f"política {policy.version}"
            )
        group_rule = group.absence_rule(absence_type)
        if group_rule is not None:
            return ResolvedRule(group_rule.pay_ratio, RuleSource.GROUP)

    company_rule = policy.absence_rule(absence_type)
    if company_rule is not None:
        return ResolvedRule(company_rule.pay_ratio, RuleSource.COMPANY)

    raise PayrollConfigError(
        f"{contract.contract_id}: no hay regla para el tipo de ausencia '{absence_type}' "
        f"(ni en el contrato, ni en su grupo, ni en la política {policy.version})"
    )


def validate_policy(policy: PayrollPolicy, tables: RateTables) -> None:
    """Valida la política de la empresa contra las tablas legales vigentes.

    Raises:
        PayrollConfigError: si la jornada supera el máximo diario legal o si la categoría de
            salario mínimo no existe en la tabla.
    """
    if policy.workday_hours > tables.labor_limits.max_daily_hours:
        raise PayrollConfigError(
            f"{policy.version}: workday_hours supera el máximo diario legal "
            f"({tables.labor_limits.version})"
        )
    if tables.minimum_wages.monthly_minimum(policy.minimum_wage_category) is None:
        raise PayrollConfigError(
            f"{policy.version}: la categoría de salario mínimo "
            f"'{policy.minimum_wage_category}' no existe en {tables.minimum_wages.version}"
        )
