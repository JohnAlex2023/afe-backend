"""
Script para poblar las tablas cuentas_correo y nit_configuracion
con la configuración inicial del sistema de extracción de facturas.

Uso:
    python -m scripts.seed_cuentas_correo
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.email_config import CuentaCorreo, NitConfiguracion
from datetime import datetime

# Datos a insertar
CUENTAS_DATA = [
    {
        "email": "facturacion.electronica@angiografiadecolombia.com",
        "nombre_descriptivo": "Angiografía de Colombia",
        "organizacion": "ANGIOGRAFIA",
        "nits": [
            "17343874", "47425554", "80818383", "800058607", "800136505",
            "800153993", "800185449", "822000582", "830042244", "830078515",
            "890903938", "900016757", "900032159", "900136505", "900156003",
            "900156470", "900266612", "900331794", "900352786", "900359573",
            "900374230", "900389156", "900399741", "900478383", "900537021",
            "900872496", "901261003", "901302708", "901701856", "901732395"
        ]
    },
    {
        "email": "facturacion.electronica@avidanti.com",
        "nombre_descriptivo": "Avidanti - Facturación Principal",
        "organizacion": "AVIDANTI",
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
    {
        "email": "diacorsoacha@avidanti.com",
        "nombre_descriptivo": "Avidanti - Diacor Soacha",
        "organizacion": "AVIDANTI",
        "nits": [
            "800058607", "800136505", "800153993", "800185347", "800242106",
            "805012966", "80828832", "811030191", "830037946", "830042244",
            "830122566", "890903938", "900032159", "900156470", "900331794",
            "900352786", "900359573", "900399741", "900537021", "900872496",
            "901163543", "901261003", "901637465", "901701856", "1000224504"
        ]
    }
]


def seed_cuentas_correo(db: Session):
    """
    Inserta las cuentas de correo y sus NITs en la base de datos.
    """
    print("=" * 70)
    print("INICIANDO POBLACIÓN DE DATOS DE CONFIGURACIÓN DE CORREOS")
    print("=" * 70)

    total_cuentas = 0
    total_nits = 0

    for cuenta_data in CUENTAS_DATA:
        email = cuenta_data["email"]

        # Verificar si ya existe
        cuenta_existente = db.query(CuentaCorreo).filter(CuentaCorreo.email == email).first()

        if cuenta_existente:
            print(f"\n[!] Cuenta ya existe: {email}")
            print(f"   ID: {cuenta_existente.id}, Activa: {cuenta_existente.activa}")
            print(f"   NITs configurados: {len(cuenta_existente.nits)}")
            continue

        # Crear nueva cuenta de correo con valores modernos
        nueva_cuenta = CuentaCorreo(
            email=email,
            nombre_descriptivo=cuenta_data["nombre_descriptivo"],
            organizacion=cuenta_data["organizacion"],
            max_correos_por_ejecucion=10000,  # Valor moderno (antes 500)
            ventana_inicial_dias=30,  # Valor moderno (antes 90)
            activa=True,
            creada_por="SEED_SCRIPT",
            creada_en=datetime.now(),
            actualizada_en=datetime.now()
        )

        db.add(nueva_cuenta)
        db.flush()  # Obtener el ID sin hacer commit todavía

        print(f"\n[OK] Cuenta creada: {email}")
        print(f"   ID: {nueva_cuenta.id}")
        print(f"   Organización: {nueva_cuenta.organizacion}")
        print(f"   Max correos/ejecución: {nueva_cuenta.max_correos_por_ejecucion}")
        print(f"   Ventana inicial: {nueva_cuenta.ventana_inicial_dias} días")

        # Insertar NITs asociados
        nits_insertados = 0
        for nit in cuenta_data["nits"]:
            nit_config = NitConfiguracion(
                cuenta_correo_id=nueva_cuenta.id,
                nit=nit,
                activo=True,
                creado_por="SEED_SCRIPT",
                creado_en=datetime.now(),
                actualizado_en=datetime.now()
            )
            db.add(nit_config)
            nits_insertados += 1

        print(f"   NITs agregados: {nits_insertados}")

        total_cuentas += 1
        total_nits += nits_insertados

    # Commit de todos los cambios
    db.commit()

    print("\n" + "=" * 70)
    print("RESUMEN:")
    print(f"[OK] Cuentas creadas: {total_cuentas}")
    print(f"[OK] NITs configurados: {total_nits}")
    print("=" * 70)

    # Verificación final
    print("\n" + "=" * 70)
    print("VERIFICACIÓN FINAL:")
    print("=" * 70)

    todas_cuentas = db.query(CuentaCorreo).all()
    for cuenta in todas_cuentas:
        nits_count = len(cuenta.nits)
        nits_activos = sum(1 for n in cuenta.nits if n.activo)
        print(f"\n[EMAIL] {cuenta.email}")
        print(f"   ID: {cuenta.id} | Activa: {cuenta.activa}")
        print(f"   Organización: {cuenta.organizacion}")
        print(f"   NITs: {nits_count} total ({nits_activos} activos)")
        print(f"   Config: max={cuenta.max_correos_por_ejecucion}, ventana={cuenta.ventana_inicial_dias}d")


def main():
    """Función principal."""
    print("\n>> Iniciando script de poblacion de datos...")

    db = SessionLocal()
    try:
        seed_cuentas_correo(db)
        print("\n[OK] Script completado exitosamente!")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
