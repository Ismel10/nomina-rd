# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Agregado
- CI con GitHub Actions (`.github/workflows/ci.yml`): `ruff check`, `ruff format --check`,
  `mypy` y `pytest` del backend en Python 3.12 y 3.13, en cada PR y en cada push a `main` (#3).
- `engine/money.py`: utilidades de dinero del motor (`to_decimal`, `round_line`, `is_rounded`,
  `sum_lines`). Redondeo único `ROUND_HALF_UP` a centavos por línea, según el criterio aceptado en
  el ADR 0001 (#1, #14).
- Modelos del motor (`engine/models.py`), errores (`engine/errors.py`) y reglas (`engine/rules.py`):
  política de pago por empresa con vigencia, grupos de empleados, reglas de ausencia resueltas en
  cascada (contrato → grupo → empresa), tablas legales (salario mínimo mensual, jornada máxima,
  licencias) y validación de la política. ADR 0002: métodos de prorrateo (#15).
- `engine/proration.py`: forma estándar del periodo (quincenas 1–15 y 16–fin de mes; mes
  calendario) y prorrateo del salario fijo con `CALENDAR_FRACTION` y `COMMERCIAL_30` (#17).
- `engine/payroll.py`: `calculate(inputs, tables, policy)` para salario fijo: validaciones de
  vigencia, política, forma del periodo y salario mínimo; ausencias en cascada; licencias del
  art. 54 (días legales al 100 % con `RuleSource.LAW`, exceso por cascada); licencias subsidiadas
  rechazadas con `PayrollUnsupportedError`; tope del descuento por ausencias
  (`ABSENCE_DISCOUNT_CAP`, `RuleSource.SYSTEM`) (#19).
- Métodos de prorrateo `WORKING_DAYS` (días laborables del tramo como dato, sin restar ausencias;
  periodo completo = salario del periodo) y `NO_PRORATION` (salida a mitad aún no soportada), y
  método por contrato por encima del de la empresa. ADR 0003 (#22).

### Cambiado
- `AGENTS.md`: TDD obligatorio también para los casos borde descubiertos al implementar (§7), y
  reglas de no desviarse ni ampliar el alcance sin preguntar (§8) (#5).
- `AGENTS.md`: MVP con pago por horas y configuración por empresa, glosario de la política de pago,
  vigencia de la política y firma `calculate(inputs, tables, policy)` (#15).
- Plan de desarrollo actualizado con el análisis de dos nóminas reales (anonimizado):
  `docs/plan/roadmap.md` y `docs/analisis/nominas-reales-2026.md`. `AGENTS.md`: MVP ampliado
  (días laborados, sin prorrateo, ingresos recurrentes, nocturnidad y feriados, per cápita
  adicional, exención del ISR con auditoría, préstamos con saldo, nómina mensual con adelanto),
  vacaciones con prioridad alta en la fase siguiente y glosario nuevo (#21).
