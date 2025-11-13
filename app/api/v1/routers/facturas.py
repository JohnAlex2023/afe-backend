# app/api/v1/routers/facturas.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.schemas.factura import FacturaCreate, FacturaRead, AprobacionRequest, RechazoRequest
from app.schemas.common import (
    ErrorResponse,
    PaginatedResponse,
    PaginationMetadata,
    CursorPaginatedResponse,
    CursorPaginationMetadata
)
from app.services.invoice_service import process_and_persist_invoice
from app.core.security import get_current_responsable, require_role
from app.crud.factura import (
    list_facturas,
    list_facturas_cursor,
    list_all_facturas_for_dashboard,
    count_facturas,
    get_factura,
    find_by_cufe,
    get_factura_by_numero,
    get_facturas_resumen_por_mes,
    get_facturas_resumen_por_mes_detallado,
    get_facturas_por_periodo,
    count_facturas_por_periodo,
    get_estadisticas_periodo,
    get_años_disponibles,
    get_jerarquia_facturas,
)
from app.utils.logger import logger
from app.utils.cursor_pagination import decode_cursor, build_cursor_from_factura
import math


router = APIRouter(tags=["Facturas"])


#  ENDPOINT PRINCIPAL PARA GRANDES VOLÚMENES 
# -----------------------------------------------------
# Listar facturas con CURSOR PAGINATION (Scroll Infinito)
# -----------------------------------------------------
@router.get(
    "/cursor",
    response_model=CursorPaginatedResponse[FacturaRead],
    summary="Listar facturas con cursor (scroll infinito)",
    description="Endpoint optimizado para grandes volúmenes (10k+ facturas). Usa cursor-based pagination para performance constante O(1)."
)
def list_with_cursor(
    limit: int = 500,
    cursor: Optional[str] = None,
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
    solo_asignadas: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    **Endpoint empresarial para scroll infinito con performance constante.**

    Ventajas sobre paginación offset:
    - Performance constante O(1) sin importar el tamaño del dataset
    - No hay "deep pagination problem" (página 10,000 es instantánea)
    -  Ideal para scroll infinito en frontend
    -  Usado por: Stripe, Twitter, GitHub, Facebook

    **Cómo usar:**

    1. Primera carga (sin cursor):
    ```
    GET /facturas/cursor?limit=500
    ```

    2. Siguientes páginas (usar next_cursor de respuesta anterior):
    ```
    GET /facturas/cursor?limit=500&cursor=MjAyNS0xMC0wOFQxMDowMDowMHwxMjM0NQ==
    ```

    **Respuesta:**
    ```json
    {
        "data": [...500 facturas...],
        "cursor": {
            "has_more": true,
            "next_cursor": "MjAyNS0xMC0wOFQxMDowMDowMHwxMjM0NQ==",
            "prev_cursor": null,
            "count": 500
        }
    }
    ```

    **Frontend (ejemplo React):**
    ```javascript
    const [facturas, setFacturas] = useState([]);
    const [nextCursor, setNextCursor] = useState(null);

    const loadMore = async () => {
        const url = nextCursor
            ? `/facturas/cursor?cursor=${nextCursor}&limit=500`
            : `/facturas/cursor?limit=500`;

        const res = await fetch(url);
        const data = await res.json();

        setFacturas([...facturas, ...data.data]);
        setNextCursor(data.cursor.next_cursor);
    };
    ```
    """
    # Validar límite
    if limit < 1 or limit > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'limit' debe estar entre 1 y 2000"
        )

    # Determinar permisos
    responsable_id = None
    if hasattr(current_user, 'role') and current_user.role.nombre == 'responsable':
        responsable_id = current_user.id
        logger.info(
            f"Responsable {current_user.usuario} (ID: {current_user.id}) usando cursor pagination"
        )
    elif solo_asignadas:
        responsable_id = current_user.id
        logger.info(f"Admin {current_user.usuario} usando cursor pagination (solo asignadas)")
    else:
        logger.info(f"Admin {current_user.usuario} usando cursor pagination (todas)")

    # Decodificar cursor si existe
    cursor_timestamp = None
    cursor_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        if not decoded:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cursor inválido"
            )
        cursor_timestamp, cursor_id = decoded

    # Obtener facturas con cursor
    facturas, has_more = list_facturas_cursor(
        db=db,
        limit=limit,
        cursor_timestamp=cursor_timestamp,
        cursor_id=cursor_id,
        direction="next",
        nit=nit,
        numero_factura=numero_factura,
        responsable_id=responsable_id
    )

    # Construir cursores para siguiente/anterior
    next_cursor = None
    prev_cursor = None

    if facturas:
        if has_more:
            # Cursor para siguiente página (última factura de la lista actual)
            last_factura = facturas[-1]
            next_cursor = build_cursor_from_factura(last_factura)

        if cursor:  # Si venimos de una página anterior
            # Cursor para página anterior (primera factura de la lista actual)
            first_factura = facturas[0]
            prev_cursor = build_cursor_from_factura(first_factura)

    # Construir respuesta
    cursor_metadata = CursorPaginationMetadata(
        has_more=has_more,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
        count=len(facturas)
    )

    return CursorPaginatedResponse(
        data=facturas,
        cursor=cursor_metadata
    )


#  ENDPOINT COMPLETO PARA DASHBOARD ADMINISTRATIVO 
# -----------------------------------------------------
# Obtener TODAS las facturas sin límites (Dashboard completo)
# -----------------------------------------------------
@router.get(
    "/all",
    response_model=List[FacturaRead],
    summary="Obtener TODAS las facturas (Dashboard administrativo)",
    description="Retorna todas las facturas sin límites de paginación. Exclusivo para dashboards administrativos que requieren vista completa del sistema."
)
def list_all_for_dashboard(
    solo_asignadas: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    ** ENDPOINT EMPRESARIAL PARA DASHBOARD COMPLETO**

    Retorna TODAS las facturas del sistema sin límites de paginación.
    Diseñado específicamente para dashboards administrativos que necesitan
    vista completa de todas las operaciones.

    **Casos de uso:**
    -  Dashboards administrativos con vista completa
    -  Análisis de tendencias sobre todo el dataset
    -  Reportes ejecutivos que requieren datos completos
    -  Vistas gerenciales sin restricciones de paginación

    **Control de acceso:**
    - Admin sin `solo_asignadas`: Ve TODAS las facturas del sistema
    - Admin con `solo_asignadas=true`: Ve solo sus facturas asignadas
    - Responsable: Automáticamente ve solo sus proveedores asignados

    **Performance:**
    - Usa índice `idx_facturas_orden_cronologico` para queries optimizadas
    -  Sin OFFSET (evita deep pagination problem)
    -  Lazy loading de relaciones para minimizar memoria
    -  Para datasets >50k facturas, considerar usar `/facturas/cursor` con scroll infinito

    **Orden de resultados:**
    Cronológico descendente: Año ↓ → Mes ↓ → Fecha ↓ (más recientes primero)

    **Ejemplo de respuesta:**
    ```json
    [
        {
            "id": 1,
            "numero_factura": "FACT-001",
            "cufe": "abc123...",
            "fecha_emision": "2025-10-08",
            "total": 15000.00,
            "estado": "aprobada",
            "proveedor": {...},
            "cliente": {...}
        },
        ...
    ]
    ```

    **Recomendaciones de uso:**
    - Use este endpoint cuando necesite vista completa sin scroll/paginación
    - Para UIs con scroll infinito, prefiera `/facturas/cursor`
    - Para reportes paginados, use `/facturas/` con parámetros page/per_page
    """
    # Determinar permisos según rol
    responsable_id = None

    if hasattr(current_user, 'role') and current_user.role.nombre == 'responsable':
        # Responsables SIEMPRE ven solo sus proveedores asignados
        responsable_id = current_user.id
        logger.info(
            f"[DASHBOARD COMPLETO] Responsable {current_user.usuario} (ID: {current_user.id}) "
            f"cargando todas sus facturas asignadas"
        )
    elif solo_asignadas:
        # Admin solicitó solo sus facturas asignadas
        responsable_id = current_user.id
        logger.info(
            f"[DASHBOARD COMPLETO] Admin {current_user.usuario} cargando facturas asignadas"
        )
    else:
        # Admin cargando TODAS las facturas del sistema
        logger.info(
            f"[DASHBOARD COMPLETO] Admin {current_user.usuario} cargando TODAS las facturas del sistema"
        )

    # Obtener TODAS las facturas (sin límites)
    facturas = list_all_facturas_for_dashboard(
        db=db,
        responsable_id=responsable_id
    )

    logger.info(
        f"[DASHBOARD COMPLETO] Retornando {len(facturas)} facturas a {current_user.usuario}"
    )

    return facturas


# -----------------------------------------------------
# Listar todas las facturas (con paginación empresarial)
# -----------------------------------------------------
@router.get(
    "/",
    response_model=PaginatedResponse[FacturaRead],
    summary="Listar facturas con paginación",
    description="Obtiene facturas con metadata de paginación empresarial. Admin puede ver todas o solo asignadas, Responsable solo sus proveedores."
)
def list_all(
    page: int = 1,
    per_page: int = 500,
    nit: Optional[str] = None,
    numero_factura: Optional[str] = None,
    solo_asignadas: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Lista facturas con control de acceso basado en roles y paginación empresarial:
    - Admin: Ve TODAS las facturas (o solo asignadas si solo_asignadas=true)
    - Responsable: Solo ve facturas de proveedores (NITs) que tiene asignados

    **Parámetros de paginación:**
    - page: Página actual (base 1, default: 1)
    - per_page: Registros por página (default: 500, máximo: 2000)

    **Respuesta:**
    ```json
    {
        "data": [...facturas...],
        "pagination": {
            "total": 5420,
            "page": 1,
            "per_page": 500,
            "total_pages": 11,
            "has_next": true,
            "has_prev": false
        }
    }
    ```
    """
    # Validar parámetros de paginación
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'page' debe ser mayor o igual a 1"
        )

    if per_page < 1 or per_page > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'per_page' debe estar entre 1 y 2000"
        )

    # Determinar si se debe filtrar por responsable
    responsable_id = None
    if hasattr(current_user, 'role') and current_user.role.nombre == 'responsable':
        # Si es responsable, SIEMPRE filtrar solo sus proveedores asignados
        responsable_id = current_user.id
        logger.info(
            f"Responsable {current_user.usuario} (ID: {current_user.id}) accediendo a sus facturas asignadas"
        )
    elif solo_asignadas:
        # Si es admin y solicita solo asignadas, filtrar por sus proveedores
        responsable_id = current_user.id
        logger.info(f"Admin {current_user.usuario} viendo solo facturas asignadas")
    else:
        logger.info(f"Admin {current_user.usuario} viendo todas las facturas")

    # Obtener total de facturas
    total = count_facturas(
        db,
        nit=nit,
        numero_factura=numero_factura,
        responsable_id=responsable_id
    )

    # Calcular skip
    skip = (page - 1) * per_page

    # Obtener facturas paginadas
    facturas = list_facturas(
        db,
        skip=skip,
        limit=per_page,
        nit=nit,
        numero_factura=numero_factura,
        responsable_id=responsable_id
    )

    # Calcular metadata de paginación
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    pagination = PaginationMetadata(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

    return PaginatedResponse(
        data=facturas,
        pagination=pagination
    )


# -----------------------------------------------------
# Crear o actualizar factura
# -----------------------------------------------------
@router.post(
    "/",
    response_model=FacturaRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
    summary="Crear o actualizar factura",
    description="Procesa una nueva factura. Si ya existe, devuelve un error de conflicto."
)
def create_invoice(
    payload: FacturaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    result, action = process_and_persist_invoice(
        db, payload, created_by=current_user.usuario
    )

    if action == "conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto con factura existente"
        )

    f = get_factura(db, result["id"])
    logger.info(
        "Factura procesada",
        extra={"id": f.id, "usuario": current_user.usuario, "action": action}
    )
    return f


# -----------------------------------------------------
# Obtener factura por ID
# -----------------------------------------------------
@router.get(
    "/{factura_id}",
    response_model=FacturaRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener factura por ID",
    description="Devuelve los datos de una factura específica por ID."
)
def get_one(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    f = get_factura(db, factura_id)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )
    return f


# -----------------------------------------------------
# Obtener facturas por NIT (con paginación)
# -----------------------------------------------------
@router.get(
    "/nit/{nit}",
    response_model=PaginatedResponse[FacturaRead],
    summary="Listar facturas por NIT",
    description="Obtiene todas las facturas asociadas a un proveedor por NIT con paginación."
)
def get_by_nit(
    nit: str,
    page: int = 1,
    per_page: int = 500,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Obtiene facturas de un proveedor específico con paginación empresarial.
    """
    # Validar parámetros
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'page' debe ser mayor o igual a 1"
        )

    if per_page < 1 or per_page > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'per_page' debe estar entre 1 y 2000"
        )

    # Obtener total
    total = count_facturas(db, nit=nit)

    # Calcular skip
    skip = (page - 1) * per_page

    # Obtener facturas
    facturas = list_facturas(db, skip=skip, limit=per_page, nit=nit)

    # Metadata
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    pagination = PaginationMetadata(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

    return PaginatedResponse(
        data=facturas,
        pagination=pagination
    )


# -----------------------------------------------------
# Obtener factura por CUFE
# -----------------------------------------------------
@router.get(
    "/cufe/{cufe}",
    response_model=FacturaRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener factura por CUFE",
    description="Devuelve una factura única usando el CUFE."
)
def get_by_cufe(
    cufe: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    f = find_by_cufe(db, cufe)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )
    return f


# -----------------------------------------------------
# Obtener factura por número de factura
# -----------------------------------------------------
@router.get(
    "/numero/{numero_factura}",
    response_model=FacturaRead,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener factura por número de factura",
    description="Devuelve una factura única usando el número de factura."
)
def get_by_numero(
    numero_factura: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    f = get_factura_by_numero(db, numero_factura)
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )
    return f


# -----------------------------------------------------
# Aprobar factura
# -----------------------------------------------------
@router.post(
    "/{factura_id}/aprobar",
    response_model=FacturaRead,
    summary="Aprobar factura",
    description="Aprueba una factura cambiando su estado a 'aprobado'"
)
def aprobar_factura(
    factura_id: int,
    request: AprobacionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    """
    Aprueba una factura y registra quién la aprobó.

    **IMPORTANTE:** También actualiza el workflow asociado para mantener sincronización.

    Parámetros esperados en payload:
    - aprobado_por: Usuario que aprueba
    - observaciones (opcional): Comentarios adicionales
    """
    from app.models.factura import Factura, EstadoFactura
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura
    from app.services.workflow_automatico import WorkflowAutomaticoService
    from datetime import datetime

    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )

    # Buscar workflow asociado
    workflow = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.factura_id == factura_id
    ).first()

    if workflow:
        # Si existe workflow, usar el servicio enterprise para mantener sincronización
        servicio = WorkflowAutomaticoService(db)
        # Usar el nombre completo del usuario, no el username
        aprobado_por = request.aprobado_por or (current_user.nombre if hasattr(current_user, 'nombre') else current_user.usuario)
        resultado = servicio.aprobar_manual(
            workflow_id=workflow.id,
            aprobado_por=aprobado_por,
            observaciones=request.observaciones
        )

        if resultado.get("error"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["error"]
            )

        # Refrescar factura para obtener datos actualizados
        db.refresh(factura)
    else:
        # Si no existe workflow (facturas antiguas), actualizar solo la factura
        # NOTA: Estos campos legacy serán eliminados en Fase 2.4
        # TODO: Migrar a crear workflow en lugar de actualizar campos directos
        factura.estado = EstadoFactura.aprobada
        # Usar el nombre completo del usuario, no el username
        factura.aprobado_por = request.aprobado_por or (current_user.nombre if hasattr(current_user, 'nombre') else current_user.usuario)
        factura.fecha_aprobacion = datetime.now()
        if request.observaciones:
            factura.observaciones = request.observaciones

        db.commit()
        db.refresh(factura)

    logger.info(
        f"Factura {factura.numero_factura} aprobada por {current_user.usuario}",
        extra={"factura_id": factura_id, "usuario": current_user.usuario, "con_workflow": workflow is not None}
    )

    # ENTERPRISE: Enviar notificación a TODOS los responsables del NIT
    try:
        from app.services.email_notifications import enviar_notificacion_factura_aprobada
        from app.crud.factura import obtener_responsables_de_nit

        # Obtener TODOS los responsables del NIT (soporte para múltiples responsables)
        responsables = []

        if factura.proveedor and factura.proveedor.nit:
            responsables = obtener_responsables_de_nit(db, factura.proveedor.nit)
            logger.info(f"Encontrados {len(responsables)} responsables para NIT {factura.proveedor.nit}")

        # Enviar notificación a cada responsable
        if responsables:
            monto_formateado = f"${factura.total_calculado:,.2f} COP" if factura.total_calculado else "N/A"
            aprobado_por_nombre = current_user.nombre if hasattr(current_user, 'nombre') else current_user.usuario

            for responsable in responsables:
                if responsable.email:
                    try:
                        resultado = enviar_notificacion_factura_aprobada(
                            email_responsable=responsable.email,
                            nombre_responsable=responsable.nombre or responsable.usuario,
                            numero_factura=factura.numero_factura or f"ID-{factura.id}",
                            nombre_proveedor=factura.proveedor.razon_social if factura.proveedor else "N/A",
                            nit_proveedor=factura.proveedor.nit if factura.proveedor else "N/A",
                            monto_factura=monto_formateado,
                            aprobado_por=aprobado_por_nombre,
                            fecha_aprobacion=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )

                        if resultado.get('success'):
                            logger.info(f"Notificacion enviada a {responsable.nombre} ({responsable.email})")
                        else:
                            logger.warning(f"Fallo notificacion a {responsable.email}: {resultado.get('error')}")
                    except Exception as e_responsable:
                        logger.error(f"Error enviando a {responsable.email}: {str(e_responsable)}")
        else:
            logger.warning(f"No se encontraron responsables para factura {factura.numero_factura}")

    except Exception as e:
        logger.error(f"Error en sistema de notificaciones: {str(e)}", exc_info=True)
        # No fallar la aprobación si falla el envío del email

    return factura


