# 🏗️ ARQUITECTURA DEFINITIVA - SISTEMA DE PAGOS CON TABLA PAGO_FACTURA

**Versión:** 3.0 - TABLA SEPARADA
**Fecha:** 20 de Noviembre de 2025
**Estado:** ARQUITECTURA FINAL APROBADA

---

## 📊 MODELO DE DATOS

### TABLA 1: facturas (CAMBIOS MÍNIMOS)

```sql
-- Tabla EXISTENTE - SOLO agregar relación (sin campos nuevos)
ALTER TABLE facturas ADD CONSTRAINT fk_facturas_pagos
  FOREIGN KEY (id) REFERENCES pagos_facturas(factura_id);
```

**Campos SIN CAMBIOS:**
- id (PK)
- numero_factura
- fecha_emision
- proveedor_id
- subtotal
- iva
- total_a_pagar
- estado (aprobada, pagada, rechazada, devuelta, etc)
- fecha_vencimiento
- responsable_id
- accion_por
- creado_en
- actualizado_en
- ... (todos los demás)

**Cambio en MODELO (Python):**
```python
# app/models/factura.py

class Factura(Base):
    # ... todos los campos existentes sin cambios ...

    # AGREGAR ESTA RELACIÓN
    pagos = relationship(
        "PagoFactura",
        back_populates="factura",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # PROPIEDADES CALCULADAS (sin almacenar en BD)
    @property
    def total_pagado(self) -> Decimal:
        """Suma de todos los pagos completados"""
        if not self.pagos:
            return Decimal('0.00')
        return sum(
            (p.monto_pagado or Decimal('0'))
            for p in self.pagos
            if p.estado_pago == EstadoPago.completado
        ) or Decimal('0.00')

    @property
    def pendiente_pagar(self) -> Decimal:
        """Total factura - total pagado"""
        total = self.total_calculado or Decimal('0.00')
        pagado = self.total_pagado
        return total - pagado

    @property
    def esta_completamente_pagada(self) -> bool:
        """¿El monto pagado >= monto total?"""
        return self.total_pagado >= (self.total_calculado or Decimal('0.00'))

    @property
    def tiene_pagos_pendientes(self) -> bool:
        """¿Tiene pagos en estado 'fallido'?"""
        return any(p.estado_pago == EstadoPago.fallido for p in self.pagos)

    @property
    def primer_pago(self):
        """El primer pago registrado (más antiguo)"""
        return min(self.pagos, key=lambda p: p.creado_en) if self.pagos else None

    @property
    def ultimo_pago(self):
        """El último pago registrado (más reciente)"""
        return max(self.pagos, key=lambda p: p.actualizado_en) if self.pagos else None

    @property
    def cantidad_pagos(self) -> int:
        """Cuántos registros de pago tiene"""
        return len([p for p in self.pagos if p.estado_pago == EstadoPago.completado])
```

---

### TABLA 2: pagos_facturas (NUEVA - TABLA SEPARADA)

```python
# app/models/pago_factura.py - ARCHIVO NUEVO

from sqlalchemy import Column, BigInteger, Numeric, String, Enum, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum
from decimal import Decimal

class EstadoPago(enum.Enum):
    """Estados de un pago"""
    completado = "completado"      # Pago exitoso (dinero recibido)
    fallido = "fallido"            # Pago rechazado/no procesado
    cancelado = "cancelado"        # Pago anulado por usuario
    revertido = "revertido"        # Pago revocado (deben dinero)


class PagoFactura(Base):
    __tablename__ = "pagos_facturas"

    # ==================== PRIMARY KEY ====================
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # ==================== FOREIGN KEYS ====================
    factura_id = Column(
        BigInteger,
        ForeignKey("facturas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Referencia a factura pagada"
    )

    # ==================== DATOS DEL PAGO ====================
    monto_pagado = Column(
        Numeric(15, 2, asdecimal=True),
        nullable=False,
        comment="Cantidad pagada en este registro"
    )

    estado_pago = Column(
        Enum(EstadoPago),
        default=EstadoPago.completado,
        nullable=False,
        index=True,
        comment="Estado: completado, fallido, cancelado, revertido"
    )

    # ==================== AUDITORÍA Y REFERENCIA ====================
    referencia_pago = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Referencia única: CHEQUE-12345, TRF-ABC123, etc"
    )

    metodo_pago = Column(
        String(50),
        nullable=True,
        comment="Método: transferencia, cheque, efectivo, tarjeta, etc"
    )

    procesado_por = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Email del contador que registró el pago"
    )

    fecha_pago = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Fecha/hora cuando se efectuó el pago"
    )

    observaciones = Column(
        String(500),
        nullable=True,
        comment="Notas del contador (ej: 'Cheque de XYZ Bank', 'Pago parcial')"
    )

    # ==================== MOTIVO DE REVERSIÓN (OPCIONAL) ====================
    motivo_cancelacion = Column(
        String(500),
        nullable=True,
        comment="Si estado=cancelado/revertido: por qué"
    )

    # ==================== TIMESTAMPS ====================
    creado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Fecha de creación del registro"
    )

    actualizado_en = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Última actualización"
    )

    # ==================== RELACIÓN ====================
    factura = relationship("Factura", back_populates="pagos")

    # ==================== CONSTRAINTS ====================
    __table_args__ = (
        UniqueConstraint("referencia_pago", name="uix_referencia_pago_unique"),
    )
```

