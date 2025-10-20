# Scripts Deprecated

Esta carpeta contiene scripts obsoletos que fueron reemplazados por el nuevo sistema unificado.

---

## Scripts Deprecados (Octubre 19, 2025)

### **Sistema Antiguo: Scripts para `responsable_proveedor`**

1. **`sincronizar_asignaciones_responsables.py`**
   - **Reemplazado por**: Los datos ya fueron migrados con `migrar_asignaciones_a_nit_responsable.py`
   - **Razon**: Ya no existe la tabla `responsable_proveedor` para sincronizar
   - **Nuevo proceso**: Todas las asignaciones ahora se hacen directamente en `asignacion_nit_responsable`

2. **`asignar_responsables_proveedores.py`**
   - **Reemplazado por**: Endpoints en `/api/v1/asignacion-nit/`
   - **Razon**: Ya no existe la tabla `responsable_proveedor`
   - **Nuevo proceso**: Usar el endpoint POST `/api/v1/asignacion-nit/bulk` para asignaciones masivas

---

## Scripts Activos

### **Sistema Nuevo: Scripts para `asignacion_nit_responsable`**

Ver la carpeta principal `scripts/` para los scripts activos:

1. **`migrar_asignaciones_a_nit_responsable.py`**
   - Migra datos de la tabla antigua a la nueva (ya ejecutado)

2. **`resincronizar_responsables_facturas.py`**
   - Sincroniza facturas con responsables basado en asignaciones NIT

3. **`validacion_pre_migracion.py`**
   - Valida el estado del sistema antes de eliminar la tabla antigua

4. **`listar_responsables_y_asignaciones.py`**
   - Lista responsables y sus asignaciones NIT actuales

5. **`fix_aprobado_rechazado_por.py`**
   - Corrige datos historicos donde IDs estaban en lugar de nombres

---

## Importante

**NO ejecutes estos scripts** - estan aqui solo como referencia historica.

Para nuevas asignaciones, usa:
- **UI**: Panel de administracion de asignaciones NIT
- **API**: POST `/api/v1/asignacion-nit/bulk`
- **Script**: `resincronizar_responsables_facturas.py` para sincronizar facturas

---

**Fecha de deprecacion**: Octubre 19, 2025
**Sistema actual**: `asignacion_nit_responsable`
