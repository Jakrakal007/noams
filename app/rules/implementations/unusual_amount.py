from decimal import Decimal
from statistics import median

from app.rules.base import BusinessRule, FindingCandidate
from app.rules.context import RuleContext, normalize_key

HIGH_RATIO = Decimal("5")
CRITICAL_RATIO = Decimal("10")
HIGH_IMPACT = Decimal("5000")
CRITICAL_IMPACT = Decimal("20000")


class UnusualSupplierAmountRule(BusinessRule):
    code = "UNUSUAL_SUPPLIER_AMOUNT"
    name = "Unusual Supplier Amount"
    description = "Compares the amount with the supplier's historical median."
    category = "unusual_amount"

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        configuration = context.configuration_for(self.code)
        minimum_history = int(configuration.get("minimum_history", context.settings.noams_unusual_min_history))
        multiplier = Decimal(str(configuration.get("multiplier", context.settings.noams_unusual_multiplier)))
        minimum_difference = Decimal(str(configuration.get("minimum_difference", context.settings.noams_unusual_min_difference)))
        findings: list[FindingCandidate] = []
        for transaction in context.transactions:
            history = context.historical_amounts.get(normalize_key(transaction.supplier_name), [])
            if len(history) < minimum_history:
                continue
            historical_median = Decimal(str(median(history)))
            if historical_median <= 0:
                continue
            ratio = transaction.total_amount / historical_median
            difference = transaction.total_amount - historical_median
            if (
                ratio < multiplier
                or difference < minimum_difference
            ):
                continue
            severity = "medium"
            if ratio >= CRITICAL_RATIO or difference >= CRITICAL_IMPACT:
                severity = "critical"
            elif ratio >= HIGH_RATIO or difference >= HIGH_IMPACT:
                severity = "high"
            # Confidence grows deterministically with sample size and deviation.
            confidence = min(
                Decimal("0.99"),
                Decimal("0.65")
                + Decimal(min(len(history), 10)) * Decimal("0.02")
                + min(ratio, Decimal("10")) * Decimal("0.01"),
            )
            findings.append(
                FindingCandidate(
                    transaction_id=transaction.id,
                    title=self.name,
                    description=(
                        f"The amount S/ {transaction.total_amount:.2f} is {ratio:.2f} times "
                        f"the historical median for {transaction.supplier_name}."
                    ),
                    category=self.category,
                    severity=severity,
                    detected_value=transaction.total_amount,
                    expected_value=historical_median,
                    deviation_percentage=(difference / historical_median * 100),
                    estimated_impact=max(difference, Decimal("0")),
                    confidence_score=confidence,
                    evidence={
                        "observations": len(history),
                        "median": str(historical_median),
                        "minimum": str(min(history)),
                        "maximum": str(max(history)),
                        "ratio": str(ratio),
                    },
                )
            )
        return findings
