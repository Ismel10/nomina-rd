# 0002. Método de prorrateo del salario fijo

- **Estado:** Aceptado (2026-11-11)
- **Fecha:** 2026-11-11
- **Issue / PR:** #15

## Contexto
Cuando un empleado con salario fijo ingresa o sale a mitad de un periodo, se le paga solo una
parte del salario del periodo (mensual, o mensual ÷ 2 en quincenal). No encontramos una norma que
imponga un método único; en la práctica las empresas usan criterios distintos. Hace falta que el
método sea **configurable por empresa** y que esté definido con precisión, para que un cálculo hecho
a mano coincida al centavo con el del sistema.

## Decisión
La política de pago de cada empresa (`PayrollPolicy.proration_method`) elige uno de dos métodos:

- **`CALENDAR_FRACTION`** (días calendario):
  `salario del periodo × días calendario de servicio dentro del periodo ÷ días calendario del periodo`.
- **`COMMERCIAL_30`** (mes comercial de 30 días; cada quincena tiene 15):
  `salario del periodo × días comerciales de servicio ÷ días comerciales del periodo` (30 en
  mensual, 15 en quincenal). **Convención del proyecto** para contar días comerciales: cada fecha
  tiene un índice `d` igual a su día del mes, salvo el **último día del mes**, que vale **30**, y el
  día 31, que también vale 30. Los días de servicio son `d(último día de servicio) − d(primer día) + 1`.

En ambos métodos el cálculo se hace a precisión completa y se redondea **una vez** en la línea del
salario (`round_line`, ADR 0001). El valor de un día de ausencia no depende del método: es
`salario mensual ÷ divisor de la política`.

### Ejemplos (salario mensual ficticio RD$30,000.00; quincena RD$15,000.00)

| Caso | `CALENDAR_FRACTION` | `COMMERCIAL_30` |
|---|---|---|
| 2.ª quincena de enero (16–31), ingreso el 24 | 15,000 × 8/16 = **7,500.00** | 15,000 × 7/15 (24…30) = **7,000.00** |
| Febrero 2026 mensual (28 días), ingreso el 15 | 30,000 × 14/28 = **15,000.00** | 30,000 × 16/30 (15…30) = **16,000.00** |
| 2.ª quincena de febrero 2026 (16–28), ingreso el 20 | 15,000 × 9/13 = 10,384.615… → **10,384.62** | 15,000 × 11/15 (20…30) = **11,000.00** |
| 2.ª quincena de febrero completa | 15,000 × 13/13 = **15,000.00** | 15,000 × 15/15 = **15,000.00** |

## Alternativas consideradas
- **Días laborables × salario diario por divisor:** es el más cercano a la práctica del divisor
  23.83, pero necesita un calendario laboral con los feriados de cada año. Queda fuera del MVP.
- **Un solo método fijo para todas las empresas:** más simple, pero no cubre los casos reales; la
  forma de pagar la define cada empresa.

## Consecuencias
- **Se gana:** cada empresa elige su criterio por configuración, sin cambiar el código. Los dos
  métodos coinciden en los periodos completos.
- **Se pierde / hay que saber:** con `COMMERCIAL_30`, febrero y el día 31 se "estiran" a 30. Salir
  el 30 o el 31 de un mes de 31 días paga lo mismo, e ingresar el 27 de febrero (no bisiesto) cuenta
  4 días comerciales (27, 28→30). Es propio del método y queda documentado en los tests.
- Agregar el método por días laborables más adelante será otro valor de `ProrationMethod` y otro
  ADR.
