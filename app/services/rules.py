from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ResourceNotFoundError, RuleConfigurationError
from app.database.models import Finding, RuleConfiguration, RuleExecution
from app.schemas.rules import RuleConfigurationResponse, RuleStatistics


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    display_name: str
    description: str
    version: str
    detection_type: str
    category: str
    severity_strategy: str
    defaults: dict[str, int | float]


def _number(value: Decimal | int | float) -> int | float:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral() else float(value)
    return value


RULE_DEFINITIONS: dict[str, RuleDefinition] = {
    "DUPLICATE_PURCHASE": RuleDefinition(
        "Duplicate Purchase",
        "Detects transactions with matching supplier, purchase order, and total amount within the same analysis run.",
        "1.0", "Deterministic", "Transaction Integrity", "Impact-based severity", {},
    ),
    "UNUSUAL_SUPPLIER_AMOUNT": RuleDefinition(
        "Unusual Supplier Amount",
        "Detects supplier transactions that significantly exceed the supplier's historical purchasing pattern.",
        "1.0", "Historical / Deterministic", "Behavioral Anomaly", "Deviation-based severity",
        {"minimum_history": settings.noams_unusual_min_history, "multiplier": _number(settings.noams_unusual_multiplier), "minimum_difference": _number(settings.noams_unusual_min_difference)},
    ),
    "BUDGET_DEVIATION": RuleDefinition(
        "Budget Deviation", "Detects transactions whose total amount exceeds the approved budget.",
        "1.0", "Deterministic", "Budget Compliance", "Percentage thresholds",
        {"medium_threshold_percentage": 10, "high_threshold_percentage": 25, "critical_threshold_percentage": 50},
    ),
    "UNAPPROVED_PURCHASE": RuleDefinition(
        "Purchase Without Valid Approval",
        "Detects purchases with pending, rejected, unapproved, or otherwise invalid approval status.",
        "1.0", "Deterministic", "Approval Compliance", "Status and amount thresholds",
        {"approval_threshold": _number(settings.noams_approval_threshold), "critical_multiplier": 2},
    ),
    "SPLIT_PURCHASE": RuleDefinition(
        "Potential Split Purchase",
        "Detects multiple purchases that may have been divided to avoid an approval threshold.",
        "1.0", "Deterministic / Grouped", "Approval Circumvention", "Grouped amount thresholds",
        {"approval_threshold": _number(settings.noams_approval_threshold), "window_days": settings.noams_split_window_days, "minimum_operations": settings.noams_split_min_operations},
    ),
}

LIMITS = {
    "minimum_history": (1, 10000, int), "multiplier": (1, 1000, float),
    "minimum_difference": (0, 1_000_000_000, float),
    "medium_threshold_percentage": (0, 100000, float),
    "high_threshold_percentage": (0, 100000, float),
    "critical_threshold_percentage": (0, 100000, float),
    "approval_threshold": (0, 1_000_000_000, float),
    "critical_multiplier": (1, 1000, float), "window_days": (1, 3650, int),
    "minimum_operations": (2, 10000, int),
}


