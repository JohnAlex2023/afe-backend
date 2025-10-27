"""
DIAGNÓSTICO EXHAUSTIVO DE INTEGRIDAD DE DATOS
Script profesional para identificar:
- Inconsistencias de estructura
- Registros huérfanos (Foreign Key violations)
- Duplicados e inconsistencias de sincronización
- Valores NULL inesperados
- Discrepancias entre tablas relacionadas
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.responsable import Responsable
from app.models.workflow_aprobacion import AsignacionNitResponsable
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from sqlalchemy import func, and_, or_
from datetime import datetime

db = SessionLocal()

def print_section(title):
    print("\n" + "="*120)
    print(f"  {title}")
    print("="*120)

def print_warning(msg):
    print(f"  [WARNING] {msg}")

def print_error(msg):
    print(f"  [ERROR] {msg}")

def print_info(msg):
    print(f"  [INFO] {msg}")

try:
    print_section("DIAGNÓSTICO EXHAUSTIVO DE INTEGRIDAD DE DATOS")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ===== 1. ANÁLISIS DE RESPONSABLES =====
    print_section("1. ANÁLISIS DE RESPONSABLES")

    responsables = db.query(Responsable).all()
    print(f"\n  Total de responsables: {len(responsables)}\n")

    for resp in responsables:
        print(f"  ID: {resp.id} | Usuario: '{resp.usuario}' | Nombre: {resp.nombre} | Activo: {resp.activo}")

    # ===== 2. ANÁLISIS DE ASIGNACIONES =====
    print_section("2. ANÁLISIS DE ASIGNACIONES (AsignacionNitResponsable)")

    asignaciones = db.query(AsignacionNitResponsable).all()
    print(f"\n  Total de asignaciones: {len(asignaciones)}")

    # 2.1: Responsables huérfanos en asignaciones
    print("\n  2.1 VERIFICAR FOREIGN KEYS VÁLIDOS:")
    responsables_ids_validos = [r.id for r in responsables]

    asignaciones_invalidas = [
        a for a in asignaciones
        if a.responsable_id not in responsables_ids_validos
    ]

    if asignaciones_invalidas:
        print_error(f"  {len(asignaciones_invalidas)} asignaciones apuntan a responsables no existentes:")
        for a in asignaciones_invalidas:
            print(f"    - NIT: {a.nit}, responsable_id: {a.responsable_id} (NO EXISTE)")
    else:
        print_info("  [OK] Todas las asignaciones apuntan a responsables validos")

    # 2.2: NITs duplicados para el MISMO responsable
    print("\n  2.2 VERIFICAR DUPLICADOS POR RESPONSABLE:")
    for resp in responsables:
        asig_resp = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.responsable_id == resp.id
        ).all()

        nits = [a.nit for a in asig_resp]
        duplicados = [nit for nit in set(nits) if nits.count(nit) > 1]

        if duplicados:
            print_warning(f"  {resp.nombre}: {len(duplicados)} NITs duplicados")
            for nit in duplicados:
                count = nits.count(nit)
                print(f"    - {nit}: {count} veces")
        else:
            print_info(f"  {resp.nombre}: [OK] Sin duplicados ({len(asig_resp)} NITs)")

    # 2.3: Distribución de NITs
    print("\n  2.3 DISTRIBUCIÓN DE NITs:")
    for resp in responsables:
        asig_resp_activos = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.responsable_id == resp.id,
            AsignacionNitResponsable.activo == True
        ).all()

        asig_resp_inactivos = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.responsable_id == resp.id,
            AsignacionNitResponsable.activo == False
        ).all()

        print(f"  {resp.nombre:15} | Activos: {len(asig_resp_activos):3} | Inactivos: {len(asig_resp_inactivos):3}")

    # 2.4: NITs compartidos entre múltiples responsables
    print("\n  2.4 VERIFICAR NITs COMPARTIDOS (mismo NIT, múltiples responsables):")
    from collections import defaultdict
    nits_por_responsable = defaultdict(list)

    for asig in asignaciones:
        if asig.activo:
            nits_por_responsable[asig.nit].append(asig.responsable_id)

    nits_compartidos = {nit: resps for nit, resps in nits_por_responsable.items() if len(resps) > 1}

    if nits_compartidos:
        print_warning(f"  {len(nits_compartidos)} NITs están asignados a múltiples responsables:")
        for nit, responsables_ids in list(nits_compartidos.items())[:10]:
            nombres = [next((r.nombre for r in responsables if r.id == rid), f"ID:{rid}")
                      for rid in responsables_ids]
            print(f"    - {nit}: {', '.join(nombres)}")
        if len(nits_compartidos) > 10:
            print(f"    ... y {len(nits_compartidos) - 10} más")
    else:
        print_info("  [OK] Cada NIT está asignado a un único responsable")

    # ===== 3. ANÁLISIS DE FACTURAS =====
    print_section("3. ANÁLISIS DE FACTURAS")

    facturas = db.query(Factura).all()
    print(f"\n  Total de facturas: {len(facturas)}\n")

    # 3.1: Facturas con proveedor_id NULL
    print("  3.1 FACTURAS CON PROVEEDOR FALTANTE:")
    facturas_sin_proveedor = [f for f in facturas if f.proveedor_id is None]

    if facturas_sin_proveedor:
        print_error(f"  {len(facturas_sin_proveedor)} facturas SIN proveedor_id:")
        for f in facturas_sin_proveedor[:5]:
            print(f"    - Factura {f.numero_factura} (ID: {f.id})")
        if len(facturas_sin_proveedor) > 5:
            print(f"    ... y {len(facturas_sin_proveedor) - 5} más")
    else:
        print_info("  [OK] Todas las facturas tienen proveedor_id")

    # 3.2: Facturas con proveedor huérfano (proveedor no existe)
    print("\n  3.2 FACTURAS CON PROVEEDOR HUÉRFANO (FK violation):")
    proveedores_validos = db.query(Proveedor.id).all()
    proveedores_ids_validos = [pid for (pid,) in proveedores_validos]

    facturas_proveedor_invalido = [
        f for f in facturas
        if f.proveedor_id and f.proveedor_id not in proveedores_ids_validos
    ]

    if facturas_proveedor_invalido:
        print_error(f"  {len(facturas_proveedor_invalido)} facturas apuntan a proveedores no existentes:")
        for f in facturas_proveedor_invalido[:5]:
            print(f"    - Factura {f.numero_factura}: proveedor_id={f.proveedor_id}")
        if len(facturas_proveedor_invalido) > 5:
            print(f"    ... y {len(facturas_proveedor_invalido) - 5} más")
    else:
        print_info("  [OK] Todas las facturas apuntan a proveedores válidos")

    # 3.3: Facturas con responsable_id NULL vs NO NULL
    print("\n  3.3 ASIGNACIÓN DE RESPONSABLES A FACTURAS:")
    facturas_sin_responsable = [f for f in facturas if f.responsable_id is None]
    facturas_con_responsable = [f for f in facturas if f.responsable_id is not None]

    print(f"  Con responsable asignado: {len(facturas_con_responsable)}")
    print(f"  Sin responsable asignado: {len(facturas_sin_responsable)}")

    if facturas_sin_responsable:
        print_warning(f"  {len(facturas_sin_responsable)} facturas SIN responsable asignado")
        for f in facturas_sin_responsable[:5]:
            print(f"    - {f.numero_factura}")
        if len(facturas_sin_responsable) > 5:
            print(f"    ... y {len(facturas_sin_responsable) - 5} más")

    # 3.4: Facturas con responsable huérfano (responsable no existe)
    print("\n  3.4 FACTURAS CON RESPONSABLE HUÉRFANO (FK violation):")
    facturas_responsable_invalido = [
        f for f in facturas_con_responsable
        if f.responsable_id not in responsables_ids_validos
    ]

    if facturas_responsable_invalido:
        print_error(f"  {len(facturas_responsable_invalido)} facturas apuntan a responsables no existentes:")
        for f in facturas_responsable_invalido[:5]:
            print(f"    - Factura {f.numero_factura}: responsable_id={f.responsable_id}")
        if len(facturas_responsable_invalido) > 5:
            print(f"    ... y {len(facturas_responsable_invalido) - 5} más")
    else:
        print_info("  [OK] Todas las facturas apuntan a responsables válidos")

    # ===== 4. ANÁLISIS DE SINCRONIZACIÓN: Factura.responsable_id vs AsignacionNitResponsable =====
    print_section("4. ANÁLISIS DE SINCRONIZACIÓN (CRÍTICO)")
    print("\n  Este análisis verifica si el responsable asignado a la factura")
    print("  coincide con lo que está definido en AsignacionNitResponsable\n")

    # 4.1: Para cada factura, verificar si su responsable coincide con su NIT
    print("  4.1 INCONSISTENCIAS DE SINCRONIZACIÓN:")

    inconsistencias = []

    for factura in facturas_con_responsable:
        if not factura.proveedor_id:
            continue

        proveedor = db.query(Proveedor).filter(Proveedor.id == factura.proveedor_id).first()
        if not proveedor or not proveedor.nit:
            continue

        # Obtener asignación(es) del NIT
        asignaciones_del_nit = db.query(AsignacionNitResponsable).filter(
            AsignacionNitResponsable.nit == proveedor.nit,
            AsignacionNitResponsable.activo == True
        ).all()

        if not asignaciones_del_nit:
            # El NIT no está asignado a nadie, pero la factura tiene responsable
            inconsistencias.append({
                "tipo": "NIT NO ASIGNADO",
                "factura": factura.numero_factura,
                "nit": proveedor.nit,
                "responsable_factura": next((r.nombre for r in responsables if r.id == factura.responsable_id), "Unknown"),
                "responsable_asignado": "NINGUNO"
            })
        else:
            # Verificar si el responsable de la factura está en las asignaciones del NIT
            responsables_asignados_ids = [a.responsable_id for a in asignaciones_del_nit]

            if factura.responsable_id not in responsables_asignados_ids:
                inconsistencias.append({
                    "tipo": "RESPONSABLE INCORRECTO",
                    "factura": factura.numero_factura,
                    "nit": proveedor.nit,
                    "responsable_factura": next((r.nombre for r in responsables if r.id == factura.responsable_id), "Unknown"),
                    "responsable_asignado": ", ".join([
                        next((r.nombre for r in responsables if r.id == rid), f"ID:{rid}")
                        for rid in responsables_asignados_ids
                    ])
                })

    if inconsistencias:
        print_error(f"  {len(inconsistencias)} INCONSISTENCIAS DE SINCRONIZACIÓN:")
        print(f"\n  {'TIPO':<30} {'FACTURA':<20} {'NIT':<20} {'RESPONSABLE FACTURA':<25} {'RESPONSABLE ASIGNADO':<25}")
        print("  " + "-"*115)

        for inc in inconsistencias[:20]:
            print(f"  {inc['tipo']:<30} {inc['factura']:<20} {inc['nit']:<20} {inc['responsable_factura']:<25} {inc['responsable_asignado']:<25}")

        if len(inconsistencias) > 20:
            print(f"\n  ... y {len(inconsistencias) - 20} más inconsistencias")
    else:
        print_info("  [OK] TODOS los responsables coinciden con las asignaciones de NITs")

    # ===== 5. ANÁLISIS DE DISTRIBUCIÓN POR RESPONSABLE =====
    print_section("5. DISTRIBUCIÓN ACTUAL DE FACTURAS POR RESPONSABLE")

    for resp in responsables:
        total_facturas = db.query(func.count(Factura.id)).filter(
            Factura.responsable_id == resp.id
        ).scalar()

        asignaciones_nits = db.query(func.count(AsignacionNitResponsable.id)).filter(
            AsignacionNitResponsable.responsable_id == resp.id,
            AsignacionNitResponsable.activo == True
        ).scalar()

        # Contar cuántas facturas DEBERÍAN tener (basado en NITs asignados)
        nits_asignados = db.query(AsignacionNitResponsable.nit).filter(
            AsignacionNitResponsable.responsable_id == resp.id,
            AsignacionNitResponsable.activo == True
        ).all()

        nits_list = [nit for (nit,) in nits_asignados]

        if nits_list:
            proveedor_ids = db.query(Proveedor.id).filter(
                Proveedor.nit.in_(nits_list)
            ).all()
            proveedor_ids_list = [pid for (pid,) in proveedor_ids]

            facturas_esperadas = db.query(func.count(Factura.id)).filter(
                Factura.proveedor_id.in_(proveedor_ids_list)
            ).scalar()
        else:
            facturas_esperadas = 0

        diferencia = total_facturas - facturas_esperadas if facturas_esperadas > 0 else 0

        status = "[OK] OK" if total_facturas == facturas_esperadas else "[WARN] INCONSISTENCIA"

        print(f"\n  {resp.nombre:15} | NITs: {asignaciones_nits:3} | Facturas: {total_facturas:3} | Esperadas: {facturas_esperadas:3} | Diff: {diferencia:+4} | {status}")

    # ===== 6. RESUMEN EJECUTIVO =====
    print_section("6. RESUMEN EJECUTIVO")

    total_issues = (
        len(asignaciones_invalidas) +
        len(facturas_sin_proveedor) +
        len(facturas_proveedor_invalido) +
        len(facturas_responsable_invalido) +
        len(inconsistencias) +
        len(facturas_sin_responsable)
    )

    if total_issues == 0:
        print("\n  [OK] NO SE ENCONTRARON PROBLEMAS DE INTEGRIDAD")
    else:
        print(f"\n  [ALERTA] Se encontraron {total_issues} problemas:")
        if asignaciones_invalidas:
            print(f"    - {len(asignaciones_invalidas)} asignaciones con responsables no existentes")
        if facturas_sin_proveedor:
            print(f"    - {len(facturas_sin_proveedor)} facturas sin proveedor")
        if facturas_proveedor_invalido:
            print(f"    - {len(facturas_proveedor_invalido)} facturas con proveedor no existente")
        if facturas_responsable_invalido:
            print(f"    - {len(facturas_responsable_invalido)} facturas con responsable no existente")
        if facturas_sin_responsable:
            print(f"    - {len(facturas_sin_responsable)} facturas sin responsable asignado")
        if inconsistencias:
            print(f"    - {len(inconsistencias)} INCONSISTENCIAS DE SINCRONIZACIÓN (CRÍTICO)")

    print("\n" + "="*120)

except Exception as e:
    print_error(f"Error en diagnóstico: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
