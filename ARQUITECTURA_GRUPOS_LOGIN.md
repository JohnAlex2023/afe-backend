# 📐 ARQUITECTURA: CLASIFICACIÓN POR GRUPOS (SEDES/EMPRESAS)

## 🎯 Objetivo General

Implementar un sistema de **aislamiento de datos por grupos** donde:
- Las facturas se clasifican por **Grupo (Avidanti, Soacha, etc.)**
- Los responsables pueden estar en **múltiples grupos**
- Un admin solo ve su grupo, los responsables ven sus asignaciones dentro de su grupo
- **NITs compartidos** funcionan correctamente (un NIT en Avidanti ≠ mismo NIT en Soacha)

---

## 🔐 1. NUEVO FLUJO DE LOGIN (CRÍTICO)

### Antes (Actual)
```
Login Form:
┌─────────────────────────────┐
│ Usuario:     [________]     │
│ Contraseña:  [________]     │
│ [No soy un robot] ✓         │
│ [LOGIN]                     │
└─────────────────────────────┘
         ↓
    Usuario + Password → JWT
         ↓
    Se conecta a todos los datos del usuario
```

### Después (Nuevo)
```
Login Form (MEJORADO):
┌──────────────────────────────────────────┐
│ Usuario:      [________________]         │
│ Empresa:      [▼ Avidanti  ]   ← NEW     │
│               ├ Avidanti                 │
│               ├ Soacha                   │
│               └ (solo si tiene acceso)   │
│ Contraseña:   [________________]         │
│ [No soy un robot] ✓                      │
│ [LOGIN]                                  │
└──────────────────────────────────────────┘
         ↓
   Usuario + Empresa + Password → JWT (con grupo_id)
         ↓
   JWT contiene: {sub: user_id, grupo_id: 1, exp: ...}
         ↓
   Se conecta SOLO a datos del grupo seleccionado
```

### ¿Cómo decide qué empresas mostrar?

```
1. Usuario escribe su usuario
2. Sistema busca: SELECT DISTINCT g.id, g.nombre
                  FROM responsable_grupo rg
                  JOIN grupos g ON rg.grupo_id = g.id
                  WHERE rg.responsable_id = (usuario encontrado)
                  AND rg.activo = 1

3. Retorna lista de empresas disponibles para ese usuario
4. Usuario selecciona una
5. Sistema verifica contraseña
6. Sistema crea JWT con grupo_id

Ejemplo:
┌─────────────────────────────────────────────┐
│ Usuario: "juan"                             │
│ Juan está en:                               │
│   ✓ Avidanti (admin)                        │
│   ✓ Soacha (responsable)                    │
│   ✗ Otros grupos                            │
│                                             │
│ Empresa: [▼ Avidanti ] (preseleccionar)    │
│          ├ Avidanti                        │
│          ├ Soacha                          │
└─────────────────────────────────────────────┘
```

---

## 📊 2. ARQUITECTURA DE DATOS ACTUALIZADA

### 2.1 Modelo de Datos (Tablas Nuevas)

```
┌─────────────────────────────────────────────┐
│             GRUPOS (NEW)                    │
│                                             │
│ id | nombre | correos_corporativos | ...   │
│ 1  | Avidanti | ["avidanti@corp.com"]      │
│ 2  | Soacha   | ["soacha@corp.com"]        │
└─────────────────────────────────────────────┘
         ↓ (M:N)
┌─────────────────────────────────────────────┐
│      RESPONSABLE_GRUPO (NEW - M:N)         │
│                                             │
│ id | responsable_id | grupo_id | activo   │
│ 1  | 1 (juan)       | 1 (Avidanti) | 1     │
│ 2  | 1 (juan)       | 2 (Soacha)   | 1     │
│ 3  | 2 (carlos)     | 1 (Avidanti) | 1     │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│      ASIGNACION_NIT_RESPONSABLE (UPDATED)   │
│                                             │
│ nit | responsable_id | grupo_id | area ... │
│ 830.122.566-1 | 1 | 1 | TI (Avidanti)      │
│ 830.122.566-1 | 2 | 2 | TI (Soacha)        │
│ 900.123.456   | 1 | 1 | Ops (Avidanti)     │
└─────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│         FACTURAS (UPDATED)                  │
│                                             │
│ id | numero_factura | nit | grupo_id | ... │
│ 1  | FAC-001 | 830122566 | 1 (Avidanti)    │
│ 2  | FAC-002 | 830122566 | 2 (Soacha)      │
│ 3  | FAC-003 | 900123456 | 1 (Avidanti)    │
└─────────────────────────────────────────────┘
```

