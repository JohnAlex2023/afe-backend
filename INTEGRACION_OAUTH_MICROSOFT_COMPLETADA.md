# Integración OAuth Microsoft - COMPLETADA

## Estado: Implementación Completa - Listo para Testing

La integración de autenticación OAuth con Microsoft Azure AD ha sido completada exitosamente en ambos frontend y backend del sistema ZENTRIA AFE.

---

## Resumen Ejecutivo

**Objetivo Alcanzado**: Sistema de login profesional y corporativo de nivel Fortune 500 con autenticación dual:
- Autenticación tradicional (usuario/contraseña)
- Autenticación OAuth con Microsoft (Azure AD)

**Diseño**: Interfaz completamente rediseñada con estándares corporativos enterprise:
- Branding oficial de Microsoft
- Animaciones y transiciones suaves
- Badges enterprise (Enterprise, Secure)
- Iconografía profesional
- Espaciado y tipografía mejorados

---

## Archivos Implementados

### Backend (afe-backend)

1. **`app/core/config.py`** - Configuración OAuth
   - Variables de entorno para OAuth Microsoft
   - Reutiliza credenciales existentes del Graph API

2. **`app/models/responsable.py`** - Modelo actualizado
   - Campo `auth_provider` (local/microsoft)
   - Campo `oauth_id` (identificador único de Microsoft)
   - Campo `oauth_picture` (URL de foto de perfil)
   - `hashed_password` ahora nullable para usuarios OAuth

3. **`alembic/versions/oauth_support_responsables_clean.py`** - Migración limpia
   - Agrega campos OAuth a tabla `responsables`
   - Índice único en `oauth_id`
   - Migración lista para ejecutar

4. **`app/services/microsoft_oauth_service.py`** - Servicio OAuth completo
   - Integración con MSAL (Microsoft Authentication Library)
   - Manejo de scopes (filtra scopes reservados)
   - Obtención de token y información de usuario
   - Creación/actualización automática de usuarios

5. **`app/api/v1/routers/auth.py`** - Endpoints OAuth
   - `GET /auth/microsoft/authorize` - Inicia flujo OAuth
   - `GET /auth/microsoft/callback` - Callback OAuth
   - Protección CSRF con parámetro `state`

6. **`requirements.txt`** - Dependencias actualizadas
   - `authlib` - Cliente OAuth genérico
   - `msal` - Microsoft Authentication Library

### Frontend (afe_frontend)

1. **`src/services/microsoftAuth.service.ts`** - Servicio OAuth frontend
   - Manejo completo del flujo OAuth
   - Validación de estado CSRF
   - Intercambio de código por token

2. **`src/features/auth/LoginPage.tsx`** - Login rediseñado
   - Diseño corporativo Fortune 500
   - Botón Microsoft con branding oficial
   - Badges Enterprise y Secure
   - Animaciones flotantes
   - Mantiene funcionalidad existente (rate limiting, recuperación)

3. **`src/features/auth/MicrosoftCallbackPage.tsx`** - Página de callback
   - Estados: loading, success, error
   - Redirección automática al dashboard
   - Manejo de errores con opción de reintentar

4. **`src/AppRoutes.tsx`** - Rutas actualizadas
   - Ruta pública: `/auth/microsoft/callback`
   - Integrada en configuración de rutas existente

### Documentación

1. **`docs/CONFIGURACION_AZURE_AD_ZENTRIA.md`**
   - Guía paso a paso para configurar Azure AD
   - Específica para ZENTRIA
   - Incluye URIs de redirección y permisos

2. **`docs/AZURE_AD_OAUTH_SETUP.md`**
   - Documentación técnica detallada
   - Arquitectura y flujos

---

## Configuración Actual

### Variables de Entorno (Backend `.env`)

```bash
# OAuth Microsoft - Reutilizando credenciales existentes
OAUTH_MICROSOFT_TENANT_ID=c9ef7bf6-bbe0-4c50-b2e9-ea58d635ca46
OAUTH_MICROSOFT_CLIENT_ID=79dc4cdc-137b-415f-8193-a7a5b3fdd47b
OAUTH_MICROSOFT_CLIENT_SECRET=M6q8Q~_g4puSEYy_gV4OmCAAk2r7oilOxXXpJc_~
OAUTH_MICROSOFT_REDIRECT_URI=http://localhost:3000/auth/microsoft/callback
OAUTH_MICROSOFT_SCOPES=openid email profile User.Read
```

**Nota**: Estas credenciales son las mismas usadas para Microsoft Graph API (notificaciones por correo). Decisión de arquitectura senior: usar UN SOLO App Registration para ambos propósitos.

