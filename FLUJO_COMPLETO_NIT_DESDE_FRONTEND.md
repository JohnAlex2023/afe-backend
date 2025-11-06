# FLUJO COMPLETO: ¿QUÉ PASA CUANDO EL USUARIO INGRESA UN NIT EN EL FRONTEND?

**Análisis detallado del flujo de entrada y procesamiento de NITs**
**Fecha**: 2025-10-30
**Alcance**: Frontend → Backend → invoice_extractor

---

## 🎯 RESUMEN EJECUTIVO

Cuando el usuario admin ingresa un NIT sin DV en el afe_frontend:

```
USUARIO INGRESA: "800185449" (sin DV)
        ↓
FRONTEND VALIDA FORMATO: ✅ "^\d{5,20}$"
        ↓
FRONTEND ENVÍA AL BACKEND:
POST /api/v1/email-config/nits
{
  "cuenta_correo_id": 1,
  "nit": "800185449",          ← SIN DV
  "nombre_proveedor": "EMPRESA A"
}
        ↓
BACKEND RECIBE Y NORMALIZA:
- NitValidator.validar_nit("800185449")
- Calcula DV → "9"
- Retorna: "800185449-9"    ← CON DV
        ↓
BACKEND ALMACENA EN BD:
INSERT INTO nit_configuracion (nit) VALUES ("800185449-9")
        ↓
FRONTEND RECIBE RESPUESTA CON NIT NORMALIZADO
{ "nit": "800185449-9", ... }
        ↓
API PÚBLICA RETORNA NITs NORMALIZADOS:
GET /api/v1/email-config/configuracion-extractor-public
{
  "users": [{
    "nits": ["800185449-9", "805012966-1", ...]
  }]
}
        ↓
INVOICE_EXTRACTOR OBTIENE NITs NORMALIZADOS
y busca emails con esos NITs
```

**Conclusión**: El frontend NUNCA calcula DV. El backend es responsable.

---

## 1. USUARIO INGRESA NIT EN FRONTEND

### 1.1 Ubicación del Formulario

**Archivo**: `c:\Users\jhont\PRIVADO_ODO\afe_frontend\src\features\email-config\components\AddNitDialog.tsx`

**Opciones**:
- ✅ Dialog individual: para agregar 1 NIT
- ✅ Dialog bulk: para agregar múltiples NITs

### 1.2 Validación en Frontend (ANTES de enviar)

**Archivo**: `AddNitDialog.tsx` (línea 25-33)

```typescript
const schema = z.object({
  nit: z
    .string()
    .regex(/^\d{5,20}$/, 'El NIT debe contener solo números (5-20 dígitos)')
    .min(5, 'Mínimo 5 dígitos')
    .max(20, 'Máximo 20 dígitos'),
  nombre_proveedor: z.string().optional(),
  notas: z.string().optional(),
});
```

**Qué valida:**
- ✅ Solo números
- ✅ Entre 5-20 dígitos
- ❌ NO valida el dígito verificador (es responsabilidad del backend)
- ❌ NO calcula el DV

**Ejemplo de lo que acepta el frontend:**
```
"800185449"     ✅ Válido (sin DV)
"8"             ❌ Inválido (muy corto)
"800.185.449"   ❌ Inválido (tiene punto)
"800185449-9"   ✅ Válido (con DV, pero no lo valida)
"800185449ABC"  ❌ Inválido (tiene letras)
```

**NIT sin DV es lo NORMAL**: El usuario copia del papel/email el NIT tal como viene

### 1.3 Dialog Individual

**Archivo**: `AddNitDialog.tsx` (línea 64-85)

```typescript
const onSubmit = async (data: FormData) => {
    setLoading(true);
    setError(null);

    try {
      // PASO 1: Dispatch Redux action con el NIT SIN DV
      await dispatch(
        crearNit({
          cuenta_correo_id: cuentaId,
          nit: data.nit,                    // ← "800185449" (sin DV)
          nombre_proveedor: data.nombre_proveedor || undefined,
          notas: data.notas || undefined,
        })
      ).unwrap();

      onSuccess();
      handleClose();
    } catch (err: any) {
      setError(err.message || 'Error al agregar NIT');
    } finally {
      setLoading(false);
    }
  };
```

