from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.analysis import (
    AnalysisDetail,
    AnalysisHistoryItem,
    AnalysisResponse,
    DashboardSummary,
)
from app.services.analysis import analysis_service

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/upload", response_model=AnalysisResponse)
async def upload_analysis(
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    return await analysis_service.process_upload(file, db)


@router.get("/metrics", response_model=DashboardSummary)
def dashboard_metrics(db: Session = Depends(get_db)) -> DashboardSummary:
    return analysis_service.dashboard_summary(db)


@router.get("", response_model=list[AnalysisHistoryItem])
def analysis_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    filename: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[AnalysisHistoryItem]:
    return analysis_service.list_analyses(
        db, limit=limit, offset=offset, filename=filename, status=status
    )


@router.get("/{analysis_id}", response_model=AnalysisDetail)
def analysis_detail(analysis_id: int, db: Session = Depends(get_db)) -> AnalysisDetail:
    return analysis_service.get_analysis(db, analysis_id)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)) -> Response:
    analysis_service.delete_analysis(db, analysis_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