# -----------------------------------------------------
# Rechazar factura
# -----------------------------------------------------
@router.post(
    "/{factura_id}/rechazar",
    response_model=FacturaRead,
    summary="Rechazar factura",
    description="Rechaza una factura cambiando su estado a 'rechazado'"
)
def rechazar_factura(
    factura_id: int,
    request: RechazoRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "responsable")),
):
    """
    Rechaza una factura y registra el motivo.

    **IMPORTANTE:** También actualiza el workflow asociado para mantener sincronización.

    Parámetros esperados en payload:
    - rechazado_por: Usuario que rechaza
    - motivo: Razón del rechazo (requerido)
    - detalle (opcional): Detalle adicional del rechazo
    """
    from app.models.factura import Factura, EstadoFactura
    from app.models.workflow_aprobacion import WorkflowAprobacionFactura
    from app.services.workflow_automatico import WorkflowAutomaticoService
    from datetime import datetime

    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Factura no encontrada"
        )

    # Buscar workflow asociado
    workflow = db.query(WorkflowAprobacionFactura).filter(
        WorkflowAprobacionFactura.factura_id == factura_id
    ).first()

    if workflow:
        # Si existe workflow, usar el servicio enterprise para mantener sincronización
        servicio = WorkflowAutomaticoService(db)
        # Usar el nombre completo del usuario, no el username
        rechazado_por = request.rechazado_por or (current_user.nombre if hasattr(current_user, 'nombre') else current_user.usuario)
        resultado = servicio.rechazar(
            workflow_id=workflow.id,
            rechazado_por=rechazado_por,
            motivo=request.motivo,
            detalle=request.detalle
        )

        if resultado.get("error"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["error"]
            )

        # Refrescar factura para obtener datos actualizados
        db.refresh(factura)
    else:
        # Si no existe workflow (facturas antiguas), actualizar solo la factura
        # NOTA: Estos campos legacy serán eliminados en Fase 2.4
        # TODO: Migrar a crear workflow en lugar de actualizar campos directos
        factura.estado = EstadoFactura.rechazada
        # Usar el nombre completo del usuario, no el username
        factura.rechazado_por = request.rechazado_por or (current_user.nombre if hasattr(current_user, 'nombre') else current_user.usuario)
        factura.fecha_rechazo = datetime.now()
        factura.motivo_rechazo = request.motivo

        db.commit()
        db.refresh(factura)

    logger.info(
        f"Factura {factura.numero_factura} rechazada por {current_user.usuario}. Motivo: {request.motivo}",
        extra={"factura_id": factura_id, "usuario": current_user.usuario, "con_workflow": workflow is not None}
    )

    # ENTERPRISE: Enviar notificación a TODOS los responsables del NIT
    try:
        from app.services.email_notifications import enviar_notificacion_factura_rechazada
        from app.crud.factura import obtener_responsables_de_nit

        # Obtener TODOS los responsables del NIT (soporte para múltiples responsables)
        responsables = []

        if factura.proveedor and factura.proveedor.nit:
            responsables = obtener_responsables_de_nit(db, factura.proveedor.nit)
            logger.info(f"Encontrados {len(responsables)} responsables para NIT {factura.proveedor.nit}")

        # Enviar notificación a cada responsable
        if responsables:
            monto_formateado = f"${factura.total_calculado:,.2f} COP" if factura.total_calculado else "N/A"
            rechazado_por_nombre = current_user.nombre if hasattr(current_user, 'nombre') else current_user.usuario

            for responsable in responsables:
                if responsable.email:
                    try:
                        resultado = enviar_notificacion_factura_rechazada(
                            email_responsable=responsable.email,
                            nombre_responsable=responsable.nombre or responsable.usuario,
                            numero_factura=factura.numero_factura or f"ID-{factura.id}",
                            nombre_proveedor=factura.proveedor.razon_social if factura.proveedor else "N/A",
                            nit_proveedor=factura.proveedor.nit if factura.proveedor else "N/A",
                            monto_factura=monto_formateado,
                            rechazado_por=rechazado_por_nombre,
                            motivo_rechazo=request.motivo,
                            fecha_rechazo=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )

                        if resultado.get('success'):
                            logger.info(f"Notificacion enviada a {responsable.nombre} ({responsable.email})")
                        else:
                            logger.warning(f"Fallo notificacion a {responsable.email}: {resultado.get('error')}")
                    except Exception as e_responsable:
                        logger.error(f"Error enviando a {responsable.email}: {str(e_responsable)}")
        else:
            logger.warning(f"No se encontraron responsables para factura {factura.numero_factura}")

    except Exception as e:
        logger.error(f"Error en sistema de notificaciones: {str(e)}", exc_info=True)
        # No fallar el rechazo si falla el envío del email

    return factura


