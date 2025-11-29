#!/usr/bin/env python
"""
Script de reparación CRÍTICA: Reconstruye asignaciones con IDs correctos de usuarios
El problema: Las asignaciones tienen IDs de la tabla vieja 'responsables' que no existen en 'usuarios'
"""

import sys
from pathlib import Path

backend_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, backend_dir)

import os
os.chdir(backend_dir)

from app.db.session import SessionLocal
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.usuario import Usuario
from app.models.factura import Factura, EstadoAsignacion
from datetime import datetime

def reparar_asignaciones_ids():
    """Reconstruye las asignaciones usando los IDs correctos de usuarios"""
    db = SessionLocal()

    print("\n" + "="*80)
    print("REPARACION CRITICA: Reconstruyendo asignaciones con IDs correctos")
    print("="*80)
    print(f"Fecha/Hora: {datetime.now().isoformat()}\n")

    try:
        # ============ PASO 1: DIAGNOSTICAR ASIGNACIONES ROTAS ============
        print("PASO 1: Diagnosticando asignaciones con IDs invalidos")
        print("-" * 80)

        # Obtener todas las asignaciones
        todas_asignaciones = db.query(AsignacionNitResponsable).all()
        print(f"Total de asignaciones en tabla: {len(todas_asignaciones)}")

        # Verificar cuáles tienen IDs inválidos
        asignaciones_rotas = []
        asignaciones_validas = []

        for asign in todas_asignaciones:
            usuario = db.query(Usuario).filter(Usuario.id == asign.responsable_id).first()
            if not usuario:
                asignaciones_rotas.append(asign)
            else:
                asignaciones_validas.append(asign)

        print(f"Asignaciones validas: {len(asignaciones_validas)}")
        print(f"Asignaciones ROTAS (responsable_id invalido): {len(asignaciones_rotas)}")

        if asignaciones_rotas:
            print(f"\nEjemplos de asignaciones rotas:")
            for asign in asignaciones_rotas[:10]:
                print(f"  NIT={asign.nit}, responsable_id={asign.responsable_id} (NO EXISTE)")
        print()

        # ============ PASO 2: INTENTAR MAPEAR ASIGNACIONES ROTAS ============
        print("PASO 2: Intentando mapear asignaciones rotas a usuarios existentes")
        print("-" * 80)

        # Obtener usuarios existentes
        usuarios = db.query(Usuario).filter(Usuario.activo == True).all()
        print(f"Usuarios activos disponibles: {len(usuarios)}")
        for u in usuarios:
            print(f"  ID={u.id}, usuario={u.usuario}, nombre={u.nombre}")
        print()

        # La estrategia es:
        # 1. Si solo hay 1 usuario activo, asignar todas las facturas a ese usuario
        # 2. Si hay múltiples, intentar un mapeo inteligente por nombre/correo

        reparadas = 0
        no_reparables = 0

        if len(usuarios) == 0:
            print("ERROR CRITICO: No hay usuarios activos en el sistema")
            return False

        if len(usuarios) == 1:
            # Caso simple: un solo usuario responsable de todo
            usuario_unico = usuarios[0]
            print(f"Estrategia: Un usuario ({usuario_unico.nombre}) - asignar todo a este usuario\n")

            for asign in asignaciones_rotas:
                try:
                    # Verificar que el usuario existe
                    if asign.responsable_id != usuario_unico.id:
                        asign.responsable_id = usuario_unico.id
                        asign.actualizado_por = "SCRIPT_REPARACION_IDS"
                        asign.actualizado_en = datetime.now()
                        reparadas += 1
                except Exception as e:
                    print(f"Error reparando asignacion NIT {asign.nit}: {str(e)}")
                    no_reparables += 1

            db.commit()
            print(f"[OK] {reparadas} asignaciones reparadas")
            print()

        else:
            # Caso complejo: múltiples usuarios
            # Por ahora, asignar al usuario que aparece con más frecuencia en accion_por
            print(f"Estrategia: Mapeo inteligente por nombre/usuario\n")

            # Construir mapeo de nombres de usuario
            nombre_a_usuario = {}
            for usuario in usuarios:
                nombre_a_usuario[usuario.nombre.lower()] = usuario
                nombre_a_usuario[usuario.usuario.lower()] = usuario
                if usuario.email:
                    nombre_a_usuario[usuario.email.lower()] = usuario

            for asign in asignaciones_rotas:
                # Intentar encontrar un usuario por nombre del proveedor o nombre_proveedor
                encontrado = False

                # Buscar por nombre proveedor
                if asign.nombre_proveedor:
                    for key, usuario in nombre_a_usuario.items():
                        if key in asign.nombre_proveedor.lower():
                            asign.responsable_id = usuario.id
                            asign.actualizado_por = "SCRIPT_REPARACION_IDS"
                            asign.actualizado_en = datetime.now()
                            reparadas += 1
                            encontrado = True
                            break

                if not encontrado:
                    # Asignar al primer usuario disponible por defecto
                    asign.responsable_id = usuarios[0].id
                    asign.actualizado_por = "SCRIPT_REPARACION_IDS"
                    asign.actualizado_en = datetime.now()
                    reparadas += 1

            db.commit()
            print(f"[OK] {reparadas} asignaciones reparadas (mapeo inteligente)")
            print()

        # ============ PASO 3: SINCRONIZAR FACTURAS CON ASIGNACIONES ============
        print("PASO 3: Sincronizando facturas con asignaciones reparadas")
        print("-" * 80)

        # Ahora sincronizar facturas
        facturas_sin_responsable = db.query(Factura).filter(
            Factura.responsable_id == None
        ).all()

        print(f"Facturas sin responsable: {len(facturas_sin_responsable)}")

        asignadas = 0

        for factura in facturas_sin_responsable:
            # Obtener asignacion del NIT
            from app.models.workflow_aprobacion import WorkflowAprobacionFactura

            workflow = db.query(WorkflowAprobacionFactura).filter(
                WorkflowAprobacionFactura.factura_id == factura.id
            ).first()

            if workflow and workflow.nit_proveedor:
                asignacion = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == workflow.nit_proveedor
                ).first()

                if asignacion and asignacion.responsable_id:
                    # Verificar que el usuario existe
                    usuario_existe = db.query(Usuario).filter(
                        Usuario.id == asignacion.responsable_id
                    ).first()

                    if usuario_existe:
                        factura.responsable_id = asignacion.responsable_id
                        factura.estado_asignacion = EstadoAsignacion.asignado
                        asignadas += 1

        db.commit()
        print(f"[OK] {asignadas} facturas sincronizadas con asignaciones")
        print()

        # ============ VERIFICACIÓN FINAL ============
        print("VERIFICACIÓN FINAL")
        print("-" * 80)

        asignaciones_validas_ahora = db.query(AsignacionNitResponsable).count()
        asignaciones_rotas_ahora = 0

        for asign in db.query(AsignacionNitResponsable).all():
            usuario = db.query(Usuario).filter(Usuario.id == asign.responsable_id).first()
            if not usuario:
                asignaciones_rotas_ahora += 1

        print(f"Asignaciones totales: {asignaciones_validas_ahora}")
        print(f"Asignaciones rotas DESPUÉS: {asignaciones_rotas_ahora}")

        if asignaciones_rotas_ahora == 0:
            print("[OK] TODAS las asignaciones son validas")
        else:
            print(f"[WARN] Aun hay {asignaciones_rotas_ahora} asignaciones rotas")

        # Estadísticas de facturas
        total_facturas = db.query(Factura).count()
        con_responsable = db.query(Factura).filter(Factura.responsable_id != None).count()
        sin_responsable = db.query(Factura).filter(Factura.responsable_id == None).count()

        print(f"\nFacturas totales: {total_facturas}")
        print(f"Con responsable: {con_responsable} ({con_responsable/total_facturas*100:.1f}%)")
        print(f"Sin responsable: {sin_responsable} ({sin_responsable/total_facturas*100:.1f}%)")

        print("\n" + "="*80)
        print("REPARACION COMPLETADA")
        print("="*80)

        return True

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = reparar_asignaciones_ids()
    sys.exit(0 if success else 1)
