"""Modelos del motor de nómina: lo que `calculate` recibe y devuelve.

Todos son dataclasses inmutables (`frozen=True`) con validación al construirse. Las colecciones
se guardan como tuplas (un dict dentro de una dataclass frozen seguiría siendo mutable). Montos,
tasas y días son `Decimal`; un `float` es `TypeError`.

La configuración de cada empresa (`PayrollPolicy`, `EmployeeGroup`, `AbsenceRule`) y las tablas
legales (`RateTables`) llegan **como datos**: el motor no tiene valores de negocio escritos en el
código. Los mensajes de error nunca incluyen montos (AGENTS.md §3.6).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from nomina.engine.errors import PayrollConfigError, PayrollInputError
from nomina.engine.money import is_rounded, sum_lines

# --------------------------------------------------------------------------- enums


class PayScheme(Enum):
    """Esquema de pago del contrato. `HOURLY` (por horas) se agrega en el paso 2b."""

    FIXED_SALARY = "fixed_salary"


class PayFrequency(Enum):
    BIWEEKLY = "biweekly"  # quincenal
    MONTHLY = "monthly"


class ConceptKind(Enum):
    EARNING = "earning"  # ingreso (percepción); una ausencia descontada es un EARNING negativo
    DEDUCTION = "deduction"  # descuento al empleado
    EMPLOYER_CONTRIBUTION = "employer_contribution"  # aporte patronal; no afecta el neto


class RuleSource(Enum):
    """Nivel del que salió una regla resuelta en cascada."""

    CONTRACT = "contract"
    GROUP = "group"
    COMPANY = "company"


class ProrationMethod(Enum):
    """Método de prorrateo por ingreso o salida dentro del periodo (ADR 0002)."""

    CALENDAR_FRACTION = "calendar_fraction"
    COMMERCIAL_30 = "commercial_30"


class LeaveCategory(Enum):
    """Categoría legal de una licencia (docs/normativa/fuentes.md#licencias)."""

    EMPLOYER_PAID = "employer_paid"  # pagada por el empleador (p. ej. art. 54)
    SUBSIDIZED = "subsidized"  # cubierta por subsidio SISALRIL; fuera del MVP


# --------------------------------------------------------------------------- validación


def _decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        raise TypeError(f"{field}: se esperaba Decimal, no {type(value).__name__}")
    return value


def _positive(value: object, field: str, error: type[ValueError]) -> Decimal:
    number = _decimal(value, field)
    if not number.is_finite() or number <= 0:
        raise error(f"{field}: debe ser un número finito mayor que cero")
    return number


def _code(value: str, field: str, error: type[ValueError]) -> str:
    if not value.strip():
        raise error(f"{field}: no puede estar vacío")
    return value


def _unique(codes: Iterable[str], what: str, error: type[ValueError]) -> None:
    seen: set[str] = set()
    for code in codes:
        if code in seen:
            raise error(f"{what} duplicado: '{code}'")
        seen.add(code)


def _freeze(instance: object, field: str) -> None:
    """Convierte la colección del campo en tupla (dentro de __post_init__ de una frozen)."""
    object.__setattr__(instance, field, tuple(getattr(instance, field)))


# --------------------------------------------------------------------------- vigencia


@dataclass(frozen=True)
class _Versioned:
    """Dato con versión y vigencia `[valid_from, valid_to]`, ambos extremos incluidos."""

    version: str
    valid_from: date
    valid_to: date | None

    def __post_init__(self) -> None:
        _code(self.version, "version", PayrollConfigError)
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise PayrollConfigError(f"{self.version}: valid_to es anterior a valid_from")

    def covers(self, on: date) -> bool:
        """Indica si la versión está vigente en la fecha `on`."""
        return self.valid_from <= on and (self.valid_to is None or on <= self.valid_to)


# --------------------------------------------------------------------------- reglas y novedades


@dataclass(frozen=True)
class AbsenceRule:
    """Porcentaje de pago de un tipo de ausencia: 1 = se paga completa, 0 = se descuenta completa,
    0.5 = se paga la mitad. El tipo es un código configurable por empresa."""

    absence_type: str
    pay_ratio: Decimal

    def __post_init__(self) -> None:
        _code(self.absence_type, "AbsenceRule.absence_type", PayrollConfigError)
        ratio = _decimal(self.pay_ratio, "AbsenceRule.pay_ratio")
        if not ratio.is_finite() or not (0 <= ratio <= 1):
            raise PayrollConfigError(
                f"AbsenceRule '{self.absence_type}': pay_ratio debe estar entre 0 y 1"
            )


def _find_rule(rules: tuple[AbsenceRule, ...], absence_type: str) -> AbsenceRule | None:
    return next((r for r in rules if r.absence_type == absence_type), None)


@dataclass(frozen=True)
class Absence:
    """Novedad resumida del periodo: días de ausencia de un tipo (admite medios días)."""

    absence_type: str
    days: Decimal

    def __post_init__(self) -> None:
        _code(self.absence_type, "Absence.absence_type", PayrollInputError)
        _positive(self.days, f"Absence '{self.absence_type}'.days", PayrollInputError)


# --------------------------------------------------------------------------- periodo y contrato


@dataclass(frozen=True)
class PayPeriod:
    start: date
    end: date
    pay_date: date
    frequency: PayFrequency

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise PayrollInputError("PayPeriod: end es anterior a start")


@dataclass(frozen=True)
class ContractInput:
    """Contrato tal como lo necesita el motor. `monthly_salary` es siempre mensual para
    `FIXED_SALARY` (la quincena es mensual ÷ 2). `absence_rules` son excepciones del contrato,
    primer nivel de la cascada."""

    contract_id: str
    scheme: PayScheme
    monthly_salary: Decimal
    start_date: date
    end_date: date | None = None
    group_code: str | None = None
    absence_rules: tuple[AbsenceRule, ...] = ()

    def __post_init__(self) -> None:
        _positive(self.monthly_salary, "ContractInput.monthly_salary", PayrollInputError)
        if self.end_date is not None and self.end_date < self.start_date:
            raise PayrollInputError(f"{self.contract_id}: end_date es anterior a start_date")
        _freeze(self, "absence_rules")
        _unique(
            (r.absence_type for r in self.absence_rules),
            f"{self.contract_id}: regla de ausencia",
            PayrollConfigError,
        )

    def absence_rule(self, absence_type: str) -> AbsenceRule | None:
        return _find_rule(self.absence_rules, absence_type)


@dataclass(frozen=True)
class PayrollInput:
    period: PayPeriod
    contract: ContractInput
    absences: tuple[Absence, ...] = ()

    def __post_init__(self) -> None:
        _freeze(self, "absences")
        _unique((a.absence_type for a in self.absences), "Novedad de ausencia", PayrollInputError)


# --------------------------------------------------------------------------- política de la empresa


@dataclass(frozen=True)
class EmployeeGroup:
    """Grupo configurable por empresa (jerarquía, departamento, turno…). Segundo nivel de la
    cascada."""

    code: str
    name: str
    absence_rules: tuple[AbsenceRule, ...] = ()

    def __post_init__(self) -> None:
        _code(self.code, "EmployeeGroup.code", PayrollConfigError)
        _code(self.name, f"EmployeeGroup '{self.code}'.name", PayrollConfigError)
        _freeze(self, "absence_rules")
        _unique(
            (r.absence_type for r in self.absence_rules),
            f"Grupo '{self.code}': regla de ausencia",
            PayrollConfigError,
        )

    def absence_rule(self, absence_type: str) -> AbsenceRule | None:
        return _find_rule(self.absence_rules, absence_type)


@dataclass(frozen=True)
class PayrollPolicy(_Versioned):
    """Política de pago de una empresa, con vigencia. Se elige por la fecha de pago del periodo.

    `absence_rules` son las reglas generales de la empresa (último nivel de la cascada).
    `minimum_wage_category` indica qué salario mínimo de `MinimumWageTable` aplica.
    """

    daily_salary_divisor: Decimal
    workday_hours: Decimal
    proration_method: ProrationMethod
    minimum_wage_category: str
    absence_rules: tuple[AbsenceRule, ...] = ()
    groups: tuple[EmployeeGroup, ...] = ()

    def __post_init__(self) -> None:
        super().__post_init__()
        _positive(
            self.daily_salary_divisor, "PayrollPolicy.daily_salary_divisor", PayrollConfigError
        )
        _positive(self.workday_hours, "PayrollPolicy.workday_hours", PayrollConfigError)
        _code(self.minimum_wage_category, "PayrollPolicy.minimum_wage_category", PayrollConfigError)
        _freeze(self, "absence_rules")
        _freeze(self, "groups")
        _unique(
            (r.absence_type for r in self.absence_rules),
            f"{self.version}: regla de ausencia",
            PayrollConfigError,
        )
        _unique((g.code for g in self.groups), f"{self.version}: grupo", PayrollConfigError)

    def absence_rule(self, absence_type: str) -> AbsenceRule | None:
        return _find_rule(self.absence_rules, absence_type)

    def group(self, code: str) -> EmployeeGroup | None:
        return next((g for g in self.groups if g.code == code), None)


# --------------------------------------------------------------------------- tablas legales


@dataclass(frozen=True)
class MinimumWage:
    """Salario mínimo **mensual** de una categoría (el valor legal es el mensual)."""

    category: str
    monthly_amount: Decimal

    def __post_init__(self) -> None:
        _code(self.category, "MinimumWage.category", PayrollConfigError)
        _positive(self.monthly_amount, f"MinimumWage '{self.category}'", PayrollConfigError)


@dataclass(frozen=True)
class MinimumWageTable(_Versioned):
    minimums: tuple[MinimumWage, ...]

    def __post_init__(self) -> None:
        super().__post_init__()
        _freeze(self, "minimums")
        _unique(
            (m.category for m in self.minimums), f"{self.version}: categoría", PayrollConfigError
        )

    def monthly_minimum(self, category: str) -> Decimal | None:
        found = next((m for m in self.minimums if m.category == category), None)
        return None if found is None else found.monthly_amount


@dataclass(frozen=True)
class LaborLimitsTable(_Versioned):
    """Jornada máxima legal (docs/normativa/fuentes.md#jornada)."""

    max_daily_hours: Decimal
    max_weekly_hours: Decimal

    def __post_init__(self) -> None:
        super().__post_init__()
        _positive(self.max_daily_hours, f"{self.version}.max_daily_hours", PayrollConfigError)
        _positive(self.max_weekly_hours, f"{self.version}.max_weekly_hours", PayrollConfigError)


@dataclass(frozen=True)
class LegalLeave:
    """Licencia definida por ley. Las pagadas por el empleador tienen un máximo de días."""

    code: str
    category: LeaveCategory
    max_days: Decimal | None

    def __post_init__(self) -> None:
        _code(self.code, "LegalLeave.code", PayrollConfigError)
        if self.max_days is not None:
            _positive(self.max_days, f"LegalLeave '{self.code}'.max_days", PayrollConfigError)
        if self.category is LeaveCategory.EMPLOYER_PAID and self.max_days is None:
            raise PayrollConfigError(f"LegalLeave '{self.code}': falta max_days")


@dataclass(frozen=True)
class LegalLeaveTable(_Versioned):
    leaves: tuple[LegalLeave, ...]

    def __post_init__(self) -> None:
        super().__post_init__()
        _freeze(self, "leaves")
        _unique((lv.code for lv in self.leaves), f"{self.version}: licencia", PayrollConfigError)

    def leave(self, code: str) -> LegalLeave | None:
        return next((lv for lv in self.leaves if lv.code == code), None)


@dataclass(frozen=True)
class RateTables:
    """Conjunto de tablas legales vigentes en la fecha de pago. Cada tabla tiene su propia
    versión y vigencia; los pasos 3 a 5 agregan TSS, ISR y recargos."""

    minimum_wages: MinimumWageTable
    labor_limits: LaborLimitsTable
    legal_leaves: LegalLeaveTable

    def covers(self, on: date) -> bool:
        """El conjunto es válido en `on` solo si todas sus tablas lo están."""
        return all(t.covers(on) for t in (self.minimum_wages, self.labor_limits, self.legal_leaves))


# --------------------------------------------------------------------------- resultado


@dataclass(frozen=True)
class PayrollLine:
    """Línea del volante con trazabilidad. `amount` debe venir de `round_line`."""

    code: str
    kind: ConceptKind
    quantity: Decimal | None
    base: Decimal
    rate: Decimal | None
    amount: Decimal
    rule_source: RuleSource | None
    policy_version: str
    table_version: str | None

    def __post_init__(self) -> None:
        if not is_rounded(self.amount):
            raise ValueError(f"PayrollLine '{self.code}': amount debe pasar por round_line")


@dataclass(frozen=True)
class PayrollResult:
    """Resultado del cálculo de un contrato en un periodo. Los totales son la suma de las líneas
    ya redondeadas (`sum_lines`); nunca se redondean aparte (ADR 0001)."""

    contract_id: str
    period: PayPeriod
    lines: tuple[PayrollLine, ...]

    def __post_init__(self) -> None:
        _freeze(self, "lines")

    def _total(self, kind: ConceptKind) -> Decimal:
        return sum_lines(line.amount for line in self.lines if line.kind is kind)

    @property
    def gross(self) -> Decimal:
        """Bruto: suma de los ingresos (una ausencia descontada es un ingreso negativo)."""
        return self._total(ConceptKind.EARNING)

    @property
    def deductions(self) -> Decimal:
        return self._total(ConceptKind.DEDUCTION)

    @property
    def net(self) -> Decimal:
        return self.gross - self.deductions

    @property
    def employer_contributions(self) -> Decimal:
        return self._total(ConceptKind.EMPLOYER_CONTRIBUTION)
