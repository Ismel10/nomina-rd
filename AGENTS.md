# AGENTS.md — Nómina RD multiempresa

Fuente de verdad para humanos y agentes (Claude Code, Codex, Cursor…). Si el código contradice
este archivo, se corrige uno de los dos **en el mismo PR**.

## 1. Resumen del proyecto

Sistema de nómina **multiempresa** para una firma contable que procesa la nómina de varias
empresas cliente en **República Dominicana**. Es un proyecto de portafolio: se prioriza
corrección, trazabilidad y claridad por encima de la cantidad de funciones.

**MVP**
- Empresas cliente, empleados y contratos: salario fijo mensual o pago por horas (horas resumidas
  como novedad del periodo); pago quincenal o mensual. La forma de pagar (ausencias, grupos,
  tarifas, prorrateo) la configura cada empresa en su política de pago, no el código.
- Motor de cálculo: salario ordinario, horas extra, retenciones de ley del empleado (AFP, SFS, ISR),
  aportes patronales (AFP, SFS, SRL, INFOTEP) y descuentos voluntarios simples (préstamo, anticipo).
- Ciclo del periodo `abierto → calculado → revisado → cerrado`; correcciones con ajustes posteriores.
- Volante de pago en PDF y archivo de dispersión bancaria (CSV genérico).
- Bitácora de auditoría y SPA para operar todo el flujo.

**Fuera del MVP (por ahora):** archivos oficiales TSS (SUIR+) y DGII (IR-3, IR-13), formatos
propietarios por banco, salario de Navidad y vacaciones (siguiente fase), prestaciones laborales
(preaviso, cesantía), bonificación (participación en beneficios), multimoneda, SSO, portal del empleado,
jornada parcial, jornada reducida de trabajos peligrosos, licencias cubiertas por subsidio (SISALRIL)
y prorrateo por días laborables (requiere calendario de feriados).

## 2. Dominio y glosario

Código en inglés; la UI y la documentación, en español. Este glosario es el puente entre ambos.

| Término (RD) | En código | Definición |
|---|---|---|
| Empresa cliente | `Company` (tenant) | Empleador al que la firma le lleva la nómina. Se identifica por su **RNC**. |
| Empleado | `Employee` | Persona con **cédula** (o pasaporte) y **NSS**. Pertenece a una sola empresa. |
| Contrato de trabajo | `Contract` | Condiciones vigentes: salario, frecuencia de pago, tipo (indefinido / obra o servicio), fechas. Se versiona por vigencia. |
| Esquema de pago | `PayScheme` | Cómo se paga el contrato: `FIXED_SALARY` (salario mensual fijo; la quincena es la mitad) o `HOURLY` (horas × tarifa). |
| Política de pago | `PayrollPolicy` | Configuración de pago de una empresa, **con vigencia**: divisor del salario diario, horas de jornada, método de prorrateo, categoría de salario mínimo, reglas de ausencia y grupos. |
| Grupo de empleados | `EmployeeGroup` | Agrupación configurable por empresa (jerarquía, departamento, turno…) con reglas propias. Un contrato pertenece a un grupo como máximo. |
| Tipo de ausencia / regla de ausencia | `AbsenceRule` | Código configurable por empresa con su **porcentaje de pago** (`pay_ratio` entre 0 y 1: 1 = se paga completa, 0 = se descuenta completa). |
| Resolución en cascada | `resolve_absence_ratio` | Se usa la regla más específica: contrato → grupo → empresa. Si no hay ninguna, es error; nunca un valor por defecto. |
| Método de prorrateo | `ProrationMethod` | Cómo se prorratea el salario por ingreso o salida: `CALENDAR_FRACTION` o `COMMERCIAL_30` (ADR 0002). |
| Licencia legal | `LegalLeave` | Licencia definida por ley: pagada por el empleador (art. 54, con máximo de días) o cubierta por subsidio (fuera del MVP). |
| Periodo de nómina | `PayrollPeriod` | Rango de fechas de una frecuencia. Estados: `open`, `calculated`, `reviewed`, `closed`. |
| Concepto | `Concept` | Regla que produce una línea del volante. Tipos: `earning`, `deduction`, `employer_contribution`. |
| Ingreso (percepción) | `earning` | Suma al bruto: salario ordinario, horas extra, comisiones… |
| Descuento (deducción) | `deduction` | Resta al neto: AFP y SFS del empleado, ISR retenido, préstamos… |
| Aporte patronal | `employer_contribution` | Costo del empleador que no afecta el neto: AFP, SFS y SRL patronales, INFOTEP. |
| Salario cotizable | `contributable_base` | Base sobre la que se calculan los aportes TSS, sujeta a **topes**. |
| Salario gravable (ISR) | `taxable_base` | Base para el ISR después de las exenciones y deducciones de ley. |
| Novedad / incidencia | `Incidence` (ausencias: `Absence`) | Hecho del periodo que altera el cálculo: horas extra, ausencias, licencias, entradas y salidas. Llega resumida (p. ej. días de ausencia por tipo). |
| Volante de pago (recibo) | `Payslip` | Detalle por empleado y periodo: líneas, totales y referencias de tabla. |
| Dispersión bancaria | `BankDisbursement` | Archivo de pagos netos para el banco de la empresa. |
| Ajuste | `Adjustment` | Corrección de un periodo cerrado, aplicada en un periodo posterior abierto. Referencia al periodo origen. |
| Tablas legales | `RateTables` | Conjunto de tablas versionadas, cada una con `valid_from` y `valid_to`: salario mínimo **mensual** por categoría, jornada máxima, licencias legales y, en pasos posteriores, TSS, ISR y recargos. |
| TSS / SDSS | — | Tesorería de la Seguridad Social (Ley 87-01). Recauda AFP, SFS y SRL. |
| DGII | — | Dirección General de Impuestos Internos. Retención de ISR a asalariados. |

