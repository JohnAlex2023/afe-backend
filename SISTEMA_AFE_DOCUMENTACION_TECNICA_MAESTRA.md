# Sistema AFE - Documentación Técnica Maestra

**Versión:** 2.0 (Sistema Unificado y Refactorizado)
**Estado:** Producción
**Nivel:** Enterprise
**Fecha de Consolidación:** 2024-10-29

---

## Resumen Ejecutivo

Este documento es la **fuente única y definitiva de verdad** para el sistema AFE (Advanced Financial Engine). Consolida toda la documentación de arquitectura, diseño, operación y mantenimiento en un solo lugar.

El sistema AFE es una solución de nivel empresarial para la **automatización de la gestión de facturas electrónicas**. Su arquitectura de 3 capas desacopladas permite la extracción automática de facturas desde buzones de correo, su procesamiento mediante un motor de reglas de negocio, y su gestión a través de una moderna interfaz web. El sistema está diseñado para ser robusto, escalable y mantenible, siguiendo los más altos estándares de la industria.

---

## 1. Arquitectura General del Sistema

El sistema AFE está diseñado bajo una arquitectura de **3 capas desacopladas**, comunicándose a través de APIs REST y una base de datos centralizada. Esto permite que cada componente evolucione de forma independiente, facilitando el mantenimiento y la escalabilidad.

### 1.1. Componentes Principales

1.  **`invoice_extractor` (Módulo de Extracción):** Un servicio *worker* independiente cuya única responsabilidad es conectarse a buzones de correo vía Microsoft Graph API, descargar facturas (XML/PDF), parsearlas y guardarlas en la base de datos en un estado inicial (`PENDIENTE`).
2.  **`bd_afe` (Base de Datos):** El corazón del sistema, una base de datos **MySQL 8.0+** que centraliza toda la información: facturas, proveedores, usuarios, configuraciones y logs de auditoría. Actúa como el punto de comunicación indirecto entre el extractor y el backend.
3.  **`afe-backend` (API y Lógica de Negocio):** Un servidor de API basado en **FastAPI** que expone endpoints para gestionar el sistema. Contiene toda la lógica de negocio: workflows de aprobación, gestión de usuarios, autenticación (local y OAuth), exportaciones y servicios de automatización.
4.  **`afe_frontend` (Interfaz de Usuario):** Una aplicación de página única (SPA) construida con **React y TypeScript**. Consume la API del `afe-backend` para presentar los datos a los usuarios y permitirles interactuar con el sistema.

### 1.2. Flujo de Datos y Comunicación

```mermaid
graph TD
    subgraph "Buzón de Correo (Microsoft 365)"
        A[Facturas en Email]
    end

    subgraph "Módulo Independiente"
        B(invoice_extractor)
    end

    subgraph "Base de Datos Central"
        C[bd_afe (MySQL)]
    end

    subgraph "Servidor Principal"
        D{afe-backend (FastAPI)}
    end

    subgraph "Cliente Web"
        E[afe_frontend (React)]
    end

    subgraph "Autenticación Externa"
        F[Microsoft Azure AD]
    end

    A --1. Extrae XML/PDF vía MS Graph API--> B
    B --2. Inserta Factura (Estado: PENDIENTE)--> C
    D --3. Lee/Escribe datos--> C
    E --4. Llama a API REST--> D
    D --5. Retorna JSON--> E
    E --6a. Redirige a Login Microsoft--> F
    F --6b. Retorna código de autorización--> E
    E --6c. Envía código a Backend--> D
    D --6d. Valida con Azure AD y crea sesión JWT--> F
```

