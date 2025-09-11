import sys
import os
import json
from contextlib import contextmanager

# Ajustar ruta del extractor
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../INVOICE_EXTRACTOR/src')
    )
)

from utils.deduplication import deduplicate_facturas
from app.models import Factura
from app.config import SessionLocal


@contextmanager
def get_db_session():
    """Context manager para manejar la sesión de base de datos de forma segura."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def cargar_facturas_desde_directorio(output_dir: str) -> list[dict]:
    """
    Lee todos los archivos 'consolidado.json' en output_dir y devuelve una lista de facturas.
    """
    facturas_total = []
    for nit_dir in os.listdir(output_dir):
        nit_path = os.path.join(output_dir, nit_dir)
        consolidado_path = os.path.join(nit_path, 'consolidado.json')
        if os.path.isdir(nit_path) and os.path.exists(consolidado_path):
            try:
                with open(consolidado_path, encoding='utf-8') as f:
                    facturas = json.load(f)
                    if isinstance(facturas, list):
                        facturas_total.extend(facturas)
            except (json.JSONDecodeError, OSError) as e:
                print(f"⚠️ Error leyendo {consolidado_path}: {e}")
    return deduplicate_facturas(facturas_total)


def actualizar_o_crear_factura(db, factura_data: dict):
    """
    Inserta o actualiza una factura en la base de datos según CUFE o número de factura.
    """
    cufe = factura_data.get('cufe')
    numero = factura_data.get('numero_factura')

    factura_existente = None
    if cufe:
        factura_existente = db.query(Factura).filter_by(cufe=cufe).first()
    elif numero:
        factura_existente = db.query(Factura).filter_by(numero_factura=numero).first()

    campos_actualizables = {
        "fecha_emision": factura_data.get("fecha_emision"),
        "fecha_vencimiento": factura_data.get("fecha_vencimiento"),
        "nit_proveedor": factura_data.get("nit_proveedor"),
        "razon_social_proveedor": factura_data.get("razon_social_proveedor"),
        "nit_cliente": factura_data.get("nit_cliente"),
        "razon_social_cliente": factura_data.get("razon_social_cliente"),
        "subtotal": factura_data.get("subtotal"),
        "iva": factura_data.get("iva"),
        "total_a_pagar": factura_data.get("total_a_pagar"),
        "terminos_pago": factura_data.get("terminos_pago"),
    }

    if factura_existente:
        for campo, valor in campos_actualizables.items():
            setattr(factura_existente, campo, valor)
    else:
        nueva_factura = Factura(**campos_actualizables, cufe=cufe, numero_factura=numero)
        db.add(nueva_factura)


def importar_facturas_desde_json(output_dir: str = '../INVOICE_EXTRACTOR/output'):
    """
    Importa facturas desde archivos JSON y las guarda/actualiza en la base de datos.
    """
    facturas_total = cargar_facturas_desde_directorio(output_dir)

    with get_db_session() as db:
        for factura_data in facturas_total:
            actualizar_o_crear_factura(db, factura_data)
