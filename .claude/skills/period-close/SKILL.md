---
name: period-close
description: Usar al implementar, modificar o ejecutar el flujo de estados de un periodo de nómina (abierto → calculado → revisado → cerrado), el cierre de periodo, la reapertura de un periodo no cerrado o la creación de ajustes sobre periodos cerrados.
---

# Cierre de periodo de nómina

## Máquina de estados
```
open ──calcular──▶ calculated ──revisar──▶ reviewed ──cerrar──▶ closed (terminal)
  ▲                    │  ▲                    │
  └──── reabrir ───────┘  └──── devolver ──────┘
```
- Se puede **recalcular** en `open` y en `calculated`. Si cambia una novedad o un contrato en
  `calculated` o `reviewed`, el periodo vuelve a `open`.
- `closed` es **terminal**: no se reabre. Para corregir se crea un `Adjustment` en un periodo
  posterior abierto, con `source_period_id` y el motivo.
- Cada transición se valida en `services/period_service.py` (nunca en el router) y escribe en
  `audit_log`.

## Precondiciones para cerrar (todas obligatorias)
El servicio `close_period(company_id, period_id, user)` ejecuta estas verificaciones **en una sola
transacción** y aborta si alguna falla:

1. **Estado:** el periodo está en `reviewed`.
2. **Tenant:** el periodo pertenece a `company_id`.
3. **Cobertura:** todo empleado con contrato vigente en el rango tiene volante, o una exclusión
   explícita con motivo.
4. **Totales cuadran:**
   - por volante, `gross − deductions == net`;
   - por periodo, `Σ net de volantes == total del archivo de dispersión`;
   - `Σ líneas por concepto == totales del resumen`.
   Todo con comparación `Decimal` exacta.
5. **Sin pendientes:** no hay novedades sin procesar ni `TODO(verificar-normativa)` activos en los
   conceptos usados (bandera en el catálogo).
6. **Documentos generados:** existen el PDF de cada volante y el archivo de dispersión, con su hash
   SHA-256 guardado.
7. **Snapshot de tablas:** queda guardada la versión de cada tabla usada (para reproducibilidad).

## Al cerrar
- `status = closed`, `closed_at`, `closed_by`.
- Registro en `audit_log` con el resumen: empleados, bruto, descuentos, neto, aportes y hashes.
- Inmutabilidad en dos capas:
  - **servicio:** todo método de escritura rechaza periodos `closed`;
  - **BD:** un trigger `BEFORE UPDATE OR DELETE` en `payroll_period`, `payslip` y `payslip_line`
    lanza un error si el periodo está `closed`.

## Tests obligatorios
- Cada precondición tiene su test que **falla** el cierre.
- Cierre exitoso: se verifican el estado, la auditoría y los hashes.
- Inmutabilidad: intentar `UPDATE` o `DELETE` sobre un volante de un periodo cerrado, vía servicio
  y vía SQL directo (integración), y ambos fallan.
- Ajuste: corrección de un periodo cerrado aplicada en el siguiente, sin modificar el original.
- Aislamiento: la empresa A no puede cerrar ni ver un periodo de la empresa B.

## Reporte de cierre
Usa [templates/close_report.md](templates/close_report.md) para el resumen que se muestra al usuario
y se adjunta en la auditoría.
