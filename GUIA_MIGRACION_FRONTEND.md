# 🎨 Guía de Migración para Frontend

**Para**: Equipo de Frontend
**De**: Backend Team
**Fecha**: Octubre 19, 2025
**Prioridad**: Alta
**Tiempo estimado**: 2-4 horas

---

## 📋 Resumen de Cambios

El backend eliminó la tabla `responsable_proveedor` y ahora usa **SOLO** `asignacion_nit_responsable`.

**Esto requiere actualizar los endpoints del frontend.**

---

## 🔄 Endpoints Migrados

### **ANTES (❌ Deprecated)**
```
/api/v1/responsable-proveedor/*
```

### **AHORA (✅ Usar estos)**
```
/api/v1/asignacion-nit/*
```

---

## 📝 Cambios Detallados por Endpoint

### **1. Listar Asignaciones**

#### ❌ ANTES
```typescript
GET /api/v1/responsable-proveedor/
Query params: ?responsable_id=5&proveedor_id=10&activo=true

Response: [
  {
    id: 1,
    responsable_id: 5,
    proveedor_id: 10,
    activo: true,
    creado_en: "2025-10-19T10:00:00"
  }
]
```

#### ✅ AHORA
```typescript
GET /api/v1/asignacion-nit/
Query params: ?responsable_id=5&nit=900156470-3&activo=true

Response: [
  {
    id: 1,
    nit: "900156470-3",
    nombre_proveedor: "Almera Information Management",
    responsable_id: 5,
    responsable_nombre: "Alex",
    area: "TI",
    permitir_aprobacion_automatica: true,
    requiere_revision_siempre: false,
    activo: true
  }
]
```

**Cambios clave:**
- `proveedor_id` → `nit` (filtro por NIT en lugar de ID)
- Se incluye `nombre_proveedor` y `responsable_nombre` automáticamente
- Nuevos campos de configuración de workflow

---

### **2. Crear Asignación**

#### ❌ ANTES
```typescript
POST /api/v1/responsable-proveedor/
Body: {
  responsable_id: 5,
  proveedor_id: 10,
  activo: true
}
```

#### ✅ AHORA
```typescript
POST /api/v1/asignacion-nit/
Body: {
  nit: "900156470-3",
  responsable_id: 5,
  nombre_proveedor: "Almera Information Management", // Opcional
  area: "TI", // Opcional
  permitir_aprobacion_automatica: true, // Default: true
  requiere_revision_siempre: false // Default: false
}
```

**Cambios clave:**
- Usar `nit` en lugar de `proveedor_id`
- `nombre_proveedor` es opcional (se puede obtener del proveedor)
- Nuevos campos opcionales para configuración

---

### **3. Actualizar Asignación**

#### ❌ ANTES
```typescript
PUT /api/v1/responsable-proveedor/{id}
Body: {
  responsable_id: 6,
  activo: true
}
```

#### ✅ AHORA
```typescript
PUT /api/v1/asignacion-nit/{id}
Body: {
  responsable_id: 6, // Opcional
  nombre_proveedor: "Nuevo Nombre", // Opcional
  area: "Operaciones", // Opcional
  permitir_aprobacion_automatica: false, // Opcional
  requiere_revision_siempre: true, // Opcional
  activo: true // Opcional
}
```

**Cambios clave:**
- Todos los campos son opcionales (solo envía lo que cambia)
- Automáticamente sincroniza facturas si cambia el responsable

---

### **4. Eliminar Asignación**

#### ❌ ANTES
```typescript
DELETE /api/v1/responsable-proveedor/{id}
```

#### ✅ AHORA
```typescript
DELETE /api/v1/asignacion-nit/{id}
// Marca como inactiva, no elimina físicamente
```

**Sin cambios en el comportamiento.**

---

### **5. NUEVO: Asignación Masiva**