---

## 🔄 SINCRONIZACIÓN: Factura ↔ PagoFactura

### REGLA 1: Cambio de Estado en Factura (AUTOMÁTICO)

**TRIGGER DE LÓGICA: En el endpoint**

```python
# Después de crear un PagoFactura:

pago = PagoFactura(
    factura_id=factura_id,
    monto_pagado=request.monto_pagado,
    referencia_pago=request.referencia_pago,
    estado_pago=EstadoPago.completado,
    procesado_por=current_user.email,
    fecha_pago=datetime.utcnow()
)

db.add(pago)
db.flush()

# SINCRONIZACIÓN: Calcular si debe cambiar estado
if factura.esta_completamente_pagada:
    factura.estado = EstadoFactura.pagada
    db.add(factura)

db.commit()
```

### REGLA 2: Cuándo Cambiar Estado a PAGADA

**Factura.estado = "pagada" ↔ Cuando:**
```
SUM(pagos.monto_pagado WHERE estado_pago='completado') >= Factura.total_calculado
```

**En código:**
```python
@property
def debe_cambiar_a_pagada(self) -> bool:
    """¿Debe esta factura cambiar a estado pagada?"""
    return self.esta_completamente_pagada and self.estado != EstadoFactura.pagada

def sincronizar_estado(self):
    """Sincroniza estado basado en pagos registrados"""
    if self.debe_cambiar_a_pagada:
        self.estado = EstadoFactura.pagada
        return True
    return False
```

### REGLA 3: Reversión Automática de Estado

**Si cancelas un pago y queda "aprobada" nuevamente:**

```python
# Al reversar un pago:

pago.estado_pago = EstadoPago.revertido
pago.motivo_cancelacion = request.motivo

# Recalcular estado de factura
if not factura.esta_completamente_pagada and factura.estado == EstadoFactura.pagada:
    factura.estado = EstadoFactura.aprobada

db.commit()
```

---

## 📋 CAMPOS RESUMEN

### Tabla `pagos_facturas` - Campos Principales

| Campo | Tipo | Req | Unique | Index | Propósito |
|-------|------|-----|--------|-------|-----------|
| `id` | BigInt | ✓ | ✓ PK | ✓ | Identificador único |
| `factura_id` | BigInt FK | ✓ | | ✓ | Link a factura |
| `monto_pagado` | Decimal(15,2) | ✓ | | | Cantidad pagada |
| `estado_pago` | Enum | ✓ | | ✓ | completado/fallido/etc |
| `referencia_pago` | String(100) | ✓ | ✓ | ✓ | CHEQUE-123 (evitar duplicados) |
| `metodo_pago` | String(50) | | | | transferencia/cheque/efectivo |
| `procesado_por` | String(255) | ✓ | | ✓ | Email contador (auditoría) |
| `fecha_pago` | DateTime | ✓ | | ✓ | Cuándo se pagó |
| `observaciones` | String(500) | | | | Notas libres |
| `motivo_cancelacion` | String(500) | | | | Por qué se canceló |
| `creado_en` | DateTime | ✓ | | ✓ | Cuándo se registró |
| `actualizado_en` | DateTime | ✓ | | | Última actualización |

