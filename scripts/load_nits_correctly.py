"""
Script para cargar correctamente los NITs con formato normalizado DIAN.

Usa los 101 NITs proporcionados por el usuario y los carga en la BD
con el formato correcto: "XXXXX-D" a "XXXXXXXXX-D" donde D es el DV DIAN.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.email_config import CuentaCorreo, NitConfiguracion
from app.utils.nit_validator import NitValidator
from datetime import datetime


# Datos de los 101 NITs según el usuario, agrupados por cuenta de correo
NITS_DATA = {
    "facturacion.electronica@angiografiadecolombia.com": {
        "nits": [
            "17343874", "47425554", "80818383", "800058607", "800136505",
            "800153993", "800185449", "822000582", "830042244", "830078515",
            "890903938", "900016757", "900032159", "900136505", "900156003",
            "900156470", "900266612", "900331794", "900352786", "900359573",
            "900374230", "900389156", "900399741", "900478383", "900537021",
            "900872496", "901261003", "901302708", "901701856", "901732395"
        ]
    },
    "facturacion.electronica@avidanti.com": {
        "nits": [
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
    },
    "diacorsoacha@avidanti.com": {
        "nits": [
            "800058607", "800136505", "800153993", "800185347", "800242106",
            "805012966", "80828832", "811030191", "830037946", "830042244",
            "830122566", "890903938", "900032159", "900156470", "900331794",
            "900352786", "900359573", "900399741", "900537021", "900872496",
            "901163543", "901261003", "901637465", "901701856", "1000224504"
        ]
    }
}


def load_nits_correctly(db: Session):
    """Carga o actualiza los NITs con el formato correcto."""
    print("=" * 80)
    print("CARGANDO NITs CON FORMATO CORRECTO (DIAN)")
    print("=" * 80)

    total_procesados = 0
    total_creados = 0
    total_actualizados = 0
    errores = []

    for email, data in NITS_DATA.items():
        print(f"\n[CUENTA] {email}")

        # Obtener o crear la cuenta
        cuenta = db.query(CuentaCorreo).filter(
            CuentaCorreo.email == email
        ).first()

        if not cuenta:
            print(f"  [!] Cuenta no encontrada: {email}")
            continue

        nits = data["nits"]
        print(f"  Procesando {len(nits)} NITs...\n")

        for nit_raw in nits:
            total_procesados += 1

            # Normalizar según DIAN
            es_valido, resultado = NitValidator.validar_nit(nit_raw)

            if not es_valido:
                errores.append({
                    "email": email,
                    "nit_original": nit_raw,
                    "error": resultado
                })
                print(f"    ✗ {nit_raw:15} - ERROR: {resultado}")
                continue

            nit_normalizado = resultado

            # Buscar si ya existe
            nit_existente = db.query(NitConfiguracion).filter(
                NitConfiguracion.cuenta_correo_id == cuenta.id,
                NitConfiguracion.nit == nit_normalizado
            ).first()

            if nit_existente:
                # Ya existe, solo actualizar el timestamp
                nit_existente.actualizado_en = datetime.now()
                nit_existente.actualizado_por = "LOAD_SCRIPT"
                total_actualizados += 1
                print(f"    = {nit_normalizado:15} (ya existe)")
            else:
                # Crear nuevo
                nuevo_nit = NitConfiguracion(
                    cuenta_correo_id=cuenta.id,
                    nit=nit_normalizado,
                    activo=True,
                    creado_por="LOAD_SCRIPT",
                    creado_en=datetime.now(),
                    actualizado_en=datetime.now()
                )
                db.add(nuevo_nit)
                total_creados += 1
                print(f"    ✓ {nit_normalizado:15} (nuevo)")

    # Guardar cambios
    db.commit()

    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN:")
    print(f"  Total procesados: {total_procesados}")
    print(f"  Creados: {total_creados}")
    print(f"  Actualizados: {total_actualizados}")
    print(f"  Errores: {len(errores)}")
    print("=" * 80)

    if errores:
        print("\nDETALLE DE ERRORES:")
        for e in errores[:10]:
            print(f"  {e['email']}: {e['nit_original']} - {e['error']}")
        if len(errores) > 10:
            print(f"  ... y {len(errores) - 10} más")

    # Verificación final
    print("\nVERIFICACIÓN:")
    for email in NITS_DATA.keys():
        cuenta = db.query(CuentaCorreo).filter(
            CuentaCorreo.email == email
        ).first()
        if cuenta:
            nits_count = db.query(NitConfiguracion).filter(
                NitConfiguracion.cuenta_correo_id == cuenta.id
            ).count()
            print(f"  {email}: {nits_count} NITs")


def main():
    print("\n>> Iniciando carga de NITs con formato correcto...\n")
    db = SessionLocal()
    try:
        load_nits_correctly(db)
        print("\n[OK] Carga completada exitosamente!")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
