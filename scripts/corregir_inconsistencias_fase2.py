"""
Script de corrección de inconsistencias detectadas en Fase 1.

ESTRATEGIA DE CORRECCIÓN (Nivel Senior):
===========================================

PRINCIPIO FUNDAMENTAL:
- Valores del XML son la VERDAD ABSOLUTA
- Valores calculados (subtotal, IVA) son DERIVADOS
- Si hay inconsistencia → recalcular derivados desde valores oficiales

FACTURAS:
- total_a_pagar (del XML <PayableAmount>) es inmutable
- subtotal e iva se recalculan si no cuadran
- Asume IVA del 19% (estándar Colombia)

ITEMS:
- item.total (del XML <LineExtensionAmount>) es inmutable
- item.subtotal se recalcula desde total - impuestos
- Validación contra cantidad × precio

Nivel: Fortune 500 Data Quality Assurance
Autor: Equipo de Desarrollo Senior
Fecha: 2025-10-19
"""

import sys
import logging
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Tuple
import csv

sys.path.insert(0, '.')

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.factura_item import FacturaItem

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
IVA_COLOMBIA = Decimal('0.19')  # 19%
TOLERANCIA = Decimal('0.01')    # 1 centavo


class CorrectorInconsistencias:
    """
    Corrector profesional de inconsistencias en datos.

    Genera reportes detallados de todos los cambios realizados.
    """

    def __init__(self, db: Session):
        self.db = db
        self.reporte_cambios: List[Dict] = []

    def corregir_facturas(self) -> Dict[str, int]:
        """
        Corrige inconsistencias en facturas.

        Returns:
            Dict con estadísticas de corrección
        """
        logger.info("\n" + "="*80)
        logger.info("CORRIGIENDO INCONSISTENCIAS EN FACTURAS")
        logger.info("="*80)

        facturas = self.db.query(Factura).all()
        stats = {
            'analizadas': len(facturas),
            'inconsistentes': 0,
            'corregidas': 0,
            'errores': 0
        }

        for factura in facturas:
            try:
                if factura.tiene_inconsistencia_total:
                    self._corregir_factura_individual(factura)
                    stats['inconsistentes'] += 1
                    stats['corregidas'] += 1
            except Exception as e:
                logger.error(f"Error corrigiendo factura {factura.id}: {e}")
                stats['errores'] += 1

        # Commit de cambios
        if stats['corregidas'] > 0:
            self.db.commit()
            logger.info(f"\n✓ {stats['corregidas']} facturas corregidas y guardadas")

        return stats

    def _corregir_factura_individual(self, factura: Factura):
        """
        Corrige una factura individual.

        Estrategia:
        1. total_a_pagar es inmutable (viene del XML)
        2. Calcular subtotal = total_a_pagar / (1 + IVA)
        3. Calcular iva = total_a_pagar - subtotal
        """
        # Valores originales
        total_original = factura.total_a_pagar
        subtotal_antes = factura.subtotal
        iva_antes = factura.iva

        # Calcular valores correctos
        if total_original and total_original > 0:
            # Calcular subtotal e IVA desde total
            subtotal_correcto = round(
                total_original / (Decimal('1') + IVA_COLOMBIA),
                2
            )
            iva_correcto = total_original - subtotal_correcto

            # Aplicar corrección
            factura.subtotal = subtotal_correcto
            factura.iva = iva_correcto

            # Registrar cambio
            diferencia_subtotal = abs(subtotal_correcto - (subtotal_antes or 0))
            diferencia_iva = abs(iva_correcto - (iva_antes or 0))

            logger.info(
                f"Factura {factura.numero_factura} (ID: {factura.id}):\n"
                f"  Total (inmutable):  ${total_original:,.2f}\n"
                f"  Subtotal: ${subtotal_antes or 0:,.2f} → ${subtotal_correcto:,.2f} "
                f"(Δ ${diferencia_subtotal:,.2f})\n"
                f"  IVA:      ${iva_antes or 0:,.2f} → ${iva_correcto:,.2f} "
                f"(Δ ${diferencia_iva:,.2f})"
            )

            self.reporte_cambios.append({
                'tipo': 'factura',
                'id': factura.id,
                'numero_factura': factura.numero_factura,
                'total_inmutable': float(total_original),
                'subtotal_antes': float(subtotal_antes or 0),
                'subtotal_despues': float(subtotal_correcto),
                'iva_antes': float(iva_antes or 0),
                'iva_despues': float(iva_correcto),
                'diferencia_subtotal': float(diferencia_subtotal),
                'diferencia_iva': float(diferencia_iva)
            })

    def corregir_items(self) -> Dict[str, int]:
        """
        Corrige inconsistencias en items de facturas.

        Returns:
            Dict con estadísticas de corrección
        """
        logger.info("\n" + "="*80)
        logger.info("CORRIGIENDO INCONSISTENCIAS EN ITEMS")
        logger.info("="*80)

        items = self.db.query(FacturaItem).all()
        stats = {
            'analizados': len(items),
            'inconsistentes_subtotal': 0,
            'inconsistentes_total': 0,
            'corregidos': 0,
            'errores': 0
        }

        for item in items:
            try:
                tiene_error_subtotal = item.tiene_inconsistencia_subtotal
                tiene_error_total = item.tiene_inconsistencia_total

                if tiene_error_subtotal or tiene_error_total:
                    self._corregir_item_individual(item)

                    if tiene_error_subtotal:
                        stats['inconsistentes_subtotal'] += 1
                    if tiene_error_total:
                        stats['inconsistentes_total'] += 1

                    stats['corregidos'] += 1

            except Exception as e:
                logger.error(f"Error corrigiendo item {item.id}: {e}")
                stats['errores'] += 1

        # Commit de cambios
        if stats['corregidos'] > 0:
            self.db.commit()
            logger.info(f"\n✓ {stats['corregidos']} items corregidos y guardados")

        return stats

    def _corregir_item_individual(self, item: FacturaItem):
        """
        Corrige un item individual.

        Estrategia:
        1. item.total es inmutable (viene del XML)
        2. Calcular subtotal = total - impuestos
        3. Validar contra cantidad × precio (warning si no cuadra)
        """
        # Valores originales
        total_original = item.total
        subtotal_antes = item.subtotal
        impuestos = item.total_impuestos or Decimal('0')

        # Calcular subtotal correcto
        subtotal_correcto = total_original - impuestos

        # Validación adicional: ¿cuadra con cantidad × precio?
        if item.cantidad and item.precio_unitario:
            descuento = item.descuento_valor or Decimal('0')
            subtotal_esperado = (item.cantidad * item.precio_unitario) - descuento

            if abs(subtotal_correcto - subtotal_esperado) > Decimal('1.00'):
                logger.warning(
                    f"    Item {item.id} (Factura {item.factura_id}): "
                    f"Subtotal calculado ${subtotal_correcto} != "
                    f"Cantidad×Precio ${subtotal_esperado} (diferencia significativa)"
                )

        # Aplicar corrección
        item.subtotal = subtotal_correcto

        # Registrar cambio
        diferencia = abs(subtotal_correcto - (subtotal_antes or 0))

        if diferencia > TOLERANCIA:
            logger.info(
                f"Item {item.id} (Factura {item.factura_id}, Línea {item.numero_linea}):\n"
                f"  Total (inmutable): ${total_original:,.2f}\n"
                f"  Impuestos:         ${impuestos:,.2f}\n"
                f"  Subtotal: ${subtotal_antes or 0:,.2f} → ${subtotal_correcto:,.2f} "
                f"(Δ ${diferencia:,.2f})"
            )

            self.reporte_cambios.append({
                'tipo': 'item',
                'id': item.id,
                'factura_id': item.factura_id,
                'numero_linea': item.numero_linea,
                'descripcion': item.descripcion[:50],
                'total_inmutable': float(total_original),
                'impuestos': float(impuestos),
                'subtotal_antes': float(subtotal_antes or 0),
                'subtotal_despues': float(subtotal_correcto),
                'diferencia': float(diferencia)
            })

    def generar_reporte_csv(self, filename: str = None):
        """Genera reporte CSV de todos los cambios."""
        if not filename:
            filename = f'reporte_correcciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        if not self.reporte_cambios:
            logger.info("\nNo hay cambios para reportar")
            return

        # Separar facturas e items
        cambios_facturas = [c for c in self.reporte_cambios if c['tipo'] == 'factura']
        cambios_items = [c for c in self.reporte_cambios if c['tipo'] == 'item']

        # Reporte de facturas
        if cambios_facturas:
            filename_facturas = filename.replace('.csv', '_facturas.csv')
            with open(filename_facturas, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=cambios_facturas[0].keys())
                writer.writeheader()
                writer.writerows(cambios_facturas)
            logger.info(f"\n✓ Reporte de facturas guardado: {filename_facturas}")

        # Reporte de items
        if cambios_items:
            filename_items = filename.replace('.csv', '_items.csv')
            with open(filename_items, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=cambios_items[0].keys())
                writer.writeheader()
                writer.writerows(cambios_items)
            logger.info(f"✓ Reporte de items guardado: {filename_items}")


