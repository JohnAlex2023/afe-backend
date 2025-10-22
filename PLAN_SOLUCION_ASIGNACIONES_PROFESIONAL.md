# PLAN DE SOLUCIÓN PROFESIONAL: ASIGNACIONES NIT Y SINCRONIZACIÓN

**Nivel:** Enterprise / Fortune 500
**Fecha:** 2025-10-22
**Responsable:** Senior Development Team
**Status:** EN DESARROLLO

---

## RESUMEN EJECUTIVO

Hemos identificado **3 problemas críticos** en el ciclo de vida de asignaciones NIT:

1. **Problema UI/Frontend:** Bulk assign by text (comma-separated) falla
2. **Problema Arquitectónico:** Reasignación incompleta cuando cambio responsable
3. **Problema de Integridad:** Facturas huérfanas cuando elimino asignación

**Solución:** 3 fases integradas que arreglan TODO sin romper funcionalidad existente

---

## PROBLEMA 1: BULK ASSIGN BY TEXT FALLA

### Síntoma
```
Usuario pega: "17343874, 47425554, 80818383, ..."
Sistema muestra: "Ninguno de los NITs ingresados está registrado como proveedor"
Pero: Si selecciono del dropdown ✓ FUNCIONA
```

### Raíz Causa
**Archivo:** `afe_frontend/src/features/proveedores/tabs/AsignacionesTab.tsx`
**Línea:** 171-221 (función `handleBulkSubmit()`)
**Problema:** Race condition en actualización de estados React

```typescript
// MALO: setTimeout recursivo causa que se ejecute antes de actualizar estado
if (hasPendingInput) {
    // ... procesa input
    setBulkProveedores(nitsUnicos);  // ← ASINCRÓNICO
    setHasPendingInput(false);       // ← ASINCRÓNICO

    // ❌ Ejecuta ANTES de que actualicen los estados
    setTimeout(() => handleBulkSubmit(), 50);
}
```

### Solución (FASE 1)

**Eliminar lógica recursiva con setTimeout**

```typescript
const handleBulkSubmit = async () => {
    // PRIMERO: Procesar cualquier input pendiente
    if (hasPendingInput) {
        const autocompleteInput = document.querySelector<HTMLInputElement>(
            'input[placeholder*="NITs separados por coma"]'
        );

        if (autocompleteInput?.value.trim()) {
            const inputValue = autocompleteInput.value.trim();

            // Separar y validar NITs
            const nits = inputValue.split(',').map(n => n.trim()).filter(n => n);

            const nitsValidos: string[] = [];
            const nitsNoEncontrados: string[] = [];

            nits.forEach(nit => {
                if (proveedores.some(p => p.nit === nit)) {
                    nitsValidos.push(nit);
                } else {
                    nitsNoEncontrados.push(nit);
                }
            });

            // Si NO hay válidos, mostrar error y salir
            if (nitsValidos.length === 0) {
                setBulkDialogError('Ninguno de los NITs ingresados está registrado.');
                setHasPendingInput(false);
                autocompleteInput.value = '';
                return;
            }

            // Agregar a lista (sin duplicados)
            const nitsUnicos = [...new Set([...bulkProveedores, ...nitsValidos])];

            // Guardar rechazados
            const rechazadosUnicos = [...new Set([...bulkNitsRechazados, ...nitsNoEncontrados])];

            // Actualizar estados (todo de una vez)
            setBulkProveedores(nitsUnicos);
            setBulkNitsRechazados(rechazadosUnicos);
            setHasPendingInput(false);

            // Limpiar input
            autocompleteInput.value = '';

            // ✅ NO recursionar - dejar que el usuario presione "Asignar NITs"
            return;
        }
    }

    // Resto de validaciones (responsable, etc)
    if (!bulkResponsableId) {
        setBulkDialogError('Debe seleccionar un responsable');
        return;
    }

    if (bulkProveedores.length === 0) {
        setBulkDialogError('Debe seleccionar al menos un NIT válido');
        return;
    }

    // ✅ AQUÍ es cuando se envía al backend
    try {
        const response = await asignacionNitService.asignarMultiplesNits({
            nits: bulkProveedores,
            responsable_id: bulkResponsableId
        });

        // Success
        setOpenBulkDialog(false);
        setBulkProveedores([]);
        // Refresh lista
    } catch (error) {
        setBulkDialogError(error.message);
    }
};
```

