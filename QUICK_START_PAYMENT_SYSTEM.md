# ⚡ QUICK START: SISTEMA DE PAGOS (15 minutos de lectura)

## 🎯 TL;DR

Tu sistema de facturas está **95% completo**. Le falta **5%: el sistema de pagos**.

### El Problema
```
Factura en "aprobada" → ¿Cómo se marca como pagada?
                      ¿Quién marcó? ¿Cuándo? ¿Cuánto?
                      → NADA. No hay forma.
```

### La Solución (3 pasos)
1. Crear tabla `PagoFactura` (auditoría de pagos)
2. Agregar endpoint POST `/pagar`
3. Crear filtro "Pagadas/Pendientes" en dashboard

**Tiempo:** 5-6 horas de coding

---

## ✨ ANTES vs DESPUÉS

### ANTES (Ahora)
```
Contador ve factura aprobada
    → "¿Cuál era el monto?"
    → "¿Ya la pagaste?"
    → "¿Cuándo?"
    → NO HAY FORMA DE REGISTRARLO
```

### DESPUÉS (Con sistema de pagos)
```
Contador ve factura aprobada
    → Click en "Marcar como Pagada"
    → Modal: cantidad, método, referencia, fecha
    → Sistema registra quién, cuándo, referencia banco
    → Email automático al proveedor: "Pago recibido"
    → Dashboard: filtro "Pagadas/Pendientes"
    → Reportes: cuánto $ está en circulación
```

---

## 🏗️ ARQUITECTURA SIMPLE

```
PagoFactura (Nueva tabla)
├── factura_id (FK)
├── numero_pago (único)
├── monto_pagado
├── metodo_pago (transferencia, cheque, efectivo)
├── referencia_externa (ID banco, número cheque)
├── fecha_pago ← IMPORTANTE para tesorería
├── procesado_por ← AUDITORÍA: quién pagó
├── estado_pago (completado, fallido, revertido)
└── [timestamps]

Factura (Actualización)
├── fecha_pago ← Cuándo fue pagada
├── pagos: Relationship → PagoFactura (multiple)
├── @property total_pagado
├── @property pendiente_pagar
├── @property esta_completamente_pagada
└── @property dias_sin_pagar
```

---

## 📋 CHECKLIST (Copia esto)

### PASO 1: Modelo (30 min)
```
[ ] Copiar código de IMPLEMENTACION_PAGO_FACTURAS.md → app/models/pago_factura.py
[ ] Actualizar Factura model (agregar relación + propiedades)
[ ] Crear migration: alembic revision --autogenerate -m "..."
[ ] Ejecutar: alembic upgrade head
```

### PASO 2: API (1.5 horas)
```
[ ] Crear app/schemas/pago.py (copiar de guía)
[ ] Agregar POST /accounting/facturas/{id}/pagar (copiar de guía)
[ ] Agregar GET /accounting/facturas/{id}/historial-pagos
[ ] Agregar POST /accounting/pagos/{id}/revertir
[ ] Testear con Postman/curl
```

### PASO 3: Frontend (1 hora)
```
[ ] Agregar botón "Marcar como Pagado" en factura aprobada
[ ] Crear modal con formulario (monto, método, referencia, fecha)
[ ] Agregar filtro "Pagadas/Pendientes" en accounting dashboard
[ ] Mostrar "Total pagado" vs "Pendiente" en factura
```

### PASO 4: Notificaciones (30 min)
```
[ ] Crear template pago_factura.html (basarse en devolucion_factura_responsable.html)
[ ] Agregar envío de email al proveedor cuando se marca como pagada
[ ] Prueba: marcar una factura como pagada y verificar email
```

### PASO 5: Testing (1 hora)
```
[ ] Test: monto válido
[ ] Test: monto mayor al pendiente (debe fallar)
[ ] Test: referencia duplicada (debe fallar)
[ ] Test: reversión de pago
[ ] Test: factura no aprobada (debe fallar)
```

**TOTAL: ~5-6 horas**

---

## 🚀 COPIAR & PEGAR (Fast Track)

### 1. Crear modelo
Copia TODO el contenido de la sección **"PASO 1: Crear Modelo PagoFactura"** en:
`IMPLEMENTACION_PAGO_FACTURAS.md`

Pégalo en nuevo archivo:
```
app/models/pago_factura.py
```

### 2. Actualizar Factura
Copia la sección **"PASO 2: Actualizar Modelo Factura"** en:
`IMPLEMENTACION_PAGO_FACTURAS.md`

Pégalo al final de:
```
app/models/factura.py
```

### 3. Crear schemas
Copia TODO de **"PASO 3: Crear Schema"** en:
`IMPLEMENTACION_PAGO_FACTURAS.md`

