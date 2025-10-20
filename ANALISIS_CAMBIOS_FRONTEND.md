# ANÁLISIS DE IMPACTO - CAMBIOS BACKEND → FRONTEND

**Fecha:** 2025-10-19
**Objetivo:** Sincronizar frontend después de Fases 2.4 y 2.5

---

## 🔍 CAMBIOS CRÍTICOS QUE AFECTAN FRONTEND

### 1. **ELIMINACIÓN DE CAMPOS EN FACTURA** (Fase 2.4)

#### Campos ELIMINADOS de `facturas`:
```python
# ❌ YA NO EXISTEN en backend
factura.aprobado_por
factura.fecha_aprobacion
factura.rechazado_por
factura.fecha_rechazo
factura.motivo_rechazo
```

#### Campos NUEVOS (acceso vía helpers):
```python
# ✅ USAR AHORA
factura.aprobado_por_workflow
factura.fecha_aprobacion_workflow
factura.rechazado_por_workflow
factura.fecha_rechazo_workflow
factura.motivo_rechazo_workflow
factura.tipo_aprobacion_workflow
```

**IMPACTO EN FRONTEND:**
- Interfaces TypeScript con campos viejos → ERROR
- Componentes que muestran `aprobado_por` → Mostrarán `null`
- Formularios de aprobación/rechazo → Pueden fallar

---

### 2. **GENERATED COLUMNS EN ITEMS** (Fase 2.5)

#### Campos READ-ONLY ahora:
```python
# ❌ NO SE PUEDEN INSERTAR/ACTUALIZAR directamente
factura_items.subtotal  # GENERATED
factura_items.total     # GENERATED
```

**IMPACTO EN FRONTEND:**
- Formularios que permiten editar `subtotal` o `total` → Rechazados por backend
- Cálculos manuales en frontend → Innecesarios (MySQL calcula)

---

### 3. **ELIMINACIÓN DE RESPONSABLE_PROVEEDOR**

#### Modelo/Endpoint ELIMINADO:
```python
# ❌ YA NO EXISTE
/api/v1/responsable-proveedor
app/models/responsable_proveedor.py
```

#### Nuevo endpoint:
```python
# ✅ USAR AHORA
/api/v1/asignacion-nit
```

**IMPACTO EN FRONTEND:**
- Rutas a `/responsable-proveedor` → 404
- Componentes de asignación → Deben usar nuevo endpoint

---

## 📋 PLAN DE SINCRONIZACIÓN

### PASO 1: Actualizar Interfaces TypeScript

**Archivo:** `frontend/src/types/factura.ts` (o similar)

```typescript
// ❌ ANTES (interfaces viejas)
interface Factura {
  id: number;
  numero_factura: string;
  total_a_pagar: number;
  aprobado_por: string | null;        // ❌ Eliminado
  fecha_aprobacion: string | null;    // ❌ Eliminado
  rechazado_por: string | null;       // ❌ Eliminado
  fecha_rechazo: string | null;       // ❌ Eliminado
  motivo_rechazo: string | null;      // ❌ Eliminado
}

// ✅ DESPUÉS (interfaces actualizadas)
interface Factura {
  id: number;
  numero_factura: string;
  total_a_pagar: number;

  // Nuevos campos de workflow
  aprobado_por_workflow: string | null;
  fecha_aprobacion_workflow: string | null;
  rechazado_por_workflow: string | null;
  fecha_rechazo_workflow: string | null;
  motivo_rechazo_workflow: string | null;
  tipo_aprobacion_workflow: 'automatica' | 'manual' | 'masiva' | 'forzada' | null;
}

interface FacturaItem {
  id: number;
  factura_id: number;
  cantidad: number;
  precio_unitario: number;
  descuento_valor: number | null;
  total_impuestos: number | null;

  // ⚠️ READONLY - Calculados por MySQL
  subtotal: number;  // GENERATED
  total: number;     // GENERATED
}
```

---

### PASO 2: Actualizar Componentes React/Vue

**Componente:** Lista de facturas

```tsx
// ❌ ANTES
<td>{factura.aprobado_por}</td>
<td>{factura.fecha_aprobacion}</td>

// ✅ DESPUÉS
<td>{factura.aprobado_por_workflow}</td>
<td>{factura.fecha_aprobacion_workflow}</td>
```

**Componente:** Formulario de aprobación

```tsx
// ❌ ANTES
const aprobarFactura = async (id: number, usuario: string) => {
  await api.put(`/facturas/${id}/aprobar`, {
    aprobado_por: usuario,           // ❌ Campo eliminado
    fecha_aprobacion: new Date()
  });
};

// ✅ DESPUÉS
const aprobarFactura = async (id: number, usuario: string) => {
  // El backend ahora crea/actualiza workflow automáticamente
  await api.put(`/facturas/${id}/aprobar`, {
    // Backend maneja workflow internamente
  });
};
```

---

### PASO 3: Actualizar Formularios de Items

**Componente:** Edición de items

```tsx
// ❌ ANTES (permitía editar subtotal y total)
<input
  type="number"
  value={item.subtotal}
  onChange={(e) => setItem({...item, subtotal: e.target.value})}
/>
<input
  type="number"
  value={item.total}
  onChange={(e) => setItem({...item, total: e.target.value})}
/>

// ✅ DESPUÉS (solo editar campos base, subtotal/total se calculan)
<input
  type="number"
  value={item.cantidad}
  onChange={(e) => setItem({...item, cantidad: e.target.value})}
/>
<input
  type="number"
  value={item.precio_unitario}
  onChange={(e) => setItem({...item, precio_unitario: e.target.value})}
/>
<!-- Mostrar subtotal/total como readonly -->
<div>Subtotal: {calcularSubtotal(item)}</div>
<div>Total: {calcularTotal(item)}</div>
```

