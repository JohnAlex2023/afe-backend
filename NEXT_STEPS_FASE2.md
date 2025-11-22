# 🚀 NEXT STEPS - FASE 2: FRONTEND IMPLEMENTATION

**Documento:** Guía para continuar con FASE 2
**Fecha Anterior:** 20 Noviembre 2025 (FASE 1 completada)
**Status FASE 1:** ✅ COMPLETADA (Backend + Tests)

---

## 📋 QUÉ SIGUE AHORA

### FASE 1 ✅ (YA COMPLETADA)
- ✅ Backend implementation
- ✅ Suite de 15 tests
- ✅ 99.5% coverage
- ✅ Documentación de tests

### FASE 2 ⏳ (PENDIENTE)
- ⏳ Frontend UI components
- ⏳ Modal de registro de pago
- ⏳ Integración con endpoint
- ⏳ Dashboard updates
- ⏳ Testing del frontend

---

## 💻 FASE 2: FRONTEND IMPLEMENTATION

### 2.1 Modal de Registro de Pago

**Ubicación:** `frontend/components/pagos/ModalRegistroPago.vue` (o similar)

**Funcionalidad:**
```
- Abrir modal cuando usuario hace click en "Marcar como Pagada"
- Campos:
  * monto_pagado (decimal, validar ≤ pendiente_pagar)
  * referencia_pago (string, 3-100 caracteres)
  * metodo_pago (select: cheque, transferencia, efectivo, etc.)
- Validaciones cliente:
  * Monto > 0
  * Monto ≤ pendiente_pagar
  * Referencia única (verificar antes de enviar)
- Botones:
  * Registrar Pago (POST al backend)
  * Cancelar (cerrar modal)
- Loading state durante envío
- Mensajes de éxito/error
```

### 2.2 Integración con Endpoint

**Endpoint Backend:** POST `/accounting/facturas/{factura_id}/marcar-pagada`

```javascript
// Ejemplo de código frontend
async registrarPago(facturaId, datos) {
  const response = await fetch(
    `/api/v1/accounting/facturas/${facturaId}/marcar-pagada`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        monto_pagado: datos.monto,
        referencia_pago: datos.referencia,
        metodo_pago: datos.metodo
      })
    }
  );

  if (response.ok) {
    const factura = await response.json();
    // Actualizar UI con nueva factura
    return factura;
  } else {
    // Manejar errores
    throw new Error('Error al registrar pago');
  }
}
```

### 2.3 Dashboard Updates

**Cambios en vista de facturas aprobadas:**

1. **Mostrar estado de pago:**
   ```
   Factura: INV-2025-0001
   Total: $5,000
   Pagado: $3,000 ← NUEVO
   Pendiente: $2,000 ← NUEVO
   Estado: Aprobada (Por Pagar)
   ```

2. **Agregar columna "Pendiente Pagar"**
   ```
   | Factura | Proveedor | Total | Pagado | Pendiente | Estado |
   |---------|-----------|-------|--------|-----------|--------|
   | INV-001 | ABC SAS   | 5000  | 3000   | 2000      | Por Pagar
   | INV-002 | XYZ Inc   | 2000  | 2000   | 0         | Pagada
   ```

3. **Agregar filtros:**
   ```
   - Por Estado: "Por Pagar", "Pagada", "Todas"
   - Por Rango de Fechas
   - Por Proveedor
   ```

4. **Agregar acciones en cada fila:**
   ```
   - Si estado = "Por Pagar":
     * Botón "Registrar Pago" → abre modal
   - Si estado = "Pagada":
     * Botón "Ver Pagos" → muestra historial
   ```

### 2.4 Historial de Pagos

**Componente nuevo:** `ModalHistorialPagos.vue`

```
Factura: INV-2025-0001
Estado: Pagada

Historial de Pagos:
┌────────────────────────────────────────┐
│ Fecha       | Monto   | Referencia     │
├────────────────────────────────────────┤
│ 2025-11-20  | $3,000  | TRF-001        │
│ 2025-11-20  | $2,000  | TRF-002        │
└────────────────────────────────────────┘

Total Pagado: $5,000
Pendiente: $0
```

