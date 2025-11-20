# 🏗️ ARQUITECTURA PAGOS - VERSIÓN FINAL (SIMPLIFICADA)

**Versión:** 4.0 - ULTRASIMPLE Y PROFESIONAL
**Fecha:** 20 de Noviembre de 2025
**Estado:** LISTO PARA CODEAR

---

## 📊 TABLAS - SIN REDUNDANCIA

### Tabla: `facturas` (SIN CAMBIOS)
```sql
-- No se agrega NADA a facturas
-- Solo cambiar estado: aprobada → pagada
-- Ya tiene el campo: estado (Enum)
```

### Tabla NUEVA: `pagos_facturas`
```python
class EstadoPago(enum.Enum):
    completado = "completado"
    fallido = "fallido"
    cancelado = "cancelado"

class PagoFactura(Base):
    __tablename__ = "pagos_facturas"

    id = Column(BigInteger, primary_key=True)
    factura_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=False, index=True)

    # Datos esenciales (sin redundancia)
    monto_pagado = Column(Numeric(15, 2, asdecimal=True), nullable=False)
    referencia_pago = Column(String(100), nullable=False, unique=True, index=True)
    metodo_pago = Column(String(50), nullable=True)  # transferencia, cheque
    estado_pago = Column(Enum(EstadoPago), default=EstadoPago.completado, nullable=False)

    # Auditoría esencial
    procesado_por = Column(String(255), nullable=False)  # Email contador
    fecha_pago = Column(DateTime(timezone=True), nullable=False, index=True)

    # Timestamps
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relación
    factura = relationship("Factura", back_populates="pagos")
```

**Eso es todo. 9 campos. Sin redundancia.**

---

## 🔄 SINCRONIZACIÓN - REGLA ÚNICA

```python
# Cuando creas un PagoFactura:

1. Validar: Factura existe y está aprobada
2. Crear: PagoFactura(monto, referencia, procesado_por, fecha_pago)
3. Sincronizar:
   total_pagado = SUM(pagos WHERE estado='completado')

   IF total_pagado >= factura.total_calculado:
       factura.estado = 'pagada'

4. Commit
5. Email al proveedor
```

---

## 📋 CAMBIOS EN FACTURA

```python
# app/models/factura.py

class Factura(Base):
    # ... todos los campos existentes, SIN CAMBIOS ...

    # AGREGAR SOLO ESTO:

    # Relación a pagos (sin campos nuevos)
    pagos = relationship("PagoFactura", back_populates="factura", lazy="selectin")

    # Propiedades calculadas (dinámicas, no almacenadas)
    @property
    def total_pagado(self) -> Decimal:
        """Suma de pagos completados"""
        return sum(
            p.monto_pagado for p in self.pagos
            if p.estado_pago == EstadoPago.completado
        ) or Decimal('0.00')

    @property
    def pendiente_pagar(self) -> Decimal:
        """Total - pagado"""
        return (self.total_calculado - self.total_pagado) or Decimal('0.00')

    @property
    def esta_completamente_pagada(self) -> bool:
        """¿Monto pagado >= monto total?"""
        return self.total_pagado >= (self.total_calculado or Decimal('0.00'))
```

---

## 📡 ENDPOINT - CÓDIGO REAL

```python
# app/api/v1/routers/accounting.py

@router.post(
    "/facturas/{factura_id}/marcar-pagada",
    response_model=FacturaConPagosResponse,
    summary="Registrar pago de factura"
)
async def marcar_factura_pagada(
    factura_id: int,
    request: PagoRequest,
    current_user=Depends(require_role("contador")),
    db: Session = Depends(get_db)
):
    """Registra un pago y sincroniza estado de factura"""

    # Obtener factura
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    # Validar estado
    if factura.estado not in [EstadoFactura.aprobada, EstadoFactura.aprobada_auto]:
        raise HTTPException(status_code=400, detail="Factura no está aprobada")

    # Validar monto
    if request.monto_pagado > factura.pendiente_pagar:
        raise HTTPException(status_code=400, detail="Monto excede pendiente")

    # Validar referencia única
    existe = db.query(PagoFactura).filter(
        PagoFactura.referencia_pago == request.referencia_pago
    ).first()
    if existe:
        raise HTTPException(status_code=409, detail="Referencia duplicada")

    # Crear pago
    pago = PagoFactura(
        factura_id=factura_id,
        monto_pagado=request.monto_pagado,
        referencia_pago=request.referencia_pago,
        metodo_pago=request.metodo_pago,
        estado_pago=EstadoPago.completado,
        procesado_por=current_user.email,
        fecha_pago=datetime.utcnow()
    )
    db.add(pago)
    db.flush()

    # SINCRONIZACIÓN: Cambiar estado si está completamente pagada
    if factura.esta_completamente_pagada:
        factura.estado = EstadoFactura.pagada

    db.commit()

    # Email
    await enviar_email_pago(factura, pago, current_user)

    return factura
```