---

## 🎯 FLUJO DE SINCRONIZACIÓN

### Escenario 1: Factura de $5,000 con 1 pago completo

```
ANTES:
┌─ Factura #123
│  ├─ estado: aprobada
│  ├─ total: $5,000
│  └─ pagos: []

ACCCIÓN:
POST /facturas/123/marcar-pagada
{
  "monto_pagado": 5000,
  "referencia_pago": "CHEQUE-001"
}

DESPUÉS:
┌─ Factura #123
│  ├─ estado: pagada ← CAMBIÓ AUTOMÁTICAMENTE
│  ├─ total: $5,000
│  └─ pagos: [
│      {
│        id: 1,
│        monto_pagado: $5,000,
│        estado_pago: completado,
│        referencia_pago: CHEQUE-001,
│        procesado_por: contador@empresa.com,
│        fecha_pago: 2025-11-20 14:30:00
│      }
│    ]

CÁLCULO:
total_pagado = $5,000
pendiente_pagar = $0
esta_completamente_pagada = TRUE → estado = pagada ✅
```

---

### Escenario 2: Factura de $5,000 con 2 pagos parciales

```
ANTES:
┌─ Factura #124
│  ├─ estado: aprobada
│  ├─ total: $5,000
│  └─ pagos: []

ACCCIÓN 1:
POST /facturas/124/marcar-pagada
{ "monto_pagado": 3000, "referencia_pago": "TRF-001" }

DESPUÉS PAGO 1:
┌─ Factura #124
│  ├─ estado: aprobada ← SIGUE IGUAL
│  ├─ total: $5,000
│  ├─ total_pagado: $3,000
│  ├─ pendiente_pagar: $2,000
│  └─ pagos: [
│      {
│        id: 1,
│        monto_pagado: $3,000,
│        referencia_pago: TRF-001,
│        estado_pago: completado
│      }
│    ]

CÁLCULO:
$3,000 < $5,000 → NO cambiar estado, sigue aprobada ✅

ACCCIÓN 2:
POST /facturas/124/marcar-pagada
{ "monto_pagado": 2000, "referencia_pago": "TRF-002" }

DESPUÉS PAGO 2:
┌─ Factura #124
│  ├─ estado: pagada ← CAMBIÓ AUTOMÁTICAMENTE
│  ├─ total: $5,000
│  ├─ total_pagado: $5,000
│  ├─ pendiente_pagar: $0
│  └─ pagos: [
│      {
│        id: 1,
│        monto_pagado: $3,000,
│        referencia_pago: TRF-001,
│        estado_pago: completado
│      },
│      {
│        id: 2,
│        monto_pagado: $2,000,
│        referencia_pago: TRF-002,
│        estado_pago: completado
│      }
│    ]

CÁLCULO:
$5,000 >= $5,000 → Cambiar estado a pagada ✅
```

---

### Escenario 3: Reversión de Pago

```
ANTES (Estado: pagada con 1 pago):
┌─ Factura #125
│  ├─ estado: pagada
│  ├─ total: $5,000
│  ├─ total_pagado: $5,000
│  └─ pagos: [
│      {
│        id: 1,
│        estado_pago: completado,
│        monto_pagado: $5,000
│      }
│    ]

ACCCIÓN:
POST /facturas/125/pagos/1/revertir
{ "motivo": "Pago duplicado, transferencia rechazada" }

DESPUÉS:
┌─ Factura #125
│  ├─ estado: aprobada ← REVERTIÓ AUTOMÁTICAMENTE
│  ├─ total: $5,000
│  ├─ total_pagado: $0
│  └─ pagos: [
│      {
│        id: 1,
│        estado_pago: revertido ← CAMBIÓ
│        monto_pagado: $5,000,
│        motivo_cancelacion: "Pago duplicado, transferencia rechazada"
│      }
│    ]

CÁLCULO:
SUM(pagos completados) = $0 < $5,000 → Revertir a aprobada ✅
```

---

## 📡 ENDPOINTS

### Endpoint 1: Marcar Factura como Pagada

