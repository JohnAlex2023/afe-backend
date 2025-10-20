"""
Script para asignar responsables a proveedores desde el CSV.
Asigna alternadamente a alex.taimal y john.taimal
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.responsable import Responsable
from app.models.proveedor import Proveedor
from app.models.responsable_proveedor import ResponsableProveedor


def asignar_responsables_desde_csv():
    """Lee el CSV y asigna responsables a proveedores"""

    db: Session = SessionLocal()

    try:
        # Leer CSV
        csv_path = r"C:\Users\john.taimalp\ODO\Listas Terceros(Hoja1).csv"
        print(f"Leyendo CSV: {csv_path}")

        df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')
        print(f"CSV cargado: {len(df)} filas")

        # Limpiar NITs (solo valores válidos, no '0' ni NaN)
        df['NIT'] = df['NIT'].astype(str).str.strip()
        df = df[df['NIT'].notna()]
        df = df[df['NIT'] != '0']
        df = df[df['NIT'] != 'nan']

        # Obtener NITs únicos con su tercero
        nits_unicos = df[['NIT', 'Tercero']].drop_duplicates(subset=['NIT'])
        print(f"NITs unicos validos: {len(nits_unicos)}")

        # Buscar responsables en BD
        alex = db.query(Responsable).filter(Responsable.usuario == 'alex.taimal').first()
        john = db.query(Responsable).filter(Responsable.usuario == 'john.taimal').first()

        if not alex or not john:
            print("ERROR: No se encontraron los responsables alex.taimal o john.taimal")
            print(f"   Alex encontrado: {alex is not None}")
            print(f"   John encontrado: {john is not None}")
            return

        print(f"Responsables encontrados:")
        print(f"   - Alex (ID: {alex.id}): {alex.nombre}")
        print(f"   - John (ID: {john.id}): {john.nombre}")

        # Contadores
        proveedores_creados = 0
        proveedores_existentes = 0
        asignaciones_creadas = 0
        asignaciones_existentes = 0
        errores = 0

        # Alternar entre alex y john
        responsables = [alex, john]
        indice_responsable = 0

        print("\nProcesando proveedores...")
        print("-" * 80)

        for idx, row in nits_unicos.iterrows():
            nit = str(row['NIT']).strip()
            tercero = str(row['Tercero']).strip() if pd.notna(row['Tercero']) else f"Proveedor NIT {nit}"

            try:
                # Buscar o crear proveedor
                proveedor = db.query(Proveedor).filter(Proveedor.nit == nit).first()

                if not proveedor:
                    # Crear nuevo proveedor
                    proveedor = Proveedor(
                        nit=nit,
                        razon_social=tercero,
                        activo=True
                    )
                    db.add(proveedor)
                    db.flush()  # Para obtener el ID
                    proveedores_creados += 1
                    print(f"Proveedor creado: {nit} - {tercero}")
                else:
                    proveedores_existentes += 1

                # Alternar responsable
                responsable_actual = responsables[indice_responsable]
                indice_responsable = (indice_responsable + 1) % 2

                # Buscar si ya existe la asignación
                asignacion_existente = db.query(ResponsableProveedor).filter(
                    ResponsableProveedor.proveedor_id == proveedor.id,
                    ResponsableProveedor.responsable_id == responsable_actual.id
                ).first()

                if not asignacion_existente:
                    # Crear asignación
                    asignacion = ResponsableProveedor(
                        responsable_id=responsable_actual.id,
                        proveedor_id=proveedor.id,
                        activo=True
                    )
                    db.add(asignacion)
                    asignaciones_creadas += 1

                    if (asignaciones_creadas + asignaciones_existentes) % 10 == 0:
                        print(f"   Procesados {asignaciones_creadas + asignaciones_existentes} proveedores...")
                else:
                    asignaciones_existentes += 1

                # Commit cada 50 registros
                if (proveedores_creados + proveedores_existentes) % 50 == 0:
                    db.commit()

            except Exception as e:
                print(f"ERROR procesando NIT {nit}: {e}")
                errores += 1
                db.rollback()
                continue

        # Commit final
        db.commit()

        print("\n" + "=" * 80)
        print("RESUMEN DE PROCESAMIENTO")
        print("=" * 80)
        print(f"Proveedores creados:        {proveedores_creados}")
        print(f"Proveedores ya existentes:  {proveedores_existentes}")
        print(f"Asignaciones creadas:       {asignaciones_creadas}")
        print(f"Asignaciones ya existentes: {asignaciones_existentes}")
        print(f"Errores:                    {errores}")
        print(f"Total procesado:            {proveedores_creados + proveedores_existentes}")
        print("=" * 80)

        # Verificar distribución
        print("\nDISTRIBUCION DE ASIGNACIONES:")
        alex_count = db.query(ResponsableProveedor).filter(
            ResponsableProveedor.responsable_id == alex.id
        ).count()
        john_count = db.query(ResponsableProveedor).filter(
            ResponsableProveedor.responsable_id == john.id
        ).count()

        print(f"   Alex ({alex.usuario}): {alex_count} proveedores")
        print(f"   John ({john.usuario}): {john_count} proveedores")
        print(f"   TOTAL: {alex_count + john_count} asignaciones")

    except Exception as e:
        print(f"\nERROR CRITICO: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("ASIGNACION DE RESPONSABLES A PROVEEDORES")
    print("=" * 80)
    print()

    try:
        asignar_responsables_desde_csv()
        print("\nProceso completado exitosamente!")
    except Exception as e:
        print(f"\nEl proceso fallo: {e}")
        sys.exit(1)
