"""merge heads

Revision ID: b62d2c9b5441
Revises: c44e9c188db7, fd6b11122033
Create Date: 2025-09-18 09:59:15.182055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b62d2c9b5441'
down_revision: Union[str, Sequence[str], None] = ('c44e9c188db7', 'fd6b11122033')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
