# Checklist de Activación OAuth Microsoft

## Estado Actual
✅ Backend implementado
✅ Frontend implementado
✅ Rutas configuradas
✅ Servicios OAuth creados
✅ Migración de BD lista
✅ Diseño corporativo enterprise completado

---

## Pasos para Activar (5 minutos)

### 1️⃣ Ejecutar Migración de Base de Datos

```bash
cd afe-backend
./venv/Scripts/activate
alembic upgrade head
```

**Resultado esperado**:
```
INFO  [alembic.runtime.migration] Running upgrade -> oauth_support_responsables_clean
```

**Verifica**: Campos agregados a tabla `responsables`:
- `auth_provider`
- `oauth_id`
- `oauth_picture`
- `hashed_password` ahora nullable

---

### 2️⃣ Configurar Azure Portal (3 minutos)

**URL**: https://portal.azure.com
**App Registration ID**: `79dc4cdc-137b-415f-8193-a7a5b3fdd47b`

#### Paso A: Agregar Redirect URI

1. Ir a **App registrations** → Buscar app por ID
2. Click en **Authentication** (menú izquierdo)
3. En **Platform configurations** → Click **Add a platform**
4. Seleccionar **Web**
5. Agregar Redirect URI:
   ```
   http://localhost:3000/auth/microsoft/callback
   ```
6. Marcar checkbox **ID tokens**
7. Click **Configure**

#### Paso B: Verificar Permisos

1. Ir a **API permissions** (menú izquierdo)
2. Verificar que existan estos permisos:
   - ✅ Microsoft Graph → `User.Read`
   - ✅ Microsoft Graph → `email`
   - ✅ Microsoft Graph → `profile`
   - ✅ Microsoft Graph → `openid`

3. Si faltan, agregar:
   - Click **Add a permission**
   - **Microsoft Graph** → **Delegated permissions**
   - Buscar y seleccionar los faltantes
   - Click **Add permissions**

4. **IMPORTANTE**: Click **Grant admin consent for [Tenant]**
   - Esto da permiso a todos los usuarios del tenant

#### Paso C: Verificar Client Secret

1. Ir a **Certificates & secrets** (menú izquierdo)
2. Verificar que existe un secreto activo
3. **Fecha de expiración**: Anotar para renovar antes de que expire
4. Si no existe o expiró, crear uno nuevo y actualizar `.env`

---

### 3️⃣ Verificar Backend

```bash
cd afe-backend
./venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

**Verificar en navegador**:

1. **Health check OAuth**:
   ```
   http://localhost:8000/api/v1/auth/microsoft/authorize
   ```

   **Resultado esperado**:
   ```json
   {
     "authorization_url": "https://login.microsoftonline.com/...",
     "state": "..."
   }
   ```

2. **Swagger UI**:
   ```
   http://localhost:8000/docs
   ```

   Verificar endpoints:
   - `GET /api/v1/auth/microsoft/authorize`
   - `GET /api/v1/auth/microsoft/callback`

---

### 4️⃣ Verificar Frontend

```bash
cd afe_frontend
npm start
```

**Verificar**:

1. **Login Page**: http://localhost:3000/login
   - ✅ Debe verse el diseño corporativo mejorado
   - ✅ Botón "Continuar con Microsoft" con logo oficial
   - ✅ Badges "Enterprise" y "Secure"
   - ✅ Animaciones suaves

2. **Callback Page**: Crear URL de prueba
   ```
   http://localhost:3000/auth/microsoft/callback?code=test&state=test
   ```
   - ✅ Debe mostrar página de callback (aunque falle, la ruta funciona)

---

### 5️⃣ Testing End-to-End

#### Test 1: Flujo Completo OAuth

1. Ir a http://localhost:3000/login
2. Click en **"Continuar con Microsoft"**
3. Deberías ser redirigido a login de Microsoft
4. Iniciar sesión con tu cuenta Microsoft
5. Aceptar permisos (primera vez)
6. Deberías volver a http://localhost:3000/auth/microsoft/callback
7. Deberías ver mensaje de éxito y redirección automática
8. Deberías terminar en http://localhost:3000/dashboard

#### Test 2: Verificar Usuario en Base de Datos

```bash
# En afe-backend
./venv/Scripts/activate
python
```

```python
from app.database import SessionLocal
from app.models.responsable import Responsable

db = SessionLocal()
usuario = db.query(Responsable).filter(Responsable.auth_provider == 'microsoft').first()

