from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.orm import Session
import asyncio
from threading import Thread

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.init_db import create_default_roles_and_admin
from app.utils.logger import logger
from app.core.config import settings


# Background scheduler para tareas automáticas
_scheduler_thread = None
_scheduler_running = False


def run_automation_task():
    """
    Ejecuta la automatización de facturas en background.
    Se ejecuta periódicamente según configuración.
    """
    try:
        from app.services.automation.automation_service import AutomationService

        db = SessionLocal()
        try:
            logger.info(" Iniciando automatización programada de facturas...")

            automation = AutomationService()
            resultado = automation.procesar_facturas_pendientes(
                db=db,
                limite_facturas=100,  # Procesar hasta 100 facturas por ciclo
                modo_debug=False
            )

            logger.info(
                f" Automatización completada: "
                f"{resultado['aprobadas_automaticamente']} aprobadas, "
                f"{resultado['enviadas_revision']} a revisión, "
                f"{resultado['errores']} errores"
            )

        except Exception as e:
            logger.error(f" Error en automatización programada: {str(e)}")
        finally:
            db.close()

    except Exception as e:
        logger.error(f" Error crítico en task de automatización: {str(e)}")


def schedule_automation_tasks():
    """
    Programa tareas de automatización periódicas.
    """
    import schedule
    import time

    global _scheduler_running

    # Configurar horarios de ejecución automática
    # Ejecutar cada hora durante horario laboral
    schedule.every().hour.at(":00").do(run_automation_task)

    # Ejecución especial: Lunes a las 8:00 AM (inicio de semana)
    schedule.every().monday.at("08:00").do(run_automation_task)

    logger.info(" Scheduler de automatización configurado")
    logger.info("   - Cada hora en punto durante el día")
    logger.info("   - Lunes a las 8:00 AM")

    _scheduler_running = True

    while _scheduler_running:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja startup/shutdown de la app.
    Ideal para inicializar y cerrar recursos empresariales.
    """
    global _scheduler_thread, _scheduler_running

    try:
        # --- Startup ---
        logger.info(" Iniciando aplicación AFE Backend...")

        if settings.environment == "development":
             Base.metadata.create_all(bind=engine)

        session = Session(bind=engine)
        try:
            create_default_roles_and_admin(session)
        finally:
            session.close()

        # --- Automatización Inicial ---
        # Ejecutar automatización al iniciar (modo asíncrono para no bloquear startup)
        logger.info(" Ejecutando automatización inicial de facturas...")

        def run_initial_automation():
            db = SessionLocal()
            try:
                from app.services.automation.automation_service import AutomationService
                automation = AutomationService()
                resultado = automation.procesar_facturas_pendientes(
                    db=db,
                    limite_facturas=50,
                    modo_debug=False
                )
                logger.info(
                    f" Automatización inicial: {resultado['aprobadas_automaticamente']} aprobadas, "
                    f"{resultado['enviadas_revision']} a revisión"
                )
            except Exception as e:
                logger.error(f" Error en automatización inicial: {str(e)}")
            finally:
                db.close()

        # Ejecutar en background thread para no bloquear
        initial_thread = Thread(target=run_initial_automation, daemon=True)
        initial_thread.start()

        # --- Scheduler de Tareas Periódicas ---
        # Iniciar scheduler en thread separado
        try:
            import schedule
            _scheduler_thread = Thread(target=schedule_automation_tasks, daemon=True)
            _scheduler_thread.start()
            logger.info(" Scheduler de automatización iniciado")
        except ImportError:
            logger.warning("  Módulo 'schedule' no disponible. Instalar con: pip install schedule")
            logger.info("   Automatización programada deshabilitada (solo manual)")

        # --- Scheduler de Notificaciones ---
        # Iniciar scheduler de notificaciones (resumen semanal, alertas urgentes)
        try:
            from app.services.scheduler_notificaciones import iniciar_scheduler_notificaciones
            iniciar_scheduler_notificaciones()
            logger.info(" Scheduler de notificaciones iniciado")
        except Exception as e:
            logger.warning(f"  Error iniciando scheduler de notificaciones: {str(e)}")

        logger.info(" Startup completado correctamente")

    except Exception as e:
        logger.exception(" Error en startup: %s", e)

    # La app se levanta aquí
    yield

    # --- Shutdown ---
    logger.info(" Aplicación apagándose...")

    # Detener scheduler de automatización
    _scheduler_running = False
    if _scheduler_thread:
        logger.info("   Deteniendo scheduler de automatización...")
        # El thread es daemon, se cerrará automáticamente

    # Detener scheduler de notificaciones
    try:
        from app.services.scheduler_notificaciones import detener_scheduler_notificaciones
        detener_scheduler_notificaciones()
    except Exception as e:
        logger.warning(f"  Error deteniendo scheduler de notificaciones: {str(e)}")

    logger.info(" Aplicación cerrada correctamente")
