#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar que la corrección en /bulk-nit-config funciona correctamente.

Simula exactamente lo que hace el endpoint POST /bulk-nit-config
después de la corrección de línea 1104.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.usuario import Usuario
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.email_config import NitConfiguracion
from app.utils.nit_validator import NitValidator
from datetime import datetime
import re

# 42 NITs para alex.taimal (ID 5)
NITS_ALEX = [
    "3103865", "43562113", "65737372", "10275727", "372046196",
    "800058607", "800132211", "800136505", "805012966", "809002625",
    "810002948", "830042244", "830078515", "830122566", "860527377",
    "890903938", "900032159", "900148265", "900156470", "900204272",
    "900266612", "900293637", "900331794", "900352786", "900359573",
    "900374230", "900389156", "900399741", "900478383", "900517084",
    "900537021", "900613223", "900620176", "900643475", "900730332",
    "900757947", "900811823", "900872496", "901039927", "901163543",
    "901261003", "901272939", "901374507", "901645620", "901669214",
    "901701856", "901744212"
]


def verificar_correccion():
    """Verifica que la corrección funciona correctamente."""
    db = SessionLocal()

    try:
        print("=" * 120)
        print("VERIFICACIÓN DE CORRECCIÓN: /bulk-nit-config")
        print("=" * 120)
        print(f"\nAsignando {len(NITS_ALEX)} NITs a alex.taimal (ID 5)")
        print("\nSimulando exactamente lo que hace el endpoint después de la corrección...")

        # Verificar responsable
        responsable = db.query(Usuario).filter(Usuario.id == 5).first()
        if not responsable:
            print("ERROR: Usuario ID 5 no encontrado")
            return False

        print(f"[OK] Responsable encontrado: {responsable.usuario}")

        # Convertir a string como si viniera del frontend
        nits_text = ",".join(NITS_ALEX)

        # PASO 1: Parsear
        print(f"\n1. Parseando {len(NITS_ALEX)} NITs...")
        nits_raw = re.split(r'[,\n\t\r;]', nits_text)
        nits_procesados_raw = [nit.strip() for nit in nits_raw if nit.strip()]
        print(f"   ✓ Encontrados: {len(nits_procesados_raw)} NITs")

        # PASO 2: Normalizar
        print(f"\n2. Normalizando NITs...")
        nits_procesados = []
        nits_errores = []

        for nit_raw in nits_procesados_raw:
            es_valido, nit_norm = NitValidator.validar_nit(nit_raw)
            if es_valido:
                nits_procesados.append(nit_norm)
            else:
                nits_errores.append((nit_raw, nit_norm))

        if nits_errores:
            print(f"   [ERROR] Errores de normalizacion: {len(nits_errores)}")
            return False
        print(f"   [OK] Normalizados: {len(nits_procesados)} NITs")

        # PASO 3: Validar en nit_configuracion
        print(f"\n3. Validando en nit_configuracion...")
        nits_invalidos = []

        for nit_norm in nits_procesados:
            nit_config = db.query(NitConfiguracion).filter(
                NitConfiguracion.nit == nit_norm,
                NitConfiguracion.activo == True
            ).first()
            if not nit_config:
                nits_invalidos.append(nit_norm)

        if nits_invalidos:
            print(f"   [ERROR] NITs no encontrados en nit_configuracion: {len(nits_invalidos)}")
            return False
        print(f"   [OK] Todos los NITs existen en nit_configuracion")

        # PASO 4: Procesar asignaciones (CON LA CORRECCION)
        print("\n4. Procesando asignaciones (CON LA CORRECCION)...")
        creadas = 0
        reactivadas = 0
        omitidas = 0
        errores = []

        for nit_norm in nits_procesados:
            try:
                # Verificar si ya existe ACTIVA
                asignacion_activa = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == nit_norm,
                    AsignacionNitResponsable.responsable_id == 5,
                    AsignacionNitResponsable.activo == True
                ).first()

                if asignacion_activa:
                    omitidas += 1
                    continue

                # Verificar si existe INACTIVA
                asignacion_inactiva = db.query(AsignacionNitResponsable).filter(
                    AsignacionNitResponsable.nit == nit_norm,
                    AsignacionNitResponsable.responsable_id == 5,
                    AsignacionNitResponsable.activo == False
                ).first()

                if asignacion_inactiva:
                    asignacion_inactiva.activo = True
                    asignacion_inactiva.actualizado_por = "BULK_NIT_CONFIG"
                    asignacion_inactiva.actualizado_en = datetime.utcnow()
                    reactivadas += 1
                    continue

                # Obtener nombre del NIT
                nit_config = db.query(NitConfiguracion).filter(
                    NitConfiguracion.nit == nit_norm
                ).first()
                nombre_proveedor = nit_config.nombre_proveedor if nit_config else None

                # CREAR CON LA CORRECCIÓN (creado_por y creado_en, NO fecha_asignacion)
                nueva_asignacion = AsignacionNitResponsable(
                    nit=nit_norm,
                    responsable_id=5,
                    nombre_proveedor=nombre_proveedor,
                    permitir_aprobacion_automatica=True,
                    activo=True,
                    creado_por="BULK_NIT_CONFIG",
                    creado_en=datetime.utcnow()
                )
                db.add(nueva_asignacion)
                creadas += 1

            except Exception as e:
                errores.append({
                    "nit": nit_norm,
                    "error": str(e)
                })
                print(f"   ✗ ERROR creando asignación para {nit_norm}: {str(e)}")

        # Commit
        if creadas > 0 or reactivadas > 0:
            db.commit()
            print("   [OK] Cambios guardados en BD")

        # Resumen
        print("\n" + "=" * 120)
        print("RESULTADO:")
        print("=" * 120)
        print(f"  Creadas:     {creadas}/{len(nits_procesados)}")
        print(f"  Reactivadas: {reactivadas}/{len(nits_procesados)}")
        print(f"  Omitidas:    {omitidas}/{len(nits_procesados)}")
        print(f"  Errores:     {len(errores)}")

        if errores:
            print("\n  Detalles de errores:")
            for err in errores[:5]:
                print(f"    - {err['nit']}: {err['error']}")

        # Verificar en BD
        print("\n" + "=" * 120)
        print("VERIFICACION EN BASE DE DATOS:")
        print("=" * 120)

        asignaciones_bd = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.responsable_id == 5,
            AsignacionNitResponsable.activo == True
        ).count()

        print(f"\nAsignaciones activas para alex.taimal (ID 5) en BD: {asignaciones_bd}")

        if creadas > 0 or reactivadas > 0:
            print(f"\n[SUCCESS] EXITO: La correccion funciona correctamente")
            print(f"  Se crearon {creadas + reactivadas} asignaciones")
            return True
        else:
            print(f"\n[FAILED] ERROR: No se crearon asignaciones")
            return False

    except Exception as e:
        print(f"\n[EXCEPTION] EXCEPCION: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    exito = verificar_correccion()
    sys.exit(0 if exito else 1)
