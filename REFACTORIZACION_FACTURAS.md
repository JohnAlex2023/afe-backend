# 🏗️ Refactorización Enterprise: Sistema de Facturas

**Problema**: Tabla `facturas` con 40+ campos mezclando responsabilidades
**Solución**: Separación de concerns en múltiples tablas especializadas

---

## 📐 ARQUITECTURA PROPUESTA (Normalizada)

```
┌─────────────────────────────────────────────────────────────┐
│ FACTURAS (Tabla Principal - Solo Datos Esenciales)         │
│ - Información básica de la factura                          │
│ - Datos DIAN (CUFE, número)                                 │
│ - Montos totales                                             │
│ - Referencias a entidades (proveedor, cliente, responsable) │
│ - Estado actual                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ├──→ factura_items (1:N)
                           │     └─ Items individuales
                           │
                           ├──→ factura_workflow (1:1)
                           │     └─ Aprobación/rechazo
                           │
                           ├──→ factura_automatizacion (1:1)
                           │     └─ Metadata de ML/automatización
                           │
                           ├──→ factura_pagos (1:N)
                           │     └─ Historial de pagos
                           │
                           └──→ factura_metadata (1:1)
                                 └─ Datos técnicos del XML
```

---

## 📋 TABLA 1: `facturas` (Core - Solo Esencial)

```python
class Factura(Base):
    """
    Tabla principal con SOLO datos esenciales de factura.
    Principio: Single Responsibility - Datos base de negocio.
    """
    __tablename__ = "facturas"

    # ========================================
    # IDENTIFICACIÓN
    # ========================================
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    numero_factura = Column(String(50), nullable=False, index=True)
    cufe = Column(String(100), unique=True, nullable=False, index=True)

    # ========================================
    # FECHAS
    # ========================================
    fecha_emision = Column(Date, nullable=False, index=True)
    fecha_vencimiento = Column(Date, nullable=True)

    # ========================================
    # RELACIONES (FKs)
    # ========================================
    proveedor_id = Column(
        BigInteger,
        ForeignKey("proveedores.id"),
        nullable=False,  # Factura SIEMPRE tiene proveedor
        index=True
    )
    cliente_id = Column(
        BigInteger,
        ForeignKey("clientes.id"),
        nullable=True,
        index=True
    )
    responsable_id = Column(
        BigInteger,
        ForeignKey("responsables.id"),
        nullable=True,
        index=True
    )

    # ========================================
    # MONTOS (Resumen)
    # ========================================
    subtotal = Column(Numeric(15, 2), nullable=False)
    total_impuestos = Column(Numeric(15, 2), nullable=False)  # Suma de todos los impuestos
    total = Column(Numeric(15, 2), nullable=False)           # subtotal + impuestos
    moneda = Column(String(10), nullable=False, server_default="COP")

    # ========================================
    # ESTADO
    # ========================================
    estado = Column(
        Enum(EstadoFactura),
        default=EstadoFactura.pendiente,
        nullable=False,
        index=True
    )

    # ========================================
    # CLASIFICACIÓN (para agrupación rápida)
    # ========================================
    # Estos campos PODRÍAN ser calculados, pero los dejamos por performance
    # (evita YEAR(fecha_emision) en WHERE clauses)
    periodo = Column(String(7), nullable=False, index=True)  # YYYY-MM

    # ========================================
    # AUDITORÍA
    # ========================================
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en = Column(DateTime(timezone=True), onupdate=func.now())
    creado_por = Column(String(100), nullable=True)

    # ========================================
    # RELATIONSHIPS
    # ========================================
    proveedor = relationship("Proveedor", back_populates="facturas")
    cliente = relationship("Cliente", back_populates="facturas")
    responsable = relationship("Responsable", back_populates="facturas")

    items = relationship("FacturaItem", back_populates="factura", cascade="all, delete-orphan")
    workflow = relationship("FacturaWorkflow", back_populates="factura", uselist=False, cascade="all, delete-orphan")
    automatizacion = relationship("FacturaAutomatizacion", back_populates="factura", uselist=False, cascade="all, delete-orphan")
    metadata_xml = relationship("FacturaMetadata", back_populates="factura", uselist=False, cascade="all, delete-orphan")
    pagos = relationship("FacturaPago", back_populates="factura", cascade="all, delete-orphan")

    # ========================================
    # CONSTRAINTS
    # ========================================
    __table_args__ = (
        UniqueConstraint("numero_factura", "proveedor_id", name="uix_factura_numero_proveedor"),
        Index("idx_factura_periodo_proveedor", "periodo", "proveedor_id"),
        Index("idx_factura_estado_periodo", "estado", "periodo"),
    )
```

**Campos**: 16 esenciales (vs 40+ actuales)
**Tamaño aprox**: ~200 bytes por registro (vs ~1KB+ actual)

---

## 📋 TABLA 2: `factura_items` (Líneas/Items)

