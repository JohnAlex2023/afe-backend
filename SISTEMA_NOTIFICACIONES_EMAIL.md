# Sistema de Notificaciones por Email - AFE Backend

## 📧 Resumen Ejecutivo

Sistema profesional de notificaciones por email para el sistema de automatización de facturas AFE. Utiliza templates HTML con Jinja2 y envío SMTP con reintentos automáticos.

**Estado**: ✅ Implementado (Fase 1 Core)

---

## 🎯 Características

### ✅ Fase 1 - Core (Implementado)

1. **Aprobación Automática** ✅
   - Email HTML profesional con tema verde
   - Detalles de la factura y razones de aprobación
   - Confianza del sistema y patrón detectado
   - Botón para ver factura completa

2. **Revisión Requerida** ✅
   - Email HTML de alerta con tema amarillo/naranja
   - Motivos de revisión detallados
   - Alertas y contexto histórico
   - 3 botones de acción: Aprobar, Ver Detalles, Rechazar

3. **Error Crítico** ✅
   - Email de error con tema rojo
   - Descripción del error y stack trace (opcional)
   - Impacto y acciones recomendadas
   - Botones para ver factura y contactar soporte

4. **Resumen Diario** ✅
   - Dashboard con estadísticas del día
   - Facturas que requieren atención
   - Últimas aprobaciones automáticas
   - Tendencias comparadas con el día anterior

### 🔜 Fase 2 - Avanzado (Futuro)

- Recordatorios de facturas pendientes (3 días, 7 días)
- Alertas de anomalías (montos altos, proveedores nuevos)
- Reportes semanales y mensuales
- Notificaciones push (móvil)
- Webhooks para integraciones externas

---

## 📁 Estructura de Archivos

```
app/
├── services/
│   ├── email_service.py              # Servicio SMTP con reintentos
│   ├── email_template_service.py     # Renderizado Jinja2
│   └── automation/
│       └── notification_service.py   # Integración con automatización
├── templates/
│   └── emails/
│       ├── base.html                 # Template base (no usado actualmente)
│       ├── aprobacion_automatica.html
│       ├── revision_requerida.html
│       ├── error_critico.html
│       └── resumen_diario.html
└── core/
    └── config.py                     # Configuración SMTP (desde .env)
```

---

## ⚙️ Configuración SMTP

### 1. Variables de Entorno

Agregar al archivo `.env`:

```bash
# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM_EMAIL=noreply@afe.com
SMTP_FROM_NAME=Sistema AFE Automatización
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_MAX_RETRIES=3
SMTP_RETRY_DELAY=2
```

### 2. Proveedores Soportados

#### Gmail (Recomendado para desarrollo)

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=tu-email@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # App Password
```

**Obtener App Password**:
1. Ir a https://myaccount.google.com/apppasswords
2. Seleccionar "App" → "Otro" → "AFE Backend"
3. Copiar la contraseña de 16 caracteres
4. Usar esta contraseña en `SMTP_PASSWORD`

#### Outlook/Office365

```bash
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=tu-email@outlook.com
SMTP_PASSWORD=tu-contraseña
```

#### SendGrid (Recomendado para producción)

```bash
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=apikey
SMTP_PASSWORD=tu-sendgrid-api-key
```

---

## 🚀 Uso

### 1. Notificar Aprobación Automática

```python
from app.services.automation.notification_service import NotificationService

notification_service = NotificationService()

resultado = notification_service.notificar_aprobacion_automatica(
    db=db,
    factura=factura,
    criterios_cumplidos=[
        "Factura idéntica al mes anterior",
        "Mismo concepto",
        "Variación de monto dentro del 5%"
    ],
    confianza=0.95,
    patron_detectado="mensual_fijo",
    factura_referencia="FAC-2024-001",
    variacion_monto=2.5  # 2.5%
)

print(f"✅ Emails enviados: {resultado['notificaciones_enviadas']}/{resultado['total_responsables']}")
```

### 2. Notificar Revisión Requerida

```python
resultado = notification_service.notificar_revision_requerida(
    db=db,
    factura=factura,
    motivo="Monto excede el 5% de variación permitida",
    confianza=0.45,
    patron_detectado="mensual_variable",
    alertas=[
        "Variación de monto: 12.5%",
        "Proveedor con historial irregular"
    ],
    contexto_historico={
        'promedio': 1500000,
        'variacion': 8.2
    }
)
```

### 3. Notificar Error Crítico

```python
import traceback

try:
    # ... código que puede fallar
    pass
except Exception as e:
    resultado = notification_service.notificar_error_procesamiento(
        db=db,
        factura=factura,
        error_descripcion=str(e),
        stack_trace=traceback.format_exc()
    )
```

### 4. Enviar Resumen Diario

```python
from datetime import datetime

