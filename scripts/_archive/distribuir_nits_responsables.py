"""
Script para distribuir NITs entre múltiples responsables

Uso:
    python scripts/distribuir_nits_responsables.py [modo]

Modos:
    crear_responsables  - Crea nuevos responsables de ejemplo
    ver_distribucion    - Muestra la distribución actual
    redistribuir        - Redistribuye NITs entre responsables
"""
import sys
from app.db.session import SessionLocal
from app.models.responsable import Responsable
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.proveedor import Proveedor
from app.core.security import hash_password
from sqlalchemy import func

db = SessionLocal()

def crear_responsables_ejemplo():
    """Crea responsables de ejemplo para distribuir las facturas"""
    from app.models.role import Role

    responsable_role = db.query(Role).filter(Role.nombre == "responsable").first()
    if not responsable_role:
        print("ERROR: Rol 'responsable' no existe")
        return

    responsables_a_crear = [
        {
            "usuario": "responsable1",
            "nombre": "Responsable 1",
            "email": "responsable1@example.com",
        },
        {
            "usuario": "responsable2",
            "nombre": "Responsable 2",
            "email": "responsable2@example.com",
        },
        {
            "usuario": "responsable3",
            "nombre": "Responsable 3",
            "email": "responsable3@example.com",
        },
    ]

    for datos in responsables_a_crear:
        existe = db.query(Responsable).filter(
            Responsable.usuario == datos["usuario"]
        ).first()

        if existe:
            print(f"✓ Responsable {datos['usuario']} ya existe (ID: {existe.id})")
        else:
            nuevo = Responsable(
                usuario=datos["usuario"],
                nombre=datos["nombre"],
                email=datos["email"],
                hashed_password=hash_password("12345678"),
                activo=True,
                role_id=responsable_role.id,
            )
            db.add(nuevo)
            db.flush()
            print(f"+ Responsable creado: {datos['usuario']} (ID: {nuevo.id})")

    db.commit()
    print("\n✓ Responsables de ejemplo creados")


def ver_distribucion_actual():
    """Muestra cómo están distribuidos los NITs actualmente"""
    print("\n" + "="*80)
    print("DISTRIBUCIÓN ACTUAL DE NITs POR RESPONSABLE")
    print("="*80)

    # Obtener todos los responsables
    responsables = db.query(Responsable).all()

    for resp in responsables:
        asignaciones = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.responsable_id == resp.id,
            AsignacionNitResponsable.activo == True
        ).all()

        total_facturas = db.query(func.count()).filter(
            db.query(Proveedor).filter(
                Proveedor.nit.in_([a.nit for a in asignaciones])
            ).exists()
        ).scalar() if asignaciones else 0

        print(f"\n{resp.nombre} (ID: {resp.id}, usuario: {resp.usuario})")
        print(f"  NITs asignados: {len(asignaciones)}")
        if asignaciones:
            for asig in asignaciones[:5]:  # Mostrar los primeros 5
                print(f"    - {asig.nit} ({asig.nombre_proveedor})")
            if len(asignaciones) > 5:
                print(f"    ... y {len(asignaciones) - 5} más")


def redistribuir_nits():
    """Redistribuye los NITs entre los responsables de forma equilibrada"""
    print("\n" + "="*80)
    print("REDISTRIBUYENDO NITs DE FORMA EQUILIBRADA")
    print("="*80)

    # Obtener todos los responsables activos
    responsables = db.query(Responsable).filter(Responsable.activo == True).all()

    if len(responsables) < 2:
        print("ERROR: Se requieren al menos 2 responsables para redistribuir")
        print(f"Responsables actuales: {len(responsables)}")
        return

    # Obtener todas las asignaciones activas
    asignaciones = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.activo == True
    ).all()

    print(f"\nTotal de asignaciones actuales: {len(asignaciones)}")
    print(f"Total de responsables: {len(responsables)}")

    # Distribuir de forma round-robin
    por_responsable = len(asignaciones) // len(responsables)
    residuo = len(asignaciones) % len(responsables)

    print(f"Distribución objetivo: {por_responsable} asignaciones por responsable")
    if residuo:
        print(f"Residuo: {residuo} asignaciones adicionales")

    # Reorganizar
    contador = 0
    for i, asig in enumerate(asignaciones):
        # Calcular cuál responsable debe tener esta asignación
        responsable_idx = i % len(responsables)
        nuevo_responsable = responsables[responsable_idx]

        # Si el responsable es diferente, actualizar
        if asig.responsable_id != nuevo_responsable.id:
            resp_actual = db.query(Responsable).filter(
                Responsable.id == asig.responsable_id
            ).first()

            print(f"\nAsignación {i+1}/{len(asignaciones)}")
            print(f"  NIT: {asig.nit} ({asig.nombre_proveedor})")
            print(f"  De: {resp_actual.nombre if resp_actual else 'Unknown'}")
            print(f"  A:  {nuevo_responsable.nombre}")

            asig.responsable_id = nuevo_responsable.id
            contador += 1

    db.commit()
    print(f"\n✓ Asignaciones actualizadas: {contador}")
    print("✓ Redistribución completada")


def main():
    modo = sys.argv[1].lower() if len(sys.argv) > 1 else "ver_distribucion"

    print(f"\n Modo: {modo}\n")

    if modo == "crear_responsables":
        crear_responsables_ejemplo()
    elif modo == "ver_distribucion":
        ver_distribucion_actual()
    elif modo == "redistribuir":
        redistribuir_nits()
    else:
        print(f"Modo desconocido: {modo}")
        print("Modos disponibles: crear_responsables, ver_distribucion, redistribuir")


try:
    main()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