---

## 📝 SCHEMAS - MINIMALISTAS

```python
# app/schemas/pago.py

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, List

class PagoRequest(BaseModel):
    monto_pagado: Decimal = Field(..., gt=0)
    referencia_pago: str = Field(..., min_length=3, max_length=100)
    metodo_pago: Optional[str] = None

class PagoResponse(BaseModel):
    id: int
    factura_id: int
    monto_pagado: Decimal
    referencia_pago: str
    procesado_por: str
    fecha_pago: datetime

    class Config:
        from_attributes = True

class FacturaConPagosResponse(BaseModel):
    id: int
    numero_factura: str
    estado: str
    total_calculado: Decimal
    total_pagado: Decimal
    pendiente_pagar: Decimal
    pagos: List[PagoResponse]

    class Config:
        from_attributes = True
```

---

## 🗓️ CHECKLIST - SIMPLE Y CLARO

### PASO 1: Modelo (30 min)
- [ ] Crear `app/models/pago_factura.py`
- [ ] Agregar relación a Factura
- [ ] Agregar 3 propiedades calculadas

### PASO 2: Migration (15 min)
- [ ] `alembic revision --autogenerate -m "Add payment system"`
- [ ] `alembic upgrade head`

### PASO 3: Schemas (20 min)
- [ ] Crear `app/schemas/pago.py`

### PASO 4: Endpoint (45 min)
- [ ] POST `/accounting/facturas/{id}/marcar-pagada`
- [ ] Validaciones
- [ ] Sincronización

### PASO 5: Email (20 min)
- [ ] Template `pago_factura_proveedor.html`
- [ ] Integración

### PASO 6: Testing (30 min)
- [ ] Test: pago completo
- [ ] Test: referencia duplicada
- [ ] Test: monto inválido

**TOTAL: 2.5 - 3 horas backend puro**

---

## ✅ DIFERENCIAS (vs versión anterior)

| Lo que ANTES | Lo que AHORA |
|-------------|------------|
| 12 campos en PagoFactura | 9 campos (solo esenciales) |
| `motivo_cancelacion` | ❌ Eliminado (no lo necesitas HOY) |
| `observaciones` | ❌ Eliminado |
| Documentación larga | ✅ Código limpio y simple |
| Mucha redundancia | ✅ Sin redundancia |

---

## 🎯 FLUJO FINAL

```
Usuario: Contador marca factura como pagada

POST /accounting/facturas/123/marcar-pagada
{
  "monto_pagado": 5000,
  "referencia_pago": "CHQ-001",
  "metodo_pago": "cheque"
}

BACKEND:
1. Validar factura existe ✅
2. Validar aprobada ✅
3. Validar monto válido ✅
4. Validar ref única ✅
5. Crear PagoFactura ✅
6. Calcular total_pagado ✅
7. Si >= total → Factura.estado = pagada ✅
8. Enviar email ✅

RESPONSE:
{
  "id": 123,
  "estado": "pagada",
  "total_calculado": 5000,
  "total_pagado": 5000,
  "pendiente_pagar": 0,
  "pagos": [{...}]
}
```

---

## 🚀 LISTO PARA CODEAR

Todo es:
- ✅ Simple (9 campos, 3 propiedades)
- ✅ Profesional (auditoría, sincronización)
- ✅ Sin redundancia
- ✅ Rápido (2.5-3 horas)
- ✅ Escalable

**¿Empezamos?**
