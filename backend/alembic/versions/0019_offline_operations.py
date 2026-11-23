"""Store acknowledged offline mutations in the same transaction as their changes."""

import sqlalchemy as sa
from alembic import op

from app.config import settings

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "offline_operation",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("operation_id", sa.Uuid(), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.LargeBinary(), nullable=False),
        schema=settings.db_schema,
    )


def downgrade() -> None:
    op.drop_table("offline_operation", schema=settings.db_schema)
