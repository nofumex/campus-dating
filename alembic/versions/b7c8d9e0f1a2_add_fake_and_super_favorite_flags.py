"""add fake and super favorite flags to users

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2025-12-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_fake and is_super_favorite columns to users table."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("is_fake", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("is_super_favorite", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    """Drop is_fake and is_super_favorite columns from users table."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_super_favorite")
        batch_op.drop_column("is_fake")


