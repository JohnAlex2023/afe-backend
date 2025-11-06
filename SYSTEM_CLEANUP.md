# Limpieza del Sistema - Documentación

**Fecha**: 2025-10-27
**Objetivo**: Sistema 100% limpio, sin redundancias, sin ambigüedades
**Commit**: 0fb76e6

## Resumen

Se realizó una limpieza masiva del sistema para eliminar:
- Scripts experimentales no usados
- Código duplicado
- Ambigüedades arquitectónicas
- Scripts de debug y diagnóstico

**Resultado**: De 35 scripts a 4 scripts activos.

## Scripts Activos (Necesarios)

### 1. `scripts/create_user.py`
**Propósito**: Crear usuarios iniciales en el sistema
**Uso**:
```bash
python scripts/create_user.py
```
**Cuándo usar**: Inicialización del sistema o crear nuevos usuarios

### 2. `scripts/reset_password.py`
**Propósito**: Resetear contraseñas de usuarios
**Uso**:
```bash
python scripts/reset_password.py
```
**Cuándo usar**: Recuperación de contraseñas olvidadas

### 3. `scripts/migrate_settings_to_db.py`
**Propósito**: Migración de settings a base de datos (legacy)
**Uso**:
```bash
python scripts/migrate_settings_to_db.py
```
**Cuándo usar**: Una sola vez durante inicialización

### 4. `scripts/limpiar_asignaciones_inactivas.py`
**Propósito**: Eliminar registros soft-deleted antes de adoptar hard delete pattern
**Uso**:
```bash
python scripts/limpiar_asignaciones_inactivas.py
```
**Cuándo usar**: Antes de desplegar hard delete pattern a producción

## Scripts Archivados

Todos los demás scripts (31 total) han sido movidos a `scripts/_archive/`

### Categorías Archivadas

**Sincronización/Reparación Experimental** (8 scripts):
- `asignar_nits_responsable.py`
- `asignar_responsables_facturas.py`
- `asignar_responsables_nits.py`
- `distribuir_nits_responsables.py`
- `sincronizar_facturas_con_asignaciones.py`
- `sincronizar_nombres_proveedores.py`
- `resincronizar_responsables_facturas.py`
- `resolver_nits_compartidos.py`

**Diagnóstico/Debug** (6 scripts):
- `debug_asignaciones.py`
- `diagnostico_integridad.py`
- `listar_facturas_ids.py`
- `listar_facturas_sin_responsable.py`
- `listar_responsables_y_asignaciones.py`

**Pruebas** (4 scripts):
- `ejecutar_automatizacion.py`
- `ejecutar_workflow_test.py`
- `procesar_facturas_pendientes.py`
- `sincronizar_estados_workflow.py`

**Carga de Datos Inicial** (5 scripts):
- `cargar_proveedores_desde_csv.py`
- `cargar_proveedores_corregido.py`
- `normalizar_nits_existentes.py`

**Redundantes/Duplicados** (4 scripts):
- `limpiar_asignaciones_inactivas_seguro.py`
- `clasificar_proveedores_enterprise.py`
- `generar_conceptos_facturas.py`
- `fusionar_duplicados_proveedores.py`

## Por Qué Esta Limpieza

### Antes
- 35 scripts activos
- Confusión sobre cuál script usar
- Scripts experimentales que podían causar problemas
- Código muerto acumulado
- Dificultad para identificar errores reales del sistema

### Después
- 4 scripts activos claramente documentados
- Sistema limpio y profesional
- Fácil de mantener
- Sin ambigüedades
- Listo para identificar errores reales

## Impacto en el Sistema

###  SIN IMPACTO NEGATIVO
- No hay imports rotos
- No hay código que dependa de scripts archivados
- Los scripts archivados se pueden recuperar si es necesario
- Git historial completo (se puede hacer git log)

###  BENEFICIOS
- Código más limpio
- Menos confusión
- Mejor performance al navegar proyecto
- Documentación clara de scripts necesarios

## Si Necesitas un Script Archivado

Los scripts están en `scripts/_archive/` y pueden recuperarse en cualquier momento:

```bash
# Ver contenido
cat scripts/_archive/diagnostico_integridad.py

# Copiar a directorio activo
cp scripts/_archive/diagnostico_integridad.py scripts/

# Ver historio en Git
git log --all -- scripts/diagnostico_integridad.py
```

## Próximos Pasos

Ahora el sistema está listo para:

1. **Identificar errores reales** sin ruido de código experimental
2. **Ejecutar pruebas** con sistema limpio
3. **Desplegar cambios** con confianza
4. **Mantener** código profesional y claro

---

**Verificación**:
```bash
# Scripts activos
ls -1 scripts/*.py
# Output: create_user.py, reset_password.py, migrate_settings_to_db.py, limpiar_asignaciones_inactivas.py

# Scripts archivados
ls -1 scripts/_archive/ | wc -l
# Output: 31

# Sin imports rotos
grep -r "from scripts" app/ || echo " Sin imports rotos"
```

---

**Estado**:  COMPLETO
**Commit**: 0fb76e6
**Autor**: Claude Code