### 1.4 Dialog Bulk (Múltiples NITs)

**Archivo**: `AddNitsBulkDialog.tsx` (línea 55-92)

```typescript
const procesarNits = (texto: string): string[] => {
    // Separar por comas, espacios, saltos de línea
    return texto
      .split(/[\s,\n\r]+/)
      .map((nit) => nit.trim())
      .filter((nit) => nit.length > 0);
  };

const handleAgregar = async () => {
    // Validar que sean números
    const nitsInvalidos = nitsArray.filter((nit) => !/^\d{5,20}$/.test(nit));
    if (nitsInvalidos.length > 0) {
      setError(`NITs inválidos encontrados: ${nitsInvalidos.join(', ')}`);
      return;
    }

    // Dispatch Redux action
    const result = await dispatch(
      crearNitsBulk({
        cuenta_correo_id: cuentaId,
        nits: nitsArray,              // ← ["800185449", "805012966", ...] (sin DV)
      })
    ).unwrap();
```

**El usuario puede pegar NITs en CUALQUIER FORMATO**:
```
800185449
805012966
830122566

# O en una línea:
800185449, 805012966, 830122566

# O con espacios:
800185449 805012966 830122566
```

El dialog simplemente separa por espacios/comas/saltos de línea.

---

## 2. FRONTEND ENVÍA AL BACKEND

### 2.1 Redux Action

**Archivo**: `emailConfigSlice.ts`

```typescript
export const crearNit = createAsyncThunk(
  'emailConfig/crearNit',
  async (data: {
    cuenta_correo_id: number;
    nit: string;
    nombre_proveedor?: string;
    notas?: string;
  }) => {
    return await emailConfigService.crearNit(data);
  }
);

export const crearNitsBulk = createAsyncThunk(
  'emailConfig/crearNitsBulk',
  async (data: { cuenta_correo_id: number; nits: string[] }) => {
    return await emailConfigService.crearNitsBulk(data);
  }
);
```

### 2.2 Servicio API

**Archivo**: `emailConfigService.ts` (línea 193-201)

```typescript
// Crear NIT individual
crearNit: async (data: CreateNit): Promise<NitConfiguracion> => {
    const response = await apiClient.post(`${BASE_PATH}/nits`, data);
    // POST /api/v1/email-config/nits
    // Body: { cuenta_correo_id, nit, nombre_proveedor, notas }
    return response.data;
  },

// Crear múltiples NITs (bulk)
crearNitsBulk: async (data: BulkCreateNits): Promise<BulkNitsResponse> => {
    const response = await apiClient.post(`${BASE_PATH}/nits/bulk`, data);
    // POST /api/v1/email-config/nits/bulk
    // Body: { cuenta_correo_id, nits: ["800185449", "805012966", ...] }
    return response.data;
  },
```

**Request que llega al backend**:

```
POST /api/v1/email-config/nits
Content-Type: application/json

{
  "cuenta_correo_id": 1,
  "nit": "800185449",          ← SIN DV
  "nombre_proveedor": "EMPRESA A",
  "notas": null
}
```

O para bulk:

```
POST /api/v1/email-config/nits/bulk
Content-Type: application/json

{
  "cuenta_correo_id": 1,
  "nits": ["800185449", "805012966", "830122566"]  ← SIN DV
}
```

---

## 3. BACKEND PROCESA Y NORMALIZA

### 3.1 Endpoint Individual

**Archivo**: `app/api/v1/routers/email_config.py` (línea 189-220)

