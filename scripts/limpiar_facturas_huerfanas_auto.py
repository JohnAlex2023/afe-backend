"""
Script para limpiar facturas huerfanas automaticamente (sin confirmacion).

PROBLEMA: Cuando se eliminan asignaciones, las facturas pueden quedar con responsable_id
pero sin una asignacion activa correspondiente. Esto causa inconsistencias en el dashboard.

SOLUCION: Este script identifica y limpia esas facturas huerfanas automaticamente.
"""
from collections import defaultdict
from sqlalchemy import and_
from app.core.database import SessionLocal
from app.models import Factura, AsignacionNitResponsable, Responsable


def main():
    """Limpia facturas huerfanas automaticamente."""
    db = SessionLocal()

    try:
        print("\n" + "="*70)
        print("LIMPIEZA AUTOMATICA DE FACTURAS HUERFANAS")
        print("="*70)

        # PASO 1: Obtener todas las facturas con responsable_id
        facturas_asignadas = db.query(Factura).filter(
            Factura.responsable_id.isnot(None)
        ).all()

        print(f"\nFacturas con responsable_id: {len(facturas_asignadas)}")

        if len(facturas_asignadas) == 0:
            print("\nSistema limpio - no hay facturas con responsable_id")
            return

        # PASO 2: Agrupar por responsable
        facturas_por_responsable = defaultdict(list)
        for factura in facturas_asignadas:
            facturas_por_responsable[factura.responsable_id].append(factura)

        print(f"\nResponsables con facturas asignadas: {len(facturas_por_responsable)}")

        # PASO 3: Verificar cuales responsables tienen asignaciones activas
        facturas_huerfanas = []
        facturas_validas = []

        for responsable_id, facturas in facturas_por_responsable.items():
            # Buscar si este responsable tiene asignaciones activas
            asignaciones_activas = db.query(AsignacionNitResponsable).filter(
                and_(
                    AsignacionNitResponsable.responsable_id == responsable_id,
                    AsignacionNitResponsable.activo == True
                )
            ).count()

            responsable = db.query(Responsable).filter(
                Responsable.id == responsable_id
            ).first()
            nombre_resp = responsable.nombre if responsable else "DESCONOCIDO"

            if asignaciones_activas == 0:
                # HUERFANAS: facturas con responsable pero sin asignaciones activas
                print(f"\n  Responsable ID={responsable_id} ({nombre_resp}):")
                print(f"    - {len(facturas)} facturas asignadas")
                print("    - 0 asignaciones activas")
                print("    -> FACTURAS HUERFANAS (se limpiaran)")
                facturas_huerfanas.extend(facturas)
            else:
                # VALIDAS: facturas con responsable y con asignaciones activas
                print(f"\n  Responsable ID={responsable_id} ({nombre_resp}):")
                print(f"    - {len(facturas)} facturas asignadas")
                print(f"    - {asignaciones_activas} asignaciones activas")
                print("    -> OK (facturas validas)")
                facturas_validas.extend(facturas)

        # PASO 4: Resumen
        print("\n" + "="*70)
        print("RESUMEN")
        print("="*70)
        print(f"Facturas VALIDAS (con asignacion activa): {len(facturas_validas)}")
        print(f"Facturas HUERFANAS (sin asignacion activa): {len(facturas_huerfanas)}")

        # PASO 5: Limpieza automatica
        if len(facturas_huerfanas) > 0:
            print("\n" + "="*70)
            print("LIMPIEZA AUTOMATICA")
            print("="*70)
            print(f"\nLimpiando {len(facturas_huerfanas)} facturas huerfanas...")

            for factura in facturas_huerfanas:
                factura.responsable_id = None

            db.commit()
            print(f"\nLIMPIEZA COMPLETADA: {len(facturas_huerfanas)} facturas limpiadas")
            print("Las facturas ahora tienen responsable_id = NULL")
            print("El dashboard mostrara los numeros correctos")
        else:
            print("\nNo hay facturas huerfanas - sistema sincronizado correctamente")

    finally:
        db.close()


if __name__ == "__main__":
    main()
