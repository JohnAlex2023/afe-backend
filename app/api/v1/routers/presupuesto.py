"""
Router API para el sistema de control presupuestal empresarial
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import presupuesto as crud_presupuesto
from app.schemas.presupuesto import (
    LineaPresupuestalCreate,
    LineaPresupuestalUpdate,
    LineaPresupuestalResponse,
    EjecucionPresupuestalCreate,
    EjecucionPresupuestalResponse,
    AprobacionRequest,
    RechazoRequest,
    DashboardPresupuesto
)


router = APIRouter(prefix="/presupuesto", tags=["Presupuesto"])


# ========================================
# Endpoints para Líneas Presupuestales
# ========================================

@router.post("/lineas", response_model=LineaPresupuestalResponse, status_code=status.HTTP_201_CREATED)
def crear_linea_presupuesto(
    linea: LineaPresupuestalCreate,
    db: Session = Depends(get_db)
):
    """
    Crea una nueva línea presupuestal.

    **Presupuestos mensuales** debe ser un dict con claves: ene, feb, mar, ..., dic
    """
    # Verificar si ya existe línea con ese código y año
    linea_existente = crud_presupuesto.get_linea_by_codigo(
        db,
        codigo=linea.codigo,
        año_fiscal=linea.año_fiscal
    )
    if linea_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una línea presupuestal con código {linea.codigo} para el año {linea.año_fiscal}"
        )

    nueva_linea = crud_presupuesto.create_linea_presupuesto(
        db=db,
        codigo=linea.codigo,
        nombre=linea.nombre,
        descripcion=linea.descripcion,
        responsable_id=linea.responsable_id,
        año_fiscal=linea.año_fiscal,
        presupuestos_mensuales=linea.presupuestos_mensuales,
        centro_costo=linea.centro_costo,
        categoria=linea.categoria,
        subcategoria=linea.subcategoria,
        proveedor_preferido=linea.proveedor_preferido,
        umbral_alerta=linea.umbral_alerta or 80,
        nivel_aprobacion=linea.nivel_aprobacion or "RESPONSABLE_LINEA",
        creado_por=linea.creado_por
    )

    return nueva_linea


@router.get("/lineas", response_model=List[LineaPresupuestalResponse])
def listar_lineas_presupuesto(
    skip: int = 0,
    limit: int = 100,
    año_fiscal: Optional[int] = None,
    responsable_id: Optional[int] = None,
    estado: Optional[str] = None,
    categoria: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista todas las líneas presupuestales con filtros opcionales.
    """
    lineas = crud_presupuesto.list_lineas_presupuesto(
        db=db,
        skip=skip,
        limit=limit,
        año_fiscal=año_fiscal,
        responsable_id=responsable_id,
        estado=estado,
        categoria=categoria
    )
    return lineas


@router.get("/lineas/{linea_id}", response_model=LineaPresupuestalResponse)
def obtener_linea_presupuesto(
    linea_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene una línea presupuestal específica por ID.
    """
    linea = crud_presupuesto.get_linea_presupuesto(db, linea_id)
    if not linea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Línea presupuestal {linea_id} no encontrada"
        )
    return linea


@router.patch("/lineas/{linea_id}", response_model=LineaPresupuestalResponse)
def actualizar_linea_presupuesto(
    linea_id: int,
    linea_update: LineaPresupuestalUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza campos de una línea presupuestal.
    """
    # Preparar campos para actualización
    campos = linea_update.model_dump(exclude_unset=True, exclude={"actualizado_por"})

    linea_actualizada = crud_presupuesto.update_linea_presupuesto(
        db=db,
        linea_id=linea_id,
        actualizado_por=linea_update.actualizado_por,
        **campos
    )

    if not linea_actualizada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Línea presupuestal {linea_id} no encontrada"
        )

    return linea_actualizada


@router.post("/lineas/{linea_id}/aprobar", response_model=LineaPresupuestalResponse)
def aprobar_linea_presupuesto(
    linea_id: int,
    aprobacion: AprobacionRequest,
    db: Session = Depends(get_db)
):
    """
    Aprueba una línea presupuestal.
    """
    linea = crud_presupuesto.aprobar_linea_presupuesto(
        db=db,
        linea_id=linea_id,
        aprobador=aprobacion.aprobador,
        observaciones=aprobacion.observaciones
    )

    if not linea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Línea presupuestal {linea_id} no encontrada"
        )

    return linea


