from decimal import Decimal

from app.rules.base import BusinessRule, FindingCandidate
from app.rules.context import RuleContext

MEDIUM_DEVIATION = Decimal("10")
HIGH_DEVIATION = Decimal("25")
CRITICAL_DEVIATION = Decimal("50")


class BudgetDeviationRule(BusinessRule):
    code = "BUDGET_DEVIATION"
    name = "Budget Deviation"
    description = "Detects purchases that exceed their stated budget."
    category = "budget_deviation"

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        configuration = context.configuration_for(self.code)
        medium_threshold = Decimal(str(configuration.get("medium_threshold_percentage", MEDIUM_DEVIATION)))
        high_threshold = Decimal(str(configuration.get("high_threshold_percentage", HIGH_DEVIATION)))
        critical_threshold = Decimal(str(configuration.get("critical_threshold_percentage", CRITICAL_DEVIATION)))
        findings: list[FindingCandidate] = []
        for transaction in context.transactions:
            budget = transaction.budget_amount
            if budget is None or budget <= 0 or transaction.total_amount <= budget:
                continue
            excess = transaction.total_amount - budget
            deviation = excess / budget * 100
            severity = "low"
            if deviation >= critical_threshold:
                severity = "critical"
            elif deviation >= high_threshold:
                severity = "high"
            elif deviation >= medium_threshold:
                severity = "medium"
            findings.append(
                FindingCandidate(
                    transaction_id=transaction.id,
                    title=self.name,
                    description=f"The purchase exceeds the budget by {deviation:.2f}%.",
                    category=self.category,
                    severity=severity,
                    detected_value=transaction.total_amount,
                    expected_value=budget,
                    deviation_percentage=deviation,
                    estimated_impact=excess,
                    confidence_score=Decimal("1.0"),
                    evidence={"currency": transaction.currency},
                )
            )
        return findings
