---
name: payroll-calculation-tests
description: Usar al escribir o revisar tests del motor de cálculo de nómina (conceptos, ISR, TSS, netos, ajustes) o al reproducir un bug de cálculo. Define fixtures de empleados ficticios, resultados calculados a mano, tolerancia cero en centavos y property-based tests de redondeo.
---

# Tests del motor de cálculo

## Reglas
- **Tolerancia cero:** se compara `Decimal` exacto (`==`). Prohibido usar `pytest.approx`,
  `round()` o `float` en tests de montos.
- **Datos ficticios** siempre: nombres inventados, cédulas `000-0000000-0` o generadas con formato
  válido inexistente, nada de cuentas reales.
- **Tablas explícitas:** cada test pasa las tablas que usa (fixture versionada) y nunca depende de
  "la tabla actual".
- Un test por regla; el nombre describe el escenario en español:
  `test_afp_empleado_topa_en_salario_cotizable_maximo`.

## 1. Fixtures
- Las factories van en `backend/tests/unit/engine/factories.py`: `make_employee(...)`,
  `make_contract(...)`, `make_period(...)`, `make_tables(version=...)`, con valores por defecto
  razonables y ficticios. Solo sobrescribe lo relevante al caso.
- Las tablas de prueba van en `backend/tests/fixtures/tables/` como JSON (formato de la skill
  `update-tax-tables`). Si un test necesita valores **reales**, deben venir de una versión con fuente
  registrada en `docs/normativa/fuentes.md`.

## 2. Caso calculado a mano
1. Llena la hoja [templates/hand_calc_case.md](templates/hand_calc_case.md) **antes** de codificar:
   entradas, tablas y versión, cada paso intermedio sin redondear, redondeo por línea y totales.
2. Transcribe la hoja al docstring del test (forma resumida) y los valores finales a `expected`.
3. Verifica la línea **y** su trazabilidad (`base`, `rate`, `table_version`), no solo el monto.
4. Verifica las identidades: `gross − deductions == net` y `sum(lines) == total`.

## 3. Property-based (Hypothesis)
Usa `hypothesis.strategies.decimals(min_value=..., max_value=..., places=2, allow_nan=False,
allow_infinity=False)`. Propiedades mínimas:
- `round_line(x)` tiene exactamente 2 decimales, y `|round_line(x) − x| <= 0.005`.
- Redondear dos veces da lo mismo que redondear una vez (idempotencia).
- El neto nunca supera al bruto y no hay descuentos de ley negativos.
- La base cotizable es `<= tope` para cualquier salario.
- Monotonía: a más salario, la retención de ISR no disminuye.
Ejemplo en [templates/test_properties_example.py](templates/test_properties_example.py).

## 4. Bugs de cálculo
1. Escribe primero el test que reproduce el bug con los datos mínimos (ficticios) y confirma que falla.
2. Nómbralo `test_regresion_<issue>_<descripcion>` y deja en el docstring el enlace al issue y la
   causa raíz.
3. Corrige. El test queda para siempre.

## 5. Dónde va cada test
| Tipo | Carpeta |
|---|---|
| Concepto individual | `tests/unit/engine/concepts/` |
| Volante completo (todas las líneas) | `tests/unit/engine/test_payslip_*.py` |
| Propiedades | `tests/unit/engine/test_properties_*.py` |
| Reproducibilidad histórica (BD) | `tests/integration/` |

Comando: `pytest tests/unit/engine -q`. Para Hypothesis más exhaustivo:
`pytest --hypothesis-profile=ci`.
