"""remove_cliente_id_from_facturas

Revision ID: 4cf72d1df18f
Revises: 4ca79fbcd3d4
Create Date: 2025-10-10 09:29:26.067233

Elimina cliente_id de facturas (no se usa en automatización de facturas de proveedores).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cf72d1df18f'
down_revision: Union[str, Sequence[str], None] = '4ca79fbcd3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina cliente_id (FK ya fue eliminada anteriormente)."""
    # Eliminar columna directamente (FK ya no existe)
    op.drop_column('facturas', 'cliente_id')


def downgrade() -> None:
    """Restaura cliente_id."""
    op.add_column('facturas', sa.Column('cliente_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('facturas_ibfk_1', 'facturas', 'clientes', ['cliente_id'], ['id'])