---

## Pasos Pendientes para Activar OAuth

### 1. Ejecutar Migración de Base de Datos

```bash
cd afe-backend
./venv/Scripts/activate
alembic upgrade head
```

Esto agregará los campos OAuth a la tabla `responsables`.

### 2. Configurar Azure AD Portal

Acceder a: https://portal.azure.com

**App Registration ID**: `79dc4cdc-137b-415f-8193-a7a5b3fdd47b`

#### a) Agregar URI de Redirección

1. Ir a **Authentication** → **Platform configurations**
2. Agregar plataforma **Web**
3. Agregar Redirect URI:
   - Desarrollo: `http://localhost:3000/auth/microsoft/callback`
   - Producción: `https://tu-dominio.com/auth/microsoft/callback`

#### b) Verificar Permisos API

1. Ir a **API permissions**
2. Verificar que estén agregados:
   - `User.Read` (Microsoft Graph)
   - `email` (OpenID)
   - `profile` (OpenID)
   - `openid` (OpenID)
3. Si no están, agregar y dar **Admin consent**

#### c) Habilitar ID tokens

1. Ir a **Authentication**
2. En **Implicit grant and hybrid flows**
3. Marcar **ID tokens**

### 3. Verificar Backend

```bash
cd afe-backend
./venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Verificar endpoints:
- http://localhost:8000/api/v1/auth/microsoft/authorize
- http://localhost:8000/api/v1/auth/microsoft/callback

### 4. Verificar Frontend

```bash
cd afe_frontend
npm start
```

Verificar:
- Página de login con botón Microsoft
- Diseño corporativo enterprise
- Callback page funcional

---

## Flujo OAuth Completo

### 1. Usuario hace clic en "Continuar con Microsoft"

```
LoginPage → microsoftAuthService.loginWithMicrosoft()
```

### 2. Backend genera URL de autorización

```
GET /auth/microsoft/authorize
→ Retorna: {authorization_url, state}
```

### 3. Usuario es redirigido a Microsoft

```
Microsoft Login → Consentimiento → Callback
```

### 4. Microsoft redirige al callback

```
http://localhost:3000/auth/microsoft/callback?code=xxx&state=yyy
```

### 5. Frontend valida y obtiene token

```
MicrosoftCallbackPage → microsoftAuthService.handleCallback()
→ GET /auth/microsoft/callback?code=xxx&state=yyy
```

### 6. Backend procesa callback

```
1. Valida código y estado
2. Obtiene token de Microsoft
3. Obtiene info de usuario (email, nombre, foto)
4. Busca o crea usuario en BD
5. Genera JWT token
6. Retorna token al frontend
```

### 7. Frontend guarda sesión

```
dispatch(setCredentials({token, usuario}))
→ Redirige a /dashboard
```

---

## Testing Manual

### Caso 1: Usuario nuevo con Microsoft

1. Ir a http://localhost:3000/login
2. Hacer clic en "Continuar con Microsoft"
3. Iniciar sesión con cuenta Microsoft
4. Verificar redirección a dashboard
5. Verificar que usuario aparece en BD con:
   - `auth_provider = 'microsoft'`
   - `oauth_id = <id de Microsoft>`
   - `hashed_password = NULL`

### Caso 2: Usuario existente local

1. Crear usuario local tradicional
2. Intentar login con Microsoft usando MISMO email
3. Verificar que se vincula cuenta:
   - `auth_provider` actualizado a 'microsoft'
   - `oauth_id` agregado
   - `hashed_password` se mantiene (para fallback)

### Caso 3: Usuario OAuth existente

1. Usuario que ya inició con Microsoft
2. Cerrar sesión
3. Iniciar con Microsoft nuevamente
4. Verificar inicio de sesión exitoso
5. Verificar que foto de perfil se actualiza

---

## Arquitectura y Decisiones

### Decisión 1: Reutilizar Credenciales

**Problema**: ¿Crear nuevo App Registration o reutilizar existente?

**Decisión**: Reutilizar credenciales del Graph API

**Justificación**:
- Misma organización (ZENTRIA)
- Mismo backend (afe-backend)
- Simplifica mantenimiento
- Auditoría centralizada
- Un solo certificado/secreto a renovar

### Decisión 2: Nullable Password

**Problema**: ¿Qué hacer con contraseña de usuarios OAuth?

**Decisión**: Hacer `hashed_password` nullable

**Justificación**:
- Usuarios OAuth no necesitan contraseña
- Permite vincular cuentas existentes
- Mantiene flexibilidad para auth dual

### Decisión 3: Scopes Filtrados

**Problema**: MSAL error con scopes reservados

**Decisión**: Filtrar `openid`, `profile`, `offline_access`

**Justificación**:
- MSAL los agrega automáticamente
- Evita errores de validación
- Mantiene funcionalidad completa

---

## Seguridad Implementada

### 1. Protección CSRF
- Parámetro `state` aleatorio
- Validación en callback
- Almacenamiento en sessionStorage

### 2. Validación de Token
- Verificación de firma JWT
- Validación de audiencia y emisor
- Tiempo de expiración

### 3. HTTPS (Producción)
- Redirect URIs deben usar HTTPS
- Cookies con flag Secure
- Headers de seguridad

### 4. Manejo de Errores
- Mensajes genéricos al usuario
- Logs detallados en servidor
- No exponer información sensible

---

## Ambiente de Producción

### Configuración Adicional

1. **Variables de entorno**:
```bash
OAUTH_MICROSOFT_REDIRECT_URI=https://afe.zentria.com/auth/microsoft/callback
```

2. **Azure AD**:
   - Agregar URI de producción
   - Renovar Client Secret antes de expiración
   - Monitorear uso de cuotas

3. **CORS**:
```python
# app/main.py
origins = [
    "https://afe.zentria.com",
]
```

4. **Certificado SSL**:
   - HTTPS obligatorio
   - Renovación automática (Let's Encrypt)

---

## Monitoreo y Métricas

### Logs a Monitorear

```python
# Exitosos
"Usuario autenticado con Microsoft: {email}"

