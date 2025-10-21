# PLAN DE LIMPIEZA Y PROFESIONALIZACIÓN DEL CÓDIGO

**Proyecto:** AFE Backend
**Fecha:** 2025-10-21
**Equipo:** Desarrollo Senior
**Prioridad:** ALTA

---

## PROBLEMAS IDENTIFICADOS

### 1. Error en Asignación Masiva
**Síntoma:** "No se pudo realizar ninguna asignación. Verifique los datos"
**Causa:** El endpoint `/bulk` no está manejando correctamente los errores
**Impacto:** Usuarios no pueden crear asignaciones masivas

### 2. Warnings de aria-hidden en Frontend
**Síntoma:** Múltiples warnings en consola del navegador
**Causa:** Elementos con aria-hidden contienen elementos focuseables
**Impacto:** Accesibilidad comprometida, mala experiencia de desarrollo

### 3. Emojis en Código de Producción
**Síntoma:** Emojis en logs y comentarios
**Causa:** Falta de estándares de código profesional
**Impacto:** No es aceptable en entorno empresarial

---

## SOLUCIONES

### Solución 1: Refactor Endpoint BULK

**Archivo:** `app/api/v1/routers/asignacion_nit.py`

**Problemas actuales:**
1. Emojis en comentarios y logs
2. Manejo de errores deficiente
3. Falta try-catch global
4. No hay rollback en caso de error crítico

**Código limpio (sin emojis):**

```python
@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def crear_asignaciones_bulk(
    payload: AsignacionBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable)
):
    """
    Asigna múltiples NITs a un responsable.

    Args:
        payload: Lista de NITs a asignar
        db: Sesión de base de datos
        current_user: Usuario autenticado

    Returns:
        dict: Estadísticas de la operación

    Raises:
        HTTPException: Si el responsable no existe o error crítico
    """
    # Verificar responsable
    responsable = db.query(Responsable).filter(
        Responsable.id == payload.responsable_id
    ).first()

    if not responsable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Responsable ID {payload.responsable_id} no encontrado"
        )

    creadas = 0
    reactivadas = 0
    omitidas = 0
    errores = []

    try:
        for nit_item in payload.nits:
            try:
                # Verificar asignación activa
                existente_activa = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == nit_item.nit,
                    AsignacionNitResponsable.responsable_id == payload.responsable_id,
                    AsignacionNitResponsable.activo == True
                ).first()

                if existente_activa:
                    omitidas += 1
                    continue

                # Verificar asignación inactiva
                existente_inactiva = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == nit_item.nit,
                    AsignacionNitResponsable.responsable_id == payload.responsable_id,
                    AsignacionNitResponsable.activo == False
                ).first()

                if existente_inactiva:
                    # Reactivar
                    existente_inactiva.activo = True
                    existente_inactiva.actualizado_en = datetime.now()
                    existente_inactiva.actualizado_por = current_user.usuario
                    existente_inactiva.nombre_proveedor = nit_item.nombre_proveedor
                    existente_inactiva.area = nit_item.area or responsable.area
                    existente_inactiva.permitir_aprobacion_automatica = payload.permitir_aprobacion_automatica

                    sincronizar_facturas_por_nit(db, nit_item.nit, payload.responsable_id)
                    reactivadas += 1
                else:
                    # Crear nueva
                    nueva = AsignacionNitResponsable(
                        nit=nit_item.nit,
                        nombre_proveedor=nit_item.nombre_proveedor,
                        responsable_id=payload.responsable_id,
                        area=nit_item.area or responsable.area,
                        permitir_aprobacion_automatica=payload.permitir_aprobacion_automatica,
                        requiere_revision_siempre=False,
                        activo=True,
                        creado_por=current_user.usuario
                    )
                    db.add(nueva)
                    sincronizar_facturas_por_nit(db, nit_item.nit, payload.responsable_id)
                    creadas += 1

            except Exception as e:
                error_msg = f"NIT {nit_item.nit}: {str(e)}"
                errores.append(error_msg)
                logger.error(f"Error procesando: {error_msg}")

        # Commit transacción
        db.commit()

        # Logging profesional (sin emojis)
        if errores:
            logger.warning(f"Bulk completado con {len(errores)} errores")
        else:
            logger.info(
                f"Bulk exitoso: {creadas} creadas, "
                f"{reactivadas} reactivadas, {omitidas} omitidas"
            )

    except Exception as e:
        db.rollback()
        logger.error(f"Error critico en bulk: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en operacion masiva: {str(e)}"
        )

    # Mensaje informativo
    mensaje_partes = []
    if creadas > 0:
        mensaje_partes.append(f"{creadas} creadas")
    if reactivadas > 0:
        mensaje_partes.append(f"{reactivadas} reactivadas")
    if omitidas > 0:
        mensaje_partes.append(f"{omitidas} omitidas")
    if errores:
        mensaje_partes.append(f"{len(errores)} errores")

    mensaje = " | ".join(mensaje_partes) if mensaje_partes else "Sin cambios"

    return {
        "total_procesados": len(payload.nits),
        "creadas": creadas,
        "reactivadas": reactivadas,
        "omitidas": omitidas,
        "errores": errores,
        "mensaje": mensaje,
        "success": True
    }
```

