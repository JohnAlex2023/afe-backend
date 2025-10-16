# Sistema de Notificaciones por Email

## 📧 Descripción General

El sistema AFE utiliza **Microsoft Graph API** como método principal para envío de emails, con fallback automático a SMTP en caso de fallo.

### Características

✅ **Microsoft Graph API** (Principal)
- Autenticación OAuth2 segura
- Envío desde buzón compartido: `notificacionrpa.auto@zentria.com.co`
- Retry automático con exponential backoff
- Soporte para HTML, adjuntos, CC, BCC
- Sin problemas de "aplicaciones menos seguras"

✅ **SMTP** (Fallback)
- Backup automático si Graph falla
- Compatible con Gmail, Outlook, servidores corporativos

✅ **Plantillas HTML Profesionales**
- Factura Aprobada
- Factura Rechazada
- Factura Pendiente
- Código 2FA
- Recuperación de Contraseña

---

## 🔧 Configuración

### 1. Variables de Entorno (.env)

```env
# Microsoft Graph (Principal)
GRAPH_TENANT_ID=c9ef7bf6-bbe0-4c50-b2e9-ea58d635ca46
GRAPH_CLIENT_ID=79dc4cdc-137b-415f-8193-a7a5b3fdd47b
GRAPH_CLIENT_SECRET=M6q8Q~_g4puSEYy_gV4OmCAAk2r7oilOxXXpJc_~
GRAPH_FROM_EMAIL=notificacionrpa.auto@zentria.com.co
GRAPH_FROM_NAME=Sistema AFE - Notificaciones

# SMTP (Fallback - Opcional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_password_o_app_password
SMTP_FROM_EMAIL=noreply@afe.com
SMTP_FROM_NAME=AFE Sistema de Facturas
SMTP_USE_TLS=True
```

### 2. Permisos en Azure AD

Para que Microsoft Graph funcione, la aplicación debe tener estos permisos:

- ✅ `Mail.Send` - Enviar emails como la aplicación
- ✅ `User.Read.All` - Leer usuarios (opcional)

**Cómo configurarlo:**
1. Ir a Azure Portal → Azure Active Directory
2. App registrations → Tu aplicación
3. API permissions → Add permission
4. Microsoft Graph → Application permissions
5. Seleccionar `Mail.Send`
6. Grant admin consent

---

## 📝 Uso Básico

### Importar el servicio

```python
from app.services.email_notifications import (
    enviar_notificacion_factura_aprobada,
    enviar_notificacion_factura_rechazada,
    enviar_notificacion_factura_pendiente,
    enviar_codigo_2fa,
    enviar_recuperacion_password
)
```

### Ejemplo 1: Notificar Factura Aprobada

```python
resultado = enviar_notificacion_factura_aprobada(
    email_responsable="juan.perez@zentria.com.co",
    nombre_responsable="Juan Pérez",
    numero_factura="FAC-2025-001",
    nombre_proveedor="Proveedor XYZ S.A.S",
    nit_proveedor="900.123.456-7",
    monto_factura="$1,500,000 COP",
    aprobado_por="María González",
    fecha_aprobacion="2025-01-15 10:30:00"
)

if resultado['success']:
    print(f"✅ Email enviado vía {resultado.get('provider', 'unknown')}")
else:
    print(f"❌ Error: {resultado['error']}")
```

### Ejemplo 2: Notificar Factura Rechazada

```python
resultado = enviar_notificacion_factura_rechazada(
    email_responsable="juan.perez@zentria.com.co",
    nombre_responsable="Juan Pérez",
    numero_factura="FAC-2025-002",
    nombre_proveedor="Proveedor ABC Ltda",
    nit_proveedor="800.987.654-3",
    monto_factura="$2,000,000 COP",
    rechazado_por="Carlos Ramírez",
    motivo_rechazo="Los valores de la factura no coinciden con la orden de compra #12345. Por favor verificar y reenviar."
)
```

### Ejemplo 3: Notificar Factura Pendiente

```python
resultado = enviar_notificacion_factura_pendiente(
    email_responsable="responsable@zentria.com.co",
    nombre_responsable="Ana López",
    numero_factura="FAC-2025-003",
    nombre_proveedor="Servicios Tecnológicos S.A.",
    nit_proveedor="900.555.666-8",
    monto_factura="$5,000,000 COP",
    fecha_recepcion="2025-01-10",
    centro_costos="IT-INFRAESTRUCTURA",
    dias_pendiente=3,
    link_sistema="https://afe.zentria.com.co/facturas/FAC-2025-003"
)
```

### Ejemplo 4: Enviar Código 2FA

```python
import random

# Generar código de 6 dígitos
codigo = str(random.randint(100000, 999999))

resultado = enviar_codigo_2fa(
    email_usuario="usuario@zentria.com.co",
    nombre_usuario="Pedro Martínez",
    codigo_2fa=codigo,
    minutos_validez=10
)
```

### Ejemplo 5: Recuperación de Contraseña

```python
import secrets

# Generar token seguro
token = secrets.token_urlsafe(32)
link = f"https://afe.zentria.com.co/reset-password?token={token}"

resultado = enviar_recuperacion_password(
    email_usuario="usuario@zentria.com.co",
    nombre_usuario="Laura Sánchez",
    link_recuperacion=link,
    minutos_validez=30,
    ip_address="192.168.1.100"
)
```

---

## 🔍 Uso Avanzado

### Envío con Adjuntos