1.  **Extracción:** `invoice_extractor` se ejecuta periódicamente (cronjob), consulta correos nuevos, extrae adjuntos de facturas y los inserta en `bd_afe`.
2.  **Procesamiento:** `afe-backend` contiene lógica (`WorkflowAutomaticoService`) que procesa las facturas `PENDIENTES`, aplicando reglas de negocio y actualizando su estado.
3.  **Interacción del Usuario:** `afe_frontend` consulta al `afe-backend` para mostrar el estado de las facturas. Las acciones del usuario (ej. aprobar manualmente) se envían como peticiones API al backend, que a su vez actualiza la base de datos.
4.  **Autenticación:** El sistema soporta dos métodos:
    *   **Local:** Usuario/contraseña almacenados de forma segura en `bd_afe`.
    *   **OAuth 2.0 con Microsoft:** El frontend inicia un flujo con Azure AD. El backend valida el callback, obtiene la información del usuario, lo crea/actualiza en `bd_afe` y emite un token JWT para la sesión.

---

## 2. Descripción Técnica de Módulos

### 2.1. Módulo `invoice_extractor` (Extracción de Facturas)

*   **Propósito:** Automatizar la ingesta de facturas desde buzones de correo de Microsoft 365. Es un sistema "tonto" enfocado únicamente en extraer y depositar.
*   **Tecnologías:** Python, Microsoft Graph API (vía MSAL).
*   **Estructura Interna:**
    *   `src/main.py`: Punto de entrada que orquesta el proceso.
    *   `src/graph_client.py`: Cliente para autenticarse y comunicarse con Microsoft Graph API.
    *   `src/parser.py`: Lógica para parsear los archivos XML.
    *   `src/database.py`: Conexión directa a `bd_afe` para insertar las facturas.
*   **Proceso Clave (Extracción Incremental):**
    1.  Lee de la tabla `cuentas_correo` la fecha del último correo procesado.
    2.  En ejecuciones posteriores, solo pide a Graph API los correos recibidos *después* de esa fecha, evitando procesar datos duplicados.
    3.  Al finalizar, actualiza `fecha_ultimo_correo_procesado` en `cuentas_correo`.
*   **Configuración (`.env`):**
    ```bash
    # Credenciales de la App Registration en Azure AD para MS Graph
    TENANT_ID_CORREOS=...
    CLIENT_ID_CORREOS=...
    CLIENT_SECRET_CORREOS=...
    # Conexión a la base de datos
    DATABASE_URL=mysql+pymysql://user:pass@host:3306/afe_db
    ```

### 2.2. Módulo `afe-backend` (API y Lógica de Negocio)

*   **Propósito:** Servir como el cerebro del sistema. Expone una API REST segura y contiene toda la lógica de negocio.
*   **Tecnologías:** FastAPI, Python, SQLAlchemy (ORM), Alembic (Migraciones), Pydantic (Validación).
*   **Estructura Interna (`app/`):**
    *   `api/v1/routers/`: Define los endpoints REST (ej. `facturas.py`, `workflow.py`, `auth.py`).
    *   `crud/`: Operaciones de base de datos (Crear, Leer, Actualizar, Borrar).
    *   `models/`: Define las tablas de la base de datos como clases de SQLAlchemy.
    *   `schemas/`: Define las formas de los datos de entrada/salida de la API usando Pydantic.
    *   `services/`: Contiene la lógica de negocio compleja (ej. `workflow_automatico.py`, `export_service.py`, `microsoft_oauth_service.py`).
    *   `core/`: Configuración central, seguridad y conexión a la base de datos.
    *   `main.py`: Punto de entrada de la aplicación FastAPI.
*   **Procesos Clave:**
    *   **Workflow de Aprobación:** Un servicio (`WorkflowAutomaticoService`) que toma facturas `PENDIENTES`, las compara con historiales, aplica reglas configurables y decide si se `APRUEBA_AUTO` o se envía a `PENDIENTE_REVISION`.
    *   **Autenticación Dual:** El router `auth.py` gestiona tanto el login local (con JWT) como el flujo OAuth 2.0 con Microsoft.
    *   **Exportación Optimizada:** El servicio `export_service.py` genera reportes de Excel de grandes volúmenes de datos de forma eficiente.
*   **Configuración (`.env`):**
    ```bash
    DATABASE_URL=mysql+pymysql://user:pass@host:3306/afe_db
    SECRET_KEY=...
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    ALLOWED_ORIGINS=http://localhost:5173
    # Credenciales OAuth (ver sección 4)
    OAUTH_MICROSOFT_TENANT_ID=...
    OAUTH_MICROSOFT_CLIENT_ID=...
    OAUTH_MICROSOFT_CLIENT_SECRET=...
    OAUTH_MICROSOFT_REDIRECT_URI=http://localhost:5173/auth/microsoft/callback
    ```

