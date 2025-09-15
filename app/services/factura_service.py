from typing import List, Dict
from app.models.factura import Factura
from sqlalchemy.orm import Session

# Ejemplo de lógica de negocio: deduplicación de facturas

def deduplicate_facturas(facturas: List[Dict]) -> List[Dict]:
    seen = set()
    deduped = []
    for factura in facturas:
        key = (factura['numero'], factura['proveedor_id'])
        if key not in seen:
            seen.add(key)
            deduped.append(factura)
    return deduped

# Ejemplo de lógica de negocio: cargar facturas desde directorio (stub)
def cargar_facturas_desde_directorio(output_dir: str) -> List[Dict]:
    # Implementar lógica real de carga y parseo de archivos
    return []