```python
from pathlib import Path
from app.services.unified_email_service import get_unified_email_service

service = get_unified_email_service()

# Preparar archivos adjuntos
adjuntos = [
    Path("/path/to/factura.pdf"),
    Path("/path/to/soporte.xml")
]

resultado = service.send_email(
    to_email="destinatario@ejemplo.com",
    subject="Factura con adjuntos",
    body_html="<h1>Ver archivos adjuntos</h1>",
    attachments=adjuntos,
    importance="high"
)
```

### Envío Masivo (Bulk)

```python
from app.services.unified_email_service import get_unified_email_service

service = get_unified_email_service()

# Lista de destinatarios con datos personalizados
destinatarios = [
    {
        "email": "user1@ejemplo.com",
        "nombre": "Usuario 1",
        "factura": "FAC-001"
    },
    {
        "email": "user2@ejemplo.com",
        "nombre": "Usuario 2",
        "factura": "FAC-002"
    }
]

resultados = service.send_bulk_emails(
    recipients=destinatarios,
    subject_template="Factura {factura} pendiente",
    body_template="<p>Hola {nombre}, tienes la factura {factura} pendiente.</p>",
    rate_limit=10,  # 10 emails por segundo
    delay_between_batches=1.0
)

print(f"Enviados: {resultados['sent']}/{resultados['total']}")
print(f"Fallidos: {resultados['failed']}")
```

### Verificar Proveedor Activo

```python
from app.services.unified_email_service import get_unified_email_service

service = get_unified_email_service()
proveedor = service.get_active_provider()

print(f"Proveedor activo: {proveedor}")
# Salida: "microsoft_graph" o "smtp" o "none"
```

---

## 🧪 Testing

### Probar envío de email

```python
# En tu terminal Python o script de prueba
from app.services.email_notifications import enviar_codigo_2fa

resultado = enviar_codigo_2fa(
    email_usuario="tu_email@zentria.com.co",
    nombre_usuario="Test User",
    codigo_2fa="123456",
    minutos_validez=10
)

print(resultado)
```

### Script de prueba completo

```python
# scripts/test_email.py
from app.services.unified_email_service import get_unified_email_service

def test_email_service():
    service = get_unified_email_service()

    resultado = service.send_email(
        to_email="tu_email@zentria.com.co",
        subject="🧪 Test - Sistema de Notificaciones AFE",
        body_html="""
        <h1>Test de Email</h1>
        <p>Si recibes este email, el sistema de notificaciones está funcionando correctamente.</p>
        <p><strong>Proveedor:</strong> Microsoft Graph</p>
        """,
        importance="normal"
    )

    if resultado['success']:
        print(f"✅ Email enviado exitosamente")
        print(f"   Proveedor: {resultado.get('provider', 'unknown')}")
        print(f"   Timestamp: {resultado.get('timestamp')}")
    else:
        print(f"❌ Error: {resultado['error']}")

if __name__ == "__main__":
    test_email_service()
```

---

## 🐛 Troubleshooting

### Error: "Token acquisition failed"

**Causa:** Credenciales de Graph incorrectas o permisos insuficientes

**Solución:**
1. Verificar `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET` en `.env`
2. Verificar permisos en Azure AD
3. Asegurar que se haya dado "Admin consent"

### Error: "Mailbox not found"

**Causa:** El buzón compartido no existe o la app no tiene permisos

**Solución:**
1. Verificar que `notificacionrpa.auto@zentria.com.co` existe
2. Dar permisos "Send As" a la aplicación en el buzón compartido
3. En Exchange Admin: Recipients → Shared mailboxes → Delegation → Send As

### Error: "SMTP authentication failed"

**Causa:** Credenciales SMTP incorrectas o 2FA habilitado

**Solución:**
1. Si usas Gmail: Usar "App Password" en vez de contraseña normal
2. Habilitar "Less secure apps" (no recomendado)
3. Mejor: Usar solo Microsoft Graph

### Los emails se envían pero no llegan

**Causa:** Emails marcados como spam

**Solución:**
1. Verificar carpeta de spam
2. Agregar `notificacionrpa.auto@zentria.com.co` a contactos seguros
3. Configurar SPF/DKIM en DNS (para producción)

---

## 📊 Logs y Monitoreo

El sistema registra todos los eventos de email:

```python
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Los logs mostrarán:
# ✅ Token de Microsoft Graph obtenido exitosamente
# 📧 Intentando envío con Microsoft Graph...
# ✅ Email enviado exitosamente vía Microsoft Graph a usuario@ejemplo.com
# ⚠️  Graph falló: [error], intentando con SMTP...
# ❌ Error enviando email después de 3 intentos: [error]
```

---

## 🔐 Seguridad

### Mejores Prácticas

1. ✅ **Nunca** hardcodear credenciales en el código
2. ✅ Usar variables de entorno para configuración
3. ✅ Rotar `CLIENT_SECRET` regularmente (cada 6 meses)
4. ✅ Limitar permisos de Azure AD a lo mínimo necesario
5. ✅ Usar buzón compartido dedicado para notificaciones
6. ✅ Implementar rate limiting para prevenir spam

### Validación de Emails

```python
from app.services.email_service import EmailService

service = EmailService()

if service.validate_email("usuario@ejemplo.com"):
    # Email válido
    pass
```

---

## 📚 Referencias

- [Microsoft Graph API - Send Mail](https://learn.microsoft.com/en-us/graph/api/user-sendmail)
- [Azure AD App Permissions](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent)
- [Buzones Compartidos en Microsoft 365](https://learn.microsoft.com/en-us/microsoft-365/admin/email/create-a-shared-mailbox)

---

## 🆘 Soporte

Para problemas o preguntas:
1. Revisar logs del sistema
2. Verificar configuración en `.env`
3. Consultar esta documentación
4. Contactar al equipo de desarrollo
