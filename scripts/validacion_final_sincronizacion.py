#!/usr/bin/env python
"""
Script de validación final: Verifica que la sincronización está completa y correcta
"""

import sys
from pathlib import Path

backend_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, backend_dir)

import os
os.chdir(backend_dir)

from app.db.session import SessionLocal
from app.models.factura import Factura, EstadoAsignacion
from app.models.workflow_aprobacion import AsignacionNitResponsable, WorkflowAprobacionFactura
from app.models.usuario import Usuario
from app.models.proveedor import Proveedor
from sqlalchemy import and_, or_
from datetime import datetime

def validar_sincronizacion():
    """Valida que el sistema esté completamente sincronizado"""
    db = SessionLocal()

    print("\n" + "="*80)
    print("VALIDACION FINAL - SINCRONIZACION DEL SISTEMA")
    print("="*80)
    print(f"Fecha/Hora: {datetime.now().isoformat()}\n")

    problemas = []
    advertencias = []
    info_general = {}

    try:
        # ============ 1. ESTADÍSTICAS GENERALES ============
        print("1. ESTADISTICAS GENERALES")
        print("-" * 80)

        total_facturas = db.query(Factura).count()
        total_usuarios = db.query(Usuario).filter(Usuario.activo == True).count()
        total_asignaciones = db.query(AsignacionNitResponsable).count()

        print(f"Total de facturas: {total_facturas}")
        print(f"Total de usuarios activos: {total_usuarios}")
        print(f"Total de asignaciones NIT: {total_asignaciones}")

        info_general['total_facturas'] = total_facturas
        info_general['total_usuarios'] = total_usuarios
        info_general['total_asignaciones'] = total_asignaciones

        if total_usuarios == 0:
            problemas.append("NO HAY USUARIOS ACTIVOS EN EL SISTEMA")
        if total_asignaciones == 0:
            advertencias.append("No hay asignaciones de NITs configuradas (opcional)")

        print()

        # ============ 2. INTEGRIDAD DE FACTURAS ============
        print("2. INTEGRIDAD DE FACTURAS")
        print("-" * 80)

        # Facturas sin responsable
        sin_responsable = db.query(Factura).filter(Factura.responsable_id == None).count()
        con_responsable = db.query(Factura).filter(Factura.responsable_id != None).count()

        print(f"Facturas CON responsable: {con_responsable} ({con_responsable/total_facturas*100:.1f}%)")
        print(f"Facturas SIN responsable: {sin_responsable} ({sin_responsable/total_facturas*100:.1f}%)")

        if sin_responsable > 0:
            problemas.append(f"Hay {sin_responsable} facturas sin responsable asignado")

        # Facturas con responsable inválido
        invalidos = db.query(Factura).outerjoin(
            Usuario, Factura.responsable_id == Usuario.id
        ).filter(
            and_(
                Factura.responsable_id != None,
                Usuario.id == None
            )
        ).count()

        print(f"Facturas con responsable INVALIDO: {invalidos}")

        if invalidos > 0:
            problemas.append(f"Hay {invalidos} facturas con referencias rotas a usuarios")

        print()

        # ============ 3. ESTADOS DE ASIGNACIÓN ============
        print("3. ESTADOS DE ASIGNACION")
        print("-" * 80)

        estados = {}
        for estado_enum in EstadoAsignacion:
            count = db.query(Factura).filter(Factura.estado_asignacion == estado_enum).count()
            estados[estado_enum.value] = count
            pct = (count / total_facturas * 100) if total_facturas > 0 else 0
            print(f"{estado_enum.value:20} {count:8} ({pct:5.1f}%)")

        if estados.get('asignado', 0) < total_facturas * 0.95:
            advertencias.append(f"Menos del 95% de facturas están en estado 'asignado'")

        print()

        # ============ 4. INTEGRIDAD DE ASIGNACIONES ============
        print("4. INTEGRIDAD DE ASIGNACIONES NIT")
        print("-" * 80)

        # Asignaciones con responsable inválido
        asign_invalidas = db.query(AsignacionNitResponsable).outerjoin(
            Usuario, AsignacionNitResponsable.responsable_id == Usuario.id
        ).filter(
            Usuario.id == None
        ).count()

        print(f"Asignaciones con responsable INVALIDO: {asign_invalidas}")

        if asign_invalidas > 0:
            problemas.append(f"Hay {asign_invalidas} asignaciones con referencias rotas a usuarios")

        # NITs sin asignación
        nits_totales = db.query(Proveedor).filter(Proveedor.nit != None).count()
        nits_con_asignacion = db.query(AsignacionNitResponsable.nit).distinct().count()

        print(f"Total de proveedores (NITs): {nits_totales}")
        print(f"NITs con asignacion: {nits_con_asignacion}")

        print()

        # ============ 5. SINCRONIZACIÓN FACTURAS-ASIGNACIONES ============
        print("5. SINCRONIZACION FACTURAS-ASIGNACIONES")
        print("-" * 80)

        # Buscar facturas cuyo responsable no coincide con la asignación NIT
        desincronizadas = 0

        for factura in db.query(Factura).filter(Factura.responsable_id != None).all():
            workflow = db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            if workflow and workflow.nit_proveedor:
                asignacion = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == workflow.nit_proveedor
                ).first()

                if asignacion and asignacion.responsable_id != factura.responsable_id:
                    desincronizadas += 1

        print(f"Facturas desincronizadas (responsable != asignacion NIT): {desincronizadas}")

        if desincronizadas > 0:
            advertencias.append(f"Hay {desincronizadas} facturas cuyo responsable no coincide con la asignacion NIT")

        print()

        # ============ 6. VERIFICACIÓN DE TABLAS ============
        print("6. VERIFICACION DE TABLAS Y MODELOS")
        print("-" * 80)

        # Intentar acceder a la tabla usuarios (no responsables)
        try:
            usuarios_count = db.query(Usuario).count()
            print(f"Tabla 'usuarios': OK ({usuarios_count} registros)")
        except Exception as e:
            problemas.append(f"Error accediendo tabla 'usuarios': {str(e)}")
            print(f"Tabla 'usuarios': ERROR - {str(e)}")

        # Intentar acceder a tabla asignaciones
        try:
            asign_count = db.query(AsignacionNitResponsable).count()
            print(f"Tabla 'asignacion_nit_responsable': OK ({asign_count} registros)")
        except Exception as e:
            problemas.append(f"Error accediendo tabla 'asignacion_nit_responsable': {str(e)}")
            print(f"Tabla 'asignacion_nit_responsable': ERROR - {str(e)}")

        # Intentar acceder a tabla facturas
        try:
            fact_count = db.query(Factura).count()
            print(f"Tabla 'facturas': OK ({fact_count} registros)")
        except Exception as e:
            problemas.append(f"Error accediendo tabla 'facturas': {str(e)}")
            print(f"Tabla 'facturas': ERROR - {str(e)}")

        print()

        # ============ 7. RESUMEN ============
        print("7. RESUMEN FINAL")
        print("-" * 80)

        if not problemas and not advertencias:
            print("[OK] SISTEMA COMPLETAMENTE SINCRONIZADO")
            print("\nEstado:")
            print(f"  - 100% de facturas tienen responsable asignado")
            print(f"  - Todas las referencias de usuarios son válidas")
            print(f"  - Todas las asignaciones NIT son válidas")
            print(f"  - Sistema listo para producción")
            print("\n" + "="*80)
            print("VALIDACION EXITOSA")
            print("="*80)
            return True

        if problemas:
            print("\n[ERROR] PROBLEMAS DETECTADOS:")
            for i, p in enumerate(problemas, 1):
                print(f"  {i}. {p}")

        if advertencias:
            print("\n[WARN] ADVERTENCIAS:")
            for i, a in enumerate(advertencias, 1):
                print(f"  {i}. {a}")

        print("\n" + "="*80)
        if problemas:
            print("VALIDACION FALLIDA - REVISAR PROBLEMAS CRITTICOS")
            return False
        else:
            print("VALIDACION CON ADVERTENCIAS - REVISAR RECOMENDACIONES")
            return True

    except Exception as e:
        print(f"\nERROR EN VALIDACION: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = validar_sincronizacion()
    sys.exit(0 if success else 1)
