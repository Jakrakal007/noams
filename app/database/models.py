from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    stored_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str] = mapped_column(String(10), default="csv")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    valid_records: Mapped[int] = mapped_column(Integer, default=0)
    invalid_records: Mapped[int] = mapped_column(Integer, default=0)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    rule_executions: Mapped[list["RuleExecution"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )
    validation_errors: Mapped[list["AnalysisValidationError"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )

    @property
    def rejected_records(self) -> int:
        return self.invalid_records


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[str] = mapped_column(String(100))
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    supplier_name: Mapped[str] = mapped_column(String(255), index=True)
    department: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), index=True)
    approval_status: Mapped[str] = mapped_column(String(50))
    purchase_order: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="PEN")
    source_row_number: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="transactions")
    findings: Mapped[list["Finding"]] = relationship(back_populates="transaction")

    __table_args__ = (Index("ix_transactions_run_source_row", "analysis_run_id", "source_row_number"),)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    rule_code: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    detected_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    expected_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    deviation_percentage: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_impact: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    evidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="findings")
    transaction: Mapped[Transaction | None] = relationship(back_populates="findings")


class RuleExecution(Base):
    __tablename__ = "rule_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    rule_code: Mapped[str] = mapped_column(String(80), index=True)
    rule_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    evaluated_records: Mapped[int] = mapped_column(Integer, default=0)
    findings_generated: Mapped[int] = mapped_column(Integer, default=0)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    configuration_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="rule_executions")


class RuleConfiguration(Base):
    __tablename__ = "rule_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(30), default="1.0")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    detection_type: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    severity_strategy: Mapped[str] = mapped_column(String(200))
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AnalysisValidationError(Base):
    __tablename__ = "analysis_validation_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    row: Mapped[int] = mapped_column(Integer)
    column: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="validation_errors")
