# 🔄 SINCRONIZACIÓN VISUAL - Factura ↔ PagoFactura

---

## 📊 TABLAS Y CAMPOS

### Tabla: `facturas` (SIN CAMBIOS en campos)
```
┌─ facturas ──────────────────────────────┐
│ id: 123                                 │
│ numero_factura: INV-2025-0001          │
│ estado: aprobada → pagada [SYNC]       │
│ total_calculado: $5,000                │
│ fecha_vencimiento: 2025-12-20          │
│ ... (todos los campos existentes)      │
└─────────────────────────────────────────┘
         │
         │ RELACIÓN 1-a-MUCHOS
         │ (una factura, muchos pagos)
         ▼
┌─ pagos_facturas ────────────────────────┐
│ id: 1                                   │
│ factura_id: 123 [FK]                    │
│ monto_pagado: $5,000                   │
│ estado_pago: completado                │
│ referencia_pago: CHEQUE-001 [UNIQUE]   │
│ procesado_por: contador@empresa.com    │
│ fecha_pago: 2025-11-20 14:30:00        │
│ metodo_pago: cheque                    │
│ observaciones: Pago por tesorería      │
│ creado_en: 2025-11-20 14:30:00         │
│ actualizado_en: 2025-11-20 14:30:00    │
└─────────────────────────────────────────┘
```

---

## 🔀 FLUJO DE SINCRONIZACIÓN

### FLUJO 1: Registrar Pago Completo

```
┌─────────────────────────────────────────────────┐
│  CONTADOR MARCA FACTURA COMO PAGADA             │
├─────────────────────────────────────────────────┤
│  POST /accounting/facturas/123/marcar-pagada    │
│  {                                              │
│    "monto_pagado": 5000,                        │
│    "referencia_pago": "CHEQUE-001"              │
│  }                                              │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  BACKEND VALIDA                                 │
├─────────────────────────────────────────────────┤
│ 1. Factura existe? ✅                           │
│ 2. Estado es aprobada? ✅                       │
│ 3. Referencia NO existe? ✅                     │
│ 4. Monto <= pendiente? ✅                       │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  CREAR REGISTRO EN pagos_facturas               │
├─────────────────────────────────────────────────┤
│ INSERT INTO pagos_facturas (                    │
│   factura_id: 123,                              │
│   monto_pagado: 5000,                           │
│   estado_pago: 'completado',                    │
│   referencia_pago: 'CHEQUE-001',               │
│   procesado_por: 'contador@empresa.com',        │
│   fecha_pago: NOW()                             │
│ )                                               │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  CALCULAR ESTADO DE FACTURA                     │
├─────────────────────────────────────────────────┤
│ total_pagado = SUM(pagos completados)           │
│                = $5,000                         │
│                                                 │
│ ¿total_pagado >= total_factura?                 │
│ ¿$5,000 >= $5,000?                              │
│ ✅ SÍ                                            │
│                                                 │
│ → Cambiar Factura.estado = 'pagada'            │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  ENVIAR EMAIL AL PROVEEDOR                      │
├─────────────────────────────────────────────────┤
│ To: proveedor@xyz.com                          │
│ Subject: Pago recibido - INV-2025-0001         │
│ Body: "Hemos procesado el pago de $5,000..."   │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  RETORNAR RESPUESTA                             │
├─────────────────────────────────────────────────┤
│ {                                               │
│   "id": 123,                                    │
│   "estado": "pagada",  ← ACTUALIZADO            │
│   "total_pagado": 5000,                         │
│   "pendiente_pagar": 0,                         │
│   "pagos": [{...}]                              │
│ }                                               │
└─────────────────────────────────────────────────┘
```

---

### FLUJO 2: Registro con Pagos Parciales