```python
class FacturaItem(Base):
    """Items/líneas individuales de la factura (del XML <InvoiceLine>)"""
    __tablename__ = "factura_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    factura_id = Column(BigInteger, ForeignKey("facturas.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_linea = Column(Integer, nullable=False)

    # Descripción y códigos
    descripcion = Column(String(2000), nullable=False)
    codigo_producto = Column(String(100), nullable=True, index=True)
    codigo_estandar = Column(String(100), nullable=True)  # EAN, UNSPSC

    # Cantidades
    cantidad = Column(Numeric(15, 4), nullable=False, default=1)
    unidad_medida = Column(String(50), nullable=True)

    # Precios
    precio_unitario = Column(Numeric(15, 4), nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False)
    total_impuestos = Column(Numeric(15, 2), nullable=False, default=0)
    total = Column(Numeric(15, 2), nullable=False)

    # Normalización (para matching)
    descripcion_normalizada = Column(String(500), nullable=True, index=True)
    item_hash = Column(String(32), nullable=True, index=True)

    # Relationship
    factura = relationship("Factura", back_populates="items")

    __table_args__ = (
        Index("idx_item_factura_linea", "factura_id", "numero_linea"),
    )
```

---

## 📋 TABLA 3: `factura_workflow` (Aprobación/Rechazo)

```python
class FacturaWorkflow(Base):
    """
    Workflow de aprobación/rechazo de factura.
    Separa la lógica de aprobación del core de la factura.
    """
    __tablename__ = "factura_workflow"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    factura_id = Column(
        BigInteger,
        ForeignKey("facturas.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Aprobación manual
    aprobado_por = Column(String(100), nullable=True)
    fecha_aprobacion = Column(DateTime(timezone=True), nullable=True)
    comentario_aprobacion = Column(String(1000), nullable=True)

    # Rechazo
    rechazado_por = Column(String(100), nullable=True)
    fecha_rechazo = Column(DateTime(timezone=True), nullable=True)
    motivo_rechazo = Column(String(1000), nullable=True)

    # Reasignaciones
    reasignado_a = Column(BigInteger, ForeignKey("responsables.id"), nullable=True)
    fecha_reasignacion = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    factura = relationship("Factura", back_populates="workflow")
```

---

## 📋 TABLA 4: `factura_automatizacion` (ML/Automatización)

```python
class FacturaAutomatizacion(Base):
    """
    Metadata de automatización y ML.
    Separada porque es información técnica, no de negocio.
    """
    __tablename__ = "factura_automatizacion"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    factura_id = Column(
        BigInteger,
        ForeignKey("facturas.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Clasificación automática
    concepto_normalizado = Column(String(200), nullable=True, index=True)
    concepto_hash = Column(String(32), nullable=True, index=True)
    tipo_factura = Column(String(50), nullable=True)  # servicio_recurrente, compra_unica

    # Patrón de recurrencia
    patron_recurrencia = Column(String(50), nullable=True)  # mensual, quincenal
    factura_referencia_id = Column(BigInteger, ForeignKey("facturas.id"), nullable=True)

    # Decisión automática
    aprobada_automaticamente = Column(Boolean, default=False)
    confianza = Column(Numeric(5, 2), nullable=True)  # 0-100%
    motivo_decision = Column(String(500), nullable=True)
    fecha_procesamiento = Column(DateTime(timezone=True), nullable=True)

    # Versión del algoritmo
    version_algoritmo = Column(String(20), nullable=True)

    # Relationship
    factura = relationship("Factura", back_populates="automatizacion")
    factura_referencia = relationship("Factura", foreign_keys=[factura_referencia_id])
```

---

## 📋 TABLA 5: `factura_metadata` (Datos Técnicos del XML)

```python
class FacturaMetadata(Base):
    """
    Metadata técnica extraída del XML.
    Datos que NO son parte del negocio core pero útiles para auditoría.
    """
    __tablename__ = "factura_metadata"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    factura_id = Column(
        BigInteger,
        ForeignKey("facturas.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Referencias externas
    orden_compra = Column(String(100), nullable=True, index=True)
    orden_compra_sap = Column(String(100), nullable=True)
    contrato_numero = Column(String(100), nullable=True)
    remision = Column(String(100), nullable=True)

    # Condiciones de pago
    forma_pago = Column(String(50), nullable=True)  # Contado, Crédito
    dias_credito = Column(Integer, nullable=True)
    medio_pago = Column(String(50), nullable=True)  # Transferencia, Cheque

    # Información DIAN adicional
    qr_code = Column(String(1000), nullable=True)
    tipo_documento_dian = Column(String(10), nullable=True)  # 01=Factura
    ambiente_dian = Column(String(20), nullable=True)  # Producción, Pruebas

    # Datos técnicos
    xml_original_path = Column(String(500), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    procesamiento_info = Column(JSON, nullable=True)  # Info técnica del parser

    # Relationship
    factura = relationship("Factura", back_populates="metadata_xml")
```

---

## 📋 TABLA 6: `factura_pagos` (Historial de Pagos)

