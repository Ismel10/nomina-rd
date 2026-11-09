"""Núcleo de cálculo de nómina.

Contrato (ver AGENTS.md §4):
- Funciones puras y deterministas: mismas entradas + mismas tablas = mismo resultado.
- Sin I/O, sin BD, sin logging, sin reloj (`datetime.now`), sin `float`.
- Solo biblioteca estándar. Verificado por tests/architecture/test_engine_purity.py.
"""