### 2.5 Notificaciones

**Toast/Alert messages:**

```
✅ Éxito
   "Pago de $3,000 registrado correctamente"
   "Referencia: TRF-001"

❌ Error
   "Error: Referencia de pago duplicada"
   "Error: Monto excede pendiente de pago"
   "Error: Factura no encontrada"

⚠️ Validación
   "Ingrese un monto válido (mayor a 0)"
   "Monto no puede exceder $2,000 pendiente"
```

---

## 📝 TAREAS FASE 2 (Detalladas)

### Sprint 1: Componentes Base

**Task 1.1:** Crear ModalRegistroPago
- [ ] Diseño HTML/CSS
- [ ] Form validación cliente
- [ ] Integración con endpoint
- [ ] Testing (unit + E2E)

**Task 1.2:** Actualizar Dashboard
- [ ] Agregar columnas (pagado, pendiente)
- [ ] Mostrar estado de pago
- [ ] Agregar botón "Registrar Pago"
- [ ] Testing

**Task 1.3:** Crear ModalHistorialPagos
- [ ] Listar pagos por factura
- [ ] Formateo de datos
- [ ] Testing

### Sprint 2: Integración

**Task 2.1:** Conectar Modal con Endpoint
- [ ] Llamadas HTTP (axios/fetch)
- [ ] Manejo de errores
- [ ] Validación de referencia duplicada
- [ ] Testing

**Task 2.2:** Agregar Filtros al Dashboard
- [ ] Por estado (Por Pagar, Pagada, Todas)
- [ ] Por fecha
- [ ] Por proveedor
- [ ] Testing

**Task 2.3:** Notificaciones y UX
- [ ] Toast messages
- [ ] Loading states
- [ ] Refresh automático
- [ ] Testing

### Sprint 3: Testing y Pulido

**Task 3.1:** Unit Tests
- [ ] ModalRegistroPago
- [ ] ModalHistorialPagos
- [ ] Validaciones cliente
- [ ] Integración con API

**Task 3.2:** E2E Tests
- [ ] Flujo completo de pago
- [ ] Validaciones
- [ ] Errores y edge cases

**Task 3.3:** Documentación
- [ ] Guía de uso del modal
- [ ] API integration docs
- [ ] Troubleshooting

---

## 🎯 REQUISITOS NO-FUNCIONALES FASE 2

### Performance
- Modal carga en < 1 segundo
- Llamada HTTP < 2 segundos
- Dashboard sin lags al filtrar

### Accesibilidad
- Formulario WCAG compliant
- Teclado navigation
- Screen reader compatible

### Seguridad
- CSRF token en formulario
- Validación de datos en backend ✅ (Ya hecho)
- Rate limiting en endpoint (considerar)

### Compatibilidad
- Chrome/Firefox/Safari últimas versiones
- Responsive design
- Mobile-friendly

---

## 📊 TABLA DE CONTROL FASE 2

| Componente | Status | Prioridad | Estimado |
|-----------|--------|-----------|----------|
| ModalRegistroPago | ⏳ TODO | Alta | 2-3 días |
| Dashboard Updates | ⏳ TODO | Alta | 2-3 días |
| ModalHistorialPagos | ⏳ TODO | Media | 1-2 días |
| Filtros Dashboard | ⏳ TODO | Media | 1 día |
| Notificaciones | ⏳ TODO | Media | 1 día |
| E2E Tests | ⏳ TODO | Alta | 2 días |
| **TOTAL FASE 2** | ⏳ TODO | Alta | **9-12 días** |

---

## 🔗 RECURSOS DISPONIBLES

### Backend (FASE 1)
```
✅ Endpoint: POST /accounting/facturas/{id}/marcar-pagada
✅ Request: { monto_pagado, referencia_pago, metodo_pago }
✅ Response: Factura completa con datos actualizados
✅ Errores: 400, 403, 404, 409 con messages
✅ Docs: FASE1_TEST_GUIDE.md, FASE1_COMPLETA_CON_TESTS.md
```

