# 🛠️ GUÍA DE IMPLEMENTACIÓN: SISTEMA DE PAGOS DE FACTURAS
## Paso a Paso para Desarrollo

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### PASO 1: Crear Modelo de Pago (30 minutos)
- [ ] Crear `app/models/pago_factura.py`
- [ ] Definir enums `EstadoPago`, `MetodoPago`
- [ ] Crear clase `PagoFactura`
- [ ] Agregar relación a `Factura`
- [ ] Crear migration Alembic

### PASO 2: Actualizar Modelo Factura (15 minutos)
- [ ] Agregar campo `fecha_pago` a Factura
- [ ] Agregar relación `pagos: Relationship`
- [ ] Agregar propiedades calculadas
- [ ] Crear migration Alembic

### PASO 3: Crear Schema de Validación (20 minutos)
- [ ] Crear `app/schemas/pago.py`
- [ ] Definir `PagoRequest`, `PagoResponse`

### PASO 4: Crear Endpoint (1 hora)
- [ ] Agregar POST `/accounting/facturas/{id}/pagar`
- [ ] Agregar GET `/accounting/pagos/historial`
- [ ] Agregar DELETE `/accounting/pagos/{id}/cancelar`

### PASO 5: Testing (1 hora)
- [ ] Tests unitarios para validaciones
- [ ] Tests de integración para endpoints

### PASO 6: Frontend (2-3 horas)
- [ ] Modal de pago en factura aprobada
- [ ] Filtro paid/unpaid en dashboard
- [ ] Historial de pagos

**TIEMPO TOTAL ESTIMADO: 5-6 horas**

---

## 💻 CÓDIGO LISTO PARA COPIAR

### PASO 1: Crear Modelo PagoFactura

**Archivo:** `app/models/pago_factura.py`

```python
"""
Modelo de transacciones de pago de facturas.

Permite registrar y auditar todos los pagos realizados.
Una factura puede tener múltiples registros de pago si hay pagos parciales.
"""

from sqlalchemy import (
    Column, BigInteger, String, Numeric, ForeignKey, DateTime,
    Enum, Text, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum
from datetime import datetime


class EstadoPago(enum.Enum):
    """Estados de un pago de factura."""
    en_proceso = "en_proceso"      # Pago iniciado, no confirmado
    completado = "completado"       # Pago confirmado y validado
    fallido = "fallido"            # Pago fue rechazado o cancelado
    revertido = "revertido"        # Pago fue revertido/reembolsado


class MetodoPago(enum.Enum):
    """Métodos de pago disponibles."""
    transferencia = "transferencia"  # Transferencia bancaria
    cheque = "cheque"               # Cheque
    efectivo = "efectivo"           # Efectivo
    tarjeta = "tarjeta"             # Tarjeta de crédito
    otro = "otro"                   # Otro método


class PagoFactura(Base):
    """
    Transacciones de pago de facturas.

    Una factura aprobada → pagada genera un registro aquí.
    Permite pagos parciales (múltiples registros por factura).
    """

    __tablename__ = "pagos_facturas"

    # ==================== PRIMARY KEY ====================
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="ID único del pago"
    )

    # ==================== RELACIÓN A FACTURA ====================
    factura_id = Column(
        BigInteger,
        ForeignKey("facturas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Factura que está siendo pagada"
    )

    # ==================== DATOS DEL PAGO ====================
    numero_pago = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Identificador único del pago (referencia banco, cheque, etc)"
    )

    monto_pagado = Column(
        Numeric(15, 2, asdecimal=True),
        nullable=False,
        comment="Cantidad pagada (puede ser parcial)"
    )

    metodo_pago = Column(
        Enum(MetodoPago),
        nullable=False,
        default=MetodoPago.transferencia,
        comment="Método: transferencia, cheque, efectivo, etc"
    )

    estado_pago = Column(
        Enum(EstadoPago),
        nullable=False,
        default=EstadoPago.completado,
        index=True,
        comment="Estado del pago: en_proceso, completado, fallido, revertido"
    )

    # ==================== DETALLES DEL PAGO ====================
    fecha_pago = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="CRÍTICO: Cuándo se ejecutó el pago"
    )

    referencia_externa = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Referencia del banco (ID transacción, número cheque, etc)"
    )

    observaciones = Column(
        Text,
        nullable=True,
        comment="Notas adicionales del contador"
    )

    # ==================== AUDITORÍA ====================
    procesado_por = Column(
        String(255),
        nullable=False,
        comment="Usuario que registró el pago (contador)"
    )

    fecha_procesamiento = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="AUDIT: Cuándo se registró en el sistema"
    )

    # ==================== REVERSIÓN (para cancelaciones) ====================
    revertido_por = Column(
        String(255),
        nullable=True,
        comment="Usuario que revirtió el pago (si aplica)"
    )

    fecha_reversion = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Cuándo se revirtió el pago"
    )

    motivo_reversion = Column(
        Text,
        nullable=True,
        comment="Razón de la reversión"
    )

    # ==================== TIMESTAMPS ====================
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    actualizado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # ==================== RELACIONES ====================
    factura = relationship(
        "Factura",
        back_populates="pagos",
        lazy="joined",
        foreign_keys=[factura_id]
    )

    # ==================== ÍNDICES COMPUESTOS ====================
    __table_args__ = (
        Index('idx_factura_fecha_pago', 'factura_id', 'fecha_pago'),
        Index('idx_estado_fecha', 'estado_pago', 'fecha_pago'),
        Index('idx_procesado_por_fecha', 'procesado_por', 'fecha_procesamiento'),
    )

    # ==================== MÉTODOS ====================

    def __repr__(self) -> str:
        return (
            f"<PagoFactura(id={self.id}, factura_id={self.factura_id}, "
            f"monto=${self.monto_pagado}, estado={self.estado_pago.value})>"
        )

    @property
    def es_completado(self) -> bool:
        """Indica si el pago fue completado exitosamente."""
        return self.estado_pago == EstadoPago.completado

    @property
    def es_revertible(self) -> bool:
        """Indica si el pago puede ser revertido."""
        return self.estado_pago in [EstadoPago.completado, EstadoPago.en_proceso]

    @property
    def dias_desde_pago(self) -> int:
        """Días desde que se realizó el pago."""
        from datetime import datetime
        return (datetime.now(self.fecha_pago.tzinfo) - self.fecha_pago).days
```

