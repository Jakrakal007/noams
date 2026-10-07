from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import analysis, findings, health, pages, rules
from app.core.config import settings, PROJECT_ROOT
from app.core.exceptions import (
    AnalysisFileError,
    ResourceNotFoundError,
    RuleConfigurationError,
    analysis_file_exception_handler,
    global_exception_handler,
    resource_not_found_handler,
    rule_configuration_error_handler,
)
from app.core.logging_config import configure_logging
from app.database.migrations import run_migrations
from app.database.session import SessionLocal
from app.services.rules import rule_service

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    if not application.dependency_overrides:
        run_migrations()
        with SessionLocal() as db:
            if rule_service.ensure_default_rules(db):
                db.commit()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    docs_url="/docs",
    lifespan=lifespan,
)


@app.middleware("http")
async def handle_unexpected_errors(request, call_next):
    """Keep error responses controlled even when development debug is enabled."""
    try:
        return await call_next(request)
    except Exception as exc:
        return await global_exception_handler(request, exc)


app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "app/static")), name="static")
app.include_router(analysis.router)
app.include_router(findings.router)
app.include_router(health.router)
app.include_router(rules.router)
app.include_router(pages.router)
app.add_exception_handler(AnalysisFileError, analysis_file_exception_handler)
app.add_exception_handler(ResourceNotFoundError, resource_not_found_handler)
app.add_exception_handler(RuleConfigurationError, rule_configuration_error_handler)
app.add_exception_handler(Exception, global_exception_handler)
