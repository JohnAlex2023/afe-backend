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
from app.services.excel_to_presupuesto import ExcelPresupuestoImporter
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

        # PASO 1: Importar desde Excel
        print("📁 PASO 1: Importando datos desde Excel...")
        print("-" * 80)

        # AJUSTA ESTA RUTA A TU ARCHIVO EXCEL
        archivo_excel = r"AVD PPTO TI 2025 - Presentación JZ - OPEX y Menor Cuantia - Copia(TI DSZF).csv"

        # Si el archivo está en otra ubicación, ajusta la ruta completa
        # archivo_excel = r"C:\ruta\completa\al\archivo.csv"

        if not Path(archivo_excel).exists():
            print(f"❌ ERROR: No se encontró el archivo: {archivo_excel}")
            print()
            print("Por favor, ajusta la ruta en el script o copia el archivo a la carpeta raíz del proyecto.")
            return

        # Configuración de mapeo de columnas (ajustar según tu Excel)
        mapeo_columnas = {
            "codigo": "ID",  # Columna con el código de la línea
            "nombre": "Nombre cuenta",  # Columna con el nombre
            "descripcion": "Descripción",
            "centro_costo": "Centro de Costo",
            "subcategoria": "Subcategoría",
            "proveedor_preferido": "Proveedor",
            # Presupuestos mensuales - AJUSTAR SEGÚN LOS NOMBRES EN TU EXCEL
            "presupuesto_ene": "Jan-25",  # O "Ene-25" si está en español
            "presupuesto_feb": "Feb-25",
            "presupuesto_mar": "Mar-25",
            "presupuesto_abr": "Apr-25",  # O "Abr-25" si está en español
            "presupuesto_may": "May-25",
            "presupuesto_jun": "Jun-25",
            "presupuesto_jul": "Jul-25",
            "presupuesto_ago": "Aug-25",  # O "Ago-25" si está en español
            "presupuesto_sep": "Sep-25",
            "presupuesto_oct": "Oct-25",
            "presupuesto_nov": "Nov-25",
            "presupuesto_dic": "Dec-25",  # O "Dic-25" si está en español
        }

        # Obtener un responsable existente (ajustar según tu BD)
        # Aquí debes poner el ID de un responsable válido de tu tabla responsables
        responsable_id = 1  # CAMBIAR POR UN ID VÁLIDO

        importer = ExcelPresupuestoImporter(db)
        resultado = importer.importar_desde_excel(
            file_path=archivo_excel,
            año_fiscal=2025,
            responsable_id=responsable_id,
            categoria="TI",
            creado_por="ADMIN",
            hoja=0,  # Primera hoja
            fila_inicio=7,  # Ajustar según donde empiecen tus datos
            mapeo_columnas=mapeo_columnas
        )

        if resultado.get("exito"):
            print(f"✅ Importación exitosa!")
            print(f"   Líneas creadas: {resultado['lineas_creadas']}")
            print(f"   Líneas actualizadas: {resultado['lineas_actualizadas']}")
            print(f"   Total procesadas: {resultado['total_procesadas']}")

            if resultado.get("errores"):
                print(f"   ⚠️  Errores: {len(resultado['errores'])}")
                for error in resultado['errores'][:5]:  # Mostrar solo primeros 5
                    print(f"      - {error}")

            if resultado.get("advertencias"):
                print(f"   ⚠️  Advertencias: {len(resultado['advertencias'])}")
                for adv in resultado['advertencias'][:5]:
                    print(f"      - {adv}")
        else:
            print(f"❌ Error en importación: {resultado.get('error')}")
            return

        print()

        # PASO 2: Aprobar líneas
        print("✅ PASO 2: Aprobando líneas presupuestales...")
        print("-" * 80)

        lineas_importadas = resultado.get('ids_creados', []) + resultado.get('ids_actualizados', [])
        lineas_aprobadas = 0

        for linea_id in lineas_importadas:
            linea = crud_presupuesto.aprobar_linea_presupuesto(
                db=db,
                linea_id=linea_id,
                aprobador="admin@afe.com",
                observaciones="Aprobación automática - Importación inicial"
            )
            if linea:
                lineas_aprobadas += 1

        print(f"✅ {lineas_aprobadas} líneas aprobadas")
        print()

        # PASO 3: Activar líneas
        print("🚀 PASO 3: Activando líneas presupuestales...")
        print("-" * 80)

        lineas_activadas = 0
        for linea_id in lineas_importadas:
            linea = crud_presupuesto.activar_linea_presupuesto(db, linea_id)
            if linea:
                lineas_activadas += 1

        print(f"✅ {lineas_activadas} líneas activadas")
        print()

        # PASO 4: Vincular facturas automáticamente
        print("🔗 PASO 4: Vinculando facturas existentes con presupuesto...")
        print("-" * 80)

        vinculador = AutoVinculador(db)
        resultado_vinculacion = vinculador.vincular_facturas_pendientes(
            año_fiscal=2025,
            umbral_confianza=80,  # 80% de confianza mínima
            limite=None  # Todas las facturas
        )

        print(f"✅ Vinculación completada:")
        print(f"   Total procesadas: {resultado_vinculacion['total_procesadas']}")
        print(f"   Vinculadas exitosamente: {resultado_vinculacion['total_vinculadas']}")
        print(f"   Sin vincular: {resultado_vinculacion['total_sin_vincular']}")

        if resultado_vinculacion['errores']:
            print(f"   ⚠️  Errores: {len(resultado_vinculacion['errores'])}")

        print()

        # PASO 5: Mostrar dashboard
        print("📊 PASO 5: Dashboard de presupuesto...")
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
        print("✅ IMPORTACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 80)
        print()
        print("Próximos pasos:")
        print("1. Revisar las vinculaciones automáticas en: GET /api/v1/presupuesto/ejecuciones")
        print("2. Ver dashboard ejecutivo en: GET /api/v1/presupuesto/dashboard/2025")
        print("3. Aprobar ejecuciones pendientes según niveles de autorización")
        print()

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    importar_presupuesto()
