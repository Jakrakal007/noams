import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db

router = APIRouter(prefix="/api", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Report application status after checking the database connection."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.error("Database health check failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unavailable",
                "application": settings.app_name,
                "environment": settings.app_env,
                "database": "disconnected",
            },
        ) from exc

    return {
        "status": "operational",
        "application": settings.app_name,
        "environment": settings.app_env,
        "database": "connected",
    }