Las tasas, topes y escalas **no van en el código ni en este archivo**: viven en tablas versionadas
(ver la skill `update-tax-tables`) con su fuente en `docs/normativa/fuentes.md`.

## 3. Reglas de negocio no negociables

1. **Dinero nunca en `float`.**
   - Python: `decimal.Decimal`, construido desde `str` o `int` (`Decimal("0.10")`), nunca desde un float.
   - BD: montos `NUMERIC(14,2)`; tasas `NUMERIC(9,6)`.
   - JSON: montos como **string** (`"1234.50"`).
   - Frontend: nunca `Number` para hacer aritmética con montos.
   - **Redondeo:** a 2 decimales con `ROUND_HALF_UP`, **una vez por línea de concepto**, solo en
     `engine/money.py`. Los intermedios van a precisión completa. Los totales son la suma de líneas
     ya redondeadas; nunca se redondea el total aparte. Criterio y fuentes: ADR 0001
     (`docs/decisiones/0001-criterio-de-redondeo.md`).
2. **Tablas con vigencia.** Toda tasa, tope o escala tiene `valid_from`/`valid_to`, y el motor recibe
   las tablas vigentes en la **fecha de pago** del periodo. Un cálculo histórico se reproduce
   idéntico con las tablas de su fecha. Las tablas publicadas no se editan: se crea una versión nueva.
   La **política de pago** de cada empresa (`PayrollPolicy`) sigue la misma regla: tiene vigencia y
   se elige por la fecha de pago del periodo.
3. **Un periodo cerrado es inmutable.** No hay `UPDATE` ni `DELETE` sobre periodos `closed`, ni sobre
   sus volantes y líneas: lo garantizan el servicio y un trigger de BD. Las correcciones se hacen
   con `Adjustment` en un periodo posterior.
4. **Aislamiento multiempresa.**
   - Toda tabla de negocio tiene `company_id NOT NULL`, y todo repositorio exige `company_id`
     (no hay consultas "globales" en código de negocio).
   - Los índices empiezan por `company_id`.
   - Hay un test que verifica que una empresa no ve datos de otra.
5. **Auditoría.** Los cambios en empleados, contratos, conceptos, tablas y estados de periodo escriben
   en `audit_log`: quién, cuándo, entidad, acción y diff. Los datos sensibles van enmascarados.
6. **Datos sensibles** (salarios, cédula, NSS, cuentas bancarias):
   - Nunca se loguean ni van en mensajes de error o excepciones.
   - Fixtures y seeds solo con datos **ficticios** (nombres inventados, cédulas con formato válido
     pero inexistentes).
   - Nunca se leen ni se commitean archivos `.env`.

## 4. Arquitectura y estructura

```
nomina-rd/
├── backend/
│   ├── src/nomina/
│   │   ├── engine/        # Núcleo de cálculo PURO: sin I/O, sin BD, sin logging, sin reloj
│   │   ├── services/      # Casos de uso: calcular periodo, cerrar, ajustar (orquesta engine + repos)
│   │   ├── persistence/   # SQLAlchemy: modelos, repositorios (siempre con company_id)
│   │   ├── documents/     # Generación de PDF (volantes) y archivos (dispersión, futuros TSS/DGII)
│   │   ├── api/           # FastAPI: routers, esquemas Pydantic, dependencias
│   │   ├── cli/           # Comandos (seed, utilidades)
│   │   └── config.py      # Settings desde variables de entorno
│   ├── migrations/        # Alembic
│   └── tests/{unit,integration,architecture}/
├── frontend/              # SPA: Vite + React + TypeScript
├── docs/normativa/        # Fuentes legales verificadas (ley, resolución, fecha, enlace)
└── .claude/skills/        # Procedimientos repetibles para agentes
```

