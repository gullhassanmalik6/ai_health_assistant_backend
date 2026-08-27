"""Alembic script template."""

from alembic import op
import sqlalchemy as sa


revision: str = ""
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
