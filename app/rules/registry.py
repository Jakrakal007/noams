from app.rules.base import BusinessRule
from app.rules.implementations import (
    BudgetDeviationRule,
    DuplicatePurchaseRule,
    SplitPurchaseRule,
    UnapprovedPurchaseRule,
    UnusualSupplierAmountRule,
)


def registered_rules() -> list[BusinessRule]:
    return [
        DuplicatePurchaseRule(),
        UnusualSupplierAmountRule(),
        BudgetDeviationRule(),
        UnapprovedPurchaseRule(),
        SplitPurchaseRule(),
    ]
