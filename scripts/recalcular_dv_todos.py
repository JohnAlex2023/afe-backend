"""
Script CRÍTICO: Recalcular TODOS los dígitos verificadores según DIAN.

El problema: Los DVs en la BD son incorrectos.
Solución: Para cada NIT, recalcular el DV según DIAN Módulo 11.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.email_config import NitConfiguracion
from app.utils.nit_validator import NitValidator
from datetime import datetime


def recalcular_dv_todos(db: Session):
    """Recalcula TODOS los DVs según DIAN."""
    print("=" * 100)
    print("RECALCULANDO TODOS LOS DVs SEGUN DIAN")
    print("=" * 100)

    nits_config = db.query(NitConfiguracion).all()
    total = len(nits_config)

    print(f"\nTotal de registros: {total}\n")

    actualizados = 0
    sin_cambios = 0
    errores = []

    for idx, nit_config in enumerate(nits_config, 1):
        nit_original = nit_config.nit

        try:
            # Extraer parte numérica sin DV
            if "-" in nit_original:
                nit_numero = nit_original.split("-")[0]
            else:
                nit_numero = nit_original

            # Calcular DV correcto
            es_valido, nit_correcto = NitValidator.validar_nit(nit_numero)

            if not es_valido:
                errores.append({
                    "id": nit_config.id,
                    "nit_original": nit_original,
                    "error": nit_correcto
                })
                if idx <= 10 or idx % 30 == 0:
                    print(f"[{idx:3d}/{total}] ERR {nit_original:15s} - {nit_correcto}")
                continue

            # Si no hay cambios
            if nit_original == nit_correcto:
                sin_cambios += 1
                if idx % 30 == 0:
                    print(f"[{idx:3d}/{total}] OK {nit_original:15s} (correcto)")
                continue

            # Actualizar
            print(f"[{idx:3d}/{total}] UPD {nit_original:15s} -> {nit_correcto:15s}")
            nit_config.nit = nit_correcto
            nit_config.actualizado_por = "RECALCULAR_DV"
            nit_config.actualizado_en = datetime.now()
            actualizados += 1

        except Exception as e:
            errores.append({
                "id": nit_config.id,
                "nit_original": nit_original,
                "error": str(e)
            })
            if idx <= 10:
                print(f"[{idx:3d}/{total}] EXC {nit_original:15s} - {str(e)}")

    # Guardar
    if actualizados > 0:
        db.commit()

    # Resumen
    print("\n" + "=" * 100)
    print(f"Total procesados:  {total}")
    print(f"Actualizados:      {actualizados}")
    print(f"Sin cambios:       {sin_cambios}")
    print(f"Errores:           {len(errores)}")
    print("=" * 100)

    if errores:
        print("\nERRORES:")
        for e in errores[:10]:
            print(f"  ID {e['id']}: {e['nit_original']} - {e['error']}")

    # Verificación
    print("\nVERIFICACION:")
    nits_ver = db.query(NitConfiguracion).all()
    invalidos = [n.nit for n in nits_ver if not NitValidator.es_nit_normalizado(n.nit)]

    if not invalidos:
        print("*** EXITO: Todos los DVs son correctos ***")
    else:
        print(f"*** ERROR: {len(invalidos)} NITs aun tienen DVs incorrectos ***")
        for nit in invalidos[:10]:
            print(f"  - {nit}")

    return len(invalidos) == 0


def main():
    print("\n>> Iniciando recalculo de DVs\n")
    db = SessionLocal()
    try:
        exito = recalcular_dv_todos(db)
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        db.rollback()
        sys.exit(2)
    finally:
        db.close()


if __name__ == "__main__":
    main()
