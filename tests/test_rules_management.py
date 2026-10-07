from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.base import Base
from app.database.models import AnalysisRun, Finding, RuleConfiguration, RuleExecution, Transaction
from app.rules.context import RuleContext
from app.rules.engine import RuleEngine
from app.rules.implementations import BudgetDeviationRule, DuplicatePurchaseRule, SplitPurchaseRule, UnapprovedPurchaseRule, UnusualSupplierAmountRule
from app.services.rules import RULE_DEFINITIONS, rule_service
from app.services.analysis import analysis_service


def database():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine


def item(identifier: int, **updates):
    values = dict(id=identifier, analysis_run_id=1, transaction_id=f"TX-{identifier}", transaction_date=date(2026, 1, 1), supplier_name="Supplier", department="Operations", category="Materials", quantity=Decimal("1"), unit_price=Decimal("100"), total_amount=Decimal("100"), approval_status="approved", purchase_order=f"PO-{identifier}", budget_amount=None, currency="PEN", source_row_number=identifier + 1)
    values.update(updates)
    return Transaction(**values)


def context(items, code, configuration, history=None):
    return RuleContext(AnalysisRun(id=1, filename="rules.csv"), items, history or {}, Settings(), None, {code: {"enabled": True, "version": "1.0", "configuration": configuration}})


def test_default_catalog_is_idempotent_complete_unique_and_enabled():
    engine = database()
    with Session(engine) as db:
        assert rule_service.ensure_default_rules(db) == 5
        db.commit()
        assert rule_service.ensure_default_rules(db) == 0
        records = db.scalars(select(RuleConfiguration)).all()
        assert {record.rule_code for record in records} == set(RULE_DEFINITIONS)
        assert len({record.rule_code for record in records}) == 5
        assert all(record.enabled for record in records)


def test_disabled_rule_is_skipped_without_findings_and_keeps_snapshot():
    engine = database()
    with Session(engine) as db:
        run = AnalysisRun(filename="duplicate.csv", source_type="csv", status="processing")
        db.add(run); db.flush()
        first = item(1, analysis_run_id=run.id, purchase_order="PO", total_amount=Decimal("1000"))
        second = item(2, analysis_run_id=run.id, purchase_order="PO", total_amount=Decimal("1000"))
        db.add_all([first, second]); db.flush()
        config = {"DUPLICATE_PURCHASE": {"enabled": False, "version": "1.0", "configuration": {}}}
        findings, executions = RuleEngine([DuplicatePurchaseRule()]).execute(RuleContext(run, [first, second], {}, Settings(), db, config))
        db.commit()
        assert findings == []
        assert executions[0].status == "skipped"
        assert executions[0].skip_reason == "Rule disabled"
        assert executions[0].configuration_snapshot_json == {}
        assert db.scalar(select(Finding)) is None


def test_reenabled_rule_executes_normally():
    engine = database()
    with Session(engine) as db:
        run = AnalysisRun(filename="duplicate.csv", status="processing")
        db.add(run); db.flush()
        items = [item(1, analysis_run_id=run.id, purchase_order="PO"), item(2, analysis_run_id=run.id, purchase_order="PO")]
        db.add_all(items); db.flush()
        findings, executions = RuleEngine([DuplicatePurchaseRule()]).execute(RuleContext(run, items, {}, Settings(), db, {"DUPLICATE_PURCHASE": {"enabled": True, "version": "1.0", "configuration": {}}}))
        assert len(findings) == 1 and executions[0].status == "completed"


def test_split_purchase_uses_window_threshold_and_minimum_operations():
    start = date(2026, 1, 1)
    items = [item(1, transaction_date=start, total_amount=Decimal("2000")), item(2, transaction_date=start + timedelta(days=4), total_amount=Decimal("2000")), item(3, transaction_date=start + timedelta(days=4), total_amount=Decimal("2000"))]
    rule = SplitPurchaseRule()
    assert rule.evaluate(context(items, rule.code, {"approval_threshold": 5000, "window_days": 3, "minimum_operations": 2})) == []
    findings = rule.evaluate(context(items, rule.code, {"approval_threshold": 3500, "window_days": 5, "minimum_operations": 3}))
    assert len(findings) == 1 and findings[0].evidence["window_days"] == 5


