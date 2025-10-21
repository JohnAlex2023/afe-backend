# 🗑️ Archivos Deprecated

Esta carpeta contiene archivos obsoletos que fueron reemplazados por la nueva arquitectura unificada.

---

##  Archivos Deprecados (Octubre 19, 2025)

### **Sistema Antiguo: `responsable_proveedor`**

Los siguientes archivos fueron reemplazados por el nuevo sistema `asignacion_nit_responsable`:

1. **`responsable_proveedor.py`** (Modelo)
   - **Reemplazado por**: `app/models/workflow_aprobacion.py::AsignacionNitResponsable`
   - **Razón**: Duplicación de datos, asignación por proveedor_id en lugar de NIT

2. **`responsable_proveedor.py`** (CRUD)
   - **Reemplazado por**: Lógica integrada en `app/crud/factura.py`
   - **Razón**: Simplificación, usa directamente `AsignacionNitResponsable`

3. **`responsable_proveedor_service.py`** (Servicio)
   - **Reemplazado por**: Lógica en nuevo router `app/api/v1/routers/asignacion_nit.py`
   - **Razón**: Consolidación de lógica de negocio

4. **`responsable_proveedor.py`** (Router)
   - **Reemplazado por**: `app/api/v1/routers/asignacion_nit.py`
   - **Nuevos endpoints**: `/api/v1/asignacion-nit/*`
   - **Razón**: API más limpia y moderna

---

##   Nueva Arquitectura

### **Sistema Unificado: `asignacion_nit_responsable`**

**Modelo**: `app/models/workflow_aprobacion.py::AsignacionNitResponsable`

**Ventajas**:
-   Una sola fuente de verdad
-   Asignación por NIT (más flexible)
-   Configuración de workflows automáticos
-   Sin duplicación de datos

**Endpoints**:
- `GET /api/v1/asignacion-nit/` - Listar asignaciones
- `POST /api/v1/asignacion-nit/` - Crear asignación
- `PUT /api/v1/asignacion-nit/{id}` - Actualizar asignación
- `DELETE /api/v1/asignacion-nit/{id}` - Eliminar asignación
- `POST /api/v1/asignacion-nit/bulk` - Asignación masiva

---

## 📖 Documentación

Ver: `ARQUITECTURA_UNIFICACION_RESPONSABLES.md` en la raíz del proyecto.

---

##  IMPORTANTE

**NO elimines estos archivos** hasta confirmar que:
1.   La migración de base de datos se ejecutó correctamente
2.   Todos los tests pasan
3.   El frontend fue actualizado para usar los nuevos endpoints
4.   El sistema funciona en producción por al menos 1 mes

Después de ese período, estos archivos pueden ser eliminados permanentemente.
