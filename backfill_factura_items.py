"""
Script de Backfill - Poblar tabla factura_items desde facturas existentes.

Este script procesa facturas existentes en la BD que no tienen items,
extrae los items de sus XMLs originales, y los guarda en factura_items.

Nivel: Enterprise
Autor: Sistema AFE
Fecha: 2025-10-09

Uso:
    # Modo prueba (primeras 10 facturas)
    python backfill_factura_items.py --test

    # Procesar todas las facturas
    python backfill_factura_items.py --all

    # Procesar facturas específicas por ID
    python backfill_factura_items.py --ids 1,2,3,4,5

    # Procesar por rango de fechas
    python backfill_factura_items.py --desde 2024-01-01 --hasta 2024-12-31

    # Procesar por proveedor
    python backfill_factura_items.py --proveedor-id 123
"""

import argparse
import sys
from datetime import datetime, date
from typing import List, Optional
from pathlib import Path

# Ajustar path para importar módulos
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "invoice_extractor"))

from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.factura_item import FacturaItem
from app.services.factura_items_service import FacturaItemsService

# Importar extractor del módulo invoice_extractor
try:
    from src.extraction.items_extractor import ItemsExtractor
    from lxml import etree
except ImportError as e:
    print(f"❌ Error: No se pudo importar invoice_extractor")
    print(f"   Asegúrate de que está en: C:\\Users\\john.taimalp\\ODO\\invoice_extractor")
    print(f"   Error: {e}")
    sys.exit(1)


