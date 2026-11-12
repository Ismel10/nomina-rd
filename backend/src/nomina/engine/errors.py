"""Errores del motor de nómina.

Ambos heredan de `ValueError`. Sus mensajes **nunca incluyen montos** (salarios, tarifas: datos
sensibles, AGENTS.md §3.6); sí pueden nombrar códigos (tipo de ausencia, grupo, categoría).
"""


class PayrollConfigError(ValueError):
    """La configuración (política de la empresa, grupos o tablas legales) es inválida o
    incompleta: por ejemplo, no hay regla para un tipo de ausencia."""


class PayrollInputError(ValueError):
    """Los datos de entrada del cálculo (periodo, contrato, novedades) son inconsistentes."""
