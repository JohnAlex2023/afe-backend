#  DOCUMENTACIÓN TÉCNICA - INVOICE EXTRACTOR

**Versión:** 1.0 (Pre-Release)
**Última actualización:** Noviembre 2024
**Estado:** Parcialmente Implementado (80% Complete)
**Módulo:** `app/services/extractor/`

---

## 📑 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Descripción General](#descripción-general)
3. [Arquitectura del Sistema](#arquitectura-del-sistema)
4. [Interface y Contrato](#interface-y-contrato)
5. [Implementaciones](#implementaciones)
6. [Flujo de Procesamiento](#flujo-de-procesamiento)
7. [Transformación de Datos](#transformación-de-datos)
8. [Servicios Integrados](#servicios-integrados)
9. [Manejo de Errores](#manejo-de-errores)
10. [Configuración](#configuración)
11. [Testing](#testing)
12. [Roadmap de Implementación](#roadmap-de-implementación)

---

## 🎯 Resumen Ejecutivo

### ¿Qué es el Invoice Extractor?

**Invoice Extractor** es un **sistema modular para la extracción automática de facturas** desde fuentes externas (principalmente correos electrónicos corporativos). Su propósito es:

-  Conectar a Microsoft Outlook/Graph API
-  Descargar facturas en formato PDF/XML
-  Parsear y extraer datos estructurados
-  Filtrar por NITs configurados
-  Procesar en batches eficientemente
-  Integrar con workflow automático de aprobación

### Estado Actual

| Componente | Implementación | Observación |
|-----------|---|---|
| Interface (IInvoiceExtractor) |  100% | Contrato bien definido |
| DummyExtractor |  100% | Solo para testing |
| **MicrosoftGraphExtractor** | ❌ 0% | **FALTA IMPLEMENTAR** |
| **PDF Parser** | ❌ 0% | **Necesita librería** |
| XML Parser | ⚠️ 30% | Estructura pero sin integración |
| NIT Filtering | ⚠️ 50% | Interface existe |
| Data Transformation |  95% | Normalización y hashing funcionan |
| BD Persistence |  100% | Guardado en facturas + items |
| Workflow Integration |  90% | Aprobación automática |
| API Endpoints |  100% | CRUD completo |

### Impacto en el Negocio

```
ACTUAL (Sin Extractor Funcional):
  Entrada: Manual vía API REST
  Procesamiento: Automático 
  Salida: Aprobación inteligente 
  Eficiencia: 30% (entrada manual es bottleneck)

CON EXTRACTOR IMPLEMENTADO:
  Entrada: Automática desde emails 
  Procesamiento: Automático 
  Salida: Aprobación inteligente 
  Eficiencia: 95% (fin-a-fin automático)
```

---

## 📖 Descripción General

### Propósito

El Invoice Extractor **automatiza la captura de facturas** desde la bandeja de entrada corporativa, eliminando:

- ❌ Ingreso manual de datos (error-prone)
- ❌ Delays en procesamiento (días a minutos)
- ❌ Duplicación de esfuerzo (personas reenviando emails)

### Casos de Uso

#### 1. **Extracción de Factura de Proveedores**
```
Proveedor envía → Email con PDF
                    ↓
             Extractor descarga
                    ↓
             Parser extrae datos
                    ↓
             Workflow aprueba automáticamente
                    ↓
        Responsable recibe notificación
```

#### 2. **Procesamiento en Batch**
```
Ejecutor automático (scheduler)
       ↓
Descarga todos los emails nuevos
       ↓
Procesa 100+ facturas en paralelo
       ↓
Aprueba inteligentemente
       ↓
Notifica resultados
```

#### 3. **Filtrado por NIT**
```
Email con factura → Extrae NIT: "800.123.456-7"
                           ↓
                  ¿NIT configurado?
                    ↙          ↘
                   SÍ           NO
                   ↓            ↓
              Procesa      Ignora/Log
```

### Flujo Conceptual

```
┌─────────────────────────────────────────────────┐
│   PROVEEDOR                                      │
│   (Outlook/Email)                                │
└────────────┬────────────────────────────────────┘
             │ Email + Facturas PDF/XML
             ↓
┌─────────────────────────────────────────────────┐
│   INVOICE EXTRACTOR                             │
│   ┌─────────────────────────────────────────┐   │
│   │ 1. CONECTAR A OUTLOOK (Microsoft Graph) │   │
│   │    - Token OAuth                        │   │
│   │    - Descargar inbox                    │   │
│   │    - Extraer attachments                │   │
│   └─────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────┐   │
│   │ 2. PARSEAR DOCUMENTOS                   │   │
│   │    - PDF → Datos estructurados          │   │
│   │    - XML → JSON/Dict                    │   │
│   │    - Validar campos                     │   │
│   └─────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────┐   │
│   │ 3. FILTRAR POR NIT                      │   │
│   │    - Validar contra tabla configurados  │   │
│   │    - Ignorar no configurados            │   │
│   │    - Loguear omisiones                  │   │
│   └─────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────┐   │
│   │ 4. NORMALIZAR DATOS                     │   │
│   │    - Normalizar descripciones           │   │
│   │    - Generar hashes MD5                 │   │
│   │    - Detectar categorías                │   │
│   │    - Identificar recurrencias           │   │
│   └─────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────┐   │
│   │ 5. RETORNAR BATCH (Generator)           │   │
│   │    - Iterable[FacturaCreate]            │   │
│   │    - Memoria eficiente (streaming)      │   │
│   └─────────────────────────────────────────┘   │
└────────────┬────────────────────────────────────┘
             │ FacturaCreate objects
             ↓
┌─────────────────────────────────────────────────┐
│   INVOICE SERVICE                               │
│   (process_and_persist_invoice)                 │
│   - Deduplicación CUFE                          │
│   - Creación en BD                              │
│   - Creación de items                           │
└────────────┬────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────┐
│   WORKFLOW AUTOMÁTICO                           │
│   - Asignar responsable por NIT                 │
│   - Analizar similitud                          │
│   - Aprobar automáticamente o enviar a revisión │
│   - Notificar por email                         │
└────────────┬────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────┐
│   BASE DE DATOS                                 │
│   - Tabla: facturas                             │
│   - Tabla: factura_items                        │
│   - Tabla: workflow_aprobacion_facturas         │
└─────────────────────────────────────────────────┘
```

---

## 🏗️ Arquitectura del Sistema

### Diseño de Capas

```
┌─────────────────────────────────────────────────┐
│              SCHEDULER / CRON                     │
│         (lifespan.py: cada 1 hora)               │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│       INVOICE EXTRACTOR FACTORY                  │
│   (factory pattern para elegir implementación)   │
└────────────────┬────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
  ┌─────┐  ┌──────────┐  ┌───────────┐
  │Dummy│  │Microsoft │  │(Futuro)   │
  │   │  │  Graph   │  │ Extensión │
  │     │  │   ❌     │  │           │
  └──┬──┘  └────┬─────┘  └─────┬─────┘
     │          │              │
     └──────────┼──────────────┘
                │
        ┌───────▼────────┐
        │ IInvoiceExtractor
        │ (Abstract Base)
        │
        │ + extract(batch_size: int)
        │   → Iterable[FacturaCreate]
        └───────┬────────┘
                │
┌───────────────▼──────────────────────────────┐
│         DATA TRANSFORMATION LAYER              │
│  ┌────────────────────────────────────────┐  │
│  │ ItemNormalizerService                  │  │
│  │ ├─ normalizar_texto()                  │  │
│  │ ├─ generar_hash()                      │  │
│  │ ├─ detectar_categoria()                │  │
│  │ └─ es_recurrente()                     │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │ FacturaItemsService                    │  │
│  │ ├─ crear_items_desde_extractor()       │  │
│  │ ├─ obtener_items_factura()             │  │
│  │ └─ eliminar_items_factura()            │  │
│  └────────────────────────────────────────┘  │
└───────────────┬──────────────────────────────┘
                │
┌───────────────▼──────────────────────────────┐
│         PERSISTENCE LAYER                     │
│  ┌────────────────────────────────────────┐  │
│  │ InvoiceService                         │  │
│  │ ├─ process_and_persist_invoice()       │  │
│  │ ├─ deduplicación por CUFE              │  │
│  │ ├─ deduplicación por num+proveedor     │  │
│  │ └─ creación transaccional              │  │
│  └────────────────────────────────────────┘  │
└───────────────┬──────────────────────────────┘
                │
        ┌───────▼───────┐
        │   DATABASE    │
        │  ┌─────────┐  │
        │  │facturas │  │
        │  └─────────┘  │
        │  ┌──────────┐ │
        │  │fact_items│ │
        │  └──────────┘ │
        │  ┌──────────┐ │
        │  │workflows │ │
        │  └──────────┘ │
        └───────────────┘
```

### Patrones de Diseño

#### 1. **Abstract Base Class (ABC)**
```python
from abc import ABC, abstractmethod

class IInvoiceExtractor(ABC):
    @abstractmethod
    def extract(self, batch_size: int = 100) -> Iterable[FacturaCreate]:
        """Contrato que todos los extractores deben cumplir"""
        raise NotImplementedError
```

**Beneficios:**
- Contrato explícito
- Fácil de testear (mock)
- Extensible (nuevo extractores)
- Type-safe

#### 2. **Generator Pattern (Memory Efficient)**
```python
def extract(self, batch_size: int = 100) -> Iterable[FacturaCreate]:
    for email in self.get_emails():
        for attachment in email.attachments:
            factura = self.parse(attachment)
            yield factura  # No carga todo en memoria
```

**Beneficios:**
- Procesa datasets grandes (100k+ emails)
- Bajo overhead de memoria
- Streaming en tiempo real

#### 3. **Service Locator Pattern**
```python
def get_extractor() -> IInvoiceExtractor:
    """Factory que retorna la implementación correcta"""
    extractor_type = settings.INVOICE_EXTRACTOR_TYPE  # "dummy" o "microsoft_graph"

    if extractor_type == "dummy":
        return DummyExtractor()
    elif extractor_type == "microsoft_graph":
        return MicrosoftGraphInvoiceExtractor()
    else:
        raise ValueError(f"Unknown extractor: {extractor_type}")
```

#### 4. **Strategy Pattern (Normalización)**
```python
class ItemNormalizerService:
    @staticmethod
    def normalizar_item_completo(descripcion: str) -> dict:
        """
        Estrategia completa:
        1. Normalizar texto
        2. Generar hash
        3. Detectar categoría
        4. Detectar recurrencia
        """
        texto_norm = ItemNormalizerService.normalizar_texto(descripcion)
        return {
            "original": descripcion,
            "normalizada": texto_norm,
            "hash": ItemNormalizerService.generar_hash(texto_norm),
            "categoria": ItemNormalizerService.detectar_categoria(descripcion),
            "es_recurrente": ItemNormalizerService.es_recurrente(descripcion),
        }
```

---

## 🔧 Interface y Contrato

### Definición

**Archivo:** `app/services/extractor/base.py`

```python
from abc import ABC, abstractmethod
from typing import Iterable
from app.schemas.factura import FacturaCreate

class IInvoiceExtractor(ABC):
    """
    Interface base para todos los extractores de facturas.

    Define el contrato que cualquier extractor debe cumplir,
    permitiendo múltiples implementaciones (dummy, Microsoft, SFTP, etc.)
    """

    @abstractmethod
    def extract(self, batch_size: int = 100) -> Iterable[FacturaCreate]:
        """
        Extrae facturas crudas en batches.

        Args:
            batch_size (int): Número de facturas a procesar por batch.
                            Default: 100 (bajar para bajo overhead de memoria).
                            Subir para mejor throughput (Trade-off).

        Yields:
            FacturaCreate: Objeto factura listo para persistir.
                          Estructura validada por Pydantic.

        Raises:
            ConnectionError: Si no puede conectar a fuente.
            ParseError: Si no puede parsear documento.
            ValidationError: Si datos no cumplen esquema FacturaCreate.

        Examples:
            >>> extractor = get_extractor()
            >>> for factura in extractor.extract(batch_size=500):
            ...     process_and_persist_invoice(db, factura, created_by="SYSTEM")
        """
        raise NotImplementedError
```

### Esquema FacturaCreate

**Archivo:** `app/schemas/factura.py`

```python
from pydantic import BaseModel, condecimal
from typing import Optional
from datetime import date

class FacturaCreate(BaseModel):
    """
    Esquema de validación para facturas que vienen del extractor.

    El extractor DEBE retornar objetos que cumplan este esquema
    para asegurar compatibilidad con el rest del sistema.
    """

    # Identificación de factura
    numero_factura: str  # Ej: "FAC-2025-001234"

    # Fechas
    fecha_emision: date  # Fecha en que se emitió
    fecha_vencimiento: Optional[date] = None  # Vencimiento (puede ser NULL)

    # Proveedor
    proveedor_id: Optional[int] = None  # FK a proveedores (puede calcularse del NIT)

    # Montos (todos en formato Decimal para precisión)
    subtotal: condecimal(max_digits=15, decimal_places=2)  # Sin impuestos
    iva: condecimal(max_digits=15, decimal_places=2)  # IVA 19%
    total_a_pagar: condecimal(max_digits=15, decimal_places=2)  # Subtotal + IVA

    # Identificadores únicos
    cufe: Optional[str] = None  # CUFE único (XML firmado Colombia)

    # Items/Líneas (opcional, puede ser creado después)
    items: Optional[List[FacturaItemCreate]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "numero_factura": "FAC-2025-001234",
                "fecha_emision": "2025-10-30",
                "fecha_vencimiento": "2025-11-30",
                "proveedor_id": 42,
                "subtotal": "1000.00",
                "iva": "190.00",
                "total_a_pagar": "1190.00",
                "cufe": "ABC123DEF456...",
                "items": [
                    {
                        "numero_linea": 1,
                        "descripcion": "Servicio de hosting",
                        "cantidad": 1,
                        "precio_unitario": "1000.00",
                        "subtotal": "1000.00",
                        "total": "1190.00"
                    }
                ]
            }
        }
```

---

## 🔍 Implementaciones

### 1. DummyExtractor (Actual)

**Archivo:** `app/services/extractor/invoice_extractor_dummy.py`

```python
from typing import Iterable
from datetime import date
from decimal import Decimal
from app.services.extractor.base import IInvoiceExtractor
from app.schemas.factura import FacturaCreate

class DummyExtractor(IInvoiceExtractor):
    """
    Implementación dummy para testing y desarrollo.

    Retorna una única factura de prueba, sin conexión a sistemas externos.
    Útil para validar:
    - Interface
    - Flujo de persistencia
    - Workflow automático
    - Integración end-to-end

    Para desarrollo local:
        INVOICE_EXTRACTOR_TYPE=dummy
    """

    def extract(self, batch_size: int = 100) -> Iterable[FacturaCreate]:
        """
        Retorna una factura de prueba.

        Nota: batch_size es ignorado (siempre retorna 1).
        """
        yield FacturaCreate(
            numero_factura="FAC-DUMMY-001",
            fecha_emision=date.today(),
            fecha_vencimiento=None,
            proveedor_id=None,  # Se resuelve después
            subtotal=Decimal("1000.00"),
            iva=Decimal("190.00"),
            total_a_pagar=Decimal("1190.00"),
            cufe="CUFE-DUMMY-0001",
            items=[
                {
                    "numero_linea": 1,
                    "descripcion": "Servicio de prueba dummy",
                    "cantidad": 1,
                    "precio_unitario": "1000.00",
                    "subtotal": "1000.00",
                    "total": "1190.00"
                }
            ]
        )
```

**Uso en Testing:**
```python
from app.services.extractor.invoice_extractor_dummy import DummyExtractor
from app.services.invoice_service import process_and_persist_invoice

def test_workflow_integration():
    extractor = DummyExtractor()

    for factura_data in extractor.extract():
        # Procesar factura dummy
        resultado, accion = process_and_persist_invoice(
            db, factura_data, created_by="TEST"
        )

        # Validar que se creó
        assert accion == "created"
        assert resultado["id"] is not None
```

### 2. MicrosoftGraphExtractor (Falta Implementar)

**Archivo:** `app/services/extractor/microsoft_graph_extractor.py` (A CREAR)

```python
# ESTRUCTURA ESPERADA (no implementada aún)

from typing import Iterable, List
from app.services.extractor.base import IInvoiceExtractor
from app.services.microsoft_graph_email_service import MicrosoftGraphEmailService
from app.schemas.factura import FacturaCreate
import logging

logger = logging.getLogger(__name__)

class MicrosoftGraphInvoiceExtractor(IInvoiceExtractor):
    """
    Extractor que descarga facturas desde Outlook/Microsoft Graph.

    ESTADO: FALTA IMPLEMENTAR

    Debe implementar:
    1. Conectar a Microsoft Graph API
    2. Descargar emails del Inbox (filtrar últimos N días)
    3. Extraer attachments (PDF, XML, ZIP)
    4. Parsear documentos
    5. Filtrar por NITs configurados
    6. Retornar batch de facturas
    """

    def __init__(self,
                 email_service: MicrosoftGraphEmailService,
                 nits_configurados: List[str]):
        """
        Initialize the extractor.

        Args:
            email_service: Instancia de MicrosoftGraphEmailService
            nits_configurados: Lista de NITs a procesar (ej: ["800.111.111-1"])
        """
        self.email_service = email_service
        self.nits_configurados = set(nits_configurados)
        self.logger = logger

    def extract(self, batch_size: int = 100) -> Iterable[FacturaCreate]:
        """
        Extrae facturas desde Outlook.

        Pasos:
        1. Conectar a Microsoft Graph
        2. Obtener emails del Inbox (últimos 7 días)
        3. Filtrar por attachments
        4. Descargar PDFs/XMLs
        5. Parsear y extraer datos
        6. Filtrar por NIT
        7. Normalizar y retornar
        """

        try:
            # Paso 1: Obtener emails
            emails = self.email_service.get_emails_with_attachments(
                mailbox="inbox",
                days_back=7,
                filter_senders=None  # O lista de senders permitidos
            )

            count = 0
            for email in emails:
                try:
                    # Paso 2: Procesar attachments
                    for attachment in email.attachments:
                        try:
                            # Paso 3: Parsear según tipo
                            if attachment.filename.endswith('.pdf'):
                                factura_data = self._parse_pdf(attachment)
                            elif attachment.filename.endswith('.xml'):
                                factura_data = self._parse_xml(attachment)
                            elif attachment.filename.endswith('.zip'):
                                factura_data = self._parse_zip(attachment)
                            else:
                                logger.warning(f"Tipo no soportado: {attachment.filename}")
                                continue

                            # Paso 4: Filtrar por NIT
                            nit = factura_data.get('nit_proveedor')
                            if nit not in self.nits_configurados:
                                logger.info(f"NIT no configurado: {nit}")
                                continue

                            # Paso 5: Crear FacturaCreate
                            factura = FacturaCreate(**factura_data)
                            yield factura

                            count += 1
                            if count >= batch_size:
                                return  # Yield hasta batch_size

                        except Exception as e:
                            logger.error(f"Error procesando attachment: {str(e)}")
                            continue

                except Exception as e:
                    logger.error(f"Error procesando email: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error crítico en extractor: {str(e)}", exc_info=True)
            raise

    def _parse_pdf(self, attachment) -> dict:
        """
        Extrae datos de PDF.

        Requiere: pdfplumber

        Debe extraer:
        - numero_factura
        - fecha_emision
        - nit_proveedor
        - subtotal, iva, total
        - items (lineas)
        """
        import pdfplumber

        try:
            with pdfplumber.open(attachment.data) as pdf:
                # Extraer texto de primera página
                first_page = pdf.pages[0]
                text = first_page.extract_text()

                # Usar OCR o regex para extraer campos
                # Esto es VARIABLE según formato de proveedor

                return {
                    "numero_factura": self._extract_numero(text),
                    "nit_proveedor": self._extract_nit(text),
                    "fecha_emision": self._extract_fecha(text),
                    "subtotal": self._extract_subtotal(text),
                    "iva": self._extract_iva(text),
                    "total_a_pagar": self._extract_total(text),
                    "cufe": self._extract_cufe(text),
                }
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise

    def _parse_xml(self, attachment) -> dict:
        """
        Extrae datos de XML (facturación electrónica DIAN).

        XML Structure (DIAN Colombia):
        <Invoice>
            <InvoiceNumber>
            <IssueDate>
            <AccountingSupplierParty>
                <PartyTaxScheme>
                    <CompanyID>  <!-- NIT -->
            <LegalMonetaryTotal>
                <LineExtensionAmount>  <!-- Subtotal -->
                <TaxTotal>
                    <TaxAmount>  <!-- IVA -->
                <PayableAmount>  <!-- Total -->
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(attachment.data)

            # Namespace (DIAN uses specific namespaces)
            ns = {
                'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
                'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
            }

            return {
                "numero_factura": root.find('.//cbc:ID', ns).text,
                "nit_proveedor": root.find('.//cac:AccountingSupplierParty//cbc:CompanyID', ns).text,
                "fecha_emision": root.find('.//cbc:IssueDate', ns).text,
                "subtotal": root.find('.//cbc:LineExtensionAmount', ns).text,
                "iva": root.find('.//cbc:TaxAmount', ns).text,
                "total_a_pagar": root.find('.//cbc:PayableAmount', ns).text,
                "cufe": root.find('.//cbc:UUID', ns).text,
            }
        except Exception as e:
            logger.error(f"Error parsing XML: {str(e)}")
            raise

    def _parse_zip(self, attachment) -> dict:
        """
        Extrae XML de un ZIP y lo parsea.
        """
        import zipfile

        try:
            with zipfile.ZipFile(attachment.data) as zf:
                # Buscar XML dentro del ZIP
                xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
                if not xml_files:
                    raise ValueError("No XML encontrado en ZIP")

                # Parsear primer XML
                with zf.open(xml_files[0]) as xf:
                    return self._parse_xml(xf.read())
        except Exception as e:
            logger.error(f"Error parsing ZIP: {str(e)}")
            raise

    # Helpers para regex/extraction (simplificados)
    def _extract_numero(self, text: str) -> str:
        import re
        match = re.search(r'Factura\s+(?:No\.?|#)?\s*(\d{4,})', text)
        return match.group(1) if match else ""

    def _extract_nit(self, text: str) -> str:
        import re
        match = re.search(r'NIT\s*:?\s*(\d{3}\.\d{3}\.\d{3}-\d{1})', text)
        return match.group(1) if match else ""

    # ... más helpers
```

---

##  Flujo de Procesamiento

### Fase 0: Extracción (Falta Implementar)

```
SCHEDULER (lifespan.py)
    │ Cada hora
    ▼
MicrosoftGraphInvoiceExtractor.extract()
    │ batch_size=500
    ├─ Conectar a Microsoft Graph
    ├─ Descargar emails (inbox, últimos 7 días)
    ├─ Iterar attachments
    │  ├─ Validar formato (PDF/XML/ZIP)
    │  ├─ Parsear documento
    │  ├─ Extraer campos
    │  ├─ Filtrar por NIT
    │  └─ Yield FacturaCreate
    └─ Retorna Iterable[FacturaCreate]
```

### Fase 1: Validación

```
FacturaCreate (Pydantic Schema)
    │ Validación automática
    ├─ numero_factura: str (requerido)
    ├─ fecha_emision: date (requerido)
    ├─ subtotal, iva, total_a_pagar: Decimal (precisión)
    ├─ cufe: str (único, puede ser NULL)
    └─ proveedor_id: int (puede ser NULL)
        │ Si falta, buscar por NIT
        ▼
    ¿Todos los campos OK?
        │
        ├─ SÍ → Pasar a Fase 2
        └─ NO → Raise ValidationError
```

### Fase 2: Transformación (Normalización)

```
FacturaCreate
    │
    ├─ Items/Líneas
    │  │ Para cada item
    │  ├─ Normalizar descripción
    │  │  └─ lowercase + sin acentos + MD5 hash
    │  ├─ Detectar categoría
    │  │  └─ software, hardware, cloud, consultoría, etc.
    │  └─ Detectar recurrencia
    │     └─ ¿Contiene: "mensual", "suscripción", "anual"?
    │
    └─ Factura completa
       ├─ Validar total = subtotal + iva
       ├─ Si faltan campos
       │  └─ Usar defaults (vencimiento +30 días)
       └─ Retornar estructura normalizada
```

### Fase 3: Persistencia

```
process_and_persist_invoice()
    │
    ├─ DEDUPLICACIÓN
    │  │ ¿Ya existe por CUFE?
    │  ├─ SÍ → Actualizar o ignorar
    │  └─ NO → Continuar
    │
    │ ¿Ya existe por numero_factura + proveedor?
    │  ├─ SÍ → Ignorar (duplicado)
    │  └─ NO → Continuar
    │
    ├─ CREACIÓN EN BD (TRANSACCIONAL)
    │  ├─ INSERT Factura
    │  │  └─ estado = "en_revision"
    │  │  └─ responsable_id = NULL (se asigna después)
    │  │
    │  ├─ INSERT FacturaItems (si hay)
    │  │  └─ Uno por línea del documento
    │  │
    │  └─ COMMIT
    │
    └─ RETORNO
       └─ {"id": 123, "action": "created"}
```

### Fase 4: Workflow Automático

```
WorkflowAutomaticoService.procesar_factura_nueva(factura_id)
    │
    ├─ EXTRACCIÓN DE CONTEXTO
    │  ├─ Obtener NIT del proveedor
    │  ├─ Buscar responsables asignados al NIT
    │  └─ Buscar factura del mes anterior (si existe)
    │
    ├─ ANÁLISIS DE SIMILITUD
    │  │ ¿Existe factura anterior?
    │  ├─ SÍ
    │  │  ├─ Comparar items (hash matching)
    │  │  ├─ Calcular % similitud
    │  │  │  └─ Si >= 95% → Alta confianza
    │  │  │  └─ Si >= 70% → Media confianza
    │  │  │  └─ Si <  70% → Baja confianza
    │  │  └─ Detectar patrón de recurrencia
    │  │
    │  └─ NO → Primera factura de este proveedor
    │
    ├─ DECISIÓN AUTOMÁTICA
    │  │ confianza >= THRESHOLD (default 85%)
    │  ├─ SÍ → APROBAR AUTOMÁTICAMENTE
    │  │  ├─ Actualizar: estado = "aprobada_auto"
    │  │  ├─ Registrar: accion_por = "AUTOMATICA"
    │  │  ├─ Calcular: confianza_automatica
    │  │  └─ Crear Workflow: tipo="AUTOMATICA"
    │  │
    │  └─ NO → ENVIAR A REVISIÓN MANUAL
    │     ├─ Actualizar: estado = "en_revision"
    │     ├─ Asignar: responsable_id (por NIT)
    │     ├─ Crear Workflow: tipo="MANUAL"
    │     └─ Notificar responsable por email
    │
    └─ RESULTADO
       └─ {"exito": true, "resultado": "aprobada_auto"|"pendiente_revision"}
```

---

##  Transformación de Datos

### Normalización de Items

**Objetivo:** Hacer que items similares se reconozcan como iguales.

```python
# ENTRADA (Raw desde PDF)
{
    "descripcion": "  Servicio de Hosting AWS - Plan Premium Mensual  ",
    "cantidad": 1,
    "precio_unitario": 1000.00
}

# PROCESO
ItemNormalizerService.normalizar_item_completo(descripcion)
    ├─ normalizar_texto()
    │  ├─ Convertir a lowercase
    │  ├─ Eliminar acentos
    │  ├─ Eliminar espacios extras
    │  └─ Quitar caracteres especiales
    │  Result: "servicio de hosting aws plan premium mensual"
    │
    ├─ generar_hash()
    │  ├─ MD5("servicio de hosting aws plan premium mensual")
    │  └─ Result: "a1b2c3d4e5f6..."
    │
    ├─ detectar_categoria()
    │  ├─ Buscar palabras clave: "hosting", "aws", "cloud"
    │  └─ Result: "servicio_cloud"
    │
    └─ es_recurrente()
       ├─ Buscar: "mensual", "suscripción", "anual"
       └─ Result: true

# SALIDA (Normalizado)
{
    "descripcion": "  Servicio de Hosting AWS - Plan Premium Mensual  ",
    "descripcion_normalizada": "servicio de hosting aws plan premium mensual",
    "item_hash": "a1b2c3d4e5f6...",
    "categoria": "servicio_cloud",
    "es_recurrente": true,
    "cantidad": 1,
    "precio_unitario": 1000.00
}
```

### Flujo de Matching de Items

```
Factura Mes Actual
└─ Item: "Servicio de Hosting AWS Premium Mensual"
   ├─ Hash: "a1b2c3d4e5f6..."
   └─ Categoría: "servicio_cloud"
        │
        ├─ Buscar hash en histórico (mes anterior)
        │  │
        │  ├─ ENCONTRADO (Mes Anterior)
        │  │  └─ Item: "Servicio Hosting Amazon AWS Plan Premium - Mensual"
        │  │     └─ Hash: "a1b2c3d4e5f6..."  MISMO
        │  │
        │  │ RESULTADO: Similitud = 100% 
        │  │
        │  └─ NO ENCONTRADO
        │     │
        │     ├─ Buscar por similitud Levenshtein
        │     │  └─ "hosting aws premium" vs "hosting aws premium"
        │     │     → Similitud = 92%
        │     │
        │     └─ RESULTADO: Similitud = 92% ⚠️
        │
        └─ DECISIÓN
           ├─ Si >= 95% similitud → Patrón CONFIRMADO 
           ├─ Si 70-95% similitud → Patrón PROBABLE ⚠️
           └─ Si <70% similitud → Patrón DESCONOCIDO ❌
```

### Categorización Automática

```python
CATEGORIAS = {
    "software": [
        "licencia", "suscripción software", "adobe", "microsoft",
        "saas", "aplicación", "desarrollo software"
    ],
    "hardware": [
        "computador", "servidor", "monitor", "teclado",
        "periférico", "equipo de cómputo"
    ],
    "servicio_cloud": [
        "aws", "azure", "gcp", "hosting", "cloud",
        "infrastructure", "datacentre"
    ],
    "conectividad": [
        "internet", "fibra", "vpn", "conectividad",
        "bandwidth", "conexión"
    ],
    "energia": [
        "electricidad", "luz", "energía", "energético"
    ],
    "consultoria": [
        "consultoría", "advisory", "asesoramiento", "consultor"
    ],
    # ... más categorías
}

# Función de detección
def detectar_categoria(descripcion: str) -> Optional[str]:
    desc_lower = descripcion.lower()

    for categoria, palabras_clave in CATEGORIAS.items():
        for palabra in palabras_clave:
            if palabra in desc_lower:
                return categoria  # Primera coincidencia

    return None  # Sin categoría
```

---

## 🔌 Servicios Integrados

### 1. InvoiceService

**Ubicación:** `app/services/invoice_service.py`

```python
def process_and_persist_invoice(
    db: Session,
    payload: FacturaCreate,
    created_by: str
) -> Tuple[dict, str]:
    """
    Procesa y persiste una factura.

    Returns:
        (dict resultado, str accion)
        - accion: "created" | "updated" | "ignored" | "conflict"
    """
```

**Responsabilidades:**
-  Validación de campos obligatorios
-  Deduplicación por CUFE
-  Deduplicación por numero_factura + proveedor
-  Creación en BD (transaccional)
-  Lanzamiento automático de workflow

### 2. FacturaItemsService

**Ubicación:** `app/services/factura_items_service.py`

```python
def crear_items_desde_extractor(
    self,
    factura_id: int,
    items_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Crea items (líneas) de factura desde datos del extractor"""
```

**Responsabilidades:**
-  Creación de items/líneas
-  Normalización de descripciones
-  Generación de hashes MD5
-  Detección de categorías
-  Identificación de recurrencias

### 3. ItemNormalizerService

**Ubicación:** `app/services/item_normalizer.py`

```python
class ItemNormalizerService:
    @staticmethod
    def normalizar_texto(texto: str) -> str:
        # Normalización para matching

    @staticmethod
    def generar_hash(texto_normalizado: str) -> str:
        # MD5 para búsqueda rápida

    @classmethod
    def detectar_categoria(cls, desc: str) -> Optional[str]:
        # Categoría automática

    @classmethod
    def es_recurrente(cls, desc: str) -> bool:
        # ¿Mensual, anual, suscripción?
```

### 4. WorkflowAutomaticoService

**Ubicación:** `app/services/workflow_automatico.py`

```python
def procesar_factura_nueva(self, factura_id: int) -> Dict[str, Any]:
    """
    Crea workflow automático:
    1. Extrae NIT
    2. Busca responsables
    3. Analiza similitud
    4. Aprueba o envía a revisión
    5. Notifica
    """
```

### 5. MicrosoftGraphEmailService

**Ubicación:** `app/services/microsoft_graph_email_service.py`

```python
def get_emails_with_attachments(
    self,
    mailbox: str = "inbox",
    days_back: int = 7,
    filter_senders: Optional[List[str]] = None
) -> Iterable[Email]:
    """
    Obtiene emails con attachments.

    Usado por MicrosoftGraphInvoiceExtractor.
    """
```

---

## ⚠️ Manejo de Errores

### 1. Errores en Parseo de PDFs

```python
try:
    # Intentar parsear PDF
    with pdfplumber.open(attachment.data) as pdf:
        data = self._extract_from_pdf(pdf)
except Exception as e:
    logger.error(f"Error parsing PDF {attachment.filename}: {str(e)}")
    # Registrar en auditoría pero continuar
    # No abortar, permitir que otros emails se procesen
    continue
```

### 2. Errores en Validación

```python
try:
    factura = FacturaCreate(**datos_parseados)
except ValidationError as e:
    logger.error(f"Validación falló: {e.errors()}")

    # Opciones:
    # 1. Ignorar factura (si error es recuperable)
    # 2. Alertar a admin (si error es crítico)
    # 3. Registrar para revisión manual

    audit_log.create(
        tabla="facturas",
        accion="validation_error",
        detalle=e.errors(),
        creado_por="SYSTEM"
    )
```

### 3. Errores en Persistencia

```python
try:
    # Insertar en BD
    factura = create_factura(db, datos)
    db.commit()

except IntegrityError as e:
    # Violación de constraint (ej: CUFE duplicado)
    db.rollback()
    logger.warning(f"Integrity error (posible duplicado): {str(e)}")
    return {"action": "ignored", "reason": "duplicate"}

except Exception as e:
    # Error desconocido
    db.rollback()
    logger.error(f"Error crítico en persistencia: {str(e)}", exc_info=True)
    raise
```

### 4. Errores en Workflow

```python
try:
    workflow_service = WorkflowAutomaticoService(db)
    resultado = workflow_service.procesar_factura_nueva(factura_id)

except Exception as e:
    # El workflow falla, pero factura ya está creada
    logger.error(f"Error en workflow: {str(e)}")

    # Registrar pero NO fallar
    audit_log.create(
        tabla="workflow",
        accion="error",
        detalle={"error": str(e)},
        creado_por="SYSTEM"
    )

    # Notificar a admin
    send_alert_to_admin(f"Workflow error para factura {factura_id}")
```

---

## ⚙️ Configuración

### Variables de Entorno

```bash
# .env

# TIPO DE EXTRACTOR
INVOICE_EXTRACTOR_TYPE=dummy                    # dummy | microsoft_graph
INVOICE_EXTRACTOR_BATCH_SIZE=500               # Facturas por batch

# MICROSOFT GRAPH (si usa microsoft_graph)
GRAPH_TENANT_ID=c9ef7bf6-bbe0-4c50-b2e9-ea58d635ca46
GRAPH_CLIENT_ID=79dc4cdc-137b-415f-8193-a7a5b3fdd47b
GRAPH_CLIENT_SECRET=M6q8Q~_...
GRAPH_FROM_EMAIL=noreply@empresa.com

# EXTRACTOR CONFIG
EXTRACTOR_DAYS_BACK=7                          # Descargar últimos N días
EXTRACTOR_MAX_RETRIES=3                        # Reintentos en error
EXTRACTOR_TIMEOUT_SECONDS=300                  # Timeout por email

# NORMALIZACIÓN
ITEM_SIMILARITY_THRESHOLD=0.70                 # Threshold para match
DESCRIPTION_NORMALIZATION_ENABLED=true         # Activar normalización

# WORKFLOW
AUTOMATION_APPROVAL_THRESHOLD=0.85              # Confianza para aprobar auto
AUTOMATION_REVISION_THRESHOLD=0.70              # Confianza para revisar

# SCHEDULER
AUTOMATION_RUN_INTERVAL_MINUTES=60              # Cada cuánto ejecutar
EXTRACTOR_RUN_INTERVAL_MINUTES=60              # (Cuando esté implementado)

# LOGGING
LOG_LEVEL=INFO
LOG_FILE=logs/invoice_extractor.log
```

### Constantes de Sistema

```python
# app/core/config.py

class Settings(BaseSettings):
    # Extractor
    INVOICE_EXTRACTOR_TYPE: str = "dummy"
    INVOICE_EXTRACTOR_BATCH_SIZE: int = 500
    INVOICE_EXTRACTOR_TIMEOUT_SECONDS: int = 300

    # Normalización
    ITEM_SIMILARITY_THRESHOLD: float = 0.70
    DESCRIPTION_NORMALIZATION_ENABLED: bool = True

    # Workflow
    WORKFLOW_APPROVAL_CONFIDENCE_MIN: Decimal = Decimal("0.85")
    WORKFLOW_REVISION_CONFIDENCE_MIN: Decimal = Decimal("0.70")

    # Análisis histórico
    MONTHS_HISTORICAL_ANALYSIS: int = 12
    PATTERN_DETECTION_ENABLED: bool = True
```

---

## 🧪 Testing

### 1. Test de Interface (Dummy)

```python
# tests/test_invoice_extractor.py

from app.services.extractor.invoice_extractor_dummy import DummyExtractor
from app.schemas.factura import FacturaCreate

def test_dummy_extractor():
    """Test que DummyExtractor retorna factura válida"""
    extractor = DummyExtractor()

    facturas = list(extractor.extract())

    assert len(facturas) == 1
    assert isinstance(facturas[0], FacturaCreate)
    assert facturas[0].numero_factura == "FAC-DUMMY-001"
    assert facturas[0].total_a_pagar == Decimal("1190.00")
```

### 2. Test de Normalización

```python
def test_item_normalizer():
    """Test que ItemNormalizerService normaliza correctamente"""
    from app.services.item_normalizer import ItemNormalizerService

    # Entrada con variaciones
    desc1 = "  Servicio de Hosting AWS - Plan Premium Mensual  "
    desc2 = "servicio hosting aws plan premium mensual"

    # Ambas deben generar el mismo hash
    hash1 = ItemNormalizerService.generar_hash(
        ItemNormalizerService.normalizar_texto(desc1)
    )
    hash2 = ItemNormalizerService.generar_hash(
        ItemNormalizerService.normalizar_texto(desc2)
    )

    assert hash1 == hash2, "Hashes deberían coincidir"
```

### 3. Test de Persistencia

```python
def test_process_and_persist_invoice(db: Session):
    """Test creación de factura en BD"""
    from app.services.invoice_service import process_and_persist_invoice

    factura_data = FacturaCreate(
        numero_factura="FAC-TEST-001",
        fecha_emision=date.today(),
        proveedor_id=1,
        subtotal=Decimal("1000.00"),
        iva=Decimal("190.00"),
        total_a_pagar=Decimal("1190.00"),
        cufe="TEST-CUFE-001"
    )

    resultado, accion = process_and_persist_invoice(db, factura_data, "TEST")

    assert accion == "created"
    assert resultado["id"] is not None

    # Verificar en BD
    factura = db.query(Factura).get(resultado["id"])
    assert factura.numero_factura == "FAC-TEST-001"
    assert factura.estado == "en_revision"  # Estado default
```

### 4. Test de Deduplicación

```python
def test_duplicate_cufe(db: Session):
    """Test que no crea duplicados por CUFE"""

    factura_data = FacturaCreate(
        numero_factura="FAC-DUP-001",
        fecha_emision=date.today(),
        proveedor_id=1,
        subtotal=Decimal("1000.00"),
        iva=Decimal("190.00"),
        total_a_pagar=Decimal("1190.00"),
        cufe="SAME-CUFE"
    )

    # Primera creación
    resultado1, accion1 = process_and_persist_invoice(db, factura_data, "TEST")
    assert accion1 == "created"

    # Intento duplicado
    resultado2, accion2 = process_and_persist_invoice(db, factura_data, "TEST")
    assert accion2 == "ignored"  # Debe ignorar
    assert resultado1["id"] == resultado2["id"]  # Mismo ID
```

### 5. Test de Workflow Integration

```python
def test_workflow_integration(db: Session):
    """Test que workflow se crea automáticamente"""

    factura_data = FacturaCreate(
        numero_factura="FAC-WF-001",
        fecha_emision=date.today(),
        proveedor_id=1,
        subtotal=Decimal("1000.00"),
        iva=Decimal("190.00"),
        total_a_pagar=Decimal("1190.00"),
        cufe="WF-TEST-001"
    )

    resultado, accion = process_and_persist_invoice(db, factura_data, "TEST")

    # Verificar que se creó workflow
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura

    workflow = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.factura_id == resultado["id"]
    ).first()

    assert workflow is not None
    assert workflow.estado in ["APROBADA_AUTO", "PENDIENTE_REVISION"]
```

---

## 🚀 Roadmap de Implementación

### PRIORIDAD 1: CRÍTICA (2-3 días)

#### 1. Implementar MicrosoftGraphInvoiceExtractor

```python
# Tareas:
- [ ] Crear clase MicrosoftGraphInvoiceExtractor
- [ ] Implementar método extract()
- [ ] Conectar a Microsoft Graph API
- [ ] Descargar emails del Inbox
- [ ] Extraer attachments
- [ ] Parsear PDFs (usar pdfplumber)
- [ ] Parsear XMLs (usar xml.etree)
- [ ] Validar datos extraídos
- [ ] Filtrar por NITs configurados
- [ ] Retornar Iterable[FacturaCreate]
```

**Estimación:** 2-3 días

#### 2. Agregar Librerías de Parseo

```bash
# Actualizar requirements.txt
pdfplumber>=0.10.0,<1.0.0        # PDF extraction
reportlab>=4.0.0,<5.0.0          # PDF generation
PyPDF2>=3.0.0,<4.0.0             # PDF manipulation

# Opcional para OCR (si PDFs no son text-based)
pytesseract>=0.3.10,<1.0.0
```

**Estimación:** 1 día (instalación + testing)

#### 3. Integrar Extractor con Scheduler

```python
# Modificar app/core/lifespan.py

async def run_automation_task():
    # FASE 0: EXTRACCIÓN (nuevo)
    try:
        extractor = get_extractor()  # Factory pattern

        for factura_data in extractor.extract(batch_size=500):
            resultado, accion = process_and_persist_invoice(
                db, factura_data, created_by="EXTRACTOR"
            )
            logger.info(f"Factura {accion}: {resultado}")

    except Exception as e:
        logger.error(f"Error en fase de extracción: {str(e)}")

    # FASE 1: WORKFLOW AUTOMÁTICO (existente)
    # ... resto de código ...
```

**Estimación:** 1 día

### PRIORIDAD 2: ALTA (1 día)

#### 1. Validación Robusta de NITs

```python
# Mejorar:
- [ ] Validación formato NIT (800.123.456-7)
- [ ] Búsqueda en tabla email_config
- [ ] Crear log de NITs rechazados
- [ ] Alertar si NIT no encontrado
- [ ] Permitir wildcard o lista blanca
```

#### 2. Error Handling Mejorado

```python
# Implementar:
- [ ] Retry logic para conexiones fallidas
- [ ] Dead letter queue para emails no procesables
- [ ] Alertas a admin de errores críticos
- [ ] Logging detallado de cada paso
```

### PRIORIDAD 3: MEDIA (1-2 días)

#### 1. Expansión de Test Coverage

```python
# Tests faltantes:
- [ ] test_microsoft_graph_extraction()
- [ ] test_pdf_parsing_with_real_pdf()
- [ ] test_xml_parsing_with_real_xml()
- [ ] test_nit_filtering()
- [ ] test_batch_processing()
- [ ] test_error_recovery()
- [ ] test_large_dataset_performance()
```

#### 2. Performance Optimization

```python
# Optimizaciones:
- [ ] Bulk insert de facturas (SQL)
- [ ] Caché de NITs configurados
- [ ] Cursor pagination para large datasets
- [ ] Índices en tabla factura_items
- [ ] Conexión pooling a Microsoft Graph
```

### PRIORIDAD 4: BAJA (Futuro)

#### 1. Soporte para Más Fuentes
```
- SFTP servers (FTP automático)
- Dropbox / Google Drive
- EDI (Electronic Data Interchange)
- WebhooksAPI de proveedores
```

#### 2. OCR para PDFs No-Estructurados
```
- Usar Tesseract/PyTorch para OCR
- Entrenar modelos para formatos específicos
- Validación humana de OCR
```

#### 3. Machine Learning para Clasificación
```
- Entrenar modelos para categorización automática
- Predicción de proveedores por descripción
- Anomaly detection en montos
```

---

##  Matriz de Dependencias

```
Invoice Extractor
├── requires: IInvoiceExtractor (ABC)
├── uses: MicrosoftGraphEmailService
├── uses: pdfplumber (para PDFs)
├── uses: xml.etree (para XMLs)
├── uses: ItemNormalizerService
│   └── uses: Regex, MD5
├── uses: FacturaItemsService
│   └── uses: ItemNormalizerService
├── uses: InvoiceService
│   ├── uses: CRUD Factura
│   ├── uses: WorkflowAutomaticoService
│   ├── uses: AuditService
│   └── produces: Factura + FacturaItems + Workflow
├── produces: FacturaCreate (Pydantic Schema)
└── integrates: WorkflowAutomaticoService
    ├── decides: aprobar automática vs revisión manual
    ├── notifies: responsables por email
    └── writes: WorkflowAprobacionFactura
```

---

## 📝 Checklist de Implementación

### Pre-Implementación
- [ ] Revisar especificaciones de PDF/XML de proveedores
- [ ] Obtener credenciales de Microsoft Graph
- [ ] Planificar estrategia de parseo (regex vs OCR)
- [ ] Hacer backup de BD de producción

### Desarrollo
- [ ] Crear clase MicrosoftGraphInvoiceExtractor
- [ ] Implementar parsing (PDF, XML)
- [ ] Implementar filtering (NITs)
- [ ] Implementar error handling
- [ ] Integrar con scheduler
- [ ] Tests unitarios
- [ ] Tests de integración
- [ ] Performance testing

### QA
- [ ] Validar con datos reales
- [ ] Pruebas de carga
- [ ] Validación de duplicados
- [ ] Validación de workflows
- [ ] Pruebas de recuperación de errores

### Deploy
- [ ] Agregar librerías a requirements.txt
- [ ] Actualizar variables de entorno
- [ ] Crear migraciones de BD (si necesario)
- [ ] Documentar cambios
- [ ] Capacitar a soporte
- [ ] Monitoreo de logs

---

## 🎯 KPIs de Éxito

Una vez implementado, el Invoice Extractor debe:

| KPI | Target | Métrica |
|---|---|---|
| **Facturas Procesadas/Hora** | >100 | Automático desde emails |
| **Tasa de Éxito de Parseo** | >95% | Facturas parseadas correctamente |
| **Tasa de Duplicados Evitados** | 100% | Deduplicación funciona |
| **Aprobación Automática** | >70% | Facturas aprobadas sin intervención |
| **Tiempo Promedio de Procesamiento** | <30 seg | Por factura |
| **Error Recovery Time** | <1 min | Recuperación de fallos |
| **Uptime** | 99.9% | Disponibilidad del servicio |

---

## 📞 Contacto y Soporte

Para implementar el Invoice Extractor:

| Rol | Contacto | Área |
|-----|----------|------|
| **Backend Lead** | Equipo Backend | Arquitectura, Integración |
| **Microsoft Azure Admin** | IT Security | Credenciales, Permisos |
| **QA Lead** | QA Team | Testing, Validación |
| **Devops** | Devops Team | Deployment, Monitoreo |

---

## 📚 Referencias Técnicas

### Documentación Oficial
- [Microsoft Graph API](https://docs.microsoft.com/graph)
- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)
- [Python xml.etree](https://docs.python.org/3/library/xml.etree.elementtree.html)
- [DIAN Colombia (Facturación Electrónica)](https://www.dian.gov.co)

### Archivos Relacionados
- `app/services/extractor/base.py` - Interface
- `app/services/extractor/invoice_extractor_dummy.py` - Dummy implementation
- `app/services/invoice_service.py` - Persistencia
- `app/services/workflow_automatico.py` - Automatización
- `app/services/item_normalizer.py` - Normalización
- `app/core/lifespan.py` - Scheduler

---

**Documento Generado:** Noviembre 2024
**Estado:** Pre-Release (Falta implementación)
**Licencia:** MIT

Este documento es una guía completa para implementar, testear y desplegar el módulo Invoice Extractor. La arquitectura está solidamente diseñada, pero la implementación requiere 3-5 días de trabajo desarrollo + testing.