class BackfillFacturaItems:
    """
    Servicio para poblar tabla factura_items desde facturas existentes.
    """

    def __init__(self, dry_run: bool = False):
        """
        Inicializa el servicio de backfill.

        Args:
            dry_run: Si es True, no guarda en BD (solo simula)
        """
        self.db = SessionLocal()
        self.items_service = FacturaItemsService(self.db)
        self.items_extractor = ItemsExtractor()
        self.dry_run = dry_run

        # Estadísticas
        self.stats = {
            'facturas_procesadas': 0,
            'facturas_con_items': 0,
            'facturas_sin_xml': 0,
            'total_items_creados': 0,
            'errores': 0
        }

    def procesar_facturas(
        self,
        facturas: List[Factura],
        xml_base_path: Optional[Path] = None
    ) -> dict:
        """
        Procesa una lista de facturas para extraer sus items.

        Args:
            facturas: Lista de facturas a procesar
            xml_base_path: Path base donde están los XMLs

        Returns:
            Dict con estadísticas del proceso
        """
        print("=" * 80)
        print("BACKFILL DE ITEMS DE FACTURAS")
        print("=" * 80)
        print(f"   Facturas a procesar: {len(facturas)}")
        print(f"   Modo: {'DRY RUN (simulación)' if self.dry_run else 'PRODUCCIÓN'}")
        print("=" * 80)

        for idx, factura in enumerate(facturas, 1):
            print(f"\n[{idx}/{len(facturas)}] Procesando factura {factura.numero_factura}...")

            try:
                # Verificar si ya tiene items
                items_existentes = self.db.query(FacturaItem).filter(
                    FacturaItem.factura_id == factura.id
                ).count()

                if items_existentes > 0:
                    print(f"   [INFO] Ya tiene {items_existentes} items, omitiendo...")
                    continue

                # Buscar XML
                xml_path = self._buscar_xml_factura(factura, xml_base_path)

                if not xml_path or not xml_path.exists():
                    print("   [WARN] XML no encontrado")
                    self.stats['facturas_sin_xml'] += 1
                    continue

                # Extraer items del XML
                items_data = self._extraer_items_de_xml(xml_path)

                if not items_data:
                    print(f"   [WARN] No se pudieron extraer items del XML: {xml_path.name}")
                    self.stats['errores'] += 1
                    continue

                print(f"   [OK] {len(items_data)} items extraidos del XML")

                # Guardar items en BD
                if not self.dry_run:
                    resultado = self.items_service.crear_items_desde_extractor(
                        factura.id,
                        items_data
                    )

                    if resultado['exito']:
                        print(f"   [SAVE] {resultado['items_creados']} items guardados en BD")
                        self.stats['total_items_creados'] += resultado['items_creados']
                        self.stats['facturas_con_items'] += 1
                    else:
                        print(f"   [ERROR] Error guardando items: {resultado.get('mensaje')}")
                        self.stats['errores'] += 1
                else:
                    print(f"   [DRY-RUN] Se guardarian {len(items_data)} items")
                    self.stats['total_items_creados'] += len(items_data)
                    self.stats['facturas_con_items'] += 1

                self.stats['facturas_procesadas'] += 1

            except Exception as e:
                print(f"   [ERROR] Error procesando factura: {str(e)}")
                self.stats['errores'] += 1
                import traceback
                traceback.print_exc()

        # Mostrar resumen final
        self._mostrar_resumen()

        return self.stats

    def _buscar_xml_factura(
        self,
        factura: Factura,
        xml_base_path: Optional[Path]
    ) -> Optional[Path]:
        """
        Busca el archivo XML de una factura.

        Estrategias de búsqueda:
        1. Buscar en xml_file_path si existe en la factura
        2. Buscar recursivamente en adjuntos/ por NIT de proveedor

        Args:
            factura: Factura a buscar
            xml_base_path: Path base de búsqueda

        Returns:
            Path al XML o None
        """
        # Estrategia 1: Si la factura tiene xml_file_path guardado
        xml_file_path = getattr(factura, 'xml_file_path', None)
        if xml_file_path and Path(xml_file_path).exists():
            return Path(xml_file_path)

        # Estrategia 2: Buscar en adjuntos del invoice_extractor
        # La estructura es: adjuntos/{NIT_PROVEEDOR}/*.xml
        base_adjuntos = xml_base_path if xml_base_path else Path("C:/Users/john.taimalp/ODO/invoice_extractor/adjuntos")

        if base_adjuntos.exists() and factura.proveedor:
            # Buscar en directorio del proveedor (quitar dígito de verificación si existe)
            nit = str(factura.proveedor.nit).split('-')[0]  # Quitar -X
            proveedor_dir = base_adjuntos / nit

            if proveedor_dir.exists():
                # Buscar todos los XMLs en ese directorio
                for xml_file in proveedor_dir.glob("*.xml"):
                    # Verificar si el CUFE coincide leyendo el contenido
                    try:
                        from lxml import etree
                        tree = etree.parse(str(xml_file))
                        root = tree.getroot()

                        # Buscar CUFE en el XML
                        ns = {'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'}
                        cufe_elem = root.find('.//cbc:UUID', namespaces=ns)

                        if cufe_elem is not None and cufe_elem.text == factura.cufe:
                            return xml_file

                    except Exception:
                        continue

        return None

    def _extraer_items_de_xml(self, xml_path: Path) -> Optional[List[dict]]:
        """
        Extrae items del archivo XML.

        Args:
            xml_path: Path al archivo XML

        Returns:
            Lista de dicts con items o None
        """
        try:
            # Parsear XML
            tree = etree.parse(str(xml_path))
            root = tree.getroot()

            # Extraer items con el método enterprise
            items_data = self.items_extractor.extract_all_items_completo(root)

            if items_data and len(items_data) > 0:
                return items_data
            else:
                print(f"   [DEBUG] extract_all_items_completo retorno: {items_data}")
                return None

        except Exception as e:
            print(f"   [ERROR] Error parseando XML: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _mostrar_resumen(self):
        """Muestra resumen final del backfill."""
        print("\n" + "=" * 80)
        print("RESUMEN DEL BACKFILL")
        print("=" * 80)
        print(f"   Facturas procesadas:        {self.stats['facturas_procesadas']}")
        print(f"   Facturas con items creados: {self.stats['facturas_con_items']}")
        print(f"   Facturas sin XML:           {self.stats['facturas_sin_xml']}")
        print(f"   Total items creados:        {self.stats['total_items_creados']}")
        print(f"   Errores:                    {self.stats['errores']}")

        if self.stats['facturas_con_items'] > 0:
            promedio = self.stats['total_items_creados'] / self.stats['facturas_con_items']
            print(f"   Promedio items/factura:     {promedio:.1f}")

        print("=" * 80)

    def close(self):
        """Cierra la sesión de BD."""
        self.db.close()


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Backfill de items de facturas desde XMLs"
    )

    # Modos de ejecución
    parser.add_argument(
        '--test',
        action='store_true',
        help='Modo prueba: procesa solo 10 facturas'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Procesar TODAS las facturas'
    )

    parser.add_argument(
        '--ids',
        type=str,
        help='IDs de facturas separados por coma: 1,2,3'
    )

    parser.add_argument(
        '--desde',
        type=str,
        help='Fecha desde (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--hasta',
        type=str,
        help='Fecha hasta (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--proveedor-id',
        type=int,
        help='ID del proveedor'
    )

    parser.add_argument(
        '--xml-path',
        type=str,
        help='Path base donde están los XMLs'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular sin guardar en BD'
    )

    args = parser.parse_args()

    # Obtener facturas según filtros
    db = SessionLocal()
    query = db.query(Factura)

    if args.ids:
        # Procesar IDs específicos
        ids = [int(x.strip()) for x in args.ids.split(',')]
        query = query.filter(Factura.id.in_(ids))

    elif args.desde or args.hasta:
        # Procesar por rango de fechas
        if args.desde:
            fecha_desde = datetime.strptime(args.desde, '%Y-%m-%d').date()
            query = query.filter(Factura.fecha_emision >= fecha_desde)

        if args.hasta:
            fecha_hasta = datetime.strptime(args.hasta, '%Y-%m-%d').date()
            query = query.filter(Factura.fecha_emision <= fecha_hasta)

    elif args.proveedor_id:
        # Procesar por proveedor
        query = query.filter(Factura.proveedor_id == args.proveedor_id)

    elif args.test:
        # Modo prueba: primeras 10
        query = query.limit(10)

    elif not args.all:
        # Si no especificó nada, modo prueba por defecto
        print("[WARN] No especificaste modo. Usando --test (10 facturas)")
        query = query.limit(10)

    # Obtener facturas
    facturas = query.all()

    if not facturas:
        print("[ERROR] No se encontraron facturas con los filtros especificados")
        db.close()
        return

    # Ejecutar backfill
    xml_base_path = Path(args.xml_path) if args.xml_path else None

    backfill = BackfillFacturaItems(dry_run=args.dry_run)

    try:
        backfill.procesar_facturas(facturas, xml_base_path)
    finally:
        backfill.close()
        db.close()

    print("\n[OK] Backfill completado!")


if __name__ == "__main__":
    main()
