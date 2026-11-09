---
name: update-tax-tables
description: Usar al cargar o corregir tablas con vigencia (escala ISR de DGII, tasas y topes TSS de AFP/SFS/SRL, INFOTEP, salario mínimo cotizable) o cuando cambie la normativa. Garantiza que los cálculos de periodos anteriores sigan siendo reproducibles.
---

# Actualizar tablas de impuestos y tasas con vigencia

Principio: **las tablas publicadas son inmutables**. Un cambio normativo crea una **versión nueva**
con su `valid_from`; nunca se edita una versión que pudo haberse usado en un cálculo.

## 1. Reunir la fuente
- Pide al usuario (o cita) la norma oficial: resolución, aviso o ley; número, fecha de publicación
  y fecha de entrada en vigor.
- Regístrala en `docs/normativa/fuentes.md`. **Sin fuente no hay tabla.** Si falta, deja
  `TODO(verificar-normativa)` y detente.

## 2. Preparar el archivo de la versión
- Formato: JSON en `backend/src/nomina/persistence/seed_data/tables/<tabla>/<valid_from>.json`
  siguiendo [templates/rate_table.example.json](templates/rate_table.example.json).
- Todos los números van como **string decimal** (`"0.0287"`, `"416220.00"`), nunca como número JSON.
- `valid_to` de la versión nueva es `null`. La versión anterior **no se toca en el archivo**: el
  cierre de su vigencia lo calcula la carga (`valid_to = nuevo valid_from − 1 día`).

## 3. Validar
```bash
python .claude/skills/update-tax-tables/scripts/validate_rate_table.py <ruta.json> [<ruta_anterior.json>]
```
El script verifica que los decimales sean válidos, que los tramos de la escala estén ordenados,
contiguos y sin solapes, que las tasas estén en [0, 1], y que las fechas sean coherentes con la
versión anterior. Debe terminar con `OK`.

## 4. Migración de datos
- Skill `db-migration`. Inserta la versión nueva y actualiza `valid_to` de la anterior **solo si
  era `null`**. Es idempotente.
- Hay una restricción de BD que impide solapes de vigencia por `(table_code)`
  (`EXCLUDE USING gist` con `daterange`).

## 5. Tests obligatorios
1. **Caso nuevo** calculado a mano con la tabla nueva (skill `payroll-calculation-tests`).
2. **Regresión histórica:** recalcula al menos un periodo **anterior** con fecha de pago antes del
   `valid_from` y verifica que el resultado es **idéntico** al guardado (snapshot de
   `tests/integration/snapshots/`).
3. **Frontera:** un periodo con fecha de pago exactamente en `valid_from` usa la tabla nueva, y uno
   un día antes usa la anterior.

## 6. Revisión
- En el PR: diff de valores entre versiones, enlace a la fuente y salida del validador.
- No hay periodos `closed` afectados: los cerrados nunca se recalculan, aunque cambie la tabla.
