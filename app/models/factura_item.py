# app/models/factura_item.py
"""
Modelo para items/líneas individuales de facturas.

Este modelo almacena cada línea de la factura extraída del XML (<InvoiceLine>),
permitiendo comparaciones granulares y análisis detallado de servicios/productos.

Autor: Sistema AFE
Fecha: 2025-10-09
"""

from sqlalchemy import Column, BigInteger, String, Numeric, Integer, ForeignKey, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class FacturaItem(Base):
    """
    Items/líneas individuales de una factura (del XML <InvoiceLine>).

    Relación: Factura (1) -> FacturaItem (N)

    Ejemplo de XML parseado:
    <InvoiceLine>
        <ID>1</ID>
        <InvoicedQuantity>10</InvoicedQuantity>
        <LineExtensionAmount>1000000</LineExtensionAmount>
        <Item>
            <Description>Servicio de hosting AWS mensual</Description>
            <SellersItemIdentification>
                <ID>PROD-AWS-001</ID>
            </SellersItemIdentification>
        </Item>
        <Price>
            <PriceAmount>100000</PriceAmount>
        </Price>
    </InvoiceLine>
    """
    __tablename__ = "factura_items"

    # ============================================================================
    # IDENTIFICACIÓN
    # ============================================================================
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID único del item"
    )

    factura_id = Column(
        BigInteger,
        ForeignKey("facturas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK a la factura padre"
    )

    numero_linea = Column(
        Integer,
        nullable=False,
        comment="Número de línea en el XML (orden)"
    )

    # ============================================================================
    # DESCRIPCIÓN Y CÓDIGOS
    # ============================================================================
    descripcion = Column(
        String(2000),
        nullable=False,
        comment="Descripción completa del item (del XML)"
    )

    codigo_producto = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Código del producto del proveedor"
    )

    codigo_estandar = Column(
        String(100),
        nullable=True,
        comment="Código estándar: EAN, UNSPSC, etc."
    )

    # ============================================================================
    # CANTIDADES Y UNIDADES
    # ============================================================================
    cantidad = Column(
        Numeric(15, 4),
        nullable=False,
        default=1,
        comment="Cantidad facturada"
    )

    unidad_medida = Column(
        String(50),
        nullable=True,
        server_default="unidad",
        comment="Unidad de medida: unidad, kg, litro, hora, etc."
    )

    # ============================================================================
    # PRECIOS Y TOTALES
    # ============================================================================
    precio_unitario = Column(
        Numeric(15, 4),
        nullable=False,
        comment="Precio unitario del item"
    )

    subtotal = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Subtotal del item (cantidad × precio_unitario - descuentos)"
    )

    total_impuestos = Column(
        Numeric(15, 2),
        nullable=False,
        server_default="0",
        comment="Total de impuestos aplicados al item (IVA, etc.)"
    )

    total = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Total del item (subtotal + impuestos)"
    )

    # Descuentos (opcional)
    descuento_porcentaje = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Porcentaje de descuento aplicado"
    )

    descuento_valor = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Valor del descuento aplicado"
    )

    # ============================================================================
    # NORMALIZACIÓN (Para comparación automática)
    # ============================================================================
    descripcion_normalizada = Column(
        String(500),
        nullable=True,
        index=True,
        comment="Descripción normalizada para matching (lowercase, sin acentos, etc.)"
    )

    item_hash = Column(
        String(32),
        nullable=True,
        index=True,
        comment="Hash MD5 de descripcion_normalizada para comparación rápida"
    )

    # ============================================================================
    # CLASIFICACIÓN (Para análisis)
    # ============================================================================
    categoria = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Categoría del item: software, hardware, servicio, consumible, etc."
    )

    es_recurrente = Column(
        Numeric(1, 0),
        nullable=True,
        server_default="0",
        comment="1 si el item aparece mensualmente, 0 si es esporádico"
    )

    # ============================================================================
    # METADATA
    # ============================================================================
    notas = Column(
        String(1000),
        nullable=True,
        comment="Notas adicionales sobre el item"
    )

    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp de creación"
    )

    # ============================================================================
    # RELATIONSHIPS
    # ============================================================================
    factura = relationship(
        "Factura",
        back_populates="items",
        lazy="joined"
    )

    # ============================================================================
    # CONSTRAINTS E ÍNDICES
    # ============================================================================
    __table_args__ = (
        # Índice compuesto para queries por factura
        Index(
            'idx_factura_item_linea',
            'factura_id',
            'numero_linea',
            unique=True  # No puede haber dos líneas con el mismo número en una factura
        ),

        # Índice para búsqueda por hash
        Index(
            'idx_item_hash_factura',
            'item_hash',
            'factura_id'
        ),

        # Índice para búsqueda por descripción normalizada
        Index(
            'idx_item_descripcion_norm',
            'descripcion_normalizada'
        ),

        # Índice para búsqueda por código de producto
        Index(
            'idx_item_codigo_producto',
            'codigo_producto',
            'factura_id'
        ),

        # Índice para items recurrentes
        Index(
            'idx_item_recurrente_categoria',
            'es_recurrente',
            'categoria'
        ),
    )

    def __repr__(self):
        return (
            f"<FacturaItem("
            f"id={self.id}, "
            f"factura_id={self.factura_id}, "
            f"linea={self.numero_linea}, "
            f"desc='{self.descripcion[:30]}...', "
            f"total={self.total}"
            f")>"
        )
