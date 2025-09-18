"""init

Revision ID: 6c3ef795ff2d
Revises:
Create Date: 2025-09-16 16:06:48.414031
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision: str = '6c3ef795ff2d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === roles ===
    op.create_table(
        'roles',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('nombre', sa.String(50), nullable=False, unique=True),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # === proveedores ===
    op.create_table(
        'proveedores',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('nit', sa.String(64), nullable=False, unique=True),
        sa.Column('razon_social', sa.String(255), nullable=False),
        sa.Column('area', sa.String(100)),
        sa.Column('contacto_email', sa.String(255)),
        sa.Column('telefono', sa.String(50)),
        sa.Column('direccion', sa.String(255)),
        sa.Column('creado_en', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # === clientes ===
    op.create_table(
        'clientes',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('nit', sa.String(64), nullable=False, unique=True),
        sa.Column('razon_social', sa.String(255), nullable=False),
        sa.Column('contacto_email', sa.String(255)),
        sa.Column('telefono', sa.String(50)),
        sa.Column('direccion', sa.String(255)),
        sa.Column('creado_en', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # === responsables ===
    op.create_table(
        'responsables',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('usuario', sa.String(100), nullable=False, unique=True),
        sa.Column('nombre', sa.String(150)),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('area', sa.String(100)),
        sa.Column('telefono', sa.String(50)),
        sa.Column('activo', sa.Boolean(), server_default=sa.text('1')),
        sa.Column('last_login', sa.TIMESTAMP(), nullable=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),  # <-- añadida aquí
        sa.Column('role_id', sa.BigInteger(), sa.ForeignKey('roles.id')),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # === responsable_proveedor ===
    op.create_table(
        'responsable_proveedor',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('responsable_id', sa.BigInteger(), sa.ForeignKey('responsables.id'), nullable=False),
        sa.Column('proveedor_id', sa.BigInteger(), sa.ForeignKey('proveedores.id'), nullable=False),
        sa.Column('activo', sa.Boolean(), server_default=sa.text('1')),
        sa.UniqueConstraint('responsable_id', 'proveedor_id', name='uix_resp_prov'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # === facturas ===
    op.create_table(
        'facturas',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('numero_factura', sa.String(50), nullable=False),
        sa.Column('fecha_emision', sa.Date(), nullable=False),
        sa.Column('cliente_id', sa.BigInteger(), sa.ForeignKey('clientes.id')),
        sa.Column('proveedor_id', sa.BigInteger(), sa.ForeignKey('proveedores.id')),
        sa.Column('subtotal', sa.Numeric(15, 2)),
        sa.Column('iva', sa.Numeric(15, 2)),
        sa.Column('total', sa.Numeric(15, 2)),
        sa.Column('moneda', sa.String(10)),
        sa.Column('estado', sa.Enum('pendiente','en_revision','aprobada','rechazada','aprobada_auto',
                                    name='estado_factura'), server_default='pendiente'),
        sa.Column('fecha_vencimiento', sa.Date()),
        sa.Column('observaciones', sa.Text()),
        sa.Column('cufe', sa.String(100), nullable=False, unique=True),
        sa.Column('total_a_pagar', sa.Numeric(15, 2)),
        sa.Column('responsable_id', sa.BigInteger(), sa.ForeignKey('responsables.id')),
        sa.Column('aprobada_automaticamente', sa.Boolean(), server_default=sa.text('0')),
        sa.Column('creado_por', sa.String(100)),
        sa.Column('creado_en', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('actualizado_en', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('numero_factura', 'proveedor_id', name='uix_num_prov'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # === audit_log ===
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('entidad', sa.String(64), nullable=False),
        sa.Column('entidad_id', sa.BigInteger(), nullable=False),
        sa.Column('accion', sa.String(50), nullable=False),
        sa.Column('usuario', sa.String(100), nullable=False),
        sa.Column('detalle', sa.JSON()),
        sa.Column('creado_en', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('facturas')
    op.drop_table('responsable_proveedor')
    op.drop_table('responsables')
    op.drop_table('clientes')
    op.drop_table('proveedores')
    op.drop_table('roles')
