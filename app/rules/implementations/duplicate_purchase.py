from decimal import Decimal

from app.rules.base import BusinessRule, FindingCandidate
from app.rules.context import RuleContext, normalize_key

MEDIUM_IMPACT = Decimal("500")
HIGH_IMPACT = Decimal("2000")
CRITICAL_IMPACT = Decimal("10000")


def impact_severity(amount: Decimal) -> str:
    if amount >= CRITICAL_IMPACT:
        return "critical"
    if amount >= HIGH_IMPACT:
        return "high"
    if amount >= MEDIUM_IMPACT:
        return "medium"
    return "low"


class DuplicatePurchaseRule(BusinessRule):
    code = "DUPLICATE_PURCHASE"
    name = "Potential Duplicate Purchase"
    description = "Detects matching suppliers, purchase orders, and amounts within a single run."
    category = "duplicate"

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        originals: dict[tuple[str, str, Decimal], object] = {}
        findings: list[FindingCandidate] = []
        for transaction in sorted(context.transactions, key=lambda item: item.source_row_number):
            purchase_order = (transaction.purchase_order or "").strip()
            if not purchase_order:
                continue
            key = (
                normalize_key(transaction.supplier_name),
                purchase_order.casefold(),
                transaction.total_amount,
            )
            original = originals.get(key)
            if original is None:
                originals[key] = transaction
                continue
            findings.append(
                FindingCandidate(
                    transaction_id=transaction.id,
                    title=self.name,
                    description=(
                        f"Match found for {transaction.supplier_name}, purchase order {purchase_order}, "
                        f"and amount S/ {transaction.total_amount:.2f}."
                    ),
                    category=self.category,
                    severity=impact_severity(transaction.total_amount),
                    detected_value=transaction.total_amount,
                    estimated_impact=transaction.total_amount,
                    confidence_score=Decimal("0.95"),
                    evidence={
                        "original_transaction_id": original.id,
                        "original_external_id": original.transaction_id,
                    },
                )
            )
        return findings