@router.post("/lineas/{linea_id}/activar", response_model=LineaPresupuestalResponse)
def activar_linea_presupuesto(
    linea_id: int,
    db: Session = Depends(get_db)
):
    """
    Activa una línea presupuestal aprobada para permitir ejecución.
    """
    linea = crud_presupuesto.activar_linea_presupuesto(db, linea_id)

    if not linea:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede activar la línea {linea_id}. Debe estar en estado APROBADO."
        )

    return linea


@router.get("/lineas/{linea_id}/ejecucion-mensual")
def obtener_ejecucion_mensual(
    linea_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna la comparación presupuesto vs ejecución mes a mes.
    """
    resultado = crud_presupuesto.get_ejecucion_mensual(db, linea_id)

    if not resultado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Línea presupuestal {linea_id} no encontrada"
        )

    return {
        "linea_presupuesto_id": linea_id,
        "ejecucion_mensual": resultado
    }


# ========================================
# Endpoints para Ejecuciones Presupuestales
# ========================================

@router.post("/ejecuciones", response_model=EjecucionPresupuestalResponse, status_code=status.HTTP_201_CREATED)
def crear_ejecucion_presupuestal(
    ejecucion: EjecucionPresupuestalCreate,
    db: Session = Depends(get_db)
):
    """
    Crea una nueva ejecución presupuestal vinculando una factura con una línea de presupuesto.

    **Automáticamente calcula desviaciones y determina niveles de aprobación requeridos.**
    """
    nueva_ejecucion = crud_presupuesto.create_ejecucion_presupuestal(
        db=db,
        linea_presupuesto_id=ejecucion.linea_presupuesto_id,
        factura_id=ejecucion.factura_id,
        monto_ejecutado=ejecucion.monto_ejecutado,
        periodo_ejecucion=ejecucion.periodo_ejecucion,
        descripcion=ejecucion.descripcion,
        vinculacion_automatica=ejecucion.vinculacion_automatica or False,
        confianza_vinculacion=ejecucion.confianza_vinculacion,
        criterios_matching=ejecucion.criterios_matching,
        creado_por=ejecucion.creado_por
    )

    if not nueva_ejecucion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede crear la ejecución. Verifique que la línea esté ACTIVA y la factura exista."
        )

    return nueva_ejecucion


@router.get("/ejecuciones", response_model=List[EjecucionPresupuestalResponse])
def listar_ejecuciones_presupuestales(
    skip: int = 0,
    limit: int = 100,
    linea_presupuesto_id: Optional[int] = None,
    factura_id: Optional[int] = None,
    año_ejecucion: Optional[int] = None,
    mes_ejecucion: Optional[int] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista todas las ejecuciones presupuestales con filtros opcionales.
    """
    ejecuciones = crud_presupuesto.list_ejecuciones_presupuestales(
        db=db,
        skip=skip,
        limit=limit,
        linea_presupuesto_id=linea_presupuesto_id,
        factura_id=factura_id,
        año_ejecucion=año_ejecucion,
        mes_ejecucion=mes_ejecucion,
        estado=estado
    )
    return ejecuciones


@router.get("/ejecuciones/{ejecucion_id}", response_model=EjecucionPresupuestalResponse)
def obtener_ejecucion_presupuestal(
    ejecucion_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene una ejecución presupuestal específica por ID.
    """
    ejecucion = crud_presupuesto.get_ejecucion_presupuestal(db, ejecucion_id)
    if not ejecucion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ejecución presupuestal {ejecucion_id} no encontrada"
        )
    return ejecucion


@router.post("/ejecuciones/{ejecucion_id}/aprobar/nivel1", response_model=EjecucionPresupuestalResponse)
def aprobar_ejecucion_nivel1(
    ejecucion_id: int,
    aprobacion: AprobacionRequest,
    db: Session = Depends(get_db)
):
    """
    Aprueba una ejecución presupuestal en Nivel 1 (Responsable de Línea).
    """
    ejecucion = crud_presupuesto.aprobar_ejecucion_nivel1(
        db=db,
        ejecucion_id=ejecucion_id,
        aprobador=aprobacion.aprobador,
        observaciones=aprobacion.observaciones
    )

    if not ejecucion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ejecución presupuestal {ejecucion_id} no encontrada"
        )

    return ejecucion


@router.post("/ejecuciones/{ejecucion_id}/aprobar/nivel2", response_model=EjecucionPresupuestalResponse)
def aprobar_ejecucion_nivel2(
    ejecucion_id: int,
    aprobacion: AprobacionRequest,
    db: Session = Depends(get_db)
):
    """
    Aprueba una ejecución presupuestal en Nivel 2 (Jefe de Área).
    Requiere aprobación previa de Nivel 1.
    """
    ejecucion = crud_presupuesto.aprobar_ejecucion_nivel2(
        db=db,
        ejecucion_id=ejecucion_id,
        aprobador=aprobacion.aprobador,
        observaciones=aprobacion.observaciones
    )

    if not ejecucion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede aprobar en Nivel 2. Verifique que exista aprobación de Nivel 1."
        )

    return ejecucion


@router.post("/ejecuciones/{ejecucion_id}/aprobar/nivel3", response_model=EjecucionPresupuestalResponse)
def aprobar_ejecucion_nivel3(
    ejecucion_id: int,
    aprobacion: AprobacionRequest,
    db: Session = Depends(get_db)
):
    """
    Aprueba una ejecución presupuestal en Nivel 3 (CFO/Gerencia).
    Requiere aprobación previa de Nivel 1 y Nivel 2.
    """
    ejecucion = crud_presupuesto.aprobar_ejecucion_nivel3(
        db=db,
        ejecucion_id=ejecucion_id,
        aprobador=aprobacion.aprobador,
        observaciones=aprobacion.observaciones
    )

    if not ejecucion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede aprobar en Nivel 3. Verifique que existan aprobaciones de Nivel 1 y 2."
        )

    return ejecucion


@router.post("/ejecuciones/{ejecucion_id}/rechazar", response_model=EjecucionPresupuestalResponse)
def rechazar_ejecucion(
    ejecucion_id: int,
    rechazo: RechazoRequest,
    db: Session = Depends(get_db)
):
    """
    Rechaza una ejecución presupuestal.
    """
    ejecucion = crud_presupuesto.rechazar_ejecucion(
        db=db,
        ejecucion_id=ejecucion_id,
        rechazado_por=rechazo.rechazado_por,
        motivo_rechazo=rechazo.motivo_rechazo
    )

    if not ejecucion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ejecución presupuestal {ejecucion_id} no encontrada"
        )

    return ejecucion


# ========================================
# Endpoints de Dashboard y Reportes
# ========================================

@router.get("/dashboard/{año_fiscal}", response_model=DashboardPresupuesto)
def obtener_dashboard_presupuesto(
    año_fiscal: int,
    responsable_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Dashboard ejecutivo del presupuesto con métricas clave:
    - Total presupuestado vs ejecutado
    - Porcentaje de ejecución global
    - Líneas por estado
    - Líneas en riesgo (sobre umbral de alerta)
    """
    dashboard = crud_presupuesto.get_dashboard_presupuesto(
        db=db,
        año_fiscal=año_fiscal,
        responsable_id=responsable_id
    )
    return dashboard


@router.post("/lineas/{linea_id}/recalcular", response_model=LineaPresupuestalResponse)
def recalcular_ejecucion_linea(
    linea_id: int,
    db: Session = Depends(get_db)
):
    """
    Recalcula el ejecutado acumulado de una línea sumando todas sus ejecuciones aprobadas.
    Útil para sincronizar después de correcciones manuales.
    """
    linea = crud_presupuesto.recalcular_ejecucion_linea(db, linea_id)

    if not linea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Línea presupuestal {linea_id} no encontrada"
        )

    return linea


# ========================================
# Endpoints de Vinculación Automática
# ========================================

@router.post("/vincular/factura/{factura_id}")
def vincular_factura_automatica(
    factura_id: int,
    año_fiscal: Optional[int] = None,
    umbral_confianza: int = 80,
    db: Session = Depends(get_db)
):
    """
    Vincula automáticamente una factura con una línea presupuestal.

    **Score mínimo recomendado: 80%**

    Criterios de matching:
    - Proveedor (35 puntos)
    - Monto (25 puntos)
    - Categoría (20 puntos)
    - Período (10 puntos)
    - Descripción (10 puntos)
    """
    from app.services.auto_vinculacion import AutoVinculador

    vinculador = AutoVinculador(db)
    resultado = vinculador.vincular_factura(
        factura_id=factura_id,
        año_fiscal=año_fiscal,
        umbral_confianza=umbral_confianza
    )

    if not resultado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Factura {factura_id} no encontrada"
        )

    return resultado


