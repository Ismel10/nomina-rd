---
name: db-migration
description: Usar al crear, modificar o revisar migraciones Alembic (tablas, columnas, índices, restricciones, datos de catálogo o tablas de tasas). Asegura aislamiento multiempresa, índices por company_id, inmutabilidad de periodos cerrados y cero pérdida de datos.
---

# Migraciones de base de datos seguras

## 1. Diseño (antes de generar)
- Toda tabla de negocio lleva `company_id UUID NOT NULL REFERENCES company(id)`. Solo son
  globales: `company`, `concept` (catálogo), `rate_table*`, `audit_log` (que de todos modos lleva
  `company_id` nullable) y tablas de sistema.
- Índices y `UNIQUE` **empiezan por `company_id`**: `(company_id, employee_code)`,
  `(company_id, period_id)`.
- Montos `NUMERIC(14,2)`, tasas `NUMERIC(9,6)`. Nunca `FLOAT`, `REAL` ni `DOUBLE PRECISION`.
- Vigencias: `valid_from DATE NOT NULL`, `valid_to DATE NULL`, y una restricción contra solapes
  (`EXCLUDE USING gist (… WITH =, daterange(valid_from, valid_to, '[]') WITH &&)`, requiere
  `btree_gist`).
- Las FKs hacia datos de periodo usan `ON DELETE RESTRICT`. Nada de `CASCADE` sobre volantes o líneas.

## 2. Generar
```bash
cd backend
alembic revision --autogenerate -m "add_<tabla>_<cambio>"
```
**Revisa el archivo a mano**, porque autogenerate no detecta todo: renombres (los ve como
drop+add), `EXCLUDE`, triggers, datos.

## 3. Verificar con el script
```bash
python .claude/skills/db-migration/scripts/check_migration.py backend/migrations/versions/<archivo>.py
```
Marca operaciones destructivas, tipos float, `create_table` sin `company_id` y índices que no
empiezan por `company_id`. Cada advertencia se **corrige** o se **justifica** en el PR.

## 4. Cambios sin pérdida de datos (expand → migrate → contract)
- **Renombrar o cambiar el tipo de una columna:** agrega la nueva, copia los datos, cambia el código
  para usar la nueva y elimina la vieja **en una migración posterior**.
- **`NOT NULL` en una columna existente:** agrégala nullable, rellena (backfill) y luego aplica
  `NOT NULL`.
- `drop_table` y `drop_column` solo con aprobación explícita del usuario y nunca sobre datos de
  periodos cerrados.
- Las migraciones de datos son **idempotentes** (`ON CONFLICT DO NOTHING`, `WHERE … IS NULL`).

## 5. `downgrade()`
- Siempre implementado. Si es imposible sin perder datos, debe lanzar
  `NotImplementedError("irreversible: <motivo>")` en vez de borrar en silencio.

## 6. Probar
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic check            # el modelo y las migraciones no divergen
pytest tests/integration
```
`alembic downgrade` contra una BD con datos reales pide confirmación (ver `.claude/settings.json`).

## Checklist del PR
- [ ] `company_id` + índices compuestos, o justificación de por qué es tabla global
- [ ] Sin tipos float; montos y tasas en NUMERIC
- [ ] Sin pérdida de datos (expand/contract) y con `downgrade` real o explícitamente irreversible
- [ ] Script `check_migration.py` sin advertencias sin justificar
- [ ] Ciclo upgrade/downgrade/upgrade y tests de integración en verde
