"""
Script para calcular y actualizar los campos de período en facturas existentes.
Ejecutar después de aplicar la migración add_periodo_fields_to_facturas.

Uso:
    python -m app.scripts.update_facturas_periodos
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.factura import Factura
from datetime import datetime
import sys

def update_periodos():
    """Actualiza los campos de período para todas las facturas existentes."""

    # Crear engine y sesión
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Contar facturas sin período
        total_facturas = db.query(Factura).filter(Factura.periodo_factura.is_(None)).count()

        if total_facturas == 0:
            print("Todas las facturas ya tienen periodo asignado.")
            return

        print(f"Actualizando {total_facturas} facturas...")

        # Procesar en lotes de 1000 para mejor rendimiento
        batch_size = 1000
        offset = 0
        updated = 0

        while True:
            # Obtener lote de facturas sin período
            facturas = db.query(Factura).filter(
                Factura.periodo_factura.is_(None)
            ).limit(batch_size).offset(offset).all()

            if not facturas:
                break

            # Actualizar cada factura en el lote
            for factura in facturas:
                if factura.fecha_emision:
                    factura.año_factura = factura.fecha_emision.year
                    factura.mes_factura = factura.fecha_emision.month
                    factura.periodo_factura = factura.fecha_emision.strftime('%Y-%m')
                    updated += 1

            # Commit del lote
            db.commit()
            print(f"Procesadas {updated}/{total_facturas} facturas...")

            offset += batch_size

        print(f"\nCompletado! {updated} facturas actualizadas correctamente.")

        # Mostrar estadísticas por período
        print("\nFacturas por periodo:")
        result = db.execute(text("""
            SELECT
                periodo_factura,
                COUNT(*) as total,
                SUM(total) as monto_total
            FROM facturas
            WHERE periodo_factura IS NOT NULL
            GROUP BY periodo_factura
            ORDER BY periodo_factura DESC
            LIMIT 12
        """))

        print(f"\n{'Periodo':<15} {'Cantidad':<15} {'Monto Total':<20}")
        print("-" * 50)
        for row in result:
            periodo, cantidad, monto = row
            monto_str = f"${monto:,.2f}" if monto else "$0.00"
            print(f"{periodo:<15} {cantidad:<15} {monto_str:<20}")

    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    print("Iniciando actualizacion de periodos en facturas...")
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    update_periodos()
