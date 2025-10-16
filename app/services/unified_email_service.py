# app/services/unified_email_service.py
"""
Servicio unificado de envío de emails.

Estrategia:
1. Intenta enviar con Microsoft Graph (principal)
2. Si falla, intenta con SMTP (fallback)
3. Logging detallado de cada intento
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from app.core.config import settings
from app.services.microsoft_graph_email_service import (
    get_graph_email_service,
    MicrosoftGraphEmailService
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class UnifiedEmailService:
    """
    Servicio unificado que combina Microsoft Graph y SMTP.

    Prioridad:
    1. Microsoft Graph (más seguro, corporativo)
    2. SMTP (fallback si Graph falla)
    """

    def __init__(self):
        """Inicializa ambos servicios de email."""
        self.graph_service = None
        self.smtp_service = None

        # Inicializar Graph si está configurado
        if self._is_graph_configured():
            try:
                self.graph_service = get_graph_email_service(
                    tenant_id=settings.graph_tenant_id,
                    client_id=settings.graph_client_id,
                    client_secret=settings.graph_client_secret,
                    from_email=settings.graph_from_email,
                    from_name=settings.graph_from_name
                )
                logger.info("✅ Microsoft Graph Email Service inicializado")
            except Exception as e:
                logger.warning(f"⚠️  Error inicializando Graph service: {str(e)}")

        # Inicializar SMTP si está configurado
        if self._is_smtp_configured():
            try:
                self.smtp_service = EmailService()
                logger.info("✅ SMTP Email Service inicializado (fallback)")
            except Exception as e:
                logger.warning(f"⚠️  Error inicializando SMTP service: {str(e)}")

        # Validar que al menos uno esté configurado
        if not self.graph_service and not self.smtp_service:
            logger.error("❌ Ningún servicio de email está configurado")

    def _is_graph_configured(self) -> bool:
        """Verifica si Microsoft Graph está configurado."""
        return bool(
            settings.graph_tenant_id and
            settings.graph_client_id and
            settings.graph_client_secret
        )

    def _is_smtp_configured(self) -> bool:
        """Verifica si SMTP está configurado."""
        return bool(
            settings.smtp_user and
            settings.smtp_password
        )

    def send_email(
        self,
        to_email: str | List[str],
        subject: str,
        body_html: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Path]] = None,
        importance: str = "normal"
    ) -> Dict[str, Any]:
        """
        Envía email usando la mejor opción disponible.

        Orden de prioridad:
        1. Microsoft Graph
        2. SMTP (fallback)

        Args:
            to_email: Destinatario(s)
            subject: Asunto
            body_html: Cuerpo en HTML
            cc: Lista de CC
            bcc: Lista de BCC
            attachments: Archivos adjuntos
            importance: Importancia ("low", "normal", "high")

        Returns:
            Dict con resultado del envío
        """
        # Normalizar destinatarios
        if isinstance(to_email, str):
            to_email = [to_email]

        # Intentar con Microsoft Graph primero
        if self.graph_service:
            try:
                logger.info("📧 Intentando envío con Microsoft Graph...")
                result = self.graph_service.send_email(
                    to_email=to_email,
                    subject=subject,
                    body_html=body_html,
                    cc=cc,
                    bcc=bcc,
                    attachments=attachments,
                    importance=importance
                )

                if result.get('success'):
                    logger.info(f"✅ Email enviado exitosamente vía Microsoft Graph a {', '.join(to_email)}")
                    return result

                logger.warning(f"⚠️  Graph falló: {result.get('error')}, intentando con SMTP...")

            except Exception as e:
                logger.warning(f"⚠️  Error con Microsoft Graph: {str(e)}, intentando con SMTP...")

        # Fallback a SMTP
        if self.smtp_service:
            try:
                logger.info("📧 Intentando envío con SMTP (fallback)...")
                result = self.smtp_service.send_email(
                    to_email=to_email,
                    subject=subject,
                    body_html=body_html,
                    cc=cc,
                    bcc=bcc,
                    attachments=attachments
                )

                if result.get('success'):
                    logger.info(f"✅ Email enviado exitosamente vía SMTP a {', '.join(to_email)}")
                    result['provider'] = 'smtp_fallback'
                    return result

                logger.error(f"❌ SMTP también falló: {result.get('error')}")
                return result

            except Exception as e:
                logger.error(f"❌ Error con SMTP: {str(e)}")
                return {
                    'success': False,
                    'error': f'SMTP fallback error: {str(e)}',
                    'provider': 'smtp_fallback'
                }

        # Si llegamos aquí, ningún servicio está disponible
        error_msg = "No hay servicios de email configurados"
        logger.error(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'provider': 'none'
        }

    def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        subject_template: str,
        body_template: str,
        rate_limit: int = 10,
        delay_between_batches: float = 1.0
    ) -> Dict[str, Any]:
        """
        Envía emails en bulk.

        Args:
            recipients: Lista de dicts con 'email' y variables
            subject_template: Template del asunto
            body_template: Template del cuerpo
            rate_limit: Emails por segundo
            delay_between_batches: Delay entre batches

        Returns:
            Estadísticas de envío
        """
        # Usar Graph si está disponible, sino SMTP
        service = self.graph_service or self.smtp_service

        if not service:
            return {
                'total': len(recipients),
                'sent': 0,
                'failed': len(recipients),
                'errors': [{'error': 'No email service configured'}]
            }

        return service.send_bulk_emails(
            recipients=recipients,
            subject_template=subject_template,
            body_template=body_template,
            rate_limit=rate_limit,
            delay_between_batches=delay_between_batches
        )

    def get_active_provider(self) -> str:
        """Retorna el proveedor activo de email."""
        if self.graph_service:
            return "microsoft_graph"
        elif self.smtp_service:
            return "smtp"
        else:
            return "none"


# Singleton global
_unified_email_service = None


def get_unified_email_service() -> UnifiedEmailService:
    """
    Obtiene instancia singleton del servicio unificado.

    Returns:
        UnifiedEmailService configurado
    """
    global _unified_email_service
    if _unified_email_service is None:
        _unified_email_service = UnifiedEmailService()
    return _unified_email_service
