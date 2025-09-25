# app/services/automation/notification_service.py
"""
Servicio de notificaciones para el sistema de automatización de facturas.

Maneja el envío de notificaciones cuando las facturas requieren revisión manual
o cuando se necesita comunicar decisiones automáticas a los responsables.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from dataclasses import dataclass

from app.models.factura import Factura, EstadoFactura
from app.models.responsable import Responsable
from app.crud import responsable as crud_responsable
from app.crud import audit as crud_audit


# Configurar logging
logger = logging.getLogger(__name__)


@dataclass
class ConfiguracionNotificacion:
    """Configuración para diferentes tipos de notificaciones."""
    activar_email: bool = True
    activar_sistema: bool = True
    incluir_detalles_tecnicos: bool = False
    idioma: str = "es"
    plantilla_personalizada: Optional[str] = None


class NotificationService:
    """
    Servicio de notificaciones para automatización de facturas.
    """
    
    def __init__(self):
        self.config_default = ConfiguracionNotificacion()
        
        # Plantillas de mensajes
        self.plantillas = {
            'revision_requerida': {
                'es': {
                    'asunto': 'Factura requiere revisión manual - {numero_factura}',
                    'mensaje': '''
Estimado/a {nombre_responsable},

Se ha recibido una factura que requiere su revisión manual debido a que no cumple con los criterios de automatización.

DETALLES DE LA FACTURA:
- Número: {numero_factura}
- Proveedor: {nombre_proveedor}
- Fecha: {fecha_emision}
- Monto: ${monto:,.2f}
- Concepto: {concepto}

MOTIVO DE REVISIÓN:
{motivo_revision}

ANÁLISIS AUTOMÁTICO:
- Nivel de confianza: {confianza_pct:.1f}%
- Patrón detectado: {patron_detectado}
- Es factura recurrente: {es_recurrente}

Para revisar la factura, ingrese al sistema y busque por el número de factura.

Saludos,
Sistema Automático de Facturas
                    '''
                }
            },
            'aprobacion_automatica': {
                'es': {
                    'asunto': 'Factura aprobada automáticamente - {numero_factura}',
                    'mensaje': '''
Estimado/a {nombre_responsable},

Se ha procesado automáticamente la siguiente factura recurrente:

DETALLES DE LA FACTURA:
- Número: {numero_factura}
- Proveedor: {nombre_proveedor}
- Fecha: {fecha_emision}
- Monto: ${monto:,.2f}
- Concepto: {concepto}

CRITERIOS CUMPLIDOS:
{criterios_cumplidos}

ANÁLISIS AUTOMÁTICO:
- Nivel de confianza: {confianza_pct:.1f}%
- Patrón detectado: {patron_detectado}
- Factura de referencia: {factura_referencia}

La factura ha sido marcada como aprobada y está lista para el siguiente paso en el proceso.

Saludos,
Sistema Automático de Facturas
                    '''
                }
            },
            'resumen_procesamiento': {
                'es': {
                    'asunto': 'Resumen de procesamiento automático - {fecha}',
                    'mensaje': '''
Estimado/a {nombre_responsable},

Se ha completado el procesamiento automático de facturas. Aquí está el resumen:

ESTADÍSTICAS GENERALES:
- Facturas procesadas: {facturas_procesadas}
- Aprobadas automáticamente: {aprobadas_auto}
- Enviadas a revisión: {revision_manual}
- Tasa de automatización: {tasa_automatizacion:.1f}%

FACTURAS QUE REQUIEREN SU ATENCIÓN:
{facturas_pendientes}

PATRONES DETECTADOS:
{patrones_detectados}

Para revisar las facturas pendientes, ingrese al sistema de gestión.

Saludos,
Sistema Automático de Facturas
                    '''
                }
            },
            'error_procesamiento': {
                'es': {
                    'asunto': 'Error en procesamiento automático - {numero_factura}',
                    'mensaje': '''
Estimado/a Administrador,

Ha ocurrido un error durante el procesamiento automático de la factura:

DETALLES:
- Factura: {numero_factura}
- Proveedor: {nombre_proveedor}
- Error: {error_descripcion}
- Fecha del error: {fecha_error}

La factura ha sido marcada para revisión manual.

Por favor, revise el sistema de logs para más detalles.

Saludos,
Sistema Automático de Facturas
                    '''
                }
            }
        }

    def notificar_revision_requerida(
        self, 
        db: Session, 
        factura: Factura,
        motivo: str,
        confianza: float,
        patron_detectado: str,
        config: Optional[ConfiguracionNotificacion] = None
    ) -> Dict[str, Any]:
        """
        Envía notificación cuando una factura requiere revisión manual.
        """
        config = config or self.config_default
        
        try:
            # Obtener responsables de la factura
            responsables = self._obtener_responsables_factura(db, factura)
            
            # Preparar datos para la plantilla
            datos_plantilla = self._preparar_datos_factura(factura, {
                'motivo_revision': motivo,
                'confianza_pct': confianza * 100,
                'patron_detectado': patron_detectado,
                'es_recurrente': 'Sí' if confianza > 0.7 else 'No'
            })
            
            resultados_envio = []
            
            for responsable in responsables:
                datos_plantilla['nombre_responsable'] = responsable.nombre
                
                resultado = self._enviar_notificacion_individual(
                    'revision_requerida',
                    responsable,
                    datos_plantilla,
                    config
                )
                resultados_envio.append(resultado)
            
            # Registrar en auditoría
            self._registrar_notificacion_auditoria(
                db, factura, 'revision_requerida', responsables, motivo
            )
            
            return {
                'exito': True,
                'notificaciones_enviadas': len([r for r in resultados_envio if r['exito']]),
                'total_responsables': len(responsables),
                'detalles': resultados_envio
            }
            
        except Exception as e:
            logger.error(f"Error enviando notificación de revisión para factura {factura.id}: {str(e)}")
            return {'exito': False, 'error': str(e)}

    def notificar_aprobacion_automatica(
        self, 
        db: Session, 
        factura: Factura,
        criterios_cumplidos: List[str],
        confianza: float,
        patron_detectado: str,
        factura_referencia: Optional[str] = None,
        config: Optional[ConfiguracionNotificacion] = None
    ) -> Dict[str, Any]:
        """
        Envía notificación cuando una factura es aprobada automáticamente.
        """
        config = config or self.config_default
        
        try:
            # Solo notificar si está configurado para hacerlo
            if not config.activar_sistema:
                return {'exito': True, 'mensaje': 'Notificaciones desactivadas'}
            
            # Obtener responsables de la factura
            responsables = self._obtener_responsables_factura(db, factura)
            
            # Preparar criterios cumplidos como texto
            criterios_texto = '\n'.join(f"✓ {criterio}" for criterio in criterios_cumplidos)
            
            # Preparar datos para la plantilla
            datos_plantilla = self._preparar_datos_factura(factura, {
                'criterios_cumplidos': criterios_texto,
                'confianza_pct': confianza * 100,
                'patron_detectado': patron_detectado,
                'factura_referencia': factura_referencia or 'N/A'
            })
            
            resultados_envio = []
            
            for responsable in responsables:
                datos_plantilla['nombre_responsable'] = responsable.nombre
                
                resultado = self._enviar_notificacion_individual(
                    'aprobacion_automatica',
                    responsable,
                    datos_plantilla,
                    config
                )
                resultados_envio.append(resultado)
            
            # Registrar en auditoría
            self._registrar_notificacion_auditoria(
                db, factura, 'aprobacion_automatica', responsables
            )
            
            return {
                'exito': True,
                'notificaciones_enviadas': len([r for r in resultados_envio if r['exito']]),
                'total_responsables': len(responsables),
                'detalles': resultados_envio
            }
            
        except Exception as e:
            logger.error(f"Error enviando notificación de aprobación para factura {factura.id}: {str(e)}")
            return {'exito': False, 'error': str(e)}

    def enviar_resumen_procesamiento(
        self, 
        db: Session,
        estadisticas_procesamiento: Dict[str, Any],
        facturas_pendientes: List[Factura],
        responsables_notificar: Optional[List[int]] = None,
        config: Optional[ConfiguracionNotificacion] = None
    ) -> Dict[str, Any]:
        """
        Envía resumen del procesamiento automático a los responsables.
        """
        config = config or self.config_default
        
        try:
            # Obtener responsables a notificar
            if responsables_notificar:
                responsables = [crud_responsable.get_responsable(db, id_resp) 
                             for id_resp in responsables_notificar]
                responsables = [r for r in responsables if r is not None]
            else:
                # Notificar a todos los responsables activos
                responsables = crud_responsable.get_responsables_activos(db)
            
            # Preparar lista de facturas pendientes
            facturas_pendientes_texto = self._formatear_facturas_pendientes(facturas_pendientes)
            
            # Preparar estadísticas de patrones
            patrones_texto = self._formatear_patrones_detectados(
                estadisticas_procesamiento.get('estadisticas_detalladas', {})
            )
            
            # Preparar datos para la plantilla
            datos_plantilla = {
                'fecha': datetime.now().strftime('%d/%m/%Y'),
                'facturas_procesadas': estadisticas_procesamiento['resumen_general']['facturas_procesadas'],
                'aprobadas_auto': estadisticas_procesamiento['resumen_general']['aprobadas_automaticamente'],
                'revision_manual': estadisticas_procesamiento['resumen_general']['enviadas_revision'],
                'tasa_automatizacion': estadisticas_procesamiento['resumen_general']['tasa_automatizacion'],
                'facturas_pendientes': facturas_pendientes_texto,
                'patrones_detectados': patrones_texto
            }
            
            resultados_envio = []
            
            for responsable in responsables:
                datos_plantilla['nombre_responsable'] = responsable.nombre
                
                resultado = self._enviar_notificacion_individual(
                    'resumen_procesamiento',
                    responsable,
                    datos_plantilla,
                    config
                )
                resultados_envio.append(resultado)
            
            return {
                'exito': True,
                'notificaciones_enviadas': len([r for r in resultados_envio if r['exito']]),
                'total_responsables': len(responsables),
                'detalles': resultados_envio
            }
            
        except Exception as e:
            logger.error(f"Error enviando resumen de procesamiento: {str(e)}")
            return {'exito': False, 'error': str(e)}

    def notificar_error_procesamiento(
        self, 
        db: Session,
        factura: Factura,
        error_descripcion: str,
        config: Optional[ConfiguracionNotificacion] = None
    ) -> Dict[str, Any]:
        """
        Notifica errores en el procesamiento automático.
        """
        config = config or self.config_default
        
        try:
            # Obtener administradores/responsables técnicos
            responsables_admin = crud_responsable.get_responsables_por_rol(db, "administrador")
            
            if not responsables_admin:
                # Si no hay administradores, notificar a todos los responsables
                responsables_admin = crud_responsable.get_responsables_activos(db)
            
            # Preparar datos para la plantilla
            datos_plantilla = self._preparar_datos_factura(factura, {
                'error_descripcion': error_descripcion,
                'fecha_error': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            })
            
            resultados_envio = []
            
            for responsable in responsables_admin:
                datos_plantilla['nombre_responsable'] = responsable.nombre
                
                resultado = self._enviar_notificacion_individual(
                    'error_procesamiento',
                    responsable,
                    datos_plantilla,
                    config
                )
                resultados_envio.append(resultado)
            
            # Registrar en auditoría
            self._registrar_notificacion_auditoria(
                db, factura, 'error_procesamiento', responsables_admin, error_descripcion
            )
            
            return {
                'exito': True,
                'notificaciones_enviadas': len([r for r in resultados_envio if r['exito']]),
                'total_responsables': len(responsables_admin),
                'detalles': resultados_envio
            }
            
        except Exception as e:
            logger.error(f"Error enviando notificación de error para factura {factura.id}: {str(e)}")
            return {'exito': False, 'error': str(e)}

    def _obtener_responsables_factura(self, db: Session, factura: Factura) -> List[Responsable]:
        """Obtiene los responsables que deben ser notificados para una factura."""
        responsables = []
        
        # Responsables por proveedor
        if factura.proveedor and factura.proveedor.responsables:
            responsables.extend(factura.proveedor.responsables)
        
        # Si no hay responsables específicos, usar responsables generales
        if not responsables:
            responsables = crud_responsable.get_responsables_activos(db)
        
        return responsables

    def _preparar_datos_factura(self, factura: Factura, datos_extra: Dict[str, Any] = None) -> Dict[str, Any]:
        """Prepara los datos básicos de la factura para las plantillas."""
        datos = {
            'numero_factura': factura.numero_factura,
            'nombre_proveedor': factura.proveedor.nombre if factura.proveedor else 'N/A',
            'fecha_emision': factura.fecha_emision.strftime('%d/%m/%Y') if factura.fecha_emision else 'N/A',
            'monto': float(factura.total_a_pagar or 0),
            'concepto': factura.concepto_principal or factura.concepto_normalizado or 'Sin concepto'
        }
        
        if datos_extra:
            datos.update(datos_extra)
        
        return datos

    def _enviar_notificacion_individual(
        self, 
        tipo_notificacion: str,
        responsable: Responsable,
        datos_plantilla: Dict[str, Any],
        config: ConfiguracionNotificacion
    ) -> Dict[str, Any]:
        """
        Envía una notificación individual a un responsable.
        
        NOTA: Esta implementación simula el envío. En un entorno real,
        aquí se integraría con servicios de email, SMS, etc.
        """
        try:
            plantilla = self.plantillas[tipo_notificacion][config.idioma]
            
            asunto = plantilla['asunto'].format(**datos_plantilla)
            mensaje = plantilla['mensaje'].format(**datos_plantilla)
            
            # Simular envío de notificación
            # En implementación real, aquí iría:
            # - Envío de email (SMTP, SendGrid, etc.)
            # - Notificación push
            # - Mensaje en sistema interno
            
            logger.info(f"Notificación simulada enviada a {responsable.email}: {asunto}")
            
            return {
                'exito': True,
                'responsable_id': responsable.id,
                'responsable_email': responsable.email,
                'tipo_notificacion': tipo_notificacion,
                'asunto': asunto,
                'metodo_envio': 'simulado'  # En real sería 'email', 'sms', etc.
            }
            
        except Exception as e:
            logger.error(f"Error enviando notificación a {responsable.email}: {str(e)}")
            return {
                'exito': False,
                'responsable_id': responsable.id,
                'error': str(e)
            }

    def _formatear_facturas_pendientes(self, facturas_pendientes: List[Factura]) -> str:
        """Formatea la lista de facturas pendientes para mostrar en notificación."""
        if not facturas_pendientes:
            return "No hay facturas pendientes de revisión."
        
        lineas = []
        for i, factura in enumerate(facturas_pendientes[:10], 1):  # Máximo 10
            monto_str = f"${float(factura.total_a_pagar or 0):,.2f}"
            proveedor = factura.proveedor.nombre if factura.proveedor else "Sin proveedor"
            lineas.append(f"{i}. {factura.numero_factura} - {proveedor} - {monto_str}")
        
        if len(facturas_pendientes) > 10:
            lineas.append(f"... y {len(facturas_pendientes) - 10} facturas más")
        
        return '\n'.join(lineas)

    def _formatear_patrones_detectados(self, estadisticas_detalladas: Dict[str, Any]) -> str:
        """Formatea las estadísticas de patrones detectados."""
        patrones = estadisticas_detalladas.get('patrones_temporales_detectados', {})
        
        if not patrones:
            return "No se detectaron patrones específicos."
        
        lineas = []
        for patron, cantidad in patrones.items():
            lineas.append(f"- {patron}: {cantidad} facturas")
        
        return '\n'.join(lineas)

    def _registrar_notificacion_auditoria(
        self, 
        db: Session,
        factura: Factura,
        tipo_notificacion: str,
        responsables: List[Responsable],
        contexto_adicional: str = None
    ) -> None:
        """Registra el envío de notificación en auditoría."""
        detalles = {
            'tipo_notificacion': tipo_notificacion,
            'responsables_notificados': [r.id for r in responsables],
            'cantidad_responsables': len(responsables),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if contexto_adicional:
            detalles['contexto'] = contexto_adicional
        
        crud_audit.create_audit(
            db=db,
            tabla="factura",
            registro_id=factura.id,
            accion=f"notificacion_{tipo_notificacion}",
            usuario="sistema_notificaciones",
            detalles=detalles
        )

    def obtener_configuracion_plantillas(self) -> Dict[str, Any]:
        """Obtiene las plantillas de notificación disponibles."""
        return {
            'tipos_disponibles': list(self.plantillas.keys()),
            'idiomas_soportados': ['es'],
            'plantillas': self.plantillas
        }

    def personalizar_plantilla(
        self, 
        tipo_notificacion: str, 
        idioma: str, 
        nueva_plantilla: Dict[str, str]
    ) -> bool:
        """
        Permite personalizar las plantillas de notificación.
        """
        try:
            if tipo_notificacion in self.plantillas:
                if idioma not in self.plantillas[tipo_notificacion]:
                    self.plantillas[tipo_notificacion][idioma] = {}
                
                self.plantillas[tipo_notificacion][idioma].update(nueva_plantilla)
                return True
            return False
        except Exception as e:
            logger.error(f"Error personalizando plantilla: {str(e)}")
            return False