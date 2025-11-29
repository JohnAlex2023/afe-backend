#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simula exactamente lo que hace el endpoint /bulk-nit-config
para identificar dónde está el cuello de botella.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.email_config import NitConfiguracion
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.utils.nit_validator import NitValidator
import re

# Los 30 NITs para john.taimalp
NITS_JOHN = [
    "17343874", "47425554", "80818383", "800058607", "800136505",
    "800153993", "800185449", "822000582", "830042244", "830078515",
    "890903938", "900016757", "900032159", "900136505", "900156003",
    "900156470", "900266612", "900331794", "900352786", "900359573",
    "900374230", "900389156", "900399741", "900478383", "900537021",
    "900872496", "901261003", "901302708", "901701856", "901732395"
]


def simular_bulk_nit_config(db: Session):
    """Simula el endpoint /bulk-nit-config paso por paso."""
    print("=" * 120)
    print("SIMULACION: /bulk-nit-config endpoint")
    print("=" * 120)

    # Convertir a string como si viniera del frontend
    nits_raw_text = ",".join(NITS_JOHN)
    print(f"\n1. ENTRADA (como vendría del frontend):")
    print(f"   {nits_raw_text[:80]}...")

    # PASO 1: Parsear el texto de NITs (igual que endpoint)
    print(f"\n2. PASO 1: Parsear texto de NITs")
    nits_raw = re.split(r'[,\n\t\r;]', nits_raw_text)
    nits_procesados_raw = [nit.strip() for nit in nits_raw if nit.strip()]
    print(f"   Encontrados: {len(nits_procesados_raw)} NITs")

    # PASO 2: Normalizar NITs (igual que endpoint)
    print(f"\n3. PASO 2: Normalizar NITs")
    nits_procesados = []
    nits_normalizacion_errores = []

    for nit_raw in nits_procesados_raw:
        es_valido, nit_normalizado_o_error = NitValidator.validar_nit(nit_raw)
        if es_valido:
            nits_procesados.append(nit_normalizado_o_error)
            print(f"   OK: {nit_raw:15} -> {nit_normalizado_o_error}")
        else:
            nits_normalizacion_errores.append((nit_raw, nit_normalizado_o_error))
            print(f"   ERROR: {nit_raw:15} -> {nit_normalizado_o_error}")

    print(f"\n   Total normalizados: {len(nits_procesados)}")
    print(f"   Total con errores: {len(nits_normalizacion_errores)}")

    if nits_normalizacion_errores:
        print(f"\n   FRENAZO: Hay errores de normalización, no continúa")
        return False

    # PASO 3: VALIDACIÓN - Verificar que los NITs existan en nit_configuracion
    print(f"\n4. PASO 3: Validar que NITs existen en nit_configuracion (ACTIVOS)")
    nits_invalidos = []
    nits_encontrados = []

    for nit_normalizado in nits_procesados:
        # ESTA ES LA QUERY EXACTA DEL ENDPOINT (líneas 1038-1041)
        nit_config = db.query(NitConfiguracion).filter(
            NitConfiguracion.nit == nit_normalizado,
            NitConfiguracion.activo == True
        ).first()

        if nit_config:
            nits_encontrados.append((nit_normalizado, nit_config.id, nit_config.cuenta_correo_id))
            print(f"   ENCONTRADO: {nit_normalizado:18} (id={nit_config.id}, cuenta_id={nit_config.cuenta_correo_id})")
        else:
            nits_invalidos.append(nit_normalizado)
            print(f"   NO ENCONTRADO: {nit_normalizado:18}")

    print(f"\n   Total encontrados: {len(nits_encontrados)}")
    print(f"   Total NO encontrados: {len(nits_invalidos)}")

    if nits_invalidos:
        print(f"\n   FRENAZO: {len(nits_invalidos)} NITs no están en nit_configuracion")
        print(f"   El endpoint RECHAZA aquí con HTTP 400")
        return False

    # PASO 4: Si llegamos aquí, podemos procesar asignaciones
    print(f"\n5. PASO 4: Procesar asignaciones")
    print(f"   (En este punto, los 30 NITs podrían ser asignados)")
    return True


def main():
    print("\n>> Iniciando simulación\n")
    db = SessionLocal()
    try:
        exito = simular_bulk_nit_config(db)

        print("\n" + "=" * 120)
        print("RESULTADO FINAL:")
        print("=" * 120)
        if exito:
            print("\nEXITO: El endpoint debería poder crear las asignaciones")
        else:
            print("\nERROR: El endpoint rechazará la solicitud en la validación")
    except Exception as e:
        print(f"\nEXCEPCION: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
