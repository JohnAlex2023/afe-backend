#app/crud/factura.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, func, desc

from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.models.cliente import Cliente


# -----------------------------------------------------
# Obtener factura por ID
# -----------------------------------------------------
def get_factura(db: Session, factura_id: int) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.id == factura_id).first()


# -----------------------------------------------------
# Listar facturas (con filtros opcionales)
# -----------------------------------------------------
def list_facturas(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
) -> List[Factura]:
    """
    Lista facturas con orden cronológico empresarial por defecto:
    Año DESC → Mes DESC → Fecha DESC (más recientes primero)

    Usa índice: idx_facturas_orden_cronologico para performance óptima
    """
    query = db.query(Factura)

    if nit:
        # Hacemos JOIN con Proveedor y filtramos por NIT
        query = query.join(Proveedor).filter(Proveedor.nit == nit)

    if numero_factura:
        query = query.filter(Factura.numero_factura == numero_factura)

    # Orden cronológico empresarial: más recientes primero
    return query.order_by(
        desc(Factura.año_factura),
        desc(Factura.mes_factura),
        desc(Factura.fecha_emision),
        desc(Factura.id)
    ).offset(skip).limit(limit).all()


# -----------------------------------------------------
# Buscar por CUFE
# -----------------------------------------------------
def find_by_cufe(db: Session, cufe: str) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.cufe == cufe).first()


# -----------------------------------------------------
# Buscar por número de factura
# -----------------------------------------------------
def get_factura_by_numero(db: Session, numero_factura: str) -> Optional[Factura]:
    return db.query(Factura).filter(Factura.numero_factura == numero_factura).first()


# -----------------------------------------------------
# Buscar por número de factura y proveedor
# -----------------------------------------------------
def find_by_numero_proveedor(db: Session, numero: str, proveedor_id: int) -> Optional[Factura]:
    return (
        db.query(Factura)
        .filter(
            and_(
                Factura.numero_factura == numero,
                Factura.proveedor_id == proveedor_id
            )
        )
        .first()
    )


# -----------------------------------------------------
# Crear factura
# -----------------------------------------------------
def create_factura(db: Session, data: dict) -> Factura:
    obj = Factura(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# -----------------------------------------------------
# Actualizar factura
# -----------------------------------------------------
def update_factura(db: Session, factura: Factura, fields: dict) -> Factura:
    for k, v in fields.items():
        setattr(factura, k, v)
    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura


# ✨ FUNCIONES PARA AUTOMATIZACIÓN DE FACTURAS RECURRENTES ✨

# -----------------------------------------------------
# Buscar facturas por concepto normalizado y proveedor
# -----------------------------------------------------
def find_facturas_by_concepto_proveedor(
    db: Session,
    proveedor_id: int,
    concepto_normalizado: str,
    limit: int = 12
) -> List[Factura]:
    """
    Busca facturas históricas del mismo proveedor con concepto similar
    para detectar patrones de recurrencia.

    Orden cronológico: más recientes primero
    Usa índice: idx_facturas_proveedor_cronologico
    """
    return (
        db.query(Factura)
        .filter(
            and_(
                Factura.proveedor_id == proveedor_id,
                Factura.concepto_normalizado == concepto_normalizado
            )
        )
        .order_by(
            desc(Factura.año_factura),
            desc(Factura.mes_factura),
            desc(Factura.fecha_emision)
        )
        .limit(limit)
        .all()
    )


# -----------------------------------------------------
# Buscar facturas por hash de concepto
# -----------------------------------------------------
def find_facturas_by_concepto_hash(
    db: Session, 
    concepto_hash: str,
    proveedor_id: Optional[int] = None,
    limit: int = 10
) -> List[Factura]:
    """
    Búsqueda rápida por hash de concepto para matching exacto
    """
    query = db.query(Factura).filter(Factura.concepto_hash == concepto_hash)
    
    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)
    
    return query.order_by(Factura.fecha_emision.desc()).limit(limit).all()