```python
POST /accounting/facturas/{factura_id}/marcar-pagada

Request:
{
  "monto_pagado": 5000,
  "referencia_pago": "CHEQUE-001",
  "metodo_pago": "cheque",
  "observaciones": "Pago por tesorería"
}

Response (200):
{
  "id": 123,
  "numero_factura": "INV-2025-0001",
  "estado": "pagada",
  "total_calculado": 5000,
  "total_pagado": 5000,
  "pendiente_pagar": 0,
  "pagos": [
    {
      "id": 1,
      "monto_pagado": 5000,
      "estado_pago": "completado",
      "referencia_pago": "CHEQUE-001",
      "procesado_por": "contador@empresa.com",
      "fecha_pago": "2025-11-20T14:30:00Z"
    }
  ]
}

Errores:
- 400: Monto > pendiente_pagar
- 400: Factura no aprobada
- 409: Referencia duplicada
- 404: Factura no encontrada
```

### Endpoint 2: Listar Pagos de Factura

```python
GET /accounting/facturas/{factura_id}/pagos

Response (200):
{
  "factura_id": 123,
  "total_pagado": 5000,
  "pendiente_pagar": 0,
  "pagos": [
    {
      "id": 1,
      "monto_pagado": 5000,
      "estado_pago": "completado",
      "referencia_pago": "CHEQUE-001",
      "procesado_por": "contador@empresa.com",
      "fecha_pago": "2025-11-20T14:30:00Z"
    }
  ]
}
```

### Endpoint 3: Revertir Pago (FASE 2)

```python
POST /accounting/pagos/{pago_id}/revertir

Request:
{
  "motivo": "Transferencia rechazada"
}

Response (200):
{
  "id": 1,
  "estado_pago": "revertido",
  "motivo_cancelacion": "Transferencia rechazada",
  "factura": {
    "id": 123,
    "estado": "aprobada"  # Cambió automáticamente
  }
}
```

---

## 📝 SCHEMAS

```python
# app/schemas/pago.py

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class PagoRequest(BaseModel):
    """Request para registrar un pago"""
    monto_pagado: Decimal = Field(..., gt=0, decimal_places=2)
    referencia_pago: str = Field(..., min_length=3, max_length=100)
    metodo_pago: Optional[str] = Field(None, max_length=50)
    observaciones: Optional[str] = Field(None, max_length=500)

class PagoResponse(BaseModel):
    """Response: datos de un pago"""
    id: int
    factura_id: int
    monto_pagado: Decimal
    estado_pago: str
    referencia_pago: str
    metodo_pago: Optional[str]
    procesado_por: str
    fecha_pago: datetime
    observaciones: Optional[str]

    class Config:
        from_attributes = True

class FacturaConPagosResponse(BaseModel):
    """Response: factura con histórico de pagos"""
    id: int
    numero_factura: str
    estado: str
    total_calculado: Decimal
    total_pagado: Decimal
    pendiente_pagar: Decimal
    cantidad_pagos: int
    pagos: List[PagoResponse]

    class Config:
        from_attributes = True
```

---

## 🗓️ IMPLEMENTACIÓN

### FASE 1: Base de Datos (45 min)

- [ ] Crear `app/models/pago_factura.py`
- [ ] Agregar relación en `Factura`
- [ ] Generar migration: `alembic revision --autogenerate -m "Add payment system"`
- [ ] Aplicar migration: `alembic upgrade head`

### FASE 2: Schemas & Validaciones (30 min)

- [ ] Crear `app/schemas/pago.py`
- [ ] Validadores de Pydantic

### FASE 3: Endpoint Principal (1 hora)

- [ ] POST `/accounting/facturas/{id}/marcar-pagada`
- [ ] Validaciones
- [ ] Sincronización de estado
- [ ] Email al proveedor

### FASE 4: Endpoints Secundarios (30 min)

- [ ] GET `/accounting/facturas/{id}/pagos`
- [ ] Filtros en GET `/facturas`

### FASE 5: Email (30 min)

- [ ] Template `pago_factura_proveedor.html`
- [ ] Integración con endpoint

**TOTAL: 3.5 - 4 horas backend**

---

## ✅ CONCLUSIÓN

**Tabla PagoFactura con Sincronización Automática:**

✅ Tabla separada (arquitectura correcta)
✅ Propiedades calculadas (sin almacenar)
✅ Sincronización automática de estado
✅ Escalable a pagos parciales
✅ Auditoría completa
✅ Mismo tiempo de implementación

---

**¿Comenzamos a implementar?**
