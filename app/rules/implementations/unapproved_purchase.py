from decimal import Decimal

from app.rules.base import BusinessRule, FindingCandidate
from app.rules.context import RuleContext, normalize_key


PENDING = {"pending", "pendiente"}
REJECTED = {"rejected", "rechazado", "unapproved", "no_aprobado"}


class UnapprovedPurchaseRule(BusinessRule):
    code = "UNAPPROVED_PURCHASE"
    name = "Purchase Without Valid Approval"
    description = "Identifies pending, rejected, or unapproved purchases."
    category = "approval_risk"

    def evaluate(self, context: RuleContext) -> list[FindingCandidate]:
        configuration = context.configuration_for(self.code)
        approval_threshold = Decimal(str(configuration.get("approval_threshold", context.settings.noams_approval_threshold)))
        critical_multiplier = Decimal(str(configuration.get("critical_multiplier", 2)))
        findings: list[FindingCandidate] = []
        for transaction in context.transactions:
            status = normalize_key(transaction.approval_status).replace(" ", "_")
            if status not in PENDING | REJECTED:
                continue
            if status in PENDING:
                severity = (
                    "high"
                    if transaction.total_amount >= approval_threshold
                    else "medium"
                )
            else:
                severity = (
                    "critical"
                    if transaction.total_amount >= approval_threshold * critical_multiplier
                    else "high"
                )
            findings.append(
                FindingCandidate(
                    transaction_id=transaction.id,
                    title=self.name,
                    description=(
                        f"The purchase has the approval status '{transaction.approval_status}'. "
                        "The exposed amount does not represent a confirmed loss."
                    ),
                    category=self.category,
                    severity=severity,
                    detected_value=transaction.total_amount,
                    estimated_impact=transaction.total_amount,
                    confidence_score=Decimal("1.0"),
                    evidence={"approval_status": status},
                )
            )
        return findings