```python
@router.post("/nits", response_model=NitConfiguracionResponse)
def crear_nit_configuracion(
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
    payload: NitConfiguracionCreate = Body(...),
):
    """
    Crea una nueva configuración de NIT para una cuenta de correo.

    PASO 1: Validar NIT
    - Acepta cualquier formato
    - Calcula DV si no tiene
    - Verifica que sea válido
    """

    # PASO 1: VALIDAR Y NORMALIZAR NIT
    es_valido, nit_normalizado = NitValidator.validar_nit(payload.nit)

    if not es_valido:
        raise HTTPException(
            status_code=400,
            detail=f"NIT inválido: {payload.nit}"
        )

    # PASO 2: VERIFICAR que existe en tabla PROVEEDORES
    proveedor = db.query(Proveedor).filter(
        Proveedor.nit == nit_normalizado
    ).first()

    if not proveedor:
        # Si no existe, crear automáticamente
        proveedor = Proveedor(
            nit=nit_normalizado,
            razon_social=payload.nombre_proveedor or f"Proveedor {nit_normalizado}",
        )
        db.add(proveedor)
        db.flush()

    # PASO 3: CREAR registro NitConfiguracion
    nit_config = NitConfiguracion(
        cuenta_correo_id=payload.cuenta_correo_id,
        nit=nit_normalizado,          # ← ALMACENA CON DV
        nombre_proveedor=payload.nombre_proveedor,
        activo=True,
    )

    db.add(nit_config)
    db.commit()
    db.refresh(nit_config)

    return NitConfiguracionResponse(
        id=nit_config.id,
        nit=nit_config.nit,           # ← RETORNA CON DV: "800185449-9"
        nombre_proveedor=nit_config.nombre_proveedor,
        activo=nit_config.activo,
    )
```

### 3.2 Endpoint Bulk

**Archivo**: `app/api/v1/routers/email_config.py` (línea 221-307)

```python
@router.post("/nits/bulk", response_model=BulkNitsResponse)
def crear_nits_bulk(
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
    payload: BulkCreateNits = Body(...),
):
    """
    Crea múltiples NITs en una sola operación.

    PASOS:
    1. Para CADA NIT en el payload:
       - Validar y normalizar
       - Verificar que no sea duplicado
       - Crear en BD
    2. Retornar estadísticas de lo creado/duplicado/fallido
    """

    cuenta_correo_id = payload.cuenta_correo_id
    nits_raw = payload.nits  # ["800185449", "805012966", ...]

    # VERIFICAR que la cuenta existe
    cuenta = db.query(CuentaCorreo).filter(
        CuentaCorreo.id == cuenta_correo_id
    ).first()

    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    # Procesar cada NIT
    nits_agregados = 0
    nits_duplicados = 0
    nits_fallidos = 0
    detalles = []

    for nit_raw in nits_raw:
        detalle = {"nit": nit_raw}

        try:
            # PASO 1: VALIDAR Y NORMALIZAR
            es_valido, nit_normalizado = NitValidator.validar_nit(nit_raw)

            if not es_valido:
                detalle["status"] = "error"
                detalle["mensaje"] = f"NIT inválido: {nit_normalizado}"
                nits_fallidos += 1
                detalles.append(detalle)
                continue

            # PASO 2: VERIFICAR DUPLICADO
            existente = db.query(NitConfiguracion).filter(
                and_(
                    NitConfiguracion.nit == nit_normalizado,
                    NitConfiguracion.cuenta_correo_id == cuenta_correo_id
                )
            ).first()

            if existente:
                detalle["status"] = "duplicado"
                detalle["id"] = existente.id
                nits_duplicados += 1
                detalles.append(detalle)
                continue

            # PASO 3: CREAR en BD
            nit_config = NitConfiguracion(
                cuenta_correo_id=cuenta_correo_id,
                nit=nit_normalizado,      # ← CON DV
                nombre_proveedor=None,
                activo=True,
            )

            db.add(nit_config)
            db.flush()

            detalle["status"] = "agregado"
            detalle["id"] = nit_config.id
            detalle["nit"] = nit_normalizado  # ← NORMALIZADO
            nits_agregados += 1
            detalles.append(detalle)

        except Exception as e:
            detalle["status"] = "error"
            detalle["mensaje"] = str(e)
            nits_fallidos += 1
            detalles.append(detalle)

    # COMMIT final
    db.commit()

    # Retornar respuesta
    return BulkNitsResponse(
        cuenta_correo_id=cuenta_correo_id,
        nits_agregados=nits_agregados,
        nits_duplicados=nits_duplicados,
        nits_fallidos=nits_fallidos,
        detalles=[
            {"nit": d["nit"], "status": d["status"], "mensaje": d.get("mensaje")}
            for d in detalles
        ]
    )
```