def main():
    """Ejecuta corrección completa de inconsistencias."""
    print("\n" + "="*80)
    print("FASE 2.1: CORRECCIÓN DE INCONSISTENCIAS")
    print("Sistema AFE Backend - Nivel Enterprise")
    print("="*80)

    # Confirmar ejecución
    print("\n  ADVERTENCIA:")
    print("Este script modificará datos en la base de datos.")
    print("Asegúrate de tener un backup antes de continuar.")
    print("\nEstrategia:")
    print("- Valores del XML (total_a_pagar, item.total) son inmutables")
    print("- Valores derivados (subtotal, iva) se recalculan")
    print("- Se genera reporte CSV de todos los cambios")

    respuesta = input("\n¿Continuar? (si/no): ")
    if respuesta.lower() != 'si':
        print("\nCancelado por el usuario")
        return

    # Ejecutar correcciones
    db = SessionLocal()
    corrector = CorrectorInconsistencias(db)

    try:
        # Corregir facturas
        stats_facturas = corrector.corregir_facturas()

        # Corregir items
        stats_items = corrector.corregir_items()

        # Generar reportes
        corrector.generar_reporte_csv()

        # Resumen final
        print("\n" + "="*80)
        print("RESUMEN DE CORRECCIONES")
        print("="*80)
        print(f"\nFacturas:")
        print(f"  Analizadas:     {stats_facturas['analizadas']}")
        print(f"  Inconsistentes: {stats_facturas['inconsistentes']}")
        print(f"  Corregidas:     {stats_facturas['corregidas']}")
        print(f"  Errores:        {stats_facturas['errores']}")

        print(f"\nItems:")
        print(f"  Analizados:              {stats_items['analizados']}")
        print(f"  Inconsist. subtotal:     {stats_items['inconsistentes_subtotal']}")
        print(f"  Inconsist. total:        {stats_items['inconsistentes_total']}")
        print(f"  Corregidos:              {stats_items['corregidos']}")
        print(f"  Errores:                 {stats_items['errores']}")

        print("\n" + "="*80)
        print("✓ CORRECCIÓN COMPLETADA")
        print("="*80)
        print("\nPróximo paso: Validar con scripts/validar_integridad_datos.py")
        print("Debe retornar 0 inconsistencias\n")

    except Exception as e:
        logger.error(f"\n Error durante corrección: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