**Cambios clave:**
- ❌ Eliminar `setTimeout(() => handleBulkSubmit(), 50)`
- ❌ Eliminar recursión
- ✅ Procesar input una sola vez al presionar Enter
- ✅ Dejar que usuario presione botón "Asignar NITs"
- ✅ Enviar al backend cuando todo está listo

---

## PROBLEMA 2: REASIGNACIÓN INCOMPLETA

### Síntoma
```
Cambio: NIT 900123456 de Alex → Maria
Resultado:
  - Facturas nuevas (sin responsable): ✅ Se asignan a Maria
  - Facturas antiguas (con Alex): ❌ Se quedan en Alex
```

### Raíz Causa
**Archivo:** `app/api/v1/routers/asignacion_nit.py`
**Línea:** 396-401 (función `actualizar_asignacion()`)
**Problema:** No pasa `responsable_anterior` a la función de sincronización

```python
# ❌ ACTUAL: Solo sincroniza facturas SIN responsable
total_facturas = sincronizar_facturas_por_nit(
    db,
    asignacion.nit,
    payload.responsable_id  # ← El NUEVO
    # FALTA: responsable_id_anterior
)
```

### Solución (FASE 2)

**Modificar funciones de sincronización para reasignar completo**

```python
def sincronizar_facturas_por_nit(
    db: Session,
    nit: str,
    responsable_id: int,
    responsable_anterior_id: Optional[int] = None  # ← NUEVO parámetro
) -> int:
    """
    Sincroniza facturas con nuevo responsable.

    Si responsable_anterior_id:
      - Actualiza facturas de responsable_anterior → responsable_id
    Si None:
      - Actualiza solo facturas sin responsable → responsable_id
    """
    proveedores = db.query(Proveedor).filter(
        Proveedor.nit.like(f'{nit}%')
    ).all()

    total_facturas = 0
    for proveedor in proveedores:
        if responsable_anterior_id is not None:
            # Reasignar facturas del responsable ANTERIOR
            facturas = db.query(Factura).filter(
                Factura.proveedor_id == proveedor.id,
                Factura.responsable_id == responsable_anterior_id  # ← DEL ANTERIOR
            ).all()
        else:
            # Solo facturas sin responsable
            facturas = db.query(Factura).filter(
                Factura.proveedor_id == proveedor.id,
                Factura.responsable_id.is_(None)
            ).all()

        for factura in facturas:
            factura.responsable_id = responsable_id
            factura.actualizado_en = datetime.now()
            total_facturas += 1

    return total_facturas


# En actualizar_asignacion() línea 378-401
if payload.responsable_id and payload.responsable_id != asignacion.responsable_id:
    responsable_anterior = asignacion.responsable_id  # ← GUARDAR EL ANTERIOR
    asignacion.responsable_id = payload.responsable_id

    # ✅ Pasar responsable_anterior para reasignar completo
    total_facturas = sincronizar_facturas_por_nit(
        db,
        asignacion.nit,
        payload.responsable_id,  # El NUEVO
        responsable_anterior_id=responsable_anterior  # ← INCLUIR
    )
```

**Cambios clave:**
- ✅ Agregar parámetro `responsable_anterior_id`
- ✅ Si se proporciona, actualizar facturas del anterior
- ✅ Si es None, comportamiento actual (solo NULL)
- ✅ Actualizar PUT endpoint para pasar responsable anterior

---

## PROBLEMA 3: FACTURAS HUÉRFANAS (sin responsable pero aprobadas)

### Síntoma
```
Elimino asignación: NIT 900123456 de Alex
Resultado:
  RESPONSABLE: (vacío)
  ACCION_POR: "Alex"
  Interpretación: ❓ ¿Sin asignar pero aprobado?
```

### Raíz Causa
Cuando elimino asignación, pongo `responsable_id = NULL` pero `accion_por` queda con el nombre de quien aprobó. Esto es técnicamente correcto (auditoría) pero confuso en UI.

### Solución (FASE 3)

**Crear campo de estado de asignación + endpoint de limpieza**

**Paso 1: Agregar campo a modelo**

```python
# app/models/factura.py
class Factura(Base):
    # Campos existentes...

    # ✨ NUEVO: Estado de asignación (para UI)
    estado_asignacion = Column(String(20), nullable=True,
        comment="Estado: asignado, huerfano, sin_asignar, requiere_reasignacion")
```

**Paso 2: Migración Alembic**

