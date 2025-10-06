"""
Servicio de Workflow Automático de Aprobación de Facturas.

Este servicio analiza facturas nuevas y:
1. Identifica el NIT del proveedor
2. Asigna automáticamente al responsable
3. Compara con la factura del mes anterior
4. Aprueba automáticamente si es idéntica
5. Envía a revisión manual si hay diferencias
6. Genera notificaciones

Integración: Se activa cuando llegan nuevas facturas desde Microsoft Graph a la tabla facturas
"""

from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.factura import Factura
from app.models.workflow_aprobacion import (
    WorkflowAprobacionFactura,
    AsignacionNitResponsable,
    NotificacionWorkflow,
    EstadoFacturaWorkflow,
    TipoAprobacion,
    TipoNotificacion
)


class WorkflowAutomaticoService:
    """
    Servicio principal de workflow automático.
    """

    def __init__(self, db: Session):
        self.db = db

    def procesar_factura_nueva(self, factura_id: int) -> Dict[str, Any]:
        """
        Punto de entrada principal: procesa una factura recién llegada.

        Args:
            factura_id: ID de la factura a procesar

        Returns:
            Dict con el resultado del procesamiento
        """
        # 1. Obtener factura
        factura = self.db.query(Factura).filter(Factura.id == factura_id).first()
        if not factura:
            return {"error": "Factura no encontrada", "factura_id": factura_id}

        # 2. Verificar si ya tiene workflow
        workflow_existente = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.factura_id == factura_id
        ).first()

        if workflow_existente:
            return {
                "mensaje": "La factura ya tiene un workflow asignado",
                "workflow_id": workflow_existente.id,
                "estado": workflow_existente.estado.value
            }

        # 3. Extraer NIT del proveedor
        nit = self._extraer_nit(factura)

        # 4. Buscar asignación de responsable
        asignacion = self._buscar_asignacion_responsable(nit)

        if not asignacion:
            return self._crear_workflow_sin_asignacion(factura, nit)

        # 5. Crear workflow inicial
        workflow = WorkflowAprobacionFactura(
            factura_id=factura.id,
            estado=EstadoFacturaWorkflow.RECIBIDA,
            nit_proveedor=nit,
            responsable_id=asignacion.responsable_id,
            area_responsable=asignacion.area,
            fecha_asignacion=datetime.now(),
            creado_en=datetime.now(),
            creado_por="SISTEMA_AUTO"
        )

        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)

        # 6. Iniciar análisis de similitud
        resultado_analisis = self._analizar_similitud_mes_anterior(factura, workflow, asignacion)

        # 7. Enviar notificaciones
        self._enviar_notificacion_inicial(workflow, factura, asignacion)

        return {
            "exito": True,
            "workflow_id": workflow.id,
            "factura_id": factura.id,
            "nit": nit,
            "responsable_id": asignacion.responsable_id,
            "area": asignacion.area,
            **resultado_analisis
        }

    def _extraer_nit(self, factura: Factura) -> Optional[str]:
        """Extrae el NIT del proveedor de la factura."""
        # Opción 1: Si el proveedor está relacionado directamente (objeto Proveedor)
        if factura.proveedor and hasattr(factura.proveedor, 'nit'):
            return factura.proveedor.nit

        # Opción 2: Si solo tenemos proveedor_id, hacer query
        if factura.proveedor_id:
            from app.models.proveedor import Proveedor
            proveedor = self.db.query(Proveedor).filter(
                Proveedor.id == factura.proveedor_id
            ).first()
            if proveedor and proveedor.nit:
                return proveedor.nit

        return None

    def _buscar_asignacion_responsable(self, nit: Optional[str]) -> Optional[AsignacionNitResponsable]:
        """Busca la asignación de responsable para un NIT."""
        if not nit:
            return None

        return self.db.query(AsignacionNitResponsable).filter(
            and_(
                AsignacionNitResponsable.nit == nit,
                AsignacionNitResponsable.activo == True
            )
        ).first()

    def _crear_workflow_sin_asignacion(self, factura: Factura, nit: Optional[str]) -> Dict[str, Any]:
        """Crea un workflow para factura sin asignación de responsable."""
        workflow = WorkflowAprobacionFactura(
            factura_id=factura.id,
            estado=EstadoFacturaWorkflow.PENDIENTE_REVISION,
            nit_proveedor=nit,
            creado_en=datetime.now(),
            creado_por="SISTEMA_AUTO",
            metadata_workflow={
                "alerta": "NIT sin asignación de responsable",
                "requiere_configuracion": True
            }
        )

        self.db.add(workflow)
        self.db.commit()

        return {
            "exito": False,
            "workflow_id": workflow.id,
            "error": "NIT sin asignación de responsable",
            "nit": nit,
            "requiere_configuracion": True
        }

    def _analizar_similitud_mes_anterior(
        self,
        factura: Factura,
        workflow: WorkflowAprobacionFactura,
        asignacion: AsignacionNitResponsable
    ) -> Dict[str, Any]:
        """
        Compara la factura con la del mes anterior del mismo proveedor.
        """
        # Cambiar estado a EN_ANALISIS
        workflow.estado = EstadoFacturaWorkflow.EN_ANALISIS
        workflow.fecha_cambio_estado = datetime.now()
        tiempo_inicio = datetime.now()

        # Buscar factura del mes anterior
        if factura.fecha_emision:
            mes_anterior = factura.fecha_emision - timedelta(days=30)

            factura_anterior = self.db.query(Factura).filter(
                and_(
                    Factura.proveedor == factura.proveedor,
                    Factura.id != factura.id,
                    Factura.fecha_emision >= mes_anterior - timedelta(days=5),
                    Factura.fecha_emision <= mes_anterior + timedelta(days=5)
                )
            ).order_by(desc(Factura.fecha_emision)).first()

            if factura_anterior:
                return self._comparar_facturas(factura, factura_anterior, workflow, asignacion, tiempo_inicio)

        # No hay factura del mes anterior
        workflow.estado = EstadoFacturaWorkflow.PENDIENTE_REVISION
        workflow.fecha_cambio_estado = datetime.now()
        workflow.tiempo_en_analisis = int((datetime.now() - tiempo_inicio).total_seconds())
        workflow.criterios_comparacion = {"sin_factura_anterior": True}

        self.db.commit()

        return {
            "requiere_revision": True,
            "motivo": "No hay factura del mes anterior para comparar",
            "estado": workflow.estado.value
        }

    def _comparar_facturas(
        self,
        factura_actual: Factura,
        factura_anterior: Factura,
        workflow: WorkflowAprobacionFactura,
        asignacion: AsignacionNitResponsable,
        tiempo_inicio: datetime
    ) -> Dict[str, Any]:
        """
        Compara dos facturas y determina si son idénticas.
        """
        diferencias = []
        criterios = {}

        # 1. Comparar proveedor (por proveedor_id)
        proveedor_igual = factura_actual.proveedor_id == factura_anterior.proveedor_id
        criterios["proveedor_igual"] = proveedor_igual
        if not proveedor_igual:
            proveedor_actual_nombre = factura_actual.proveedor.razon_social if factura_actual.proveedor else "Sin proveedor"
            proveedor_anterior_nombre = factura_anterior.proveedor.razon_social if factura_anterior.proveedor else "Sin proveedor"
            diferencias.append({
                "campo": "proveedor",
                "actual": proveedor_actual_nombre,
                "anterior": proveedor_anterior_nombre
            })

        # 2. Comparar monto
        monto_actual = factura_actual.total or Decimal("0")
        monto_anterior = factura_anterior.total or Decimal("0")

        if monto_anterior > 0:
            variacion_pct = abs((monto_actual - monto_anterior) / monto_anterior * 100)
        else:
            variacion_pct = 100 if monto_actual > 0 else 0

        umbral_variacion = asignacion.porcentaje_variacion_permitido or Decimal("5.0")
        monto_igual = variacion_pct <= umbral_variacion

        criterios["monto_igual"] = monto_igual
        criterios["variacion_porcentaje"] = float(variacion_pct)

        if not monto_igual:
            diferencias.append({
                "campo": "monto",
                "actual": float(monto_actual),
                "anterior": float(monto_anterior),
                "variacion_pct": float(variacion_pct)
            })

        # 3. Comparar concepto
        concepto_actual = factura_actual.concepto_normalizado or factura_actual.concepto_principal or ""
        concepto_anterior = factura_anterior.concepto_normalizado or factura_anterior.concepto_principal or ""
        concepto_igual = self._comparar_conceptos(concepto_actual, concepto_anterior)
        criterios["concepto_igual"] = concepto_igual

        if not concepto_igual:
            diferencias.append({
                "campo": "concepto",
                "actual": concepto_actual,
                "anterior": concepto_anterior
            })

        # 4. Calcular porcentaje de similitud global
        puntos = 0
        if proveedor_igual:
            puntos += 40
        if monto_igual:
            puntos += 40
        if concepto_igual:
            puntos += 20

        porcentaje_similitud = Decimal(str(puntos))

        # Actualizar workflow
        workflow.factura_mes_anterior_id = factura_anterior.id
        workflow.porcentaje_similitud = porcentaje_similitud
        workflow.criterios_comparacion = criterios
        workflow.diferencias_detectadas = diferencias if diferencias else None
        workflow.es_identica_mes_anterior = (porcentaje_similitud >= 95)
        workflow.tiempo_en_analisis = int((datetime.now() - tiempo_inicio).total_seconds())

        # Decidir: ¿Aprobación automática o revisión manual?
        if self._puede_aprobar_automaticamente(workflow, asignacion, factura_actual):
            return self._aprobar_automaticamente(workflow, factura_actual)
        else:
            return self._enviar_a_revision_manual(workflow, diferencias)

    def _comparar_conceptos(self, concepto1: Optional[str], concepto2: Optional[str]) -> bool:
        """Compara dos conceptos de factura."""
        if not concepto1 or not concepto2:
            return concepto1 == concepto2

        # Normalizar
        c1 = concepto1.lower().strip()
        c2 = concepto2.lower().strip()

        # Similitud exacta
        if c1 == c2:
            return True

        # Similitud por palabras clave (al menos 70% de palabras en común)
        palabras1 = set(c1.split())
        palabras2 = set(c2.split())

        if len(palabras1) == 0 or len(palabras2) == 0:
            return False

        interseccion = palabras1.intersection(palabras2)
        similitud = len(interseccion) / max(len(palabras1), len(palabras2)) * 100

        return similitud >= 70

    def _puede_aprobar_automaticamente(
        self,
        workflow: WorkflowAprobacionFactura,
        asignacion: AsignacionNitResponsable,
        factura: Factura
    ) -> bool:
        """Determina si la factura puede aprobarse automáticamente."""
        # Regla 1: Debe estar habilitada la aprobación automática
        if not asignacion.permitir_aprobacion_automatica:
            return False

        # Regla 2: No debe requerir revisión siempre
        if asignacion.requiere_revision_siempre:
            return False

        # Regla 3: Debe ser idéntica al mes anterior
        if not workflow.es_identica_mes_anterior:
            return False

        # Regla 4: Monto debe estar dentro del límite
        if asignacion.monto_maximo_auto_aprobacion:
            if factura.total and factura.total > asignacion.monto_maximo_auto_aprobacion:
                return False

        return True

    def _aprobar_automaticamente(
        self,
        workflow: WorkflowAprobacionFactura,
        factura: Factura
    ) -> Dict[str, Any]:
        """Aprueba automáticamente una factura."""
        workflow.estado = EstadoFacturaWorkflow.APROBADA_AUTO
        workflow.fecha_cambio_estado = datetime.now()
        workflow.tipo_aprobacion = TipoAprobacion.AUTOMATICA
        workflow.aprobada = True
        workflow.aprobada_por = "SISTEMA_AUTO"
        workflow.fecha_aprobacion = datetime.now()
        workflow.observaciones_aprobacion = f"Aprobación automática - {workflow.porcentaje_similitud}% similitud con mes anterior"

        self.db.commit()

        # Enviar notificación de aprobación automática
        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.FACTURA_APROBADA,
            destinatarios=[],  # Se llenará con emails del responsable y contabilidad
            asunto=f"✅ Factura Aprobada Automáticamente - {factura.numero_factura}",
            cuerpo=f"""
            La factura {factura.numero_factura} ha sido aprobada automáticamente.

            Proveedor: {factura.proveedor}
            Monto: ${factura.total:,.2f}
            Similitud con mes anterior: {workflow.porcentaje_similitud}%

            No requiere acción adicional.
            """
        )

        return {
            "aprobacion_automatica": True,
            "estado": workflow.estado.value,
            "porcentaje_similitud": float(workflow.porcentaje_similitud),
            "mensaje": "Factura aprobada automáticamente"
        }

    def _enviar_a_revision_manual(
        self,
        workflow: WorkflowAprobacionFactura,
        diferencias: List[Dict]
    ) -> Dict[str, Any]:
        """Envía la factura a revisión manual."""
        workflow.estado = EstadoFacturaWorkflow.PENDIENTE_REVISION
        workflow.fecha_cambio_estado = datetime.now()

        self.db.commit()

        # Crear notificación para el responsable
        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.PENDIENTE_REVISION,
            destinatarios=[],  # Email del responsable
            asunto=f"⚠️ Factura Pendiente de Revisión - {workflow.factura.numero_factura}",
            cuerpo=f"""
            La factura {workflow.factura.numero_factura} requiere su revisión.

            Se detectaron diferencias con respecto al mes anterior:
            {self._formatear_diferencias(diferencias)}

            Por favor, revise y apruebe o rechace la factura.
            """
        )

        return {
            "requiere_revision": True,
            "estado": workflow.estado.value,
            "diferencias": diferencias,
            "porcentaje_similitud": float(workflow.porcentaje_similitud or 0),
            "mensaje": "Factura enviada a revisión manual"
        }

    def _formatear_diferencias(self, diferencias: List[Dict]) -> str:
        """Formatea las diferencias para mostrar en notificación."""
        texto = ""
        for dif in diferencias:
            texto += f"\n- {dif['campo'].upper()}: {dif.get('actual')} (anterior: {dif.get('anterior')})"
        return texto

    def _crear_notificacion(
        self,
        workflow: WorkflowAprobacionFactura,
        tipo: TipoNotificacion,
        destinatarios: List[str],
        asunto: str,
        cuerpo: str
    ) -> NotificacionWorkflow:
        """Crea un registro de notificación."""
        notif = NotificacionWorkflow(
            workflow_id=workflow.id,
            tipo=tipo,
            destinatarios=destinatarios,
            asunto=asunto,
            cuerpo=cuerpo,
            enviada=False,
            creado_en=datetime.now()
        )

        self.db.add(notif)
        self.db.commit()

        return notif

    def _enviar_notificacion_inicial(
        self,
        workflow: WorkflowAprobacionFactura,
        factura: Factura,
        asignacion: AsignacionNitResponsable
    ):
        """Envía notificación inicial de factura recibida."""
        proveedor_nombre = factura.proveedor.razon_social if factura.proveedor else "Sin proveedor"
        monto = factura.total or 0
        fecha = factura.fecha_emision or "Sin fecha"

        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.FACTURA_RECIBIDA,
            destinatarios=[],  # Email del responsable
            asunto=f"📩 Nueva Factura Recibida - {factura.numero_factura}",
            cuerpo=f"""
            Se ha recibido una nueva factura asignada a su área.

            Proveedor: {proveedor_nombre}
            Monto: ${monto:,.2f}
            Fecha: {fecha}

            El sistema está analizando la factura automáticamente.
            """
        )

    def aprobar_manual(
        self,
        workflow_id: int,
        aprobado_por: str,
        observaciones: Optional[str] = None
    ) -> Dict[str, Any]:
        """Aprueba manualmente una factura."""
        workflow = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.id == workflow_id
        ).first()

        if not workflow:
            return {"error": "Workflow no encontrado"}

        workflow.estado = EstadoFacturaWorkflow.APROBADA_MANUAL
        workflow.estado_anterior = workflow.estado
        workflow.fecha_cambio_estado = datetime.now()
        workflow.tipo_aprobacion = TipoAprobacion.MANUAL
        workflow.aprobada = True
        workflow.aprobada_por = aprobado_por
        workflow.fecha_aprobacion = datetime.now()
        workflow.observaciones_aprobacion = observaciones

        self.db.commit()

        # Notificar aprobación
        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.FACTURA_APROBADA,
            destinatarios=[],  # Contabilidad
            asunto=f"✅ Factura Aprobada - {workflow.factura.numero_factura}",
            cuerpo=f"Factura aprobada manualmente por {aprobado_por}"
        )

        return {
            "exito": True,
            "workflow_id": workflow.id,
            "estado": workflow.estado.value,
            "aprobada_por": aprobado_por
        }

    def rechazar(
        self,
        workflow_id: int,
        rechazado_por: str,
        motivo: str,
        detalle: Optional[str] = None
    ) -> Dict[str, Any]:
        """Rechaza una factura."""
        workflow = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.id == workflow_id
        ).first()

        if not workflow:
            return {"error": "Workflow no encontrado"}

        from app.models.workflow_aprobacion import MotivoRechazo

        workflow.estado = EstadoFacturaWorkflow.RECHAZADA
        workflow.estado_anterior = workflow.estado
        workflow.fecha_cambio_estado = datetime.now()
        workflow.rechazada = True
        workflow.rechazada_por = rechazado_por
        workflow.fecha_rechazo = datetime.now()
        workflow.detalle_rechazo = detalle

        self.db.commit()

        # Notificar rechazo
        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.FACTURA_RECHAZADA,
            destinatarios=[],  # Proveedor, responsable, contabilidad
            asunto=f"❌ Factura Rechazada - {workflow.factura.numero_factura}",
            cuerpo=f"Motivo: {motivo}\n{detalle or ''}"
        )

        return {
            "exito": True,
            "workflow_id": workflow.id,
            "estado": workflow.estado.value,
            "rechazada_por": rechazado_por
        }
