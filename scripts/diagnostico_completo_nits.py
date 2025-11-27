"""
Diagnóstico completo de NITs en la BD vs lo que debería haber.

Compara:
1. Los 101 NITs que el usuario proporcionó
2. Los NITs que están actualmente en nit_configuracion
3. Identifica cuáles faltan o están incorrectos
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.email_config import NitConfiguracion
from app.utils.nit_validator import NitValidator


# Los 101 NITs correctos que debería haber (sin DV)
NITS_CORRECTOS = {
    "facturacion.electronica@angiografiadecolombia.com": [
        "17343874", "47425554", "80818383", "800058607", "800136505",
        "800153993", "800185449", "822000582", "830042244", "830078515",
        "890903938", "900016757", "900032159", "900136505", "900156003",
        "900156470", "900266612", "900331794", "900352786", "900359573",
        "900374230", "900389156", "900399741", "900478383", "900537021",
        "900872496", "901261003", "901302708", "901701856", "901732395"
    ],
    "facturacion.electronica@avidanti.com": [
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
    ],
    "diacorsoacha@avidanti.com": [
        "800058607", "800136505", "800153993", "800185347", "800242106",
        "805012966", "80828832", "811030191", "830037946", "830042244",
        "830122566", "890903938", "900032159", "900156470", "900331794",
        "900352786", "900359573", "900399741", "900537021", "900872496",
        "901163543", "901261003", "901637465", "901701856", "1000224504"
    ]
}


def diagnostico_completo(db: Session):
    """Realiza diagnóstico completo."""
    print("=" * 100)
    print("DIAGNOSTICO COMPLETO DE NITs")
    print("=" * 100)

    # Contar NITs esperados
    total_esperados = sum(len(nits) for nits in NITS_CORRECTOS.values())
    print(f"\nNITs ESPERADOS: {total_esperados}")
    print(f"  - facturacion.electronica@angiografiadecolombia.com: {len(NITS_CORRECTOS['facturacion.electronica@angiografiadecolombia.com'])}")
    print(f"  - facturacion.electronica@avidanti.com: {len(NITS_CORRECTOS['facturacion.electronica@avidanti.com'])}")
    print(f"  - diacorsoacha@avidanti.com: {len(NITS_CORRECTOS['diacorsoacha@avidanti.com'])}")

    # Obtener NITs actuales de la BD
    nits_bd = db.query(NitConfiguracion).filter(NitConfiguracion.activo == True).all()
    print(f"\nNITs EN BD: {len(nits_bd)} registros, {len(set(n.nit for n in nits_bd))} únicos")

    # Normalizar NITs esperados
    nits_esperados_normalizados = {}
    for email, nits_sin_dv in NITS_CORRECTOS.items():
        nits_normalizados = []
        for nit in nits_sin_dv:
            es_valido, resultado = NitValidator.validar_nit(nit)
            if es_valido:
                nits_normalizados.append(resultado)
            else:
                print(f"  ERROR normalizando {nit}: {resultado}")
        nits_esperados_normalizados[email] = nits_normalizados

    # Comparar por correo
    print("\n" + "=" * 100)
    print("COMPARACIÓN POR CORREO:")
    print("=" * 100)

    for email, nits_esperados in nits_esperados_normalizados.items():
        print(f"\n[{email}]")

        # Obtener cuentas
        from app.models.email_config import CuentaCorreo
        cuenta = db.query(CuentaCorreo).filter(CuentaCorreo.email == email).first()

        if not cuenta:
            print(f"  ERROR: Cuenta no encontrada en BD")
            continue

        # Obtener NITs de esta cuenta
        nits_en_cuenta = db.query(NitConfiguracion).filter(
            NitConfiguracion.cuenta_correo_id == cuenta.id,
            NitConfiguracion.activo == True
        ).all()
        nits_en_cuenta_set = {n.nit for n in nits_en_cuenta}
        nits_esperados_set = set(nits_esperados)

        print(f"  Esperados: {len(nits_esperados)}")
        print(f"  En BD: {len(nits_en_cuenta)}")

        # Encontrados
        encontrados = nits_esperados_set & nits_en_cuenta_set
        print(f"  Encontrados: {len(encontrados)}")

        # Faltantes
        faltantes = nits_esperados_set - nits_en_cuenta_set
        if faltantes:
            print(f"  FALTANTES ({len(faltantes)}):")
            for nit in sorted(faltantes)[:10]:
                print(f"    - {nit}")
            if len(faltantes) > 10:
                print(f"    ... y {len(faltantes) - 10} más")

        # Extras (en BD pero no esperados)
        extras = nits_en_cuenta_set - nits_esperados_set
        if extras:
            print(f"  EXTRAS ({len(extras)}):")
            for nit in sorted(extras)[:10]:
                print(f"    - {nit}")
            if len(extras) > 10:
                print(f"    ... y {len(extras) - 10} más")

    # Resumen general
    print("\n" + "=" * 100)
    print("RESUMEN GENERAL:")
    print("=" * 100)

    todos_esperados = set()
    for nits in nits_esperados_normalizados.values():
        todos_esperados.update(nits)

    todos_en_bd = {n.nit for n in nits_bd}

    encontrados_total = todos_esperados & todos_en_bd
    faltantes_total = todos_esperados - todos_en_bd
    extras_total = todos_en_bd - todos_esperados

    print(f"\nNITs únicos esperados: {len(todos_esperados)}")
    print(f"NITs únicos en BD: {len(todos_en_bd)}")
    print(f"Encontrados: {len(encontrados_total)}")
    print(f"Faltantes: {len(faltantes_total)}")
    print(f"Extras: {len(extras_total)}")

    if faltantes_total:
        print(f"\nNITs FALTANTES ({len(faltantes_total)}):")
        for nit in sorted(faltantes_total)[:20]:
            print(f"  - {nit}")
        if len(faltantes_total) > 20:
            print(f"  ... y {len(faltantes_total) - 20} más")

    if extras_total:
        print(f"\nNITs EXTRAS en BD ({len(extras_total)}):")
        for nit in sorted(extras_total)[:10]:
            print(f"  - {nit}")
        if len(extras_total) > 10:
            print(f"  ... y {len(extras_total) - 10} más")

    print("\n" + "=" * 100)
    if len(faltantes_total) == 0 and len(extras_total) == 0:
        print("*** EXITO: BD está correcta ***")
        return True
    else:
        print("*** PROBLEMA: Discrepancias encontradas ***")
        return False


def main():
    print("\n>> Iniciando diagnóstico completo\n")
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
