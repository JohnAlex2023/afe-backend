#!/usr/bin/env python
"""
Script de validación: Verifica que el dashboard muestre responsables correctamente
Prueba que la sincronización de responsables está funcionando en el API
"""

import sys
from pathlib import Path

backend_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, backend_dir)

import os
os.chdir(backend_dir)

from app.db.session import SessionLocal
from app.models.factura import Factura
from app.schemas.factura import FacturaRead
from datetime import datetime

def validar_dashboard_responsables():
    """Valida que los responsables se mapeen correctamente en el schema"""
    db = SessionLocal()

    print("\n" + "="*80)
    print("VALIDACION: Dashboard - Mapeo de Responsables")
    print("="*80)
    print(f"Fecha/Hora: {datetime.now().isoformat()}\n")

    try:
        # Obtener todas las facturas
        facturas_db = db.query(Factura).limit(10).all()

        print(f"Validando {len(facturas_db)} facturas aleatorias\n")

        errores = []
        validadas = 0

        for factura in facturas_db:
            # Convertir a schema (como lo hace FastAPI)
            schema = FacturaRead.model_validate(factura)

            # Verificaciones
            if factura.responsable_id:
                # Debe tener responsable en schema
                if not schema.responsable:
                    errores.append(
                        f"Factura {factura.numero_factura}: "
                        f"responsable_id={factura.responsable_id} "
                        f"pero schema.responsable=None"
                    )
                elif schema.responsable.id != factura.responsable_id:
                    errores.append(
                        f"Factura {factura.numero_factura}: "
                        f"responsable_id={factura.responsable_id} "
                        f"pero schema.responsable.id={schema.responsable.id}"
                    )
                else:
                    validadas += 1

                # Verificar nombre_responsable
                if not schema.nombre_responsable:
                    errores.append(
                        f"Factura {factura.numero_factura}: "
                        f"nombre_responsable es None"
                    )

            else:
                # Sin responsable en BD
                if schema.responsable:
                    errores.append(
                        f"Factura {factura.numero_factura}: "
                        f"sin responsable_id pero schema.responsable={schema.responsable}"
                    )
                else:
                    validadas += 1

        print(f"Facturas validadas correctamente: {validadas}/{len(facturas_db)}")

        if errores:
            print(f"\nERRORES ENCONTRADOS ({len(errores)}):")
            for err in errores:
                print(f"  - {err}")
            return False

        # Verificar que el JSON tenga el campo responsable
        print(f"\nVerificando serialización JSON\n")

        factura_muestra = facturas_db[0]
        schema_muestra = FacturaRead.model_validate(factura_muestra)
        json_data = schema_muestra.model_dump()

        print(f"Factura: {factura_muestra.numero_factura}")
        print(f"  responsable_id (BD): {factura_muestra.responsable_id}")
        print(f"  schema.responsable: {schema_muestra.responsable}")
        print(f"  JSON['responsable']: {json_data.get('responsable')}")
        print(f"  nombre_responsable: {json_data.get('nombre_responsable')}")

        if json_data.get('responsable'):
            print(f"\n[OK] Campo 'responsable' en JSON")
        else:
            print(f"\n[WARN] Campo 'responsable' es None en JSON")

        print("\n" + "="*80)
        print("VALIDACION COMPLETADA - Sistema funcionando correctamente")
        print("="*80)

        return True

    except Exception as e:
        print(f"\nERROR EN VALIDACION: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = validar_dashboard_responsables()
    sys.exit(0 if success else 1)