@router.post("/vincular/lote/{año_fiscal}")
def vincular_facturas_pendientes(
    año_fiscal: int,
    umbral_confianza: int = 80,
    limite: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Vincula automáticamente todas las facturas pendientes de un año fiscal.

    **Recomendado ejecutar con umbral >= 80% para alta precisión.**

    Args:
        año_fiscal: Año a procesar
        umbral_confianza: Score mínimo (70-100)
        limite: Máximo de facturas a procesar (None = todas)

    Returns:
        Reporte detallado con estadísticas de vinculación
    """
    from app.services.auto_vinculacion import AutoVinculador

    vinculador = AutoVinculador(db)
    resultado = vinculador.vincular_facturas_pendientes(
        año_fiscal=año_fiscal,
        umbral_confianza=umbral_confianza,
        limite=limite
    )

    return resultado


@router.get("/vincular/sugerencias/{factura_id}")
def obtener_sugerencias_vinculacion(
    factura_id: int,
    año_fiscal: Optional[int] = None,
    top_n: int = 5,
    db: Session = Depends(get_db)
):
    """
    Obtiene sugerencias de líneas presupuestales para una factura sin vincular automáticamente.

    Útil para revisión manual antes de vincular.
    """
    from app.services.auto_vinculacion import AutoVinculador

    vinculador = AutoVinculador(db)
    sugerencias = vinculador.sugerir_vinculacion(
        factura_id=factura_id,
        año_fiscal=año_fiscal,
        top_n=top_n
    )

    if not sugerencias:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron sugerencias para la factura {factura_id}"
        )

    return {
        "factura_id": factura_id,
        "total_sugerencias": len(sugerencias),
        "sugerencias": sugerencias
    }


# ========================================
# Endpoints de Importación Excel
# ========================================

@router.post("/importar/excel")
def importar_presupuesto_excel(
    file_path: str,
    año_fiscal: int,
    responsable_id: int,
    categoria: str = "TI",
    creado_por: str = "ADMIN",
    hoja: str | int = 0,
    fila_inicio: int = 0,
    db: Session = Depends(get_db)
):
    """
    Importa líneas presupuestales desde un archivo Excel/CSV.

    **Estructura esperada del Excel:**
    - Columna "ID": Código de la línea
    - Columna "Nombre cuenta": Nombre
    - Columnas mensuales: Ene-25, Feb-25, ..., Dic-25

    Args:
        file_path: Ruta completa al archivo
        año_fiscal: Año del presupuesto
        responsable_id: ID del responsable
        categoria: Categoría (TI, Operaciones, etc.)
        creado_por: Usuario que importa
        hoja: Nombre o índice de la hoja Excel
        fila_inicio: Fila donde empiezan los datos
    """
    from app.services.excel_to_presupuesto import ExcelPresupuestoImporter

    importer = ExcelPresupuestoImporter(db)
    resultado = importer.importar_desde_excel(
        file_path=file_path,
        año_fiscal=año_fiscal,
        responsable_id=responsable_id,
        categoria=categoria,
        creado_por=creado_por,
        hoja=hoja,
        fila_inicio=fila_inicio
    )

    if not resultado.get("exito"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=resultado.get("error", "Error al importar archivo")
        )

    return resultado


@router.get("/importar/plantilla")
def generar_plantilla_importacion(
    año_fiscal: int,
    output_path: str = "plantilla_presupuesto.xlsx",
    incluir_ejemplo: bool = True,
    db: Session = Depends(get_db)
):
    """
    Genera una plantilla Excel para importación de presupuesto.

    Args:
        año_fiscal: Año fiscal de la plantilla
        output_path: Ruta donde guardar (xlsx o csv)
        incluir_ejemplo: Si incluye fila de ejemplo
    """
    from app.services.excel_to_presupuesto import ExcelPresupuestoImporter

    importer = ExcelPresupuestoImporter(db)
    resultado = importer.generar_plantilla_excel(
        output_path=output_path,
        año_fiscal=año_fiscal,
        incluir_ejemplo=incluir_ejemplo
    )

    return resultado
