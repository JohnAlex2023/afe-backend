# 🔧 Corrección del Frontend para Nueva Estructura de Paginación

## ❌ Problema

El frontend está fallando con el error:
```
Uncaught TypeError: facturas.filter is not a function
```

**Causa:** El backend ahora retorna `{ data: [...], pagination: {...} }` en lugar de un array directo.

---

## ✅ Solución

### Archivo a Modificar:
`afe_frontend/src/features/dashboard/DashboardPage.tsx`

### Cambios Necesarios:

#### 1. En la función `loadData()`, línea ~110-180:

**❌ ANTES:**
```typescript
const [todasResponse, asignadasResponse] = await Promise.all([
  apiClient.get('/facturas/'), // Todas las facturas
  apiClient.get('/facturas/', { params: { solo_asignadas: true } }), // Solo asignadas
]);

setTotalTodasFacturas(todasResponse.data.length);
setTotalAsignadas(asignadasResponse.data.length);

const allFacturas = vistaFacturas === 'todas' ? todasResponse.data : asignadasResponse.data;
```

**✅ DESPUÉS:**
```typescript
const [todasResponse, asignadasResponse] = await Promise.all([
  apiClient.get('/facturas/', { params: { page: 1, per_page: 2000 } }), // Todas las facturas
  apiClient.get('/facturas/', { params: { solo_asignadas: true, page: 1, per_page: 2000 } }), // Solo asignadas
]);

// ✅ CORRECCIÓN: Ahora el backend devuelve { data: [...], pagination: {...} }
const todasFacturasData = todasResponse.data.data || [];
const asignadasData = asignadasResponse.data.data || [];

setTotalTodasFacturas(todasResponse.data.pagination?.total || todasFacturasData.length);
setTotalAsignadas(asignadasResponse.data.pagination?.total || asignadasData.length);

const allFacturas = vistaFacturas === 'todas' ? todasFacturasData : asignadasData;
```

#### 2. Para usuarios Responsable, línea ~180-200:

**❌ ANTES:**
```typescript
const response = await apiClient.get('/facturas/');
const allFacturas = response.data;

setTotalAsignadas(allFacturas.length);
setTotalTodasFacturas(allFacturas.length);
```

**✅ DESPUÉS:**
```typescript
const response = await apiClient.get('/facturas/', { params: { page: 1, per_page: 2000 } });

// ✅ CORRECCIÓN: Ahora el backend devuelve { data: [...], pagination: {...} }
const allFacturas = response.data.data || [];

setTotalAsignadas(response.data.pagination?.total || allFacturas.length);
setTotalTodasFacturas(response.data.pagination?.total || allFacturas.length);
```

#### 3. Agregar función de exportación (nueva):

Busca la función `handleReject` y agrega DESPUÉS de ella:

```typescript
const handleExport = () => {
  // Construir URL de exportación
  const params = new URLSearchParams();

  if (filterEstado !== 'todos') {
    params.append('estado', filterEstado);
  }

  if (user?.rol === 'admin' && vistaFacturas === 'asignadas') {
    params.append('solo_asignadas', 'true');
  }

  // Descargar CSV
  const url = `/facturas/export/csv${params.toString() ? '?' + params.toString() : ''}`;
  window.location.href = apiClient.defaults.baseURL + url;
};
```

#### 4. Conectar botón de exportar:

Busca los botones de "Exportar" (hay 2, uno para admin y otro para responsable) y cambia:

**❌ ANTES:**
```typescript
<Button
  ...
  // SIN onClick
>
  Exportar
</Button>
```

**✅ DESPUÉS:**
```typescript
<Button
  ...
  onClick={handleExport}  // ✅ Agregar esta línea
>
  Exportar
</Button>
```

---

## 🎯 Resultado Esperado

Después de aplicar los cambios:

1. ✅ El dashboard cargará correctamente
2. ✅ Se mostrarán TODAS las facturas (hasta 2000 por carga)
3. ✅ El contador mostrará el total real de facturas
4. ✅ El botón "Exportar" descargará CSV completo

---

## 🧪 Cómo Verificar

1. Recarga el navegador (Ctrl + Shift + R)
2. Abre la consola del navegador (F12)
3. Verifica que no haya errores
4. Confirma que se muestran las facturas correctamente
5. Prueba el botón "Exportar"

---

## 📝 Archivos de Referencia

Si necesitas más detalles, revisa:
- Backend: `/app/api/v1/routers/facturas.py` (línea 186-290)
- Schemas: `/app/schemas/common.py` (línea 16-58)
- Documentación: `SOLUCION_PAGINACION_EMPRESARIAL.md`