**Helper de cálculo (temporal hasta recarga desde backend):**

```typescript
const calcularSubtotal = (item: FacturaItem) => {
  const base = item.cantidad * item.precio_unitario;
  const descuento = item.descuento_valor || 0;
  return base - descuento;
};

const calcularTotal = (item: FacturaItem) => {
  const subtotal = calcularSubtotal(item);
  const impuestos = item.total_impuestos || 0;
  return subtotal + impuestos;
};
```

---

### PASO 4: Actualizar Rutas de Asignación

**Servicio API:**

```typescript
// ❌ ANTES
const asignarResponsableProveedor = async (proveedorId: number, responsableId: number) => {
  return api.post('/api/v1/responsable-proveedor', {
    proveedor_id: proveedorId,
    responsable_id: responsableId
  });
};

// ✅ DESPUÉS
const asignarResponsableNIT = async (nit: string, responsableId: number) => {
  return api.post('/api/v1/asignacion-nit', {
    nit: nit,
    responsable_id: responsableId
  });
};
```

---

### PASO 5: Verificar Schemas de Respuesta

**Endpoint:** `GET /api/v1/facturas/{id}`

```json
// ✅ Respuesta actual del backend
{
  "id": 1,
  "numero_factura": "FETE14569",
  "total_a_pagar": 15000.00,
  "subtotal": 12605.04,
  "iva": 2394.96,

  // Campos de workflow (via helpers)
  "aprobado_por_workflow": "5",
  "fecha_aprobacion_workflow": "2024-10-15T10:30:00",
  "rechazado_por_workflow": null,
  "fecha_rechazo_workflow": null,
  "motivo_rechazo_workflow": null,
  "tipo_aprobacion_workflow": "manual"
}
```

---

## 🔧 SCRIPTS DE AYUDA

### Script 1: Buscar usos de campos viejos

```bash
# En el directorio del frontend
grep -r "aprobado_por[^_]" src/
grep -r "fecha_aprobacion[^_]" src/
grep -r "rechazado_por[^_]" src/
grep -r "fecha_rechazo[^_]" src/
grep -r "motivo_rechazo[^_]" src/
grep -r "responsable-proveedor" src/
```

### Script 2: Reemplazos globales (con precaución)

```bash
# Reemplazar campos de workflow
find src/ -type f -name "*.ts" -o -name "*.tsx" | xargs sed -i 's/aprobado_por\b/aprobado_por_workflow/g'
find src/ -type f -name "*.ts" -o -name "*.tsx" | xargs sed -i 's/fecha_aprobacion\b/fecha_aprobacion_workflow/g'
```

---

## ⚠️ CAMBIOS QUE REQUIEREN REVISIÓN MANUAL

1. **Validaciones de formularios**
   - Si había validación de `subtotal` o `total` → Eliminar

2. **Cálculos locales**
   - Si frontend calculaba totales → Confiar en backend

3. **Estados de aprobación**
   - Verificar que flujos de aprobación/rechazo usen workflow

4. **Filtros y búsquedas**
   - Si filtraban por `aprobado_por` → Actualizar a `aprobado_por_workflow`

---

## 📊 CHECKLIST DE SINCRONIZACIÓN

### Interfaces TypeScript
- [ ] Actualizar `Factura` interface
- [ ] Actualizar `FacturaItem` interface
- [ ] Eliminar `ResponsableProveedor` interface
- [ ] Agregar `AsignacionNIT` interface

### Componentes
- [ ] Actualizar lista de facturas
- [ ] Actualizar detalle de factura
- [ ] Actualizar formulario de aprobación
- [ ] Actualizar formulario de rechazo
- [ ] Actualizar formulario de items
- [ ] Actualizar componente de asignación de responsables

### Servicios API
- [ ] Actualizar `facturaService.ts`
- [ ] Actualizar `responsableService.ts`
- [ ] Eliminar/deprecar `responsableProveedorService.ts`
- [ ] Crear `asignacionNitService.ts`

### Testing
- [ ] Probar flujo de aprobación
- [ ] Probar flujo de rechazo
- [ ] Probar creación/edición de items
- [ ] Probar asignación de responsables por NIT
- [ ] Verificar cálculo automático de totales

---

## 🚨 ERRORES COMUNES A EVITAR

1. **Intentar enviar `subtotal` o `total` en items**
   ```typescript
   // ❌ ESTO FALLARÁ
   await api.post('/items', {
     cantidad: 10,
     precio_unitario: 100,
     subtotal: 1000,  // ❌ Backend rechazará
     total: 1000      // ❌ Backend rechazará
   });

   // ✅ CORRECTO
   await api.post('/items', {
     cantidad: 10,
     precio_unitario: 100
     // subtotal y total se calculan automáticamente
   });
   ```

2. **Acceder a campos eliminados**
   ```typescript
   // ❌ Retornará undefined
   console.log(factura.aprobado_por);

   // ✅ Usar campos workflow
   console.log(factura.aprobado_por_workflow);
   ```

3. **Usar endpoint viejo de responsable-proveedor**
   ```typescript
   // ❌ Retornará 404
   await api.get('/api/v1/responsable-proveedor');

   // ✅ Usar nuevo endpoint
   await api.get('/api/v1/asignacion-nit');
   ```

---

## 📝 PRÓXIMOS PASOS

1. Ubicar directorio del frontend
2. Ejecutar scripts de búsqueda
3. Actualizar interfaces TypeScript
4. Actualizar componentes uno por uno
5. Testing exhaustivo
6. Deploy sincronizado con backend

---

**Preparado para sincronización frontend**
**Fecha:** 2025-10-19
