from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.analysis import FindingResponse, FindingsPage
from app.services.findings import findings_service

router = APIRouter(prefix="/api/findings", tags=["findings"])


@router.get("", response_model=FindingsPage)
def list_findings(
    analysis_id: int | None = None,
    severity: Literal["low", "medium", "high", "critical"] | None = None,
    status: Literal["open", "under_review", "confirmed", "dismissed", "resolved"] | None = None,
    rule_code: str | None = None,
    category: Literal[
        "duplicate", "unusual_amount", "budget_deviation", "approval_risk", "split_purchase"
    ] | None = None,
    supplier_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> FindingsPage:
    return findings_service.list_findings(
        db,
        analysis_id=analysis_id,
        severity=severity,
        status=status,
        rule_code=rule_code,
        category=category,
        supplier_name=supplier_name,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/{finding_id}", response_model=FindingResponse)
def finding_detail(finding_id: int, db: Session = Depends(get_db)) -> FindingResponse:
    return findings_service.get_finding(db, finding_id)
