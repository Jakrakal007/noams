from collections import defaultdict
from decimal import Decimal

from app.rules.base import BusinessRule, FindingCandidate
from app.rules.context import RuleContext, normalize_key


class SplitPurchaseRule(BusinessRule):
    code = "SPLIT_PURCHASE"
    name = "Potential Split Purchase"
    description = "Detects groups of closely timed purchases that collectively exceed the threshold."
    category = "split_purchase"

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        configuration = context.configuration_for(self.code)
        threshold = Decimal(str(configuration.get("approval_threshold", context.settings.noams_approval_threshold)))
        window_days = int(configuration.get("window_days", context.settings.noams_split_window_days))
        minimum_operations = int(configuration.get("minimum_operations", context.settings.noams_split_min_operations))
        groups: dict[tuple[str, str, str], list] = defaultdict(list)
        for transaction in context.transactions:
            if transaction.total_amount < threshold:
                groups[
                    (
                        normalize_key(transaction.supplier_name),
                        normalize_key(transaction.department),
                        normalize_key(transaction.category),
                    )
                ].append(transaction)

        findings: list[FindingCandidate] = []
        for transactions in groups.values():
            ordered = sorted(transactions, key=lambda item: (item.transaction_date, item.id))
            consumed: set[int] = set()
            for start_index, first in enumerate(ordered):
                if first.id in consumed:
                    continue
                window = [
                    item
                    for item in ordered[start_index:]
                    if item.id not in consumed
                    and (item.transaction_date - first.transaction_date).days
                    <= window_days
                ]
                total = sum((item.total_amount for item in window), Decimal("0"))
                if len(window) < minimum_operations or total < threshold:
                    continue
                consumed.update(item.id for item in window)
                severity = "medium"
                if total >= threshold * 5:
                    severity = "critical"
                elif total >= threshold * 2:
                    severity = "high"
                findings.append(
                    FindingCandidate(
                        title=self.name,
                        description=(
                            f"{len(window)} purchases from {first.supplier_name} total S/ {total:.2f} "
                            f"within a {window_days}-day window."
                        ),
                        category=self.category,
                        severity=severity,
                        detected_value=total,
                        expected_value=threshold,
                        estimated_impact=total,
                        confidence_score=Decimal("0.75"),
                        evidence={
                            "transaction_ids": [item.id for item in window],
                            "external_transaction_ids": [item.transaction_id for item in window],
                            "dates": [item.transaction_date.isoformat() for item in window],
                            "amounts": [str(item.total_amount) for item in window],
                            "total": str(total),
                            "threshold": str(threshold),
                            "window_days": window_days,
                        },
                    )
                )
        return findings
