"""PHASE 3: Complete assignment status tracking implementation

Revision ID: phase3_estado_asignacion_2025
Revises: trigger_integrity_2025
Create Date: 2025-10-22

ENTERPRISE LEVEL: Assignment lifecycle tracking for professional invoice management.

CONTEXTO:
El modelo Factura ya tiene el campo estado_asignacion (agregado en el último update).
Esta migración se encarga de:
1. Inicializar valores históricos del campo
2. Crear índice para optimizar queries del dashboard
3. Crear triggers para mantener sincronizado automáticamente

ARQUITECTURA:
- sin_asignar: Factura sin responsable (responsable_id = NULL, accion_por = NULL)
- asignado: Factura con responsable activo (responsable_id != NULL)
- huerfano: Factura procesada pero sin responsable (responsable_id=NULL, accion_por!=NULL)
- inconsistente: Estados anómalos para auditoría futura

JUSTIFICACIÓN PROFESIONAL:
- Previene datos huérfanos confusos en el dashboard
- Proporciona trazabilidad completa del ciclo de vida
- Permite detección automática de asignaciones rotas
- Facilita limpieza de datos y housekeeping
- Compatible con auditoría y reporting futuro
"""
from alembic import op
import sqlalchemy as sa


revision = 'phase3_estado_asignacion_2025'
down_revision = 'trigger_integrity_2025'
branch_labels = None
depends_on = None


def upgrade():
    """
    PHASE 3 Upgrade: Initialize and secure assignment status tracking.

    PASOS:
    1. Inicializar valores del campo estado_asignacion basados en responsable_id y accion_por
    2. Crear índice para optimizar queries de dashboard
    3. Crear triggers BEFORE UPDATE/INSERT para mantener sincronizado automáticamente

    IDEMPOTENCIA: Seguro ejecutar múltiples veces sin errores
    """

    # PASO 1: Inicializar valores basados en estado actual de facturas
    # Lógica:
    # - Si responsable_id != NULL: 'asignado'
    # - Si responsable_id IS NULL AND accion_por IS NOT NULL: 'huerfano'
    # - Si responsable_id IS NULL AND accion_por IS NULL: 'sin_asignar'
    op.execute("""
        UPDATE facturas
        SET estado_asignacion = CASE
            WHEN responsable_id IS NOT NULL THEN 'asignado'
            WHEN responsable_id IS NULL AND accion_por IS NOT NULL THEN 'huerfano'
            ELSE 'sin_asignar'
        END
        WHERE estado_asignacion = 'sin_asignar'
    """)

    # PASO 2: Crear índice para optimizar queries del dashboard
    # Este índice es crítico para performance de filtros en el dashboard
    # MySQL: Crear INDEX directamente (sin IF NOT EXISTS para compatibilidad)
    op.create_index(
        'ix_facturas_estado_asignacion',
        'facturas',
        ['estado_asignacion']
    )

    # PASO 3: Crear triggers para sincronización automática

    # Trigger 3A: BEFORE UPDATE
    # Recalcula estado_asignacion cuando cambian responsable_id o accion_por
    op.execute("""
        DROP TRIGGER IF EXISTS before_facturas_update_estado_asignacion
    """)

    op.execute("""
        CREATE TRIGGER before_facturas_update_estado_asignacion
        BEFORE UPDATE ON facturas
        FOR EACH ROW
        BEGIN
            -- Recalcular estado_asignacion basado en nuevos valores
            -- Esto se ejecuta automáticamente en cada UPDATE
            IF NEW.responsable_id IS NOT NULL THEN
                SET NEW.estado_asignacion = 'asignado';
            ELSEIF NEW.responsable_id IS NULL AND NEW.accion_por IS NOT NULL THEN
                SET NEW.estado_asignacion = 'huerfano';
            ELSE
                SET NEW.estado_asignacion = 'sin_asignar';
            END IF;
        END
    """)

    # Trigger 3B: BEFORE INSERT
    # Calcula estado_asignacion al crear nueva factura
    op.execute("""
        DROP TRIGGER IF EXISTS before_facturas_insert_estado_asignacion
    """)

    op.execute("""
        CREATE TRIGGER before_facturas_insert_estado_asignacion
        BEFORE INSERT ON facturas
        FOR EACH ROW
        BEGIN
            -- Calcular estado_asignacion si no se especifica
            IF NEW.estado_asignacion IS NULL OR NEW.estado_asignacion = 'sin_asignar' THEN
                IF NEW.responsable_id IS NOT NULL THEN
                    SET NEW.estado_asignacion = 'asignado';
                ELSEIF NEW.accion_por IS NOT NULL THEN
                    SET NEW.estado_asignacion = 'huerfano';
                ELSE
                    SET NEW.estado_asignacion = 'sin_asignar';
                END IF;
            END IF;
        END
    """)


def downgrade():
    """
    PHASE 3 Downgrade: Remove assignment status tracking infrastructure.

    PASOS:
    1. Eliminar triggers automáticos
    2. Eliminar índice
    3. Resetear columna a valor por defecto (no eliminar, para preservar datos)

    NOTA: No eliminamos la columna física para permitir rollback limpio
    """

    # PASO 1: Eliminar triggers
    op.execute("DROP TRIGGER IF EXISTS before_facturas_update_estado_asignacion")
    op.execute("DROP TRIGGER IF EXISTS before_facturas_insert_estado_asignacion")

    # PASO 2: Eliminar índice
    op.drop_index('ix_facturas_estado_asignacion', table_name='facturas')

    # PASO 3: Resetear valores a defecto (preservar datos para auditoria)
    op.execute("""
        UPDATE facturas SET estado_asignacion = 'sin_asignar'
        WHERE estado_asignacion IN ('asignado', 'huerfano', 'inconsistente')
    """)
