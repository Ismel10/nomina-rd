"""Entorno de Alembic: toma DATABASE_URL de la configuración de la app."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from nomina.config import get_settings
from nomina.persistence.base import Base

# Importar aquí los módulos de modelos para que autogenerate los vea:
# from nomina.persistence import models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL no está configurada (ver .env.example)")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