```
PAGO 1 (PARCIAL):
─────────────────

Factura: $5,000
     │
     ├─ POST /marcar-pagada { monto: $3,000, ref: TRF-001 }
     │
     ▼
  CREAR PagoFactura #1:
  ├─ monto_pagado: $3,000
  ├─ estado_pago: completado
  └─ referencia: TRF-001
     │
     ▼
  CALCULAR:
  ├─ total_pagado: $3,000
  ├─ pendiente: $2,000
  ├─ ¿$3,000 >= $5,000? NO
  └─ Factura.estado: SIGUE aprobada ✅


PAGO 2 (COMPLETA):
──────────────────

Factura: $5,000 (todavía aprobada)
     │
     ├─ POST /marcar-pagada { monto: $2,000, ref: TRF-002 }
     │
     ▼
  CREAR PagoFactura #2:
  ├─ monto_pagado: $2,000
  ├─ estado_pago: completado
  └─ referencia: TRF-002
     │
     ▼
  CALCULAR:
  ├─ total_pagado: $3,000 + $2,000 = $5,000
  ├─ pendiente: $0
  ├─ ¿$5,000 >= $5,000? SÍ ✅
  └─ Factura.estado: CAMBIAR a pagada ✅
```

---

### FLUJO 3: Revertir un Pago

```
ESTADO ACTUAL:
┌─────────────────────────┐
│ Factura #125: pagada    │
├─────────────────────────┤
│ PagoFactura #1:         │
│ ├─ monto: $5,000        │
│ ├─ estado: completado   │
│ └─ referencia: CHQ-001  │
└─────────────────────────┘

ACCIÓN:
POST /accounting/pagos/1/revertir
{ "motivo": "Cheque rechazado" }

CAMBIOS EN BD:
└─ PagoFactura #1:
   ├─ estado: completado → revertido ✅
   ├─ motivo_cancelacion: "Cheque rechazado"
   └─ actualizado_en: NOW()

SINCRONIZACIÓN:
├─ Recalcular total_pagado
│  = SUM(pagos donde estado='completado')
│  = $0 (porque la única está 'revertida')
│
├─ ¿$0 >= $5,000? NO
│
└─ Factura.estado: pagada → aprobada ✅

RESULTADO FINAL:
┌─────────────────────────┐
│ Factura #125: aprobada  │ ← REVERTIDA
├─────────────────────────┤
│ PagoFactura #1:         │
│ ├─ monto: $5,000        │
│ ├─ estado: revertido    │ ← CAMBIÓ
│ ├─ referencia: CHQ-001  │
│ └─ motivo: Cheque...    │ ← AGREGADO
└─────────────────────────┘
```

---

## 🧮 LÓGICA DE SINCRONIZACIÓN (CÓDIGO)

```python
# Pseudo-código Python

def marcar_factura_pagada(factura_id, monto, referencia):
    """Registra un pago y sincroniza estado de factura"""

    # 1. OBTENER FACTURA
    factura = db.query(Factura).get(factura_id)
    if not factura:
        raise 404("Factura no encontrada")

    # 2. VALIDAR ESTADO
    if factura.estado not in ['aprobada', 'aprobada_auto']:
        raise 400("Factura no está aprobada")

    # 3. VALIDAR MONTO
    if monto > factura.pendiente_pagar:
        raise 400("Monto excede pendiente")

    # 4. VALIDAR REFERENCIA ÚNICA
    existe = db.query(PagoFactura).filter(
        PagoFactura.referencia_pago == referencia
    ).first()
    if existe:
        raise 409("Referencia ya existe")

    # 5. CREAR PAGO
    pago = PagoFactura(
        factura_id=factura_id,
        monto_pagado=monto,
        referencia_pago=referencia,
        estado_pago=EstadoPago.completado,
        procesado_por=current_user.email,
        fecha_pago=datetime.utcnow()
    )
    db.add(pago)
    db.flush()

    # 6. SINCRONIZACIÓN: RECALCULAR ESTADO
    # ====================================
    total_pagado = factura.total_pagado  # Propiedad calculada
    total_factura = factura.total_calculado

    if total_pagado >= total_factura:
        # La factura está completamente pagada
        factura.estado = EstadoFactura.pagada
    else:
        # Aún hay pendiente
        factura.estado = EstadoFactura.aprobada

    db.commit()

    # 7. NOTIFICAR
    await enviar_email_pago(factura, pago)

    return factura


def revertir_pago(pago_id, motivo):
    """Revierte un pago y sincroniza estado"""

    pago = db.query(PagoFactura).get(pago_id)
    if not pago:
        raise 404("Pago no encontrado")

    factura = pago.factura

    # 1. CAMBIAR ESTADO DEL PAGO
    pago.estado_pago = EstadoPago.revertido
    pago.motivo_cancelacion = motivo
    db.add(pago)
    db.flush()

    # 2. SINCRONIZACIÓN: RECALCULAR ESTADO DE FACTURA
    # ===============================================
    total_pagado = factura.total_pagado  # Recalcula excluyendo 'revertido'
    total_factura = factura.total_calculado

    if total_pagado < total_factura and factura.estado == EstadoFactura.pagada:
        # Estaba pagada pero ya no está completamente pagada
        factura.estado = EstadoFactura.aprobada

    db.commit()
    return factura
```

