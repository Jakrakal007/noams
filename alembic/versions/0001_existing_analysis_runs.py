"""Baseline compatible with the Sprint 1 schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "analysis_runs" not in inspector.get_table_names():
        op.create_table(
            "analysis_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processing_time_ms", sa.Integer(), nullable=False),
            sa.Column("total_records", sa.Integer(), nullable=False),
            sa.Column("valid_records", sa.Integer(), nullable=False),
            sa.Column("invalid_records", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
        )


def downgrade() -> None:
    pass
