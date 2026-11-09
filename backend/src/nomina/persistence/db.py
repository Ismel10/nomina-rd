"""Engine y sesiones de base de datos (creación perezosa: importar no conecta)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from nomina.config import get_settings


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL no está configurada (ver .env.example)")
    return create_engine(url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """Dependencia FastAPI: una sesión por request."""
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    with factory() as session:
        yield session
