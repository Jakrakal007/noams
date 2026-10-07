from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.models import AnalysisRun, Transaction


@dataclass(slots=True)
class RuleContext:
    analysis_run: AnalysisRun
    transactions: list[Transaction]
    historical_amounts: dict[str, list[Decimal]]
    settings: Settings
    session: Session
    rule_configurations: dict[str, dict[str, Any]] | None = None

    def configuration_for(self, rule_code: str) -> dict[str, Any]:
        if not self.rule_configurations:
            return {}
        return dict(self.rule_configurations.get(rule_code, {}).get("configuration", {}))


def normalize_key(value: str) -> str:
    return " ".join(value.casefold().split())
