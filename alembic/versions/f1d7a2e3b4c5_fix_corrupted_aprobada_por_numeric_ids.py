"""
Fix corrupted aprobada_por field - convert numeric IDs to actual names.

Revision ID: f1d7a2e3b4c5
Revises: a40e54d122a3
Create Date: 2025-10-22 21:30:00.000000

This migration fixes workflows where aprobada_por was stored as a numeric ID
instead of the user's actual name (e.g., '5' instead of 'Alex').

The issue occurred due to a bug in earlier versions where responsable IDs
were being saved directly instead of the responsable's nombre field.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'f1d7a2e3b4c5'
down_revision = 'a40e54d122a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Find workflows where aprobada_por is a pure number and convert to actual name.
    """
    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        # Find all workflows where aprobada_por looks like a numeric ID
        query = text("""
            SELECT waf.id, waf.aprobada_por, r.nombre
            FROM workflow_aprobacion_facturas waf
            LEFT JOIN responsables r ON CAST(waf.aprobada_por AS INTEGER) = r.id
            WHERE waf.aprobada_por ~ '^[0-9]+$'
            AND waf.aprobada == true
        """)

        results = session.execute(query).fetchall()

        for row_id, aprobada_por_id, nombre in results:
            if nombre:
                # Update with actual name
                update_query = text("""
                    UPDATE workflow_aprobacion_facturas
                    SET aprobada_por = :nombre
                    WHERE id = :id
                """)
                session.execute(update_query, {"nombre": nombre, "id": row_id})

        session.commit()

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def downgrade() -> None:
    """
    Rollback would require storing the original numeric ID mapping, which is not feasible.
    This migration is one-way due to data loss potential.
    """
    pass