#### ✅ NUEVO ENDPOINT
```typescript
POST /api/v1/asignacion-nit/bulk
Body: {
  responsable_id: 5,
  nits: [
    "900156470-3",
    "800242106-2",
    "900399741-7"
  ],
  area: "TI" // Opcional
}

Response: {
  creadas: 2,
  actualizadas: 1,
  errores: [],
  total_procesados: 3
}
```

**Uso:** Asignar múltiples NITs a un responsable de una sola vez.

---

### **6. NUEVO: Asignaciones por Responsable**

#### ✅ NUEVO ENDPOINT
```typescript
GET /api/v1/asignacion-nit/por-responsable/{responsable_id}
Query params: ?activo=true

Response: [
  {
    id: 1,
    nit: "900156470-3",
    nombre_proveedor: "Almera",
    responsable_id: 5,
    responsable_nombre: "Alex",
    ...
  }
]
```

**Uso:** Obtener todas las asignaciones de un responsable.

---

## 🔧 Actualización de Modelos TypeScript

### **Modelo Antiguo (❌ Eliminar)**
```typescript
interface AsignacionResponsableProveedor {
  id: number;
  responsable_id: number;
  proveedor_id: number;
  activo: boolean;
  creado_en: string;
}
```

### **Modelo Nuevo (✅ Usar)**
```typescript
interface AsignacionNIT {
  id: number;
  nit: string;
  nombre_proveedor: string | null;
  responsable_id: number;
  responsable_nombre: string | null;
  area: string | null;
  permitir_aprobacion_automatica: boolean;
  requiere_revision_siempre: boolean;
  activo: boolean;
}
```

---

## 📦 Actualización de Servicios

### **Archivo:** `src/services/asignacionNitService.ts` (NUEVO)

```typescript
import api from './api';
import { AsignacionNIT } from '../types';

export const asignacionNitService = {
  /**
   * Listar todas las asignaciones NIT
   */
  listar: async (params?: {
    responsable_id?: number;
    nit?: string;
    activo?: boolean;
  }): Promise<AsignacionNIT[]> => {
    const response = await api.get('/asignacion-nit/', { params });
    return response.data;
  },

  /**
   * Crear nueva asignación NIT
   */
  crear: async (data: {
    nit: string;
    responsable_id: number;
    nombre_proveedor?: string;
    area?: string;
    permitir_aprobacion_automatica?: boolean;
    requiere_revision_siempre?: boolean;
  }): Promise<AsignacionNIT> => {
    const response = await api.post('/asignacion-nit/', data);
    return response.data;
  },

  /**
   * Actualizar asignación existente
   */
  actualizar: async (id: number, data: Partial<AsignacionNIT>): Promise<AsignacionNIT> => {
    const response = await api.put(`/asignacion-nit/${id}`, data);
    return response.data;
  },

  /**
   * Eliminar asignación
   */
  eliminar: async (id: number): Promise<void> => {
    await api.delete(`/asignacion-nit/${id}`);
  },

  /**
   * Asignación masiva de NITs
   */
  asignarBulk: async (data: {
    responsable_id: number;
    nits: string[];
    area?: string;
  }): Promise<{
    creadas: number;
    actualizadas: number;
    errores: any[];
    total_procesados: number;
  }> => {
    const response = await api.post('/asignacion-nit/bulk', data);
    return response.data;
  },

  /**
   * Obtener asignaciones de un responsable
   */
  porResponsable: async (responsable_id: number, activo = true): Promise<AsignacionNIT[]> => {
    const response = await api.get(`/asignacion-nit/por-responsable/${responsable_id}`, {
      params: { activo }
    });
    return response.data;
  }
};
```

---

## 🎨 Actualización de Componentes

### **Ejemplo: Componente de Asignación**

