# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Agregado
- CI con GitHub Actions (`.github/workflows/ci.yml`): `ruff check`, `ruff format --check`,
  `mypy` y `pytest` del backend en Python 3.12 y 3.13, en cada PR y en cada push a `main` (#3).
- `engine/money.py`: utilidades de dinero del motor (`to_decimal`, `round_line`, `is_rounded`,
  `sum_lines`). Redondeo único `ROUND_HALF_UP` a centavos por línea, pendiente de verificar contra
  la normativa DGII/TSS (#1).
