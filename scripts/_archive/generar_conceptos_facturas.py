"""
Script para generar conceptos para todas las facturas existentes.

Este script:
1. Lee los items de cada factura
2. Genera un concepto_principal a partir de las descripciones de items
3. Normaliza el concepto (quita stopwords, lowercase)
4. Genera el hash MD5 del concepto normalizado

Uso:
    python -m scripts.generar_conceptos_facturas
"""
import sys
from pathlib import Path
import hashlib
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.factura import Factura
from app.models.factura_item import FacturaItem


# Stopwords en español para normalización
STOP_WORDS = {
    'de', 'la', 'el', 'en', 'y', 'a', 'por', 'para', 'con', 'sin',
    'del', 'al', 'los', 'las', 'un', 'una', 'unos', 'unas',
    'es', 'son', 'fue', 'ser', 'estar', 'haber'
}


def normalizar_concepto(texto: str) -> str:
    """
    Normaliza un concepto removiendo stopwords y caracteres especiales.
    """
    if not texto:
        return ""

    # Lowercase
    texto = texto.lower()

    # Remover caracteres especiales (mantener letras, números y espacios)
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)

    # Remover stopwords
    palabras = texto.split()
    palabras_filtradas = [p for p in palabras if p and p not in STOP_WORDS and len(p) > 2]

    # Unir con espacios
    resultado = ' '.join(palabras_filtradas)

    return resultado.strip()


def generar_concepto_desde_items(factura: Factura) -> str:
    """
    Genera el concepto principal de una factura desde sus items.

    Estrategia:
    - Si tiene items: concatenar descripciones únicas (max 3)
    - Si no tiene items: usar número de factura
    """
    if not factura.items or len(factura.items) == 0:
        # No tiene items, usar numero de factura
        return f"Factura {factura.numero_factura}"

    # Obtener descripciones únicas de los primeros 3 items
    descripciones = []
    for item in factura.items[:3]:  # Solo primeros 3 items
        if item.descripcion and item.descripcion.strip():
            desc = item.descripcion.strip()[:100]  # Max 100 chars por item
            if desc not in descripciones:
                descripciones.append(desc)

    if descripciones:
        concepto = " | ".join(descripciones)
    else:
        concepto = f"Factura {factura.numero_factura}"

    # Limitar longitud total
    if len(concepto) > 500:
        concepto = concepto[:497] + "..."

    return concepto


def generar_hash_concepto(concepto_normalizado: str) -> str:
    """
    Genera hash MD5 del concepto normalizado.
    """
    if not concepto_normalizado:
        return ""

    return hashlib.md5(concepto_normalizado.encode('utf-8')).hexdigest()


def procesar_facturas(db: Session):
    """
    Procesa todas las facturas sin concepto y genera sus conceptos.
    """
    print("\n" + "=" * 80)
    print("GENERACION DE CONCEPTOS PARA FACTURAS")
    print("=" * 80)

    # Obtener facturas sin concepto
    facturas_sin_concepto = db.query(Factura).filter(
        Factura.concepto_principal.is_(None)
    ).all()

    total_facturas = len(facturas_sin_concepto)
    print(f"\nFacturas a procesar: {total_facturas}")

    if total_facturas == 0:
        print("\n[INFO] Todas las facturas ya tienen concepto generado")
        return

    print("\nGenerando conceptos...")
    print("-" * 80)

    procesadas = 0
    con_items = 0
    sin_items = 0

    for factura in facturas_sin_concepto:
        try:
            # Generar concepto principal
            concepto_principal = generar_concepto_desde_items(factura)

            # Normalizar concepto
            concepto_normalizado = normalizar_concepto(concepto_principal)

            # Generar hash
            concepto_hash = generar_hash_concepto(concepto_normalizado)

            # Actualizar factura
            factura.concepto_principal = concepto_principal
            factura.concepto_normalizado = concepto_normalizado
            factura.concepto_hash = concepto_hash

            # Estadísticas
            if factura.items and len(factura.items) > 0:
                con_items += 1
            else:
                sin_items += 1

            procesadas += 1

            # Mostrar progreso cada 50 facturas
            if procesadas % 50 == 0:
                print(f"  Procesadas: {procesadas}/{total_facturas}")
                db.commit()  # Commit intermedio

        except Exception as e:
            print(f"\n[ERROR] Factura {factura.id}: {e}")
            continue

    # Commit final
    db.commit()

    print("\n" + "=" * 80)
    print("RESUMEN:")
    print("=" * 80)
    print(f"Total procesadas: {procesadas}")
    print(f"Facturas con items: {con_items}")
    print(f"Facturas sin items: {sin_items}")

    # Mostrar ejemplos
    print("\nEJEMPLOS DE CONCEPTOS GENERADOS:")
    print("-" * 80)

    ejemplos = db.query(Factura).filter(
        Factura.concepto_principal.isnot(None)
    ).limit(5).all()

    for ej in ejemplos:
        print(f"\nFactura #{ej.numero_factura}")
        print(f"  Proveedor: {ej.proveedor.razon_social if ej.proveedor else 'N/A'}")
        print(f"  Items: {len(ej.items)}")
        print(f"  Concepto: {ej.concepto_principal[:80]}...")
        print(f"  Normalizado: {ej.concepto_normalizado[:60]}...")
        print(f"  Hash: {ej.concepto_hash}")


def main():
    """Funcion principal."""
    db = SessionLocal()
    try:
        procesar_facturas(db)
        print("\n[OK] Proceso completado\n")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
