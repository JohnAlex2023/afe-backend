# 💾 DOCUMENTACIÓN TÉCNICA - BASE DE DATOS AFE

**Versión:** 2.0 (Estable)
**Última actualización:** Noviembre 2024
**Estado:** Production Ready
**Motor:** MySQL 8.0+

---

## 📑 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Tablas Principales](#tablas-principales)
3. [Modelos SQLAlchemy](#modelos-sqlalchemy)
4. [Diagrama E-R](#diagrama-er)
5. [Migraciones Alembic](#migraciones-alembic)
6. [Índices y Performance](#índices-y-performance)
7. [Triggers y Integridad](#triggers-y-integridad)
8. [Datos de Inicialización](#datos-de-inicialización)
9. [Queries Críticas](#queries-críticas)
10. [Optimizaciones y Mejores Prácticas](#optimizaciones-y-mejores-prácticas)
11. [Documentación de Campos](#documentación-de-campos)
12. [Mantenimiento y Administración](#mantenimiento-y-administración)

---

## 🎯 Visión General

### Propósito de la BD

La base de datos AFE está diseñada para:

-  **Gestionar facturas electrónicas** desde ingesta hasta aprobación/pago
-  **Automatizar workflows** de aprobación con inteligencia
-  **Auditar completamente** cada cambio (compliance)
-  **Soportar múltiples responsables** por proveedor (enterprise)
-  **Analizar patrones** de gasto y recurrencia
-  **Controlar presupuestos** con aprobaciones multinivel

### Datos Clave

| Aspecto | Detalle |
|---------|---------|
| **Motor** | MySQL 8.0+ |
| **ORM** | SQLAlchemy 2.0 |
| **Migraciones** | Alembic |
| **Tablas Principales** | 14 + 3 auditoría |
| **Relaciones** | 1:1, 1:N, M:N |
| **Índices** | 30+ estratégicos |
| **Triggers** | 2+ de integridad |
| **Tamaño Esperado** | 5-100GB (según volumen) |

### Capas de la BD

```
┌─────────────────────────────────────┐
│  APLICACIÓN (FastAPI + SQLAlchemy)  │
├─────────────────────────────────────┤
│  MODELOS ORM (Python classes)       │
├─────────────────────────────────────┤
│  MIGRACIONES (Alembic versions)     │
├─────────────────────────────────────┤
│  ESQUEMA (Tablas + Índices)         │
├─────────────────────────────────────┤
│  TRIGGERS (Integridad)              │
├─────────────────────────────────────┤
│  MYSQL 8.0+ (Motor)                 │
└─────────────────────────────────────┘
```

---

##  Tablas Principales

### 1. TABLA: roles

**Descripción:** Roles de usuario (admin, responsable, viewer)

```sql
CREATE TABLE roles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(50) NOT NULL UNIQUE
);
```

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| id | BIGINT | PK, AI | Identificador único |
| nombre | VARCHAR(50) | NOT NULL, UNIQUE | Nombre del rol |

**Valores Predefinidos:**
- `admin` - Acceso total
- `responsable` - Aprobación de facturas
- `viewer` - Solo lectura

---

### 2. TABLA: responsables

**Descripción:** Usuarios que aprueban facturas. Soporta autenticación local y OAuth (Microsoft).

```sql
CREATE TABLE responsables (
    -- Identificación
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    usuario VARCHAR(100) NOT NULL UNIQUE,
    nombre VARCHAR(150),
    email VARCHAR(255) NOT NULL UNIQUE,

    -- Información
    area VARCHAR(100),
    telefono VARCHAR(50),
    activo BOOLEAN DEFAULT TRUE,
    last_login DATETIME,

    -- Autenticación
    role_id BIGINT NOT NULL,
    hashed_password VARCHAR(255),  -- NULL para OAuth
    must_change_password BOOLEAN DEFAULT TRUE,
    auth_provider VARCHAR(50) DEFAULT 'local',  -- local, microsoft, google
    oauth_id VARCHAR(255) UNIQUE,  -- ID en OAuth provider
    oauth_picture VARCHAR(500),    -- URL foto perfil

    -- Auditoría
    creado_en DATETIME DEFAULT NOW(),

    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT,
    INDEX idx_activo (activo),
    INDEX idx_oauth_id (oauth_id)
);
```

**Campos Especiales:**
- `auth_provider`: Método de autenticación (local = contraseña, microsoft/google = OAuth)
- `oauth_id`: ID único en el proveedor OAuth (ej: UPN de Azure AD)
- `hashed_password`: NULL para usuarios OAuth, populated para local

---

### 3. TABLA: proveedores

**Descripción:** Proveedores que emiten facturas

```sql
CREATE TABLE proveedores (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    nit VARCHAR(64) NOT NULL UNIQUE,
    razon_social VARCHAR(255) NOT NULL,
    area VARCHAR(100),
    contacto_email VARCHAR(255),
    telefono VARCHAR(50),
    direccion VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE,
    creado_en DATETIME DEFAULT NOW(),

    INDEX idx_nit (nit),
    INDEX idx_activo (activo)
);
```

**Constraints:**
- NIT es único (identifica unívocamente al proveedor)
- Un proveedor puede emitir múltiples facturas
- Un proveedor puede estar asignado a múltiples responsables

---

### 4. TABLA: facturas (CORE)

**Descripción:** Facturas electrónicas - tabla central del sistema

```sql
CREATE TABLE facturas (
    -- Identificación
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    numero_factura VARCHAR(50) NOT NULL,
    cufe VARCHAR(100) NOT NULL UNIQUE,

    -- Fechas
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE,

    -- Monto
    subtotal NUMERIC(15,2),
    iva NUMERIC(15,2),
    total_a_pagar NUMERIC(15,2),

    -- Referencias
    proveedor_id BIGINT,
    responsable_id BIGINT,  -- Aprobador asignado
    factura_referencia_id BIGINT,  -- Mes anterior

    -- Estados
    estado ENUM('en_revision', 'aprobada', 'aprobada_auto', 'rechazada', 'pagada')
        DEFAULT 'en_revision',
    estado_asignacion ENUM('sin_asignar', 'asignado', 'huerfano', 'inconsistente'),

    -- Automatización
    confianza_automatica NUMERIC(3,2),
    fecha_procesamiento_auto DATETIME,
    motivo_decision VARCHAR(500),
    accion_por VARCHAR(255),  -- Usuario que aprobó/rechazó

    -- Análisis
    tipo_factura VARCHAR(20),  -- COMPRA, VENTA, NOTA_CREDITO
    patron_recurrencia VARCHAR(20),  -- FIJO, VARIABLE, UNICO
    concepto_principal VARCHAR(500),
    concepto_hash VARCHAR(32),  -- MD5 para matching
    concepto_normalizado VARCHAR(500),
    orden_compra_numero VARCHAR(50),

    -- Auditoría
    creado_en DATETIME DEFAULT NOW(),
    actualizado_en DATETIME DEFAULT NOW() ON UPDATE NOW(),

    UNIQUE (numero_factura, proveedor_id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
    FOREIGN KEY (responsable_id) REFERENCES responsables(id),
    FOREIGN KEY (factura_referencia_id) REFERENCES facturas(id),

    -- Índices
    INDEX idx_estado (estado),
    INDEX idx_proveedor_id (proveedor_id),
    INDEX idx_responsable_id (responsable_id),
    INDEX idx_concepto_hash (concepto_hash),
    INDEX idx_creado_en (creado_en),
    INDEX idx_proveedor_estado (proveedor_id, estado)
);
```

**Estados Posibles:**
```
en_revision     → Estado inicial, requiere decisión
aprobada        → Aprobado manualmente
aprobada_auto   → Aprobado por sistema automáticamente
rechazada       → Rechazado por usuario
pagada          → Procesado para pago
```

**Enums:**
- `tipo_factura`: COMPRA, VENTA, NOTA_CREDITO, NOTA_DEBITO
- `patron_recurrencia`: FIJO, VARIABLE, UNICO, DESCONOCIDO
- `estado_asignacion`: sin_asignar, asignado, huerfano, inconsistente

---

### 5. TABLA: factura_items

**Descripción:** Líneas individuales de facturas (desglose)

```sql
CREATE TABLE factura_items (
    -- Identificación
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    factura_id BIGINT NOT NULL,
    numero_linea INT NOT NULL,

    -- Descripción
    descripcion VARCHAR(2000) NOT NULL,
    codigo_producto VARCHAR(100),

    -- Cantidad y Precio
    cantidad NUMERIC(15,4) DEFAULT 1,
    unidad_medida VARCHAR(50),
    precio_unitario NUMERIC(15,4) NOT NULL,

    -- Montos
    subtotal NUMERIC(15,2) NOT NULL,
    total_impuestos NUMERIC(15,2) DEFAULT 0,
    total NUMERIC(15,2) NOT NULL,

    -- Descuentos
    descuento_porcentaje NUMERIC(5,2),
    descuento_valor NUMERIC(15,2),

    -- Normalización
    descripcion_normalizada VARCHAR(500),
    item_hash VARCHAR(32),  -- MD5 para matching

    -- Clasificación
    categoria VARCHAR(100),  -- software, hardware, cloud, etc.
    es_recurrente BOOLEAN DEFAULT FALSE,

    -- Metadata
    notas VARCHAR(1000),
    creado_en DATETIME DEFAULT NOW(),

    UNIQUE (factura_id, numero_linea),
    FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE,

    INDEX idx_factura_linea (factura_id, numero_linea),
    INDEX idx_item_hash (item_hash, factura_id),
    INDEX idx_descripcion_norm (descripcion_normalizada)
);
```

**Categorías Disponibles:**
- software, hardware, servicio_cloud, conectividad
- energia, consultoria, desarrollo, soporte, capacitacion
- materiales, etc.

---

### 6. TABLA: workflow_aprobacion_facturas

**Descripción:** Ciclo de vida completo de aprobación de facturas

```sql
CREATE TABLE workflow_aprobacion_facturas (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,

    -- Referencias
    factura_id BIGINT NOT NULL UNIQUE,
    responsable_id BIGINT,
    factura_mes_anterior_id BIGINT,

    -- Email
    email_id VARCHAR(255),
    email_asunto VARCHAR(500),
    email_remitente VARCHAR(255),
    email_fecha_recepcion DATETIME,
    nit_proveedor VARCHAR(20),

    -- Estados
    estado ENUM('RECIBIDA', 'EN_ANALISIS', 'APROBADA_AUTO', 'PENDIENTE_REVISION',
                'EN_REVISION', 'APROBADA_MANUAL', 'RECHAZADA', 'PROCESADA') DEFAULT 'RECIBIDA',

    -- Análisis de similitud
    porcentaje_similitud NUMERIC(5,2),
    diferencias_detectadas JSON,

    -- Aprobación
    tipo_aprobacion ENUM('AUTOMATICA', 'MANUAL', 'MASIVA', 'FORZADA'),
    aprobada_por VARCHAR(255),
    fecha_aprobacion DATETIME,

    -- Rechazo
    rechazada_por VARCHAR(255),
    fecha_rechazo DATETIME,
    motivo_rechazo ENUM('MONTO_INCORRECTO', 'SERVICIO_NO_PRESTADO', 'DUPLICADA', 'OTRO'),
    detalle_rechazo TEXT,

    -- Tiempos (en segundos)
    tiempo_en_revision BIGINT,
    tiempo_total_aprobacion BIGINT,

    -- Metadata
    metadata_workflow JSON,

    -- Auditoría
    creado_en DATETIME DEFAULT NOW(),
    actualizado_en DATETIME DEFAULT NOW() ON UPDATE NOW(),

    FOREIGN KEY (factura_id) REFERENCES facturas(id),
    FOREIGN KEY (responsable_id) REFERENCES responsables(id),
    FOREIGN KEY (factura_mes_anterior_id) REFERENCES facturas(id),

    INDEX idx_estado (estado),
    INDEX idx_responsable_id (responsable_id),
    INDEX idx_nit_proveedor (nit_proveedor),
    INDEX idx_estado_responsable (estado, responsable_id)
);
```

---

### 7. TABLA: asignacion_nit_responsable

**Descripción:** Configuración: qué responsable(s) aprueban facturas de cada NIT

```sql
CREATE TABLE asignacion_nit_responsable (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,

    -- Identificación
    nit VARCHAR(20) NOT NULL,
    responsable_id BIGINT NOT NULL,
    nombre_proveedor VARCHAR(255),
    area VARCHAR(100),

    -- Configuración automática
    permitir_aprobacion_automatica BOOLEAN DEFAULT TRUE,
    requiere_revision_siempre BOOLEAN DEFAULT FALSE,

    -- Umbrales
    monto_maximo_auto_aprobacion NUMERIC(15,2),
    porcentaje_variacion_permitido NUMERIC(5,2) DEFAULT 5.0,

    -- Enterprise: Riesgos
    tipo_servicio_proveedor VARCHAR(50),
    nivel_confianza_proveedor VARCHAR(50),
    coeficiente_variacion_historico NUMERIC(7,2),
    requiere_orden_compra_obligatoria BOOLEAN DEFAULT FALSE,

    -- Metadata
    metadata_riesgos JSON,

    -- Estado
    activo BOOLEAN DEFAULT TRUE,

    -- Auditoría
    creado_en DATETIME DEFAULT NOW(),
    actualizado_en DATETIME DEFAULT NOW() ON UPDATE NOW(),

    UNIQUE uq_nit_responsable (nit, responsable_id),
    FOREIGN KEY (responsable_id) REFERENCES responsables(id),

    INDEX idx_nit (nit),
    INDEX idx_responsable (responsable_id),
    INDEX idx_activo (activo)
);
```

**Constraint Importante:**
- Un NIT puede estar asignado a MÚLTIPLES responsables
- Pero NO puede haber duplicado (nit, responsable_id)

---

### 8. TABLA: alertas_aprobacion_automatica

**Descripción:** Sistema de alertas para Fortune 500 compliance - registra alertas incluso en aprobaciones automáticas

```sql
CREATE TABLE alertas_aprobacion_automatica (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    factura_id BIGINT NOT NULL,
    workflow_id BIGINT,

    -- Tipo y severidad
    tipo_alerta VARCHAR(50),  -- CONFIANZA_BORDE, VARIACION_PRECIO, etc.
    severidad VARCHAR(50),    -- BAJA, MEDIA, ALTA, CRITICA

    -- Datos de la alerta
    confianza_calculada NUMERIC(5,2),
    umbral_requerido NUMERIC(5,2),
    diferencia NUMERIC(5,2),
    valor_detectado VARCHAR(255),
    valor_esperado VARCHAR(255),

    -- Gestión
    requiere_revision_urgente BOOLEAN DEFAULT FALSE,
    revisada BOOLEAN DEFAULT FALSE,
    revisada_por VARCHAR(255),
    fecha_revision DATETIME,
    accion_tomada TEXT,

    -- Metadata
    metadata_alerta JSON,

    -- Auditoría
    creado_en DATETIME DEFAULT NOW(),
    actualizado_en DATETIME,

    FOREIGN KEY (factura_id) REFERENCES facturas(id),
    FOREIGN KEY (workflow_id) REFERENCES workflow_aprobacion_facturas(id),

    INDEX idx_pendientes (revisada, severidad, creado_en),
    INDEX idx_tipo_severidad (tipo_alerta, severidad)
);
```

---

### 9. TABLA: historial_pagos

**Descripción:** Análisis histórico de patrones de pago por proveedor

```sql
CREATE TABLE historial_pagos (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,

    -- Identificación
    proveedor_id BIGINT NOT NULL,
    concepto_normalizado VARCHAR(200) NOT NULL,
    concepto_hash VARCHAR(32) NOT NULL,

    -- Tipo de patrón
    tipo_patron ENUM('TIPO_A', 'TIPO_B', 'TIPO_C') NOT NULL,
    -- TIPO_A: Fijo (CV < 5%)
    -- TIPO_B: Fluctuante (CV < 30%)
    -- TIPO_C: Variable (CV > 30%)

    -- Estadísticas (últimos 12 meses)
    pagos_analizados INT NOT NULL DEFAULT 0,
    meses_con_pagos INT NOT NULL DEFAULT 0,

    -- Análisis
    monto_promedio NUMERIC(15,2) NOT NULL,
    monto_minimo NUMERIC(15,2) NOT NULL,
    monto_maximo NUMERIC(15,2) NOT NULL,
    desviacion_estandar NUMERIC(15,2) NOT NULL,
    coeficiente_variacion NUMERIC(5,2) NOT NULL,

    -- Rango esperado
    rango_inferior NUMERIC(15,2),
    rango_superior NUMERIC(15,2),

    -- Recurrencia
    frecuencia_detectada VARCHAR(50),
    ultimo_pago_fecha DATETIME,
    ultimo_pago_monto NUMERIC(15,2),

    -- Detalles
    pagos_detalle JSON,

    -- Control
    fecha_analisis DATETIME DEFAULT NOW(),
    version_algoritmo VARCHAR(20) DEFAULT '1.0',
    puede_aprobar_auto INT DEFAULT 0,
    umbral_alerta NUMERIC(5,2),

    -- Auditoría
    creado_en DATETIME DEFAULT NOW(),
    actualizado_en DATETIME DEFAULT NOW() ON UPDATE NOW(),

    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),

    INDEX idx_proveedor (proveedor_id),
    INDEX idx_concepto_hash (concepto_hash)
);
```

---

### 10. TABLA: cuentas_correo (Email Extraction)

**Descripción:** Cuentas de correo corporativo para extracción de facturas

```sql
CREATE TABLE cuentas_correo (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- Identificación
    email VARCHAR(255) NOT NULL UNIQUE,
    nombre_descriptivo VARCHAR(255),
    organizacion VARCHAR(100),

    -- Configuración extractor
    max_correos_por_ejecucion INT DEFAULT 10000,
    ventana_inicial_dias INT DEFAULT 30,

    -- Tracking
    ultima_ejecucion_exitosa DATETIME,
    fecha_ultimo_correo_procesado DATETIME,

    -- Estado
    activa BOOLEAN DEFAULT TRUE,

    -- Auditoría
    creada_en DATETIME DEFAULT NOW(),
    actualizada_en DATETIME DEFAULT NOW() ON UPDATE NOW(),
    creada_por VARCHAR(100) NOT NULL,
    actualizada_por VARCHAR(100),

    CHECK (max_correos_por_ejecucion > 0 AND max_correos_por_ejecucion <= 100000),
    CHECK (ventana_inicial_dias > 0 AND ventana_inicial_dias <= 365),

    INDEX idx_activa (activa)
);
```

---

### 11. TABLA: nit_configuracion

**Descripción:** NITs configurados por cuenta de correo (qué NITs extraer)

```sql
CREATE TABLE nit_configuracion (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- Referencias
    cuenta_correo_id INT NOT NULL,
    nit VARCHAR(20) NOT NULL,

    -- Información
    nombre_proveedor VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE,
    notas VARCHAR(500),

    -- Auditoría
    creado_en DATETIME DEFAULT NOW(),
    actualizado_en DATETIME DEFAULT NOW() ON UPDATE NOW(),
    creado_por VARCHAR(100) NOT NULL,
    actualizado_por VARCHAR(100),

    UNIQUE (cuenta_correo_id, nit),
    FOREIGN KEY (cuenta_correo_id) REFERENCES cuentas_correo(id),

    INDEX idx_nit_activo (nit, activo)
);
```

---

### 12. TABLA: historial_extracciones

**Descripción:** Log de ejecuciones del extractor de correos

```sql
CREATE TABLE historial_extracciones (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- Referencia
    cuenta_correo_id INT NOT NULL,

    -- Ejecución
    fecha_ejecucion DATETIME DEFAULT NOW(),
    exito BOOLEAN DEFAULT TRUE,
    mensaje_error VARCHAR(1000),
    tiempo_ejecucion_ms INT,

    -- Resultados
    correos_procesados INT DEFAULT 0,
    facturas_encontradas INT DEFAULT 0,
    facturas_creadas INT DEFAULT 0,
    facturas_actualizadas INT DEFAULT 0,
    facturas_ignoradas INT DEFAULT 0,

    -- Configuración usada
    fetch_limit_usado INT,
    fetch_days_usado INT,
    nits_usados INT,
    fecha_desde DATETIME,
    fecha_hasta DATETIME,
    es_primera_ejecucion BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (cuenta_correo_id) REFERENCES cuentas_correo(id),

    INDEX idx_fecha_exito (fecha_ejecucion, exito),
    INDEX idx_cuenta_fecha (cuenta_correo_id, fecha_ejecucion)
);
```

---

### 13. TABLA: lineas_presupuesto (Enterprise)

**Descripción:** Líneas presupuestarias (enterprise presupuesto)

```sql
CREATE TABLE lineas_presupuesto (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,

    -- Identificación
    año INT NOT NULL,
    codigo_linea VARCHAR(50) NOT NULL,
    nombre_cuenta VARCHAR(255) NOT NULL,

    -- Tipo y responsables
    tipo_linea VARCHAR(50),
    responsable_id BIGINT NOT NULL,
    responsable_backup_id BIGINT,

    -- Proveedor relacionado
    proveedor_id BIGINT,

    -- Presupuesto mensual (ene-dic)
    presupuesto_ene NUMERIC(15,2),
    presupuesto_feb NUMERIC(15,2),
    -- ... presupuesto_mar a presupuesto_dic ...
    presupuesto_anual NUMERIC(15,2),  -- Suma automática

    -- Ejecución acumulada
    ejecutado_acumulado NUMERIC(15,2) DEFAULT 0,
    saldo_disponible NUMERIC(15,2) DEFAULT 0,
    porcentaje_ejecucion NUMERIC(5,2) DEFAULT 0,

    -- Control
    estado VARCHAR(50),
    umbral_alerta_pct NUMERIC(5,2) DEFAULT 80,

    -- Aprobación multinivel
    nivel_aprobacion_requerido VARCHAR(50),  -- RESPONSABLE, JEFE, CFO, etc.

    -- Auditoría
    creada_en DATETIME DEFAULT NOW(),
    actualizada_en DATETIME DEFAULT NOW() ON UPDATE NOW(),

    UNIQUE (año, codigo_linea),
    FOREIGN KEY (responsable_id) REFERENCES responsables(id),
    FOREIGN KEY (responsable_backup_id) REFERENCES responsables(id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),

    INDEX idx_año (año),
    INDEX idx_responsable (responsable_id)
);
```

---

### 14. TABLA: ejecuciones_presupuestales (Enterprise)

**Descripción:** Vinculación de facturas a líneas presupuestarias

```sql
CREATE TABLE ejecuciones_presupuestales (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,

    -- Referencias
    linea_presupuesto_id BIGINT NOT NULL,
    factura_id BIGINT NOT NULL,

    -- Período
    período VARCHAR(7),  -- YYYY-MM

    -- Análisis
    desviacion NUMERIC(15,2),
    desviacion_pct NUMERIC(5,2),

    -- Control
    estado VARCHAR(50),  -- OK, ALERTA, CRITICA
    requiere_aprobacion BOOLEAN DEFAULT FALSE,

    -- Auditoría
    creada_en DATETIME DEFAULT NOW(),
    actualizada_en DATETIME DEFAULT NOW() ON UPDATE NOW(),

    FOREIGN KEY (linea_presupuesto_id) REFERENCES lineas_presupuesto(id),
    FOREIGN KEY (factura_id) REFERENCES facturas(id),

    INDEX idx_linea_periodo (linea_presupuesto_id, período),
    INDEX idx_factura (factura_id)
);
```

---

### 15. TABLA: audit_log

**Descripción:** Log de auditoría de todos los cambios

```sql
CREATE TABLE audit_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,

    -- Entidad afectada
    entidad VARCHAR(64) NOT NULL,
    entidad_id BIGINT NOT NULL,

    -- Cambio
    accion VARCHAR(50) NOT NULL,  -- CREATE, UPDATE, DELETE
    usuario VARCHAR(100) NOT NULL,
    detalle JSON,

    -- Timestamp
    creado_en DATETIME(6) DEFAULT NOW(6),

    INDEX idx_entidad (entidad, entidad_id),
    INDEX idx_usuario (usuario),
    INDEX idx_accion (accion),
    INDEX idx_fecha (creado_en)
);
```

---

## 🔗 Modelos SQLAlchemy

Todos los modelos están en `/c/Users/jhont/PRIVADO_ODO/afe-backend/app/models/`

### Convenios SQLAlchemy

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime

class MyModel(Base):
    __tablename__ = "my_table"

    # PK
    id = Column(Integer, primary_key=True, index=True)

    # Atributos
    name = Column(String(100), nullable=False)
    active = Column(Boolean, default=True, index=True)

    # FK
    parent_id = Column(Integer, ForeignKey("parent.id"))

    # Relación
    parent = relationship("Parent", back_populates="children")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 📈 Diagrama E-R

```
┌─────────────────────────────────────────────────────────────────┐
│                  SISTEMA AFE - MODELO ENTIDAD RELACION           │
└─────────────────────────────────────────────────────────────────┘

NÚCLEO:
═══════

    ┌──────────┐         ┌─────────────┐         ┌──────────────┐
    │  roles   │         │ responsables │         │ proveedores  │
    ├──────────┤         ├─────────────┤         ├──────────────┤
    │ id (PK)  │◄────────│ id (PK)     │         │ id (PK)      │
    │ nombre   │ 1:N     │ role_id (FK)│         │ nit (U)      │
    └──────────┘         │ usuario (U) │         │ razon_social │
                         │ email (U)   │         └──────────────┘
                         │ oauth_id    │              ▲
                         │ auth_provi. │              │ 1:N
                         └─────────────┘              │
                                ▲                     │
                                │ 1:N         ┌───────┴──────────┐
                    ┌───────────┴────────┐    │                  │
                    │                    │    │                  │
         ┌──────────┴────────┐  ┌───────┴────┴──────────┐       │
         │   facturas       │  │asignacion_nit_        │       │
         │  (CORE TABLE)    │  │responsable            │       │
         ├─────────────────┤  ├───────────────────────┤       │
         │ id (PK)         │  │ id (PK)               │       │
         │ numero_factura  │  │ nit (FK/U)            │       │
         │ fecha_emision   │  │ responsable_id (FK/U) │       │
         │ proveedor_id───┐│  │ tipo_servicio         │       │
         │ responsable_id├┼┤  │ nivel_confianza       │       │
         │ estado        │ │  │ cv_historico          │       │
         │ estado_asignac│ │  │ activo                │       │
         │ accion_por    │ │  └───────────────────────┘       │
         ├──────────────┤ │          ▲                         │
         │ creado_en    │ │    1:N   │                    1:N  │
         │ actualizado_ │ │         │                         │
         │  en          │ │         │                         │
         └──────────────┘ │         │                         │
              │           │         │                         │
         1:N  │      1:N  │         │         (proveedor)    │
             │           │         │                        │
    ┌────────┘           │  ┌──────┘        ┌─────────────────┘
    │                    │  │               │
┌───┴──────────────┐     │  │    ┌──────────┴──────────────┐
│ factura_items    │     │  │    │workflow_aprobacion_    │
├──────────────────┤     │  │    │   facturas             │
│ id (PK)          │     │  │    ├───────────────────────┤
│ factura_id (FK)──┼─────┤  │    │ id (PK)               │
│ numero_linea (U) │     │  │    │ factura_id (FK, U)────┤
│ descripcion      │     │  │    │ responsable_id (FK)───┤
│ cantidad         │     │  │    │ estado                │
│ precio_unitario  │     │  │    │ tipo_aprobacion       │
│ categoria        │     │  │    │ confianza_calculada   │
│ es_recurrente    │     │  │    │ porcentaje_similitud  │
└──────────────────┘     │  │    └───────────────────────┘
                         │  │          │
                         │  │    1:N   │
                    ┌────┘  │          │
                    │       │    ┌─────┴──────────────┐
                    │       │    │ notificaciones_    │
                    │       │    │  workflow          │
                    │       │    ├───────────────────┤
                    │       │    │ id (PK)           │
                    │       │    │ workflow_id (FK)──┤
                    │       │    │ tipo              │
                    │       │    │ destinatarios (J) │
                    │       │    │ enviada           │
                    │       │    └───────────────────┘
                    │       │
        ┌───────────┴───────┘
        │
    ┌───┴────────────────┐      ┌──────────────────────┐
    │ historial_pagos    │      │ alertas_aprobacion_  │
    ├────────────────────┤      │ automatica           │
    │ id (PK)            │      ├──────────────────────┤
    │ proveedor_id───────┼────┐ │ id (PK)              │
    │ concepto_hash      │    │ │ factura_id (FK)──────┤
    │ tipo_patron        │    │ │ workflow_id (FK)─────┤
    │ cv_historico       │    │ │ tipo_alerta          │
    │ monto_promedio     │    │ │ severidad            │
    │ rango_inferior     │    │ │ revisada             │
    │ rango_superior     │    │ └──────────────────────┘
    │ puede_aprobar_auto │    │
    └────────────────────┘    │
                          (proveedores)

EMAIL EXTRACTION:
════════════════

┌──────────────────┐      ┌─────────────────┐      ┌──────────────────┐
│ cuentas_correo   │◄─────│ nit_configuracion│      │ historial_       │
├──────────────────┤ 1:N  ├─────────────────┤      │ extracciones      │
│ id (PK)          │      │ id (PK)         │      ├──────────────────┤
│ email (U)        │      │ cuenta_correo_  │      │ id (PK)          │
│ max_correos      │      │  id (FK)────────┼─────┬│ cuenta_correo_id  │
│ ventana_dias     │      │ nit             │  1:N││  (FK)            │
│ ultima_ejecucion │      │ activo          │     └│ fecha_ejecucion  │
│ activa           │      └─────────────────┘      │ facturas_creadas │
└──────────────────┘                              │ exito            │
                                                   └──────────────────┘

ENTERPRISE PRESUPUESTO:
═════════════════════

┌──────────────────────────┐      ┌───────────────────────┐
│ lineas_presupuesto       │      │ejecuciones_presupuest│
├──────────────────────────┤      │      ales             │
│ id (PK)                  │      ├───────────────────────┤
│ año + codigo_linea (U)   │      │ id (PK)              │
│ responsable_id (FK)──────┼─────┐│ linea_presupuesto_id │
│ responsable_backup_id    │     ││  (FK)                │
│ proveedor_id (FK)────────┼──┐  ││ factura_id (FK)      │
│ presupuesto_ene...12     │  │  ││ período              │
│ presupuesto_anual        │  │  ││ desviacion           │
│ ejecutado_acumulado  ◄───┼──┼──┼─ (desde items)
│ saldo_disponible         │  │  ││ estado               │
│ porcentaje_ejecucion     │  │  ││ nivel_aprobacion_req │
│ nivel_aprobacion_req     │  │  └┼─ (MULTI-NIVEL)      │
│ estado                   │  │    │
└──────────────────────────┘  │    │
                              │    │
                    (responsable, proveedor)
                              │    │
                         (factura_items)

AUDITORÍA:
═════════

┌──────────────────────┐
│    audit_log         │
├──────────────────────┤
│ id (PK)              │
│ entidad              │
│ entidad_id           │
│ accion               │
│ usuario              │
│ detalle (JSON)       │
│ creado_en            │
└──────────────────────┘
```

---

## 📜 Migraciones Alembic

**Directorio:** `/c/Users/jhont/PRIVADO_ODO/afe-backend/alembic/versions/`

### Orden Cronológico

```
1. da7367e01cd7_initial_migration.py
   └─ Crea: audit_log, proveedores, roles, responsables, facturas

2. 22f577b537a1_agregar_tabla_historial_pagos.py
   └─ Agrega: historial_pagos

3. abc123_add_workflow_tables.py (PHASE 1 - Workflow)
   ├─ workflow_aprobacion_facturas
   ├─ asignacion_nit_responsable
   ├─ notificaciones_workflow
   └─ alertas_aprobacion_automatica

4. 8c6834305516_add_factura_items_table.py
   └─ Agrega: factura_items (desglose de líneas)

5. f6feb264b552_add_presupuesto_tables_enterprise.py
   ├─ lineas_presupuesto
   └─ ejecuciones_presupuestales

6. 2025_10_21_create_integrity_triggers.py
   ├─ auto_update_estado_asignacion
   └─ sync_accion_por_from_workflow

7. 2025_10_22_phase3_add_estado_asignacion_field.py (PHASE 3)
   └─ Agrega: estado_asignacion a facturas

8. Más migraciones de limpieza y optimización...
```

### Comando para Ver Estado

```bash
# Ver estado de migraciones
alembic current

# Ver historial
alembic history

# Aplicar todas las migraciones
alembic upgrade head

# Revertir última migración
alembic downgrade -1
```

---

## 🚀 Índices y Performance

### Índices Estratégicos

**Tabla: facturas**
```sql
-- Búsqueda básica
INDEX idx_estado (estado)
INDEX idx_proveedor_id (proveedor_id)
INDEX idx_responsable_id (responsable_id)

-- Análisis
INDEX idx_concepto_hash (concepto_hash)  -- Crucial para matching

-- Dashboard
INDEX idx_proveedor_estado (proveedor_id, estado)  -- Composite
INDEX idx_responsable_estado (responsable_id, estado)  -- Composite

-- Timeline
INDEX idx_creado_en (creado_en)
```

**Tabla: factura_items**
```sql
-- Identificación
UNIQUE idx_factura_item_linea (factura_id, numero_linea)

-- Búsqueda de items similares
INDEX idx_item_hash (item_hash, factura_id)
INDEX idx_item_descripcion_norm (descripcion_normalizada)

-- Categorización
INDEX idx_recurrente_categoria (es_recurrente, categoria)
```

**Tabla: workflow_aprobacion_facturas**
```sql
-- Búsquedas frecuentes
INDEX idx_estado (estado)
INDEX idx_responsable_id (responsable_id)

-- Composite para dashboard
INDEX idx_estado_responsable (estado, responsable_id)
INDEX idx_nit_fecha (nit_proveedor, email_fecha_recepcion)
```

**Tabla: alertas_aprobacion_automatica**
```sql
-- Alertas pendientes
INDEX idx_pendientes (revisada, severidad, creado_en)

-- Por tipo
INDEX idx_tipo_severidad (tipo_alerta, severidad)
```

### Performance Queries

**Query: Dashboard - Facturas por estado**
```sql
SELECT estado, COUNT(*) as cantidad, SUM(total_a_pagar) as monto
FROM facturas
WHERE creado_en >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY estado;

-- Usa: idx_estado, idx_creado_en
-- Tempo esperado: <100ms
```

**Query: Responsable - Facturas pendientes**
```sql
SELECT COUNT(*) as cantidad, SUM(total_a_pagar) as monto
FROM facturas
WHERE responsable_id = ? AND estado IN ('en_revision', 'aprobada_auto')
ORDER BY creado_en DESC;

-- Usa: idx_responsable_estado
-- Tempo esperado: <50ms
```

---

## 🔒 Triggers y Integridad

### Trigger: auto_update_estado_asignacion

**Ubicación:** Migración 2025_10_21_create_integrity_triggers.py

**Propósito:** Mantener sincronizado estado_asignacion basado en responsable_id

```sql
BEFORE UPDATE ON facturas
FOR EACH ROW
BEGIN
    IF NEW.responsable_id IS NOT NULL THEN
        SET NEW.estado_asignacion = 'asignado';
    ELSEIF NEW.accion_por IS NOT NULL THEN
        SET NEW.estado_asignacion = 'huerfano';
    ELSE
        SET NEW.estado_asignacion = 'sin_asignar';
    END IF;
END
```

### Trigger: sync_accion_por_from_workflow

**Propósito:** Sincronizar accion_por desde workflow hacia facturas

```sql
AFTER UPDATE ON workflow_aprobacion_facturas
FOR EACH ROW
BEGIN
    IF NEW.aprobada_por IS NOT NULL THEN
        UPDATE facturas SET accion_por = NEW.aprobada_por
        WHERE id = NEW.factura_id;
    ELSEIF NEW.rechazada_por IS NOT NULL THEN
        UPDATE facturas SET accion_por = NEW.rechazada_por
        WHERE id = NEW.factura_id;
    END IF;
END
```

---

## 🌱 Datos de Inicialización

### Roles Predefinidos

```sql
INSERT INTO roles (nombre) VALUES
('RESPONSABLE'),
('AUDITOR'),
('ADMIN'),
('VIEWER');
```

### Usuario Admin Inicial

```sql
INSERT INTO responsables (usuario, nombre, email, role_id, hashed_password, auth_provider)
VALUES (
    'admin',
    'Administrador',
    'admin@example.com',
    (SELECT id FROM roles WHERE nombre = 'ADMIN'),
    '[bcrypt_hash_de_password]',
    'local'
);
```

**Script de Inicialización:**
- `/c/Users/jhont/PRIVADO_ODO/afe-backend/app/db/init_db.py`
- `/c/Users/jhont/PRIVADO_ODO/afe-backend/app/scripts/inicializar_sistema_completo.py`

---

##  Queries Críticas

### 1. Dashboard - Resumen por Estado

```sql
SELECT
    f.estado,
    COUNT(*) as cantidad,
    SUM(f.total_a_pagar) as monto_total,
    AVG(f.total_a_pagar) as monto_promedio
FROM facturas f
WHERE f.creado_en >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY f.estado
ORDER BY cantidad DESC;
```

**Índices:** idx_estado, idx_creado_en

### 2. Responsable - Facturas Pendientes

```sql
SELECT
    f.id,
    f.numero_factura,
    p.razon_social,
    f.total_a_pagar,
    f.creado_en,
    f.confianza_automatica
FROM facturas f
INNER JOIN proveedores p ON p.id = f.proveedor_id
WHERE f.responsable_id = ? AND f.estado = 'en_revision'
ORDER BY f.creado_en ASC
LIMIT 50;
```

**Índices:** idx_responsable_estado

### 3. Matching - Factura Idéntica Mes Anterior

```sql
SELECT f2.id, f2.total_a_pagar
FROM facturas f1
INNER JOIN facturas f2 ON (
    f1.proveedor_id = f2.proveedor_id
    AND f1.concepto_hash = f2.concepto_hash
    AND MONTH(f1.fecha_emision) = MONTH(f2.fecha_emision) - 1
)
WHERE f1.id = ?
LIMIT 1;
```

**Índices:** idx_concepto_hash, idx_proveedor_id

### 4. Items Recurrentes

```sql
SELECT
    fi.descripcion_normalizada,
    fi.categoria,
    COUNT(*) as veces_repetido,
    AVG(fi.precio_unitario) as precio_promedio,
    MAX(fi.precio_unitario) as precio_maximo
FROM factura_items fi
WHERE fi.es_recurrente = 1
    AND fi.creado_en >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY fi.descripcion_normalizada, fi.categoria
HAVING COUNT(*) >= 3
ORDER BY COUNT(*) DESC;
```

**Índices:** idx_recurrente_categoria, idx_descripcion_norm

### 5. Alertas Críticas Pendientes

```sql
SELECT
    a.id,
    a.factura_id,
    a.tipo_alerta,
    a.confianza_calculada,
    f.numero_factura,
    f.total_a_pagar,
    p.razon_social
FROM alertas_aprobacion_automatica a
INNER JOIN facturas f ON f.id = a.factura_id
INNER JOIN proveedores p ON p.id = f.proveedor_id
WHERE a.revisada = FALSE AND a.severidad IN ('ALTA', 'CRITICA')
ORDER BY a.creado_en ASC;
```

**Índices:** idx_pendientes

---

## 🔧 Optimizaciones y Mejores Prácticas

### 1. Lazy Loading vs Eager Loading

```python
# En modelos ORM:

# Lazy (por defecto) - carga cuando se accede
items = relationship("FacturaItem", lazy="select")

# Selectin (recomendado para relacionados) - carga en query adicional
items = relationship("FacturaItem", lazy="selectin")

# Joined (para relaciones 1:1) - INNER JOIN
workflow = relationship("WorkflowAprobacionFactura", lazy="joined")
```

### 2. N+1 Query Problem

**❌ MAL:**
```python
facturas = db.query(Factura).all()
for factura in facturas:
    print(factura.proveedor.razon_social)  # N queries adicionales
```

** BIEN:**
```python
facturas = db.query(Factura).options(
    selectinload(Factura.proveedor)
).all()
for factura in facturas:
    print(factura.proveedor.razon_social)  # No hay queries adicionales
```

### 3. Batch Operations

```python
# ❌ Lento: inserción uno por uno
for item_data in items_list:
    item = FacturaItem(**item_data)
    db.add(item)
    db.commit()

#  Rápido: bulk insert
db.bulk_insert_mappings(FacturaItem, items_list)
db.commit()
```

### 4. Query Timeout

```python
# Configurar timeout
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("SET SESSION wait_timeout = 3600")
```

### 5. Índices Útiles a Considerar

```sql
-- Para presupuesto (si hay muchas líneas)
CREATE INDEX idx_linea_presupuesto_año_estado
ON lineas_presupuesto(año, estado);

-- Para búsquedas de alertas por período
CREATE INDEX idx_alerta_fecha_severidad
ON alertas_aprobacion_automatica(creado_en, severidad);

-- Para historial de extracciones
CREATE INDEX idx_extraccion_cuenta_resultado
ON historial_extracciones(cuenta_correo_id, exito, fecha_ejecucion);
```

---

## 📝 Documentación de Campos

### estado (facturas)

**Valores:**
```
en_revision    - Estado inicial, requiere decisión
aprobada       - Aprobado por usuario manualmente
aprobada_auto  - Aprobado por sistema automáticamente
rechazada      - Rechazado por usuario
pagada         - Enviado a contabilidad para pago
```

**Transiciones válidas:**
```
en_revision  → aprobada | aprobada_auto | rechazada
aprobada     → pagada
aprobada_auto → pagada
rechazada    → (se puede reenviar como en_revision)
```

### confianza_automatica (0.00-1.00)

- < 0.80: NO auto-aprobar, requiere revisión
- 0.80-0.95: Auto-aprobar con precaución, generar alerta
- > 0.95: Auto-aprobar con confianza alta

**Cálculo basado en:**
- Similitud con factura anterior (%)
- Coeficiente de variación histórica (CV%)
- Nivel de confianza del proveedor (1-5)
- Presencia de orden de compra

### estado_asignacion (PHASE 3)

- `sin_asignar`: No tiene responsable asignado
- `asignado`: Tiene responsable activo
- `huerfano`: Tiene registro pero responsable fue removido
- `inconsistente`: Estado anómalo (para auditoría)

**Lógica:**
```python
if responsable_id is not None:
    estado = 'asignado'
elif accion_por is not None:
    estado = 'huerfano'
else:
    estado = 'sin_asignar'
```

### tipo_patron (historial_pagos)

- TIPO_A: Fijo - CV < 5%
- TIPO_B: Fluctuante - CV < 30%
- TIPO_C: Variable - CV > 30%

---

## 🛠️ Mantenimiento y Administración

### Backups

```bash
# Backup completo
mysqldump -u user -p database_name > backup_$(date +%Y%m%d).sql

# Backup con compresión
mysqldump -u user -p database_name | gzip > backup_$(date +%Y%m%d).sql.gz

# Restaurar
mysql -u user -p database_name < backup_file.sql
```

### Monitoreo

```sql
-- Tamaño de tabla
SELECT
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.TABLES
WHERE table_schema = 'afe_database'
ORDER BY size_mb DESC;

-- Índices no usados
SELECT object_schema, object_name, count_read, count_write, count_delete
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE object_schema = 'afe_database'
AND count_read = 0
ORDER BY count_write DESC;
```

### Mantenimiento Preventivo

```sql
-- Optimizar tablas (reduce fragmentación)
OPTIMIZE TABLE facturas;
OPTIMIZE TABLE factura_items;
OPTIMIZE TABLE workflow_aprobacion_facturas;

-- Analizar estadísticas
ANALYZE TABLE facturas;
ANALYZE TABLE factura_items;

-- Verificar integridad
CHECK TABLE facturas;
REPAIR TABLE facturas;
```

---

##  Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Tablas Principales** | 14 + 3 auditoría |
| **Relaciones** | 1:1, 1:N, M:N |
| **Índices** | 30+ |
| **Triggers** | 2+ |
| **Migraciones** | 40+ |
| **Modelos SQLAlchemy** | 12 |
| **Estado** | Production Ready |

---

**Documento generado:** Noviembre 2024
**Versión BD:** 2025_10_23
**Licencia:** MIT
