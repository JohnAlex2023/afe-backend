# 📋 RECOMENDACIONES ARQUITECTÓNICAS - AFE BACKEND
## Análisis : Sistema de Gestión de Facturas Electronicas

**Fecha:** 19 de Noviembre de 2025
**Autor:** DESARROLLO 
**Nivel:** Fortune 500

---

## 🎯 ESTADO ACTUAL DEL SISTEMA

### ✅ Lo que está bien implementado
- **Autenticación & Roles**: Microsoft OAuth integrado, roles granulares (admin, responsable, contador, viewer)
- **Workflow de Aprobación**: Aprobación manual y automática con auditoría completa
- **Normalización de Datos**: Modelo 3NF perfecto, sin redundancia
- **Automatización**: Detección de patrones, aprobación inteligente (TIPO_A, TIPO_B, TIPO_C)
- **Email Service**: Unificado (Graph + SMTP fallback)
- **Historial de Pagos**: Ya existe tabla `historial_pagos` con análisis estadístico
- **Audit Log**: Logging completo y profesional

### ⚠️ Áreas de mejora identificadas

---

## 🔴 RECOMENDACIÓN #1: COMPLETAR CICLO DE PAGO
**Prioridad:** CRÍTICA | **Impacto:** Muy Alto | **Esfuerzo:** Medio

### Situación Actual
- Existe estado `pagada` en enum pero **no se usa**
- No hay forma de marcar facturas como pagadas
- Dashboard de contabilidad no tiene filtro paid/unpaid
- Falta auditoría de quién marcó como pagada y cuándo

### Solución Recomendada (TODO List)

#### 1.1 Crear Tabla de Transacciones de Pago
```python
# NEW FILE: app/models/pago_factura.py
class EstadoPago(enum.Enum):
    en_proceso = "en_proceso"      # Pago iniciado
    completado = "completado"       # Pago confirmado
    fallido = "fallido"            # Pago rechazado
    cancelado = "cancelado"        # Pago cancelado
    reembolsado = "reembolsado"    # Reembolso procesado

class PagoFactura(Base):
    __tablename__ = "pagos_facturas"

    id: BigInteger (PK)
    factura_id: BigInteger (FK facturas)
    numero_pago: String(50)  # Ref: transferencia, cheque, etc
    monto_pagado: Numeric(15, 2)
    estado_pago: Enum(EstadoPago)
    fecha_pago: DateTime  # CRITICAL: Cuándo se pagó
    procesado_por: String(255)  # AUDIT: Quién marcó como pagado
    fecha_procesamiento: DateTime  # Cuándo se registró
    metodo_pago: String(50)  # transferencia, cheque, efectivo, etc
    referencia_banco: String(100)  # Ref externa (transferencia ID)
    observaciones: String(500)
    creado_en: DateTime
    actualizado_en: DateTime

    factura: Relationship
    responsable_procesador: Relationship
```

#### 1.2 Actualizar Modelo Factura
```python
# MODIFY: app/models/factura.py - Agregar:
- fecha_pago: DateTime (cuando pasó a "pagada")
- pagos: Relationship a PagoFactura  # One-to-Many
- @property dias_sin_pagar()  # Para alerts
- @property dias_vencido()  # Urgencia
```

#### 1.3 Crear Endpoint de Pago
```python
# NEW: app/api/v1/routers/accounting.py

@router.post(
    "/facturas/{factura_id}/pagar",
    summary="Marcar factura como pagada",
    description="Solo contadores pueden procesar pagos"
)
async def procesar_pago_factura(
    factura_id: int,
    request: PagoRequest,  # monto, referencia, metodo_pago
    current_user=Depends(require_role("contador")),
    db: Session = Depends(get_db)
):
    """
    Procesa pago de factura.

    Validaciones:
    - Factura debe estar en estado aprobada/aprobada_auto
    - Monto pagado no puede exceder monto factura
    - Una factura aprobada solo pasa a pagada, no a otros estados

    Auditoría:
    - Registra quién procesó el pago
    - Guarda referencia de banco
    - Crea registro en PagoFactura
    - Actualiza estado de Factura a 'pagada'
    - Envía notificación a proveedor
    """
    pass
```

#### 1.4 Actualizar Dashboard (Frontend)
```typescript
// ADD: Filtros en accounting.dashboard
- Estado: [Aprobadas, Pagadas, Devueltas, Todas]
- Fecha pago: [Última semana, Último mes, Rango custom]
- Urgencia: [Vencidas, Por vencer, En plazo]

// ADD: Columnas
- Días sin pagar
- Estado pago
- Referencia pago
- Responsable pago
```