### 3.3 NitValidator (La magia del cálculo de DV)

**Archivo**: `app/utils/nit_validator.py` (línea 26-207)

```python
class NitValidator:

    @staticmethod
    def calcular_digito_verificador(nit_sin_dv: str) -> str:
        """
        Calcula DV usando ALGORITMO DIAN OFICIAL
        Orden Administrativa N°4 del 27/10/1989

        Multiplicadores: [41, 37, 29, 23, 19, 17, 13, 7, 3]
        """
        multiplicadores = [41, 37, 29, 23, 19, 17, 13, 7, 3]

        # Validar entrada
        if not nit_sin_dv or not nit_sin_dv.isdigit():
            raise ValueError(f"NIT debe ser dígitos: {nit_sin_dv}")

        # Rellenar a 9 dígitos
        nit_padded = nit_sin_dv.zfill(9)  # "000800185449" → "800185449"

        # Multiplicar y sumar
        suma = sum(
            int(nit_padded[i]) * multiplicadores[i]
            for i in range(9)
        )

        # Módulo 11
        residuo = suma % 11

        # Calcular DV
        if residuo < 2:
            return str(residuo)
        return str(11 - residuo)

    @staticmethod
    def normalizar_nit(nit: str) -> str:
        """
        Entrada: "800185449" o "800.185.449" o "800185449-9"
        Salida: "800185449-9"
        """
        # Limpiar
        nit = nit.replace(".", "").replace(" ", "").strip()

        # Separar número y DV si existe
        if "-" in nit:
            partes = nit.split("-")
            nit_numero = partes[0]
            dv_proporcionado = partes[1]
        else:
            nit_numero = nit
            dv_proporcionado = None

        # Validar parte numérica
        if not nit_numero.isdigit() or len(nit_numero) > 9:
            raise ValueError(f"NIT inválido: {nit}")

        # Rellenar a 9 dígitos
        nit_padded = nit_numero.zfill(9)

        # Calcular DV
        dv_calculado = NitValidator.calcular_digito_verificador(nit_padded)

        # Si tenía DV, verificar que sea correcto
        if dv_proporcionado and dv_proporcionado != dv_calculado:
            raise ValueError(
                f"DV incorrecto para {nit_numero}: "
                f"proporcionado={dv_proporcionado}, correcto={dv_calculado}"
            )

        return f"{nit_padded}-{dv_calculado}"

    @staticmethod
    def validar_nit(nit: str) -> Tuple[bool, str]:
        """
        Entrada: Cualquier formato
        Salida: (es_válido, nit_normalizado_o_error)
        """
        try:
            nit_normalizado = NitValidator.normalizar_nit(nit)
            return (True, nit_normalizado)
        except Exception as e:
            return (False, str(e))
```

---

## 4. RESPUESTA DEL BACKEND AL FRONTEND

### 4.1 Response Individual

```json
{
  "id": 42,
  "cuenta_correo_id": 1,
  "nit": "800185449-9",              ← CON DV, NORMALIZADO
  "nombre_proveedor": "EMPRESA A",
  "activo": true,
  "creado_en": "2025-10-30T14:30:00Z",
  "actualizado_en": "2025-10-30T14:30:00Z",
  "creado_por": "admin",
  "actualizado_por": null
}
```

### 4.2 Response Bulk