**Cambios clave:**
- Sin emojis
- Try-catch global con rollback
- Logging profesional
- Documentación clara
- Campo `success: True` agregado

---

### Solución 2: Limpiar Todos los Emojis

**Script de búsqueda y reemplazo:**

```bash
# Buscar todos los emojis en el código
grep -r " \|\|\|→\|\|📊" app/ --include="*.py"

# Reemplazos necesarios:
  → (eliminar o reemplazar con OK)
 → (eliminar o reemplazar con ERROR)
 → (eliminar o reemplazar con WARNING)
→ → ->
 → (eliminar)
→ (eliminar)
```

**Archivos a limpiar:**
1. `app/api/v1/routers/asignacion_nit.py`
2. `app/services/*.py` (si los hay)
3. Tests (pueden mantener emojis en asserts para legibilidad)

---

### Solución 3: Corregir Warnings de Frontend

**Problema:** Elementos con `aria-hidden="true"` contienen elementos focuseables

**Solución:** (Este es un problema del frontend, no del backend)

Si el frontend está en React/Vue/etc., agregar a los elementos afectados:

```jsx
// ANTES
<div aria-hidden="true">
  <button>Click me</button>  {/* ERROR: botón focuseable */}
</div>

// DESPUÉS
<div aria-hidden="true">
  <button tabIndex={-1}>Click me</button>  {/* OK: no focuseable */}
</div>
```

O mejor, no usar `aria-hidden` en contenedores con elementos interactivos.

---

## PLAN DE IMPLEMENTACIÓN

### Fase 1: Emergencia (HOY)
- [ ] Corregir endpoint `/bulk` con código profesional
- [ ] Eliminar emojis de logs críticos
- [ ] Agregar try-catch global

### Fase 2: Limpieza (Esta semana)
- [ ] Buscar y eliminar TODOS los emojis del backend
- [ ] Estandarizar mensajes de log
- [ ] Actualizar documentación sin emojis

### Fase 3: Prevención (Próxima semana)
- [ ] Agregar linter que rechace emojis
- [ ] Crear guía de estándares de código
- [ ] Code review obligatorio

---

## ESTÁNDARES PROFESIONALES

### DO (Hacer)
```python
# Logging profesional
logger.info("Operation completed successfully")
logger.error(f"Failed to process: {error}")
logger.warning("Threshold exceeded")

# Comentarios claros
# Process active assignments only
# Reactivate soft-deleted records

# Mensajes de error útiles
"Unable to create assignment: NIT already exists"
"Responsable ID 123 not found"
```

### DON'T (No hacer)
```python
# NO usar emojis
logger.info("Operation completed successfully  ")  # MAL
logger.error("Failed to process ")  # MAL

# NO usar jerga
logger.info("Yay! It worked!")  # MAL
logger.error("Oops, something broke")  # MAL

# NO mensajes vagos
"Error"  # MAL
"Something went wrong"  # MAL
```

---

## VERIFICACIÓN

### Checklist Post-Implementación
- [ ] Asignación masiva funciona correctamente
- [ ] No hay emojis en logs
- [ ] No hay emojis en comentarios
- [ ] Try-catch en todos los endpoints críticos
- [ ] Mensajes de error informativos
- [ ] Tests pasan
- [ ] Code review aprobado

### Comando de Verificación
```bash
# Verificar que no hay emojis
grep -r "[^\x00-\x7F]" app/ --include="*.py" | grep -v "tests/" | grep -v ".pyc"

# Debería retornar 0 resultados (o solo strings legítimos como nombres)
```

---

## RESPONSABLES

- **Backend Lead:** Implementar correcciones
- **QA:** Verificar asignación masiva
- **Tech Lead:** Code review
- **DevOps:** Deploy en staging

---

**Prioridad:** ALTA
**Deadline:** HOY (problema crítico de usuario)
**Status:** PENDIENTE DE IMPLEMENTACIÓN