---

## 🟡 RECOMENDACIÓN #2: MEJORAR CONTROL DE DEVOLUCIONES
**Prioridad:** ALTA | **Impacto:** Alto | **Esfuerzo:** Medio-Alto

### Situación Actual
- Cuando devuelves factura → estado = "rechazada"
- No hay forma de distinguir entre:
  - Rechazo definitivo
  - Devolución por información faltante
  - Devolución por error del proveedor

### Solución Recomendada

#### 2.1 Ampliar Estados de Factura
```python
# MODIFY: app/models/factura.py
class EstadoFactura(enum.Enum):
    en_revision = "en_revision"
    aprobada = "aprobada"
    aprobada_auto = "aprobada_auto"
    # NUEVOS ESTADOS:
    devuelta_proveedor = "devuelta_proveedor"  # Info faltante
    devuelta_correccion = "devuelta_correccion"  # Error del proveedor
    rechazada_definitiva = "rechazada_definitiva"  # Rechazo formal
    pagada = "pagada"
```

#### 2.2 Crear Tabla de Devoluciones
```python
# NEW FILE: app/models/devolucion_factura.py
class TipoDevolucion(enum.Enum):
    informacion_faltante = "informacion_faltante"
    correccion_error = "correccion_error"
    incumplimiento_contrato = "incumplimiento_contrato"
    otro = "otro"

class DevolucionFactura(Base):
    __tablename__ = "devoluciones_facturas"

    id: BigInteger (PK)
    factura_id: BigInteger (FK) - UNIQUE
    tipo_devolucion: Enum(TipoDevolucion)
    motivo_detalle: String(1000)  # Campo libre para descripción
    devuelto_por: String(255)  # Quién devolvió (contador)
    fecha_devolucion: DateTime
    estado_devolucion: String(50)  # pendiente, resuelto, cancelado
    fecha_resolucion: DateTime  # Cuando se resubió o se resolvió
    observaciones_resolucion: String(1000)
    creado_en: DateTime
    actualizado_en: DateTime
```

#### 2.3 Mejorar Endpoint de Devolución
```python
# MODIFY: app/api/v1/routers/accounting.py - devolver_factura()

# Cambiar parámetro:
- observaciones → motivo_devolucion
- Agregar: tipo_devolucion (select)
- Agregar: pasos_resolucion (instrucciones para proveedor)
```

---

## 🟢 RECOMENDACIÓN #3: REPORTES Y ANALYTICS (QUICK WINS)
**Prioridad:** MEDIA | **Impacto:** Medio | **Esfuerzo:** Bajo-Medio

### Agregar Endpoints de Reporting
```python
# NEW: app/api/v1/routers/reports.py

@router.get("/reports/tesoreria/resumen")
# Dinero en circulación, por pagar, vencido

@router.get("/reports/contador/performance")
# Facturas procesadas por contador, tiempo promedio

@router.get("/reports/proveedores/top10")
# Proveedores con más facturas, montos

@router.get("/reports/cash-flow/prediccion")
# Forecast de pagos próximos 90 días

@router.get("/reports/kpi/pagos")
# KPIs: días promedio pago, % pagadas a tiempo, etc
```

---

## 🟠 RECOMENDACIÓN #4: MEJORAR VALIDACIONES
**Prioridad:** MEDIA-ALTA | **Impacto:** Medio | **Esfuerzo:** Bajo

### Agregar Validaciones de Negocio
```python
# app/services/validacion_factura_service.py

class ValidacionFacturaService:

    def validar_antes_aprobar(self, factura: Factura) -> List[ErrorValidacion]:
        """
        Validaciones antes de aprobar:
        - Proveedor activo
        - Fecha vencimiento no pasada (alerta si está vencida)
        - Total coherente con items
        - Campos obligatorios completos
        - Duplicado con última factura (mismo proveedor + 5% monto)
        """

    def validar_antes_pagar(self, factura: Factura) -> List[ErrorValidacion]:
        """
        Validaciones antes de pagar:
        - Debe estar aprobada
        - No estar ya pagada
        - Monto válido
        - Referencia pago válida
        """
```

---

## 🔵 RECOMENDACIÓN #5: ARQUITECTURA DE DATOS
**Prioridad:** MEDIA | **Impacto:** Medio-Alto | **Esfuerzo:** Medio