def test_unusual_rule_uses_multiplier_and_minimum_history():
    rule = UnusualSupplierAmountRule(); target = item(1, total_amount=Decimal("500")); history = {"supplier": [Decimal("100"), Decimal("100")]}
    assert rule.evaluate(context([target], rule.code, {"minimum_history": 3, "multiplier": 3, "minimum_difference": 0}, history)) == []
    assert len(rule.evaluate(context([target], rule.code, {"minimum_history": 2, "multiplier": 4, "minimum_difference": 0}, history))) == 1
    assert rule.evaluate(context([target], rule.code, {"minimum_history": 2, "multiplier": 6, "minimum_difference": 0}, history)) == []


def test_budget_and_unapproved_rules_use_configured_thresholds():
    budget = BudgetDeviationRule()
    finding = budget.evaluate(context([item(1, total_amount=Decimal("120"), budget_amount=Decimal("100"))], budget.code, {"medium_threshold_percentage": 5, "high_threshold_percentage": 15, "critical_threshold_percentage": 30}))[0]
    assert finding.severity == "high"
    approval = UnapprovedPurchaseRule()
    finding = approval.evaluate(context([item(1, total_amount=Decimal("800"), approval_status="pending")], approval.code, {"approval_threshold": 500, "critical_multiplier": 2}))[0]
    assert finding.severity == "high"


def test_rules_api_lists_statistics_updates_validates_resets_and_returns_404(client):
    listing = client.get("/api/rules")
    assert listing.status_code == 200 and len(listing.json()["items"]) == 5
    assert "statistics" in listing.json()["items"][0]
    changed = client.patch("/api/rules/SPLIT_PURCHASE", json={"enabled": False, "configuration": {"window_days": 10}})
    assert changed.status_code == 200 and changed.json()["configuration"]["window_days"] == 10
    assert client.patch("/api/rules/SPLIT_PURCHASE", json={"configuration": {"unknown": 1}}).status_code == 422
    assert client.patch("/api/rules/BUDGET_DEVIATION", json={"configuration": {"medium_threshold_percentage": 30, "high_threshold_percentage": 20}}).status_code == 422
    assert client.patch("/api/rules/SPLIT_PURCHASE", json={"configuration": {"window_days": 0}}).status_code == 422
    reset = client.post("/api/rules/SPLIT_PURCHASE/reset")
    assert reset.status_code == 200 and reset.json()["enabled"] is True and reset.json()["configuration"] == RULE_DEFINITIONS["SPLIT_PURCHASE"].defaults
    assert client.get("/api/rules/UNKNOWN").status_code == 404


def test_patch_disables_and_enables_rule(client):
    assert client.get("/api/rules").status_code == 200
    disabled = client.patch("/api/rules/DUPLICATE_PURCHASE", json={"enabled": False, "configuration": {}})
    assert disabled.status_code == 200 and disabled.json()["enabled"] is False
    enabled = client.patch("/api/rules/DUPLICATE_PURCHASE", json={"enabled": True, "configuration": {}})
    assert enabled.status_code == 200 and enabled.json()["enabled"] is True


def test_patch_updates_each_configurable_rule(client):
    assert client.get("/api/rules").status_code == 200
    updates = {
        "UNUSUAL_SUPPLIER_AMOUNT": {"minimum_history": 4, "multiplier": 4.5, "minimum_difference": 750},
        "BUDGET_DEVIATION": {"medium_threshold_percentage": 12, "high_threshold_percentage": 30, "critical_threshold_percentage": 60},
        "UNAPPROVED_PURCHASE": {"approval_threshold": 6000, "critical_multiplier": 2.5},
        "SPLIT_PURCHASE": {"approval_threshold": 6000, "window_days": 5, "minimum_operations": 3},
    }
    for code, configuration in updates.items():
        response = client.patch(f"/api/rules/{code}", json={"enabled": True, "configuration": configuration})
        assert response.status_code == 200
        assert response.json()["configuration"] == configuration


