# Fuentes normativas (República Dominicana)

Fuente de verdad de los valores legales y de los criterios del proyecto. **Sin entrada aquí, no hay
tabla en el sistema.** Los valores se cargan en `RateTables` con la skill `update-tax-tables`; este
documento no reemplaza esa carga.

**Estados**

| Estado | Significado |
|---|---|
| `oficial` | Verificado en un documento oficial (enlace incluido). |
| `secundaria` | Confirmado en una fuente secundaria confiable; falta el enlace oficial. |
| `decisión del proyecto` | Criterio adoptado por el proyecto, no impuesto por una norma. |
| `pendiente` | Sin fuente suficiente. No se carga. |

Registrado por Ismel10 el 2026-11-11 (issues #11 y #12). Lo que sigue abierto está en el issue
"Seguimiento normativo".

---

<a id="redondeo"></a>
## Redondeo — `decisión del proyecto`

| Dato | Valor |
|---|---|
| Criterio | Redondeo aritmético convencional (half up) a 2 decimales, **para todos los montos** (DGII y TSS) |
| Base | Criterio de facturación electrónica de la DGII: apartado 13 del Informe Técnico de e-CF |
| TSS | No publica un criterio propio; el proyecto adopta el mismo |
| Implementación | `engine/money.py`: `ROUND_HALF_UP`, una vez por línea (ADR 0001) |

<a id="divisor"></a>
## Divisor del salario diario y por hora — práctica común, sin norma

| Dato | Valor |
|---|---|
| Días por mes | 23.83 |
| Horas por mes | 190.64 (23.83 × 8) |

**No es una regla del sistema:** cada empresa configura el divisor en su política de pago. Estos
valores solo sirven como referencia y para los datos de ejemplo.

<a id="tss-topes"></a>
## TSS: salario mínimo de referencia y topes — `oficial`

- **Norma:** Resolución TSS 01-2025, del 11-03-2025: https://www.tss.gob.do/assets/reso01-2025.pdf
- **Base:** Ley 87-01 y Resolución CNSS 151-10. **Cada seguro tiene su propio tope.**

| Vigente desde | Salario de referencia | Tope SRL | Tope SFS | Tope pensiones |
|---|---|---|---|---|
| 2025-04-01 | RD$21,674.80 | RD$86,699.20 | RD$216,748.00 | RD$433,496.00 |
| 2026-02-01 | RD$23,223.00 | RD$92,892.00 (4×) | RD$232,230.00 (10×) | RD$464,460.00 (20×) |

<a id="tss-tasas"></a>
## TSS: tasas — `oficial`

- **Fuente:** ABC No. 40 (feb. 2024), Generalidades del SDSS:
  https://dida.panel-dev-pys.ogtic.gob.do/wp-content/uploads/2024/10/ABC-No.-40-Febrero-2024-generalidades-del-Sistema-Dominicano-de-la-Seguridad-Social.pdf

| Seguro | Empleador | Empleado | Total |
|---|---|---|---|
| Pensiones | 7.10 % | 2.87 % | 9.97 % |
| SFS | 7.09 % | 3.04 % | 10.13 % |
| SRL | 1 % fijo + 0.1 % a 0.3 % según el riesgo de la actividad | — | — |
| **Totales** | 15.29 % a 15.49 % (con SRL de 0.1 % a 0.3 %) | 5.91 % | — |

El art. 199 de la Ley 87-01 permite un recargo SRL por riesgo de hasta 0.6 %.

<a id="isr-escala"></a>
## ISR asalariados, año fiscal 2026 — `oficial`

- **Fuente:** documento IR-3 de la DGII:
  https://dgii.gov.do/publicacionesOficiales/bibliotecaVirtual/contribuyentes/retencionesRetribucionesComplementarias/Documents/4-IR-3.pdf
- **Norma (`secundaria`):** Resolución DGII DDG-AR1-2026-00001 (escala 2026) y Ley 99-25, art. 45
  (suspende el ajuste por inflación en 2026).

| Renta anual | Impuesto |
|---|---|
| Hasta RD$416,220.00 | Exento |
| Hasta RD$624,329.00 | 15 % del excedente de RD$416,220.00 |
| Hasta RD$867,123.00 | RD$31,216.00 + 20 % del excedente de RD$624,329.00 |
| Por encima de RD$867,123.00 | RD$79,776.00 + 25 % del excedente de RD$867,123.00 |

- **Cuotas fijas:** se usan **los valores publicados**, aunque recalcularlas a partir de los tramos
  da una diferencia:
  - tramo 2: (624,329.00 − 416,220.00) × 15 % = 31,216.35; publicado 31,216.00 (**−0.35**);
  - tramo 3: 31,216.00 + (867,123.00 − 624,329.00) × 20 % = 79,774.80; publicado 79,776.00
    (**+1.20**).
- **Procedimiento:** renta gravable − AFP − SFS del empleado → anualizar → aplicar la escala →
  dividir entre 12.
- **Pago:** la IR-3 se paga a más tardar el día 10 del mes siguiente.

<a id="isr-2027"></a>
## ISR, año fiscal 2027 (versión futura) — `secundaria`

- **Norma:** Ley 30-26, promulgada el 2026-06-18; modifica el art. 296 del Código Tributario a partir
  del año fiscal 2027. Incluye un ajuste anual por inflación (Banco Central).

| Renta anual | Impuesto |
|---|---|
| Hasta RD$480,000 | Exento |
| Hasta RD$685,000 | 15 % del excedente de RD$480,000 |
| Hasta RD$910,000 | RD$30,750 + 20 % del excedente de RD$685,000 |
| Hasta RD$4,800,000 | RD$75,750 + 25 % del excedente de RD$910,000 |
| Por encima de RD$4,800,000 | RD$1,048,250 + 27 % del excedente de RD$4,800,000 |

**No se aplica a 2026.** No se carga hasta que la DGII publique la resolución de la escala 2027.

<a id="salario-minimo"></a>
## Salario mínimo, sector privado no sectorizado — `secundaria`

- **Norma:** Resolución CNS-01-2025 (la TSS la fecha el 3 de marzo de 2025): aumento del 12 % desde
  2025-04-01 y del 8 % desde 2026-02-01.
- **El valor legal es el mensual**; el valor por hora es derivado (mensual ÷ 190.64).

| Tamaño de empresa | Mensual desde 2026-02-01 | Por hora (derivado) |
|---|---|---|
| Grande | RD$29,988.00 | RD$157.30 |
| Mediana | RD$27,489.60 | RD$144.20 |
| Pequeña | RD$18,421.20 | RD$96.63 |
| Micro | RD$16,993.20 | RD$89.14 |

<a id="salario-minimo-sectorizado"></a>
## Salarios mínimos sectorizados (vigentes desde 2026-06-01) — `secundaria`

| Sector | Resolución | Mensual |
|---|---|---|
| Zonas francas | CNS-03-2025 | RD$20,875.00 |
| Hoteles y casinos, 151 empleados o más | CNS-04-2025 | RD$21,840.00 |
| Hoteles y casinos, hasta 150 empleados | CNS-04-2025 | RD$18,409.30 |
| Restaurantes, 151 empleados o más | CNS-04-2025 | RD$21,000.00 |
| Restaurantes, hasta 150 empleados | CNS-04-2025 | RD$17,701.25 |

<a id="aumento-2027"></a>
## Próximo aumento del salario mínimo — `pendiente`

El Comité Nacional de Salarios anunció (julio de 2026) un aumento para el sector no sectorizado a
partir de febrero de 2027, sin porcentaje publicado. **No se carga nada.**

<a id="jornada"></a>
## Jornada (Código de Trabajo, Ley 16-92) — `secundaria`

| Dato | Valor |
|---|---|
| Jornada máxima (art. 147) | 8 h diarias y 44 h semanales |
| Diurna / nocturna | Diurna de 7:00 a 21:00; nocturna de 21:00 a 7:00; mixta con menos de 3 h nocturnas |
| Trabajos peligrosos o insalubres | 6 h diarias y 36 h semanales |

<a id="horas-extra"></a>
## Horas extra y nocturnas (Código de Trabajo) — `secundaria`

| Dato | Recargo mínimo |
|---|---|
| Horas extra hasta 68 h semanales (art. 203) | No menor del 35 % sobre la hora normal |
| Horas extra por encima de 68 h semanales (art. 203) | No menor del 100 % |
| Hora nocturna (art. 204) | No menor del 15 % |

Son **mínimos legales**: una empresa puede pagar más, pero nunca menos.

<a id="licencias"></a>
## Licencias y ausencias

**1. Pagadas por el empleador**

| Licencia | Días | Norma | Estado |
|---|---|---|---|
| Matrimonio | 5 | Ley 16-92, art. 54 | `oficial` |
| Fallecimiento de abuelos, padres, hijos o compañera | 3 | Ley 16-92, art. 54 | `oficial` |
| Nacimiento de un hijo | 2 | Ley 16-92, art. 54 | `oficial` |
| Vacaciones | 14 días laborables desde el primer año; 18 desde el quinto | art. 177 | `secundaria` |
| Feriados | — | art. 165 | `secundaria` |
| Descanso semanal | 36 h | art. 163 | `secundaria` |
| Lactancia | 3 descansos de 20 min | art. 240 | `secundaria` |

Fuente oficial del art. 54: texto de la Ley 16-92 publicado por la SEGIB:
https://www.segib.org/wp-content/uploads/Textos-legales_Rep.Dominicana.pdf

**2. Cubiertas por subsidio (SISALRIL), fuera del MVP**

| Licencia | Detalle | Estado |
|---|---|---|
| Maternidad | 12 semanas (art. 236 del Código de Trabajo) | `secundaria` |
| Maternidad | 14 semanas (según otras fuentes) | `pendiente` |
| Enfermedad común con licencia médica | — | Solo clasificación |

**3. Justificadas sin disfrute de salario:** las define cada empresa (solo clasificación).

<a id="infotep"></a>
## INFOTEP — `secundaria`

| Dato | Valor |
|---|---|
| Empleador | 1 % de la nómina, sin tope |
| Empleado | 0.5 % de utilidades y bonificaciones (fuera del MVP) |
| Norma | Ley 116-80 (falta el enlace) |

<a id="reforma-codigo-trabajo"></a>
## Reforma del Código de Trabajo — `secundaria`, en seguimiento

**No es ley.** El proyecto del Senado (2025) perimió y fue reintroducido el 2026-08-27. Se sigue
aplicando la Ley 16-92; no cambia ningún valor de este documento.
