# Guía de Sincronización de Migraciones de Base de Datos

## 📋 Problema Identificado

Las migraciones `fix_version_algoritmo_length` y `add_automation_001` usaban **revision IDs textuales personalizados** en lugar de **hashes autogenerados por Alembic**, causando problemas de sincronización entre equipos.

### ¿Por qué es problemático?

1. **Colisiones de IDs**: Dos desarrolladores podrían crear migraciones con el mismo ID textual
2. **Falta de unicidad**: Los hashes de Alembic garantizan IDs únicos basados en timestamp + random
3. **Desincronización**: Git puede compartir archivos, pero la BD de cada equipo queda inconsistente

---

## ✅ Solución Implementada

### Migraciones Regeneradas:

| Antes (ID Textual) | Después (Hash Único) |
|-------------------|----------------------|
| `fix_version_algoritmo_length` | `05b5bdfbca40` |
| `add_automation_001` | `7bad075511e9` |

### Cadena de Migraciones Actualizada:

```
da7367e01cd7 (initial_migration)
    ↓
e4b2063b3d6e (automation fields)
    ↓
129ab8035fa8 (periodo fields)
    ↓
6a652d604685 (chronological index)
    ↓
757c660b2207 (importaciones_presupuesto)
    ↓
f6feb264b552 (presupuesto_tables)
    ↓
abc123 (workflow_tables)
    ↓
22f577b537a1 (historial_pagos)
    ↓
ab8f4888b5b5 (approval fields)
    ↓
05b5bdfbca40 (extend version_algoritmo) ← NUEVO
    ↓
7bad075511e9 (automation tables) ← NUEVO (HEAD)
```

---

## 🔧 Pasos para Sincronizar en el Otro Equipo

### Equipo Personal (Este equipo) ✅
**Estado**: Ya sincronizado

### Equipo Empresa (Pendiente)

#### Paso 1: Backup de la Base de Datos
```bash
# Crear backup antes de hacer cambios
mysqldump -u root -p bd_afe > backup_bd_afe_$(date +%Y%m%d_%H%M%S).sql
```

#### Paso 2: Obtener las Nuevas Migraciones
```bash
# Hacer pull de los cambios del repositorio
git pull origin main

# Verificar que los archivos nuevos existen
ls -la alembic/versions/05b5bdfbca40_*
ls -la alembic/versions/7bad075511e9_*
```

#### Paso 3: Actualizar Versión en la Base de Datos

**Opción A: Usando Python (Recomendado)**
```python
# fix_sync.py
import pymysql

connection = pymysql.connect(
    host='localhost',
    user='root',
    password='root',  # Ajustar según tu configuración
    database='bd_afe',
    charset='utf8mb4'
)

try:
    with connection.cursor() as cursor:
        # Ver versión actual
        cursor.execute("SELECT * FROM alembic_version")
        print(f"Versión actual: {cursor.fetchall()}")

        # Actualizar versión
        cursor.execute("DELETE FROM alembic_version")
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('7bad075511e9')")

    connection.commit()
    print("✓ Versión actualizada a: 7bad075511e9")

finally:
    connection.close()
```

```bash
python fix_sync.py
```

**Opción B: Usando MySQL CLI**
```sql
-- Ver versión actual
SELECT * FROM alembic_version;

-- Actualizar versión
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('7bad075511e9');

-- Verificar
SELECT * FROM alembic_version;
```

#### Paso 4: Verificar Sincronización
```bash
# Debe mostrar: 7bad075511e9 (head)
alembic current

# Debe mostrar la cadena completa sin errores
alembic history

# Verificar que no hay migraciones pendientes
alembic upgrade head
```

---

## 🚨 Qué Hacer si Algo Sale Mal

### Si hay conflictos de migraciones:

1. **Restaurar backup**:
   ```bash
   mysql -u root -p bd_afe < backup_bd_afe_YYYYMMDD_HHMMSS.sql
   ```

2. **Contactar al equipo** para coordinar la sincronización

### Si `alembic current` falla:

```bash
# Ver qué versión tiene la BD
python -c "
import pymysql
conn = pymysql.connect(host='localhost', user='root', password='root', database='bd_afe')
cursor = conn.cursor()
cursor.execute('SELECT * FROM alembic_version')
print(cursor.fetchall())
"
```

---

## 📚 Mejores Prácticas (Para Futuro)

### ✅ Hacer:

1. **Usar `alembic revision --autogenerate`**: Siempre genera hashes únicos
2. **Coordinar migraciones grandes**: Comunicar cuando se crea una migración importante
3. **Hacer pull antes de crear migraciones**: Evita conflictos
4. **Probar en desarrollo**: Antes de aplicar en otros entornos

### ❌ NO Hacer:

1. **NO usar revision IDs textuales**: Ejemplo: `revision = 'mi_migracion_v1'`
2. **NO editar revision IDs manualmente**: Dejar que Alembic los genere
3. **NO hacer `alembic stamp`** sin entender qué hace
4. **NO aplicar migraciones en producción** sin probar primero

---

## 🔍 Comandos Útiles

```bash
# Ver versión actual
alembic current

# Ver historial completo
alembic history --verbose

# Ver migraciones pendientes
alembic upgrade --sql head

# Aplicar todas las migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1

# Ver estado de la BD vs migraciones
alembic check
```

---

## 📞 Contacto

Si tienes problemas con la sincronización:
1. No hagas cambios destructivos en la BD
2. Crea un backup primero
3. Documenta el error específico
4. Coordina con el equipo para resolverlo

---

## 📝 Registro de Cambios

### 2025-10-09
- **Problema**: Migraciones con IDs textuales causaban desincronización
- **Solución**: Regeneradas con hashes únicos (05b5bdfbca40, 7bad075511e9)
- **Estado**: Equipo personal sincronizado ✅ | Equipo empresa pendiente ⏳

---

## 🎯 Verificación Final

Después de sincronizar ambos equipos, ambos deben mostrar:

```bash
$ alembic current
7bad075511e9 (head)

$ alembic history | head -1
05b5bdfbca40 -> 7bad075511e9 (head), add automation tables
```

✅ **¡Sincronización completa!**