### Estado Actual ✅
Tu arquitectura está muy bien:
- Normalización 3NF perfecta
- Relaciones bien definidas
- Audit log completo
- Soft deletes (considerar agregar)

### Mejoras Propuestas

#### 5.1 Agregar Soft Deletes
```python
# Para poder recuperar datos "eliminados" por error
class Factura(Base):
    # ... campos existentes ...
    eliminada = Column(Boolean, default=False, index=True)
    fecha_eliminacion = Column(DateTime, nullable=True)
    eliminada_por = Column(String(255), nullable=True)
```

#### 5.2 Agregar Caché de Estados
```python
# Para queries más rápidas
class FacturaEstado(Base):
    __tablename__ = "vista_facturas_estados"  # Materialized view

    factura_id: BigInteger
    estado_actual: String
    estado_pago: String
    dias_sin_cambio: Integer
    # ... resumido para dashboard rápido
```

---

## 🏆 RECOMENDACIÓN #6: SEGURIDAD Y COMPLIANCE
**Prioridad:** CRÍTICA | **Impacto:** Muy Alto | **Esfuerzo:** Bajo

### Audit Trail Completo
```python
# Validar que TODO cambio de estado se audite:
- ✅ Aprobación: Logged
- ✅ Rechazo: Logged
- ✅ Devolución: Logged
- ❌ Cambio a pagada: NO ESTÁ AUDITADO
- ❌ Edición de facturas: Revisar cobertura
```

### Permisos y Roles
```
✅ RESPONSABLE (Aprobador):
   - Ver facturas asignadas
   - Aprobar/rechazar

✅ CONTADOR:
   - Ver todas las aprobadas
   - Marcar como pagadas
   - Devolver facturas

⚠️ VERIFICAR:
   - ¿Puede contador EDITAR facturas aprobadas?
   - ¿Puede contador CANCELAR pagos?
   - ¿Puede responsable ver facturas de otros?
```

---

## 📊 ROADMAP RECOMENDADO (Fases)

### Fase 1 (1-2 semanas) - CRÍTICA
- ✅ [HECHO] Arreglar método send_html_email → send_email
- ✅ [HECHO] Arreglar atributo proveedor.nombre → razon_social
- ⏳ Implementar Tabla PagoFactura
- ⏳ Crear endpoint POST /pagar
- ⏳ Agregar filtros en dashboard

### Fase 2 (2-3 semanas) - IMPORTANTE
- Mejorar estados de factura (devuelta_proveedor, etc)
- Crear tabla DevolucionFactura
- Mejorar validaciones
- Agregar soft deletes

### Fase 3 (1 mes) - NICE TO HAVE
- Reportes y analytics
- Materialized views para performance
- Integración bancaria (si aplica)
- Dashboard KPIs

---

## 💡 DECISIONES CLAVE

### 1. ¿Pagos Parciales o Solo Completos?
**Recomendación:** Inicialmente SOLO COMPLETOS
- Después soportar parciales si el negocio lo requiere
- Más simple de implementar y auditar

### 2. ¿Integración Bancaria Automática?
**Recomendación:** NO por ahora
- Primero marcar manualmente (contador)
- Luego considerar integración con banco
- Requiere verificaciones adicionales

### 3. ¿Quién Marca como Pagado?
**Recomendación:** SOLO CONTADOR
- Requiere evidencia (referencia banco)
- No automatizar hasta tener integración
- Mantener auditoría clara

### 4. ¿Cancelar Pagos?
**Recomendación:** SÍ, agregar endpoint
```python
@router.post("/facturas/{id}/cancelar-pago")
# Registra cancelación en PagoFactura
# Cambia estado factura de vuelta a aprobada
# Requiere motivo y autorización
```

---

## 📈 METRICS A MONITOREAR

Una vez implementado:
```
- Tiempo promedio de pago: días entre aprobación y pago
- % facturas pagadas a tiempo: vs fecha vencimiento
- Facturas devueltas: %
- Dinero en circulación: total aprobado no pagado
- Performance contador: facturas/día, devoluciones
```

---

## 🎓 CONCLUSIÓN

Tu sistema tiene **BUENA ARQUITECTURA BASE**. El foco debería ser:

1. **Inmediato:** Completar ciclo de pago (es el "missing link")
2. **Importante:** Mejor auditoría de devoluciones
3. **Nice to have:** Reportes y analytics

La implementación es **straightforward** si sigues el patrón ya establecido en el código.


