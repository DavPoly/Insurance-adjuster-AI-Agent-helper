import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.constants.api.triage_route_error_codes import (
    INTAKE_VALIDATION_FAILED_ERROR_CODE,
    SAFETY_CHECK_FAILED_ERROR_CODE,
)
from app.constants.api.unexpected_error_response import (
    UNEXPECTED_ERROR_CODE,
    UNEXPECTED_ERROR_MESSAGE,
)
from app.dependencies import get_decision_model_client, get_qdrant_client
from app.rag.vector_db_readiness import wait_for_vector_db_ready
from app.routers import health, triage
from app.routers.triage_exceptions import IntakeValidationFailed, SafetyCheckFailed
from app.routers.triage_schemas import SafetyErrorOut, ValidationErrorOut

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = get_qdrant_client()
    if wait_for_vector_db_ready(client):
        logger.info("Vector DB is ready.")
    else:
        logger.error("Vector DB did not become ready; /health will report it as disconnected.")
    yield
    await get_decision_model_client().aclose()
    get_decision_model_client.cache_clear()


app = FastAPI(
    title="Claim Triage API",
    description="AI-powered property damage claim triage system",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)
app.include_router(health.router, prefix="/api/v1")
app.include_router(triage.router, prefix="/api/v1")


@app.exception_handler(IntakeValidationFailed)
async def handle_intake_validation_failed(
    request: Request, exc: IntakeValidationFailed
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ValidationErrorOut(
            error=INTAKE_VALIDATION_FAILED_ERROR_CODE,
            intake_validation=exc.intake_validation,
            message=exc.message,
        ).model_dump(),
    )


@app.exception_handler(SafetyCheckFailed)
async def handle_safety_check_failed(request: Request, exc: SafetyCheckFailed) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=SafetyErrorOut(
            error=SAFETY_CHECK_FAILED_ERROR_CODE,
            safety_checks=exc.safety_checks,
            message=exc.message,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": UNEXPECTED_ERROR_CODE, "message": UNEXPECTED_ERROR_MESSAGE},
    )