---

### PASO 2: Actualizar Modelo Factura

**Archivo:** `app/models/factura.py` - Agregar dentro de la clase `Factura`:

```python
# Agregar en la sección de relaciones (línea ~112):
pagos = relationship(
    "PagoFactura",
    back_populates="factura",
    lazy="selectin",
    cascade="all, delete-orphan",
    foreign_keys="[PagoFactura.factura_id]"
)

# Agregar al final de la clase (antes del __repr__):

@property
def total_pagado(self) -> Decimal:
    """Total pagado en todas las transacciones."""
    from decimal import Decimal
    if not self.pagos:
        return Decimal('0.00')
    return sum(
        p.monto_pagado
        for p in self.pagos
        if p.estado_pago == EstadoPago.completado
    )

@property
def pendiente_pagar(self) -> Decimal:
    """Monto pendiente de pagar."""
    total = self.total_a_pagar or self.total_calculado
    return total - self.total_pagado

@property
def esta_completamente_pagada(self) -> bool:
    """Indica si la factura está completamente pagada."""
    return self.pendiente_pagar <= Decimal('0.01')  # 1 centavo de tolerancia

@property
def fecha_ultimo_pago(self) -> datetime | None:
    """Fecha del último pago registrado."""
    if not self.pagos:
        return None
    pagos_completados = [p for p in self.pagos if p.es_completado]
    if not pagos_completados:
        return None
    return max(p.fecha_pago for p in pagos_completados)

@property
def dias_sin_pagar(self) -> int:
    """Días desde que fue aprobada pero no pagada."""
    if self.estado == EstadoFactura.pagada:
        return 0

    fecha_referencia = None
    if self.fecha_aprobacion_workflow:
        fecha_referencia = self.fecha_aprobacion_workflow
    elif self.fecha_procesamiento_auto:
        fecha_referencia = self.fecha_procesamiento_auto

    if not fecha_referencia:
        return -1

    from datetime import datetime
    return (datetime.now(fecha_referencia.tzinfo) - fecha_referencia).days

@property
def requiere_atencion_pago(self) -> bool:
    """Indica si requiere atención de tesorería."""
    if self.estado != EstadoFactura.aprobada and \
       self.estado != EstadoFactura.aprobada_auto:
        return False

    # Si no está pagada y pasaron más de 5 días
    return self.dias_sin_pagar > 5
```

