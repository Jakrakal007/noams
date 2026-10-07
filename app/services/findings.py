from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ResourceNotFoundError
from app.database.models import Finding, Transaction
from app.schemas.analysis import FindingResponse, FindingsPage
from app.services.analysis import analysis_service


class FindingsService:
    def list_findings(
        self,
        db: Session,
        *,
        analysis_id: int | None,
        severity: str | None,
        status: str | None,
        rule_code: str | None,
        category: str | None,
        supplier_name: str | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> FindingsPage:
        filters = []
        if analysis_id is not None:
            filters.append(Finding.analysis_run_id == analysis_id)
        if severity:
            filters.append(Finding.severity == severity)
        if status:
            filters.append(Finding.status == status)
        if rule_code:
            filters.append(Finding.rule_code == rule_code)
        if category:
            filters.append(Finding.category == category)

        query = select(Finding).options(joinedload(Finding.transaction))
        count_query = select(func.count(Finding.id))
        needs_transaction = supplier_name is not None or date_from is not None or date_to is not None
        if needs_transaction:
            query = query.join(Transaction)
            count_query = count_query.join(Transaction)
        if supplier_name:
            filters.append(func.lower(Transaction.supplier_name).contains(supplier_name.casefold()))
        if date_from:
            filters.append(Transaction.transaction_date >= date_from)
        if date_to:
            filters.append(Transaction.transaction_date <= date_to)

        severity_order = case(
            (Finding.severity == "critical", 0),
            (Finding.severity == "high", 1),
            (Finding.severity == "medium", 2),
            (Finding.severity == "low", 3),
            else_=4,
        )
        total = db.scalar(count_query.where(*filters)) or 0
        findings = db.scalars(
            query.where(*filters)
            .order_by(severity_order, Finding.estimated_impact.desc(), Finding.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return FindingsPage(
            page=page,
            page_size=page_size,
            total=total,
            items=[analysis_service.finding_schema(item, item.transaction) for item in findings],
        )

    def get_finding(self, db: Session, finding_id: int) -> FindingResponse:
        finding = db.scalar(
            select(Finding)
            .where(Finding.id == finding_id)
            .options(joinedload(Finding.transaction))
        )
        if finding is None:
            raise ResourceNotFoundError("finding_not_found", "The requested finding does not exist.")
        return analysis_service.finding_schema(finding, finding.transaction)


findings_service = FindingsService()
