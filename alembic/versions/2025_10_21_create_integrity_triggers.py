"""Create database triggers for assignment-invoice integrity

Revision ID: trigger_integrity_2025
Revises:
Create Date: 2025-10-21

ENTERPRISE LEVEL: Database-level guarantees for data consistency
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'trigger_integrity_2025'
down_revision = '8cac6c86089d'  # Performance index for activo in asignacion
branch_labels = None
depends_on = None


def upgrade():
    """
    Create triggers to guarantee invoice-assignment synchronization at database level.

    Benefits:
    - Works even if Python code has bugs
    - Works with manual SQL operations
    - Works with any future framework/language
    - Cannot be bypassed or forgotten
    - Atomic with the transaction
    """

    # Read SQL file
    import os
    sql_file = os.path.join(
        os.path.dirname(__file__),
        '2025_10_21_triggers_integridad_asignaciones.sql'
    )

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Execute triggers
    op.execute(sql_content)

    print("✅ Triggers de integridad creados exitosamente")
    print("   - after_asignacion_soft_delete: Desasigna facturas al eliminar")
    print("   - after_asignacion_activate: Asigna facturas al crear")
    print("   - after_asignacion_restore: Reasigna facturas al restaurar")


def downgrade():
    """Remove triggers."""

    op.execute("DROP TRIGGER IF EXISTS after_asignacion_soft_delete")
    op.execute("DROP TRIGGER IF EXISTS after_asignacion_activate")
    op.execute("DROP TRIGGER IF EXISTS after_asignacion_restore")

    print("🔄 Triggers de integridad eliminados")
