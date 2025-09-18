"""add unique constraint to responsable_nit

Revision ID: 9d3b96e23dbe
Revises: b62d2c9b5441
Create Date: 2025-09-18 10:45:10.927615

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9d3b96e23dbe'
down_revision = 'b62d2c9b5441'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_unique_constraint('uq_responsable_nit', 'responsable_nit', ['responsable_id', 'nit'])

def downgrade() -> None:
    op.drop_constraint('uq_responsable_nit', 'responsable_nit', type_='unique')