### 2.3. Módulo `afe_frontend` (Interfaz de Usuario)

*   **Propósito:** Proporcionar una interfaz web moderna, reactiva y fácil de usar.
*   **Tecnologías:** React, TypeScript, Redux Toolkit (Gestión de estado), Axios (Cliente HTTP).
*   **Estructura Interna (`src/`):**
    *   `features/`: Organiza el código por funcionalidad (ej. `auth/`, `dashboard/`). Cada feature contiene sus componentes, slices de Redux y estilos.
    *   `services/`: Define la comunicación con la API del backend (ej. `facturas.api.ts`, `microsoftAuth.service.ts`).
    *   `components/`: Componentes de UI reutilizables.
    *   `app/`: Configuración de Redux store, rutas y layout principal.
    *   `AppRoutes.tsx`: Define las rutas públicas y privadas de la aplicación.
*   **Procesos Clave:**
    *   **Login y Callback:** La `LoginPage.tsx` presenta las opciones de login. Al usar Microsoft, redirige al usuario. La `MicrosoftCallbackPage.tsx` maneja el retorno, extrae el código de autorización y lo envía al backend para obtener el token de sesión.
    *   **Gestión de Estado Global:** Redux Toolkit se usa para mantener un estado global consistente (información del usuario, token, etc.).
*   **Configuración (`.env`):**
    ```bash
    VITE_API_BASE_URL=http://localhost:8000/api/v1
    ```

---

## 3. Diseño de la Base de Datos (`bd_afe`)

La base de datos es el pilar del sistema. Tras un análisis senior, se han identificado fortalezas y áreas de mejora para evolucionar hacia una arquitectura de nivel Fortune 500.

### 3.1. Modelo Entidad-Relación (Simplificado)

```mermaid
erDiagram
    clientes {
        int id PK
        string nit UK
        string nombre
    }

    facturas {
        int id PK
        string numero_factura
        date fecha_emision
        decimal total_factura
        string estado_aprobacion
        int cliente_id FK
        int responsable_id FK
        string accion_por "Sincronizado"
    }

    factura_items {
        int id PK
        int factura_id FK
        string descripcion
        decimal cantidad
        decimal precio_unitario
    }

    responsables {
        int id PK
        string nombre
        string email UK
        string auth_provider "local/microsoft"
        string oauth_id UK
    }

    asignacion_nit_responsable {
        int id PK
        string nit UK
        int responsable_id FK
        bool permitir_aprobacion_automatica
    }

    workflow_aprobacion_facturas {
        int id PK
        int factura_id FK
        string estado "Detallado"
        string aprobada_por
        string rechazada_por
    }

    clientes ||--o{ facturas : "tiene"
    facturas ||--|{ factura_items : "contiene"
    responsables ||--o{ asignacion_nit_responsable : "tiene asignado"
    facturas ||--o{ workflow_aprobacion_facturas : "es detallado por"
    responsables ||--o{ facturas : "es responsable de"
```

### 3.2. Tablas Principales y Decisiones de Diseño

*   **`facturas`**: Almacena la información principal de cada factura. **Decisión de Diseño**: Esta tabla contiene algunos campos redundantes (`aprobado_por`, `fecha_aprobacion`, etc.) que se sincronizan desde `workflow_aprobacion_facturas`. Esto es un *trade-off* intencional para optimizar el rendimiento de lectura del dashboard principal, evitando JOINS costosos. La sincronización es automática y transaccional para garantizar la consistencia.
*   **`clientes`**: Catálogo de proveedores, identificado unívocamente por su `nit`.
*   **`responsables`**: Usuarios del sistema. Soporta autenticación local y externa (`oauth_id`).
*   **`asignacion_nit_responsable`**: **Fuente única de verdad** para mapear un `nit` de proveedor a un `responsable`. Esta tabla es el resultado de una refactorización mayor que eliminó la tabla duplicada `responsable_proveedor`.
*   **`workflow_aprobacion_facturas`**: Registra cada paso del proceso de aprobación. Es la **fuente de verdad** para los detalles de auditoría del workflow.

