#!/usr/bin/env python
"""
Script de reparación: Sincroniza facturas con asignaciones de NITs
Corrige la desincronización después de la migración responsables -> usuarios
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
from sqlalchemy import func, text, and_, or_
from datetime import datetime

def reparar_desincronizacion():
    """Repara la desincronización del sistema"""
    db = SessionLocal()

    print("\n" + "="*80)
    print("SCRIPT DE REPARACIÓN - DESINCRONIZACIÓN FACTURAS/NITs")
    print("="*80)
    print(f"Fecha/Hora: {datetime.now().isoformat()}\n")

    try:
        # ============ PASO 1: ACTIVAR ASIGNACIONES ============
        print("PASO 1: Activando asignaciones de NITs deshabilitadas")
        print("-" * 80)

        asignaciones_inactivas = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == False
        ).all()

        inactivas_count = len(asignaciones_inactivas)
        print(f"Encontradas {inactivas_count} asignaciones inactivas")

        for asignacion in asignaciones_inactivas:
            asignacion.activo = True
            asignacion.actualizado_en = datetime.now()
            asignacion.actualizado_por = "SCRIPT_REPARACION"

        db.commit()
        print(f"[OK] {inactivas_count} asignaciones activadas")
        print()

        # ============ PASO 2: SINCRONIZAR RESPONSABLES EN FACTURAS ============
        print("PASO 2: Sincronizando responsables de facturas")
        print("-" * 80)

        # Obtener todas las facturas sin responsable
        facturas_sin_responsable = db.query(Factura).filter(
            Factura.responsable_id == None
        ).all()

        print(f"Encontradas {len(facturas_sin_responsable)} facturas sin responsable")

        asignadas = 0
        no_encontradas = 0

        for factura in facturas_sin_responsable:
            # Buscar asignación en workflow
            workflow = db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            if workflow and workflow.responsable_id:
                # Si hay un responsable en workflow, usarlo
                factura.responsable_id = workflow.responsable_id
                factura.estado_asignacion = EstadoAsignacion.asignado
                asignadas += 1
            elif workflow and workflow.nit_proveedor:
                # Si hay NIT en workflow, buscar asignación
                asignacion = db.query(AsignacionNitResponsable).filter(
                    and_(
                        AsignacionNitResponsable.nit == workflow.nit_proveedor,
                        AsignacionNitResponsable.activo == True
                    )
                ).first()

                if asignacion:
                    factura.responsable_id = asignacion.responsable_id
                    factura.estado_asignacion = EstadoAsignacion.asignado
                    asignadas += 1
                else:
                    no_encontradas += 1
            else:
                no_encontradas += 1

        db.commit()
        print(f"[OK] {asignadas} facturas sincronizadas")
        print(f"[WARN] {no_encontradas} facturas sin asignacion disponible")
        print()

        # ============ PASO 3: REPARAR FACTURAS HUÉRFANAS ============
        print("PASO 3: Procesando facturas huérfanas")
        print("-" * 80)

        # Facturas que tienen accion_por pero no responsable_id
        huerfanas = db.query(Factura).filter(
            and_(
                Factura.responsable_id == None,
                Factura.accion_por != None
            )
        ).all()

        print(f"Encontradas {len(huerfanas)} facturas huérfanas")

        # Intentar asignarlas por accion_por (nombre del usuario)
        reparadas = 0
        sin_reparar = 0

        for factura in huerfanas:
            # Buscar usuario por nombre
            usuario = db.query(Usuario).filter(
                or_(
                    Usuario.nombre == factura.accion_por,
                    Usuario.usuario == factura.accion_por,
                    Usuario.nombre.ilike(f"%{factura.accion_por}%")
                )
            ).first()

            if usuario:
                factura.responsable_id = usuario.id
                factura.estado_asignacion = EstadoAsignacion.asignado
                reparadas += 1
            else:
                # Marcar como huérfana pero con estado actualizado
                factura.estado_asignacion = EstadoAsignacion.huerfano
                sin_reparar += 1

        db.commit()
        print(f"[OK] {reparadas} facturas huerfanas reparadas")
        print(f"[WARN] {sin_reparar} facturas siguen huerfanas (sin usuario identificado)")
        print()

        # ============ PASO 4: ACTUALIZAR ESTADOS DE ASIGNACIÓN ============
        print("PASO 4: Recalculando estados de asignación")
        print("-" * 80)

        todas_facturas = db.query(Factura).all()
        actualizadas = 0

        for factura in todas_facturas:
            nuevo_estado = factura.calcular_estado_asignacion()
            if factura.estado_asignacion != nuevo_estado:
                factura.estado_asignacion = nuevo_estado
                actualizadas += 1

        db.commit()
        print(f"[OK] {actualizadas} estados de asignacion actualizados")
        print()

        # ============ VERIFICACIÓN FINAL ============
        print("VERIFICACIÓN FINAL")
        print("-" * 80)

        total = db.query(Factura).count()
        con_responsable = db.query(Factura).filter(Factura.responsable_id != None).count()
        sin_responsable = db.query(Factura).filter(Factura.responsable_id == None).count()

        print(f"Total de facturas: {total}")
        print(f"Con responsable asignado: {con_responsable} ({con_responsable/total*100:.1f}%)")
        print(f"Sin responsable: {sin_responsable} ({sin_responsable/total*100:.1f}%)")

        # Estados
        estados = {}
        for estado_enum in EstadoAsignacion:
            count = db.query(Factura).filter(Factura.estado_asignacion == estado_enum).count()
            estados[estado_enum.value] = count

        print(f"\nEstados de asignación:")
        for estado, count in estados.items():
            print(f"  {estado:20} {count:8} ({count/total*100:5.1f}%)")

        print("\n" + "="*80)
        print("REPARACIÓN COMPLETADA")
        print("="*80)

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

    return True

if __name__ == "__main__":
    success = reparar_desincronizacion()
    sys.exit(0 if success else 1)
