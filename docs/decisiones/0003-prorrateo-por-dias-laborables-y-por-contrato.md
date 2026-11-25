# 0003. Prorrateo por días laborables, sin prorrateo y método por contrato

- **Estado:** Aceptado (2026-11-25)
- **Fecha:** 2026-11-23
- **Issue / PR:** #22
- **Amplía:** ADR 0002 (no lo reemplaza: `CALENDAR_FRACTION` y `COMMERCIAL_30` siguen igual)

## Contexto
El análisis de nóminas reales (`docs/analisis/nominas-reales-2026.md`, hallazgos 1 y 2) muestra
dos prácticas que el ADR 0002 no cubre:

1. Casi siempre se prorratea con `salario diario × días`, contando a mano los días laborables
   (con medios días: el sábado vale medio día). Los días **llegan como dato**; no hace falta un
   calendario de feriados.
2. Hay contratos que pagan el periodo completo aunque el empleado entre a mitad, mientras otros
   contratos de la **misma empresa** sí se prorratean.

El ADR 0002 dejó fuera del MVP el prorrateo por días laborables porque exigía un calendario. Con los
días como dato, ese obstáculo desaparece. El prorrateo calculado con un calendario de feriados sigue
fuera del MVP.

## Decisión

### 1. Método `WORKING_DAYS`
- **Periodo completo** (el contrato cubre todo el periodo): paga el **salario del periodo**
  (mensual, o mensual ÷ 2), como en los Excel reales.
- **Periodo parcial** (ingreso o salida a mitad): `salario diario × working_days`, con
  `salario diario = salario mensual ÷ divisor de la política`, a precisión completa y redondeado una
  sola vez en la línea (ADR 0001).
- **`working_days` = días laborables del tramo con contrato dentro del periodo, SIN restar las
  ausencias.** Lunes a viernes cuentan 1, el sábado 0.5 y el domingo 0. Las ausencias llegan aparte
  como novedades y se descuentan por la cascada, como hasta ahora; así no se descuentan dos veces.
  Se evitaron los nombres `WORKED_DAYS` y `worked_days` ("días trabajados") porque se prestan a
  entenderlos como días sin las faltas.
- **Validaciones** (`PayrollInputError`):
  - **regla única:** `working_days` solo es válido con `WORKING_DAYS` en un periodo parcial, donde
    es obligatorio. En cualquier otro caso (otro método o periodo completo) es un error: un dato
    que no se usa no se ignora en silencio, y un método nuevo queda cubierto automáticamente;
  - mayor que 0 y en múltiplos de 0.5;
  - no mayor que los días calendario con contrato vigente dentro del periodo;
  - `salario diario × working_days` no puede superar el salario del periodo;
  - los días de ausencia no pueden superar `working_days`.
- "A veces `/30`" no es otro método: es `WORKING_DAYS` con divisor 30 en la política.

### 2. Método `NO_PRORATION`
- Paga el **salario del periodo completo** si el contrato tiene al menos un día en el periodo,
  aunque el ingreso sea a mitad.
- **Salida a mitad de periodo:** `PayrollUnsupportedError`. No se paga de más sin una regla
  confirmada; cuando la firma responda (#27), se crea un ADR nuevo.

### 3. Método por contrato
- `ContractInput.proration_method` es opcional; si existe, **gana sobre el de la política**
  (`contrato → empresa`, sin nivel de grupo).
- La línea `ORDINARY_SALARY` registra el origen: `RuleSource.CONTRACT` o `RuleSource.COMPANY`.

### 4. Lo que no cambia
El límite de ausencias en días calendario con contrato, el tope `ABSENCE_DISCOUNT_CAP`, el error por
novedades sin días de servicio y el valor del día de ausencia (`mensual ÷ divisor`).

### Ejemplos con el calendario real de marzo de 2026 (el 1 de marzo es domingo)

Salario mensual ficticio RD$30,000.00, divisor 23.83 → salario diario 1,258.917331…; quincena
RD$15,000.00.

| Caso | Conteo de días laborables | Resultado |
|---|---|---|
| `WORKING_DAYS`, 1.ª quincena completa | — (periodo completo) | **15,000.00** |
| `WORKING_DAYS`, ingreso el viernes 6 (1.ª quincena) | vie 6 = 1, sáb 7 = 0.5, lun 9–vie 13 = 5, sáb 14 = 0.5 → **7** | 1,258.917331… × 7 → **8,812.42** |
| Lo mismo con 1 día injustificado (ratio 0) | 7 (la ausencia no se resta de los días) | 8,812.42 − 1,258.92 = **7,553.50** |
| Divisor 30, ingreso el viernes 6 | **7** | 1,000.00 × 7 = **7,000.00** |
| `WORKING_DAYS`, ingreso el lunes 9 (1.ª quincena) | lun 9–vie 13 = 5, sáb 14 = 0.5 → **5.5** | → **6,924.05** |
| `WORKING_DAYS`, salida el martes 24 (2.ª quincena) | lun 16–vie 20 = 5, sáb 21 = 0.5, lun 23–mar 24 = 2 → **7.5** | → **9,441.88** |
| `WORKING_DAYS`, mensual, ingreso el lunes 16 | lun 16–vie 20 = 5, sáb 21 = 0.5, lun 23–vie 27 = 5, sáb 28 = 0.5, lun 30–mar 31 = 2 → **13** | → **16,365.93** |
| `NO_PRORATION`, ingreso el martes 10 (1.ª quincena) | — | **15,000.00** |
| Política `COMMERCIAL_30`, contrato `NO_PRORATION`, ingreso el martes 24 (2.ª quincena) | — | **15,000.00** (con `COMMERCIAL_30` serían 7,000.00) |

## Alternativas consideradas
- **Aplicar `WORKING_DAYS` también a periodos completos:** la 1.ª quincena de marzo de 2026 tiene 11
  días laborables, y 11 × 1,258.917331… = 13,848.09, no 15,000.00. Los Excel reales pagan el periodo
  completo. Descartada.
- **Días laborables calculados con un calendario de feriados:** exige un calendario por año y no
  aporta sobre el dato contado a mano. Sigue fuera del MVP.
- **Método también por grupo de empleados:** no hay un caso real que lo pida. Se puede agregar
  después como un nivel más de la cascada.
- **Topar `WORKING_DAYS` al salario del periodo en vez de dar error:** con días contados a mano,
  superar el periodo suele ser un error de carga; el tope lo ocultaría.

## Consecuencias
- **Se gana:** se cubren las dos prácticas reales sin calendario y por contrato, con trazabilidad del
  nivel que eligió el método.
- **Hay que saber:** con `WORKING_DAYS`, la exactitud depende de los días que cuente la firma; el
  motor valida los rangos, pero no puede saber si un día era laborable o feriado.
- **Revisión futura:** cuando la firma defina la salida a mitad de periodo con `NO_PRORATION` (#27),
  se crea un ADR nuevo que la regule; este no se edita.
