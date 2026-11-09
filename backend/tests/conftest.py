"""Configuración global de pytest."""

from hypothesis import settings

# Perfil por defecto rápido; `pytest --hypothesis-profile=ci` para más ejemplos.
settings.register_profile("default", max_examples=200)
settings.register_profile("ci", max_examples=2000, deadline=None)
settings.load_profile("default")
