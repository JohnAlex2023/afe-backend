# FLUJO VISUAL: Sistema de Validación por Contador

**Fecha:** 2025-11-29
**Sistema:** AFE Backend - Contador (sin Tesorería)

---

## FLUJO COMPLETO DE FACTURA

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                    ENTRADA DE FACTURA AL SISTEMA                           │
│                                                                             │
│                           en_revision                                      │
│                              │                                             │
│                              ↓                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                    FASE 1: APROBACIÓN (Responsable)                        │
│                                                                             │
│              Estado: en_revision                                           │
│              Rol: RESPONSABLE (aprobar/rechazar)                           │
│              Endpoint: POST /facturas/{id}/aprobar                         │
│                    ↓                                                       │
│           ┌─────────────────────────────┐                                 │
│           │ ¿Responsable aprueba?       │                                 │
│           └────────────┬────────────────┘                                 │
│                        │                                                   │
│          ┌─────────────┴──────────────┐                                   │
│          │                            │                                   │
│          ↓ Sí                         ↓ No                                │
│     ┌─────────────┐             ┌──────────────┐                         │
│     │  aprobada   │             │  rechazada   │                         │
│     │ (manual)    │             │  (TERMINAL)  │                         │
│     └─────┬───────┘             └──────────────┘                         │
│           │                                                               │
│           ├─ O aprobada_auto (Sistema)                                   │
│           │                                                               │
│           ↓ (aprobada | aprobada_auto)                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                    FASE 2: VALIDACIÓN (Contador)                          │
│                                                                             │
│              Estado: aprobada | aprobada_auto                              │
│              Rol: CONTADOR (validar/devolver)                              │
│              Endpoint: POST /accounting/facturas/{id}/validar              │
│                        POST /accounting/facturas/{id}/devolver             │
│                                                                             │
│          GET /accounting/facturas/por-revisar ← Panel del Contador        │
│                              ↓                                             │
│           ┌──────────────────────────────────┐                            │
│           │ ¿Factura correcta?               │                            │
│           │ (totales, datos completos, etc)  │                            │
│           └────────────┬─────────────────────┘                            │
│                        │                                                   │
│          ┌─────────────┴──────────────────────┐                           │
│          │                                    │                           │
│          ↓ Sí                                 ↓ No                        │
│     ┌─────────────────────────┐    ┌──────────────────────────┐          │
│     │ validada_contabilidad   │    │ devuelta_contabilidad    │          │
│     │ ✓ OK para Tesorería     │    │ ✗ Requiere corrección    │          │
│     └────────────┬────────────┘    └──────────┬───────────────┘          │
│                  │                             │                          │
│                  │                             ├─ Email → Responsable     │
│                  │                             │ "Devuelta por Contador" │
│                  │                             │                          │
│                  │                             ↓                          │
│                  │                      en_revision (reinicia)           │
│                  │                             │                          │
│                  ↓                             └─→ Responsable puede:    │
└─────────────────────────────────────────────────────────────────────────────┘
                  │                                   - Rechazar
                  │                                   - Corregir y reenviar
                  │
                  ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                    FASE 3: PAGO (Tesorería - SISTEMA APARTE)              │
│                                                                             │
│              Estado: validada_contabilidad                                 │
│              ⚠️ AQUÍ TERMINA NUESTRO SISTEMA                               │
│              🔗 INTERFAZ A TESORERÍA (sistema independiente)              │
│                                                                             │
│              Rol: TESORERÍA (sistema aparte)                               │
│              Endpoint: (en sistema de Tesorería)                           │
│                                                                             │
│              validada_contabilidad                                         │
│                              ↓                                             │
│                      (Tesorería procesa)                                   │
│                              ↓                                             │
│                          pagada                                            │
│                          (TERMINAL)                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## MATRIZ DE ESTADOS

```
╔════════════════════════════════════════════════════════════════════════════╗
║                              MATRIZ DE ESTADOS                             ║
╠═════════════════════════════╦═════════════════════════════════════════════╣
║ FASE                        ║ ESTADOS                                     ║
╠═════════════════════════════╬═════════════════════════════════════════════╣
║ 1. ENTRADA (inicial)        ║ en_revision                                 ║
║                             ║ - Factura acaba de llegar                  ║
║                             ║ - Espera revisión del Responsable          ║
╠═════════════════════════════╬═════════════════════════════════════════════╣
║ 2. APROBACIÓN (Responsable) ║ aprobada (manual)                           ║
║                             ║ - Responsable revisó y aprobó              ║
║                             ║                                             ║
║                             ║ aprobada_auto (sistema)                    ║
║                             ║ - Sistema aprobó automáticamente           ║
║                             ║ - Idéntica a mes anterior                  ║
║                             ║                                             ║
║                             ║ rechazada (TERMINAL)                       ║
║                             ║ - Responsable rechazó                      ║
║                             ║ - No llega a Contador                      ║
╠═════════════════════════════╬═════════════════════════════════════════════╣
║ 3. VALIDACIÓN (Contador)    ║ validada_contabilidad ✓                    ║
║                             ║ - Contador validó como CORRECTA            ║
║                             ║ - Lista para Tesorería                     ║
║                             ║                                             ║
║                             ║ devuelta_contabilidad ✗                    ║
║                             ║ - Contador encontró problema               ║
║                             ║ - Requiere corrección                      ║
║                             ║ - Responsable recibe email                 ║
║                             ║ - Vuelve a en_revision                     ║
╠═════════════════════════════╬═════════════════════════════════════════════╣
║ 4. PAGO (Tesorería - APARTE) ║ pagada (TERMINAL)                          ║
║                             ║ - Tesorería procesó                        ║
║                             ║ - En sistema de Tesorería (no aquí)       ║
║                             ║                                             ║
║                             ║ cancelada (TERMINAL)                       ║
║                             ║ - Anulada en el proceso                    ║
╚═════════════════════════════╩═════════════════════════════════════════════╝
```

