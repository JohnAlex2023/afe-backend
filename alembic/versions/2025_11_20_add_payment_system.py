"""Add payment system with pagos_facturas table

Revision ID: 2025_11_20_add_payment_system
Revises: 2025_11_11_cleanup_accion_por
Create Date: 2025-11-20 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2025_11_20_add_payment_system'
down_revision = '2025_11_11_cleanup_accion_por'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pagos_facturas table
    op.create_table(
        'pagos_facturas',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('factura_id', sa.BigInteger(), nullable=False),
        sa.Column('monto_pagado', sa.Numeric(precision=15, scale=2, asdecimal=True), nullable=False),
        sa.Column('referencia_pago', sa.String(length=100), nullable=False),
        sa.Column('metodo_pago', sa.String(length=50), nullable=True),
        sa.Column('estado_pago', sa.Enum('completado', 'fallido', 'cancelado', name='estadopago'), nullable=False, server_default='completado'),
        sa.Column('procesado_por', sa.String(length=255), nullable=False),
        sa.Column('fecha_pago', sa.DateTime(timezone=True), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['factura_id'], ['facturas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('referencia_pago', name='referencia_pago'),
    )

    # Create indexes
    op.create_index('ix_pagos_facturas_factura_id_estado', 'pagos_facturas', ['factura_id', 'estado_pago'])
    op.create_index('ix_pagos_facturas_fecha_pago', 'pagos_facturas', ['fecha_pago'])
    op.create_index('ix_pagos_facturas_factura_id', 'pagos_facturas', ['factura_id'])
    op.create_index('ix_pagos_facturas_estado_pago', 'pagos_facturas', ['estado_pago'])
    op.create_index('ix_pagos_facturas_procesado_por', 'pagos_facturas', ['procesado_por'])
    op.create_index('ix_pagos_facturas_referencia_pago', 'pagos_facturas', ['referencia_pago'])
    op.create_index('ix_pagos_facturas_creado_en', 'pagos_facturas', ['creado_en'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_pagos_facturas_creado_en', table_name='pagos_facturas')
    op.drop_index('ix_pagos_facturas_referencia_pago', table_name='pagos_facturas')
    op.drop_index('ix_pagos_facturas_procesado_por', table_name='pagos_facturas')
    op.drop_index('ix_pagos_facturas_estado_pago', table_name='pagos_facturas')
    op.drop_index('ix_pagos_facturas_fecha_pago', table_name='pagos_facturas')
    op.drop_index('ix_pagos_facturas_factura_id_estado', table_name='pagos_facturas')
    op.drop_index('ix_pagos_facturas_factura_id', table_name='pagos_facturas')

    # Drop table
    op.drop_table('pagos_facturas')