# -----------------------------------------------------
# Buscar facturas por orden de compra
# -----------------------------------------------------
def find_facturas_by_orden_compra(
    db: Session,
    orden_compra_numero: str,
    proveedor_id: Optional[int] = None
) -> List[Factura]:
    """
    Busca facturas con la misma orden de compra para detectar recurrencia
    """
    query = db.query(Factura).filter(Factura.orden_compra_numero == orden_compra_numero)
    
    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)
        
    return query.order_by(Factura.fecha_emision.desc()).all()


# -----------------------------------------------------
# Obtener facturas pendientes para procesamiento automático
# -----------------------------------------------------
def get_facturas_pendientes_procesamiento(db: Session, limit: int = 50) -> List[Factura]:
    """
    Obtiene facturas en estado 'pendiente' que aún no han sido procesadas
    por el sistema de automatización
    """
    return (
        db.query(Factura)
        .filter(
            and_(
                Factura.estado == "pendiente",
                Factura.fecha_procesamiento_auto.is_(None)
            )
        )
        .order_by(Factura.creado_en.asc())  # Procesar las más antiguas primero
        .limit(limit)
        .all()
    )


# -----------------------------------------------------
# Marcar factura como procesada automáticamente
# -----------------------------------------------------
def marcar_como_procesada_automaticamente(
    db: Session,
    factura: Factura,
    decision_data: dict
) -> Factura:
    """
    Actualiza una factura con los resultados del procesamiento automático
    """
    from datetime import datetime
    
    campos_actualizacion = {
        "patron_recurrencia": decision_data.get("patron_recurrencia"),
        "confianza_automatica": decision_data.get("confianza"),
        "factura_referencia_id": decision_data.get("factura_referencia_id"),
        "motivo_decision": decision_data.get("motivo_decision"),
        "procesamiento_info": decision_data.get("procesamiento_info", {}),
        "fecha_procesamiento_auto": datetime.utcnow(),
        "version_algoritmo": decision_data.get("version_algoritmo", "1.0")
    }
    
    # Solo actualizar estado si se recomienda aprobación automática
    if decision_data.get("estado_sugerido") == "aprobada_auto":
        campos_actualizacion["estado"] = "aprobada_auto"
        campos_actualizacion["aprobada_automaticamente"] = True
    elif decision_data.get("estado_sugerido") == "en_revision":
        campos_actualizacion["estado"] = "en_revision"
    
    return update_factura(db, factura, campos_actualizacion)


# -----------------------------------------------------
# Obtener facturas procesadas automáticamente
# -----------------------------------------------------
def get_facturas_procesadas_automaticamente(
    db: Session,
    fecha_desde: Optional[object] = None,
    estado: Optional[str] = None,
    proveedor_id: Optional[int] = None,
    limit: int = 100
) -> List[Factura]:
    """
    Obtiene facturas que han sido procesadas por el sistema automático
    """
    from datetime import datetime
    
    query = db.query(Factura).filter(
        Factura.fecha_procesamiento_auto.isnot(None)
    )
    
    if fecha_desde:
        query = query.filter(Factura.fecha_procesamiento_auto >= fecha_desde)
    
    if estado:
        query = query.filter(Factura.estado == estado)
        
    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)
    
    return (
        query
        .order_by(Factura.fecha_procesamiento_auto.desc())
        .limit(limit)
        .all()
    )


# -----------------------------------------------------
# Obtener facturas por proveedor y rango de fechas
# -----------------------------------------------------
def get_facturas_by_proveedor_fecha(
    db: Session,
    proveedor_id: int,
    fecha_desde: object,
    fecha_hasta: Optional[object] = None,
    limit: int = 200
) -> List[Factura]:
    """
    Obtiene facturas de un proveedor específico en un rango de fechas
    """
    from datetime import datetime
    
    query = db.query(Factura).filter(
        and_(
            Factura.proveedor_id == proveedor_id,
            Factura.fecha_emision >= fecha_desde
        )
    )
    
    if fecha_hasta:
        query = query.filter(Factura.fecha_emision <= fecha_hasta)
    
    return (
        query
        .order_by(Factura.fecha_emision.desc())
        .limit(limit)
        .all()
    )


