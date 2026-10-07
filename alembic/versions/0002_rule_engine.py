"""Add normalized transactions and deterministic findings."""
from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("analysis_runs")}

    additions = {
        "run_uuid": sa.Column("run_uuid", sa.String(36), nullable=True),
        "source_type": sa.Column("source_type", sa.String(10), nullable=True),
        "findings_count": sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
        "error_message": sa.Column("error_message", sa.Text(), nullable=True),
        "started_at": sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        "completed_at": sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        "updated_at": sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("analysis_runs", column)

    runs = sa.table(
        "analysis_runs",
        sa.column("id", sa.Integer),
        sa.column("run_uuid", sa.String),
        sa.column("source_type", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("started_at", sa.DateTime),
        sa.column("completed_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    now = datetime.now(timezone.utc)
    for row in bind.execute(sa.select(runs.c.id, runs.c.created_at)):
        timestamp = row.created_at or now
        bind.execute(
            runs.update().where(runs.c.id == row.id).values(
                run_uuid=str(uuid4()),
                source_type="csv",
                started_at=timestamp,
                completed_at=timestamp,
                updated_at=timestamp,
            )
        )
    existing_indexes = {item["name"] for item in sa.inspect(bind).get_indexes("analysis_runs")}
    if "ux_analysis_runs_run_uuid" not in existing_indexes:
        op.create_index("ux_analysis_runs_run_uuid", "analysis_runs", ["run_uuid"], unique=True)

    inspector = sa.inspect(bind)
    if "transactions" not in inspector.get_table_names():
        op.create_table(
            "transactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("analysis_run_id", sa.Integer(), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("transaction_id", sa.String(100), nullable=False),
            sa.Column("transaction_date", sa.Date(), nullable=False),
            sa.Column("supplier_name", sa.String(255), nullable=False),
            sa.Column("department", sa.String(150), nullable=False),
            sa.Column("category", sa.String(150), nullable=False),
            sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
            sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
            sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
            sa.Column("approval_status", sa.String(50), nullable=False),
            sa.Column("purchase_order", sa.String(100), nullable=True),
            sa.Column("budget_amount", sa.Numeric(18, 2), nullable=True),
            sa.Column("currency", sa.String(3), nullable=False, server_default="PEN"),
            sa.Column("source_row_number", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        for name, columns in (
            ("ix_transactions_analysis_run_id", ["analysis_run_id"]),
            ("ix_transactions_supplier_name", ["supplier_name"]),
            ("ix_transactions_transaction_date", ["transaction_date"]),
            ("ix_transactions_purchase_order", ["purchase_order"]),
            ("ix_transactions_total_amount", ["total_amount"]),
            ("ix_transactions_run_source_row", ["analysis_run_id", "source_row_number"]),
        ):
            op.create_index(name, "transactions", columns)

    if "findings" not in inspector.get_table_names():
        op.create_table(
            "findings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("finding_uuid", sa.String(36), nullable=False, unique=True),
            sa.Column("analysis_run_id", sa.Integer(), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True),
            sa.Column("rule_code", sa.String(80), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("detected_value", sa.Numeric(18, 2), nullable=True),
            sa.Column("expected_value", sa.Numeric(18, 2), nullable=True),
            sa.Column("deviation_percentage", sa.Numeric(12, 2), nullable=True),
            sa.Column("estimated_impact", sa.Numeric(18, 2), nullable=True),
            sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
            sa.Column("evidence_json", sa.JSON(), nullable=True),
            sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        for name, column in (
            ("ix_findings_analysis_run_id", "analysis_run_id"),
            ("ix_findings_transaction_id", "transaction_id"),
            ("ix_findings_rule_code", "rule_code"),
            ("ix_findings_category", "category"),
            ("ix_findings_severity", "severity"),
            ("ix_findings_status", "status"),
        ):
            op.create_index(name, "findings", [column])

    if "rule_executions" not in inspector.get_table_names():
        op.create_table(
            "rule_executions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("analysis_run_id", sa.Integer(), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("rule_code", sa.String(80), nullable=False),
            sa.Column("rule_name", sa.String(200), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("evaluated_records", sa.Integer(), nullable=False),
            sa.Column("findings_generated", sa.Integer(), nullable=False),
            sa.Column("execution_time_ms", sa.Integer(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_rule_executions_analysis_run_id", "rule_executions", ["analysis_run_id"])
        op.create_index("ix_rule_executions_rule_code", "rule_executions", ["rule_code"])


def downgrade() -> None:
    pass
