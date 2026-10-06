from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from app.core.config import settings
from app.core.database import Database
from app.core.logging import get_logger, setup_logging
from app.di.container import Container
from app.errors.base import ApplicationError
from app.errors.handlers import (
    application_error_handler,
    http_exception_handler,
    request_validation_exception_handler,
    unhandled_exception_handler,
)
from app.routers.coding import router as coding_router
from app.routers.terminology import router as terminology_router

setup_logging()
logger = get_logger(__name__)

container = Container()
db: Database = container.core.database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "🟢 Starting up the application",
        extra={
            "event": "startup.begin",
            "environment": settings.ENVIRONMENT,
            "log_level": settings.logging.level,
            "log_format": settings.logging.format,
        },
    )
    yield
    logger.info("🔴 Shutting down application...", extra={"event": "shutdown.begin"})
    await db.disconnect()
    logger.info("Database engine disposed.", extra={"event": "shutdown.db_disposed"})
    await container.core.embedding_client().close()
    await container.coding.jev_opencode().close()
    await container.coding.jev_vercel().close()


app: FastAPI = FastAPI(
    title="Open ICD Coder API",
    version="0.1.0",
    description=(
        "Prototype backend for AI-augmented medical coding: ICD-10-CM "
        "terminology search (Stage 1) and the coding pipeline — candidates, "
        "decision engine, human review (Stages 2-4). See docs/goal.md."
    ),
    lifespan=lifespan,
)

app.add_exception_handler(ApplicationError, application_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.container = container

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    terminology_router,
    prefix="/api/v1/terminology",
    tags=["Terminology"],
)

app.include_router(
    coding_router,
    prefix="/api/v1/coding",
    tags=["Coding"],
)


@app.get(
    "/health",
    operation_id="health_check",
    summary="Liveness probe",
    description="Returns 200 if the process is running. Does not check the database.",
    tags=["Health"],
)
async def health_check():
    return {"status": "ok"}


@app.get(
    "/health/ready",
    operation_id="readiness_check",
    summary="Readiness probe",
    description="Returns 200 only when the database is reachable.",
    tags=["Health"],
    responses={503: {"description": "Database unavailable"}},
)
async def readiness_check(request: Request):
    try:
        async with db.session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "checks": {"database": "ok"}}
    except Exception as exc:
        logger.error("Readiness: database check failed", exc_info=exc)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "checks": {"database": "unavailable"}},
        )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)