---

## 🎯 PROPIEDADES CALCULADAS (NO almacenadas en BD)

```python
class Factura(Base):

    @property
    def total_pagado(self) -> Decimal:
        """
        Suma de pagos completados.
        Se calcula dinámicamente cada vez.
        """
        return sum(
            p.monto_pagado
            for p in self.pagos
            if p.estado_pago == EstadoPago.completado
        ) or Decimal('0.00')

    @property
    def pendiente_pagar(self) -> Decimal:
        """
        Lo que aún debe pagarse.
        = total - pagado
        """
        return self.total_calculado - self.total_pagado

    @property
    def esta_completamente_pagada(self) -> bool:
        """
        ¿Monto pagado >= Monto total?
        """
        return self.total_pagado >= self.total_calculado

    @property
    def cantidad_pagos(self) -> int:
        """
        Cuántos pagos completados tiene.
        """
        return len([p for p in self.pagos
                   if p.estado_pago == EstadoPago.completado])

    @property
    def ultimo_pago(self):
        """
        El pago más reciente.
        """
        return max(self.pagos, key=lambda p: p.actualizado_en) if self.pagos else None
```

---

## 📊 DIAGRAMA DE DECISIÓN

```
¿Crear PagoFactura?
       │
       ├─ Validar Factura existe?
       │  ├─ NO → Error 404
       │  └─ SÍ → Continuar
       │
       ├─ Validar está aprobada?
       │  ├─ NO → Error 400
       │  └─ SÍ → Continuar
       │
       ├─ Validar referencia única?
       │  ├─ NO → Error 409
       │  └─ SÍ → Continuar
       │
       ├─ Validar monto válido?
       │  ├─ NO → Error 400
       │  └─ SÍ → Continuar
       │
       ▼
   ✅ CREAR PagoFactura
       │
       ├─ INSERT en pagos_facturas
       ├─ FLUSH (obtener ID)
       │
       ▼
   SINCRONIZAR ESTADO
       │
       ├─ Calcular: total_pagado
       │
       ├─ Comparar: ¿total_pagado >= total_factura?
       │
       ├─ SÍ → Factura.estado = 'pagada'
       │
       ├─ NO → Factura.estado = 'aprobada'
       │
       ▼
   COMMIT BD
       │
       ▼
   ENVIAR EMAIL
       │
       ▼
   RETORNAR 200 ✅
```

---

## ✅ CHECKLIST DE SINCRONIZACIÓN

**Garantizar que Factura.estado siempre refleja:**

- [ ] Si tiene pagos completados que suman >= total → `pagada`
- [ ] Si tiene pagos pero no suma total → `aprobada`
- [ ] Si todos los pagos están revertidos → `aprobada`
- [ ] Si se revierte un pago → recalcular estado
- [ ] Si se agrega nuevo pago → recalcular estado
- [ ] Propiedades calculadas actualizadas dinámicamente
- [ ] No hay campos `fecha_pago` o `pagada_por` en Factura
- [ ] Todo está en tabla `pagos_facturas`

---

## 🎓 CONCLUSIÓN

**Sincronización Automática:**

✅ Factura.estado cambia basado en pagos_facturas
✅ Sin campos redundantes en Factura
✅ Cálculos dinámicos con propiedades
✅ Arquitectura 3NF normalizada
✅ Escalable a múltiples pagos
✅ Auditoría completa en pagos_facturas

---

**Ahora sí, ¿empezamos a codear?** 🚀