### 2.2 Relaciones SQL

```sql
-- RESPONSABLE (sin cambios en la tabla, solo relación)
-- Agregamos: relationship a ResponsableGrupo

-- NUEVA: GRUPOS
CREATE TABLE grupos (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(150) UNIQUE NOT NULL,
    descripcion TEXT,
    correos_corporativos JSON,
    activo BOOLEAN DEFAULT 1,
    creado_en DATETIME DEFAULT NOW(),
    actualizado_en DATETIME DEFAULT NOW(),
    INDEX idx_grupo_activo (activo),
    INDEX idx_grupo_nombre (nombre)
);

-- NUEVA: RESPONSABLE_GRUPO (relación M:N)
CREATE TABLE responsable_grupo (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    responsable_id BIGINT NOT NULL,
    grupo_id BIGINT NOT NULL,
    activo BOOLEAN DEFAULT 1,
    creado_en DATETIME DEFAULT NOW(),
    UNIQUE KEY uq_responsable_grupo (responsable_id, grupo_id),
    FOREIGN KEY (responsable_id) REFERENCES responsables(id),
    FOREIGN KEY (grupo_id) REFERENCES grupos(id),
    INDEX idx_responsable_grupo_grupo (grupo_id),
    INDEX idx_responsable_grupo_responsable (responsable_id)
);

-- ACTUALIZAR: ASIGNACION_NIT_RESPONSABLE
ALTER TABLE asignacion_nit_responsable
ADD COLUMN grupo_id BIGINT NOT NULL DEFAULT 1,
ADD FOREIGN KEY (grupo_id) REFERENCES grupos(id),
ADD INDEX idx_asignacion_grupo (grupo_id),
-- Cambiar constraint a (nit, responsable_id, grupo_id)
DROP CONSTRAINT uq_nit_responsable,
ADD UNIQUE KEY uq_nit_responsable_grupo (nit, responsable_id, grupo_id);

-- ACTUALIZAR: FACTURAS
ALTER TABLE facturas
ADD COLUMN grupo_id BIGINT NOT NULL DEFAULT 1,
ADD FOREIGN KEY (grupo_id) REFERENCES grupos(id),
ADD INDEX idx_factura_grupo (grupo_id);
```

---

## 🔄 3. FLUJO COMPLETO DE FUNCIONAMIENTO

### 3.1 FASE 1: LOGIN CON SELECCIÓN DE GRUPO

```
┌─────────────────────────────────────────────────────────┐
│ USUARIO INGRESA AL SITIO                                │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ FRONTEND: Mostrar formulario de login                   │
│  ├─ Campo: Usuario (text input)                         │
│  ├─ Campo: Empresa (select, inicialmente VACÍO)        │
│  ├─ Campo: Contraseña (password)                       │
│  ├─ Campo: No soy un robot (reCAPTCHA)                │
│  └─ Botón: [LOGIN]                                     │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ USER ESCRIBE USUARIO Y SALE DEL CAMPO (blur)           │
│                                                         │
│ FRONTEND: Hacer request a endpoint nuevo:              │
│ POST /api/v1/auth/get-grupos/{usuario}                 │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ BACKEND: /api/v1/auth/get-grupos/{usuario}             │
│                                                         │
│ 1. SELECT responsable WHERE usuario = ?                │
│ 2. Si NO existe → ERROR 404 (usuario no encontrado)    │
│ 3. Si existe:                                          │
│    SELECT DISTINCT g.id, g.nombre                      │
│    FROM responsable_grupo rg                           │
│    JOIN grupos g ON rg.grupo_id = g.id                 │
│    WHERE rg.responsable_id = ?                         │
│    AND rg.activo = 1                                   │
│ 4. Retornar: [{id: 1, nombre: "Avidanti"},             │
│              {id: 2, nombre: "Soacha"}]                │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ FRONTEND: Llenar select de Empresa                      │
│                                                         │
│ Empresa: [▼ Avidanti ]     ← Preseleccionar el primero │
│          ├ Avidanti        │ (o si solo hay 1, ya)     │
│          ├ Soacha          │                           │
│          └ ...                                         │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ USUARIO INGRESA CONTRASEÑA + RESUELVE CAPTCHA          │
│ Y HACE CLICK EN [LOGIN]                                │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ FRONTEND: Enviar request a:                             │
│ POST /api/v1/auth/login                                │
│                                                         │
│ {                                                       │
│   "usuario": "juan",                                    │
│   "password": "mi_password",                           │
│   "grupo_id": 1,           ← NUEVO CAMPO               │
│   "recaptcha_token": "..."                             │
│ }                                                       │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ BACKEND: /api/v1/auth/login (MEJORADO)                 │
│                                                         │
│ 1. Validar reCAPTCHA                                   │
│ 2. SELECT responsable WHERE usuario = ?                │
│ 3. Verificar contraseña (bcrypt)                       │
│ 4. Verificar relación ResponsableGrupo:                │
│    SELECT * FROM responsable_grupo                     │
│    WHERE responsable_id = ? AND grupo_id = ?           │
│    AND activo = 1                                      │
│ 5. Si NO existe relación → ERROR 403 (acceso denegado) │
│ 6. Si OK:                                              │
│    - Crear JWT con EXTRA CLAIM: grupo_id               │
│    - Payload: {sub: 1, grupo_id: 1, exp: ...}         │
│    - Actualizar last_login en responsable              │
│    - Retornar JWT                                      │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ FRONTEND: Guardar JWT en localStorage                  │
│ REDIRECT a /dashboard                                  │
└─────────────────────────────────────────────────────────┘
```