**IMPORTANTE:** Actualizar los imports en el archivo:
```python
# Agregar en los imports de enums:
from app.models.pago_factura import EstadoPago  # ADD THIS LINE
```

---

### PASO 3: Crear Schema de Validación

**Archivo:** `app/schemas/pago.py`

```python
"""
Schemas de validación para transacciones de pago.
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum


class MetodoPagoEnum(str, Enum):
    transferencia = "transferencia"
    cheque = "cheque"
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    otro = "otro"


class PagoRequest(BaseModel):
    """Request para procesar un pago."""

    monto_pagado: Decimal = Field(
        ...,
        gt=Decimal('0'),
        decimal_places=2,
        description="Monto a pagar (debe ser positivo)"
    )

    metodo_pago: MetodoPagoEnum = Field(
        default=MetodoPagoEnum.transferencia,
        description="Método de pago"
    )

    referencia_externa: Optional[str] = Field(
        None,
        max_length=100,
        description="Ref. externa: ID transferencia, número cheque, etc"
    )

    fecha_pago: datetime = Field(
        ...,
        description="Cuándo se realizó el pago"
    )

    observaciones: Optional[str] = Field(
        None,
        max_length=500,
        description="Notas adicionales"
    )

    @validator('fecha_pago')
    def validar_fecha_pago(cls, v):
        """Valida que la fecha no sea futura."""
        from datetime import datetime as dt
        if v > dt.now(v.tzinfo):
            raise ValueError("La fecha de pago no puede ser futura")
        return v

    class Config:
        schema_extra = {
            "example": {
                "monto_pagado": 1500000.00,
                "metodo_pago": "transferencia",
                "referencia_externa": "TRF20251119001234",
                "fecha_pago": "2025-11-19T14:30:00",
                "observaciones": "Pago cliente XYZ"
            }
        }


class PagoResponse(BaseModel):
    """Response después de procesar un pago."""

    id: int
    factura_id: int
    numero_pago: str
    monto_pagado: Decimal
    metodo_pago: str
    estado_pago: str
    fecha_pago: datetime
    procesado_por: str
    fecha_procesamiento: datetime
    referencia_externa: Optional[str]
    observaciones: Optional[str]

    class Config:
        from_attributes = True


class ReversionPagoRequest(BaseModel):
    """Request para revertir un pago."""

    motivo_reversion: str = Field(
        ...,
        max_length=500,
        description="Razón de la reversión"
    )

    class Config:
        schema_extra = {
            "example": {
                "motivo_reversion": "Pago duplicado - se procesó dos veces"
            }
        }


class HistorialPagosResponse(BaseModel):
    """Response con historial de pagos de una factura."""

    factura_id: int
    total_a_pagar: Decimal
    total_pagado: Decimal
    pendiente_pagar: Decimal
    esta_completamente_pagada: bool
    fecha_ultimo_pago: Optional[datetime]
    pagos: list[PagoResponse]

    class Config:
        from_attributes = True
```

---

### PASO 4: Crear Endpoints de Pago

**Archivo:** `app/api/v1/routers/accounting.py` - Agregar estos endpoints:

