from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import math
from typing import Any

from app.schemas.analysis import RowError

REQUIRED_COLUMNS = (
    "transaction_id",
    "transaction_date",
    "supplier_name",
    "department",
    "category",
    "quantity",
    "unit_price",
    "total_amount",
    "approval_status",
    "purchase_order",
)
OPTIONAL_COLUMNS = ("budget_amount", "currency")

REQUIRED_TEXT_FIELDS = (
    "transaction_id",
    "supplier_name",
    "department",
    "category",
    "approval_status",
)


def validate_columns(columns: list[str]) -> tuple[list[str], list[str]]:
    column_set = set(columns)
    allowed_set = set(REQUIRED_COLUMNS) | set(OPTIONAL_COLUMNS)
    missing = [column for column in REQUIRED_COLUMNS if column not in column_set]
    unexpected = [column for column in columns if column not in allowed_set]
    return missing, unexpected


def validate_row(row: dict[str, Any], row_number: int) -> list[RowError]:
    errors: list[RowError] = []

    for field in REQUIRED_TEXT_FIELDS:
        if _is_empty(row.get(field)):
            errors.append(RowError(row=row_number, column=field, message="Value is required"))

    if not _is_valid_date(row.get("transaction_date")):
        errors.append(RowError(row=row_number, column="transaction_date", message="Invalid date"))

    quantity = _as_decimal(row.get("quantity"))
    if quantity is None or quantity <= 0:
        errors.append(
            RowError(row=row_number, column="quantity", message="Must be greater than zero")
        )

    for field in ("unit_price", "total_amount"):
        amount = _as_decimal(row.get(field))
        if amount is None:
            errors.append(RowError(row=row_number, column=field, message="Invalid amount"))
        elif amount < 0:
            errors.append(RowError(row=row_number, column=field, message="Amount cannot be negative"))

    if not _is_empty(row.get("budget_amount")):
        budget = _as_decimal(row.get("budget_amount"))
        if budget is None or budget < 0:
            errors.append(
                RowError(row=row_number, column="budget_amount", message="Invalid budget amount")
            )

    return errors


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _is_valid_date(value: Any) -> bool:
    if isinstance(value, (date, datetime)):
        return True
    if not isinstance(value, str) or not value.strip():
        return False

    candidate = value.strip()
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        return True
    except ValueError:
        pass

    for date_format in ("%d/%m/%Y", "%m/%d/%Y"):
        try:
            datetime.strptime(candidate, date_format)
            return True
        except ValueError:
            continue
    return False


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool) or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        result = Decimal(str(value).strip())
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None