# ✨ FUNCIONES PARA CLASIFICACIÓN POR PERÍODOS MENSUALES ✨

# -----------------------------------------------------
# Obtener resumen de facturas agrupadas por mes
# -----------------------------------------------------
def get_facturas_resumen_por_mes(
    db: Session,
    año: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene un resumen de facturas agrupadas por mes/año con totales.
    Optimizado con índices en periodo_factura.

    Returns:
        Lista de diccionarios con: periodo, año, mes, total_facturas, monto_total
    """
    query = db.query(
        Factura.periodo_factura,
        Factura.año_factura,
        Factura.mes_factura,
        func.count(Factura.id).label('total_facturas'),
        func.sum(Factura.total).label('monto_total'),
        func.sum(Factura.subtotal).label('subtotal_total'),
        func.sum(Factura.iva).label('iva_total')
    ).filter(Factura.periodo_factura.isnot(None))

    if año:
        query = query.filter(Factura.año_factura == año)

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    if estado:
        query = query.filter(Factura.estado == estado)

    result = query.group_by(
        Factura.periodo_factura,
        Factura.año_factura,
        Factura.mes_factura
    ).order_by(desc(Factura.periodo_factura)).all()

    return [
        {
            "periodo": row.periodo_factura,
            "año": row.año_factura,
            "mes": row.mes_factura,
            "total_facturas": row.total_facturas,
            "monto_total": float(row.monto_total) if row.monto_total else 0.0,
            "subtotal_total": float(row.subtotal_total) if row.subtotal_total else 0.0,
            "iva_total": float(row.iva_total) if row.iva_total else 0.0
        }
        for row in result
    ]


# -----------------------------------------------------
# Obtener facturas de un período específico
# -----------------------------------------------------
def get_facturas_por_periodo(
    db: Session,
    periodo: str,  # formato: "YYYY-MM"
    skip: int = 0,
    limit: int = 100,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None
) -> List[Factura]:
    """
    Obtiene facturas de un período específico (mes/año).
    Usa índice en periodo_factura para búsqueda rápida.

    Args:
        periodo: Período en formato "YYYY-MM" (ej: "2025-07")
    """
    query = db.query(Factura).filter(Factura.periodo_factura == periodo)

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    if estado:
        query = query.filter(Factura.estado == estado)

    return query.order_by(Factura.fecha_emision.desc()).offset(skip).limit(limit).all()


# -----------------------------------------------------
# Contar facturas por período
# -----------------------------------------------------
def count_facturas_por_periodo(
    db: Session,
    periodo: str,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None
) -> int:
    """
    Cuenta facturas de un período específico.
    """
    query = db.query(func.count(Factura.id)).filter(Factura.periodo_factura == periodo)

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    if estado:
        query = query.filter(Factura.estado == estado)

    return query.scalar()


# -----------------------------------------------------
# Obtener estadísticas por período
# -----------------------------------------------------
def get_estadisticas_periodo(
    db: Session,
    periodo: str,
    proveedor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Obtiene estadísticas detalladas de un período específico.
    """
    query = db.query(Factura).filter(Factura.periodo_factura == periodo)

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    # Estadísticas por estado
    stats_by_estado = db.query(
        Factura.estado,
        func.count(Factura.id).label('cantidad'),
        func.sum(Factura.total).label('monto')
    ).filter(Factura.periodo_factura == periodo)

    if proveedor_id:
        stats_by_estado = stats_by_estado.filter(Factura.proveedor_id == proveedor_id)

    stats_by_estado = stats_by_estado.group_by(Factura.estado).all()

    # Totales generales
    totales = db.query(
        func.count(Factura.id).label('total_facturas'),
        func.sum(Factura.total).label('monto_total'),
        func.sum(Factura.subtotal).label('subtotal'),
        func.sum(Factura.iva).label('iva'),
        func.avg(Factura.total).label('promedio')
    ).filter(Factura.periodo_factura == periodo)

    if proveedor_id:
        totales = totales.filter(Factura.proveedor_id == proveedor_id)

    totales = totales.first()

    return {
        "periodo": periodo,
        "total_facturas": totales.total_facturas or 0,
        "monto_total": float(totales.monto_total) if totales.monto_total else 0.0,
        "subtotal": float(totales.subtotal) if totales.subtotal else 0.0,
        "iva": float(totales.iva) if totales.iva else 0.0,
        "promedio": float(totales.promedio) if totales.promedio else 0.0,
        "por_estado": [
            {
                "estado": row.estado.value if hasattr(row.estado, 'value') else row.estado,
                "cantidad": row.cantidad,
                "monto": float(row.monto) if row.monto else 0.0
            }
            for row in stats_by_estado
        ]
    }


# -----------------------------------------------------
# Obtener años disponibles
# -----------------------------------------------------
def get_años_disponibles(db: Session) -> List[int]:
    """
    Obtiene lista de años que tienen facturas registradas.
    """
    result = db.query(Factura.año_factura).filter(
        Factura.año_factura.isnot(None)
    ).distinct().order_by(desc(Factura.año_factura)).all()

    return [row.año_factura for row in result]


# -----------------------------------------------------
# Obtener jerarquía año → mes → facturas
# -----------------------------------------------------
def get_jerarquia_facturas(
    db: Session,
    año: Optional[int] = None,
    mes: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit_por_mes: int = 100
) -> Dict[str, Any]:
    """
    Retorna facturas organizadas jerárquicamente: Año → Mes → Facturas

    Estructura de respuesta:
    {
        "2025": {
            "10": {
                "total_facturas": 4,
                "monto_total": 12500.00,
                "facturas": [...]
            },
            "09": {...}
        },
        "2024": {...}
    }

    Optimizado con índices: idx_facturas_orden_cronologico, idx_facturas_año_mes_estado
    """
    from collections import defaultdict

    query = db.query(Factura).filter(Factura.periodo_factura.isnot(None))

    # Filtros opcionales
    if año:
        query = query.filter(Factura.año_factura == año)

    if mes:
        query = query.filter(Factura.mes_factura == mes)

    if proveedor_id:
        query = query.filter(Factura.proveedor_id == proveedor_id)

    if estado:
        query = query.filter(Factura.estado == estado)

    # Ordenar cronológicamente: más recientes primero
    facturas = query.order_by(
        desc(Factura.año_factura),
        desc(Factura.mes_factura),
        desc(Factura.fecha_emision),
        desc(Factura.id)
    ).all()

    # Construir jerarquía
    jerarquia = defaultdict(lambda: defaultdict(lambda: {
        "total_facturas": 0,
        "monto_total": 0.0,
        "subtotal": 0.0,
        "iva": 0.0,
        "facturas": []
    }))

    for factura in facturas:
        año_key = str(factura.año_factura)
        mes_key = str(factura.mes_factura).zfill(2)  # "01", "02", etc.

        mes_data = jerarquia[año_key][mes_key]

        # Agregar a contadores
        mes_data["total_facturas"] += 1
        mes_data["monto_total"] += float(factura.total or 0)
        mes_data["subtotal"] += float(factura.subtotal or 0)
        mes_data["iva"] += float(factura.iva or 0)

        # Agregar factura (limitado por mes para performance)
        if len(mes_data["facturas"]) < limit_por_mes:
            mes_data["facturas"].append({
                "id": factura.id,
                "numero_factura": factura.numero_factura,
                "fecha_emision": factura.fecha_emision.isoformat() if factura.fecha_emision else None,
                "total": float(factura.total or 0),
                "estado": factura.estado.value if hasattr(factura.estado, 'value') else factura.estado,
                "proveedor_id": factura.proveedor_id,
                "cufe": factura.cufe
            })

    # Convertir defaultdict a dict normal para JSON
    return {año: dict(meses) for año, meses in jerarquia.items()}