```python
class FacturaPago(Base):
    """
    Historial de pagos de la factura.
    Una factura puede tener múltiples pagos parciales.
    """
    __tablename__ = "factura_pagos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    factura_id = Column(
        BigInteger,
        ForeignKey("facturas.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Datos del pago
    fecha_pago = Column(Date, nullable=False)
    monto_pagado = Column(Numeric(15, 2), nullable=False)
    metodo_pago = Column(String(50), nullable=True)  # Transferencia, Cheque
    referencia_pago = Column(String(100), nullable=True)  # Número de comprobante

    # Auditoría
    registrado_por = Column(String(100), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    factura = relationship("Factura", back_populates="pagos")

    __table_args__ = (
        Index("idx_pago_factura_fecha", "factura_id", "fecha_pago"),
    )
```

---

## 📊 COMPARACIÓN: Antes vs Después

### **Tabla `facturas` Actual** ❌
```
- 40+ campos
- ~1 KB por registro
- Mezcla responsabilidades
- JSONs anidados
- Campos redundantes
- Difícil de mantener
```

### **Sistema Propuesto** ✅
```
facturas:              16 campos (~200 bytes)
factura_items:         12 campos (tabla separada)
factura_workflow:       8 campos (tabla separada)
factura_automatizacion: 9 campos (tabla separada)
factura_metadata:      12 campos (tabla separada)
factura_pagos:          7 campos (tabla separada)

Total: 64 campos distribuidos en 6 tablas especializadas
Ventaja: Cada tabla con una responsabilidad clara
```

---

## 🔄 PLAN DE MIGRACIÓN (Sin Downtime)

### **Opción 1: Migración Incremental** (Recomendado)

```python
# Fase 1: Crear nuevas tablas (SIN tocar facturas)
alembic revision -m "add_factura_items"
alembic revision -m "add_factura_workflow"
alembic revision -m "add_factura_automatizacion"
alembic revision -m "add_factura_metadata"
alembic revision -m "add_factura_pagos"

# Fase 2: Migrar datos de facturas → nuevas tablas
# Script de migración que copia datos actuales
python migrate_factura_data.py

# Fase 3: Marcar campos viejos como deprecated
# NO borrarlos aún, solo agregar @deprecated

# Fase 4: Actualizar código para usar nuevas tablas
# Gradualmente reemplazar accesos a campos viejos

# Fase 5: Una vez todo migrado, borrar campos viejos
alembic revision -m "cleanup_factura_deprecated_fields"
```

### **Opción 2: Big Bang Migration** (No recomendado)

Crear todo de una vez. Riesgoso para producción.

---

## ✅ BENEFICIOS DE LA REFACTORIZACIÓN

### **1. Mantenibilidad**
```python
# Antes: Todo mezclado
factura.aprobado_por
factura.confianza_automatica
factura.orden_compra_numero
factura.items_resumen  # JSON feo

# Después: Separación clara
factura.workflow.aprobado_por
factura.automatizacion.confianza
factura.metadata_xml.orden_compra
factura.items  # Relación ORM limpia
```

### **2. Performance**
```python
# Queries más rápidos
# Antes: SELECT * FROM facturas (40 columnas, JOINs pesados)
# Después: SELECT * FROM facturas (16 columnas)

# Solo cargas tablas relacionadas cuando las necesitas
factura = db.query(Factura).get(id)  # Ligero
workflow = factura.workflow  # Lazy load solo si se necesita
```

### **3. Escalabilidad**
```
# Tabla facturas: 100,000 registros × 200 bytes = 20 MB
# vs
# Tabla facturas actual: 100,000 × 1KB = 100 MB

# Índices más pequeños = queries más rápidos
```

### **4. Testabilidad**
```python
# Puedes testear cada concern independientemente
test_factura_core()
test_factura_workflow()
test_factura_automatizacion()
```

### **5. Extensibilidad**
```
# Agregar nueva funcionalidad = nueva tabla
# Sin tocar tabla core
```

---

## 🎯 RECOMENDACIÓN FINAL

**Como arquitecto senior**:

1. ✅ **SÍ, refactorizar tabla `facturas`**
2. ✅ **Separar en 6 tablas especializadas**
3. ✅ **Usar migración incremental** (sin downtime)
4. ✅ **Implementar factura_items primero** (más crítico)
5. ✅ **Después workflow, automatización, metadata**

**Prioridad**:
1. 🔴 `factura_items` (CRÍTICO - para comparaciones)
2. 🟡 `factura_workflow` (IMPORTANTE - separar lógica de aprobación)
3. 🟡 `factura_automatizacion` (IMPORTANTE - limpiar facturas)
4. 🟢 `factura_metadata` (DESEABLE - mejorar trazabilidad)
5. 🟢 `factura_pagos` (DESEABLE - historial completo)

---

**¿Procedemos con la refactorización?**
Empezamos por crear `factura_items` y limpiar la tabla principal.