### Tecnologías y para qué se usan

| Capa / área | Tecnología | Para qué se usa |
|---|---|---|
| Lenguaje backend | **Python 3.12+** | Lógica de negocio, motor de cálculo y API. |
| Dinero | `decimal.Decimal` (biblioteca estándar) | Montos y tasas exactos al centavo; nunca `float`. |
| Motor de cálculo | Python puro (`dataclasses` `frozen`) | Cálculo determinista de la nómina, sin I/O ni dependencias externas. |
| API | **FastAPI** + **Uvicorn** | Endpoints HTTP y documentación automática (Swagger en `/docs`). |
| Validación / esquemas | **Pydantic** (+ `pydantic-settings`) | Validar entrada/salida de la API y cargar la configuración desde variables de entorno. |
| Acceso a datos | **SQLAlchemy 2** + **psycopg 3** | Modelos ORM, repositorios (siempre con `company_id`) y conexión a PostgreSQL. |
| Migraciones | **Alembic** | Versionar los cambios del esquema y los datos de catálogo/tablas de tasas. |
| Base de datos | **PostgreSQL 16** | Almacenamiento; `NUMERIC` para montos, triggers de inmutabilidad, auditoría. |
| Contenedores | **Docker Compose** | Levantar PostgreSQL en local con la misma configuración para todos. |
| Documentos | Por definir | Volantes de pago en PDF y archivo CSV de dispersión bancaria. |
| Tests backend | **pytest** (+ `pytest-cov`) | Tests unitarios, de integración y de arquitectura, con cobertura. |
| Tests por propiedades | **Hypothesis** | Probar reglas con datos aleatorios: redondeo, neto, topes, sumas. |
| Tests de API | **httpx** | Cliente HTTP para probar los endpoints de FastAPI. |
| Lint + formato (Python) | **Ruff** | Detectar errores y malas prácticas (incluye `Decimal` desde float) y formatear. |
| Tipado (Python) | **mypy** (`--strict`) | Verificar tipos estáticamente antes de ejecutar. |
| Lenguaje frontend | **TypeScript 5** (`strict`) | Código de la SPA con tipos verificados. |
| UI | **React 19** | Componentes de la interfaz (empresas, empleados, periodos, volantes). |
| Build / servidor dev | **Vite** | Servidor de desarrollo rápido y build de producción. |
| Tests frontend | **Vitest** + **Testing Library** + **jsdom** | Probar componentes como los usaría una persona, sin navegador real. |
| Lint + formato (TS) | **ESLint** + **Prettier** | Detectar errores en el frontend y mantener un formato uniforme. |
| Control de versiones | **Git** (Conventional Commits) | Historial de cambios legible y ramas `feat/`, `fix/`, `chore/`. |
| Agentes | `AGENTS.md`, `CLAUDE.md`, `.claude/skills/` | Reglas y procedimientos para que los agentes de IA trabajen igual que una persona del equipo. |

**Dependencias permitidas:** `api → services → {engine, persistence, documents}`. `engine` solo
importa la biblioteca estándar (`decimal`, `dataclasses`, `datetime`, `enum`, `typing`) y su propio
paquete. Lo verifica `tests/architecture/`.

**Contrato del motor:** `calculate(inputs, tables, policy) -> PayrollResult`, una función pura y
determinista. Las tablas legales y la política de la empresa **se inyectan**; el motor nunca las
busca. Cada línea del resultado lleva trazabilidad: código de concepto, tipo, base, cantidad o tasa,
versión de tabla o de política, nivel del que salió la regla (contrato, grupo o empresa) y monto.

## 5. Comandos

Backend (desde `backend/`, con el venv activo: `.venv\Scripts\activate` en Windows o
`source .venv/bin/activate` en Linux/macOS):

