from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.config import Settings
from app.database.models import AnalysisRun, Transaction
from app.rules.context import RuleContext
from app.rules.implementations import (
    BudgetDeviationRule,
    DuplicatePurchaseRule,
    SplitPurchaseRule,
    UnapprovedPurchaseRule,
    UnusualSupplierAmountRule,
)


def transaction(identifier: int, **overrides) -> Transaction:
    values = {
        "id": identifier,
        "analysis_run_id": 1,
        "transaction_id": f"TX-{identifier}",
        "transaction_date": date(2026, 7, 1),
        "supplier_name": "Proveedor Uno",
        "department": "Operaciones",
        "category": "Insumos",
        "quantity": Decimal("1"),
        "unit_price": Decimal("100"),
        "total_amount": Decimal("100"),
        "approval_status": "approved",
        "purchase_order": f"PO-{identifier}",
        "budget_amount": None,
        "currency": "PEN",
        "source_row_number": identifier + 1,
    }
    values.update(overrides)
    return Transaction(**values)


def context(items, history=None) -> RuleContext:
    return RuleContext(
        analysis_run=AnalysisRun(id=1, filename="test.csv"),
        transactions=items,
        historical_amounts=history or {},
        settings=Settings(),
        session=None,
    )


def test_duplicate_detects_only_subsequent_matching_purchase() -> None:
    items = [
        transaction(1, purchase_order="PO-1", total_amount=Decimal("4200")),
        transaction(2, purchase_order="PO-1", total_amount=Decimal("4200")),
        transaction(3, purchase_order="", total_amount=Decimal("4200")),
        transaction(4, purchase_order="PO-2", total_amount=Decimal("4200")),
    ]

    findings = DuplicatePurchaseRule().evaluate(context(items))

    assert len(findings) == 1
    assert findings[0].transaction_id == 2
    assert findings[0].estimated_impact == Decimal("4200")
    assert findings[0].severity == "high"
    assert findings[0].evidence["original_transaction_id"] == 1


@pytest.mark.parametrize(
    ("amount", "severity"),
    [("100", "low"), ("500", "medium"), ("2000", "high"), ("10000", "critical")],
)
def test_duplicate_severity(amount: str, severity: str) -> None:
    findings = DuplicatePurchaseRule().evaluate(
        context(
            [
                transaction(1, purchase_order="PO", total_amount=Decimal(amount)),
                transaction(2, purchase_order="PO", total_amount=Decimal(amount)),
            ]
        )
    )
    assert findings[0].severity == severity


def test_unusual_amount_requires_history_and_uses_median() -> None:
    item = transaction(1, total_amount=Decimal("3000"))
    rule = UnusualSupplierAmountRule()
    assert rule.evaluate(context([item], {"proveedor uno": [Decimal("100"), Decimal("200")]})) == []

    findings = rule.evaluate(
        context([item], {"proveedor uno": [Decimal("100"), Decimal("200"), Decimal("300")]})
    )
    assert len(findings) == 1
    assert findings[0].expected_value == Decimal("200")
    assert findings[0].estimated_impact == Decimal("2800")
    assert Decimal("0") <= findings[0].confidence_score <= Decimal("1")


def test_unusual_amount_ignores_normal_variation() -> None:
    item = transaction(1, total_amount=Decimal("350"))
    assert UnusualSupplierAmountRule().evaluate(
        context([item], {"proveedor uno": [Decimal("100"), Decimal("200"), Decimal("300")]})
    ) == []


@pytest.mark.parametrize(
    ("amount", "budget", "severity"),
    [("109", "100", "low"), ("110", "100", "medium"), ("125", "100", "high"), ("150", "100", "critical")],
)
def test_budget_deviation_calculates_percentage_and_severity(
    amount: str, budget: str, severity: str
) -> None:
    finding = BudgetDeviationRule().evaluate(
        context([transaction(1, total_amount=Decimal(amount), budget_amount=Decimal(budget))])
    )[0]
    assert finding.severity == severity
    assert finding.deviation_percentage == (Decimal(amount) - Decimal(budget)) / Decimal(budget) * 100


def test_budget_deviation_does_not_apply_without_budget() -> None:
    assert BudgetDeviationRule().evaluate(context([transaction(1)])) == []


@pytest.mark.parametrize(
    ("status", "amount", "severity"),
    [
        ("approved", "100", None),
        ("aprobado", "100", None),
        ("pending", "100", "medium"),
        ("pendiente", "5000", "high"),
        ("rejected", "100", "high"),
        ("rechazado", "10000", "critical"),
        ("no_aprobado", "100", "high"),
    ],
)
def test_unapproved_purchase_statuses(status: str, amount: str, severity: str | None) -> None:
    findings = UnapprovedPurchaseRule().evaluate(
        context([transaction(1, approval_status=status, total_amount=Decimal(amount))])
    )
    assert (findings[0].severity if findings else None) == severity


def test_split_purchase_detects_one_group_with_evidence() -> None:
    start = date(2026, 7, 1)
    items = [
        transaction(1, transaction_date=start, total_amount=Decimal("2600")),
        transaction(2, transaction_date=start + timedelta(days=2), total_amount=Decimal("2500")),
        transaction(3, transaction_date=start + timedelta(days=8), total_amount=Decimal("2500")),
    ]
    findings = SplitPurchaseRule().evaluate(context(items))
    assert len(findings) == 1
    assert findings[0].transaction_id is None
    assert findings[0].estimated_impact == Decimal("5100")
    assert findings[0].evidence["transaction_ids"] == [1, 2]


def test_split_purchase_rejects_outside_window_under_threshold_and_large_individual() -> None:
    start = date(2026, 7, 1)
    rule = SplitPurchaseRule()
    assert rule.evaluate(
        context(
            [
                transaction(1, transaction_date=start, total_amount=Decimal("3000")),
                transaction(2, transaction_date=start + timedelta(days=4), total_amount=Decimal("3000")),
            ]
        )
    ) == []
    assert rule.evaluate(
        context([transaction(1, total_amount=Decimal("1000")), transaction(2, total_amount=Decimal("2000"))])
    ) == []
    assert rule.evaluate(
        context([transaction(1, total_amount=Decimal("5000")), transaction(2, total_amount=Decimal("100"))])
    ) == []