### 3.2 FASE 2: SOLICITUD DE FACTURAS (FILTRO POR GRUPO)

```
┌─────────────────────────────────────────────────────────┐
│ USUARIO EN DASHBOARD                                    │
│ Hace click: GET /api/v1/facturas/?limit=50             │
│                                                         │
│ Headers: {Authorization: "Bearer JWT"}                 │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ BACKEND MIDDLEWARE: Validar JWT                         │
│                                                         │
│ 1. Decodificar JWT                                     │
│ 2. Extraer: user_id = 1, grupo_id = 1                 │
│ 3. Guardar en context: current_user.grupo_id = 1      │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ BACKEND ENDPOINT: GET /api/v1/facturas/cursor          │
│                                                         │
│ Lógica ANTERIOR:                                       │
│ if current_user.role == "responsable":                │
│     responsable_id = current_user.id                   │
│ else:  # admin                                         │
│     responsable_id = None (ve todas)                   │
│                                                         │
│ LÓGICA NUEVA: Agregar filtro por grupo_id             │
│ ─────────────────────────────────────────────────────  │
│ if current_user.role == "responsable":                │
│     responsable_id = current_user.id                   │
│     grupo_id = current_user.grupo_id  ← ADD THIS       │
│                                                        │
│ else:  # admin                                         │
│     responsable_id = None (ve todas su grupo)          │
│     grupo_id = current_user.grupo_id  ← ADD THIS       │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ QUERY MEJORADO:                                         │
│                                                         │
│ SELECT f.* FROM facturas f                             │
│ WHERE f.grupo_id = ? ← FILTRO NUEVO                    │
│ AND (                                                   │
│     (current_user.role = 'responsable'                 │
│      AND f.responsable_id = current_user.id)           │
│     OR                                                  │
│     (current_user.role = 'admin')                      │
│ )                                                       │
│ ORDER BY f.creado_en DESC                              │
│ LIMIT 50                                                │
└─────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────┐
│ RETORNAR: Facturas SOLO del grupo seleccionado         │
│                                                         │
│ [                                                       │
│   {id: 1, numero_factura: "FAC-001", grupo_id: 1, ...},│
│   {id: 3, numero_factura: "FAC-003", grupo_id: 1, ...},│
│   ... solo facturas de Avidanti (grupo_id=1)           │
│ ]                                                       │
└─────────────────────────────────────────────────────────┘
```

### 3.3 FASE 3: ASIGNACIÓN DE FACTURAS (CON NITs COMPARTIDOS)