---

## RESPONSABILIDADES POR ROL

```
╔════════════════════════════════════════════════════════════════════════════╗
║                     RESPONSABILIDADES POR ROL                             ║
╠═════════════════════════════╦═════════════════════════════════════════════╣
║ ROL: RESPONSABLE            ║ PUEDE HACER:                                ║
║                             ║ ✓ Ver facturas en en_revision              ║
║                             ║ ✓ Aprobar factura                          ║
║                             ║ ✓ Rechazar factura                         ║
║                             ║ ✗ NO puede validar (Contador)              ║
║                             ║ ✗ NO puede ver facturas validadas          ║
╠═════════════════════════════╬═════════════════════════════════════════════╣
║ ROL: CONTADOR               ║ PUEDE HACER:                                ║
║                             ║ ✓ Ver facturas en aprobada/aprobada_auto   ║
║                             ║ ✓ Validar factura (validada_contabilidad)  ║
║                             ║ ✓ Devolver factura (devuelta_contabilidad) ║
║                             ║ ✗ NO puede aprobar (Responsable)           ║
║                             ║ ✗ NO puede ver en_revision                 ║
║                             ║ ✗ NO puede tocar pagada (Tesorería)       ║
╠═════════════════════════════╬═════════════════════════════════════════════╣
║ ROL: TESORERÍA (APARTE)     ║ PUEDE HACER:                                ║
║                             ║ ✓ Ver facturas validadas_contabilidad      ║
║                             ║ ✓ Marcar como pagada                       ║
║                             ║ ✗ NO hace parte de este sistema            ║
║                             ║ ⚠️ Sistema independiente (interfaz)        ║
╠═════════════════════════════╬═════════════════════════════════════════════╣
║ ROL: ADMIN                  ║ PUEDE HACER:                                ║
║                             ║ ✓ Ver TODO                                 ║
║                             ║ ✓ Ver historial completo                   ║
║                             ║ ✗ NO ejecuta acciones (solo lectura)       ║
╚═════════════════════════════╩═════════════════════════════════════════════╝
```

---

## ENDPOINTS IMPLEMENTADOS

```
╔════════════════════════════════════════════════════════════════════════════╗
║                         ENDPOINTS DE CONTADOR                             ║
╠════════════════════════════════════════════════════════════════════════════╣

┌─ GET /api/v1/accounting/facturas/por-revisar
│  Acceso: CONTADOR
│  Retorna: Lista de facturas pendientes de validación
│  Estadísticas: Total, monto pendiente, validadas hoy
│  Paginación: ?pagina=1&limit=50

┌─ POST /api/v1/accounting/facturas/{id}/validar
│  Acceso: CONTADOR
│  Body: { "observaciones": "..." }
│  Efecto: aprobada → validada_contabilidad ✓
│  Emails: NINGUNO (solo auditoría en logs)
│  Retorna: Confirmación + timestamp

┌─ POST /api/v1/accounting/facturas/{id}/devolver
│  Acceso: CONTADOR
│  Body: { "observaciones": "...", "notificar_responsable": true }
│  Efecto: aprobada → devuelta_contabilidad ✗
│  Emails: SÍ → Responsable ("Devuelta por Contador")
│  Retorna: Confirmación + notificaciones enviadas

╚════════════════════════════════════════════════════════════════════════════╝
```

---

## FLUJO DE VALIDACIÓN (PASO A PASO)

