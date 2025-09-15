import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Generator
from contextlib import contextmanager

# Ajustar ruta del extractor
sys.path.append(str(Path(__file__).resolve().parents[2] / "INVOICE_EXTRACTOR" / "src"))

from utils.deduplication import deduplicate_facturas
from app.models import Factura
from app.config import SessionLocal
from sqlalchemy.orm import Session

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Maneja la sesión de base de datos con commit/rollback automático."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Error en sesión DB: %s", e)
        raise
    finally:
        db.close()


def cargar_facturas_desde_directorio(output_dir: str) -> List[Dict]:
    """
    Lee todos los archivos 'consolidado.json' en subdirectorios de output_dir
    y devuelve una lista deduplicada de facturas.
    """
    output_path = Path(output_dir)
    facturas_total: List[Dict] = []

    for nit_dir in output_path.iterdir():
        consolidado_path = nit_dir / "consolidado.json"
        if nit_dir.is_dir() and consolidado_path.exists():
            try:
                with consolidado_path.open(encoding="utf-8") as f:
                    facturas = json.load(f)
                    if isinstance(facturas, list):
                        facturas_total.extend(facturas)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("⚠️ Error leyendo %s: %s", consolidado_path, e)

    return deduplicate_facturas(facturas_total)


def actualizar_o_crear_factura(db: Session, factura_data: Dict) -> None:
    """
    Inserta o actualiza una factura en la base de datos según CUFE o número de factura.
    """
    cufe = factura_data.get("cufe")
    numero = factura_data.get("numero_factura")

    query = None
    if cufe:
        query = db.query(Factura).filter_by(cufe=cufe).first()
    elif numero:
        query = db.query(Factura).filter_by(numero_factura=numero).first()

    campos = {
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

    if query:
        for campo, valor in campos.items():
            setattr(query, campo, valor)
        logger.debug("Factura actualizada: %s", query.id)
    else:
        nueva_factura = Factura(**campos, cufe=cufe, numero_factura=numero)
        db.add(nueva_factura)
        logger.debug("Factura creada: %s", numero or cufe)


def importar_facturas_desde_json(output_dir: str = "../INVOICE_EXTRACTOR/output") -> None:
    """
    Importa facturas desde archivos JSON y las guarda/actualiza en la base de datos.
    """
    facturas_total = cargar_facturas_desde_directorio(output_dir)
    if not facturas_total:
        logger.info("No se encontraron facturas para importar en %s", output_dir)
        return

    with get_db_session() as db:
        for factura_data in facturas_total:
            actualizar_o_crear_factura(db, factura_data)

    logger.info("✅ %d facturas procesadas", len(facturas_total))