```
Escenario: NIT 830.122.566-1 está en 2 grupos

1. FACTURA LLEGA POR CORREO AVIDANTI
   ├─ Email: avidanti@corp.com
   ├─ Backend identifica grupo = 1 (por correo corporativo)
   ├─ Extrae NIT: 830.122.566-1
   ├─ Busca asignación:
   │  SELECT * FROM asignacion_nit_responsable
   │  WHERE nit = '830122566-1'
   │  AND grupo_id = 1  ← FILTRO CRÍTICO
   │  AND responsable_id IN (usuarios de grupo 1)
   ├─ Obtiene: responsable_id = 1 (juan en Avidanti)
   └─ Factura.grupo_id = 1, Factura.responsable_id = 1

2. MISMA FACTURA LLEGA POR CORREO SOACHA
   ├─ Email: soacha@corp.com
   ├─ Backend identifica grupo = 2
   ├─ Extrae NIT: 830.122.566-1
   ├─ Busca asignación:
   │  SELECT * FROM asignacion_nit_responsable
   │  WHERE nit = '830122566-1'
   │  AND grupo_id = 2  ← DIFERENTE GRUPO
   │  AND responsable_id IN (usuarios de grupo 2)
   ├─ Obtiene: responsable_id = 2 (carlos en Soacha)
   └─ Factura.grupo_id = 2, Factura.responsable_id = 2

RESULTADO:
┌──────────────────────────────────────────────┐
│ Factura 1: NIT 830.122.566-1 en AVIDANTI    │
│ └─ responsable_id = 1, grupo_id = 1         │
│                                              │
│ Factura 2: NIT 830.122.566-1 en SOACHA      │
│ └─ responsable_id = 2, grupo_id = 2         │
│                                              │
│ ✓ Mismo NIT, DIFERENTES responsables        │
│ ✓ Cada responsable ve SOLO su factura       │
└──────────────────────────────────────────────┘
```

---

## 🛠️ 4. CAMBIOS POR COMPONENTE

### 4.1 MODELOS (app/models/)

**NUEVOS:**
- `grupo.py` → Tabla `Grupo` y `ResponsableGrupo`

**MODIFICADOS:**
- `responsable.py` → Agregar relación a `ResponsableGrupo`
- `factura.py` → Agregar campo `grupo_id`
- `workflow_aprobacion.py` → Agregar campo `grupo_id` a `AsignacionNitResponsable`

### 4.2 SCHEMAS (app/schemas/)

**NUEVOS:**
- `GrupoCreate`, `GrupoRead`, `GrupoUpdate`
- `ResponsableGrupoCreate`, `ResponsableGrupoRead`

**MODIFICADOS:**
- `LoginRequest` → Agregar campo `grupo_id`
- `ResponsableRead` → Agregar lista de grupos

### 4.3 CRUD (app/crud/)

**NUEVOS:**
- `grupo.py` → CRUD completo para Grupo
- `responsable_grupo.py` → CRUD para relación M:N

**MODIFICADOS:**
- `responsable.py` → Métodos que ahora necesitan filtrar por grupo
- `factura.py` → Métodos de lista/obtener con filtro grupo_id
- `asignacion_nit.py` → Agregar grupo_id a operaciones

### 4.4 ROUTERS (app/api/v1/routers/)

**NUEVOS:**
- `grupos.py` → Endpoints CRUD para Grupo
  - POST   /api/v1/grupos/
  - GET    /api/v1/grupos/
  - GET    /api/v1/grupos/{id}
  - PUT    /api/v1/grupos/{id}
  - DELETE /api/v1/grupos/{id}
  - POST   /api/v1/grupos/{grupo_id}/responsables
  - DELETE /api/v1/grupos/{grupo_id}/responsables/{responsable_id}

**MODIFICADOS:**
- `auth.py` → Mejorado login
  - POST   /api/v1/auth/login (ahora requiere grupo_id)
  - POST   /api/v1/auth/get-grupos/{usuario} ← NUEVO
- `facturas.py` → Filtro automático por grupo
- `asignacion_nit.py` → Incluir grupo en operaciones

### 4.5 SERVICIOS (app/services/)

**MODIFICADOS:**
- `invoice_service.py` → Identificar grupo por correo corporativo
- `workflow_automatico.py` → Asignar responsable dentro del grupo

---

## 💡 5. LÓGICA DE NEGOCIO CLAVE

### 5.1 ¿Cómo identifica el grupo de una factura?

```python
# En invoice_service.py
def process_and_persist_invoice(..., email_from: str):
    """
    email_from = "avidanti@corp.com" o "soacha@corp.com"
    """

    # 1. Buscar grupo por correo corporativo
    grupo = db.query(Grupo).filter(
        func.json_contains(
            Grupo.correos_corporativos,
            f'"{email_from}"'
        )
    ).first()

    if not grupo:
        # Si no encuentra grupo, crear error o asignar default
        raise ValueError(f"Email {email_from} no asociado a ningún grupo")

    # 2. Procesar factura
    factura = Factura(...)
    factura.grupo_id = grupo.id

    # 3. Buscar responsable DENTRO DEL GRUPO
    nit = extract_nit(...)
    asignacion = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.nit == nit,
        AsignacionNitResponsable.grupo_id == grupo.id
    ).first()

    factura.responsable_id = asignacion.responsable_id
```

