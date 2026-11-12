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

### Cambiado
- `AGENTS.md`: TDD obligatorio también para los casos borde descubiertos al implementar (§7), y
  reglas de no desviarse ni ampliar el alcance sin preguntar (§8) (#5).
- `AGENTS.md`: MVP con pago por horas y configuración por empresa, glosario de la política de pago,
  vigencia de la política y firma `calculate(inputs, tables, policy)` (#15).