```python
# Agregar estos imports al inicio del archivo:
from app.models.pago_factura import PagoFactura, EstadoPago, MetodoPago
from app.schemas.pago import (
    PagoRequest, PagoResponse, ReversionPagoRequest, HistorialPagosResponse
)
from decimal import Decimal

# AGREGAR ESTOS ENDPOINTS al final del archivo:

@router.post(
    "/facturas/{factura_id}/pagar",
    response_model=PagoResponse,
    summary="Procesar pago de factura",
    description="""
    Procesa un pago de factura aprobada.

    **Permisos:** Solo usuarios con rol 'contador'

    **Validaciones:**
    - Factura debe estar en estado 'aprobada' o 'aprobada_auto'
    - El monto a pagar no debe exceder el pendiente
    - La referencia externa debe ser única (no duplicados)

    **Auditoría:**
    - Se registra quién procesó el pago
    - Se guarda referencia bancaria
    - Se crea timestamp de procesamiento
    - Se envía notificación al proveedor

    **Estados:**
    - Si monto pagado == total → factura pasa a 'pagada'
    - Si monto pagado < total → factura pasa a 'pago_parcial'
    """,
    responses={
        200: {"description": "Pago procesado exitosamente"},
        400: {"description": "Validación fallida"},
        403: {"description": "Sin permisos (solo contador)"},
        404: {"description": "Factura no encontrada"},
    }
)
async def procesar_pago_factura(
    factura_id: int,
    request: PagoRequest,
    current_user=Depends(require_role("contador")),
    db: Session = Depends(get_db)
):
    """
    Procesa pago de factura aprobada.
    """

    # ========================================================================
    # OBTENER Y VALIDAR FACTURA
    # ========================================================================

    factura = db.query(Factura).filter(Factura.id == factura_id).first()

    if not factura:
        logger.warning(
            f"Intento de pagar factura inexistente: {factura_id}",
            extra={"factura_id": factura_id, "contador": current_user.usuario}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Factura con ID {factura_id} no encontrada"
        )

    # Validar estado
    if factura.estado not in [EstadoFactura.aprobada, EstadoFactura.aprobada_auto]:
        logger.warning(
            f"Intento de pagar factura en estado inválido: {factura.estado.value}",
            extra={
                "factura_id": factura_id,
                "estado": factura.estado.value,
                "contador": current_user.usuario
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede pagar una factura en estado '{factura.estado.value}'. "
                   f"Solo se pueden pagar facturas aprobadas."
        )

    # Validar monto
    total_pendiente = factura.pendiente_pagar
    if request.monto_pagado > total_pendiente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Monto a pagar (${request.monto_pagado}) excede pendiente (${total_pendiente})"
        )

    # Validar referencia única
    if request.referencia_externa:
        existe_referencia = db.query(PagoFactura).filter(
            PagoFactura.referencia_externa == request.referencia_externa
        ).first()
        if existe_referencia:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referencia '{request.referencia_externa}' ya está registrada"
            )

    # ========================================================================
    # CREAR REGISTRO DE PAGO
    # ========================================================================

    numero_pago = f"PAG-{factura_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    pago = PagoFactura(
        factura_id=factura_id,
        numero_pago=numero_pago,
        monto_pagado=request.monto_pagado,
        metodo_pago=MetodoPago(request.metodo_pago),
        estado_pago=EstadoPago.completado,
        fecha_pago=request.fecha_pago,
        referencia_externa=request.referencia_externa,
        observaciones=request.observaciones,
        procesado_por=current_user.usuario
    )

    db.add(pago)
    db.flush()  # Para obtener el ID

    # ========================================================================
    # ACTUALIZAR ESTADO DE FACTURA
    # ========================================================================

    nuevo_total_pagado = factura.total_pagado + request.monto_pagado

    # Si está completamente pagada
    if nuevo_total_pagado >= factura.total_a_pagar or factura.total_calculado:
        factura.estado = EstadoFactura.pagada
        factura.fecha_pago = request.fecha_pago
        logger.info(
            f"Factura completamente pagada",
            extra={
                "factura_id": factura_id,
                "monto_pagado": float(request.monto_pagado),
                "contador": current_user.usuario
            }
        )
    else:
        logger.info(
            f"Pago parcial registrado",
            extra={
                "factura_id": factura_id,
                "monto_pagado": float(request.monto_pagado),
                "pendiente": float(factura.pendiente_pagar - request.monto_pagado)
            }
        )

    db.commit()
    db.refresh(pago)

    # ========================================================================
    # ENVIAR NOTIFICACIÓN AL PROVEEDOR
    # ========================================================================

    if factura.proveedor and factura.proveedor.contacto_email:
        try:
            email_service = UnifiedEmailService()
            template_service = EmailTemplateService()

            context = {
                "numero_factura": factura.numero_factura,
                "nombre_proveedor": factura.proveedor.razon_social,
                "nit_proveedor": factura.proveedor.nit,
                "monto_factura": f"${factura.total_a_pagar:,.2f} COP",
                "monto_pagado": f"${request.monto_pagado:,.2f} COP",
                "metodo_pago": request.metodo_pago.value,
                "referencia_pago": request.referencia_externa or "N/A",
                "fecha_pago": request.fecha_pago.strftime("%d/%m/%Y %H:%M"),
                "pendiente": f"${factura.pendiente_pagar:,.2f} COP" if factura.pendiente_pagar > 0 else "Completamente pagada"
            }

            html_content = template_service.render_template(
                "pago_factura.html",
                context
            )

            email_service.send_email(
                to_email=factura.proveedor.contacto_email,
                subject=f"✅ Pago Recibido - Factura {factura.numero_factura}",
                body_html=html_content
            )

            logger.info(
                f"Notificación de pago enviada a proveedor",
                extra={
                    "factura_id": factura_id,
                    "proveedor_email": factura.proveedor.contacto_email
                }
            )
        except Exception as e:
            logger.error(
                f"Error enviando notificación de pago: {str(e)}",
                exc_info=True,
                extra={"factura_id": factura_id}
            )

    # ========================================================================
    # RETORNAR RESPUESTA
    # ========================================================================

    return PagoResponse.from_orm(pago)


@router.get(
    "/facturas/{factura_id}/historial-pagos",
    response_model=HistorialPagosResponse,
    summary="Obtener historial de pagos de una factura",
)
async def obtener_historial_pagos(
    factura_id: int,
    current_user=Depends(require_role("contador")),
    db: Session = Depends(get_db)
):
    """Obtiene el historial completo de pagos de una factura."""

    factura = db.query(Factura)\
        .filter(Factura.id == factura_id)\
        .first()

    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )

    pagos = db.query(PagoFactura)\
        .filter(PagoFactura.factura_id == factura_id)\
        .order_by(PagoFactura.fecha_pago.desc())\
        .all()

    return HistorialPagosResponse(
        factura_id=factura.id,
        total_a_pagar=factura.total_a_pagar or factura.total_calculado,
        total_pagado=factura.total_pagado,
        pendiente_pagar=factura.pendiente_pagar,
        esta_completamente_pagada=factura.esta_completamente_pagada,
        fecha_ultimo_pago=factura.fecha_ultimo_pago,
        pagos=[PagoResponse.from_orm(p) for p in pagos]
    )


@router.post(
    "/pagos/{pago_id}/revertir",
    response_model=PagoResponse,
    summary="Revertir un pago registrado",
)
async def revertir_pago(
    pago_id: int,
    request: ReversionPagoRequest,
    current_user=Depends(require_role("contador")),
    db: Session = Depends(get_db)
):
    """
    Revierte un pago registrado.

    **Restricciones:**
    - Solo se pueden revertir pagos completados
    - Requiere motivo
    - La factura vuelve a estado aprobada
    """

    pago = db.query(PagoFactura).filter(PagoFactura.id == pago_id).first()

    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )

    if not pago.es_revertible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede revertir un pago en estado '{pago.estado_pago.value}'"
        )

    # Actualizar pago
    pago.estado_pago = EstadoPago.revertido
    pago.revertido_por = current_user.usuario
    pago.fecha_reversion = datetime.now()
    pago.motivo_reversion = request.motivo_reversion

    # Actualizar factura
    factura = pago.factura
    if factura.esta_completamente_pagada:
        factura.estado = EstadoFactura.aprobada
        factura.fecha_pago = None

    db.commit()
    db.refresh(pago)

    logger.info(
        f"Pago revertido",
        extra={
            "pago_id": pago_id,
            "factura_id": factura.id,
            "revertido_por": current_user.usuario,
            "motivo": request.motivo_reversion
        }
    )

    return PagoResponse.from_orm(pago)
```

---

## 🔄 PRÓXIMOS PASOS

1. **Crear Migration Alembic:**
   ```bash
   cd afe-backend
   alembic revision --autogenerate -m "Add payment system for invoices"
   alembic upgrade head
   ```

2. **Crear Template de Email:**
   `app/templates/emails/pago_factura.html` (similar a los existentes)

3. **Actualizar Frontend:**
   - Agregar botón "Marcar como Pagado" en factura aprobada
   - Crear modal con formulario de pago
   - Agregar filtro "Pagadas/Pendientes" en dashboard

4. **Tests:**
   - Validaciones de monto
   - Auditoría de transacciones
   - Notificaciones por email

---

**¿Necesitas ayuda con algún paso específico?**