Pégalo en nuevo archivo:
```
app/schemas/pago.py
```

### 4. Agregar endpoints
Copia TODO de **"PASO 4: Crear Endpoints"** en:
`IMPLEMENTACION_PAGO_FACTURAS.md`

Pégalo al final de:
```
app/api/v1/routers/accounting.py
```

### 5. Migration
```bash
cd afe-backend
alembic revision --autogenerate -m "Add payment processing system"
alembic upgrade head
```

**Listo. Sistema de pagos funcional.**

---

## 🎓 PREGUNTAS FRECUENTES

### P: ¿Una factura puede tener múltiples pagos?
**R:** SÍ. Ejemplo: factura de $100 → pago $60 + pago $40 = completada

### P: ¿Puedo cancelar un pago?
**R:** SÍ. Endpoint `POST /pagos/{id}/revertir`. Factura vuelve a "aprobada"

### P: ¿Qué pasa si pago más de lo debido?
**R:** El sistema rechaza si el monto > pendiente. No permite sobrepago.

### P: ¿Se integra con banco automáticamente?
**R:** NO por ahora. Marcar manualmente. Integración bancaria es fase 2.

### P: ¿Quién puede marcar como pagado?
**R:** Solo CONTADOR. Requiere autenticación y rol.

### P: ¿Se audita quién pagó?
**R:** SÍ. Campo `procesado_por` + timestamp `fecha_procesamiento`

### P: ¿Se notifica al proveedor?
**R:** SÍ. Email automático cuando se marca como pagada.

### P: ¿Puedo tener pagos parciales?
**R:** SÍ. Una factura puede tener múltiples `PagoFactura`

---

## 📊 GANANCIA INMEDIATA

Una vez implementado tendrás:

✅ **Visibilidad:** Dinero en circulación = facturas aprobadas - pagadas
✅ **Auditoría:** Quién pagó qué, cuándo, con qué referencia
✅ **Alertas:** Facturas vencidas sin pagar
✅ **Reportes:** Cash flow, días promedio pago, % pagadas a tiempo
✅ **Control:** Reversión de pagos con motivo
✅ **Notificaciones:** Proveedor confirmado de pago

---

## 🔗 PRÓXIMOS PASOS DESPUÉS DEL PAGO

Una vez tengas pagos funcionando:

1. **Reportes de Tesorería** (3-4 horas)
   - Dashboard: dinero en circulación
   - Forecast: próximos 90 días
   - KPIs: días promedio pago

2. **Mejorar Devoluciones** (2-3 horas)
   - Distinguir: rechazo vs devolución
   - Tabla auditoría de devoluciones
   - Dashboard: causas de devoluciones

3. **Validaciones** (2-3 horas)
   - Detectar duplicados
   - Validar proveedor activo
   - Alertas de fecha vencida

4. **Soft Deletes** (1 hora)
   - Poder recuperar facturas eliminadas
   - Auditoría de eliminaciones

---

## ⚠️ ERRORES COMUNES A EVITAR

❌ NO guardes el email del pagador en Factura
→ Guárdalo en PagoFactura.procesado_por

❌ NO elimines facturas pagadas
→ Usa soft delete (flag eliminada = True)

❌ NO permitas editar un pago completado
→ Crear uno nuevo o revertir + crear

❌ NO confundas PagoFactura con HistorialPagos
→ PagoFactura = transacciones reales
→ HistorialPagos = análisis estadístico

❌ NO olvides validar monto < pendiente
→ Siempre: `monto_pagado <= factura.pendiente_pagar`

---

## 🎯 META

**Semana próxima:**
- Lunes: Modelo + Endpoints (4 horas)
- Martes: Frontend (2-3 horas)
- Miércoles: Testing (1 hora)
- Jueves: Deploy (1 hora)
- Viernes: Documentación + cierre

**Resultado:** Sistema de pagos completamente funcional ✅

---

## 📞 SOPORTE

Si necesitas ayuda:
1. Revisa `IMPLEMENTACION_PAGO_FACTURAS.md` (código detallado)
2. Revisa `RECOMENDACIONES_SENIOR_2025.md` (contexto)
3. Pregunta cualquier duda

**Estoy aquí para ayudarte a implementarlo.**

---

**¿Listo para empezar?**

Da el primer paso:
```bash
# 1. Crea el modelo
touch app/models/pago_factura.py

# 2. Copia el código de IMPLEMENTACION_PAGO_FACTURAS.md

# 3. Crea la migration
alembic revision --autogenerate -m "Add payment system"

# 4. Aplica
alembic upgrade head

# 5. Commit
git add . && git commit -m "feat: Add payment processing system"
```

¡Adelante! 🚀

