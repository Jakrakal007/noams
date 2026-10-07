"""Persist uploaded files and row validation errors."""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("analysis_runs")}

    if "stored_file_path" not in columns:
        op.add_column(
            "analysis_runs", sa.Column("stored_file_path", sa.String(500), nullable=True)
        )
    if "file_size_bytes" not in columns:
        op.add_column(
            "analysis_runs", sa.Column("file_size_bytes", sa.Integer(), nullable=True)
        )

    inspector = sa.inspect(bind)
    if "analysis_validation_errors" not in inspector.get_table_names():
        op.create_table(
            "analysis_validation_errors",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "analysis_run_id",
                sa.Integer(),
                sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("row", sa.Integer(), nullable=False),
            sa.Column("column", sa.String(150), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_analysis_validation_errors_analysis_run_id",
            "analysis_validation_errors",
            ["analysis_run_id"],
        )


def downgrade() -> None:
    pass
