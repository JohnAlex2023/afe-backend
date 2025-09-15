# Duplicación y utilidades de listas de facturas
from typing import List, Dict

def deduplicate_facturas(facturas: List[Dict]) -> List[Dict]:
    seen = set()
    deduped = []
    for factura in facturas:
        key = (factura['numero'], factura['proveedor_id'])
        if key not in seen:
            seen.add(key)
            deduped.append(factura)
    return deduped