def test_upload_executes_all_enabled_rules_and_rules_page_is_database_backed(client):
    csv_data = b"transaction_id,transaction_date,supplier_name,department,category,quantity,unit_price,total_amount,approval_status,purchase_order,budget_amount,currency\nTX-1,2026-01-01,Supplier,Ops,Materials,1,100,100,approved,PO-1,100,PEN\n"
    response = client.post("/api/analysis/upload", files={"file": ("rules.csv", csv_data, "text/csv")})
    assert response.status_code == 200
    assert len(response.json()["rule_executions"]) == 5
    assert all(execution["configuration_snapshot_json"] is not None for execution in response.json()["rule_executions"])
    page = client.get("/rules")
    assert page.status_code == 200 and page.text.count('data-rule-code="') == 5


def test_unusual_amount_uses_only_previous_completed_runs_and_generates_one_finding():
    engine = database()
    with Session(engine) as db:
        historical_run = AnalysisRun(filename="baseline.csv", source_type="csv", status="completed")
        db.add(historical_run); db.flush()
        historical = [
            item(index, analysis_run_id=historical_run.id, transaction_id=f"H-{index}", total_amount=Decimal("1000"))
            for index in range(1, 4)
        ]
        db.add_all(historical); db.flush()

        current_run = AnalysisRun(filename="current.csv", source_type="csv", status="processing")
        db.add(current_run); db.flush()
        current = item(10, analysis_run_id=current_run.id, transaction_id="CURRENT", total_amount=Decimal("5000"))
        db.add(current); db.flush()
        history = analysis_service._historical_amounts(db, current_run, [current])
        assert history == {"supplier": [Decimal("1000.00")] * 3}
        assert Decimal("5000.00") not in history["supplier"]

        configuration = {"UNUSUAL_SUPPLIER_AMOUNT": {"enabled": True, "version": "1.0", "configuration": {"minimum_history": 3, "multiplier": 3, "minimum_difference": 500}}}
        findings, executions = RuleEngine([UnusualSupplierAmountRule()]).execute(
            RuleContext(current_run, [current], history, Settings(), db, configuration)
        )
        db.commit()

        assert len(findings) == 1
        assert findings[0].rule_code == "UNUSUAL_SUPPLIER_AMOUNT"
        assert findings[0].analysis_run_id == current_run.id
        assert findings[0].transaction_id == current.id
        assert findings[0].expected_value == Decimal("1000.00")
        assert findings[0].evidence_json["observations"] == 3
        assert executions[0].status == "completed"
        assert executions[0].findings_generated == 1


def test_unusual_amount_normal_value_is_negative_and_disabled_rule_is_skipped():
    engine = database()
    with Session(engine) as db:
        historical_run = AnalysisRun(filename="baseline.csv", source_type="csv", status="completed")
        db.add(historical_run); db.flush()
        db.add_all([item(index, analysis_run_id=historical_run.id, total_amount=Decimal("1000")) for index in range(1, 4)])
        db.flush()

        normal_run = AnalysisRun(filename="normal.csv", source_type="csv", status="processing")
        db.add(normal_run); db.flush()
        normal = item(10, analysis_run_id=normal_run.id, total_amount=Decimal("1500"))
        db.add(normal); db.flush()
        history = analysis_service._historical_amounts(db, normal_run, [normal])
        enabled = {"UNUSUAL_SUPPLIER_AMOUNT": {"enabled": True, "version": "1.0", "configuration": {"minimum_history": 3, "multiplier": 3, "minimum_difference": 500}}}
        findings, executions = RuleEngine([UnusualSupplierAmountRule()]).execute(RuleContext(normal_run, [normal], history, Settings(), db, enabled))
        assert findings == [] and executions[0].status == "completed"

        disabled_run = AnalysisRun(filename="disabled.csv", source_type="csv", status="processing")
        db.add(disabled_run); db.flush()
        outlier = item(20, analysis_run_id=disabled_run.id, total_amount=Decimal("5000"))
        db.add(outlier); db.flush()
        disabled_history = analysis_service._historical_amounts(db, disabled_run, [outlier])
        disabled = {"UNUSUAL_SUPPLIER_AMOUNT": {"enabled": False, "version": "1.0", "configuration": {"minimum_history": 3, "multiplier": 3, "minimum_difference": 500}}}
        disabled_findings, disabled_executions = RuleEngine([UnusualSupplierAmountRule()]).execute(RuleContext(disabled_run, [outlier], disabled_history, Settings(), db, disabled))
        assert disabled_findings == []
        assert disabled_executions[0].status == "skipped"
        assert disabled_executions[0].skip_reason == "Rule disabled"
