from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.paths import ensure_data_directories
from app.api.v1 import api_v1_router
from app.schemas import HealthResponse, ErrorResponse
from app.services.water_body_service import (
    WaterBodyConflictError,
    WaterBodyNotFoundError,
)
from app.services.storage_service import StoragePathTraversalError

logger = logging.getLogger("jalnetra")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup centralized logging
    setup_logging(level="DEBUG" if settings.DEBUG else "INFO")
    logger.info("Starting up %s v%s...", settings.APP_NAME, settings.APP_VERSION)

    # Ensure data directory hierarchy exists
    ensure_data_directories(settings.resolved_data_dir)
    logger.info("Storage directories initialized at: %s", settings.resolved_data_dir)
    logger.info("Database URL: %s", settings.resolved_database_url)

    yield

    logger.info("Shutting down %s...", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="JalNetra 2.0 - Geospatial Water Monitoring Platform API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS configuration
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Root health endpoint
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    def root_health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.APP_NAME,
            version=settings.APP_VERSION,
        )

    # API v1 routes (includes /health, /water-bodies, /storage)
    app.include_router(api_v1_router, prefix="/api/v1")

    # Domain specific exception handlers
    @app.exception_handler(WaterBodyNotFoundError)
    async def not_found_handler(request: Request, exc: WaterBodyNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error={"code": "NOT_FOUND", "message": str(exc)}
            ).model_dump(),
        )

    @app.exception_handler(WaterBodyConflictError)
    async def conflict_handler(request: Request, exc: WaterBodyConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(
                error={"code": "CONFLICT", "message": str(exc)}
            ).model_dump(),
        )

    @app.exception_handler(StoragePathTraversalError)
    async def traversal_handler(request: Request, exc: StoragePathTraversalError):
        logger.warning("Security alert: path traversal attempt: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error={"code": "INVALID_PATH", "message": "Invalid storage path specified."}
            ).model_dump(),
        )

    # Global Exception Handlers for consistent API error responses
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning("HTTP %s error on %s: %s", exc.status_code, request.url.path, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error={
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                }
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error={
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters or payload",
                }
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled error processing %s: %s", request.url.path, str(exc), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error={
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal server error occurred.",
                }
            ).model_dump(),
        )

    return app


app = create_app()
