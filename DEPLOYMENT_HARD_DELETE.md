# Deployment: Hard Delete Pattern para AsignacionNitResponsable

## Resumen del Cambio

Se ha cambiado de **SOFT DELETE** a **HARD DELETE** para las eliminaciones de asignaciones NIT-Responsable.

- **Antes**: Se marcaba `activo = FALSE` (quedaba registro "fantasma" en BD)
- **Ahora**: Se elimina completamente el registro de la BD

## Pasos de Deployment

### PASO 1: Actualizar el Código
```bash
git pull origin main  # O deploy normal de tu CI/CD
```

Este pull incluye:
- `app/api/v1/routers/asignacion_nit.py` - Nuevo comportamiento hard delete
- `scripts/limpiar_asignaciones_inactivas.py` - Script para limpiar datos históricos

### PASO 2: Limpiar Registros Inactivos (OPCIONAL pero RECOMENDADO)

Si tienes registros viejos con `activo = FALSE`:

```bash
# Contar cuántos hay
SELECT COUNT(*) FROM asignacion_nit_responsable WHERE activo = FALSE;

# Limpiar (requiere confirmación interactiva)
python scripts/limpiar_asignaciones_inactivas.py
```

**O hacerlo directamente en BD:**
```sql
DELETE FROM asignacion_nit_responsable WHERE activo = FALSE;
```

### PASO 3: Reiniciar la Aplicación

Si está en local:
```bash
# Ctrl+C para detener FastAPI
# Luego reiniciar:
python -m uvicorn app.main:app --reload
```

Si está en servidor/Docker:
```bash
docker-compose restart  # O tu comando de restart
```

### PASO 4: Verificar

```bash
# 1. Verificar que no hay registros con activo=FALSE
SELECT * FROM asignacion_nit_responsable WHERE activo = FALSE;
# Resultado: 0 filas

# 2. Verificar que la tabla está limpia
SELECT COUNT(*) FROM asignacion_nit_responsable;
# Resultado: solo registros activos

# 3. Probar endpoint DELETE
DELETE /asignacion-nit/77  # Prueba con un ID

# 4. Verificar que se eliminó completamente
SELECT * FROM asignacion_nit_responsable WHERE id = 77;
# Resultado: 0 filas
```

## Cambios de API

### Endpoint DELETE: Ahora HARD DELETE
```
DELETE /asignacion-nit/{id}
Status: 204 NO_CONTENT

ANTES: Marcaba activo = FALSE (registro seguía en BD)
AHORA: Elimina completamente el registro (no hay vuelta atrás)
```

### Endpoint POST /restore: ELIMINADO
```
ANTES: POST /asignacion-nit/{id}/restore -> reactivaba
AHORA: No existe este endpoint

Si necesitas reasignar un NIT:
POST /asignacion-nit/
{
  "nit": "800185449",
  "responsable_id": 1,
  ...
}
```

### Endpoint GET: SIMPLIFICADO
```
ANTES:
GET /asignacion-nit/?activo=true
GET /asignacion-nit/?incluir_inactivos=true

AHORA:
GET /asignacion-nit/  # Solo activas (sin parámetros)
GET /asignacion-nit/?responsable_id=1
GET /asignacion-nit/?nit=800185449
```

## Impacto en Frontend

El frontend probablemente necesita cambios:

1. **Remover referencias a `/restore` endpoint**
   ```typescript
   // ANTES
   await api.restaurarAsignacion(id)  // ❌ Ya no existe
   
   // AHORA
   // No hacer nada, el usuario debe crear una nueva asignación
   ```

2. **Remover parámetros `activo` e `incluir_inactivos` de GET**
   ```typescript
   // ANTES
   getAsignaciones({ incluir_inactivos: true })
   
   // AHORA
   getAsignaciones()  // Solo retorna activas
   ```

3. **Actualizar interfaz de usuario**
   - No mostrar "Restaurar" option
   - En lugar de eso, mostrar "Reasignar" (crear nueva)
   - Mensaje claro: "Para reasignar este NIT, cree una nueva asignación"

## Datos Históricos

Los registros con `activo = FALSE` son datos de transacciones pasadas.

**Opciones:**
1. **Limpiarlos** (recomendado): `python scripts/limpiar_asignaciones_inactivas.py`
2. **Dejarlos** (no afecta): La aplicación no los ve, pero ocupan espacio en BD
3. **Archivarlos**: Si necesitas auditoría, antes de limpiar puedes hacer:
   ```sql
   -- Crear tabla de archivo
   CREATE TABLE asignacion_nit_responsable_archive AS
   SELECT * FROM asignacion_nit_responsable WHERE activo = FALSE;
   
   -- Luego limpiar
   DELETE FROM asignacion_nit_responsable WHERE activo = FALSE;
   ```

## FAQ

**P: ¿Qué pasa si elimino una asignación por error?**
A: No se puede deshacer. El usuario debe crear una nueva asignación.

**P: ¿Los registros históricos desaparecen?**
A: Sí. Con hard delete no hay auditoría nativa. Si necesitas historial, considera agregar tabla `asignacion_nit_responsable_audit`.

**P: ¿Esto afecta las facturas?**
A: No. Las facturas se desasignan (responsable_id = NULL) pero no se eliminan. Los proveedores NUNCA se tocan.

**P: ¿Puedo reasignar el mismo NIT después de borrarlo?**
A: Sí. El NIT queda libre para asignar a otro responsable.

## Rollback

Si necesitas volver a soft delete:

```bash
git revert 5fafd3a  # Revert del commit hard delete
git revert a089271  # Revert del cleanup script
# Redeploy
```

Pero esto es complejo. Mejor mantener hard delete.

---

**Creado**: 2025-10-27
**Commit**: 5fafd3a y a089271
**Autor**: Claude Code