class RuleService:
    def ensure_default_rules(self, db: Session) -> int:
        existing = set(db.scalars(select(RuleConfiguration.rule_code)).all())
        created = 0
        for code, definition in RULE_DEFINITIONS.items():
            if code in existing:
                continue
            db.add(RuleConfiguration(
                rule_code=code, display_name=definition.display_name, description=definition.description,
                version=definition.version, enabled=True, detection_type=definition.detection_type,
                category=definition.category, severity_strategy=definition.severity_strategy,
                configuration_json=deepcopy(definition.defaults),
            ))
            created += 1
        if created:
            db.flush()
        return created

    def list_rules(self, db: Session) -> list[RuleConfigurationResponse]:
        if self.ensure_default_rules(db):
            db.commit()
        records = db.scalars(select(RuleConfiguration).order_by(RuleConfiguration.id)).all()
        return [self._response(db, record) for record in records]

    def get_rule(self, db: Session, rule_code: str) -> RuleConfigurationResponse:
        if self.ensure_default_rules(db):
            db.commit()
        record = self._record(db, rule_code)
        return self._response(db, record)

    def update_rule(self, db: Session, rule_code: str, *, enabled: bool | None, configuration: dict[str, Any] | None) -> RuleConfigurationResponse:
        self.ensure_default_rules(db)
        record = self._record(db, rule_code)
        if enabled is None and configuration is None:
            raise RuleConfigurationError("empty_update", "Provide enabled or configuration values.")
        if enabled is not None:
            record.enabled = enabled
        if configuration is not None:
            validated = self._validate(rule_code, configuration)
            current = dict(record.configuration_json or {})
            current.update(validated)
            record.configuration_json = current
        db.commit()
        db.refresh(record)
        return self._response(db, record)

    def reset_rule(self, db: Session, rule_code: str) -> RuleConfigurationResponse:
        self.ensure_default_rules(db)
        record = self._record(db, rule_code)
        record.enabled = True
        record.configuration_json = deepcopy(RULE_DEFINITIONS[rule_code].defaults)
        db.commit()
        db.refresh(record)
        return self._response(db, record)

    def execution_configurations(self, db: Session) -> dict[str, dict[str, Any]]:
        self.ensure_default_rules(db)
        records = db.scalars(select(RuleConfiguration)).all()
        return {record.rule_code: {"enabled": record.enabled, "version": record.version, "configuration": deepcopy(record.configuration_json or {})} for record in records}

    def get_rule_statistics(self, db: Session, rule_code: str) -> RuleStatistics:
        values = db.execute(select(
            func.count(RuleExecution.id),
            func.coalesce(func.sum(case((RuleExecution.status == "completed", 1), else_=0)), 0),
            func.coalesce(func.sum(case((RuleExecution.status == "failed", 1), else_=0)), 0),
            func.coalesce(func.sum(case((RuleExecution.status == "skipped", 1), else_=0)), 0),
            func.avg(RuleExecution.execution_time_ms),
        ).where(RuleExecution.rule_code == rule_code)).one()
        last = db.scalar(select(RuleExecution).where(RuleExecution.rule_code == rule_code).order_by(desc(RuleExecution.started_at), desc(RuleExecution.id)).limit(1))
        finding_count = db.scalar(select(func.count(Finding.id)).where(Finding.rule_code == rule_code)) or 0
        return RuleStatistics(total_executions=values[0], successful_executions=values[1], failed_executions=values[2], skipped_executions=values[3], total_findings=finding_count, last_executed_at=last.started_at if last else None, last_status=last.status if last else None, average_execution_time_ms=round(float(values[4]), 2) if values[4] is not None else None)

    def _record(self, db: Session, rule_code: str) -> RuleConfiguration:
        record = db.scalar(select(RuleConfiguration).where(RuleConfiguration.rule_code == rule_code))
        if record is None or rule_code not in RULE_DEFINITIONS:
            raise ResourceNotFoundError("rule_not_found", "The requested rule does not exist.")
        return record

    def _response(self, db: Session, record: RuleConfiguration) -> RuleConfigurationResponse:
        return RuleConfigurationResponse(id=record.id, rule_code=record.rule_code, display_name=record.display_name, description=record.description, version=record.version, enabled=record.enabled, detection_type=record.detection_type, category=record.category, severity_strategy=record.severity_strategy, configuration=dict(record.configuration_json or {}), default_configuration=deepcopy(RULE_DEFINITIONS[record.rule_code].defaults), updated_at=record.updated_at, statistics=self.get_rule_statistics(db, record.rule_code))

    def _validate(self, rule_code: str, configuration: dict[str, Any]) -> dict[str, int | float]:
        allowed = RULE_DEFINITIONS[rule_code].defaults
        unknown = sorted(set(configuration) - set(allowed))
        if unknown:
            raise RuleConfigurationError("unsupported_configuration", f"Unsupported configuration field: {unknown[0]}.", {"field": unknown[0]})
        validated: dict[str, int | float] = {}
        for key, value in configuration.items():
            minimum, maximum, expected = LIMITS[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or (expected is int and not isinstance(value, int)):
                raise RuleConfigurationError("invalid_configuration", f"{key} has an invalid type.", {"field": key})
            if key in {"multiplier", "critical_multiplier"} and value <= minimum:
                raise RuleConfigurationError("invalid_configuration", f"{key} must be greater than {minimum}.", {"field": key})
            if key not in {"multiplier", "critical_multiplier"} and value < minimum or value > maximum:
                raise RuleConfigurationError("invalid_configuration", f"{key} must be between {minimum} and {maximum}.", {"field": key})
            if value > maximum:
                raise RuleConfigurationError("invalid_configuration", f"{key} must be between {minimum} and {maximum}.", {"field": key})
            validated[key] = value
        if rule_code == "BUDGET_DEVIATION":
            merged = {**allowed, **validated}
            if not merged["medium_threshold_percentage"] < merged["high_threshold_percentage"] < merged["critical_threshold_percentage"]:
                raise RuleConfigurationError("invalid_threshold_order", "Severity thresholds must be ordered from medium to high to critical.", {"field": "medium_threshold_percentage"})
        return validated


rule_service = RuleService()
