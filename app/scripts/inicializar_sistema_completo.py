"""
Script de Inicialización Completa del Sistema AFE.

Ejecutar: python -m app.scripts.inicializar_sistema_completo

Opciones:
    --dry-run: Simula sin hacer cambios
    --presupuesto: Ruta al archivo Excel de presupuesto
    --año: Año fiscal (default: 2025)
    --responsable-id: ID del responsable default (default: 1)
    --skip-vinculacion: No vincular facturas
    --skip-workflow: No activar workflow

Autor: Senior Backend Developer
"""

import sys
import argparse
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.session import SessionLocal
from app.services.inicializacion_sistema import InicializacionSistemaService
import json


def main():
    """Función principal."""
    # Parsear argumentos
    parser = argparse.ArgumentParser(description="Inicialización completa del sistema AFE")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo simulación (no hace cambios reales)'
    )
    parser.add_argument(
        '--presupuesto',
        type=str,
        help='Ruta al archivo Excel de presupuesto',
        default=None
    )
    parser.add_argument(
        '--año',
        type=int,
        help='Año fiscal',
        default=2025
    )
    parser.add_argument(
        '--responsable-id',
        type=int,
        help='ID del responsable por defecto',
        default=1
    )
    parser.add_argument(
        '--skip-vinculacion',
        action='store_true',
        help='No ejecutar vinculación de facturas'
    )
    parser.add_argument(
        '--skip-workflow',
        action='store_true',
        help='No ejecutar workflow de aprobación'
    )

    args = parser.parse_args()

    # Crear sesión de BD
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        print(" INICIALIZACIÓN ENTERPRISE DEL SISTEMA AFE")
        print("=" * 80)
        print(f"Modo: {'DRY RUN (simulación)' if args.dry_run else 'PRODUCCIÓN'}")
        print(f"Año fiscal: {args.año}")
        print(f"Responsable default ID: {args.responsable_id}")
        print(f"Archivo presupuesto: {args.presupuesto or 'No especificado'}")
        print("=" * 80 + "\n")

        # Inicializar servicio
        servicio = InicializacionSistemaService(db)

        # Ejecutar inicialización
        resultado = servicio.inicializar_sistema_completo(
            archivo_presupuesto=args.presupuesto,
            año_fiscal=args.año,
            responsable_default_id=args.responsable_id,
            ejecutar_vinculacion=not args.skip_vinculacion,
            ejecutar_workflow=not args.skip_workflow,
            dry_run=args.dry_run
        )

        # Mostrar resultado
        print("\n" + "=" * 80)
        print(" REPORTE EJECUTIVO")
        print("=" * 80)

        if resultado.get("exito"):
            print(" Status: EXITOSO\n")

            # Estado inicial vs final
            if "estado_inicial" in resultado and "estado_final" in resultado:
                print(" Cambios en el Sistema:")
                print(f"   Líneas de Presupuesto: {resultado['estado_inicial']['lineas_presupuesto']} → {resultado['estado_final']['lineas_presupuesto']}")
                print(f"   Ejecuciones Presupuestales: {resultado['estado_inicial']['ejecuciones_presupuestales']} → {resultado['estado_final']['ejecuciones_presupuestales']}")
                print(f"   Asignaciones NIT: {resultado['estado_inicial']['asignaciones_nit']} → {resultado['estado_final']['asignaciones_nit']}")
                print(f"   Workflows Creados: {resultado['estado_inicial']['workflows_creados']} → {resultado['estado_final']['workflows_creados']}")

            print(f"\n  Duración: {resultado.get('duracion_segundos', 0):.2f} segundos")
            print(f" Pasos completados: {len(resultado.get('pasos_completados', []))}")

            if resultado.get("warnings"):
                print(f"\n  Warnings: {len(resultado['warnings'])}")
                for warning in resultado["warnings"]:
                    print(f"   - {warning}")

        else:
            print(" Status: FALLIDO\n")
            print("Errores:")
            for error in resultado.get("errores", []):
                if isinstance(error, dict):
                    print(f"   - {error.get('mensaje', error)}")
                else:
                    print(f"   - {error}")

        print("=" * 80)

        # Guardar reporte en JSON
        reporte_file = f"reporte_inicializacion_{args.año}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(reporte_file, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, default=str)
        print(f"\n Reporte guardado en: {reporte_file}")

        # Retornar código de salida
        sys.exit(0 if resultado.get("exito") else 1)

    except Exception as e:
        print(f"\n ERROR CRÍTICO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    from datetime import datetime
    main()
