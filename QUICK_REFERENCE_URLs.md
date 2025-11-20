# Quick Reference - URLs del Sistema AFE

## URLs por Entorno

### DESARROLLO (localhost)
```
Frontend:       http://localhost:5173
API:            http://localhost:8000
Database:       localhost:3306
OAuth Callback: http://localhost:5173/auth/microsoft/callback
```

### PRODUCCIÓN (zentria.com.co)
```
Frontend:       https://afe.zentria.com.co
API:            https://api.afe.zentria.com.co (o similar)
Database:       [host privado]
OAuth Callback: https://afe.zentria.com.co/auth/microsoft/callback
```

---

## Construcción de URLs - SIEMPRE USAR URLBuilderService

### Para obtener URL de factura
```python
from app.services.url_builder_service import URLBuilderService

# CORRECTO ✅
url = URLBuilderService.get_factura_detail_url(factura_id=123)
# Resultado: "https://afe.zentria.com.co/facturas?id=123"

# INCORRECTO ❌
url = f"{settings.frontend_url}/facturas/{factura_id}"
url = f"{settings.frontend_url}/facturas?id={factura_id}"
```

### Para pasar a templates
```python
# CORRECTO ✅
context = {
    "url_factura": URLBuilderService.get_factura_detail_url(factura.id)
}

# INCORRECTO ❌
context = {
    "url_factura": settings.frontend_url,
    "factura_id": factura.id
}
```

### En templates Jinja2
```html
<!-- CORRECTO ✅ -->
<a href="{{ url_factura }}">Ver Factura</a>

<!-- INCORRECTO ❌ -->
<a href="{{ url_factura }}/facturas/{{ factura_id }}">Ver Factura</a>
```

---

## Métodos Disponibles en URLBuilderService

| Método | Retorna | Uso |
|--------|---------|-----|
| `get_factura_detail_url(id)` | URL a detalles | Emails, links |
| `get_frontend_url()` | URL base frontend | Redirecciones |
| `get_api_base_url()` | URL base API | Llamadas API |
| `get_oauth_microsoft_redirect_uri()` | URI OAuth callback | Auth Microsoft |
| `get_microsoft_logout_url()` | URL logout Microsoft | Logout |
| `get_api_endpoint(path)` | URL completa endpoint | APIs |
| `is_valid_url(url)` | bool | Validación |
| `get_config_summary()` | dict | Debug |

---

## Servicios Actualizados

### ✅ accounting_notification_service.py
- Línea 34: Import de URLBuilderService
- Línea 148: `notificar_aprobacion_automatica_a_contabilidad()`
- Línea 247: `notificar_aprobacion_manual_a_contabilidad()`
- Línea 352: `notificar_rechazo_a_contabilidad()`

### ✅ notificaciones_programadas.py
- Línea 26: Import de URLBuilderService
- Línea 88: `notificar_nueva_factura()`

### ✅ Templates
- `aprobacion_contabilidad.html` (línea 387)
- `aprobacion_automatica_contabilidad.html` (línea 410)
- `rechazo_contabilidad.html` (línea 373)

---

## URLs de Emails - ANTES vs DESPUÉS

### Aprobación Automática
```
ANTES: https://afe.zentria.com.co/facturas/123
AHORA: https://afe.zentria.com.co/facturas?id=123 ✅

Email a contador → Click en "Ver Detalles" → Dashboard abre factura correctamente
```

### Aprobación Manual
```
ANTES: https://afe.zentria.com.co/facturas/123
AHORA: https://afe.zentria.com.co/facturas?id=123 ✅

Email a contador → Click en "Ver Detalles" → Dashboard abre factura correctamente
```

### Rechazo
```
ANTES: https://afe.zentria.com.co/facturas/123
AHORA: https://afe.zentria.com.co/facturas?id=123 ✅

Email a contador → Click en "Ver Información Completa" → Dashboard abre factura
```

---

## Validación Local

```bash
# Ejecutar test rápido
python test_url_builder_quick.py

# Resultado esperado
Total: 8/8 tests pasados (100%)
[SUCCESS] TODOS LOS TESTS PASARON - LISTO PARA DEPLOY
```

---

## Cambios en .env por Entorno

### .env (Desarrollo)
```
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173
API_BASE_URL=http://localhost:8000
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
OAUTH_MICROSOFT_REDIRECT_URI=http://localhost:5173/auth/microsoft/callback
```

