"""FastAPI application factory."""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.base import init_db
from api.routers import market, products, margins, health

logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting API server...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down API server...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Torob Intelligence Platform API",
        description="Read-only analytics API for Bosch product market intelligence",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS
    origins = os.getenv("API_CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(market.router)
    app.include_router(products.router)
    app.include_router(margins.router)
    app.include_router(health.router)

    return app


app = create_app()
