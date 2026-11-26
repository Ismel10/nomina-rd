# Plan general de desarrollo (roadmap)

Fuente única del orden de trabajo. Cada paso tiene su issue y su PR (skill `git-workflow`). Reúne el
backlog original del MVP y lo aprendido del análisis de nóminas reales
(`docs/analisis/nominas-reales-2026.md`, #21).

**Estados:** ✅ hecho · 🔄 en curso · ⏳ pendiente.

## MVP

### Base del proyecto (hecho)

| Paso | Qué | Estado | Issue / PR |
|---|---|---|---|
| — | Andamiaje del monorepo, `AGENTS.md`, skills | ✅ | commit inicial |
| — | CI con GitHub Actions (backend) | ✅ | #3 / #4 |
| — | Reglas de TDD estricto y de no desviarse sin preguntar | ✅ | #5 / #6 |
| — | ADR 0001 (redondeo) y guarda "solo `money.py` redondea" | ✅ | #7 / #9, #8 / #10 |
| — | Normativa verificada (`fuentes.md`), ADR 0001 aceptado | ✅ | #11, #12 / #14 |

### Motor de cálculo

| Paso | Qué | Estado | Issue / PR |
|---|---|---|---|
| 1 | Dinero: `to_decimal`, `round_line`, `sum_lines` | ✅ | #1 / #2 |
| 2a-1 | Modelos, política de pago, grupos, cascada de reglas, ADR 0002 | ✅ | #15 / #16 |
| 2a-2 (i) | Forma del periodo y prorrateo (`CALENDAR_FRACTION`, `COMMERCIAL_30`) | ✅ | #17 / #18 |
| 2a-2 (ii) | `calculate` con salario fijo, ausencias, art. 54 y tope | ✅ | #19 / #20 |
| **2c** | **Métodos de prorrateo** `WORKING_DAYS` (días laborables del tramo con contrato como dato, con medios días, sin restar ausencias) y `NO_PRORATION` (periodo completo); método configurable **por contrato**, por encima del de la empresa. **ADR 0003** (amplía el ADR 0002). | ⏳ | #22 |
| 2b | Pago por horas (`HOURLY`): horas × tarifa resuelta en cascada (contrato → grupo → empresa); tarifa no menor que el mínimo por hora derivado de la política | ⏳ | sin issue |
| **2d** | **Ingresos recurrentes por contrato** (incentivo fijo): monto fijo, cada periodo o solo en la primera quincena | ⏳ | #23 |
| 3 | TSS (ver detalle) | ⏳ | sin issue |
| 4 | ISR (ver detalle) | ⏳ | sin issue |
| 5 | Horas extra, nocturnidad y feriados (ver detalle) | ⏳ | sin issue |
| **5b** | **Préstamos:** cuota por quincena (en nómina mensual, suma de las cuotas del mes); el motor recibe cuota y saldo como datos y nunca descuenta más que el saldo | ⏳ | #24 |

### Persistencia, periodos y salida

| Paso | Qué | Estado | Issue / PR |
|---|---|---|---|
| 6 | Persistencia multiempresa: empresa, empleado, **contrato versionado**, tablas con vigencia (`EXCLUDE`), `audit_log`; aislamiento entre tenants; seed ficticio; **saldo de préstamos** | ⏳ | #26 |
| 7 | Servicio de periodos: máquina de estados, calcular y recalcular, versión de cada tabla y política usada | ⏳ | sin issue |
| **7b** | **Nómina mensual con adelanto quincenal:** se calcula el mes; adelanto en la primera quincena y resto al final; convive con quincenal y mensual | ⏳ | #25 |
| 8 | Cierre de periodo e inmutabilidad (trigger) y ajustes | ⏳ | sin issue |
| 9 | Documentos: volante PDF y dispersión CSV con hash | ⏳ | sin issue |
| 10 | API y SPA; CI del frontend (requiere `package-lock.json`) | ⏳ | sin issue |
| 11 | **Corrida en paralelo** con los Excel de la firma durante al menos un periodo, documentando cada diferencia (se esperan diferencias de centavos por redondeo, ADR 0001) | ⏳ | sin issue |

### Detalle de los pasos 3, 4 y 5 (para cuando se creen sus issues)

**3. TSS**
- Marca "cotiza TSS" **por concepto**, configurable (hoy las empresas cotizan solo sobre el sueldo base; `TODO(verificar-normativa)`).
- Topes por seguro con vigencia (`fuentes.md#tss-topes`) y tasas (`fuentes.md#tss-tasas`).
- Tasa SRL por empresa, validada entre 1 % y 1.6 % (1 % + recargo por riesgo de hasta 0.6 %, art. 199).
- Per cápita adicional como descuento al empleado.
- Aportes patronales (AFP, SFS, SRL e INFOTEP 1 % sin tope) en el volante.
- Pendiente con la firma: cómo se aplica el tope mensual en una nómina quincenal.

**4. ISR**
- Marca "grava ISR" **por concepto** (incluye incentivos y horas extra).
- Base: ingresos gravados − AFP − SFS − per cápita adicional (`TODO(verificar-normativa)` del per cápita); anualizar, aplicar la escala y dividir entre 12.
- **Exención del ISR** con motivo obligatorio, vigencia y registro en la auditoría; nunca un ISR en 0 sin explicación.
- Escala 2027 (Ley 30-26) como versión futura, sin cargar hasta que la DGII publique su resolución.
- Pendiente con la firma: retención del ISR en una nómina quincenal.

**5. Horas extra, nocturnidad y feriados**
- Recargos mínimos legales en tabla: 35 % hasta 68 h semanales, 100 % por encima, 15 % nocturno (`fuentes.md#horas-extra`); la empresa puede pagar más, nunca menos.
- Feriado trabajado: un día extra de salario (recargo del 100 %; `TODO(verificar-normativa)`).
- Novedades que separen horas ordinarias, extra (≤ 68 h y > 68 h), nocturnas y feriados trabajados.

### Por qué este orden

- **2c antes que 2b:** el prorrateo por días laborados es lo que usan casi todas las nóminas reales; el pago por horas es menos frecuente.
- **2d antes que 3 (cambio respecto de la propuesta original):** los ingresos recurrentes son un concepto simple del motor, y tenerlos antes de la TSS y el ISR permite diseñar las marcas "cotiza TSS" y "grava ISR" con varios ingresos reales (salario e incentivo), no solo con el salario.
- **5b después de 4:** los préstamos son "otros descuentos", que se evalúan después del ISR (orden de la skill `add-payroll-concept`). La parte del motor no necesita base de datos; el **saldo** persistente queda en el paso 6.
- **7b después de 7:** el adelanto es un pago dentro de un periodo mensual, no un periodo de cálculo; depende de la máquina de estados de periodos y de la dispersión.

## Fase siguiente (fuera del MVP)

| Qué | Prioridad |
|---|---|
| **Vacaciones** (pagadas por adelantado, con su ISR) | **Alta** |
| Control de asistencia | Media |
| Salario de Navidad, prestaciones laborales, bonificación | Ver `AGENTS.md` §1 |
| Archivos oficiales TSS (SUIR+) y DGII (IR-3, IR-13) | Ver `AGENTS.md` §1 |
