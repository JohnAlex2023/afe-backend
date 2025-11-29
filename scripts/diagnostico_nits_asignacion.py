#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico profundo: NITs en nit_configuracion vs asignacion_nit_responsable

Verifica:
1. Si los 30 NITs existen en nit_configuracion (activos/inactivos)
2. Si ya están asignados en asignacion_nit_responsable (activos/inactivos)
3. Identifica inconsistencias de caché o estado
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.email_config import NitConfiguracion, CuentaCorreo
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.utils.nit_validator import NitValidator

# Los 30 NITs para john.taimalp
NITS_JOHN = [
    "17343874", "47425554", "80818383", "800058607", "800136505",
    "800153993", "800185449", "822000582", "830042244", "830078515",
    "890903938", "900016757", "900032159", "900136505", "900156003",
    "900156470", "900266612", "900331794", "900352786", "900359573",
    "900374230", "900389156", "900399741", "900478383", "900537021",
    "900872496", "901261003", "901302708", "901701856", "901732395"
]


def diagnostico_completo(db: Session):
    """Diagnóstico profundo de NITs."""
    print("=" * 120)
    print("DIAGNOSTICO PROFUNDO: NITs en nit_configuracion vs asignacion_nit_responsable")
    print("=" * 120)
    print(f"\nAnalizando {len(NITS_JOHN)} NITs para john.taimalp\n")

    # Normalizar NITs
    nits_normalizados = {}
    for nit_raw in NITS_JOHN:
        es_valido, nit_norm = NitValidator.validar_nit(nit_raw)
        if es_valido:
            nits_normalizados[nit_raw] = nit_norm
        else:
            nits_normalizados[nit_raw] = f"ERROR: {nit_norm}"

    # Estadísticas
    nits_config_activos = 0
    nits_config_inactivos = 0
    nits_asignados_activos = 0
    nits_asignados_inactivos = 0
    nits_no_existen = 0
    inconsistencias = []

    print("\n" + "=" * 120)
    print("DETALLE POR NIT:")
    print("=" * 120)
    print(f"{'NIT Original':15} {'NIT Normalizado':18} {'En nit_config':15} {'En asignaciones':20} {'Estado':<40}")
    print("-" * 120)

    for nit_raw, nit_norm in nits_normalizados.items():
        if nit_norm.startswith("ERROR"):
            print(f"{nit_raw:15} {nit_norm:18} {'ERROR':15} {'-':20} {'Normalización fallida':<40}")
            nits_no_existen += 1
            inconsistencias.append((nit_raw, nit_norm))
            continue

        # Buscar en nit_configuracion
        nit_config = db.query(NitConfiguracion).filter(
            NitConfiguracion.nit == nit_norm
        ).first()

        # Buscar en asignacion_nit_responsable (cualquier responsable)
        nit_asignado = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.nit == nit_norm
        ).first()

        # Determinar estado
        estado_config = ""
        if nit_config:
            if nit_config.activo:
                nits_config_activos += 1
                estado_config = f"SI (activo, cuenta_id={nit_config.cuenta_correo_id})"
            else:
                nits_config_inactivos += 1
                estado_config = f"SI (INACTIVO, cuenta_id={nit_config.cuenta_correo_id})"
        else:
            nits_no_existen += 1
            estado_config = "NO"

        estado_asignacion = ""
        if nit_asignado:
            if nit_asignado.activo:
                nits_asignados_activos += 1
                estado_asignacion = f"SI (activo, resp_id={nit_asignado.responsable_id})"
            else:
                nits_asignados_inactivos += 1
                estado_asignacion = f"SI (INACTIVO, resp_id={nit_asignado.responsable_id})"
        else:
            estado_asignacion = "NO"

        # Detectar inconsistencias
        if nit_config and not nit_config.activo and nit_asignado:
            inconsistencias.append(
                (nit_raw, "NIT inactivo en nit_config pero asignado en asignaciones")
            )

        estado_final = f"{estado_config} | {estado_asignacion}"

        # Imprimir línea
        print(f"{nit_raw:15} {nit_norm:18} {('SI' if nit_config else 'NO'):15} {('SI' if nit_asignado else 'NO'):20} {estado_final:<40}")

    # Resumen
    print("\n" + "=" * 120)
    print("RESUMEN:")
    print("=" * 120)
    print(f"\nNIT CONFIGURACION:")
    print(f"  - Activos:     {nits_config_activos}/30")
    print(f"  - Inactivos:   {nits_config_inactivos}/30")
    print(f"  - No existen:  {nits_no_existen}/30")

    print(f"\nASIGNACION NIT RESPONSABLE:")
    print(f"  - Activos:     {nits_asignados_activos}/30")
    print(f"  - Inactivos:   {nits_asignados_inactivos}/30")

    # Mostrar inconsistencias
    if inconsistencias:
        print(f"\nINCONSISTENCIAS ENCONTRADAS ({len(inconsistencias)}):")
        for nit, problema in inconsistencias:
            print(f"  - {nit}: {problema}")

    # Diagnóstico final
    print("\n" + "=" * 120)
    print("DIAGNOSTICO FINAL:")
    print("=" * 120)

    if nits_no_existen > 0:
        print(f"\n⚠️  PROBLEMA CRÍTICO: {nits_no_existen} NITs NO existen en nit_configuracion")
        print("   → Por eso el endpoint /bulk-nit-config rechaza la asignación")
        print("   → Los NITs deben existir en nit_configuracion ANTES de asignar")
        print("\n   Solución: Crear/activar estos NITs en nit_configuracion primero")
    elif nits_config_inactivos > 0:
        print(f"\n⚠️  ADVERTENCIA: {nits_config_inactivos} NITs están INACTIVOS en nit_configuracion")
        print("   → El endpoint /bulk-nit-config también rechaza NITs inactivos")
        print("   → Necesita que estén ACTIVOS (activo=True)")

    if nits_asignados_activos > 0:
        print(f"\n✓ {nits_asignados_activos} NITs ya están asignados (activos)")

    if nits_asignados_inactivos > 0:
        print(f"\n⚠️  {nits_asignados_inactivos} NITs están asignados pero INACTIVOS")
        print("   → Podrían reactivarse")

    if nits_no_existen == 0 and nits_config_inactivos == 0:
        print("\n✓ EXITO: Todos los NITs existen y están ACTIVOS en nit_configuracion")
        print("  → La asignación debería funcionar")
        return True
    else:
        print("\n✗ PROBLEMA: No todos los NITs están listos para asignar")
        return False


def main():
    print("\n>> Iniciando diagnóstico de NITs\n")
    db = SessionLocal()
    try:
        diagnostico_completo(db)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
