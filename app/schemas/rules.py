from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RuleStatistics(BaseModel):
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    skipped_executions: int = 0
    total_findings: int = 0
    last_executed_at: datetime | None = None
    last_status: str | None = None
    average_execution_time_ms: float | None = None


class RuleConfigurationResponse(BaseModel):
    id: int
    rule_code: str
    display_name: str
    description: str
    version: str
    enabled: bool
    detection_type: str
    category: str
    severity_strategy: str
    configuration: dict[str, Any]
    default_configuration: dict[str, Any]
    updated_at: datetime
    statistics: RuleStatistics


class RuleListResponse(BaseModel):
    items: list[RuleConfigurationResponse]


class RuleDetailResponse(RuleConfigurationResponse):
    pass


class RuleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    configuration: dict[str, Any] | None = None
