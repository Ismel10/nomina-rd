# 0001. Criterio de redondeo de montos

- **Estado:** Propuesto
- **Fecha:** 2026-11-10
- **Issue / PR:** #7

## Contexto
El motor de nómina calcula montos en `decimal.Decimal` con precisión completa (base × tasa,
prorrateos), pero cada línea del volante, el archivo de dispersión y los reportes necesitan montos
en centavos de DOP. Hace falta un criterio único y explícito de **cuándo** y **cómo** se redondea,
para que:

- un cálculo hecho a mano coincida al centavo con el del sistema;
- el volante cuadre: la suma de las líneas impresas es igual al total impreso;
- el criterio esté en un solo lugar, para poder auditarlo o cambiarlo.

AGENTS.md §3.1 fija el criterio actual, y `backend/src/nomina/engine/money.py` (#1, PR #2) lo
implementa con `round_line` y `sum_lines`.

**Fuentes normativas:** no se han verificado todavía. No sabemos si la DGII (retención de ISR) o la
TSS (aportes AFP, SFS y SRL) establecen un modo de redondeo, ni si lo aplican por línea, sobre la
base o sobre el total. Ver `docs/normativa/fuentes.md#redondeo`.

## Decisión
Redondear con `ROUND_HALF_UP` a 2 decimales, **una sola vez por línea de concepto**, y solo en
`engine/money.py` (`round_line`). Los pasos intermedios conservan la precisión completa. Los totales
son la **suma de las líneas ya redondeadas** (`sum_lines`) y nunca se redondean por separado.

## Alternativas consideradas
- **`ROUND_HALF_EVEN` (redondeo bancario):** en el empate exacto de medio centavo redondea al par
  (0.125 → 0.12 y 0.135 → 0.14), lo que reduce el sesgo acumulado en grandes volúmenes. No se
  eligió porque es menos intuitivo de verificar a mano y porque no tenemos evidencia de que la
  normativa local lo exija. Si la verificación normativa lo indica, se cambia solo `ROUNDING_MODE`
  en `money.py`.
- **Redondear solo el total:** sumar las líneas a precisión completa y redondear al final. Se pierde
  menos precisión en el total, pero las líneas impresas (redondeadas para mostrarlas) dejarían de
  sumar el total impreso, y habría diferencias de centavos entre el volante, la dispersión y los
  reportes. Se descartó porque rompe la regla de que el volante cuadre.

## Consecuencias
- **Se gana:** un criterio único, testeado (casos a mano y propiedades con Hypothesis en
  `tests/unit/engine/test_money.py`) y fácil de auditar. Los totales cuadran por construcción.
- **Se pierde:** la suma de líneas redondeadas puede diferir en algunos centavos de un cálculo
  sobre el total a precisión completa. Es el costo aceptado de que el volante cuadre.
- **Sesgo:** en empates exactos, `ROUND_HALF_UP` siempre se aleja de cero, lo que puede acumular un
  pequeño sesgo en volúmenes grandes.
- **Pendiente:** `TODO(verificar-normativa)`: confirmar con la DGII y con la TSS el modo de
  redondeo y su punto de aplicación (por línea, sobre la base o sobre el total). Mientras tanto,
  este ADR sigue en estado **Propuesto**. Si la normativa difiere, se crea un ADR nuevo que
  reemplace a este (este no se edita), se ajusta `money.py` con TDD y se registra la fuente en
  `docs/normativa/fuentes.md`.