| Acción | Comando |
|---|---|
| Instalar | `python -m venv .venv` y luego `python -m pip install -e ".[dev]"` |
| Correr API | `uvicorn nomina.api.main:app --reload` (docs en http://localhost:8000/docs) |
| Tests | `pytest` (motor solo: `pytest tests/unit/engine`) |
| Lint + tipos | `ruff check .` y `mypy` |
| Formato | `ruff format .` (verificar: `ruff format --check .`) |
| Nueva migración | `alembic revision --autogenerate -m "descripcion"` |
| Aplicar migraciones | `alembic upgrade head` |
| Seed (datos ficticios) | `python -m nomina.cli.seed` |

Base de datos: `docker compose up -d db` desde la raíz (requiere `.env` copiado de `.env.example`).

Frontend (desde `frontend/`): `npm install` · `npm run dev` · `npm test` · `npm run lint` ·
`npm run format` · `npm run typecheck` · `npm run build`.

**Definición de "listo":** `ruff check`, `ruff format --check`, `mypy` y `pytest` en verde. Si se
tocó el frontend, también `npm run lint`, `npm run typecheck` y `npm test`.

## 6. Convenciones

- **Python:** 3.12+, tipado estricto (`mypy --strict`), Ruff para lint y formato (línea de 100),
  dataclasses `frozen=True` en el motor, sin lógica en `__init__.py`.
- **TypeScript:** `strict`, ESLint + Prettier, componentes funcionales; los montos se muestran con
  `Intl.NumberFormat('es-DO', { style: 'currency', currency: 'DOP' })` a partir del string recibido.
- **Nombres:** código, tablas y columnas en inglés `snake_case` / `PascalCase`. Términos de dominio
  según el glosario; si introduces uno nuevo, agrégalo al glosario en el mismo PR.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/es/) con scope:
  `feat(engine): …`, `fix(api): …`, `chore(db): …`, `docs: …`, `test(engine): …`. Commits pequeños.
- **Ramas:** `main` siempre verde. Trabajo en `<tipo>/<n-issue>-<tema>` (p. ej. `feat/1-engine-money`);
  todo entra por PR enlazado a su issue. Flujo completo (issues, etiquetas, PR, CHANGELOG, ADR):
  skill `git-workflow`.

## 7. Testing

- **TDD en el motor (obligatorio):** primero el test con el resultado esperado, verlo fallar, y
  después el código. Aplica a **todo** comportamiento nuevo, incluidos los casos borde que descubras
  mientras implementas (p. ej. `-0.00`): detente, escribe su test, verifica que falla y luego
  impleméntalo. Escribir test y código juntos, o el test después, es saltarse TDD (ver §8).
- **Casos calculados a mano:** cada concepto tiene al menos un caso con la hoja de cálculo manual
  documentada en el test (base, tasa, tope, redondeo). **Tolerancia cero:** se compara `Decimal`
  exacto al centavo.
- **Property-based (Hypothesis):** redondeo, que bruto − descuentos = neto, que la suma de líneas
  = total, que no haya montos negativos donde no corresponde, y que los topes se respeten.
- **Regresión:** cada bug de cálculo agrega un test que lo reproduce **antes** del fix.
- **Integración:** repositorios contra PostgreSQL real, incluido el aislamiento entre tenants.
- **Arquitectura:** el motor no importa I/O ni frameworks y no usa `float`.
- Guía detallada: skill `payroll-calculation-tests`.

## 8. Cómo trabajar conmigo

- **No te saltes las reglas sin preguntar.** Si vas a desviarte de cualquier regla de este archivo
  (TDD, alcance pedido, reglas de negocio, convenciones o flujo de Git), **detente y pregúntame
  antes**, explicando qué regla, por qué y qué alternativa propones. No sigas hasta tener mi
  respuesta. Si te das cuenta después de que ya te la saltaste, dilo explícitamente en el reporte
  final y propón cómo corregirlo.
- **No amplíes el alcance por tu cuenta.** Si ves algo útil que no se pidió (un caso borde, una
  validación, un refactor), propónlo y espera mi visto bueno, o sugiérelo como un issue aparte.
- **Plan primero** en cambios que toquen más de un módulo, el esquema de BD o reglas de cálculo:
  propón el plan y espera el visto bueno.
- **No inventes normativa.** Si no tienes certeza de una tasa, tope, exención o criterio legal,
  escribe `TODO(verificar-normativa): <qué falta>` y pregúntame. Nunca rellenes con números
  "aproximados".
- Cambios **pequeños y revisables**: un tema por PR, y tests en el mismo cambio.
- Antes de un procedimiento conocido, usa su skill: `add-payroll-concept`, `update-tax-tables`,
  `payroll-calculation-tests`, `db-migration`, `period-close`.
- **Git y GitHub:** antes de **cualquier** operación (rama, commit, push, merge, tag, issue, PR,
  etiquetas, release, CHANGELOG o ADR) carga y sigue la skill `git-workflow`.
- No instales dependencias ni hagas `git push` sin pedirlo; no leas `.env`.
- Al terminar, reporta qué comandos de verificación corriste y su resultado real.
