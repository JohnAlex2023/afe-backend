# Instrucciones: Cómo Configurar "Facturas Asignadas" por Responsable

## El Problema

Actualmente TODAS las facturas muestran "Alexander" en la columna "RESPONSABLE" porque TODOS los NITs están asignados a Alexander en la tabla `AsignacionNitResponsable`.

Esto hace que tanto "Todas las Facturas" como "Facturas Asignadas" muestren las mismas 294 facturas.

## La Solución

Necesitas **distribuir los NITs entre múltiples responsables** para que cada uno vea sus propias facturas.

### Paso 1: Ver la Distribución Actual

```bash
python scripts/distribuir_nits_responsables.py ver_distribucion
```

Esto te mostrará algo como:

```
================================================================================
DISTRIBUCIÓN ACTUAL DE NITs POR RESPONSABLE
================================================================================

John Alex (ID: 1, usuario: )
  NITs asignados: 247
    - 800185449-9 (Proveedor A)
    - 800123456-1 (Proveedor B)
    ... y 245 más
```

### Paso 2: Crear Responsables Adicionales

```bash
python scripts/distribuir_nits_responsables.py crear_responsables
```

Esto crea 3 responsables de ejemplo:
- `responsable1` / Contraseña: `12345678`
- `responsable2` / Contraseña: `12345678`
- `responsable3` / Contraseña: `12345678`

Salida esperada:

```
+ Responsable creado: responsable1 (ID: 2)
+ Responsable creado: responsable2 (ID: 3)
+ Responsable creado: responsable3 (ID: 4)

✓ Responsables de ejemplo creados
```

### Paso 3: Redistribuir NITs Entre los Responsables

```bash
python scripts/distribuir_nits_responsables.py redistribuir
```

Esto distribuye los 247 NITs de forma equilibrada:
- Responsable 1: ~62 NITs
- Responsable 2: ~62 NITs
- Responsable 3: ~62 NITs
- John Alex: ~61 NITs

Salida esperada:

```
Total de asignaciones actuales: 247
Total de responsables: 4
Distribución objetivo: 61 asignaciones por responsable

Asignación 1/247
  NIT: 800185449-9 (Proveedor A)
  De: John Alex
  A:  Responsable 1

Asignación 2/247
  ...

✓ Asignaciones actualizadas: 247
✓ Redistribución completada
```

### Paso 4: Verificar la Distribución

```bash
python scripts/distribuir_nits_responsables.py ver_distribucion
```

Ahora deberías ver algo como:

```
John Alex (ID: 1, usuario: )
  NITs asignados: 61
    - NIT1
    - NIT2
    ... y 59 más

Responsable 1 (ID: 2, usuario: responsable1)
  NITs asignados: 62
    - NIT3
    - NIT4
    ... y 60 más

Responsable 2 (ID: 3, usuario: responsable2)
  NITs asignados: 62
    - NIT5
    - NIT6
    ... y 60 más

Responsable 3 (ID: 4, usuario: responsable3)
  NITs asignados: 62
    - NIT7
    - NIT8
    ... y 60 más
```

## ¿Qué Pasará Después?

Después de redistribuir, cuando:

### Admin "John Alex" acceda:

**"Todas las Facturas"** → Ve las 294 facturas (todas las del sistema)

**"Facturas Asignadas"** → Ve ~61 facturas (las de sus NITs asignados)

### Responsable1 acceda:

**"Facturas"** → Ve ~62 facturas (automáticamente, solo sus NITs asignados)

## Cómo Funciona el Filtrado

El código usa esta lógica en el endpoint `GET /facturas/`:

```python
if solo_asignadas:
    # Obtener NITs asignados al responsable desde AsignacionNitResponsable
    asignaciones = SELECT nit FROM asignacion_nit_responsable
                   WHERE responsable_id = current_user.id AND activo = TRUE

    # Buscar proveedores con esos NITs
    proveedor_ids = SELECT id FROM proveedores
                    WHERE nit IN (asignaciones.nit)

    # Retornar facturas de esos proveedores
    facturas = SELECT * FROM facturas
               WHERE proveedor_id IN (proveedor_ids)
```

## Commits Realizados

1. **ca560d7** - fix: Corregir filtrado de facturas en cursor pagination
2. **374870f** - fix: Añadir fallback inteligente al filtrado
3. **55d681a** - feat: Añadir endpoint de diagnóstico `/responsables/me/diagnostico`
4. **0601d73** - feat: Añadir script para distribuir NITs

## Si Necesitas Hacerlo Manualmente

Si prefieres hacer la distribución manualmente en lugar de usar el script:

### 1. Crear Responsable

```sql
INSERT INTO responsables (usuario, nombre, email, hashed_password, activo, role_id)
SELECT 'responsable1', 'Responsable 1', 'resp1@example.com',
       (SELECT hashed_password FROM responsables LIMIT 1), 1,
       (SELECT id FROM roles WHERE nombre = 'responsable');
```

### 2. Obtener IDs de la Tabla AsignacionNitResponsable

```sql
SELECT id, nit, responsable_id FROM asignacion_nit_responsable
WHERE activo = TRUE LIMIT 10;
```

### 3. Actualizar Responsable para Algunos NITs

```sql
UPDATE asignacion_nit_responsable
SET responsable_id = 2  -- ID del nuevo responsable
WHERE nit IN ('800185449-9', '800123456-1', ...)  -- NITs específicos
AND activo = TRUE;
```

## Debugging: Endpoint de Diagnóstico

Si algo sigue sin funcionar, puedes usar el endpoint de diagnóstico:

```
GET /api/v1/responsables/me/diagnostico
```

Retorna:
- Info del responsable actual
- Asignaciones explícitas en `AsignacionNitResponsable`
- Total de facturas directas (`responsable_id = current_user`)
- IDs de proveedores obtenidos
- Total de facturas de esos proveedores

## Resumen

| Admin John Alex | Responsable1 | Responsable2 | Responsable3 |
|---|---|---|---|
| **Todas** → 294 | N/A | N/A | N/A |
| **Asignadas** → ~61 | **Facturas** → ~62 | **Facturas** → ~62 | **Facturas** → ~62 |
| NITs: 61 | NITs: 62 | NITs: 62 | NITs: 62 |
