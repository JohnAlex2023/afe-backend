"""Asignar roles a usuarios admin y responsable

Revision ID: c44e9c188db7
Revises: 6c3ef795ff2d
Create Date: 2025-09-17 23:18:30.894107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c44e9c188db7'
down_revision: Union[str, Sequence[str], None] = '6c3ef795ff2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Asigna roles a los usuarios admin y responsable si existen."""
    op.execute("UPDATE responsables SET role_id = 1 WHERE usuario = 'admin';")
    op.execute("UPDATE responsables SET role_id = 2 WHERE usuario = 'responsable';")


def downgrade() -> None:
    """Revierte los roles de admin y responsable a NULL."""
    op.execute("UPDATE responsables SET role_id = NULL WHERE usuario IN ('admin', 'responsable');")
