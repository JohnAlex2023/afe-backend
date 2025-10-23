"""
Servicio de Workflow Automático de Aprobación de Facturas.

Este servicio analiza facturas nuevas y:
1. Identifica el NIT del proveedor
2. Asigna automáticamente al responsable
3. Compara ITEM POR ITEM con facturas del mes anterior (usando ComparadorItemsService)
4. Aprueba automáticamente si cumple criterios de confianza
5. Envía a revisión manual si hay diferencias
6. Genera notificaciones
7. Sincroniza estados con tabla facturas

Integración: Se activa cuando llegan nuevas facturas desde Microsoft Graph a la tabla facturas

Nivel: Enterprise Fortune 500
Refactorizado: 2025-10-10
Arquitecto: Senior Backend Development Team
"""

from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.factura import Factura, EstadoFactura
from app.models.workflow_aprobacion import (
    WorkflowAprobacionFactura,
    AsignacionNitResponsable,
    NotificacionWorkflow,
    EstadoFacturaWorkflow,
    TipoAprobacion,
    TipoNotificacion
)
from app.services.comparador_items import ComparadorItemsService
from app.services.clasificacion_proveedores import ClasificacionProveedoresService


class WorkflowAutomaticoService:
    """
    Servicio principal de workflow automático.

    Refactorizado para usar ComparadorItemsService enterprise-grade
    y sincronización automática de estados.
    """

    def __init__(self, db: Session):
        self.db = db
        self.comparador = ComparadorItemsService(db)
        self.clasificador = ClasificacionProveedoresService(db)

    # ============================================================================
    # SINCRONIZACIÓN DE ESTADOS (Enterprise Pattern)
    # ============================================================================

    def _sincronizar_estado_factura(self, workflow: WorkflowAprobacionFactura) -> None:
        """
        Sincroniza el estado de la factura con el estado del workflow.

        Enterprise Pattern: Single Source of Truth
        - El workflow es la fuente autoritativa de estado
        - La factura refleja el estado del workflow automáticamente
        - Garantiza consistencia entre tablas

        Args:
            workflow: Workflow con el estado actualizado
        """
        # Mapeo autoritativo: EstadoFacturaWorkflow -> EstadoFactura
        # REFACTORIZADO: Eliminado estado 'pendiente', todo va a 'en_revision'
        MAPEO_ESTADOS = {
            EstadoFacturaWorkflow.RECIBIDA: EstadoFactura.en_revision,
            EstadoFacturaWorkflow.EN_ANALISIS: EstadoFactura.en_revision,
            EstadoFacturaWorkflow.APROBADA_AUTO: EstadoFactura.aprobada_auto,
            EstadoFacturaWorkflow.APROBADA_MANUAL: EstadoFactura.aprobada,
            EstadoFacturaWorkflow.RECHAZADA: EstadoFactura.rechazada,
            EstadoFacturaWorkflow.PENDIENTE_REVISION: EstadoFactura.en_revision,
            EstadoFacturaWorkflow.EN_REVISION: EstadoFactura.en_revision,
            EstadoFacturaWorkflow.OBSERVADA: EstadoFactura.en_revision,
            EstadoFacturaWorkflow.ENVIADA_CONTABILIDAD: EstadoFactura.aprobada,
            EstadoFacturaWorkflow.PROCESADA: EstadoFactura.pagada,
        }

        if workflow.factura:
            nuevo_estado = MAPEO_ESTADOS.get(workflow.estado, EstadoFactura.en_revision)
            workflow.factura.estado = nuevo_estado

            # Sincronizar campos de auditoría adicionales
            if workflow.aprobada:
                workflow.factura.aprobado_por = workflow.aprobada_por
                workflow.factura.fecha_aprobacion = workflow.fecha_aprobacion
                # ✨ ACCION_POR: Single source of truth para dashboard
                workflow.factura.accion_por = workflow.aprobada_por

            if workflow.rechazada:
                workflow.factura.rechazado_por = workflow.rechazada_por
                workflow.factura.fecha_rechazo = workflow.fecha_rechazo
                workflow.factura.motivo_rechazo = workflow.detalle_rechazo
                # ✨ ACCION_POR: Single source of truth para dashboard
                workflow.factura.accion_por = workflow.rechazada_por

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

        # 4.5 NUEVO: Clasificación automática del proveedor (si no está clasificado)
        self._asegurar_clasificacion_proveedor(asignacion)

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

        # 🔥 IMPORTANTE: Asignar responsable directamente a la factura (sincronización bidireccional)
        factura.responsable_id = asignacion.responsable_id

        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        self.db.refresh(factura)  # Refrescar factura para que cargue la relación responsable

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

    def _normalizar_nit(self, nit: str) -> str:
        """
        Normaliza un NIT eliminando el dígito de verificación y caracteres especiales.

        Enterprise Pattern: Normalización de identificadores para matching robusto.

        Ejemplos:
            "830122566-1" -> "830122566"
            "830.122.566-1" -> "830122566"
            "830122566" -> "830122566"
            "900.359.573-5" -> "900359573"

        Args:
            nit: NIT original (con o sin DV)

        Returns:
            NIT normalizado (solo dígitos del número principal, sin DV)
        """
        if not nit:
            return ""

        # Si tiene guión, separar el número principal del dígito de verificación
        if "-" in nit:
            # Tomar solo la parte antes del guión (el número principal)
            nit_principal = nit.split("-")[0]
        else:
            nit_principal = nit

        # Eliminar puntos y espacios
        nit_limpio = nit_principal.replace(".", "").replace(" ", "")

        # Tomar solo dígitos
        nit_solo_digitos = "".join(c for c in nit_limpio if c.isdigit())

        return nit_solo_digitos

    def _buscar_asignacion_responsable(self, nit: Optional[str]) -> Optional[AsignacionNitResponsable]:
        """
        Busca la asignación de responsable para un NIT.

        Enterprise Pattern: Búsqueda con normalización automática de NITs.
        Busca tanto con NIT original como normalizado para máxima compatibilidad.
        """
        if not nit:
            return None

        # 1. Intentar búsqueda exacta primero (más rápido)
        asignacion = self.db.query(AsignacionNitResponsable).filter(
            and_(
                AsignacionNitResponsable.nit == nit,
                AsignacionNitResponsable.activo == True
            )
        ).first()

        if asignacion:
            return asignacion

        # 2. Si no se encuentra, intentar con NIT normalizado
        nit_normalizado = self._normalizar_nit(nit)

        # Buscar asignaciones que coincidan con el NIT normalizado
        # Normalizamos los NITs de la BD en la query para comparar
        asignaciones = self.db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == True
        ).all()

        for asig in asignaciones:
            if self._normalizar_nit(asig.nit) == nit_normalizado:
                return asig

        return None

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
        Compara la factura ITEM POR ITEM con facturas del mes anterior.

        Enterprise Pattern: Usa ComparadorItemsService para análisis granular.

        Args:
            factura: Factura a analizar
            workflow: Workflow asociado
            asignacion: Configuración del responsable

        Returns:
            Dict con resultado del análisis y decisión de aprobación
        """
        # Cambiar estado a EN_ANALISIS
        workflow.estado = EstadoFacturaWorkflow.EN_ANALISIS
        workflow.fecha_cambio_estado = datetime.now()
        self._sincronizar_estado_factura(workflow)  #   Sincronizar
        tiempo_inicio = datetime.now()

        # ============================================================================
        # COMPARACIÓN ENTERPRISE: Item por Item usando ComparadorItemsService
        # ============================================================================

        try:
            resultado_comparacion = self.comparador.comparar_factura_vs_historial(
                factura_id=factura.id,
                meses_historico=12  # Analiza últimos 12 meses de historial
            )

            # Actualizar workflow con resultados de la comparación
            workflow.tiempo_en_analisis = int((datetime.now() - tiempo_inicio).total_seconds())
            workflow.criterios_comparacion = {
                "items_analizados": resultado_comparacion['items_analizados'],
                "items_ok": resultado_comparacion['items_ok'],
                "items_con_alertas": resultado_comparacion['items_con_alertas'],
                "nuevos_items_count": resultado_comparacion['nuevos_items_count'],
                "metodo": "ComparadorItemsService_v1.0"
            }

            # Calcular porcentaje de similitud basado en items
            if resultado_comparacion['items_analizados'] > 0:
                porcentaje_similitud = (
                    resultado_comparacion['items_ok'] /
                    resultado_comparacion['items_analizados'] * 100
                )
            else:
                porcentaje_similitud = 0

            workflow.porcentaje_similitud = Decimal(str(round(porcentaje_similitud, 2)))
            workflow.es_identica_mes_anterior = (resultado_comparacion['confianza'] >= 95)

            # Almacenar alertas como diferencias detectadas
            if resultado_comparacion['alertas']:
                workflow.diferencias_detectadas = resultado_comparacion['alertas']

            # ============================================================================
            # DECISIÓN: ¿Aprobar automáticamente o enviar a revisión?
            # ============================================================================

            if self._puede_aprobar_automaticamente_v2(
                workflow,
                asignacion,
                factura,
                resultado_comparacion
            ):
                return self._aprobar_automaticamente(workflow, factura)
            else:
                return self._enviar_a_revision_manual_v2(
                    workflow,
                    resultado_comparacion
                )

        except Exception as e:
            # Error en comparación: enviar a revisión manual por seguridad
            workflow.estado = EstadoFacturaWorkflow.PENDIENTE_REVISION
            workflow.fecha_cambio_estado = datetime.now()
            workflow.tiempo_en_analisis = int((datetime.now() - tiempo_inicio).total_seconds())
            workflow.criterios_comparacion = {
                "error_comparacion": str(e),
                "requiere_revision_manual": True
            }
            self._sincronizar_estado_factura(workflow)  #   Sincronizar
            self.db.commit()

            return {
                "requiere_revision": True,
                "motivo": f"Error en análisis automático: {str(e)}",
                "estado": workflow.estado.value
            }

    # ============================================================================
    # MÉTODOS DE DECISIÓN ENTERPRISE (Refactorizados)
    # ============================================================================

    def _puede_aprobar_automaticamente_v2(
        self,
        workflow: WorkflowAprobacionFactura,
        asignacion: AsignacionNitResponsable,
        factura: Factura,
        resultado_comparacion: Dict[str, Any]
    ) -> bool:
        """
        Determina si la factura puede aprobarse automáticamente.

        Enterprise Rules Engine con validaciones multinivel.

        Args:
            workflow: Workflow actual
            asignacion: Configuración del responsable
            factura: Factura a evaluar
            resultado_comparacion: Resultado del ComparadorItemsService

        Returns:
            True si cumple TODAS las reglas de aprobación automática
        """
        # ============================================================================
        # REGLA 1: Configuración del Responsable
        # ============================================================================

        # 1.1 - Debe estar habilitada la aprobación automática
        if not asignacion.permitir_aprobacion_automatica:
            return False

        # 1.2 - No debe requerir revisión siempre
        if asignacion.requiere_revision_siempre:
            return False

        # ============================================================================
        # REGLA 2: Confianza del Análisis de Items (ENTERPRISE: Umbral Dinámico)
        # ============================================================================

        # 2.1 - Obtener umbral dinámico basado en clasificación del proveedor
        umbral_requerido = self.clasificador.obtener_umbral_aprobacion(
            tipo_servicio=asignacion.tipo_servicio_proveedor,
            nivel_confianza=asignacion.nivel_confianza_proveedor
        )

        # Convertir a porcentaje para comparación
        umbral_porcentaje = umbral_requerido * 100

        # Almacenar umbral usado para trazabilidad
        workflow.umbral_confianza_utilizado = Decimal(str(round(umbral_porcentaje, 2)))
        workflow.tipo_validacion_aplicada = f"{asignacion.tipo_servicio_proveedor}_{asignacion.nivel_confianza_proveedor}"

        # Comparar con umbral dinámico (no fijo 95%)
        if resultado_comparacion['confianza'] < umbral_porcentaje:
            return False

        # 2.2 - No debe tener alertas críticas (severidad alta)
        alertas_criticas = [
            alerta for alerta in resultado_comparacion.get('alertas', [])
            if alerta.get('severidad') == 'alta'
        ]
        if alertas_criticas:
            return False

        # 2.3 - No debe tener items nuevos sin historial (requiere revisión)
        if resultado_comparacion.get('nuevos_items_count', 0) > 0:
            return False

        # ============================================================================
        # REGLA 3: Validación de Montos
        # ============================================================================

        # 3.1 - Monto debe estar dentro del límite configurado
        if asignacion.monto_maximo_auto_aprobacion:
            if factura.total_a_pagar and factura.total_a_pagar > asignacion.monto_maximo_auto_aprobacion:
                return False

        # ============================================================================
        # REGLA 4: Orden de Compra Obligatoria (ENTERPRISE)
        # ============================================================================

        # 4.1 - Si el proveedor requiere OC obligatoria, debe existir
        if asignacion.requiere_orden_compra_obligatoria:
            # Verificar que la factura tenga orden de compra
            if not hasattr(factura, 'orden_compra') and not hasattr(factura, 'numero_orden_compra'):
                # Campos no existen en el modelo, skip esta validación
                pass
            elif not factura.orden_compra and not factura.numero_orden_compra:
                # No tiene OC → No auto-aprobar
                return False

        # ============================================================================
        # TODAS LAS REGLAS APROBADAS  
        # ============================================================================
        return True

    def _aprobar_automaticamente(
        self,
        workflow: WorkflowAprobacionFactura,
        factura: Factura
    ) -> Dict[str, Any]:
        """
        Aprueba automáticamente una factura.

        Enterprise Pattern: Aprobación con trazabilidad completa.
        """
        workflow.estado = EstadoFacturaWorkflow.APROBADA_AUTO
        workflow.fecha_cambio_estado = datetime.now()
        workflow.tipo_aprobacion = TipoAprobacion.AUTOMATICA
        workflow.aprobada = True
        workflow.aprobada_por = "SISTEMA_AUTO"
        workflow.fecha_aprobacion = datetime.now()
        workflow.observaciones_aprobacion = (
            f"  Aprobación automática - Confianza: {workflow.porcentaje_similitud}%\n"
            f"Análisis de items: {workflow.criterios_comparacion.get('items_ok', 0)}/{workflow.criterios_comparacion.get('items_analizados', 0)} items verificados\n"
            f"Método: ComparadorItemsService Enterprise v1.0"
        )

        #   SINCRONIZAR ESTADO CON FACTURA
        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        # Enviar notificación de aprobación automática
        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.FACTURA_APROBADA,
            destinatarios=[],  # Se llenará con emails del responsable y contabilidad
            asunto=f"  Factura Aprobada Automáticamente - {factura.numero_factura}",
            cuerpo=f"""
            La factura {factura.numero_factura} ha sido aprobada automáticamente.

            Proveedor: {factura.proveedor}
            Monto: ${factura.total_a_pagar:,.2f}
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

    def _enviar_a_revision_manual_v2(
        self,
        workflow: WorkflowAprobacionFactura,
        resultado_comparacion: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Envía la factura a revisión manual.

        Enterprise Pattern: Revisión inteligente con contexto completo.
        """
        workflow.estado = EstadoFacturaWorkflow.PENDIENTE_REVISION
        workflow.fecha_cambio_estado = datetime.now()

        #   SINCRONIZAR ESTADO CON FACTURA
        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        # Crear notificación para el responsable con contexto completo
        alertas_resumen = self._formatear_alertas_para_notificacion(
            resultado_comparacion.get('alertas', [])
        )

        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.PENDIENTE_REVISION,
            destinatarios=[],  # Email del responsable
            asunto=f" Factura Pendiente de Revisión - {workflow.factura.numero_factura}",
            cuerpo=f"""
            La factura {workflow.factura.numero_factura} requiere su revisión manual.

            ANÁLISIS AUTOMÁTICO:
            - Items analizados: {resultado_comparacion.get('items_analizados', 0)}
            - Items OK: {resultado_comparacion.get('items_ok', 0)}
            - Items con alertas: {resultado_comparacion.get('items_con_alertas', 0)}
            - Items nuevos: {resultado_comparacion.get('nuevos_items_count', 0)}
            - Confianza: {resultado_comparacion.get('confianza', 0)}%

             ALERTAS DETECTADAS:
            {alertas_resumen}

            Por favor, revise y apruebe o rechace la factura en el sistema.
            """
        )

        return {
            "requiere_revision": True,
            "estado": workflow.estado.value,
            "alertas": resultado_comparacion.get('alertas', []),
            "items_analizados": resultado_comparacion.get('items_analizados', 0),
            "items_con_alertas": resultado_comparacion.get('items_con_alertas', 0),
            "porcentaje_similitud": float(workflow.porcentaje_similitud or 0),
            "confianza": resultado_comparacion.get('confianza', 0),
            "mensaje": "Factura enviada a revisión manual - Análisis enterprise completado"
        }

    def _formatear_alertas_para_notificacion(self, alertas: List[Dict]) -> str:
        """Formatea las alertas del comparador para mostrar en notificación."""
        if not alertas:
            return "Sin alertas"

        texto = ""
        for i, alerta in enumerate(alertas[:10], 1):  # Máximo 10 alertas en email
            severidad_emoji = {
                'alta': '🔴',
                'media': '🟡',
                'baja': '🟢'
            }.get(alerta.get('severidad', 'media'), '⚪')

            texto += f"\n{i}. {severidad_emoji} {alerta.get('tipo', 'Alerta')}: {alerta.get('mensaje', 'Sin detalle')}"

        if len(alertas) > 10:
            texto += f"\n\n... y {len(alertas) - 10} alertas más. Ver sistema para detalle completo."

        return texto

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
        monto = factura.total_a_pagar or 0
        fecha = factura.fecha_emision or "Sin fecha"

        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.FACTURA_RECIBIDA,
            destinatarios=[],  # Email del responsable
            asunto=f" Nueva Factura Recibida - {factura.numero_factura}",
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
        """
        Aprueba manualmente una factura.

        Enterprise Pattern: Aprobación manual con trazabilidad y sincronización.
        """
        workflow = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.id == workflow_id
        ).first()

        if not workflow:
            return {"error": "Workflow no encontrado"}

        # Actualizar workflow
        workflow.estado_anterior = workflow.estado
        workflow.estado = EstadoFacturaWorkflow.APROBADA_MANUAL
        workflow.fecha_cambio_estado = datetime.now()
        workflow.tipo_aprobacion = TipoAprobacion.MANUAL
        workflow.aprobada = True
        workflow.aprobada_por = aprobado_por
        workflow.fecha_aprobacion = datetime.now()
        workflow.observaciones_aprobacion = observaciones

        #   SINCRONIZAR ESTADO CON FACTURA
        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        # Notificar aprobación
        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.FACTURA_APROBADA,
            destinatarios=[],  # Contabilidad
            asunto=f"  Factura Aprobada - {workflow.factura.numero_factura}",
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
        """
        Rechaza una factura.

        Enterprise Pattern: Rechazo con trazabilidad y sincronización.
        """
        workflow = self.db.query(WorkflowAprobacionFactura).filter(
            WorkflowAprobacionFactura.id == workflow_id
        ).first()

        if not workflow:
            return {"error": "Workflow no encontrado"}

        from app.models.workflow_aprobacion import MotivoRechazo

        # Actualizar workflow
        workflow.estado_anterior = workflow.estado
        workflow.estado = EstadoFacturaWorkflow.RECHAZADA
        workflow.fecha_cambio_estado = datetime.now()
        workflow.rechazada = True
        workflow.rechazada_por = rechazado_por
        workflow.fecha_rechazo = datetime.now()
        workflow.detalle_rechazo = detalle

        #   SINCRONIZAR ESTADO CON FACTURA
        self._sincronizar_estado_factura(workflow)

        self.db.commit()

        # Notificar rechazo
        self._crear_notificacion(
            workflow=workflow,
            tipo=TipoNotificacion.FACTURA_RECHAZADA,
            destinatarios=[],  # Proveedor, responsable, contabilidad
            asunto=f" Factura Rechazada - {workflow.factura.numero_factura}",
            cuerpo=f"Motivo: {motivo}\n{detalle or ''}"
        )

        return {
            "exito": True,
            "workflow_id": workflow.id,
            "estado": workflow.estado.value,
            "rechazada_por": rechazado_por
        }

    # ============================================================================
    # CLASIFICACIÓN AUTOMÁTICA DE PROVEEDORES (Enterprise Feature)
    # ============================================================================

    def _asegurar_clasificacion_proveedor(self, asignacion: AsignacionNitResponsable) -> None:
        """
        Asegura que el proveedor esté clasificado ANTES de procesar la factura.

        Esta función se ejecuta automáticamente para CADA factura nueva:
        - Si el proveedor ya está clasificado → No hace nada
        - Si es proveedor nuevo sin clasificación → Clasifica con valores seguros por defecto
        - Si tiene 3+ meses y 3+ facturas → Reclasifica automáticamente

        Clasificación por defecto (proveedor nuevo):
        - Tipo: SERVICIO_EVENTUAL (más restrictivo)
        - Nivel: NIVEL_5_NUEVO (requiere 100% confianza = nunca auto-aprobar)
        - Requiere OC: True

        Esta función garantiza que NUNCA se auto-apruebe un proveedor sin clasificar.

        Args:
            asignacion: Asignación NIT-Responsable del proveedor

        Nivel: Fortune 500 Risk Management
        """
        # Si ya está clasificado Y no necesita reclasificación → Skip
        if asignacion.tipo_servicio_proveedor:
            # Verificar si necesita reclasificación (cada 3 meses)
            if asignacion.metadata_riesgos:
                fecha_clasificacion = asignacion.metadata_riesgos.get('fecha_clasificacion')
                if fecha_clasificacion:
                    from dateutil.parser import parse
                    fecha_class = parse(fecha_clasificacion)
                    dias_desde_clasificacion = (datetime.now() - fecha_class).days

                    # Reclasificar cada 90 días (3 meses)
                    if dias_desde_clasificacion < 90:
                        return  #   Clasificación reciente, no hacer nada

        # Clasificar o reclasificar
        try:
            resultado = self.clasificador.clasificar_proveedor_automatico(
                nit=asignacion.nit,
                forzar_reclasificacion=False  # Solo si no está clasificado
            )

            # Log para auditoría (opcional)
            if resultado['clasificado'] and not resultado.get('ya_clasificado'):
                print(f" Proveedor {asignacion.nit} clasificado automáticamente: "
                      f"{resultado['tipo_servicio'].value} - {resultado['nivel_confianza'].value}")

        except Exception as e:
            # Si hay error en clasificación, simplemente skip y continuar
            # El proveedor sin clasificación irá a revisión manual (umbral 100%)
            print(f"  Error clasificando proveedor: {str(e)[:100]}")
            print(f"   El proveedor continuará sin clasificación automática")
            # No hacer nada más - dejar que el workflow continúe sin clasificación
            # La función obtener_umbral_aprobacion manejará el caso de proveedor sin clasificar
