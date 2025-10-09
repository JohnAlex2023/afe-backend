"""
Servicio de Inicialización Enterprise del Sistema Completo.

Este servicio orquesta la inicialización completa del sistema:
1. Importación de presupuesto desde Excel
2. Auto-configuración de asignaciones NIT-Responsable
3. Vinculación automática de facturas existentes con presupuesto
4. Activación de workflow de aprobación
5. Generación de reporte ejecutivo

Características Enterprise:
- Transacciones atómicas
- Validaciones completas
- Rollback automático en caso de error
- Idempotente (se puede ejecutar múltiples veces)
- Logging detallado
- Reporte ejecutivo

Autor: Senior Backend Developer
Nivel: Fortune 500 Enterprise
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.factura import Factura
from app.models.presupuesto import LineaPresupuesto, EjecucionPresupuestal
from app.models.workflow_aprobacion import AsignacionNitResponsable, WorkflowAprobacionFactura
from app.services.excel_to_presupuesto import ExcelPresupuestoImporter
from app.services.auto_vinculacion import AutoVinculador
from app.services.workflow_automatico import WorkflowAutomaticoService


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InicializacionSistemaService:
    """
    Servicio de inicialización completa del sistema.
    """

    def __init__(self, db: Session):
        self.db = db
        self.resultados = {
            "inicio": datetime.now(),
            "pasos_completados": [],
            "errores": [],
            "warnings": [],
            "estadisticas": {}
        }

    def inicializar_sistema_completo(
        self,
        archivo_presupuesto: Optional[str] = None,
        año_fiscal: int = 2025,
        responsable_default_id: int = 1,
        ejecutar_vinculacion: bool = True,
        ejecutar_workflow: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Inicialización completa del sistema.

        Args:
            archivo_presupuesto: Ruta al Excel de presupuesto (None = buscar automáticamente)
            año_fiscal: Año fiscal a procesar
            responsable_default_id: ID del responsable por defecto
            ejecutar_vinculacion: Si debe vincular facturas con presupuesto
            ejecutar_workflow: Si debe activar workflow de aprobación
            dry_run: Si True, solo simula sin hacer cambios

        Returns:
            Dict con reporte completo de la inicialización
        """
        logger.info("=" * 80)
        logger.info("INICIALIZACIÓN ENTERPRISE DEL SISTEMA AFE")
        logger.info("=" * 80)

        try:
            # PASO 1: Verificar estado actual
            logger.info("\n PASO 1: Verificando estado actual del sistema...")
            estado_inicial = self._verificar_estado_sistema()
            self.resultados["estado_inicial"] = estado_inicial
            self._log_paso_completado("Verificación de estado")

            # PASO 2: Validar pre-requisitos
            logger.info("\n PASO 2: Validando pre-requisitos...")
            validacion = self._validar_prerequisitos(
                archivo_presupuesto,
                responsable_default_id
            )
            if not validacion["valido"]:
                return self._generar_reporte_error(validacion["errores"])
            self._log_paso_completado("Validación de pre-requisitos")

            # PASO 3: Importar presupuesto
            if archivo_presupuesto and estado_inicial["lineas_presupuesto"] == 0:
                logger.info("\n PASO 3: Importando presupuesto desde Excel...")
                resultado_import = self._importar_presupuesto(
                    archivo_presupuesto,
                    año_fiscal,
                    responsable_default_id,
                    dry_run
                )
                self.resultados["importacion_presupuesto"] = resultado_import
                self._log_paso_completado("Importación de presupuesto")
            else:
                logger.info("\n  PASO 3: Saltando importación (ya existen datos o no hay archivo)")
                self.resultados["warnings"].append("Importación de presupuesto omitida")

            # PASO 4: Auto-configurar asignaciones NIT-Responsable
            logger.info("\n PASO 4: Auto-configurando asignaciones NIT-Responsable...")
            resultado_asignaciones = self._autoconfigurar_asignaciones(
                responsable_default_id,
                dry_run
            )
            self.resultados["asignaciones"] = resultado_asignaciones
            self._log_paso_completado("Auto-configuración de asignaciones")

            # PASO 5: Vincular facturas con presupuesto
            if ejecutar_vinculacion:
                logger.info("\n PASO 5: Vinculando facturas existentes con presupuesto...")
                resultado_vinculacion = self._vincular_facturas_masivo(
                    año_fiscal,
                    dry_run
                )
                self.resultados["vinculacion"] = resultado_vinculacion
                self._log_paso_completado("Vinculación de facturas")
            else:
                logger.info("\n  PASO 5: Saltando vinculación (deshabilitado)")

            # PASO 6: Activar workflow de aprobación
            if ejecutar_workflow:
                logger.info("\n  PASO 6: Activando workflow de aprobación...")
                resultado_workflow = self._activar_workflow_masivo(dry_run)
                self.resultados["workflow"] = resultado_workflow
                self._log_paso_completado("Activación de workflow")
            else:
                logger.info("\n  PASO 6: Saltando workflow (deshabilitado)")

            # PASO 7: Generar reporte ejecutivo
            logger.info("\n PASO 7: Generando reporte ejecutivo...")
            estado_final = self._verificar_estado_sistema()
            self.resultados["estado_final"] = estado_final
            self.resultados["fin"] = datetime.now()
            self.resultados["duracion_segundos"] = (
                self.resultados["fin"] - self.resultados["inicio"]
            ).total_seconds()
            self._log_paso_completado("Generación de reporte")

            # Commit final si no es dry_run
            if not dry_run:
                self.db.commit()
                logger.info("\n Cambios guardados en la base de datos")
            else:
                self.db.rollback()
                logger.info("\n DRY RUN: Cambios revertidos (modo simulación)")

            return self._generar_reporte_exitoso()

        except Exception as e:
            logger.error(f"\n ERROR CRÍTICO: {str(e)}")
            self.db.rollback()
            self.resultados["errores"].append({
                "tipo": "error_critico",
                "mensaje": str(e),
                "timestamp": datetime.now()
            })
            return self._generar_reporte_error([str(e)])

    def _verificar_estado_sistema(self) -> Dict[str, Any]:
        """Verifica el estado actual del sistema."""
        estado = {}

        # Contar facturas
        estado["total_facturas"] = self.db.query(func.count(Factura.id)).scalar() or 0
        estado["facturas_con_periodo"] = self.db.query(func.count(Factura.id)).filter(
            Factura.periodo_factura != None
        ).scalar() or 0
        estado["facturas_sin_periodo"] = estado["total_facturas"] - estado["facturas_con_periodo"]

        # Contar presupuesto
        estado["lineas_presupuesto"] = self.db.query(func.count(LineaPresupuesto.id)).scalar() or 0
        estado["ejecuciones_presupuestales"] = self.db.query(func.count(EjecucionPresupuestal.id)).scalar() or 0

        # Contar asignaciones
        estado["asignaciones_nit"] = self.db.query(func.count(AsignacionNitResponsable.id)).scalar() or 0
        estado["asignaciones_activas"] = self.db.query(func.count(AsignacionNitResponsable.id)).filter(
            AsignacionNitResponsable.activo == True
        ).scalar() or 0

        # Contar workflows
        estado["workflows_creados"] = self.db.query(func.count(WorkflowAprobacionFactura.id)).scalar() or 0

        logger.info(f"    Facturas totales: {estado['total_facturas']}")
        logger.info(f"    Líneas de presupuesto: {estado['lineas_presupuesto']}")
        logger.info(f"    Ejecuciones presupuestales: {estado['ejecuciones_presupuestales']}")
        logger.info(f"    Asignaciones NIT-Responsable: {estado['asignaciones_nit']}")
        logger.info(f"    Workflows creados: {estado['workflows_creados']}")

        return estado

    def _validar_prerequisitos(
        self,
        archivo_presupuesto: Optional[str],
        responsable_id: int
    ) -> Dict[str, Any]:
        """Valida que se cumplan los pre-requisitos."""
        errores = []

        # Validar que exista al menos un responsable
        from app.models.responsable import Responsable
        responsable = self.db.query(Responsable).filter(Responsable.id == responsable_id).first()
        if not responsable:
            errores.append(f"Responsable con ID {responsable_id} no existe")

        # Validar archivo de presupuesto si se proporcionó
        if archivo_presupuesto:
            if not Path(archivo_presupuesto).exists():
                errores.append(f"Archivo de presupuesto no encontrado: {archivo_presupuesto}")

        if errores:
            logger.error("    Pre-requisitos no cumplidos:")
            for error in errores:
                logger.error(f"      - {error}")
            return {"valido": False, "errores": errores}

        logger.info("    Todos los pre-requisitos cumplidos")
        return {"valido": True, "errores": []}

    def _importar_presupuesto(
        self,
        archivo: str,
        año_fiscal: int,
        responsable_id: int,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Importa el presupuesto desde Excel."""
        try:
            importer = ExcelPresupuestoImporter(self.db)

            # Configurar mapeo de columnas según tu Excel
            # AJUSTAR SEGÚN LA ESTRUCTURA REAL DE TU EXCEL
            resultado = importer.importar_desde_excel(
                file_path=archivo,
                año_fiscal=año_fiscal,
                responsable_id=responsable_id,
                categoria="TI",
                creado_por="SISTEMA_INICIALIZACION",
                hoja=0,
                fila_inicio=7
            )

            logger.info(f"    Líneas creadas: {resultado.get('lineas_creadas', 0)}")
            logger.info(f"    Líneas actualizadas: {resultado.get('lineas_actualizadas', 0)}")

            if resultado.get("errores"):
                logger.warning(f"     Errores: {len(resultado['errores'])}")
                for error in resultado["errores"][:5]:
                    logger.warning(f"      - {error}")

            return resultado

        except Exception as e:
            logger.error(f"    Error en importación: {str(e)}")
            raise

    def _autoconfigurar_asignaciones(
        self,
        responsable_default_id: int,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Auto-configura asignaciones NIT-Responsable basándose en proveedores existentes."""
        from app.models.proveedor import Proveedor

        # Obtener todos los proveedores únicos desde la tabla Proveedores
        proveedores = self.db.query(Proveedor).filter(
            Proveedor.nit != None
        ).all()

        asignaciones_creadas = 0
        asignaciones_existentes = 0

        for proveedor in proveedores:
            # Verificar si ya existe asignación para este NIT
            existente = self.db.query(AsignacionNitResponsable).filter(
                AsignacionNitResponsable.nit == proveedor.nit
            ).first()

            if existente:
                asignaciones_existentes += 1
                continue

            # Crear asignación nueva
            if not dry_run:
                nueva_asignacion = AsignacionNitResponsable(
                    nit=proveedor.nit,
                    nombre_proveedor=proveedor.razon_social,
                    responsable_id=responsable_default_id,
                    area=proveedor.area or "General",  # Usar área del proveedor si existe
                    permitir_aprobacion_automatica=True,
                    requiere_revision_siempre=False,
                    monto_maximo_auto_aprobacion=Decimal("10000000"),  # $10M default
                    porcentaje_variacion_permitido=Decimal("5.0"),
                    activo=True,
                    creado_en=datetime.now(),
                    creado_por="SISTEMA_INICIALIZACION"
                )
                self.db.add(nueva_asignacion)
                asignaciones_creadas += 1

                logger.info(f"    Asignación creada: {proveedor.nit} - {proveedor.razon_social[:50]}")
            else:
                # En dry-run, solo contar
                asignaciones_creadas += 1
                logger.info(f"   [DRY-RUN] Asignación: {proveedor.nit} - {proveedor.razon_social[:50]}")

        if not dry_run:
            self.db.flush()

        logger.info(f"    Asignaciones creadas: {asignaciones_creadas}")
        logger.info(f"    Asignaciones existentes: {asignaciones_existentes}")

        return {
            "creadas": asignaciones_creadas,
            "existentes": asignaciones_existentes,
            "total": asignaciones_creadas + asignaciones_existentes
        }

    def _extraer_nit_de_texto(self, texto: str) -> Optional[str]:
        """Extrae NIT de un texto."""
        import re

        if not texto:
            return None

        # Buscar patrón NIT
        match = re.search(r'NIT[:\s]*(\d{9,10}[-]?\d?)', texto, re.IGNORECASE)
        if match:
            return match.group(1).replace('-', '')

        # Buscar solo números (9-10 dígitos)
        match = re.search(r'\b(\d{9,10})\b', texto)
        if match:
            return match.group(1)

        return None

    def _vincular_facturas_masivo(
        self,
        año_fiscal: int,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Vincula facturas existentes con líneas de presupuesto."""

        vinculador = AutoVinculador(self.db)

        resultado = vinculador.vincular_facturas_pendientes(
            año_fiscal=año_fiscal,
            umbral_confianza=75,  # 75% para ser más inclusivo en la inicial
            limite=None  # Todas las facturas
        )

        logger.info(f"    Total procesadas: {resultado['total_procesadas']}")
        logger.info(f"    Vinculadas exitosamente: {resultado['total_vinculadas']}")
        logger.info(f"     Sin vincular: {resultado['total_sin_vincular']}")

        if resultado['errores']:
            logger.warning(f"    Errores: {len(resultado['errores'])}")

        return resultado

    def _activar_workflow_masivo(self, dry_run: bool) -> Dict[str, Any]:
        """Activa workflow para facturas que aún no lo tienen."""

        # Obtener facturas sin workflow
        facturas_sin_workflow = self.db.query(Factura).filter(
            ~Factura.id.in_(
                self.db.query(WorkflowAprobacionFactura.factura_id)
            )
        ).limit(100).all()  # Procesar primeras 100

        servicio = WorkflowAutomaticoService(self.db)
        workflows_creados = 0
        errores = 0

        for factura in facturas_sin_workflow:
            try:
                if not dry_run:
                    resultado = servicio.procesar_factura_nueva(factura.id)
                    if resultado.get("exito") or resultado.get("workflow_id"):
                        workflows_creados += 1
                else:
                    workflows_creados += 1  # Simular
            except Exception as e:
                logger.error(f"    Error procesando factura {factura.id}: {str(e)}")
                errores += 1

        logger.info(f"    Workflows creados: {workflows_creados}")
        logger.info(f"    Errores: {errores}")

        return {
            "workflows_creados": workflows_creados,
            "errores": errores,
            "total_procesadas": len(facturas_sin_workflow)
        }

    def _log_paso_completado(self, paso: str):
        """Registra un paso completado."""
        self.resultados["pasos_completados"].append({
            "paso": paso,
            "timestamp": datetime.now()
        })
        logger.info(f"    {paso} completado")

    def _generar_reporte_exitoso(self) -> Dict[str, Any]:
        """Genera reporte de éxito."""
        logger.info("\n" + "=" * 80)
        logger.info(" INICIALIZACIÓN COMPLETADA EXITOSAMENTE")
        logger.info("=" * 80)
        logger.info(f"Duración total: {self.resultados['duracion_segundos']:.2f} segundos")
        logger.info(f"Pasos completados: {len(self.resultados['pasos_completados'])}")

        return {
            "exito": True,
            **self.resultados
        }

    def _generar_reporte_error(self, errores: List[str]) -> Dict[str, Any]:
        """Genera reporte de error."""
        logger.error("\n" + "=" * 80)
        logger.error(" INICIALIZACIÓN FALLIDA")
        logger.error("=" * 80)
        for error in errores:
            logger.error(f"   - {error}")

        return {
            "exito": False,
            "errores": errores,
            **self.resultados
        }
