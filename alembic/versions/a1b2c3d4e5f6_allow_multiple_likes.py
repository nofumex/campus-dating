"""allow multiple likes between same users

Revision ID: a1b2c3d4e5f6
Revises: 637213a8ed2c
Create Date: 2025-12-01
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "637213a8ed2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop unique constraint on likes (from_user_id, to_user_id)."""
    with op.batch_alter_table("likes") as batch_op:
        try:
            batch_op.drop_constraint("unique_like", type_="unique")
        except Exception:
            # Констрейнт может уже не существовать; в этом случае тихо продолжаем.
            pass


def downgrade() -> None:
    """Re-create unique constraint on likes (from_user_id, to_user_id)."""
    with op.batch_alter_table("likes") as batch_op:
        batch_op.create_unique_constraint(
            "unique_like",
            ["from_user_id", "to_user_id"],
        )


