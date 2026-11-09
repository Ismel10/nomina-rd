---
name: add-payroll-concept
description: Usar al agregar o modificar un concepto de nómina (ingreso/percepción, descuento/deducción o aporte patronal), p. ej. horas extra, comisiones, préstamo, AFP, SFS, ISR, INFOTEP. Cubre modelo, fórmula en el motor, configuración por empresa, tests, migración y glosario.
---

# Agregar un concepto de nómina

Un concepto toca 6 capas. Hazlas en este orden; cada paso deja los tests en verde.

## 0. Antes de escribir código
1. Define con el usuario y deja por escrito en el PR:
   - código estable en `UPPER_SNAKE` (p. ej. `OVERTIME_35`);
   - tipo: `earning` | `deduction` | `employer_contribution`;
   - si afecta la base **cotizable TSS** o la base **gravable ISR** (sí/no para cada una);
   - fórmula, base, tasa o tope y su **fuente normativa**.
2. Si cualquier dato legal es incierto, escribe `TODO(verificar-normativa): …` y **pregunta**.
   No inventes tasas, topes ni exenciones.
3. Si la tasa o el tope cambia con el tiempo, **no la codifiques**: va en una tabla con vigencia
   (skill `update-tax-tables`).

## 1. Test primero (motor)
- Usa la skill `payroll-calculation-tests`. Escribe al menos:
  - un caso **calculado a mano**, documentado con la plantilla
    [templates/concept_test_template.py.tmpl](templates/concept_test_template.py.tmpl);
  - un caso borde: tope alcanzado, monto cero, prorrateo por ingreso o salida a mitad de periodo;
  - una propiedad Hypothesis si hay redondeo o topes.
- Ubicación: `backend/tests/unit/engine/concepts/test_<codigo_en_minusculas>.py`.
- Córrelo y confirma que **falla** por la razón correcta.

## 2. Fórmula en el motor (`backend/src/nomina/engine/`)
- Implementa el concepto como una función pura que recibe un `ConceptContext` (inputs del empleado,
  novedades, bases acumuladas, tablas inyectadas) y devuelve una línea con: `code`, `kind`, `base`,
  `rate`, `amount`, `table_version`.
- Redondea **solo** con `engine.money.round_line()` y una vez por línea.
- Sin `float`, sin I/O, sin `datetime.now()`, sin logging.
- Regístralo en el catálogo de conceptos del motor, respetando el **orden de evaluación**:
  ingresos → bases cotizables → TSS → base gravable → ISR → otros descuentos → aportes patronales.

## 3. Modelo y configuración por empresa
- Catálogo global: fila en `concept` (código, tipo, flags de afectación de bases).
- Configuración por empresa en `company_concept`: `company_id`, `concept_code`, `enabled`,
  parámetros opcionales y `valid_from`/`valid_to`.
- El servicio carga la configuración **filtrando por `company_id`** y la pasa al motor como datos.

## 4. Migración
- Usa la skill `db-migration`. Si el concepto es de catálogo, inserta la fila con una migración de
  datos idempotente (`INSERT … ON CONFLICT DO NOTHING`).

## 5. API y frontend (si aplica)
- Expón el concepto en el esquema de configuración por empresa. Los montos van como string.
- Si la SPA muestra el concepto, agrega su etiqueta en español.

## 6. Documentación
- Agrega o actualiza la fila en el **glosario** de `AGENTS.md` si es un término nuevo.
- Agrega la fuente legal en `docs/normativa/fuentes.md` (norma, artículo, fecha, enlace).

## Checklist final
- [ ] Test manual + borde + propiedad, en verde
- [ ] Sin `float` ni I/O en el motor (`pytest tests/architecture`)
- [ ] Configuración por empresa filtrada por `company_id`
- [ ] Migración revisada con `db-migration`
- [ ] Glosario y fuentes actualizados; los `TODO(verificar-normativa)` quedan listados en el PR
- [ ] `ruff check .`, `ruff format --check .`, `mypy` y `pytest` en verde
