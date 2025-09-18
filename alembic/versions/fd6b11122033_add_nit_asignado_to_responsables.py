"""add nit_asignado to responsables

Revision ID: fd6b11122033
Revises: 
Create Date: 2025-09-18 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fd6b11122033'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('responsables', sa.Column('nit_asignado', sa.String(length=30), nullable=True))

def downgrade():
    op.drop_column('responsables', 'nit_asignado')