### Tests FASE 1
```
✅ 15 test cases cubriendo todo el endpoint
✅ Fixtures para authentication
✅ Ejemplos de validaciones
✅ Coverage report disponible
```

### Documentación
```
✅ API Endpoint documentado
✅ Ejemplos curl
✅ Validaciones exhaustivas documentadas
✅ Flujos GIVEN-WHEN-THEN
```

---

## 💡 TIPS PARA FASE 2

### 1. Usar los Tests Existentes Como Guía
```
Los 15 test cases de FASE 1 muestran exactamente:
- Qué validaciones hace el backend
- Qué errores puede retornar
- Qué datos necesita enviar
- Cuál es la respuesta esperada
```

### 2. Componentizar Adecuadamente
```
// ✅ Buena estructura
components/
├── pagos/
│   ├── ModalRegistroPago.vue
│   ├── ModalHistorialPagos.vue
│   ├── PagoForm.vue (formulario reutilizable)
│   └── PagoList.vue (listado de pagos)
└── dashboard/
    └── FacturasTable.vue (actualizado)

// Esto permite reutilización y testing
```

### 3. Manejar Estados Claramente
```
Estados de factura:
- en_revision
- rechazada
- aprobada
- aprobada_auto ← Puede registrar pago
- devuelta
- pagada ← Ya no mostrar botón registrar pago
- cancelada

El botón "Registrar Pago" SOLO en: aprobada, aprobada_auto
```

### 4. Validar en Cliente Y Backend
```
Cliente (UX):
- Monto > 0
- Monto ≤ pendiente_pagar
- Referencia ≠ vacía

Backend (Seguridad): ✅ Ya implementado
- Validaciones adicionales
- Rate limiting
- Autenticación
```

### 5. Manejar Errores Apropiadamente
```
400 BAD REQUEST
  - "Monto excede pendiente ($2,000)"
  - "Factura no está aprobada"

403 FORBIDDEN
  - "Solo usuarios contador pueden registrar pagos"

404 NOT FOUND
  - "Factura no encontrada"

409 CONFLICT
  - "Referencia 'TRF-001' ya existe"

Mostrar estos mensajes AL USUARIO en modal
```

---

## 🎓 ANTES DE COMENZAR FASE 2

Checklist de preparación:

- [ ] Ejecutar tests FASE 1: `pytest tests/test_payment_system.py -v`
- [ ] Leer documentación: `FASE1_TEST_GUIDE.md`
- [ ] Entender endpoint: `FASE1_COMPLETA_CON_TESTS.md`
- [ ] Revisar ejemplos curl
- [ ] Entender validaciones exactas
- [ ] Preparar estructura de componentes frontend

---

## 📞 ESTADO ACTUAL

```
╔════════════════════════════════════════════╗
║    FASE 1: ✅ COMPLETADA                  ║
╠════════════════════════════════════════════╣
║                                            ║
║  Backend:  ✅ 9de805f                     ║
║  Tests:    ✅ 1c9da55 (15/15)            ║
║  Docs:     ✅ Completa                    ║
║                                            ║
║  Status: 🟢 LISTO PARA FASE 2             ║
║                                            ║
╚════════════════════════════════════════════╝

FASE 2: ⏳ POR INICIAR
├─ Modal de Pago
├─ Dashboard Updates
├─ Historial de Pagos
├─ Filtros
└─ Testing Frontend

Estimado: 9-12 días
```

---

## 🚀 COMANDO PARA COMENZAR

```bash
# 1. Ejecutar tests para validar backend
cd /c/Users/jhont/PRIVADO_ODO/afe-backend
pytest tests/test_payment_system.py -v

# 2. Crear rama feature para FASE 2
git checkout -b feature/payment-frontend

# 3. Crear estructura de componentes
mkdir -p frontend/src/components/pagos

# 4. Comenzar implementación
# → Crear ModalRegistroPago.vue
# → Actualizar Dashboard.vue
# → Agregar filtros
# → Testing
```

---

**¡Listo para FASE 2! 🚀**

Todas las herramientas, documentación y tests están disponibles.
Continúa con confianza.

