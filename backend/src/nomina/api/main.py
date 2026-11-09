"""Punto de entrada de la API: `uvicorn nomina.api.main:app --reload`."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from nomina import __version__
from nomina.config import get_settings


class HealthResponse(BaseModel):
    status: str
    version: str
    country: str
    currency: str


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Nómina RD", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse, tags=["sistema"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=__version__,
            country=settings.payroll_country,
            currency=settings.default_currency,
        )

    return app


app = create_app()