#  ENDPOINTS PARA CLASIFICACIÓN POR PERÍODOS MENSUALES 

# -----------------------------------------------------
# Obtener resumen de facturas agrupadas por mes
# -----------------------------------------------------
@router.get(
    "/periodos/resumen",
    tags=["Reportes - Períodos Mensuales"],
    summary="Resumen de facturas por mes",
    description="Obtiene un resumen de facturas agrupadas por mes/año con totales agregados. Ideal para dashboards y reportes mensuales."
)
def get_resumen_por_mes(
    año: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Retorna facturas agrupadas por período (mes/año) con:
    - Total de facturas por mes
    - Monto total por mes
    - Subtotal e IVA por mes

    Ejemplo de respuesta:
    [
        {
            "periodo": "2025-07",
            "año": 2025,
            "mes": 7,
            "total_facturas": 6,
            "monto_total": 17126907.00,
            "subtotal_total": 14000000.00,
            "iva_total": 3126907.00
        },
        ...
    ]
    """
    return get_facturas_resumen_por_mes(
        db=db,
        año=año,
        proveedor_id=proveedor_id,
        estado=estado
    )


# =====================================================
# NUEVO: Obtener resumen DETALLADO con desglose por estado
# =====================================================
@router.get(
    "/periodos/resumen-detallado",
    tags=["Reportes - Períodos Mensuales"],
    summary="Resumen DETALLADO de facturas por mes con desglose por estado",
    description="Obtiene un resumen de facturas agrupadas por mes/año CON DESGLOSE POR ESTADO. Ideal para dashboards que necesitan visualizar distribución de estados (en_revision, aprobada, aprobada_auto, rechazada)."
)
def get_resumen_detallado_por_mes(
    año: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Retorna facturas agrupadas por período (mes/año) CON DESGLOSE DETALLADO POR ESTADO.

    Ejemplo de respuesta:
    [
        {
            "periodo": "2025-10",
            "año": 2025,
            "mes": 10,
            "total_facturas": 100,
            "monto_total": 50000000.00,
            "subtotal_total": 42000000.00,
            "iva_total": 8000000.00,
            "facturas_por_estado": {
                "en_revision": 30,
                "aprobada": 40,
                "aprobada_auto": 25,
                "rechazada": 5
            }
        },
        ...
    ]
    """
    return get_facturas_resumen_por_mes_detallado(
        db=db,
        año=año,
        proveedor_id=proveedor_id
    )


# -----------------------------------------------------
# Obtener facturas de un período específico (con paginación)
# -----------------------------------------------------
@router.get(
    "/periodos/{periodo}",
    response_model=PaginatedResponse[FacturaRead],
    tags=["Reportes - Períodos Mensuales"],
    summary="Facturas de un período específico",
    description="Obtiene todas las facturas de un mes/año específico (formato: YYYY-MM) con paginación"
)
def get_facturas_periodo(
    periodo: str,
    page: int = 1,
    per_page: int = 500,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Obtiene facturas de un período específico con paginación empresarial.

    Args:
        periodo: Formato "YYYY-MM" (ej: "2025-07" para julio 2025)
        page: Página actual (base 1, default: 1)
        per_page: Registros por página (default: 500, máximo: 2000)
        proveedor_id: Filtrar por proveedor (opcional)
        estado: Filtrar por estado (opcional)

    Returns:
        Respuesta paginada con facturas del período
    """
    # Validar formato de período
    if len(periodo) != 7 or periodo[4] != '-':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de período inválido. Use YYYY-MM (ej: 2025-07)"
        )

    # Validar parámetros de paginación
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'page' debe ser mayor o igual a 1"
        )

    if per_page < 1 or per_page > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El parámetro 'per_page' debe estar entre 1 y 2000"
        )

    # Obtener total del período
    total = count_facturas_por_periodo(
        db=db,
        periodo=periodo,
        proveedor_id=proveedor_id,
        estado=estado
    )

    # Calcular skip
    skip = (page - 1) * per_page

    # Obtener facturas del período
    facturas = get_facturas_por_periodo(
        db=db,
        periodo=periodo,
        skip=skip,
        limit=per_page,
        proveedor_id=proveedor_id,
        estado=estado
    )

    # Metadata de paginación
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    pagination = PaginationMetadata(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )

    return PaginatedResponse(
        data=facturas,
        pagination=pagination
    )


# -----------------------------------------------------
# Obtener estadísticas de un período
# -----------------------------------------------------
@router.get(
    "/periodos/{periodo}/estadisticas",
    tags=["Reportes - Períodos Mensuales"],
    summary="Estadísticas de un período",
    description="Obtiene estadísticas detalladas de un período específico incluyendo desglose por estado"
)
def get_stats_periodo(
    periodo: str,
    proveedor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Retorna estadísticas completas de un período:
    - Total de facturas
    - Monto total, subtotal, IVA
    - Promedio por factura
    - Desglose por estado (pendiente, aprobada, etc.)

    Ejemplo de respuesta:
    {
        "periodo": "2025-07",
        "total_facturas": 6,
        "monto_total": 17126907.00,
        "subtotal": 14000000.00,
        "iva": 3126907.00,
        "promedio": 2854484.50,
        "por_estado": [
            {"estado": "en_revision", "cantidad": 6, "monto": 17126907.00}
        ]
    }
    """
    # Validar formato
    if len(periodo) != 7 or periodo[4] != '-':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de período inválido. Use YYYY-MM"
        )

    return get_estadisticas_periodo(
        db=db,
        periodo=periodo,
        proveedor_id=proveedor_id
    )


# -----------------------------------------------------
# Contar facturas de un período
# -----------------------------------------------------
@router.get(
    "/periodos/{periodo}/count",
    tags=["Reportes - Períodos Mensuales"],
    summary="Contar facturas de un período",
    description="Retorna el número total de facturas en un período"
)
def count_periodo(
    periodo: str,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Cuenta facturas de un período específico.
    Útil para paginación y reportes rápidos.
    """
    if len(periodo) != 7 or periodo[4] != '-':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de período inválido. Use YYYY-MM"
        )

    count = count_facturas_por_periodo(
        db=db,
        periodo=periodo,
        proveedor_id=proveedor_id,
        estado=estado
    )

    return {"periodo": periodo, "total": count}


# -----------------------------------------------------
# Obtener años disponibles
# -----------------------------------------------------
@router.get(
    "/periodos/años/disponibles",
    tags=["Reportes - Períodos Mensuales"],
    summary="Años con facturas",
    description="Retorna lista de años que tienen facturas registradas"
)
def get_años(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Retorna años disponibles en orden descendente.
    Útil para filtros en frontend.

    Ejemplo: [2025, 2024, 2023]
    """
    años = get_años_disponibles(db)
    return {"años": años}


# -----------------------------------------------------
# Jerarquía empresarial: Año → Mes → Facturas
# -----------------------------------------------------
@router.get(
    "/periodos/jerarquia",
    tags=["Reportes - Períodos Mensuales"],
    summary="Vista jerárquica año→mes→facturas",
    description="Retorna facturas organizadas jerárquicamente por año y mes. Ideal para dashboards con drill-down."
)
def get_jerarquia(
    año: Optional[int] = None,
    mes: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    limit_por_mes: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    **Vista Jerárquica Empresarial** para organización cronológica de facturas.

    Retorna estructura anidada:
    ```json
    {
        "2025": {
            "10": {
                "total_facturas": 4,
                "monto_total": 12500.00,
                "subtotal": 10500.00,
                "iva": 2000.00,
                "facturas": [
                    {
                        "id": 123,
                        "numero_factura": "FACT-001",
                        "fecha_emision": "2025-10-15",
                        "total": 5000.00,
                        "estado": "aprobada"
                    },
                    ...
                ]
            },
            "09": {...}
        },
        "2024": {...}
    }
    ```

    **Filtros disponibles:**
    - `año`: Filtrar por año específico (ej: 2025)
    - `mes`: Filtrar por mes específico (1-12)
    - `proveedor_id`: Filtrar por proveedor
    - `estado`: Filtrar por estado
    - `limit_por_mes`: Límite de facturas por mes (default: 100)

    **Orden:** Año DESC → Mes DESC → Fecha DESC (más recientes primero)

    **Performance:** Usa índice `idx_facturas_orden_cronologico` para queries ultra-rápidas
    """
    return get_jerarquia_facturas(
        db=db,
        año=año,
        mes=mes,
        proveedor_id=proveedor_id,
        estado=estado,
        limit_por_mes=limit_por_mes
    )


#  ENDPOINT DE EXPORTACIÓN PARA REPORTES COMPLETOS 
# -----------------------------------------------------
# Exportar facturas a CSV
# -----------------------------------------------------
@router.get(
    "/export/csv",
    tags=["Exportación"],
    summary="Exportar facturas a CSV",
    description="Genera archivo CSV con todas las facturas filtradas. Ideal para reportes y análisis en Excel."
)
def export_to_csv(
    fecha_desde: Optional[datetime] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    nit: Optional[str] = None,
    estado: Optional[str] = None,
    solo_asignadas: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    **Exportación empresarial de facturas a CSV.**

    Permite descargar reportes completos sin límites de paginación.

    **Casos de uso:**
    -  Análisis en Excel/Google Sheets
    -  Reportes financieros para gerencia
    -  Auditorías contables
    -  Backup de datos

    **Recomendaciones:**
    - Use filtros de fecha para limitar el dataset
    - Para datasets >50k registros, considere exportar por períodos
    - El archivo se genera en tiempo real (puede tardar en datasets grandes)

    **Ejemplo:**
    ```
    GET /facturas/export/csv?fecha_desde=2025-01-01&fecha_hasta=2025-12-31&estado=aprobada
    ```
    """
    from app.services.export_service import export_facturas_to_csv

    # Determinar permisos
    responsable_id = None
    if hasattr(current_user, 'role') and current_user.role.nombre == 'responsable':
        responsable_id = current_user.id
        logger.info(f"Responsable {current_user.usuario} exportando facturas asignadas")
    elif solo_asignadas:
        responsable_id = current_user.id
        logger.info(f"Admin {current_user.usuario} exportando facturas asignadas")
    else:
        logger.info(f"Admin {current_user.usuario} exportando todas las facturas")

    # Generar CSV
    try:
        csv_content = export_facturas_to_csv(
            db=db,
            nit=nit,
            responsable_id=responsable_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            estado=estado
        )

        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"facturas_export_{timestamp}.csv"

        # Retornar como descarga
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )

    except Exception as e:
        logger.error(f"Error al exportar facturas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar exportación: {str(e)}"
        )


# -----------------------------------------------------
# Metadata de exportación
# -----------------------------------------------------
@router.get(
    "/export/metadata",
    tags=["Exportación"],
    summary="Obtener metadata de exportación",
    description="Retorna información sobre el dataset a exportar (total registros, rangos, etc.)"
)
def get_export_info(
    fecha_desde: Optional[datetime] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    solo_asignadas: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_responsable),
):
    """
    Obtiene información sobre el dataset a exportar antes de generar el archivo.

    Útil para:
    - Validar tamaño del dataset antes de exportar
    - Mostrar preview de lo que se va a descargar
    - Estimar tiempo de generación

    **Respuesta:**
    ```json
    {
        "total_registros": 15420,
        "fecha_desde": "2025-01-01",
        "fecha_hasta": "2025-12-31",
        "timestamp_generacion": "2025-10-08T10:30:00"
    }
    ```
    """
    from app.services.export_service import get_export_metadata

    # Determinar permisos
    responsable_id = None
    if hasattr(current_user, 'role') and current_user.role.nombre == 'responsable':
        responsable_id = current_user.id
    elif solo_asignadas:
        responsable_id = current_user.id

    # Obtener metadata
    metadata = get_export_metadata(
        db=db,
        responsable_id=responsable_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta
    )

    return metadata


# =====================================================
# MANUAL TRIGGER FOR AUTOMATION (TESTING/ADMIN ONLY)
# =====================================================
@router.post(
    "/admin/trigger-automation",
    summary="Trigger automation scheduler manually",
    description="Admin-only endpoint to manually trigger the automation scheduler for testing purposes. Processes pending facturas and creates workflows."
)
def trigger_automation_manually(
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """
    Manually triggers the automation scheduler.

    This endpoint is useful for testing workflow automation without waiting for the scheduled hourly execution.
    It executes the same logic as the background scheduler:
    1. Creates workflows for facturas that don't have them yet
    2. Processes automation decisions (approve/reject/send to review)

    Admin only.
    """
    try:
        from app.services.workflow_automatico import WorkflowAutomaticoService
        from app.services.automation.automation_service import AutomationService
        from app.models.factura import Factura
        from app.models.workflow_aprobacion import WorkflowAprobacionFactura

        logger.info(f"🚀 MANUAL AUTOMATION TRIGGER initiated by admin {current_user.usuario}")

        # PHASE 1: Get statistics BEFORE automation
        total_facturas = db.query(Factura).count()
        total_workflows_before = db.query(WorkflowAprobacionFactura).count()

        facturas_sin_workflow = db.query(Factura).filter(
            ~Factura.id.in_(
                db.query(WorkflowAprobacionFactura.factura_id)
            )
        ).all()

        facturas_sin_workflow_count = len(facturas_sin_workflow)

        logger.info(
            f" BEFORE automation: "
            f"Total facturas: {total_facturas}, "
            f"Workflows: {total_workflows_before}, "
            f"Sin workflow: {facturas_sin_workflow_count}"
        )

        # PHASE 2: Create workflows for facturas without them
        logger.info(f" [FASE 1] Creando workflows para {facturas_sin_workflow_count} facturas...")
        workflow_service = WorkflowAutomaticoService(db)

        workflows_creados = 0
        workflows_fallidos = 0

        for idx, factura in enumerate(facturas_sin_workflow[:100], 1):  # Limit to 100 per execution
            try:
                resultado = workflow_service.procesar_factura_nueva(factura.id)
                if resultado.get('exito'):
                    workflows_creados += 1
                    if idx <= 5:  # Log first 5 only
                        logger.info(f"   Workflow creado para factura {factura.id}")
                else:
                    workflows_fallidos += 1
                    if idx <= 5:
                        logger.warning(f"  ⚠️  Workflow falló para factura {factura.id}: {resultado.get('error')}")
            except Exception as e:
                workflows_fallidos += 1
                if idx <= 5:
                    logger.error(f"  ❌ Error creando workflow para factura {factura.id}: {str(e)}")

        if workflows_creados > 0:
            db.commit()

        logger.info(f" [FASE 1] Completada: {workflows_creados} creados, {workflows_fallidos} fallidos")

        # PHASE 3: Run automation decisions
        logger.info(f"⚙️  [FASE 2] Procesando automatización de facturas...")
        automation = AutomationService()
        automation_resultado = automation.procesar_facturas_pendientes(
            db=db,
            limite_facturas=100,
            modo_debug=False
        )

        logger.info(
            f" [FASE 2] Completada: "
            f"{automation_resultado['aprobadas_automaticamente']} aprobadas, "
            f"{automation_resultado['enviadas_revision']} a revisión, "
            f"{automation_resultado['errores']} errores"
        )

        # PHASE 4: Get statistics AFTER automation
        total_workflows_after = db.query(WorkflowAprobacionFactura).count()

        logger.info(f" MANUAL AUTOMATION TRIGGER completed by admin {current_user.usuario}")

        return {
            "status": "success",
            "message": "Automation scheduler executed successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "triggered_by": current_user.usuario,
            "statistics": {
                "before": {
                    "total_facturas": total_facturas,
                    "workflows": total_workflows_before,
                    "sin_workflow": facturas_sin_workflow_count
                },
                "after": {
                    "total_facturas": db.query(Factura).count(),
                    "workflows": total_workflows_after,
                    "sin_workflow": db.query(Factura).filter(
                        ~Factura.id.in_(
                            db.query(WorkflowAprobacionFactura.factura_id)
                        )
                    ).count()
                },
                "fase_1": {
                    "workflows_creados": workflows_creados,
                    "workflows_fallidos": workflows_fallidos
                },
                "fase_2": {
                    "aprobadas_automaticamente": automation_resultado['aprobadas_automaticamente'],
                    "enviadas_revision": automation_resultado['enviadas_revision'],
                    "errores": automation_resultado['errores']
                }
            }
        }

    except Exception as e:
        logger.error(
            f"❌ Error in manual automation trigger: {str(e)}",
            exc_info=True,
            extra={"admin_user": current_user.usuario}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing automation: {str(e)}"
        )