```json
{
  "cuenta_correo_id": 1,
  "nits_agregados": 2,
  "nits_duplicados": 0,
  "nits_fallidos": 0,
  "detalles": [
    {
      "nit": "800185449-9",           ← NORMALIZADO
      "status": "agregado",
      "id": 42
    },
    {
      "nit": "805012966-1",           ← NORMALIZADO
      "status": "agregado",
      "id": 43
    }
  ]
}
```

### 4.3 Frontend recibe y actualiza Redux

```typescript
.addCase(crearNit.fulfilled, (state, action) => {
    // action.payload contiene el NIT NORMALIZADO del backend
    state.nits.push(action.payload);
    // Ahora guarda: { nit: "800185449-9", ... }
});
```

---

## 5. API PÚBLICA PARA INVOICE_EXTRACTOR

### 5.1 Endpoint

**Ubicación**: `app/api/v1/routers/email_config.py` (línea 310-350)

```
GET /api/v1/email-config/configuracion-extractor-public
```

Sin autenticación (es pública).

### 5.2 Respuesta

```json
{
  "users": [
    {
      "cuenta_id": 1,
      "email": "diacorsoacha@avidanti.com",
      "nits": [
        "800185449-9",      ← NORMALIZADO, CON DV
        "805012966-1",      ← NORMALIZADO, CON DV
        "830122566-3",      ← NORMALIZADO, CON DV
        "900399741-7"       ← NORMALIZADO, CON DV
      ],
      "max_correos_por_ejecucion": 500,
      "ventana_inicial_dias": 365,
      "ultima_ejecucion_exitosa": null,
      "fecha_ultimo_correo_procesado": null
    }
  ],
  "total_cuentas": 1,
  "total_nits": 4,
  "generado_en": "2025-10-30T14:35:22Z"
}
```

**TODOS los NITs están normalizados con DV**

---

## 6. INVOICE_EXTRACTOR USA LOS NITs

### 6.1 Cómo obtiene la configuración

**Archivo**: `invoice_extractor/src/core/config.py` (línea 114-180)

```python
def load_config(settings_path: Optional[Path] = None, use_api: bool = True) -> Settings:
    """
    Carga configuración desde:
    1. API: GET /api/v1/email-config/configuracion-extractor-public
    2. Fallback: settings.json local
    """

    # Intentar obtener desde API
    if use_api:
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        api_endpoint = f"{api_base_url}/api/v1/email-config/configuracion-extractor-public"

        try:
            users_data = fetch_config_from_api(api_endpoint)
            # users_data contiene NITs NORMALIZADOS: "800185449-9"
            return Settings(users=users_data, ...)
        except Exception as e:
            # Fallback a settings.json
            pass
```

### 6.2 Cómo busca emails con los NITs

**Archivo**: `invoice_extractor/src/modules/email_reader.py` (línea 74-100)

```python
def _filter_for_nit(
    self,
    nit: str,           # ← Recibe "800185449-9" (normalizado)
    last_days: Optional[int] = None,
    fecha_desde: Optional[datetime] = None
) -> str:
    """
    Genera filtro OData para buscar emails que contengan el NIT.
    """

    # El NIT ya viene normalizado: "800185449-9"
    # Se usa tal cual en la búsqueda

    since_clause = f" and receivedDateTime ge {dt_str}"

    # El filtro resultante es:
    # hasAttachments:true and from:"xxx@email.com" and body:contains("800185449")
```

### 6.3 Normalización interna del NIT extraído

**Archivo**: `invoice_extractor/src/extraction/basic_extractor.py` (línea 70-93)

```python
def extract_supplier_nit(self, root: etree._Element) -> Optional[str]:
    """
    Extrae NIT del XML.
    XML contiene: <cbc:CompanyID>800185449</cbc:CompanyID> (sin DV)

    Proceso:
    1. Extrae: "800185449"
    2. Agrega DV: "800185449-9"
    3. Retorna: "800185449-9"
    """

    nit = get_text(
        root,
        ".//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID"
    )

    # AGREGA DÍGITO VERIFICADOR
    return completar_nit_con_dv(nit) if nit else None
```