### 3.3. Patrón de Eliminación (Hard Delete)

Para la tabla `asignacion_nit_responsable`, se ha adoptado un patrón de **Hard Delete**.
*   **Antes**: Se usaba Soft Delete (`activo = FALSE`), dejando registros "fantasma".
*   **Ahora**: `DELETE /asignacion-nit/{id}` elimina el registro por completo. Esto simplifica la lógica de la aplicación, ya que no necesita filtrar registros inactivos. Para reasignar, se debe crear un nuevo registro.

---

## 4. Autenticación Corporativa con Microsoft OAuth 2.0

El sistema implementa un flujo de autenticación de nivel empresarial utilizando Microsoft Azure AD, permitiendo un inicio de sesión corporativo seguro y profesional.

### 4.1. Flujo de Autenticación

1.  **Inicio (Frontend):** El usuario hace clic en "Continuar con Microsoft". El frontend llama al endpoint `GET /api/v1/auth/microsoft/authorize` del backend.
2.  **Generación de URL (Backend):** El backend genera una URL de autorización única de Microsoft, incluyendo un parámetro `state` para protección CSRF, y la devuelve al frontend.
3.  **Redirección a Microsoft:** El frontend redirige al usuario a la página de inicio de sesión de Microsoft.
4.  **Consentimiento y Código:** El usuario inicia sesión y (la primera vez) consiente los permisos. Microsoft redirige de vuelta al frontend a la `OAUTH_MICROSOFT_REDIRECT_URI` (`/auth/microsoft/callback`), incluyendo un `code` de autorización.
5.  **Intercambio de Código (Frontend -> Backend):** La página de callback del frontend envía el `code` al endpoint `GET /api/v1/auth/microsoft/callback` del backend.
6.  **Validación y Creación de Sesión (Backend):**
    a.  El backend intercambia el `code` con Microsoft por un `access_token`.
    b.  Usa el `access_token` para obtener la información del usuario desde Microsoft Graph API.
    c.  Busca al usuario en la tabla `responsables` por email.
        *   Si no existe, lo crea.
        *   Si existe, vincula su cuenta actualizando los campos `auth_provider` y `oauth_id`.
    d.  Genera un **token JWT** interno para la sesión del usuario.
    e.  Devuelve el token JWT y los datos del usuario al frontend.
7.  **Sesión Activa (Frontend):** El frontend almacena el token JWT (en Redux/memoria) y redirige al usuario al dashboard, ahora autenticado.

### 4.2. Configuración en Azure AD

Se utiliza una **única App Registration** en Azure AD para gestionar tanto el envío de correos (Graph API) como la autenticación OAuth.

*   **App Registration ID:** `79dc4cdc-137b-415f-8193-a7a5b3fdd47b`
*   **Redirect URIs:**
    *   Desarrollo: `http://localhost:5173/auth/microsoft/callback`
    *   Producción: `https://afe.zentria.com/auth/microsoft/callback`
*   **API Permissions (Delegated):**
    *   `Mail.Send` (para notificaciones)
    *   `openid`, `email`, `profile`, `User.Read` (para autenticación)

---

## 5. Flujo Funcional Completo y Automatización

El sistema está diseñado para automatizar el ciclo de vida de las facturas recurrentes.

### 5.1. Ejemplo de Flujo: Procesamiento Automático de una Factura

