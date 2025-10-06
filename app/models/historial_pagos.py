# app/models/historial_pagos.py
from sqlalchemy import Column, BigInteger, String, Numeric, Integer, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class TipoPatron(enum.Enum):
    """
    Clasificación de patrones según el PDF del proyecto:
    - TIPO_A: Valores fijos predecibles (misma cantidad mensual)
    - TIPO_B: Valores fluctuantes predecibles (dentro de rangos conocidos)
    - TIPO_C: Valores excepcionales (nuevos proveedores, montos atípicos)
    """
    TIPO_A = "TIPO_A"  # Fijo - CV < 5%
    TIPO_B = "TIPO_B"  # Fluctuante predecible - CV < 30%
    TIPO_C = "TIPO_C"  # Excepcional - CV > 30% o sin historial

class HistorialPagos(Base):
    """
    Modelo para almacenar análisis histórico de pagos por proveedor y concepto.
    Usado para generar recomendaciones inteligentes en el workflow de aprobación.
    """
    __tablename__ = "historial_pagos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Identificación del patrón
    proveedor_id = Column(BigInteger, ForeignKey("proveedores.id"), nullable=False, index=True)
    concepto_normalizado = Column(String(200), nullable=False, index=True,
                                 comment="Concepto normalizado para matching")
    concepto_hash = Column(String(32), nullable=False, index=True,
                          comment="Hash MD5 del concepto para búsqueda rápida")

    # Clasificación del patrón
    tipo_patron = Column(Enum(TipoPatron), nullable=False, index=True,
                        comment="Clasificación: TIPO_A (fijo), TIPO_B (fluctuante), TIPO_C (excepcional)")

    # Estadísticas de pagos históricos (últimos 12 meses)
    pagos_analizados = Column(Integer, nullable=False, default=0,
                             comment="Cantidad de pagos en el análisis")
    meses_con_pagos = Column(Integer, nullable=False, default=0,
                            comment="Cantidad de meses diferentes con pagos")

    # Análisis estadístico
    monto_promedio = Column(Numeric(15, 2), nullable=False,
                          comment="Promedio de montos pagados")
    monto_minimo = Column(Numeric(15, 2), nullable=False,
                         comment="Monto mínimo histórico")
    monto_maximo = Column(Numeric(15, 2), nullable=False,
                         comment="Monto máximo histórico")
    desviacion_estandar = Column(Numeric(15, 2), nullable=False,
                                comment="Desviación estándar de los montos")
    coeficiente_variacion = Column(Numeric(5, 2), nullable=False,
                                  comment="CV = (desv_std / promedio) * 100")

    # Rango esperado para Tipo B
    rango_inferior = Column(Numeric(15, 2), nullable=True,
                          comment="Límite inferior esperado (promedio - 2*desv)")
    rango_superior = Column(Numeric(15, 2), nullable=True,
                          comment="Límite superior esperado (promedio + 2*desv)")

    # Patrón de recurrencia
    frecuencia_detectada = Column(String(50), nullable=True,
                                 comment="mensual, quincenal, trimestral, etc.")
    ultimo_pago_fecha = Column(DateTime(timezone=True), nullable=True,
                              comment="Fecha del último pago registrado")
    ultimo_pago_monto = Column(Numeric(15, 2), nullable=True,
                              comment="Monto del último pago")

    # Datos históricos detallados (para análisis)
    pagos_detalle = Column(JSON, nullable=True,
                          comment="Array con últimos 12 meses: [{periodo, monto, factura_id}]")

    # Metadata del análisis
    fecha_analisis = Column(DateTime(timezone=True), server_default=func.now(),
                          comment="Cuándo se realizó este análisis")
    version_algoritmo = Column(String(20), nullable=False, server_default="1.0",
                              comment="Versión del algoritmo de análisis")

    # Recomendación automática
    puede_aprobar_auto = Column(Integer, nullable=False, default=0,
                               comment="1 si cumple criterios para aprobación automática")
    umbral_alerta = Column(Numeric(5, 2), nullable=True,
                          comment="Porcentaje de desviación para generar alerta")

    # Auditoría
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    proveedor = relationship("Proveedor", backref="patrones_historicos", lazy="joined")