```python
# alembic/versions/xxxxx_add_estado_asignacion_field.py
def upgrade():
    op.add_column('facturas', sa.Column('estado_asignacion', sa.String(20), nullable=True))
    op.create_index('idx_facturas_estado_asignacion', 'facturas', ['estado_asignacion'])

def downgrade():
    op.drop_index('idx_facturas_estado_asignacion')
    op.drop_column('facturas', 'estado_asignacion')
```

**Paso 3: Función que calcula estado de asignación**

```python
# app/schemas/factura.py
class FacturaRead(FacturaBase):
    # Campos existentes...
    responsable_id: Optional[int]
    accion_por: Optional[str]

    # NUEVO
    estado_asignacion: Optional[str] = None

    @model_validator(mode='after')
    def compute_assignment_status(self):
        """Calcula estado de asignación para UI"""

        if self.responsable_id is not None:
            self.estado_asignacion = "asignado"
        elif self.responsable_id is None and self.accion_por is not None:
            self.estado_asignacion = "huerfano"  # Sin responsable pero aprobado
        else:
            self.estado_asignacion = "sin_asignar"

        return self
```

**Paso 4: Endpoint de limpieza (housekeeping)**

```python
# app/api/v1/routers/asignacion_nit.py
@router.post("/housekeeping/limpiar-inactivos")
def limpiar_asignaciones_inactivas(
    dias_antiguedad: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(require_role('admin'))
):
    """
    Limpia asignaciones inactivas > N días.
    Solo para admin.
    """
    from datetime import datetime, timedelta

    fecha_limite = datetime.now() - timedelta(days=dias_antiguedad)

    asignaciones_antiguas = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.activo == False,
        AsignacionNitResponsable.actualizado_en < fecha_limite
    ).all()

    count = len(asignaciones_antiguas)
    for asignacion in asignaciones_antiguas:
        db.delete(asignacion)

    db.commit()

    return {
        "mensaje": f"{count} asignaciones inactivas eliminadas permanentemente",
        "fecha_limite": fecha_limite.isoformat()
    }
```

**Cambios clave:**
- ✅ Agregar campo `estado_asignacion` (auditoría)
- ✅ Calcular en schema (no toca BD logic)
- ✅ Dashboard puede mostrar estado claro
- ✅ Endpoint de limpieza para mantenimiento

---

## FASE 4 (BONUS): LIMPIAR CÓDIGO OBSOLETO

Hay **16 referencias a código deprecated** que deben eliminarse sin romper funcionalidad:

```bash
grep -r "from app._deprecated\|from ._deprecated\|import.*_deprecated" --include="*.py"
```

**Pasos:**
1. Identificar qué archivos importan deprecated
2. Verificar que no se usan
3. Remover imports
4. Ejecutar validación: `python scripts/validate_before_commit.py`
5. Ejecutar tests
6. Commit de limpieza

---

## CRONOGRAMA DE IMPLEMENTACIÓN

### SEMANA 1: FASE 1 (Frontend - Bulk Assign Fix)

**Tiempo:** 2-3 horas

| Tarea | Archivo | Esfuerzo |
|-------|---------|----------|
| Refactorizar `handleBulkSubmit()` | AsignacionesTab.tsx | 1h |
| Remover setTimeout recursivo | AsignacionesTab.tsx | 0.5h |
| Tests del componente | AsignacionesTab.test.tsx | 1h |
| Validación manual en UI | - | 0.5h |

**Commit:** `fix: Remove race condition in bulk NIT assignment`

### SEMANA 2: FASE 2 (Backend - Reasignación Completa)

**Tiempo:** 3-4 horas

| Tarea | Archivo | Esfuerzo |
|-------|---------|----------|
| Modificar `sincronizar_facturas_por_nit()` | asignacion_nit.py | 1h |
| Actualizar PUT endpoint | asignacion_nit.py | 1h |
| Tests de reasignación | test_asignacion_*.py | 1.5h |
| Validación en BD | - | 0.5h |

**Commit:** `feat: Complete reassignment when changing responsible`

### SEMANA 3: FASE 3 (Backend - Orphan Facturas + Cleanup)

**Tiempo:** 3-4 horas

| Tarea | Archivo | Esfuerzo |
|-------|---------|----------|
| Agregar campo `estado_asignacion` | models/factura.py | 0.5h |
| Crear migración Alembic | alembic/versions/... | 0.5h |
| Actualizar schema validator | schemas/factura.py | 1h |
| Endpoint housekeeping | asignacion_nit.py | 1h |
| Tests | test_asignacion_*.py | 1h |