print(f"Usuario: {usuario.usuario}")
print(f"Email: {usuario.email}")
print(f"Provider: {usuario.auth_provider}")
print(f"OAuth ID: {usuario.oauth_id}")
print(f"Foto: {usuario.oauth_picture}")
print(f"Password: {usuario.hashed_password}")  # Debe ser None
```

#### Test 3: Re-login

1. Cerrar sesión (logout)
2. Volver a iniciar con Microsoft
3. Debería ser más rápido (sin pedir permisos de nuevo)
4. Debería funcionar sin problemas

---

## Troubleshooting Rápido

### ❌ Error: "Redirect URI mismatch"

**Causa**: URI no coincide exactamente

**Solución**:
- Verificar `.env`: `OAUTH_MICROSOFT_REDIRECT_URI=http://localhost:3000/auth/microsoft/callback`
- Verificar Azure Portal: URI idéntica (sin trailing slash)

---

### ❌ Error: "AADSTS700016: Application not found"

**Causa**: Client ID incorrecto

**Solución**:
- Verificar `.env`: `OAUTH_MICROSOFT_CLIENT_ID=79dc4cdc-137b-415f-8193-a7a5b3fdd47b`

---

### ❌ Error: "The reply URL specified in the request does not match"

**Causa**: URI no agregada en Azure Portal

**Solución**:
- Ir a Azure Portal → Authentication → Agregar URI exacta

---

### ❌ Error: "AADSTS50011: The reply URL specified in the request does not match the reply URLs configured"

**Causa**: Trailing slash o diferencia mínima en URI

**Solución**:
- NO usar: `http://localhost:3000/auth/microsoft/callback/`
- Usar: `http://localhost:3000/auth/microsoft/callback` (sin `/` final)

---

### ❌ Error: "Invalid state parameter"

**Causa**: sessionStorage limpiado o CSRF

**Solución**:
- Limpiar cache del navegador
- Iniciar flujo de nuevo
- Verificar que no hay extensiones bloqueando sessionStorage

---

### ❌ Backend no arranca: "ModuleNotFoundError: No module named 'msal'"

**Causa**: Dependencias no instaladas en venv

**Solución**:
```bash
cd afe-backend
./venv/Scripts/pip.exe install authlib msal
```

---

### ❌ Frontend: Botón Microsoft no aparece

**Causa**: LoginPage.tsx no actualizado o error de compilación

**Solución**:
```bash
cd afe_frontend
npm install
npm start
```

Verificar consola del navegador por errores

---

## Comandos Útiles

### Ver logs del backend en tiempo real

```bash
cd afe-backend
./venv/Scripts/python.exe -m uvicorn app.main:app --reload --log-level debug
```

### Ver estado de migraciones

```bash
cd afe-backend
./venv/Scripts/activate
alembic current
alembic history
```

### Conectar a base de datos

```bash
# PostgreSQL
psql -U postgres -d zentria_afe

# Verificar tabla
\d responsables

# Ver usuarios OAuth
SELECT id, usuario, email, auth_provider, oauth_id FROM responsables WHERE auth_provider = 'microsoft';
```

---

## Configuración para Producción

### Cuando estés listo para producción:

1. **Azure Portal**: Agregar URI de producción
   ```
   https://afe.zentria.com/auth/microsoft/callback
   ```

2. **Backend `.env`**:
   ```bash
   OAUTH_MICROSOFT_REDIRECT_URI=https://afe.zentria.com/auth/microsoft/callback
   ```

3. **CORS**: Actualizar dominios permitidos en `app/main.py`

4. **SSL/HTTPS**: Obligatorio para OAuth en producción

---

## Checklist Final

Antes de marcar como completo, verificar:

- [ ] Migración ejecutada sin errores
- [ ] Redirect URI agregada en Azure Portal
- [ ] Permisos verificados y consent otorgado
- [ ] Backend arranca sin errores
- [ ] Frontend muestra diseño mejorado
- [ ] Botón Microsoft visible y funcional
- [ ] Flujo OAuth completo funciona
- [ ] Usuario creado en BD con datos correctos
- [ ] Re-login funciona sin problemas
- [ ] Logout y login de nuevo funciona

---

## Tiempo Estimado

- ⏱️ **Migración BD**: 30 segundos
- ⏱️ **Azure Portal**: 2-3 minutos
- ⏱️ **Testing**: 2 minutos
- ⏱️ **Total**: ~5 minutos

---

## Soporte

Si encuentras problemas:

1. Ver logs del backend (uvicorn)
2. Ver consola del navegador (F12)
3. Verificar network tab en DevTools
4. Consultar `INTEGRACION_OAUTH_MICROSOFT_COMPLETADA.md` para detalles técnicos

---

**Estado**: ✅ Todo listo para activar
**Próximo paso**: Ejecutar migración y configurar Azure Portal
**Tiempo necesario**: 5 minutos

---

¡Éxito! 🚀