resultado = notification_service.enviar_resumen_procesamiento(
    db=db,
    estadisticas_procesamiento={
        'resumen_general': {
            'aprobadas_automaticamente': 57,
            'enviadas_revision': 18,
            'tasa_automatizacion': 76.0,
            'monto_total_procesado': 125000000
        }
    },
    facturas_pendientes=facturas_revision,
    facturas_aprobadas=facturas_auto_aprobadas,
    tendencias={
        'aprobaciones_cambio': 5.2,  # +5.2% vs ayer
        'tasa_cambio': 3.1,           # +3.1% vs ayer
        'monto_cambio': -2.5          # -2.5% vs ayer
    }
)
```

---

## 🎨 Templates HTML

### Características de los Templates

1. **Diseño Responsive**
   - Compatible con Gmail, Outlook, Apple Mail
   - Width: 600px (estándar de la industria)
   - Uso de tables para máxima compatibilidad

2. **Estilos Inline**
   - Todos los estilos inline para compatibilidad
   - Degradados CSS3 para headers
   - Colores corporativos

3. **Filtros Jinja2 Personalizados**
   - `{{ monto|currency }}` → `$1.500.000,00`
   - `{{ confianza|percentage }}` → `95.0%`
   - `{{ fecha|date_es }}` → `14 de Octubre de 2025`

4. **Accesibilidad**
   - Versión HTML + texto plano (multipart/alternative)
   - Alto contraste para legibilidad
   - Estructura semántica

### Personalización de Templates

Para personalizar un template:

1. Editar archivo en `app/templates/emails/`
2. Los templates usan Jinja2 syntax: `{{ variable }}`
3. Soporta condicionales: `{% if condicion %}...{% endif %}`
4. Soporta loops: `{% for item in lista %}...{% endfor %}`

Ejemplo:
```html
{% if alertas %}
<table>
    <tr><td>⚠️ ALERTAS:</td></tr>
    {% for alerta in alertas %}
    <tr><td>• {{ alerta }}</td></tr>
    {% endfor %}
</table>
{% endif %}
```

---

## 🧪 Testing

### Testing Local (Sin enviar emails reales)

Desactivar envío de emails en configuración:

```python
from app.services.automation.notification_service import ConfiguracionNotificacion

config = ConfiguracionNotificacion(activar_email=False)

resultado = notification_service.notificar_aprobacion_automatica(
    db=db,
    factura=factura,
    # ... otros parámetros
    config=config
)
# Resultado: {'exito': True, 'metodo_envio': 'simulado'}
```

### Testing con Emails Reales

1. Configurar SMTP en `.env` (usar Gmail para desarrollo)
2. Crear una factura de prueba
3. Ejecutar notificación:

```python
# Script de prueba: scripts/test_notificaciones.py
from app.core.database import get_db
from app.crud import factura as crud_factura
from app.services.automation.notification_service import NotificationService

db = next(get_db())
notification_service = NotificationService()

# Obtener primera factura
factura = crud_factura.get_facturas(db, limit=1)[0]

# Enviar email de prueba
resultado = notification_service.notificar_aprobacion_automatica(
    db=db,
    factura=factura,
    criterios_cumplidos=["Test notification"],
    confianza=0.95,
    patron_detectado="test"
)

print(resultado)
```

### Verificar HTML en Browser

Para previsualizar el HTML sin enviar:

```python
from app.services.email_template_service import get_template_service

template_service = get_template_service()

datos = {
    'responsable_nombre': 'Juan Pérez',
    'numero_factura': 'FAC-2024-001',
    'proveedor_nombre': 'Proveedor Test',
    'monto': 1500000,
    'fecha_emision': datetime.now(),
    'concepto': 'Servicio de prueba',
    'confianza': 0.95,
    'patron_detectado': 'mensual_fijo',
    'factura_referencia': 'FAC-2024-000',
    'variacion_monto': 2.5,
    'criterios_cumplidos': ['Criterio 1', 'Criterio 2'],
    'url_ver_factura': '/facturas/1'
}

html, text = template_service.render_aprobacion_automatica(datos)

