# 0001. Criterio de redondeo de montos

- **Estado:** Aceptado (2026-11-11)
- **Fecha:** 2026-11-10
- **Issue / PR:** #7 (propuesto), #11 (verificación normativa)

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

**Fuentes normativas** (ver `docs/normativa/fuentes.md#redondeo`):
- **DGII:** el criterio de facturación electrónica es el redondeo aritmético convencional (half up)
  a 2 decimales (apartado 13 del Informe Técnico de e-CF).
- **TSS:** no publica un criterio de redondeo propio.
- **Proyecto:** adopta el criterio de la DGII para **todos** los montos (DGII y TSS). Es una
  `decisión del proyecto`, no una norma que lo imponga para la nómina.

## Decisión
Para todos los montos (DGII y TSS), redondear con `ROUND_HALF_UP` a 2 decimales, **una sola vez por
línea de concepto**, y solo en
`engine/money.py` (`round_line`). Los pasos intermedios conservan la precisión completa. Los totales
son la **suma de las líneas ya redondeadas** (`sum_lines`) y nunca se redondean por separado.

## Alternativas consideradas
- **`ROUND_HALF_EVEN` (redondeo bancario):** en el empate exacto de medio centavo redondea al par
  (0.125 → 0.12 y 0.135 → 0.14), lo que reduce el sesgo acumulado en grandes volúmenes. No se
  eligió porque la DGII usa half up en e-CF, la TSS no publica otro criterio y es menos intuitivo
  de verificar a mano.
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
- **Revisión futura:** si la DGII o la TSS publican un criterio de redondeo distinto para la nómina,
  se crea un ADR nuevo que reemplace a este (este no se edita), se ajusta `money.py` con TDD y se
  registra la fuente en `docs/normativa/fuentes.md`.
