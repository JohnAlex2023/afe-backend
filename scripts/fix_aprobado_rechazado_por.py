"""
Script de migracion para corregir campos aprobado_por y rechazado_por
que fueron guardados con IDs en lugar de nombres de usuarios.

Este script:
1. Busca todas las facturas donde aprobado_por o rechazado_por son numeros (IDs)
2. Intenta encontrar el responsable con ese ID
3. Actualiza el campo con el nombre completo del responsable
"""
import sys
import os

# Agregar el directorio padre al path para poder importar app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.responsable import Responsable

def es_numero(valor: str) -> bool:
    """Verifica si un string es un numero"""
    if not valor:
        return False
    try:
        int(valor)
        return True
    except ValueError:
        return False

def fix_aprobado_rechazado_por():
    """Corrige los campos aprobado_por y rechazado_por en facturas"""
    db: Session = SessionLocal()

    try:
        # Obtener todas las facturas
        facturas = db.query(Factura).all()

        total_facturas = len(facturas)
        aprobado_corregidos = 0
        rechazado_corregidos = 0

        print(f"\n[INFO] Analizando {total_facturas} facturas...")
        print("-" * 70)

        for factura in facturas:
            factura_actualizada = False

            # Verificar aprobado_por
            if factura.aprobado_por and es_numero(factura.aprobado_por):
                responsable_id = int(factura.aprobado_por)
                responsable = db.query(Responsable).filter(Responsable.id == responsable_id).first()

                if responsable:
                    print(f"\n[FIX] Factura {factura.numero_factura}:")
                    print(f"      aprobado_por: '{factura.aprobado_por}' (ID) -> '{responsable.nombre}'")
                    factura.aprobado_por = responsable.nombre
                    factura_actualizada = True
                    aprobado_corregidos += 1
                else:
                    print(f"\n[WARN] Factura {factura.numero_factura}:")
                    print(f"       No se encontro responsable con ID {responsable_id}")

            # Verificar rechazado_por
            if factura.rechazado_por and es_numero(factura.rechazado_por):
                responsable_id = int(factura.rechazado_por)
                responsable = db.query(Responsable).filter(Responsable.id == responsable_id).first()

                if responsable:
                    print(f"\n[FIX] Factura {factura.numero_factura}:")
                    print(f"      rechazado_por: '{factura.rechazado_por}' (ID) -> '{responsable.nombre}'")
                    factura.rechazado_por = responsable.nombre
                    factura_actualizada = True
                    rechazado_corregidos += 1
                else:
                    print(f"\n[WARN] Factura {factura.numero_factura}:")
                    print(f"       No se encontro responsable con ID {responsable_id}")

            # Commit si hubo cambios
            if factura_actualizada:
                db.add(factura)

        # Commit final
        db.commit()

        print("\n" + "=" * 70)
        print(f"\n[RESUMEN] Migracion completada:")
        print(f"  - Total facturas analizadas: {total_facturas}")
        print(f"  - Campos 'aprobado_por' corregidos: {aprobado_corregidos}")
        print(f"  - Campos 'rechazado_por' corregidos: {rechazado_corregidos}")
        print(f"  - Total correcciones: {aprobado_corregidos + rechazado_corregidos}")
        print("\n[OK] Migracion exitosa!")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error durante la migracion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SCRIPT DE MIGRACION: Corregir aprobado_por y rechazado_por")
    print("=" * 70)

    respuesta = input("\nEste script corregira los datos historicos. Continuar? (s/n): ")

    if respuesta.lower() == 's':
        fix_aprobado_rechazado_por()
    else:
        print("\n[CANCELADO] Migracion cancelada por el usuario")