# Guardar a archivo
with open('preview.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Abrir en browser: preview.html
```

---

## 📊 Monitoreo y Logs

### Logs de Envío

Los logs se guardan en nivel INFO:

```
INFO - Email enviado exitosamente a responsable@afe.com: Factura aprobada automáticamente - FAC-2024-001
INFO - Notificación simulada (email desactivado) a responsable@afe.com: revision_requerida
ERROR - Error enviando email a responsable@afe.com: Connection timeout
```

### Auditoría

Todas las notificaciones se registran en la tabla `audit`:

```sql
SELECT * FROM audit
WHERE accion LIKE 'notificacion_%'
ORDER BY fecha_hora DESC
LIMIT 10;
```

Detalles guardados:
- `tipo_notificacion`: aprobacion_automatica, revision_requerida, etc.
- `responsables_notificados`: IDs de responsables
- `cantidad_responsables`: Número de emails enviados
- `contexto`: Motivo o contexto adicional

---

## 🔒 Seguridad

### Credenciales SMTP

- ❌ **NUNCA** commitear credenciales al repositorio
- ✅ Usar variables de entorno (`.env`)
- ✅ `.env` está en `.gitignore`
- ✅ Usar App Passwords para Gmail (no contraseña principal)
- ✅ Rotar passwords regularmente

### Protección Anti-Spam

- Tasa de envío limitada (100 emails/5 min)
- Emails con estructura HTML válida
- Encabezados SPF/DKIM (configurar en servidor)
- Links internos (no acortadores de URL)

### Validación de Destinatarios

```python
# Solo enviar a emails válidos y activos
responsables = crud_responsable.get_responsables_activos(db)
# Filtra automáticamente responsables con email NULL o inactivos
```

---

## 🐛 Troubleshooting

### Error: "Connection refused" o "Timeout"

**Causa**: Servidor SMTP incorrecto o bloqueado por firewall

**Solución**:
1. Verificar `SMTP_SERVER` y `SMTP_PORT` en `.env`
2. Comprobar firewall: `telnet smtp.gmail.com 587`
3. Usar puerto 587 (TLS) o 465 (SSL)

### Error: "Authentication failed"

**Causa**: Credenciales incorrectas

**Solución**:
1. Gmail: Usar App Password, no contraseña normal
2. Verificar `SMTP_USERNAME` y `SMTP_PASSWORD`
3. Verificar que 2FA esté habilitado (Gmail)

### Error: "Template not found"

**Causa**: Archivo de template no existe

**Solución**:
1. Verificar que existan archivos en `app/templates/emails/`
2. Nombres correctos: `aprobacion_automatica.html`, etc.
3. Permisos de lectura en directorio

### Emails no llegan o van a Spam

**Causas posibles**:
1. Email sin configuración SPF/DKIM
2. Contenido HTML mal formado
3. Links externos sospechosos
4. Tasa de envío muy alta

**Solución**:
1. Configurar registros DNS (SPF, DKIM)
2. Usar servicio profesional (SendGrid, Mailgun)
3. Evitar palabras spam ("FREE", "WIN", "CLICK HERE")
4. Rate limiting activado

---

## 📈 Métricas y KPIs

### Métricas a Monitorear

1. **Tasa de Entrega**
   - Emails enviados exitosamente / Total intentos
   - Meta: >95%

2. **Tasa de Apertura** (requiere tracking)
   - Emails abiertos / Emails entregados
   - Meta: >40%

3. **Tiempo de Respuesta**
   - Tiempo desde notificación hasta acción
   - Meta: <2 horas (revisión requerida)

4. **Errores de Envío**
   - Emails fallidos / Total intentos
   - Meta: <5%

### Consultas Útiles

```sql
-- Notificaciones enviadas hoy
SELECT
    accion,
    COUNT(*) as cantidad,
    MIN(fecha_hora) as primera,
    MAX(fecha_hora) as ultima
FROM audit
WHERE DATE(fecha_hora) = CURDATE()
    AND accion LIKE 'notificacion_%'
GROUP BY accion;

-- Responsables más notificados (última semana)
SELECT
    JSON_EXTRACT(detalles, '$.responsables_notificados') as responsables,
    COUNT(*) as notificaciones
FROM audit
WHERE fecha_hora >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    AND accion LIKE 'notificacion_%'
GROUP BY responsables
ORDER BY notificaciones DESC
LIMIT 10;
```

---

## 🔄 Roadmap

### Fase 1 - Core ✅ (Implementado)
- [x] EmailService con SMTP
- [x] EmailTemplateService con Jinja2
- [x] Templates HTML profesionales (4)
- [x] Integración con NotificationService
- [x] Configuración SMTP en .env
- [x] Documentación completa

### Fase 2 - Scheduler 🔜 (Siguiente)
- [ ] Background scheduler (APScheduler)
- [ ] Resumen diario automático (8 AM)
- [ ] Recordatorios de facturas pendientes
- [ ] Rate limiting avanzado

### Fase 3 - Avanzado 📅 (Futuro)
- [ ] Dashboard de métricas de email
- [ ] A/B testing de templates
- [ ] Notificaciones push (móvil)
- [ ] Webhooks para integraciones
- [ ] Multi-idioma (EN, ES)

---

## 📚 Referencias

### Documentación Externa

- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Python smtplib](https://docs.python.org/3/library/smtplib.html)
- [Email HTML Best Practices](https://www.campaignmonitor.com/css/)
- [Gmail SMTP Setup](https://support.google.com/mail/answer/7126229)

### Estándares Seguidos

- **RFC 5321**: Simple Mail Transfer Protocol (SMTP)
- **RFC 2045-2049**: Multipurpose Internet Mail Extensions (MIME)
- **HTML Email Standards**: Campaign Monitor CSS Support

### Inspiración de Diseño

Templates inspirados en emails de:
- Stripe (transaccionales)
- GitHub (notificaciones)
- AWS (alertas y reportes)

---

## 👥 Soporte

Para preguntas o problemas:

1. Revisar esta documentación
2. Verificar logs en `logs/app.log`
3. Consultar tabla `audit` para histórico
4. Contactar al equipo técnico

**Última actualización**: 14 de Octubre de 2025
