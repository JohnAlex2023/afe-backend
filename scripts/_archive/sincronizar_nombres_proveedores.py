# -*- coding: utf-8 -*-
"""
Script para sincronizar nombres de proveedores en asignaciones existentes.

Proposito:
- Actualiza el campo nombre_proveedor en asignacion_nit_responsable
- Obtiene el nombre real (razon_social) de la tabla proveedores
- Aplica a todos los registros activos que tengan un NIT valido
"""

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.proveedor import Proveedor
from app.utils.logger import logger
from datetime import datetime


def sincronizar_nombres_proveedores():
    """
    Sincroniza todos los nombres de proveedores en asignaciones existentes.

    Logica:
    1. Obtener todas las asignaciones activas
    2. Para cada NIT, buscar el proveedor
    3. Si existe, actualizar nombre_proveedor con razon_social
    4. Registrar cambios en logs
    """
    db = SessionLocal()

    try:
        # PASO 1: Obtener todas las asignaciones activas
        asignaciones = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.activo == True
        ).all()

        logger.info(f"Iniciando sincronizacion de {len(asignaciones)} asignaciones activas")

        actualizadas = 0
        sin_cambios = 0
        sin_proveedor = 0
        errores = []

        for asignacion in asignaciones:
            try:
                # PASO 2: Buscar proveedor por NIT
                proveedor = db.query(Proveedor).filter(
                    Proveedor.nit == asignacion.nit
                ).first()

                if not proveedor:
                    logger.debug(f"No se encontro proveedor para NIT: {asignacion.nit}")
                    sin_proveedor += 1
                    continue

                nombre_nuevo = proveedor.razon_social
                nombre_actual = asignacion.nombre_proveedor

                # PASO 3: Actualizar solo si cambio
                if nombre_actual != nombre_nuevo:
                    asignacion.nombre_proveedor = nombre_nuevo
                    logger.debug(
                        f"NIT {asignacion.nit}: "
                        f"'{nombre_actual}' -> '{nombre_nuevo}'"
                    )
                    actualizadas += 1
                else:
                    sin_cambios += 1

            except Exception as e:
                errores.append(f"NIT {asignacion.nit}: {str(e)}")
                logger.error(f"Error procesando NIT {asignacion.nit}: {str(e)}")

        # PASO 4: Commit
        if actualizadas > 0:
            db.commit()
            logger.info(
                f"Sincronizacion completada: "
                f"{actualizadas} actualizadas, "
                f"{sin_cambios} sin cambios, "
                f"{sin_proveedor} sin proveedor"
            )
            if errores:
                logger.warning(f"Errores encontrados: {errores}")
        else:
            logger.info(
                f"Nada que actualizar: "
                f"{sin_cambios} sin cambios, "
                f"{sin_proveedor} sin proveedor"
            )

        return {
            "actualizadas": actualizadas,
            "sin_cambios": sin_cambios,
            "sin_proveedor": sin_proveedor,
            "errores": errores
        }

    except Exception as e:
        logger.error(f"Error critico en sincronizacion: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    resultado = sincronizar_nombres_proveedores()
    print("\n" + "="*60)
    print("RESULTADO DE SINCRONIZACION")
    print("="*60)
    print(f"Actualizadas:  {resultado['actualizadas']}")
    print(f"Sin cambios:   {resultado['sin_cambios']}")
    print(f"Sin proveedor: {resultado['sin_proveedor']}")
    print(f"Errores:       {len(resultado['errores'])}")
    if resultado['errores']:
        print("\nDetalles de errores:")
        for error in resultado['errores']:
            print(f"  - {error}")
    print("="*60)
