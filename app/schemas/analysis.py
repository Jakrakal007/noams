from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class DecimalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimals(self, value: Any) -> Any:
        return format(value, ".2f") if isinstance(value, Decimal) else value


class RowError(BaseModel):
    row: int
    column: str
    message: str


class FindingSummary(DecimalSchema):
    total: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0
    estimated_impact: Decimal = Decimal("0.00")


class FindingResponse(DecimalSchema):
    id: int
    finding_uuid: str
    rule_code: str
    title: str
    description: str
    category: str
    severity: str
    status: str
    detected_value: Decimal | None
    expected_value: Decimal | None
    deviation_percentage: Decimal | None
    estimated_impact: Decimal | None
    confidence_score: Decimal | None
    transaction_id: int | None
    detected_at: datetime
    evidence_json: dict[str, Any] | None = None
    supplier_name: str | None = None
    transaction_date: date | None = None
    purchase_order: str | None = None


class RuleExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rule_code: str
    rule_name: str
    status: str
    evaluated_records: int
    findings_generated: int
    execution_time_ms: int
    error_message: str | None = None
    rule_version: str | None = None
    configuration_snapshot_json: dict[str, Any] | None = None
    skip_reason: str | None = None


class TransactionResponse(DecimalSchema):
    id: int
    transaction_id: str
    transaction_date: date
    supplier_name: str
    department: str
    category: str
    quantity: Decimal
    unit_price: Decimal
    total_amount: Decimal
    approval_status: str
    purchase_order: str | None
    budget_amount: Decimal | None
    currency: str
    source_row_number: int


class AnalysisResponse(BaseModel):
    analysis_id: int
    filename: str
    status: str
    total_records: int
    valid_records: int
    invalid_records: int
    processing_time_ms: int
    errors: list[RowError]
    findings_summary: FindingSummary = Field(default_factory=FindingSummary)
    findings: list[FindingResponse] = Field(default_factory=list)
    rule_executions: list[RuleExecutionResponse] = Field(default_factory=list)


class AnalysisDetail(AnalysisResponse):
    run_uuid: str
    source_type: str
    started_at: datetime
    completed_at: datetime | None
    transactions: list[TransactionResponse]


class AnalysisHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    created_at: datetime
    status: str
    total_records: int
    valid_records: int
    invalid_records: int
    findings_count: int
    processing_time_ms: int
    source_type: str
    versions_count: int = 1
    is_updated: bool = False


class FindingsPage(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[FindingResponse]


class DashboardSummary(DecimalSchema):
    analyses_count: int
    records_processed: int
    findings_count: int
    critical_risks: int
    estimated_impact: Decimal
    last_run_at: datetime | None
    last_run_status: str | None
