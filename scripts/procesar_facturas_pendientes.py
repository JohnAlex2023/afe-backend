#!/usr/bin/env python3
"""
Script para procesar automáticamente facturas pendientes.

Ejecutar después de que invoice_extractor haya ingresado facturas nuevas.
Activa el workflow automático para todas las facturas sin procesar.

Uso:
    python scripts/procesar_facturas_pendientes.py [--limite LIMITE]

Ejemplo:
    python scripts/procesar_facturas_pendientes.py --limite 100
"""

import sys
import os
import argparse
from pathlib import Path

# Agregar el directorio raíz al PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.workflow_automatico import WorkflowAutomaticoService
from app.models.factura import Factura
from app.models.workflow_aprobacion import WorkflowAprobacionFactura


def procesar_facturas_pendientes(limite: int = 100, verbose: bool = True):
    """
    Procesa todas las facturas que no tienen workflow asignado.

    Args:
        limite: Máximo de facturas a procesar
        verbose: Si debe mostrar mensajes detallados

    Returns:
        dict: Estadísticas del procesamiento
    """
    db: Session = SessionLocal()

    try:
        if verbose:
            print("=" * 70)
            print("PROCESAMIENTO AUTOMÁTICO DE FACTURAS PENDIENTES")
            print("=" * 70)
            print()

        # Obtener facturas sin workflow
        facturas_sin_workflow = db.query(Factura).filter(
            ~Factura.id.in_(
                db.query(WorkflowAprobacionFactura.factura_id)
            )
        ).limit(limite).all()

        if not facturas_sin_workflow:
            if verbose:
                print("  No hay facturas pendientes de procesar")
            return {
                "total_procesadas": 0,
                "exitosas": 0,
                "errores": []
            }

        if verbose:
            print(f" Facturas encontradas: {len(facturas_sin_workflow)}")
            print(f" Iniciando procesamiento...")
            print()

        # Inicializar servicio
        servicio = WorkflowAutomaticoService(db)

        # Estadísticas
        stats = {
            "total_procesadas": 0,
            "exitosas": 0,
            "aprobadas_automaticamente": 0,
            "en_revision": 0,
            "errores": [],
            "workflows_creados": []
        }

        # Procesar cada factura
        for i, factura in enumerate(facturas_sin_workflow, 1):
            try:
                if verbose:
                    print(f"[{i}/{len(facturas_sin_workflow)}] Procesando factura {factura.numero_factura}...")

                resultado = servicio.procesar_factura_nueva(factura.id)

                stats["total_procesadas"] += 1

                if resultado.get("exito"):
                    stats["exitosas"] += 1

                    # Clasificar por estado
                    if resultado.get("aprobada_automaticamente"):
                        stats["aprobadas_automaticamente"] += 1
                        if verbose:
                            print(f"    APROBADA AUTOMÁTICAMENTE")
                    elif resultado.get("requiere_revision"):
                        stats["en_revision"] += 1
                        if verbose:
                            print(f"    EN REVISIÓN (similitud: {resultado.get('porcentaje_similitud', 0)}%)")

                    stats["workflows_creados"].append({
                        "factura_id": factura.id,
                        "numero_factura": factura.numero_factura,
                        "workflow_id": resultado.get("workflow_id"),
                        "estado": resultado.get("estado")
                    })
                else:
                    error_msg = resultado.get("error", "Error desconocido")
                    stats["errores"].append({
                        "factura_id": factura.id,
                        "numero_factura": factura.numero_factura,
                        "error": error_msg
                    })
                    if verbose:
                        print(f"   ERROR: {error_msg}")

            except Exception as e:
                stats["errores"].append({
                    "factura_id": factura.id,
                    "numero_factura": factura.numero_factura,
                    "error": str(e)
                })
                if verbose:
                    print(f"   EXCEPCIÓN: {e}")

        # Resumen final
        if verbose:
            print()
            print("=" * 70)
            print("RESUMEN DEL PROCESAMIENTO")
            print("=" * 70)
            print(f"Total procesadas:              {stats['total_procesadas']}")
            print(f"Exitosas:                      {stats['exitosas']}")
            print(f"  ├─ Aprobadas automáticamente: {stats['aprobadas_automaticamente']}")
            print(f"  └─ Requieren revisión:        {stats['en_revision']}")
            print(f"Errores:                       {len(stats['errores'])}")

            if stats['errores']:
                print()
                print("ERRORES DETECTADOS:")
                for error in stats['errores']:
                    print(f"  - Factura {error['numero_factura']}: {error['error']}")

            print("=" * 70)

        return stats

    finally:
        db.close()


def main():
    """Punto de entrada principal del script"""
    parser = argparse.ArgumentParser(
        description="Procesar facturas pendientes con workflow automático"
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=100,
        help="Máximo de facturas a procesar (default: 100)"
    )
    parser.add_argument(
        "--silencioso",
        action="store_true",
        help="No mostrar mensajes detallados"
    )

    args = parser.parse_args()

    try:
        stats = procesar_facturas_pendientes(
            limite=args.limite,
            verbose=not args.silencioso
        )

        # Código de salida basado en resultados
        if stats["total_procesadas"] == 0:
            sys.exit(0)  # Sin facturas pendientes
        elif len(stats["errores"]) > 0:
            sys.exit(1)  # Hubo errores
        else:
            sys.exit(0)  # Todo OK

    except KeyboardInterrupt:
        print("\n Procesamiento interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
