from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.base import Base
from app.database.models import AnalysisRun, Finding, RuleExecution, Transaction
from app.rules.base import BusinessRule
from app.rules.context import RuleContext
from app.rules.engine import RuleEngine
from app.rules.implementations.unapproved_purchase import UnapprovedPurchaseRule


class FailingRule(BusinessRule):
    code = "FAIL_TEST"
    name = "Failing rule"
    description = "Test isolation"
    category = "test"

    def evaluate(self, context):
        raise RuntimeError("controlled test failure")


def test_engine_persists_traceability_and_continues_after_failure() -> None:
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        run = AnalysisRun(filename="test.csv", source_type="csv", status="processing")
        db.add(run)
        db.flush()
        item = Transaction(
            analysis_run_id=run.id,
            transaction_id="TX-1",
            transaction_date=date(2026, 7, 1),
            supplier_name="Proveedor",
            department="Operaciones",
            category="Insumos",
            quantity=Decimal("1"),
            unit_price=Decimal("1200"),
            total_amount=Decimal("1200"),
            approval_status="pending",
            purchase_order="PO-1",
            currency="PEN",
            source_row_number=2,
        )
        db.add(item)
        db.flush()
        context = RuleContext(run, [item], {}, Settings(), db)

        findings, executions = RuleEngine([FailingRule(), UnapprovedPurchaseRule()]).execute(context)
        db.commit()

        assert len(findings) == 1
        assert run.findings_count == 1
        assert [execution.status for execution in executions] == ["failed", "completed"]
        assert db.query(RuleExecution).count() == 2
        assert db.query(Finding).count() == 1
        assert findings[0].estimated_impact == Decimal("1200.00")
