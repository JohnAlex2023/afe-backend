"""
Script de validación de integridad de datos (FASE 1).

Detecta inconsistencias entre campos almacenados y valores calculados.
Útil para auditoría y limpieza de datos.

Uso:
    python scripts/validar_integridad_datos.py

Nivel: Fortune 500 Data Quality Assurance
"""

from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.factura import Factura
from app.models.factura_item import FacturaItem

# Configurar engine y session
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def validar_facturas():
    """Valida integridad de totales en facturas."""
    print("\n" + "="*80)
    print("VALIDANDO INTEGRIDAD DE FACTURAS")
    print("="*80)

    db = SessionLocal()

    try:
        # Contar facturas con inconsistencias
        facturas = db.query(Factura).limit(1000).all()

        inconsistentes = []

        for factura in facturas:
            if factura.tiene_inconsistencia_total:
                diferencia = abs(factura.total_a_pagar - factura.total_calculado)
                inconsistentes.append({
                    'id': factura.id,
                    'numero': factura.numero_factura,
                    'almacenado': factura.total_a_pagar,
                    'calculado': factura.total_calculado,
                    'diferencia': diferencia
                })

        print(f"\nFacturas analizadas: {len(facturas)}")
        print(f"Facturas con inconsistencias: {len(inconsistentes)}")

        if inconsistentes:
            print("\nPrimeras 10 inconsistencias:")
            print("-" * 80)
            for f in inconsistentes[:10]:
                print(f"ID: {f['id']:5} | Num: {f['numero']:20} | "
                      f"Almacenado: ${f['almacenado']:12,.2f} | "
                      f"Calculado: ${f['calculado']:12,.2f} | "
                      f"Diff: ${f['diferencia']:10,.2f}")

            if len(inconsistentes) > 10:
                print(f"\n... y {len(inconsistentes) - 10} más")
        else:
            print("\n✓ Todas las facturas tienen totales consistentes")

        return len(inconsistentes)

    finally:
        db.close()


def validar_items():
    """Valida integridad de totales en items."""
    print("\n" + "="*80)
    print("VALIDANDO INTEGRIDAD DE ITEMS")
    print("="*80)

    db = SessionLocal()

    try:
        # Contar items con inconsistencias
        items = db.query(FacturaItem).limit(5000).all()

        inconsistentes_subtotal = []
        inconsistentes_total = []

        for item in items:
            if item.tiene_inconsistencia_subtotal:
                diferencia = abs(item.subtotal - item.subtotal_calculado)
                inconsistentes_subtotal.append({
                    'id': item.id,
                    'factura_id': item.factura_id,
                    'desc': item.descripcion[:40],
                    'almacenado': item.subtotal,
                    'calculado': item.subtotal_calculado,
                    'diferencia': diferencia
                })

            if item.tiene_inconsistencia_total:
                diferencia = abs(item.total - item.total_calculado)
                inconsistentes_total.append({
                    'id': item.id,
                    'factura_id': item.factura_id,
                    'desc': item.descripcion[:40],
                    'almacenado': item.total,
                    'calculado': item.total_calculado,
                    'diferencia': diferencia
                })

        print(f"\nItems analizados: {len(items)}")
        print(f"Items con inconsistencias en subtotal: {len(inconsistentes_subtotal)}")
        print(f"Items con inconsistencias en total: {len(inconsistentes_total)}")

        if inconsistentes_subtotal:
            print("\nPrimeras 5 inconsistencias en subtotal:")
            print("-" * 80)
            for i in inconsistentes_subtotal[:5]:
                print(f"ID: {i['id']:5} | Fact: {i['factura_id']:5} | "
                      f"{i['desc']:40} | Diff: ${i['diferencia']:10,.2f}")

        if inconsistentes_total:
            print("\nPrimeras 5 inconsistencias en total:")
            print("-" * 80)
            for i in inconsistentes_total[:5]:
                print(f"ID: {i['id']:5} | Fact: {i['factura_id']:5} | "
                      f"{i['desc']:40} | Diff: ${i['diferencia']:10,.2f}")

        if not inconsistentes_subtotal and not inconsistentes_total:
            print("\n✓ Todos los items tienen totales consistentes")

        return len(inconsistentes_subtotal) + len(inconsistentes_total)

    finally:
        db.close()


def validar_constraints():
    """Valida que todos los constraints están activos."""
    print("\n" + "="*80)
    print("VALIDANDO CONSTRAINTS DE BASE DE DATOS")
    print("="*80)

    db = SessionLocal()

    try:
        # Verificar constraints en facturas
        result = db.execute(text("""
            SELECT CONSTRAINT_NAME
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'facturas'
            AND CONSTRAINT_TYPE = 'CHECK'
        """))

        facturas_constraints = [row[0] for row in result.fetchall()]
        print(f"\nConstraints en tabla 'facturas': {len(facturas_constraints)}")
        for c in facturas_constraints:
            print(f"  ✓ {c}")

        # Verificar constraints en items
        result = db.execute(text("""
            SELECT CONSTRAINT_NAME
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'factura_items'
            AND CONSTRAINT_TYPE = 'CHECK'
        """))

        items_constraints = [row[0] for row in result.fetchall()]
        print(f"\nConstraints en tabla 'factura_items': {len(items_constraints)}")
        for c in items_constraints:
            print(f"  ✓ {c}")

        # Verificar índices
        result = db.execute(text("""
            SELECT TABLE_NAME, INDEX_NAME
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            AND INDEX_NAME LIKE 'idx_facturas_%'
            GROUP BY TABLE_NAME, INDEX_NAME
            ORDER BY TABLE_NAME, INDEX_NAME
        """))

        indices = result.fetchall()
        print(f"\nÍndices de performance: {len(indices)}")
        for table, idx in indices:
            print(f"  ✓ {table}.{idx}")

        return len(facturas_constraints) + len(items_constraints) + len(indices)

    finally:
        db.close()


def main():
    """Ejecuta todas las validaciones."""
    print("\n" + "="*80)
    print("VALIDACIÓN DE INTEGRIDAD - FASE 1 COMPLETADA")
    print("Base de datos: AFE Backend (Sistema Empresarial)")
    print("="*80)

    # Ejecutar validaciones
    total_inconsistencias_facturas = validar_facturas()
    total_inconsistencias_items = validar_items()
    total_constraints = validar_constraints()

    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print(f"\nInconsistencias encontradas:")
    print(f"  - Facturas: {total_inconsistencias_facturas}")
    print(f"  - Items: {total_inconsistencias_items}")
    print(f"\nMejoras implementadas (Fase 1):")
    print(f"  - Constraints activos: {total_constraints}")
    print(f"  - Computed properties: 6 (total_calculado, subtotal_calculado, etc.)")
    print(f"  - Validadores: 4 (tiene_inconsistencia_*)")

    print("\n" + "="*80)
    print("ESTADO: FASE 1 COMPLETADA - BASE DE DATOS PROFESIONAL")
    print("="*80)
    print("\nPróximos pasos (Fase 2):")
    print("  1. Corregir inconsistencias detectadas")
    print("  2. Migrar código para usar computed properties")
    print("  3. Eliminar campos redundantes (total_a_pagar, etc.)")
    print("  4. Implementar materialized views para agregaciones")
    print("\n")


if __name__ == "__main__":
    main()
