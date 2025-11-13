# Configuración Azure AD - ZENTRIA AFE

## 🏢 Arquitectura Empresarial Implementada

**Decisión de Diseño:** Usar **UNA SOLA App Registration** para:
-  Envío de notificaciones (Graph API - Mail.Send)
-  Autenticación de usuarios (OAuth 2.0)

**Ventajas:**
- Gestión simplificada
- Un solo client secret que rotar
- Auditoría centralizada
- Coherencia empresarial

---

##  Configuración Actual

```
Tenant: Zentria
Tenant ID: c9ef7bf6-bbe0-4c50-b2e9-ea58d635ca46
Client ID: 79dc4cdc-137b-415f-8193-a7a5b3fdd47b
App Name: ZENTRIA AFE Backend (o similar)
```

---

## 🔧 Pasos de Configuración en Azure Portal

### Paso 1: Acceder a tu App Registration

1. Ve a [Azure Portal](https://portal.azure.com)
2. Busca **"Azure Active Directory"** o **"Microsoft Entra ID"**
3. Menú lateral → **"App registrations"**
4. Busca tu app con Client ID: `79dc4cdc-137b-415f-8193-a7a5b3fdd47b`

---

### Paso 2: Agregar Redirect URIs

1. En tu App Registration, ve a **"Authentication"**
2. En **"Platform configurations"** → **"Web"**
3. Clic en **"Add URI"**
4. Agrega estas URLs:

```
Desarrollo:
✓ http://localhost:3000/auth/microsoft/callback
✓ http://localhost:5173/auth/microsoft/callback

Producción (cuando esté listo):
✓ https://afe.zentria.com/auth/microsoft/callback
```

5. **NO marques** "Implicit grant" (usamos Authorization Code Flow)
6. Clic en **"Save"**

---

### Paso 3: Configurar API Permissions

1. Ve a **"API permissions"** en el menú lateral
2. Verifica que tengas estos permisos (algunos ya deberías tenerlos):

#### Permisos Existentes (para notificaciones):
```
Microsoft Graph - Delegated:
✓ Mail.Send
```

#### Permisos NUEVOS a Agregar (para OAuth):
```
Microsoft Graph - Delegated:
✓ openid              - Identificación básica (REQUERIDO)
✓ email               - Email del usuario (REQUERIDO)
✓ profile             - Información del perfil (REQUERIDO)
✓ User.Read           - Leer datos del usuario (REQUERIDO)
```

3. Clic en **"+ Add a permission"**
4. Selecciona **"Microsoft Graph"**
5. Selecciona **"Delegated permissions"**
6. Busca y marca cada uno de los permisos listados arriba
7. Clic en **"Add permissions"**
8. **IMPORTANTE:** Clic en **"Grant admin consent for [Zentria]"** (requiere permisos de admin)

---

### Paso 4: Verificar Client Secret

1. Ve a **"Certificates & secrets"**
2. Verifica que tu client secret esté activo:
   ```
   Value: M6q8Q~_g4puSEYy_gV4OmCAAk2r7oilOxXXpJc_~
   Expires: [Fecha de expiración]
   ```
3. **⚠️ Importante:**
   - Si expira pronto, crea uno nuevo
   - Actualiza el `.env` con el nuevo valor
   - Rota secrets cada 6-12 meses

---

##  Verificación Final

### Checklist de Configuración:

```
□ Redirect URIs agregados
□ Permisos OAuth agregados (openid, email, profile, User.Read)
□ Admin consent otorgado
□ Client secret válido y no expirado
□ .env actualizado con credenciales correctas
```

### Permisos Finales (debería verse así):

```
Microsoft Graph - Delegated permissions:
├── Mail.Send                    ← Ya existente (notificaciones)
├── openid                       ← NUEVO (OAuth)
├── email                        ← NUEVO (OAuth)
├── profile                      ← NUEVO (OAuth)
└── User.Read                    ← NUEVO (OAuth)

Status: ✓ Admin consent granted
```

---

## 🧪 Testing

### 1. Verificar Configuración Backend

```bash
# En la terminal
cd afe-backend
python -c "from app.core.config import settings; \
    print('Tenant:', settings.oauth_microsoft_tenant_id[:12]); \
    print('Client:', settings.oauth_microsoft_client_id[:12]); \
    print('Scopes:', settings.oauth_microsoft_scopes)"
```

Esperado:
```
Tenant: c9ef7bf6-bbe...
Client: 79dc4cdc-137...
Scopes: openid email profile User.Read
```

### 2. Probar Authorization URL

```bash
# Iniciar servidor
python -m uvicorn app.main:app --reload

# En otra terminal
curl http://localhost:8000/api/v1/auth/microsoft/authorize
```

Esperado:
```json
{
  "authorization_url": "https://login.microsoftonline.com/c9ef7bf6-.../oauth2/v2.0/authorize?...",
  "state": "random_string"
}
```

### 3. Probar Flujo Completo

1. Abre el navegador
2. Ve a: http://localhost:8000/api/v1/auth/microsoft/authorize
3. Deberías ver un JSON con `authorization_url`
4. Copia esa URL y ábrela en el navegador
5. Login con tu cuenta @zentria.com.co
6. Deberías ser redirigido a `localhost:3000/auth/microsoft/callback?code=...`

---

##  Arquitectura del Flujo

```
┌──────────────────────────────────────────────────────────────┐
│                    Azure AD - Zentria                         │
│  App Registration: "ZENTRIA AFE Backend"                     │
│  Client: 79dc4cdc-137b-415f-8193-a7a5b3fdd47b               │
│                                                               │
│  Permisos:                                                    │
│  ├─ Mail.Send        → Notificaciones email                  │
│  ├─ openid           → OAuth login                           │
│  ├─ email            → Email del usuario                     │
│  ├─ profile          → Nombre y foto                         │
│  └─ User.Read        → Info del perfil                       │
└──────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────┐
        │   Backend FastAPI (afe-backend)   │
        ├───────────────────────────────────┤
        │                                    │
        │  1. Email Service                  │
        │     └─ Graph API (Mail.Send)      │
        │                                    │
        │  2. OAuth Service                  │
        │     ├─ /microsoft/authorize        │
        │     └─ /microsoft/callback         │
        │                                    │
        └───────────────────────────────────┘
                            ↓
        ┌───────────────────────────────────┐
        │   Frontend (afe-frontend)         │
        ├───────────────────────────────────┤
        │  - Login con Microsoft button      │
        │  - Callback handler                │
        │  - Token storage                   │
        └───────────────────────────────────┘
```

---

## 🔒 Seguridad

### Variables de Entorno (.env)

```bash
# NO commitear al repositorio
# Usar .env.example para documentación
# En producción, usar Azure Key Vault o similar

OAUTH_MICROSOFT_TENANT_ID=c9ef7bf6-bbe0-4c50-b2e9-ea58d635ca46
OAUTH_MICROSOFT_CLIENT_ID=79dc4cdc-137b-415f-8193-a7a5b3fdd47b
OAUTH_MICROSOFT_CLIENT_SECRET=M6q8Q~_g4puSEYy_gV4OmCAAk2r7oilOxXXpJc_~
```

### Mejores Prácticas

-  Rotar client secret cada 6-12 meses
-  Usar HTTPS en producción
-  Validar state en callback (CSRF protection)
-  Implementar rate limiting en endpoints OAuth
-  Logs de auditoría para autenticaciones
-  Validar dominios de email permitidos (@zentria.com.co)

---

## 🆘 Troubleshooting

### Error: "AADSTS50011: redirect_uri mismatch"
**Solución:** Verifica que la URI en `.env` coincida exactamente con Azure Portal

### Error: "AADSTS65001: user has not consented"
**Solución:** Otorga admin consent en Azure Portal → API Permissions

### Error: "Invalid client secret"
**Solución:** Client secret expiró, genera uno nuevo en Azure Portal

### Error: "User cannot access application"
**Solución:** Usuario no está en el tenant de Zentria o app no está asignada

---

## 📞 Soporte

**Equipo:** Desarrollo ZENTRIA AFE
**Contacto IT:** [Administrador Azure AD de Zentria]
**Documentación:** `/docs/AZURE_AD_OAUTH_SETUP.md` (guía completa)

---

## 🎯 Próximos Pasos

1.  Configurar Azure AD (este documento)
2. ⏳ Integrar frontend con endpoints OAuth
3. ⏳ Testing end-to-end con usuarios reales
4. ⏳ Deploy a producción
5. ⏳ Configurar monitoreo y alertas

---

**Versión:** 1.0
**Última actualización:** 2025-10-28
**Responsable:** Equipo Backend AFE
