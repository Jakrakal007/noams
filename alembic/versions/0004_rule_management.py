"""Add persistent rule configuration and execution snapshots."""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    if "rule_configurations" not in tables:
        op.create_table(
            "rule_configurations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("rule_code", sa.String(80), nullable=False),
            sa.Column("display_name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("version", sa.String(30), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("detection_type", sa.String(100), nullable=False),
            sa.Column("category", sa.String(100), nullable=False),
            sa.Column("severity_strategy", sa.String(200), nullable=False),
            sa.Column("configuration_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("rule_code", name="uq_rule_configurations_rule_code"),
        )
        op.create_index("ix_rule_configurations_rule_code", "rule_configurations", ["rule_code"], unique=True)

    execution_columns = {column["name"] for column in inspector.get_columns("rule_executions")}
    if "rule_version" not in execution_columns:
        op.add_column("rule_executions", sa.Column("rule_version", sa.String(30), nullable=True))
    if "configuration_snapshot_json" not in execution_columns:
        op.add_column("rule_executions", sa.Column("configuration_snapshot_json", sa.JSON(), nullable=True))
    if "skip_reason" not in execution_columns:
        op.add_column("rule_executions", sa.Column("skip_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    pass
