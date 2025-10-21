"""
Script para importar el presupuesto 2025 desde Excel a la base de datos.

Este script:
1. Lee el archivo Excel de presupuesto TI 2025
2. Crea las líneas presupuestales en la BD
3. Aprueba y activa las líneas automáticamente
4. Vincula facturas existentes con las líneas de presupuesto

Uso:
    python -m app.scripts.importar_presupuesto_2025
"""

import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db.session import get_db
from app.core.database import engine
from app.services.auto_vinculacion import AutoVinculador
from app.crud import presupuesto as crud_presupuesto


def importar_presupuesto():
    """
    Importa el presupuesto desde Excel y configura el sistema.
    """
    # Crear sesión de BD
    db = next(get_db())

    try:
        print("=" * 80)
        print("IMPORTACIÓN DE PRESUPUESTO 2025 - SISTEMA ENTERPRISE")
        print("=" * 80)
        print()

        # NOTA: El servicio de importación de Excel ha sido deprecado.
        # Usa la API REST para crear líneas de presupuesto manualmente
        # o migra los datos mediante scripts SQL directos.

        print("  Este script está deprecado.")
        print("El servicio ExcelPresupuestoImporter ha sido eliminado.")
        print()
        print("Para importar presupuesto, usa una de estas alternativas:")
        print("1. API REST: POST /api/v1/presupuesto/lineas")
        print("2. Script SQL directo para migración de datos")
        print("3. Interfaz de administración web")
        print()
        print("Continuando solo con vinculación de facturas existentes...")
        print()

        # PASO 1: Vincular facturas automáticamente
        print("🔗 PASO 1: Vinculando facturas existentes con presupuesto...")
        print("-" * 80)

        vinculador = AutoVinculador(db)
        resultado_vinculacion = vinculador.vincular_facturas_pendientes(
            año_fiscal=2025,
            umbral_confianza=80,  # 80% de confianza mínima
            limite=None  # Todas las facturas
        )

        print(f"  Vinculación completada:")
        print(f"   Total procesadas: {resultado_vinculacion['total_procesadas']}")
        print(f"   Vinculadas exitosamente: {resultado_vinculacion['total_vinculadas']}")
        print(f"   Sin vincular: {resultado_vinculacion['total_sin_vincular']}")

        if resultado_vinculacion['errores']:
            print(f"     Errores: {len(resultado_vinculacion['errores'])}")

        print()

        # PASO 2: Mostrar dashboard
        print("PASO 2: Dashboard de presupuesto...")
        print("-" * 80)

        dashboard = crud_presupuesto.get_dashboard_presupuesto(db, año_fiscal=2025)

        print(f"Año Fiscal: {dashboard['año_fiscal']}")
        print(f"Total líneas: {dashboard['total_lineas']}")
        print(f"Presupuesto total: ${dashboard['presupuesto_total']:,.2f}")
        print(f"Ejecutado total: ${dashboard['ejecutado_total']:,.2f}")
        print(f"Saldo disponible: ${dashboard['saldo_total']:,.2f}")
        print(f"% Ejecución global: {dashboard['porcentaje_ejecucion_global']:.2f}%")
        print()
        print("Líneas por estado:")
        for estado, cantidad in dashboard['lineas_por_estado'].items():
            print(f"   {estado}: {cantidad}")
        print()
        print(f"Líneas en riesgo (>{80}%): {dashboard['total_lineas_en_riesgo']}")

        print()
        print("=" * 80)
        print("  IMPORTACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 80)
        print()
        print("Próximos pasos:")
        print("1. Revisar las vinculaciones automáticas en: GET /api/v1/presupuesto/ejecuciones")
        print("2. Ver dashboard ejecutivo en: GET /api/v1/presupuesto/dashboard/2025")
        print("3. Aprobar ejecuciones pendientes según niveles de autorización")
        print()

    except Exception as e:
        print(f" ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    importar_presupuesto()
