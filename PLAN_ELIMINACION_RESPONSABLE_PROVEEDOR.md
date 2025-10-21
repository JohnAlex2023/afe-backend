# 🗑️ Plan de Eliminación Completa: `responsable_proveedor`

**Fecha**: Octubre 19, 2025
**Objetivo**: Eliminar completamente la tabla `responsable_proveedor` y migrar todo a `asignacion_nit_responsable`

---

##  Archivos Afectados (13 archivos)

### **Categoría 1: Modelos y CRUD** (Eliminar completamente)
1.   `app/models/responsable_proveedor.py` - **ELIMINAR**
2.   `app/crud/responsable_proveedor.py` - **ELIMINAR**
3.   `app/services/responsable_proveedor_service.py` - **ELIMINAR**

### **Categoría 2: Routers API** (Reescribir)
4.  `app/api/v1/routers/responsable_proveedor.py` - **RENOMBRAR** a `asignacion_nit.py` y reescribir
5.  `app/api/v1/routers/responsables.py` - **ACTUALIZAR** endpoints

### **Categoría 3: Schemas** (Actualizar)
6.  `app/schemas/responsable.py` - **ELIMINAR** schemas de ResponsableProveedor

### **Categoría 4: Servicios** (Actualizar)
7.  `app/services/export_service.py` - **ACTUALIZAR** si usa ResponsableProveedor

### **Categoría 5: Scripts** (Marcar como obsoletos)
8.  `scripts/asignar_responsables_proveedores.py` - **OBSOLETO** (marcar)
9.  `scripts/sincronizar_asignaciones_responsables.py` - **OBSOLETO** (marcar)
10. ℹ️ `scripts/migrar_asignaciones_a_nit_responsable.py` - **MANTENER** (histórico)
11. ℹ️ `scripts/listar_responsables_y_asignaciones.py` - **ACTUALIZAR** (remover parte de ResponsableProveedor)

### **Categoría 6: Init y Documentación**
12.  `app/models/__init__.py` - **ELIMINAR** import de ResponsableProveedor
13. ℹ️ `ARQUITECTURA_UNIFICACION_RESPONSABLES.md` - **YA ACTUALIZADO**

---

##  Estrategia de Migración

### **Fase 1: Preparación**   COMPLETADA
- [x] Migrar datos a `asignacion_nit_responsable`
- [x] Actualizar CRUD de facturas
- [x] Documentar cambio

### **Fase 2: Actualización de APIs** (AHORA)
- [ ] Reescribir router `responsable_proveedor.py` → `asignacion_nit.py`
- [ ] Actualizar `responsables.py` router
- [ ] Actualizar schemas
- [ ] Actualizar servicios

### **Fase 3: Limpieza de Código**
- [ ] Eliminar modelos obsoletos
- [ ] Eliminar CRUD obsoleto
- [ ] Eliminar servicios obsoletos
- [ ] Actualizar `__init__.py`

### **Fase 4: Migración de Base de Datos**
- [ ] Crear migración Alembic para `DROP TABLE responsable_proveedor`
- [ ] Ejecutar migración en desarrollo
- [ ] Validar que todo funciona

### **Fase 5: Frontend** (Coordinación necesaria)
- [ ] Actualizar endpoints del frontend
- [ ] Cambiar de `/responsable-proveedor` a `/asignacion-nit`
- [ ] Probar interfaz de asignaciones

---

##  Acción Inmediata

Voy a crear los nuevos archivos y actualizar los existentes.