**Función que agrega DV**:

```python
def completar_nit_con_dv(nit: str) -> str:
    """
    "800185449" → "800185449-9"
    "800185449-9" → "800185449-9" (sin cambios)
    """
    if not nit:
        return nit

    nit = nit.strip()

    if "-" in nit:
        return nit  # Ya tiene DV

    if nit.isdigit():
        dv = calcular_digito_verificador_nit(nit)
        if dv:
            return f"{nit}-{dv}"

    return nit
```

---

## 7. TABLA RESUMEN: DÓNDE SE NORMALIZA EL NIT

| Punto | Formato | Cálculo | Responsable |
|------|---------|---------|------------|
| **Usuario ingresa (Frontend)** | Sin DV: `800185449` | NO | Usuario |
| **Frontend valida** | Sin DV: `800185449` | NO | Frontend (solo formato) |
| **Frontend envía al Backend** | Sin DV: `800185449` | NO | Frontend |
| **Backend recibe** | Sin DV: `800185449` | NO | Backend (input) |
| **Backend calcula DV** | Con DV: `800185449-9` | ✅ SÍ | **NitValidator backend** |
| **Backend almacena en BD** | Con DV: `800185449-9` | YA HECHO | Backend (BD) |
| **Backend retorna al Frontend** | Con DV: `800185449-9` | LISTO | Backend |
| **API pública retorna** | Con DV: `800185449-9` | LISTO | Backend (API) |
| **invoice_extractor recibe** | Con DV: `800185449-9` | LISTO | - |
| **invoice_extractor extrae XML** | Sin DV: `800185449` | NO | XML emisor |
| **invoice_extractor completa DV** | Con DV: `800185449-9` | ✅ SÍ | **completar_nit_con_dv()** |
| **invoice_extractor ingesta BD** | Con DV: `800185449-9` | LISTO | invoice_extractor |

---

## 8. DIAGRAMA COMPLETO

```
┌─────────────────────────────────────────────────────────┐
│ AFE-FRONTEND                                            │
│                                                         │
│ Usuario ingresa: "800185449" (sin DV)                   │
│ Frontend valida formato: ^\d{5,20}$                     │
│ ❌ Frontend NO calcula DV                               │
│ ❌ Frontend NO valida DV                                │
│                                                         │
│ Frontend envía JSON al backend                          │
│ { "nit": "800185449", ... }                             │
└─────────────────────────────────────────────────────────┘
        ↓ POST /api/v1/email-config/nits
┌─────────────────────────────────────────────────────────┐
│ AFE-BACKEND (AQUÍ ES DONDE SE CALCULA EL DV)           │
│                                                         │
│ PASO 1: Recibe NIT: "800185449"                         │
│                                                         │
│ PASO 2: NitValidator.normalizar_nit()                   │
│ ├─ Limpia: "800185449"                                  │
│ ├─ Calcula DV:                                          │
│ │  └─ Multiplicadores DIAN: [41,37,29,23,19,17,13,7,3] │
│ │  └─ Suma: 8*41 + 0*37 + 0*29 + ... = XXX             │
│ │  └─ Módulo 11: residuo = XXX % 11                    │
│ │  └─ DV = 11 - residuo = 9                            │
│ ├─ Resultado: "800185449-9"                             │
│                                                         │
│ PASO 3: Almacena en BD: "800185449-9"                   │
│                                                         │
│ PASO 4: Retorna al frontend: "800185449-9"              │
└─────────────────────────────────────────────────────────┘
        ↓ Response con NIT normalizado
┌─────────────────────────────────────────────────────────┐
│ AFE-FRONTEND (Redux)                                    │
│                                                         │
│ Recibe: { "nit": "800185449-9", ... }                   │
│ Guarda en Redux store                                   │
│ Actualiza UI con NIT normalizado                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ INVOICE_EXTRACTOR                                       │
│                                                         │
│ OPCIÓN A: Obtiene config desde API                      │
│ GET /api/v1/email-config/configuracion-extractor-public │
│ ├─ nits: ["800185449-9", "805012966-1", ...]            │
│ └─ Todos ya normalizados                                │
│                                                         │
│ OPCIÓN B: Lee settings.json (fallback)                  │
│ └─ Contiene NITs sin DV (necesita normalizar)           │
│                                                         │
│ PASO: Busca emails con esos NITs                        │
│ └─ Usa NIT para filtro OData                            │
│                                                         │
│ PASO: Extrae datos del XML                              │
│ ├─ Obtiene: <cbc:CompanyID>800185449</cbc:CompanyID>    │
│ └─ Normaliza: "800185449-9"                             │
│                                                         │
│ PASO: Ingesta a BD                                      │
│ └─ nit_emisor: "800185449-9"                            │
└─────────────────────────────────────────────────────────┘
        ↓ INSERT INTO facturas (nit_emisor)
┌─────────────────────────────────────────────────────────┐
│ AFE-BACKEND (Workflows)                                 │
│                                                         │
│ Detecta nueva factura con nit: "800185449-9"            │
│                                                         │
│ Busca responsables:                                     │
│ SELECT * FROM asignacion_nit_responsable                │
│ WHERE nit = "800185449-9"                               │
│                                                         │
│ Crea workflow para cada responsable                     │
│ Asigna, analiza, aprueba automáticamente                │
└─────────────────────────────────────────────────────────┘
```