### .env.production (Producción)
```
ENVIRONMENT=production
FRONTEND_URL=https://afe.zentria.com.co
API_BASE_URL=https://api.afe.zentria.com.co
BACKEND_CORS_ORIGINS=https://afe.zentria.com.co
OAUTH_MICROSOFT_REDIRECT_URI=https://afe.zentria.com.co/auth/microsoft/callback
```

---

## API Endpoints Base

```
GET    /api/v1/auth/login
GET    /api/v1/auth/logout
GET    /api/v1/auth/microsoft/authorize
GET    /api/v1/auth/microsoft/callback
GET    /api/v1/auth/microsoft/logout-url

GET    /api/v1/facturas/cursor
GET    /api/v1/facturas/{id}
POST   /api/v1/facturas/aprobar
POST   /api/v1/facturas/rechazar

GET    /api/v1/responsables
GET    /api/v1/proveedores
GET    /api/v1/roles

POST   /api/v1/automation/procesar
GET    /api/v1/automation/estadisticas

GET    /docs                        (Swagger/OpenAPI)
```

---

## Microsoft Endpoints (No cambiar)

```
Auth Token:     https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Auth Authorize: https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize
Auth Logout:    https://login.microsoftonline.com/{tenant}/oauth2/v2.0/logout

Graph Base:     https://graph.microsoft.com/v1.0
Graph User:     https://graph.microsoft.com/v1.0/me
Graph Photo:    https://graph.microsoft.com/v1.0/me/photo/$value
```

---

## Common Mistakes ❌

### ❌ Construir URL manualmente
```python
url = f"{settings.frontend_url}/facturas?id={factura_id}"
```

### ❌ Pasar URL base y ID separados a template
```python
context = {"url_factura": settings.frontend_url, "factura_id": factura.id}
```

### ❌ Concatenar en template
```html
<a href="{{ url_factura }}/facturas/{{ factura_id }}">Link</a>
```

### ❌ Hardcodear dominios
```python
url = "https://afe.zentria.com.co/facturas?id=" + str(factura_id)
```

---

## Best Practices ✅

### ✅ Siempre usar URLBuilderService
```python
from app.services.url_builder_service import URLBuilderService
url = URLBuilderService.get_factura_detail_url(factura_id)
```

### ✅ Pasar URL completa a templates
```python
context = {"url_factura": URLBuilderService.get_factura_detail_url(factura.id)}
```

### ✅ Usar directamente en templates
```html
<a href="{{ url_factura }}">Ver Factura</a>
```

### ✅ Validar en ciertos casos
```python
if URLBuilderService.is_valid_url(url):
    # hacer algo
```

---

## Testing URLs

### Test Unitario
```bash
python test_url_builder_quick.py
```

### Test Manual en Navegador
```
Desarrollo: http://localhost:5173/facturas?id=123
Producción: https://afe.zentria.com.co/facturas?id=123
```

### Test de Email
1. Crear factura en dev
2. Aprobar factura (automático o manual)
3. Verificar email en terminal/logs
4. Copiar URL del email
5. Hacer paste en navegador
6. Verificar que carga detalles de factura

---

## Monitoreo Post-Deploy

### Logs a Vigilar
```bash
# URLs siendo generadas
grep "URL de factura construida" logs/

# Errores de URL
grep "URLBuilderException" logs/
grep "URL inválida" logs/

# Emails enviados
grep "Email.*enviado" logs/
```

### Métricas
- % de emails entregados
- % de clicks en links de emails
- 404 errors en factura detail
- Errores de construcción de URL

---

## Documentación Completa

- `IMPLEMENTACION_URL_BUILDER.md` - Resumen ejecutivo
- `URL_BUILDER_VALIDATION.md` - Plan testing y deployment
- `app/services/url_builder_service.py` - Código fuente (documentado)

---

## Soporte Rápido

| Problema | Solución |
|----------|----------|
| Links en email no funcionan | Validar que URLBuilderService devuelve URL correcta |
| URL muestra 404 | Verificar que frontend puede cargar `/facturas?id=X` |
| URLBuilderException | Validar que factura_id es entero positivo |
| Cambiar dominio producción | Actualizar FRONTEND_URL en .env.production |
| Cambiar patrón URL | Modificar `get_factura_detail_url()` en URLBuilderService |

---

**Última actualización:** 19 de Noviembre de 2025
**Versión:** 1.0.0
**Status:** Production-Ready ✅