1.  **Recepción del Correo:** Un proveedor envía una factura al buzón configurado.
2.  **Extracción:** El `invoice_extractor` se ejecuta, detecta el nuevo correo, descarga el XML, lo parsea y crea un registro en `facturas` con `estado_aprobacion = 'PENDIENTE'`.
3.  **Detección por el Backend:** Un script programado (`POST /api/v1/facturas/admin/trigger-automation`) o una tarea `cron` busca facturas en estado `PENDIENTE`.
4.  **Inicio del Workflow de Automatización (`AutomationService`):**
    a.  **Generación de Huella Digital (`FingerprintGenerator`):** Se crea una "huella digital" para la factura basada en su concepto normalizado.
    b.  **Búsqueda de Patrones (`PatternDetector`):** El sistema busca facturas históricas con la misma huella para detectar patrones de recurrencia, temporalidad y montos.
    c.  **Motor de Decisión (`DecisionEngine`):** Se evalúan múltiples criterios con pesos configurables (recurrencia, estabilidad del monto, confianza en el proveedor, etc.) para calcular un **puntaje de confianza**.
5.  **Toma de Decisión:**
    *   **Caso A (Aprobación Automática):** Si el puntaje de confianza supera el umbral (ej. > 85%), el estado se actualiza a `APROBADA_AUTO`.
    *   **Caso B (Revisión Manual):** Si el puntaje es bajo, el estado se actualiza a `PENDIENTE_REVISION` y se notifica al responsable asignado.
6.  **Visualización y Acción Manual (si es necesario):**
    *   El responsable ve la factura en su dashboard en `afe_frontend`.
    *   La revisa y hace clic en "Aprobar".
    *   El frontend envía una petición `POST /api/v1/facturas/{id}/aprobar`.
7.  **Finalización:** El backend actualiza el estado a `APROBADA_MANUAL`. El ciclo para esa factura ha terminado.

### 5.2. Endpoint de Disparo Manual para Automatización

Para facilitar el testing y la operación, se dispone de un endpoint de administrador que dispara el proceso de automatización bajo demanda.

*   **Endpoint:** `POST /api/v1/facturas/admin/trigger-automation`
*   **Autenticación:** Requiere rol de Administrador.
*   **Respuesta:** Devuelve estadísticas detalladas del proceso, incluyendo cuántas facturas fueron procesadas, cuántas se aprobaron automáticamente y cuántas se enviaron a revisión.

---

## 6. Diseño y Patrones de Desarrollo

### 6.1. Arquitectura y Estándares

*   **Arquitectura de Capas (Backend):**
    *   **Capa de API (`routers`):** Maneja las peticiones HTTP y la validación inicial.
    *   **Capa de Servicio (`services`):** Contiene la lógica de negocio.
    *   **Capa de Acceso a Datos (`crud`):** Abstrae las operaciones de base de datos.
    *   **Capa de Modelo (`models`):** Representa la estructura de la base de datos.
*   **Inyección de Dependencias (FastAPI):** Se utiliza para gestionar las sesiones de base de datos y otras dependencias, facilitando las pruebas y el desacoplamiento.
*   **Single Source of Truth (SSoT):** Se han realizado esfuerzos significativos para unificar la lógica y eliminar la duplicación. La tabla `asignacion_nit_responsable` es ahora la SSoT para las asignaciones. El `workflow_aprobacion_facturas` es la SSoT para la auditoría de aprobación.
*   **Estándares de Código:** Se utilizan herramientas como `black` para formateo y `flake8` para linting, asegurando un estilo de código consistente.

### 6.2. Salud y Mantenimiento del Código

El sistema ha pasado por un **proceso de limpieza exhaustivo** para eliminar código muerto, scripts experimentales y redundancias.

*   **Scripts Archivados:** Más de 30 scripts de diagnóstico, prueba y sincronización experimental han sido movidos a una carpeta `_archive/`.
*   **Scripts Activos (4):** Solo se mantienen los scripts esenciales para la operación del sistema:
    1.  `create_user.py`: Para crear usuarios iniciales.
    2.  `reset_password.py`: Para resetear contraseñas.
    3.  `migrate_settings_to_db.py`: Para migraciones de configuración legacy.
    4.  `limpiar_asignaciones_inactivas.py`: Para limpiar datos antes de la transición a Hard Delete.
*   **Código Obsoleto Eliminado:** Se han eliminado funciones `deprecated` y servicios huérfanos, reduciendo la complejidad y mejorando la mantenibilidad.

