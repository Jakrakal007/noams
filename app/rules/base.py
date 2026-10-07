from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, ClassVar


@dataclass(slots=True)
class FindingCandidate:
    title: str
    description: str
    category: str
    severity: str
    transaction_id: int | None = None
    detected_value: Decimal | None = None
    expected_value: Decimal | None = None
    deviation_percentage: Decimal | None = None
    estimated_impact: Decimal | None = None
    confidence_score: Decimal | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


class BusinessRule(ABC):
    code: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    category: ClassVar[str]
    version: ClassVar[str] = "1.0"

    @abstractmethod
    def evaluate(self, context: "RuleContext") -> list[FindingCandidate]:
        raise NotImplementedError


from app.rules.context import RuleContext  # noqa: E402