```typescript
// ❌ ANTES
const AsignacionComponent = () => {
  const [asignaciones, setAsignaciones] = useState<AsignacionResponsableProveedor[]>([]);

  useEffect(() => {
    fetch('/api/v1/responsable-proveedor/')
      .then(res => res.json())
      .then(data => setAsignaciones(data));
  }, []);

  return (
    <div>
      {asignaciones.map(asig => (
        <div key={asig.id}>
          Responsable: {asig.responsable_id}, Proveedor: {asig.proveedor_id}
        </div>
      ))}
    </div>
  );
};
```

```typescript
// ✅ AHORA
import { asignacionNitService } from '../services/asignacionNitService';

const AsignacionComponent = () => {
  const [asignaciones, setAsignaciones] = useState<AsignacionNIT[]>([]);

  useEffect(() => {
    asignacionNitService.listar()
      .then(data => setAsignaciones(data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div>
      {asignaciones.map(asig => (
        <div key={asig.id}>
          <strong>NIT:</strong> {asig.nit} <br />
          <strong>Proveedor:</strong> {asig.nombre_proveedor || 'N/A'} <br />
          <strong>Responsable:</strong> {asig.responsable_nombre || `ID: ${asig.responsable_id}`}
        </div>
      ))}
    </div>
  );
};
```

---

## ✅ Checklist de Migración

### **Fase 1: Preparación**
- [ ] Crear nuevo servicio `asignacionNitService.ts`
- [ ] Crear nueva interfaz `AsignacionNIT`
- [ ] Revisar todos los componentes que usan `/responsable-proveedor/`

### **Fase 2: Actualización**
- [ ] Reemplazar llamadas a `/responsable-proveedor/` por `/asignacion-nit/`
- [ ] Actualizar modelos de datos
- [ ] Actualizar componentes que muestran asignaciones
- [ ] Actualizar formularios de creación/edición

### **Fase 3: Testing**
- [ ] Probar listar asignaciones
- [ ] Probar crear asignación
- [ ] Probar actualizar asignación
- [ ] Probar eliminar asignación
- [ ] Probar asignación masiva (nuevo)
- [ ] Probar filtros por responsable

### **Fase 4: Limpieza**
- [ ] Eliminar servicio antiguo `responsableProveedorService.ts`
- [ ] Eliminar interfaz antigua `AsignacionResponsableProveedor`
- [ ] Eliminar imports no usados
- [ ] Validar que no quedan referencias al endpoint antiguo

---

## 🚨 Advertencias Importantes

### **1. NITs vs IDs de Proveedor**
- El nuevo sistema usa **NITs** en lugar de **IDs de proveedor**
- Esto es más flexible: un NIT puede tener múltiples proveedores
- Necesitarás obtener el NIT del proveedor antes de crear asignaciones

### **2. Sincronización Automática**
- Al crear/actualizar asignaciones, **las facturas se sincronizan automáticamente**
- No necesitas sincronizar manualmente

### **3. Campos Nuevos**
- `permitir_aprobacion_automatica`: Para workflows automáticos (futuro)
- `requiere_revision_siempre`: Para forzar revisión manual

---

## 📞 Soporte

Si tienes dudas durante la migración:

1. **Documentación Backend**:
   - `ARQUITECTURA_UNIFICACION_RESPONSABLES.md`
   - `ELIMINACION_COMPLETADA.md`
   - `PLAN_ELIMINACION_RESPONSABLE_PROVEEDOR.md`

2. **Endpoint de Prueba**:
   ```bash
   curl http://localhost:8000/api/v1/asignacion-nit/
   ```

3. **Swagger Docs**:
   ```
   http://localhost:8000/docs
   ```

---

## 🎯 Resultado Esperado

Después de esta migración:
- ✅ Frontend usa nuevos endpoints `/asignacion-nit/*`
- ✅ Asignaciones por NIT (más flexible)
- ✅ Información enriquecida (nombres de responsable y proveedor)
- ✅ Soporte para workflows automáticos (futuro)
- ✅ Código más limpio y mantenible

---

**¡Buena suerte con la migración! 🚀**
