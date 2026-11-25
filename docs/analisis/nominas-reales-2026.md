# Análisis de nóminas reales (2026)

Lecciones de dos nóminas reales en Excel de empresas cliente de la firma, para ajustar el plan
(`docs/plan/roadmap.md`). Issue #21.

> **Privacidad.** Los archivos originales **no están en el repositorio** ni deben agregarse:
> contienen datos personales reales. Este documento está anonimizado: las empresas son "Empresa A"
> y "Empresa B", y **todos los montos son ficticios** (salario mensual de ejemplo RD$30,000.00).

## 1. Contexto

| | Empresa A (hotel) | Empresa B (servicios) |
|---|---|---|
| Frecuencia | Quincenal | **Mensual pagada en dos partes**: se calcula el mes completo y se paga un **adelanto** en la primera quincena y el resto en la segunda |
| Ingresos | Quincena, feriado trabajado, horas extra, nocturnidad, incentivo | Salario y otros ingresos |
| Deducciones | AFP, SFS, ISR y otros descuentos | AFP, SFS, ISR y **préstamos** (en una hoja aparte, con cuotas y saldo) |

## 2. Lo que confirman (el diseño ya lo cubre)

| Práctica observada | En el sistema |
|---|---|
| Salario diario = mensual ÷ 23.83; hora = diario ÷ 8 | Divisor y jornada en `PayrollPolicy` (`fuentes.md#divisor`) |
| Quincena = mensual ÷ 2 | `period_salary` (`engine/proration.py`) |
| AFP 2.87 % y SFS 3.04 % del empleado | Tasas oficiales (`fuentes.md#tss-tasas`); paso 3 |
| Horas extra: hora normal × 1.35 × horas | Recargo mínimo legal del 35 % (art. 203, `fuentes.md#horas-extra`); paso 5 |
| Descuento por ausencia: salario diario × días | `AbsenceRule` con porcentaje de pago 0 (`calculate`, #19) |
| ISR mensual con la escala 2026 sobre ingresos − AFP − SFS | Equivale a anualizar y dividir entre 12 (`fuentes.md#isr-escala`); paso 4 |
| Salario mínimo por categoría (una empresa usa el de empresa pequeña) | `minimum_wage_category` en la política (#15) |

Ejemplos ficticios (mensual RD$30,000.00, divisor 23.83):
- **salario diario:** 1,258.917331… y **hora:** 157.364666…;
- **10 h extra:** 157.364666… × 1.35 × 10 = 2,124.422996… → **2,124.42**;
- **AFP de una quincena de 15,000.00:** 430.50; **SFS:** 456.00.

## 3. Lo nuevo y las decisiones de la firma

| # | Hallazgo | Decisión / tratamiento | Paso |
|---|---|---|---|
| 1 | **Prorrateo por días laborados**, casi siempre `salario diario × días laborados`, con medios días (5.5, 8.5, 10.5; el sábado vale medio día). A veces `/30`. | Los días se cuentan a mano y **llegan como dato**: no hace falta calendario. Nuevo método `WORKING_DAYS` (días laborables del tramo con contrato, sin restar ausencias; ADR 0003). Ejemplo: 10.5 días × 1,258.917331… = 13,218.631976… → **13,218.63**. | 2c |
| 2 | **Sin prorrateo por contrato:** hay contratos que pagan la quincena completa aunque el empleado entre a mitad; en la misma empresa, otros sí se prorratean. | Método `NO_PRORATION` y método configurable **por contrato**, por encima del de la empresa. **Pendiente:** ¿también se paga completa si sale a mitad? | 2c |
| 3 | **Base de la TSS por concepto:** en las dos empresas, AFP y SFS se calculan **solo sobre el sueldo base**; incentivos, horas extra, nocturnidad y feriados no cotizan. El ISR sí incluye incentivos y horas extra. | Marca "cotiza TSS" y "grava ISR" **por concepto**, configurable. **Pendiente:** confirmar que es correcto según la ley (`TODO(verificar-normativa)`). | 3, 4 |
| 4 | **Nocturnidad:** salario diario × noches × 15 % (art. 204). | Recargo mínimo legal en tabla. Ejemplo: 1,258.917331… × 3 × 0.15 = 566.512798… → **566.51**. | 5 |
| 5 | **Feriado trabajado:** un día extra de salario por cada feriado trabajado (recargo del 100 %). | Concepto con recargo configurable, con mínimo legal en tabla. Ejemplo: 1 feriado = **1,258.92**. | 5 |
| 6 | **Incentivo fijo recurrente:** monto fijo por contrato, cada mes o solo en la primera quincena. | Ingreso recurrente por contrato, con su programación por periodo. | 2d |
| 7 | **Per cápita adicional:** descuento al empleado por dependientes adicionales del seguro de salud (SFS). **Reduce la base del ISR.** | Concepto de descuento que entra en la base del ISR como deducción. | 3, 4 |
| 8 | **Préstamos:** la cuota se define **por quincena**; en una nómina mensual se descuenta la suma de las cuotas del mes. Hoy el saldo se lleva a mano. | Préstamo con cuota y saldo. El motor recibe la cuota y el saldo como datos y nunca descuenta más que el saldo; el saldo persiste fuera del motor. Ejemplo ficticio: cuota quincenal 1,500.00 → mes 3,000.00. | 5b, 6 |
| 9 | **Nómina mensual con adelanto quincenal:** se calcula el mes, se paga un adelanto en la primera quincena y el resto al final. | Nuevo modo de pago que convive con quincenal y mensual: el adelanto es un pago, no un periodo de cálculo. | 7b |
| 10 | **Exención del ISR:** hay empleados exentos de retención por motivos particulares. | **Regla:** una exención del ISR solo puede existir con **motivo obligatorio, vigencia y registro en la auditoría**. Nunca un ISR en 0 sin explicación. | 4 |
| 11 | **Vacaciones:** se usan de forma habitual (pagadas por adelantado, con su ISR). | Siguen fuera del MVP, con **prioridad alta** en la fase siguiente. | Fase siguiente |
| 12 | **Aportes patronales** (TSS del empleador e INFOTEP) no aparecen en los Excel; se calculan aparte. | El sistema los calculará en el volante (`EMPLOYER_CONTRIBUTION`). | 3 |

## 4. Errores humanos frecuentes (confirmados por la firma)

- **Sin redondeo:** montos con 3 o más decimales (por ejemplo 13,218.632 donde el sistema da 13,218.63).
- **Fórmulas distintas de una fila a otra** para el mismo concepto.
- **Números fijos dentro de las fórmulas** (tasas o divisores escritos a mano).
- **Fechas escritas como texto.**

**Consecuencia para la comparación:** al comparar el sistema con estos Excel habrá **diferencias de
centavos por redondeo**. El criterio correcto es el del sistema (ADR 0001: half up a 2 decimales,
una vez por línea). Las diferencias de más de unos centavos se investigan una por una.

## 5. Preguntas pendientes para la firma

- [ ] Con "sin prorrateo", ¿la salida a mitad de periodo también se paga completa?
- [ ] ¿Es correcto que los incentivos, las horas extra y la nocturnidad no coticen a la TSS?
- [ ] ¿Cómo se retiene el ISR y cómo se aplica el tope mensual de la TSS en una nómina quincenal?
- [ ] ¿Cómo se define el adelanto de la nómina mensual (monto fijo, porcentaje o mitad del neto)?
- [ ] ¿Qué significa la columna "Turno" (valores del 1 al 7) de la Empresa A?

## 6. Puntos que requieren fuente normativa

No están en `docs/normativa/fuentes.md`. Se marcan `TODO(verificar-normativa)` y **no se cargan
como regla** hasta tener fuente:
- qué conceptos forman el salario cotizable de la TSS (hallazgo 3);
- recargo mínimo legal del feriado trabajado (hallazgo 5);
- tratamiento del per cápita adicional en la base del ISR (hallazgo 7);
- si el recargo nocturno del art. 204 se aplica por hora nocturna o por noche completa (hallazgo 4).