### 5.2 ¿Qué pasa si un admin intenta acceder a otro grupo?

```python
# En middleware de autenticación
def get_current_user(token: str, grupo_id: int):
    payload = jwt.decode(token)
    user_id = payload.get("sub")
    token_grupo_id = payload.get("grupo_id")

    # VALIDACIÓN CRÍTICA: No permitir cambiar grupo en request
    if grupo_id != token_grupo_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a este grupo"
        )

    return get_responsable_by_id(user_id)
```

### 5.3 ¿Qué pasa si un responsable está en múltiples grupos?

```python
# Login: Mostrar lista de grupos disponibles
# El usuario ELIGE uno (no puede estar en 2 al mismo tiempo)

# Si quiere cambiar de grupo:
# → Debe hacer LOGOUT y volver a LOGIN
# → Seleccionar otro grupo
# → Obtener JWT con nuevo grupo_id
```

---

## 📋 6. TABLA DE CAMBIOS RESUMIDA

| Componente | Cambio | Tipo |
|-----------|--------|------|
| Login Form | Agregar select de Empresa | UI |
| /auth/get-grupos | Nuevo endpoint | API |
| /auth/login | Agregar campo grupo_id en request | API |
| JWT Payload | Agregar grupo_id claim | Backend |
| Tabla grupos | NUEVA | DB |
| Tabla responsable_grupo | NUEVA | DB |
| Tabla asignacion_nit_responsable | Agregar grupo_id | DB |
| Tabla facturas | Agregar grupo_id | DB |
| GET /facturas | Filtrar por grupo_id automáticamente | API |
| GET /responsables | Filtrar por grupo_id | API |
| invoice_service.py | Identificar grupo por email | Service |

---

## ✅ 7. CASOS DE USO VALIDADOS

### Caso 1: Usuario en UN solo grupo
```
juan está SOLO en Avidanti
└─ Login: Mostrar [Avidanti] preseleccionado
└─ Puede cambiar contabilidad ahorando con "cambiar grupo"
   pero necesita re-login
```

### Caso 2: Usuario en MÚLTIPLES grupos
```
carlos está en Avidanti Y Soacha
└─ Login: Mostrar [Avidanti, Soacha]
└─ Elige Avidanti → Ve facturas Avidanti
└─ Elige Soacha → Ve facturas Soacha
└─ No puede ver ambas al mismo tiempo
```

### Caso 3: NITs compartidos
```
NIT 830.122.566-1:
├─ En Avidanti → asignado a juan
├─ En Soacha → asignado a carlos
└─ Facturas del NIT se distribuyen por grupo
```

### Caso 4: Admin que supervisa múltiples grupos
```
super_admin está en [Avidanti, Soacha, Otros]
└─ Cada login es EN UN GRUPO
└─ Ve todas las facturas de ese grupo (no solo suyas)
└─ Si quiere ver otro grupo, debe hacer logout/login
```

---

## 🚀 8. PRÓXIMOS PASOS (ORDEN DE IMPLEMENTACIÓN)

1. ✅ Crear documento (ESTE)
2. ⏳ Crear modelos: `Grupo` y `ResponsableGrupo`
3. ⏳ Actualizar modelos existentes: Responsable, Factura, AsignacionNitResponsable
4. ⏳ Crear migraciones Alembic
5. ⏳ Crear schemas Pydantic
6. ⏳ Crear CRUD
7. ⏳ Mejorar endpoint /auth/login (agregar grupo_id)
8. ⏳ Crear endpoint /auth/get-grupos/{usuario}
9. ⏳ Crear router de Grupos (/grupos/)
10. ⏳ Actualizar queries de Factura para filtrar por grupo
11. ⏳ Actualizar invoice_service para asignar grupo_id
12. ⏳ Actualizar frontend (formulario de login)
13. ⏳ Testing completo
14. ⏳ Documentar para equipo

---

## 📚 REFERENCIAS EN CÓDIGO

**Después de la implementación:**
- Flujo de login: `app/api/v1/routers/auth.py`
- Modelos: `app/models/grupo.py`, `app/models/responsable.py`, `app/models/factura.py`
- CRUD: `app/crud/grupo.py`, `app/crud/responsable_grupo.py`
- Servicios: `app/services/invoice_service.py`
- Schemas: `app/schemas/grupo.py`, `app/schemas/auth.py`