**Commit:** `feat: Add assignment status tracking and cleanup endpoint`

### SEMANA 4: FASE 4 (Cleanup + Testing)

**Tiempo:** 2-3 horas

| Tarea | Archivo | Esfuerzo |
|-------|---------|----------|
| Identificar deprecated imports | grep -r | 0.5h |
| Remover imports | *.py | 1h |
| Run full test suite | pytest | 1h |
| Pre-commit validation | validate_before_commit.py | 0.5h |

**Commit:** `refactor: Remove deprecated code references`

---

## VALIDACIÓN POR FASE

### FASE 1: UI Bulk Assign

```bash
# 1. Validación manual en UI
- Abrir Gestión de Proveedores
- Seleccionar responsable
- Pegar lista de NITs (comma-separated)
- Presionar Enter
- Presionar "Asignar NITs"
- Verificar: Se asignan correctamente

# 2. Ejecutar tests
pytest tests/test_asignacion_nit_sync.py -v -k "bulk"

# 3. Validación en BD
SELECT COUNT(*) FROM asignacion_nit_responsable
WHERE creado_en > NOW() - INTERVAL 1 HOUR;
# Debe mostrar número > 0
```

### FASE 2: Backend Reasignación

```bash
# 1. Test manual
- Cambiar responsable de un NIT (Alex → Maria)
- Verificar que facturas antiguas se reasignan
SELECT responsable_id FROM facturas
WHERE proveedor_id = (SELECT id FROM proveedores WHERE nit = '900123456')
# Deben mostrar ID de Maria (6)

# 2. Tests automatizados
pytest tests/test_asignacion_nit_sync.py -v -k "reassign"

# 3. Validación de sincronización
python scripts/validate_before_commit.py
# Debe mostrar: [SUCCESS] ALL VALIDATIONS PASSED
```

### FASE 3: Assignment Status

```bash
# 1. Eliminar asignación y ver estado
- DELETE asignación
- GET /facturas/all
- Verificar: estado_asignacion = "huerfano"

# 2. Tests
pytest tests/test_asignacion_nit_sync.py -v -k "orphan"

# 3. Limpieza
curl -X POST http://localhost:8000/api/v1/asignacion-nit/housekeeping/limpiar-inactivos
# Respuesta: {message: "X asignaciones inactivas eliminadas"}
```

### FASE 4: Code Cleanup

```bash
# 1. Verificar que no hay deprecated imports
grep -r "from app._deprecated\|import.*_deprecated" app/
# Resultado: (sin resultados)

# 2. Ejecutar full test suite
pytest tests/ -v

# 3. Pre-commit validation
python scripts/validate_before_commit.py
# [SUCCESS] ALL VALIDATIONS PASSED

# 4. Linting
pylint app/ --disable=C0111,C0103 --max-line-length=120
# Sin errores E, F
```

---

## DOCUMENTACIÓN QUE SE ACTUALIZARÁ

| Documento | Cambios |
|-----------|---------|
| ARQUITECTURA_ACCION_POR_SYNC.md | Agregar flujo de asignaciones |
| DATA_SYNCHRONIZATION_RULES.md | Agregar reglas de sincronización de asignaciones |
| README.md | Actualizar sección de asignaciones |

---

## ROLLBACK PLAN

Si algo falla, rollback por fase:

```bash
# FASE 1 (Frontend)
git revert <commit-frontend>

# FASE 2 (Backend)
git revert <commit-backend-reassign>
alembic downgrade -1

# FASE 3 (Status)
git revert <commit-status>
alembic downgrade -1

# FASE 4 (Cleanup)
git revert <commit-cleanup>
```

---

## MÉTRICAS DE ÉXITO

| Métrica | Objetivo |
|---------|----------|
| Bulk assign sin errores | 100% |
| Reasignación completa | 100% |
| Facturas huérfanas detectadas | 0 inconsistencias |
| Tests pasando | 100% |
| Pre-commit validation | PASS |
| Código deprecated | 0 referencias |

---

## RESPONSABILIDADES

| Rol | Responsabilidad |
|-----|-----------------|
| Frontend Dev | FASE 1: Fix bulk assign UI |
| Backend Dev | FASE 2, 3: Sincronización y status |
| Senior Dev | Review + validación de sincronización |
| QA | Testing exhaustivo de ciclo vida |

---

**Status:** 🔄 EN PLANIFICACIÓN
**Próximo paso:** Iniciar FASE 1 después de aprobación

¿Aprobado para continuar?