# Errores
"Error en OAuth callback: {error}"
"Token inválido de Microsoft"
"Usuario sin permiso"
```

### Métricas Sugeridas

- Cantidad de logins por método (local vs Microsoft)
- Tasa de éxito de OAuth flow
- Tiempo promedio de autenticación
- Errores de callback

---

## Próximos Pasos Opcionales

### 1. Google OAuth
- Agregar botón "Continuar con Google"
- Servicio similar a `microsoft_oauth_service.py`
- Agregar `auth_provider = 'google'`

### 2. Single Sign-On (SSO)
- Integrar con Azure AD B2C
- Inicio automático si ya tiene sesión
- Logout global

### 3. Multi-Factor Authentication (2FA)
- Integrar con Microsoft MFA
- 2FA para usuarios locales
- Backup codes

### 4. Gestión de Sesiones
- Refresh tokens
- Logout de todas las sesiones
- Control de dispositivos

---

## Soporte y Troubleshooting

### Error: "Redirect URI mismatch"

**Causa**: URI no configurada en Azure AD

**Solución**:
1. Ir a Azure Portal
2. Authentication → Redirect URIs
3. Agregar URI exacta (sin trailing slash)

### Error: "AADSTS50011: Reply URL mismatch"

**Causa**: URI con/sin trailing slash

**Solución**: Usar URI EXACTA en `.env` y Azure Portal

### Error: "Invalid state parameter"

**Causa**: Posible ataque CSRF o sesión expirada

**Solución**:
1. Verificar que `state` se guarda correctamente
2. Limpiar sessionStorage
3. Reintentar login

### Error: "User not found in directory"

**Causa**: Usuario Microsoft no tiene permisos

**Solución**:
1. Verificar que email está en dominio correcto
2. Agregar usuario a Azure AD tenant
3. Dar permisos necesarios

---

## Contactos y Referencias

### Documentación
- [Microsoft Identity Platform](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [OAuth 2.0 RFC](https://datatracker.ietf.org/doc/html/rfc6749)

### Archivos Internos
- `docs/CONFIGURACION_AZURE_AD_ZENTRIA.md` - Configuración específica
- `docs/AZURE_AD_OAUTH_SETUP.md` - Documentación técnica

---

## Conclusión

La integración OAuth con Microsoft Azure AD está **100% completa** y lista para testing. El sistema ahora ofrece:

- Autenticación profesional de nivel enterprise
- Diseño corporativo Fortune 500
- Seguridad robusta con protección CSRF
- Arquitectura escalable y mantenible

**Estado**:  Implementación completa - Pendiente solo configuración Azure Portal y testing

**Próximo paso inmediato**: Ejecutar migración de base de datos y configurar URIs en Azure Portal.

---

**Documento generado**: 2025-10-28
**Sistema**: ZENTRIA AFE - Advanced Financial Engine
**Autor**: Equipo de Desarrollo ZENTRIA
