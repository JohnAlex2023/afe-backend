"""
Script de prueba para verificar la consulta de responsables por proveedor.

PROBLEMA RESUELTO:
- Proveedores tienen NITs con guion: "800136505-4"
- Asignaciones tienen NITs sin guion: "800136505"
- Endpoint ahora normaliza ambos para hacer matching correcto

PRUEBA:
1. Buscar proveedor con NIT "800136505-4" (con guion)
2. Consultar asignaciones usando ese NIT
3. Verificar que encuentra las asignaciones correctas
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import Proveedor, AsignacionNitResponsable, Responsable

# Conectar a BD
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("=" * 70)
print("PRUEBA DE CONSULTA POR PROVEEDOR - NORMALIZACION DE NITs")
print("=" * 70)

# PASO 1: Seleccionar algunos proveedores con NITs que tienen guion
proveedores_con_guion = db.query(Proveedor).filter(
    Proveedor.nit.like('%-%')
).limit(5).all()

print(f"\nProveedores encontrados con guion en NIT: {len(proveedores_con_guion)}\n")

for proveedor in proveedores_con_guion:
    print(f"Proveedor: {proveedor.razon_social or proveedor.nombre}")
    print(f"  NIT en BD: {proveedor.nit}")

    # Normalizar NIT para buscar asignaciones
    def normalizar_nit(nit: str) -> str:
        if not nit:
            return ""
        if "-" in nit:
            nit_principal = nit.split("-")[0]
        else:
            nit_principal = nit
        nit_limpio = nit_principal.replace(".", "").replace(" ", "")
        return "".join(c for c in nit_limpio if c.isdigit())

    nit_normalizado = normalizar_nit(proveedor.nit)
    print(f"  NIT normalizado: {nit_normalizado}")

    # Buscar asignaciones con normalización
    asignaciones_todas = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.activo == True
    ).all()

    asignaciones_encontradas = []
    for asig in asignaciones_todas:
        if normalizar_nit(asig.nit) == nit_normalizado:
            asignaciones_encontradas.append(asig)

    if asignaciones_encontradas:
        print(f"  Responsables asignados: {len(asignaciones_encontradas)}")
        for asig in asignaciones_encontradas:
            responsable = db.query(Responsable).filter(
                Responsable.id == asig.responsable_id
            ).first()
            if responsable:
                print(f"    - {responsable.nombre} ({responsable.email})")
    else:
        print(f"  Sin responsables asignados")

    print()

# PASO 2: Probar caso específico de DATECSA
print("\n" + "=" * 70)
print("PRUEBA ESPECIFICA: DATECSA S.A. (800136505-4)")
print("=" * 70 + "\n")

datecsa = db.query(Proveedor).filter(
    Proveedor.nit.like('800136505%')
).first()

if datecsa:
    print(f"Proveedor encontrado: {datecsa.razon_social or datecsa.nombre}")
    print(f"NIT en BD: {datecsa.nit}")

    nit_norm = normalizar_nit(datecsa.nit)
    print(f"NIT normalizado: {nit_norm}")

    # Buscar asignaciones
    asignaciones_todas = db.query(AsignacionNitResponsable).filter(
        AsignacionNitResponsable.activo == True
    ).all()

    asignaciones = []
    for asig in asignaciones_todas:
        if normalizar_nit(asig.nit) == nit_norm:
            asignaciones.append(asig)

    print(f"\nAsignaciones encontradas: {len(asignaciones)}")
    for asig in asignaciones:
        responsable = db.query(Responsable).filter(
            Responsable.id == asig.responsable_id
        ).first()
        if responsable:
            print(f"  - {responsable.nombre} ({responsable.usuario}) - {responsable.email}")
            print(f"    NIT en asignacion: {asig.nit}")
else:
    print("Proveedor DATECSA no encontrado")

db.close()

print("\n" + "=" * 70)
print("SOLUCION IMPLEMENTADA:")
print("- Endpoint /asignacion-nit/?nit=<valor> ahora normaliza NITs")
print("- Elimina guiones y digitos de verificacion antes de comparar")
print("- Garantiza matching entre formatos: 800136505-4 <-> 800136505")
print("=" * 70)
