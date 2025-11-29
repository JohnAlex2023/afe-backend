#!/usr/bin/env python
"""
Script de diagnóstico: Detecta desincronización entre Facturas y Asignaciones de NITs
Analiza el estado del sistema después de la migración de tabla responsables -> usuarios
"""

import sys
from pathlib import Path

# Agregar el directorio padre al path
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

def diagnostico_completo():
    """Ejecuta diagnóstico completo del sistema"""
    db = SessionLocal()

    print("\n" + "="*80)
    print("DIAGNÓSTICO COMPLETO DE DESINCRONIZACIÓN")
    print("="*80)
    print(f"Fecha/Hora: {datetime.now().isoformat()}\n")

    try:
        # ============ 1. ESTADÍSTICAS GENERALES ============
        print("1. ESTADÍSTICAS GENERALES")
        print("-" * 80)

        total_facturas = db.query(Factura).count()
        total_usuarios = db.query(Usuario).filter(Usuario.activo == True).count()
        total_asignaciones = db.query(AsignacionNitResponsable).count()
        total_asignaciones_activas = db.query(AsignacionNitResponsable).filter(AsignacionNitResponsable.activo == True).count()

        print(f"Total de facturas: {total_facturas}")
        print(f"Total de usuarios activos: {total_usuarios}")
        print(f"Total de asignaciones NIT: {total_asignaciones}")
        print(f"Total de asignaciones NIT activas: {total_asignaciones_activas}")
        print()

        # ============ 2. ESTADO DE RESPONSABLES ============
        print("2. ESTADO DE RESPONSABLES EN FACTURAS")
        print("-" * 80)

        facturas_con_responsable = db.query(Factura).filter(Factura.responsable_id != None).count()
        facturas_sin_responsable = db.query(Factura).filter(Factura.responsable_id == None).count()

        print(f"Facturas CON responsable_id: {facturas_con_responsable}")
        print(f"Facturas SIN responsable_id: {facturas_sin_responsable}")
        print(f"Porcentaje asignado: {(facturas_con_responsable/total_facturas*100):.1f}%")
        print()

        # ============ 3. ESTADOS DE ASIGNACIÓN ============
        print("3. ESTADOS DE ASIGNACIÓN")
        print("-" * 80)

        estados = {
            EstadoAsignacion.sin_asignar: "Sin asignar",
            EstadoAsignacion.asignado: "Asignado",
            EstadoAsignacion.huerfano: "Huérfano",
            EstadoAsignacion.inconsistente: "Inconsistente"
        }

        for estado_enum, label in estados.items():
            count = db.query(Factura).filter(Factura.estado_asignacion == estado_enum).count()
            pct = (count/total_facturas*100) if total_facturas > 0 else 0
            print(f"{label:20} {count:8}  ({pct:5.1f}%)")
        print()

        # ============ 4. NITs Y ASIGNACIONES ============
        print("4. ANÁLISIS DE NITs Y ASIGNACIONES")
        print("-" * 80)

        # NITs únicos en asignaciones
        nits_asignados = db.query(AsignacionNitResponsable.nit).distinct().count()

        # NITs identificados en workflow
        nits_en_workflow = db.query(WorkflowAprobacionFactura.nit_proveedor).filter(
            WorkflowAprobacionFactura.nit_proveedor != None
        ).distinct().count()

        print(f"NITs únicos en tabla de asignaciones: {nits_asignados}")
        print(f"NITs identificados en workflow: {nits_en_workflow}")
        print()

        # ============ 5. FACTURAS DESINCRONIZADAS (CRÍTICO) ============
        print("5. FACTURAS DESINCRONIZADAS (CRÍTICO)")
        print("-" * 80)

        # Facturas con responsable que NO EXISTE en usuarios
        facturas_responsable_invalido = db.query(Factura).outerjoin(
            Usuario, Factura.responsable_id == Usuario.id
        ).filter(
            and_(
                Factura.responsable_id != None,
                Usuario.id == None
            )
        ).count()

        print(f"Facturas con responsable_id INVÁLIDO (usuario no existe): {facturas_responsable_invalido}")

        if facturas_responsable_invalido > 0:
            print("  ⚠️  PROBLEMA CRÍTICO: Referencias rotas a usuarios\n")

        # ============ 6. ASIGNACIONES DESINCRONIZADAS ============
        print("6. ASIGNACIONES DESINCRONIZADAS")
        print("-" * 80)

        # Asignaciones con responsable inválido
        asignaciones_invalidas = db.query(AsignacionNitResponsable).outerjoin(
            Usuario, AsignacionNitResponsable.responsable_id == Usuario.id
        ).filter(
            Usuario.id == None
        ).count()

        print(f"Asignaciones con responsable_id INVÁLIDO: {asignaciones_invalidas}")

        # ============ 7. FACTURAS HUÉRFANAS ============
        print("7. FACTURAS HUÉRFANAS (sin responsable pero procesadas)")
        print("-" * 80)

        huerfanas = db.query(Factura).filter(
            and_(
                Factura.responsable_id == None,
                Factura.accion_por != None
            )
        ).count()

        print(f"Total de facturas huérfanas: {huerfanas}")

        if huerfanas > 0:
            print("\nEjemplos de facturas huérfanas:")
            ejemplos = db.query(Factura).filter(
                and_(
                    Factura.responsable_id == None,
                    Factura.accion_por != None
                )
            ).limit(5).all()

            for f in ejemplos:
                print(f"  - Factura #{f.id} ({f.numero_factura}): acción_por='{f.accion_por}'")
        print()

        # ============ 8. PROBLEMAS IDENTIFICADOS ============
        print("8. RESUMEN DE PROBLEMAS")
        print("-" * 80)

        problemas = []

        if facturas_responsable_invalido > 0:
            problemas.append(f"✗ {facturas_responsable_invalido} facturas con responsable_id inválido")

        if asignaciones_invalidas > 0:
            problemas.append(f"✗ {asignaciones_invalidas} asignaciones con responsable_id inválido")

        if huerfanas > 0:
            problemas.append(f"✗ {huerfanas} facturas huérfanas (sin responsable)")

        if facturas_sin_responsable > 0:
            problemas.append(f"⚠️  {facturas_sin_responsable} facturas sin asignar")

        if not problemas:
            print("✓ No se detectaron problemas críticos")
        else:
            print("PROBLEMAS DETECTADOS:")
            for p in problemas:
                print(f"  {p}")

        print()
        print("="*80)

    finally:
        db.close()

if __name__ == "__main__":
    diagnostico_completo()
