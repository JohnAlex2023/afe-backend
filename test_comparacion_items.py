"""
Script de Prueba - Comparación Enterprise de Items de Facturas

Este script demuestra el nuevo sistema de comparación granular item por item.

Uso:
    python test_comparacion_items.py
"""

from app.db.session import SessionLocal
from app.services.item_normalizer import ItemNormalizerService
from app.services.comparador_items import ComparadorItemsService
from app.models.factura import Factura
from app.models.factura_item import FacturaItem


def test_normalizador():
    """Prueba el servicio de normalización de items."""
    print("=" * 80)
    print("TEST 1: SERVICIO DE NORMALIZACIÓN")
    print("=" * 80)

    normalizer = ItemNormalizerService()

    # Ejemplos de descripciones
    descripciones = [
        "Licencia Mensual Office 365 - Plan E3",
        "Servicio de Hosting AWS Premium",
        "Soporte Técnico 24/7",
        "Energía Eléctrica - Consumo Mensual",
        "Internet Fibra Óptica 100 Mbps"
    ]

    for desc in descripciones:
        resultado = normalizer.normalizar_item_completo(desc)
        print(f"\n📄 Original: {desc}")
        print(f"   Normalizado: {resultado['descripcion_normalizada']}")
        print(f"   Hash: {resultado['item_hash'][:16]}...")
        print(f"   Categoría: {resultado['categoria'] or 'N/A'}")
        print(f"   Recurrente: {'Sí' if resultado['es_recurrente'] else 'No'}")


def test_similitud():
    """Prueba la detección de similitud entre items."""
    print("\n" + "=" * 80)
    print("TEST 2: DETECCIÓN DE SIMILITUD")
    print("=" * 80)

    normalizer = ItemNormalizerService()

    # Pares de descripciones
    pares = [
        (
            "Hosting AWS Plan Premium Mensual",
            "Plan Premium de Hosting Amazon AWS - Mensual"
        ),
        (
            "Licencia Office 365",
            "Microsoft Office 365 License"
        ),
        (
            "Soporte Técnico",
            "Servicio de Internet"
        )
    ]

    for desc1, desc2 in pares:
        similares = normalizer.son_items_similares(desc1, desc2)
        similitud = normalizer.calcular_similitud(
            normalizer.normalizar_texto(desc1),
            normalizer.normalizar_texto(desc2)
        )

        print(f"\n🔍 Comparación:")
        print(f"   Item 1: {desc1}")
        print(f"   Item 2: {desc2}")
        print(f"   Similitud: {similitud:.2%}")
        print(f"   ¿Son similares?: {'✅ SÍ' if similares else '❌ NO'}")


def test_comparador_con_bd():
    """Prueba el comparador con datos reales de BD."""
    print("\n" + "=" * 80)
    print("TEST 3: COMPARADOR CON BASE DE DATOS")
    print("=" * 80)

    db = SessionLocal()

    try:
        # Buscar una factura con items
        factura = db.query(Factura).join(FacturaItem).first()

        if not factura:
            print("\n   ⚠️  No hay facturas con items en la BD.")
            print("   💡 Primero debes agregar items a las facturas usando el parser XML.")
            return

        print(f"\n📋 Factura: {factura.numero_factura}")
        print(f"   Proveedor: {factura.proveedor.razon_social if factura.proveedor else 'N/A'}")
        print(f"   Fecha: {factura.fecha_emision}")
        print(f"   Items: {len(factura.items)}")

        # Mostrar items
        print(f"\n   📦 Items de la factura:")
        for item in factura.items[:5]:  # Primeros 5
            print(f"      {item.numero_linea}. {item.descripcion[:50]}...")
            print(f"         Cantidad: {item.cantidad} × ${item.precio_unitario:,.2f} = ${item.total:,.2f}")

        # Ejecutar comparador
        print(f"\n🔍 Ejecutando comparación vs histórico...")

        comparador = ComparadorItemsService(db)
        resultado = comparador.comparar_factura_vs_historial(factura.id)

        print(f"\n📊 RESULTADO DE LA COMPARACIÓN:")
        print(f"   Items analizados: {resultado['items_analizados']}")
        print(f"   ✅ Items OK: {resultado['items_ok']}")
        print(f"   ⚠️  Items con alertas: {resultado['items_con_alertas']}")
        print(f"   🆕 Items nuevos: {resultado['nuevos_items_count']}")
        print(f"   📈 Confianza: {resultado['confianza']:.1f}%")
        print(f"   🎯 Recomendación: {resultado['recomendacion'].upper()}")

        # Mostrar alertas
        if resultado['alertas']:
            print(f"\n🚨 ALERTAS DETECTADAS:")
            for i, alerta in enumerate(resultado['alertas'][:5], 1):
                severidad_emoji = "🔴" if alerta['severidad'] == 'alta' else "🟡"
                print(f"\n   {severidad_emoji} Alerta {i} ({alerta['severidad'].upper()}):")
                print(f"      Tipo: {alerta['tipo']}")
                print(f"      Mensaje: {alerta['mensaje']}")
                if 'precio_actual' in alerta:
                    print(f"      Precio actual: ${alerta['precio_actual']:,.2f}")
                    print(f"      Precio esperado: ${alerta['precio_esperado']:,.2f}")

        # Mostrar items nuevos
        if resultado['nuevos_items']:
            print(f"\n🆕 ITEMS NUEVOS (sin historial):")
            for i, item_nuevo in enumerate(resultado['nuevos_items'][:3], 1):
                print(f"\n   {i}. {item_nuevo['descripcion'][:50]}...")
                print(f"      Total: ${item_nuevo['total_actual']:,.2f}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


def main():
    """Ejecuta todos los tests."""
    print("\n" + "="*80)
    print("🚀 SISTEMA ENTERPRISE DE COMPARACIÓN DE ITEMS")
    print("="*80)

    # Test 1: Normalización
    test_normalizador()

    # Test 2: Similitud
    test_similitud()

    # Test 3: Comparador con BD
    test_comparador_con_bd()

    print("\n" + "="*80)
    print("✅ TESTS COMPLETADOS")
    print("="*80)


if __name__ == "__main__":
    main()
