from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings, PROJECT_ROOT
from app.database.session import get_db
from app.services.analysis import analysis_service
from app.services.rules import rule_service

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app/templates"))


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    summary = analysis_service.dashboard_summary(db)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "summary": summary,
            "active_page": "dashboard",
        },
    )


@router.get("/analysis", response_class=HTMLResponse)
def analysis_history_page(
    request: Request,
    filename: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    analyses = analysis_service.list_analyses(
        db, limit=50, offset=0, filename=filename, status=status
    )
    return templates.TemplateResponse(
        request=request,
        name="analysis.html",
        context={
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "active_page": "analysis",
            "analyses": analyses,
            "filename_filter": filename or "",
            "status_filter": status or "",
        },
    )


@router.get("/analysis/{analysis_id}", response_class=HTMLResponse)
def analysis_detail_page(
    request: Request, analysis_id: int, db: Session = Depends(get_db)
):
    analysis = analysis_service.get_analysis(db, analysis_id)
    return templates.TemplateResponse(
        request=request,
        name="analysis_detail.html",
        context={
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "active_page": "analysis",
            "analysis": analysis,
        },
    )


@router.get("/rules", response_class=HTMLResponse)
def rules_page(request: Request, db: Session = Depends(get_db)):
    rules = rule_service.list_rules(db)
    return templates.TemplateResponse(
        request=request,
        name="rules.html",
        context={"app_name": settings.app_name, "environment": settings.app_env, "active_page": "rules", "rules": rules},
    )
