# Hoja de cálculo manual: caso <ID>

> Datos ficticios. Completar ANTES de escribir el test.

## Entradas
| Campo | Valor |
|---|---|
| Empresa (ficticia) | Ejemplo SRL |
| Empleado (ficticio) | Ana Ficticia Pérez, cédula 000-0000000-0 |
| Salario mensual | 0.00 |
| Frecuencia / periodo | quincenal, 2026-01-01 → 2026-01-15, pago 2026-01-15 |
| Novedades | (horas extra, ausencias…) |

## Tablas usadas
| Tabla | Versión | Vigente desde | Fuente |
|---|---|---|---|
| ISR_ANNUAL_SCALE | | | docs/normativa/fuentes.md#… |
| TSS_RATES | | | |

## Paso a paso (sin redondear hasta "Redondeo")
| # | Concepto | Base | Tasa / fórmula | Exacto | Redondeo (HALF_UP 0.01) |
|---|---|---|---|---|---|
| 1 | Salario ordinario | | | | |
| 2 | AFP empleado | | | | |
| 3 | SFS empleado | | | | |
| 4 | Base gravable ISR | | | | |
| 5 | ISR | | | | |

## Totales (suma de líneas ya redondeadas)
| Total | Valor |
|---|---|
| Ingresos (bruto) | |
| Descuentos | |
| Neto | |
| Aportes patronales | |

## Verificaciones
- [ ] bruto − descuentos = neto
- [ ] Cada línea con exactamente 2 decimales
- [ ] Puntos con `TODO(verificar-normativa)`: …