### 6.3. Sincronización del Campo `accion_por`

Para garantizar la consistencia en el dashboard, el campo `facturas.accion_por` (quién realizó la última acción) sigue un patrón de diseño estricto:

1.  El campo **nunca se actualiza manualmente** desde la API.
2.  Es **sincronizado automáticamente** por el `WorkflowAutomaticoService` dentro de la misma transacción de base de datos cuando una factura es aprobada o rechazada.
3.  La fuente de verdad es `workflow_aprobacion_facturas.aprobada_por` o `rechazada_por`.
4.  Esto asegura que el dashboard siempre muestre el nombre correcto de quién ejecutó la acción, diferenciándolo del `responsable` (quién estaba asignado).

---

## 7. Instalación y Despliegue

### 7.1. Configuración Local

#### Backend (`afe-backend`)

```bash
# 1. Clonar y entrar al proyecto
cd afe-backend

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno (copiar .env.example a .env y editar)
cp .env.example .env

# 5. Aplicar migraciones de base de datos
alembic upgrade head

# 6. Levantar servidor de desarrollo
uvicorn app.main:app --reload --port 8000
```
*   **Servidor corriendo en:** `http://localhost:8000`
*   **Documentación API (Swagger):** `http://localhost:8000/docs`

#### Frontend (`afe_frontend`)

```bash
# 1. Entrar al proyecto
cd afe_frontend

# 2. Instalar dependencias
npm install

# 3. Configurar variables de entorno (crear .env y añadir VITE_API_BASE_URL)
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env

# 4. Levantar servidor de desarrollo
npm run dev
```
*   **Frontend corriendo en:** `http://localhost:5173`

### 7.2. Despliegue en Producción

*   **Backend:** Se recomienda usar `Gunicorn` con `UvicornWorker` para ejecutar la aplicación FastAPI detrás de un reverse proxy como `Nginx`. Docker es la opción preferida para empaquetar y desplegar.
*   **Frontend:** Se compila en archivos estáticos (`npm run build`) que pueden ser servidos por `Nginx` o un servicio de hosting de sitios estáticos (ej. S3, Vercel).
*   **Extractor:** Se ejecuta como una tarea programada (`cronjob` en Linux o Tareas Programadas en Windows) que invoca el script de Python a intervalos regulares.

---

## 8. Resumen Final y Diagrama de Interacción

El sistema AFE es una solución completa y profesional para la automatización de facturas. Su arquitectura modular, flujos de trabajo automatizados y autenticación corporativa lo posicionan como una herramienta de nivel empresarial. Los procesos de refactorización y limpieza garantizan que la base de código sea mantenible y escalable a futuro.

### Diagrama Conceptual de Interacción

```text
                               +--------------------------------+
                               |      Microsoft Azure AD        |
                               | (Para Autenticación OAuth)     |
                               +----------------+---------------+
                                                ^
                                                | 6. Flujo OAuth
                                                v
+----------------------+       +--------------------------------+       +----------------------+
| INVOICE_EXTRACTOR    |       |         AFE_FRONTEND           |       | Buzón de Correo      |
| (Python Worker)      |------>| (React SPA)                    |<------| (Microsoft 365)      |
| - Lee de MS Graph    |       | - Dashboard de Facturas        |       | - Recibe Facturas    |
| - Parsea XML         |       | - Gestión de Asignaciones      |       +----------------------+
| - Inserta en BD      |       | - Login (Local/OAuth)          |
+----------------------+       +----------------+---------------+
          |                                     ^
          | 1. Inserta Facturas                 | 4. API REST (JSON)
          v                                     v
+----------------------+       +--------------------------------+
|      BD_AFE          |       |          AFE_BACKEND           |
| (MySQL Database)     |<----->| (FastAPI Server)               |
| - Fuente de Verdad   | 3. Lee/| - Lógica de Workflow           |
| - Almacena todo      | Escribe| - API RESTful                  |
+----------------------+       | - Autenticación JWT/OAuth      |
                               | - Servicios de Automatización  |
                               +--------------------------------+
```

---

**Fin del Documento Maestro.**