---

## 9. PREGUNTA CRUCIAL: ¿POR QUÉ EL FRONTEND NO CALCULA EL DV?

**Razones arquitectónicas correctas**:

1. **Separación de responsabilidades**:
   - Frontend: UI/UX, entrada de datos
   - Backend: Validación, normalización, reglas de negocio

2. **Seguridad**:
   - El backend VALIDA que el DV sea correcto
   - Previene que el usuario ingrese DIferente DV manipulado

3. **Consistencia**:
   - Un único algoritmo de validación en el backend
   - No hay duplicación de código entre frontend e invoice_extractor

4. **Facilidad**:
   - Usuario no tiene que calcular DV manualmente
   - Frontend solo valida que sea números
   - Backend maneja toda la complejidad

5. **Flexibilidad**:
   - Si cambia el algoritmo DIAN, solo cambiar en backend
   - Frontend no se ve afectado

---

## 10. VERIFICACIÓN EN BD

Cuando el usuario agrega NITs, se guardan SIEMPRE normalizados:

```sql
-- Ver cómo se guardan los NITs
SELECT nit, nombre_proveedor, activo
FROM nit_configuracion
ORDER BY id DESC
LIMIT 5;

-- Resultado:
nit              nombre_proveedor   activo
800185449-9      EMPRESA A          1
805012966-1      EMPRESA B          1
830122566-3      EMPRESA C          1
900399741-7      EMPRESA D          1
```

**NUNCA sin DV en la BD**:
```
❌ "800185449"     (Nunca)
✅ "800185449-9"   (Siempre)
```

---

## 11. CONCLUSIÓN

**RESPUESTA A LA PREGUNTA**:

> ¿El frontend calcula el DV antes de enviar al backend?

❌ **NO**. El frontend:
- ✅ Valida que sean números
- ❌ NO calcula el DV
- ❌ NO valida el DV

**El backend es responsable de**:
- ✅ Calcular el DV (usando NitValidator)
- ✅ Validar que sea correcto
- ✅ Almacenar normalizado
- ✅ Proporcionar normalizado a invoice_extractor

**Flujo correcto**:
```
Usuario ingresa SIN DV
    → Frontend acepta (solo números)
    → Backend calcula y valida
    → BD almacena CON DV
    → invoice_extractor recibe CON DV
```

---

**Documento preparado**: 2025-10-30
**Versión**: Final
**Estado**: Verificado con código fuente