```
PASO 1: Contador inicia sesión
┌────────────────────────────────┐
│ GET /api/v1/accounting/        │ Dashboard Contador
│     facturas/por-revisar       │ - 5 facturas esperando
│                                │ - $7.5M total
│ RESPONSE:                      │
│ {                              │
│   "facturas": [...],           │
│   "estadisticas": {            │
│     "total_pendiente": 5,      │
│     "monto_pendiente": 7500000 │
│   }                            │
│ }                              │
└────────────────────────────────┘

PASO 2: Contador abre factura INV-2025-001
┌────────────────────────────────┐
│ Revisa datos:                  │
│ - Monto: $1.5M                 │
│ - Proveedor: Empresa XYZ       │
│ - Totales: ✓ Coinciden         │
│ - Datos: ✓ Completos           │
│ - NIT: ✓ Válido                │
│                                │
│ DECISIÓN: ✓ OK - Validar      │
└────────────────────────────────┘

PASO 3: Contador valida factura
┌────────────────────────────────┐
│ POST /accounting/facturas/100/  │
│      validar                   │
│                                │
│ BODY:                          │
│ {                              │
│   "observaciones":             │
│     "Verificada contra BD"     │
│ }                              │
│                                │
│ RESPONSE:                      │
│ {                              │
│   "success": true,             │
│   "estado_nuevo":              │
│     "validada_contabilidad",   │
│   "validado_por": "María",     │
│   "fecha_validacion": "...",   │
│   "mensaje": "Lista para       │
│              Tesorería"        │
│ }                              │
└────────────────────────────────┘

PASO 4: Factura está lista para Tesorería
┌────────────────────────────────┐
│ Estado: validada_contabilidad  │
│ ✓ Contador aprobó              │
│ → Tesorería puede procesarla   │
└────────────────────────────────┘


ALTERNATIVA (Si hay problema):

PASO 3B: Contador encuentra problema
┌────────────────────────────────┐
│ INV-2025-002                   │
│ Datos: ✗ Incompletos           │
│ Falta: Centro de costos        │
│                                │
│ DECISIÓN: ✗ Requiere corrección│
└────────────────────────────────┘

PASO 4B: Contador devuelve factura
┌────────────────────────────────┐
│ POST /accounting/facturas/101/  │
│      devolver                  │
│                                │
│ BODY:                          │
│ {                              │
│   "observaciones":             │
│     "Falta centro de costos",  │
│   "notificar_responsable": true│
│ }                              │
│                                │
│ RESPONSE:                      │
│ {                              │
│   "success": true,             │
│   "estado_nuevo":              │
│     "devuelta_contabilidad",   │
│   "notificaciones_enviadas": 1 │
│ }                              │
│                                │
│ EMAIL → Responsable:           │
│ "Tu factura fue devuelta por   │
│  Contador. Requiere corrección:│
│  Falta centro de costos"       │
└────────────────────────────────┘

PASO 5B: Responsable recibe email
┌────────────────────────────────┐
│ Lee email de Contador          │
│ Opción 1: Rechazar definitivo  │
│ Opción 2: Corregir datos       │
│ Opción 3: Reenviár a Contador  │
└────────────────────────────────┘
```

---

## AUDITORÍA Y LOGS

```
Cada acción queda registrada en logs del sistema:

[2025-11-29 15:30:00] INFO - Factura validada por contador: INV-2025-001
  contador: maria.garcia
  estado_anterior: aprobada
  estado_nuevo: validada_contabilidad
  observaciones: Verificada contra registros contables

[2025-11-29 15:35:00] INFO - Factura devuelta por contador: INV-2025-002
  contador: maria.garcia
  estado_anterior: aprobada
  estado_nuevo: devuelta_contabilidad
  notificaciones_enviadas: 1
  destinatarios: [responsable@empresa.com]
```

---

## PUNTO CLAVE: LÍMITES DEL SISTEMA

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  NUESTRO SISTEMA (AFE Backend - Contador)                               │
│  ════════════════════════════════════════════════════════════════════  │
│                                                                          │
│  Responsabilidades:                                                    │
│  ✓ Aprobación: Responsable aprueba facturas                            │
│  ✓ Validación: Contador valida facturas aprobadas                      │
│  ✗ Pago: NO lo hacemos (Tesorería)                                     │
│  ✗ Contabilización: NO lo hacemos (Contabilidad)                       │
│  ✗ Archivo: NO lo hacemos (Documentería)                               │
│                                                                          │
│  Punto de entrega:                                                     │
│  ─────────────────────────────────────────────────────────────────────  │
│  Estado: validada_contabilidad ← Aquí termina nuestro sistema          │
│          ↓ (interfaz)                                                   │
│  Sistema Tesorería → (sistema independiente que consume facturas)      │
│                                                                          │
│  Garantizamos:                                                         │
│  ✓ Que SOLO facturas correctas llegan a Tesorería                      │
│  ✓ Que cada validación queda registrada (auditoría)                    │
│  ✓ Que Responsable es notificado si hay problemas                      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## RESUMEN

Este es un sistema **simple, claro y profesional**:

1. **Responsable aprueba** (automático o manual)
2. **Contador valida** (correcta o requiere corrección)
3. **Tesorería paga** (sistema aparte)

**Nuestro trabajo termina en VALIDACIÓN.** 🎯
