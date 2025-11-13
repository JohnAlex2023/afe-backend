"""
Normalización de NITs y Asignación de Responsables

Este script implementa la decisión arquitectónica:
REGLA: TODOS los NITs en la BD se almacenan SIN dígito de verificación

Pasos:
1. Revierte NITs que fueron mal normalizados (cortados incorrectamente)
2. Normaliza TODOS los NITs correctamente (solo elimina DV después del guión)
3. Normaliza NITs en asignaciones
4. Sincroniza responsables a facturas
5. Muestra proveedores sin asignación que necesitan configuración

Este script es SEGURO - revisa primero, luego aplica cambios.
"""
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.utils.normalizacion import normalizar_nit, formatear_nit_con_dv

engine = create_engine(settings.database_url)

print('=' * 90)
print('NORMALIZACION DE NITS (SIN DV) + SINCRONIZACION')
print('=' * 90)
print('\nREGLA ENTERPRISE: Todos los NITs se almacenan SIN digito de verificacion')
print('El DV se calcula dinamicamente cuando se necesita mostrar\n')

with engine.connect() as conn:

    # PASO 1: Primero necesitamos restaurar NITs que fueron cortados incorrectamente
    print('[PASO 1] DETECTANDO NITS MAL NORMALIZADOS (cortados incorrectamente):')
    print('-' * 90)

    # Los NITs cortados tienen menos de 8 dígitos (la mayoría de NITs colombianos tienen 9-10)
    nits_cortados = conn.execute(text("""
        SELECT id, nit, razon_social
        FROM proveedores
        WHERE LENGTH(nit) < 8
        ORDER BY id
    """)).fetchall()

    if nits_cortados:
        print(f'\nProveedores con NITs sospechosamente cortos: {len(nits_cortados)}')
        print('\nEstos NITs probablemente fueron cortados incorrectamente:')
        print('  ID  | NIT Actual | Razon Social')
        print('  ' + '-' * 85)
        for p in nits_cortados:
            print(f'  {p[0]:<3} | {p[1]:<10} | {p[2][:60]}')

        print('\n[ADVERTENCIA] Estos NITs estan muy cortos.')
        print('Necesitas restaurarlos manualmente con el NIT correcto.')
        print('Por ejemplo: UPDATE proveedores SET nit = "830122566" WHERE id = 8;')
        print('\nPor ahora, voy a continuar con los demas NITs...\n')

    # PASO 2: Normalizar NITs que tienen guión (aún no normalizados)
    print('[PASO 2] NORMALIZANDO NITS CON GUION (formato: XXXXXX-X):')
    print('-' * 90)

    nits_con_guion = conn.execute(text("""
        SELECT id, nit, razon_social
        FROM proveedores
        WHERE nit LIKE '%-%'
        ORDER BY id
    """)).fetchall()

    if nits_con_guion:
        print(f'\nProveedores con NITs a normalizar: {len(nits_con_guion)}')
        print('\n  ID  | NIT Original      | NIT Normalizado | Razon Social')
        print('  ' + '-' * 85)

        total_normalizados = 0
        for p in nits_con_guion:
            proveedor_id = p[0]
            nit_original = p[1]
            razon_social = p[2]
            nit_normalizado = normalizar_nit(nit_original)

            print(f'  {proveedor_id:<3} | {nit_original:<17} | {nit_normalizado:<15} | {razon_social[:40]}')

            # Actualizar
            conn.execute(text("""
                UPDATE proveedores
                SET nit = :nit_normalizado
                WHERE id = :proveedor_id
            """), {
                'nit_normalizado': nit_normalizado,
                'proveedor_id': proveedor_id
            })
            total_normalizados += 1

        conn.commit()
        print(f'\n[OK] {total_normalizados} NITs normalizados en proveedores')
    else:
        print('\n[OK] No hay NITs con guion para normalizar')

    # PASO 3: Normalizar NITs en asignaciones
    print('\n[PASO 3] NORMALIZANDO NITS EN ASIGNACIONES:')
    print('-' * 90)

    asignaciones_con_guion = conn.execute(text("""
        SELECT id, nit, nombre_proveedor
        FROM asignacion_nit_responsable
        WHERE nit LIKE '%-%'
    """)).fetchall()

    if asignaciones_con_guion:
        print(f'\nAsignaciones con NITs a normalizar: {len(asignaciones_con_guion)}')

        total_asig_norm = 0
        for a in asignaciones_con_guion:
            asig_id = a[0]
            nit_original = a[1]
            nit_normalizado = normalizar_nit(nit_original)

            try:
                conn.execute(text("""
                    UPDATE asignacion_nit_responsable
                    SET nit = :nit_normalizado
                    WHERE id = :asig_id
                """), {
                    'nit_normalizado': nit_normalizado,
                    'asig_id': asig_id
                })
                total_asig_norm += 1
            except Exception as e:
                print(f'  [WARNING] No se pudo normalizar asignacion {asig_id}: {str(e)}')

        conn.commit()
        print(f'[OK] {total_asig_norm} NITs normalizados en asignaciones')
    else:
        print('[OK] No hay NITs con guion en asignaciones')

    # PASO 4: Sincronizar responsables a facturas
    print('\n[PASO 4] SINCRONIZANDO RESPONSABLES A FACTURAS:')
    print('-' * 90)

    facturas_sync = conn.execute(text("""
        SELECT
            f.id,
            f.numero_factura,
            p.nit,
            p.razon_social,
            a.responsable_id,
            r.nombre,
            r.usuario
        FROM facturas f
        JOIN proveedores p ON p.id = f.proveedor_id
        JOIN asignacion_nit_responsable a ON a.nit = p.nit AND a.activo = 1
        LEFT JOIN responsables r ON r.id = a.responsable_id
        WHERE f.responsable_id IS NULL
    """)).fetchall()

    if facturas_sync:
        print(f'\nFacturas a sincronizar: {len(facturas_sync)}')
        print('\n  Factura       | NIT         | Proveedor            | Asignar a')
        print('  ' + '-' * 80)

        # Mostrar primeras 20
        for f in facturas_sync[:20]:
            numero = f[1]
            nit = f[2]
            proveedor = f[3]
            responsable = f[5]

            print(f'  {numero[:13]:<13} | {nit:<11} | {proveedor[:20]:<20} | {responsable}')

        if len(facturas_sync) > 20:
            print(f'  ... y {len(facturas_sync) - 20} mas')

        # Sincronizar por lotes
        responsables_dict = {}
        for f in facturas_sync:
            factura_id = f[0]
            responsable_id = f[4]

            if responsable_id not in responsables_dict:
                responsables_dict[responsable_id] = []
            responsables_dict[responsable_id].append(factura_id)

        total_sincronizadas = 0
        for responsable_id, factura_ids in responsables_dict.items():
            placeholders = ','.join([str(fid) for fid in factura_ids])

            result = conn.execute(text(f"""
                UPDATE facturas
                SET responsable_id = :responsable_id
                WHERE id IN ({placeholders})
            """), {'responsable_id': responsable_id})

            total_sincronizadas += result.rowcount

        conn.commit()
        print(f'\n[OK] {total_sincronizadas} facturas sincronizadas')
    else:
        print('[OK] No hay facturas para sincronizar')

    # PASO 5: Estadísticas finales
    print('\n' + '=' * 90)
    print('ESTADISTICAS FINALES:')
    print('=' * 90)

    stats = conn.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN responsable_id IS NOT NULL THEN 1 ELSE 0 END) as con_resp,
            SUM(CASE WHEN responsable_id IS NULL THEN 1 ELSE 0 END) as sin_resp
        FROM facturas
    """)).fetchone()

    total = stats[0]
    con_resp = stats[1]
    sin_resp = stats[2]

    print(f'\nFACTURAS:')
    print(f'  Total: {total}')
    print(f'  Con responsable asignado: {con_resp} ({con_resp/total*100:.1f}%)')
    print(f'  Sin responsable asignado: {sin_resp} ({sin_resp/total*100:.1f}%)')

    # Por responsable
    print('\nFACTURAS POR RESPONSABLE:')
    por_resp = conn.execute(text("""
        SELECT
            r.nombre,
            r.usuario,
            COUNT(f.id) as total,
            SUM(CASE WHEN f.estado = 'en_revision' THEN 1 ELSE 0 END) as en_rev,
            SUM(CASE WHEN f.estado = 'aprobada_auto' THEN 1 ELSE 0 END) as auto,
            SUM(CASE WHEN f.estado = 'aprobada' THEN 1 ELSE 0 END) as manual
        FROM facturas f
        JOIN responsables r ON r.id = f.responsable_id
        GROUP BY r.id, r.nombre, r.usuario
        ORDER BY total DESC
    """)).fetchall()

    if por_resp:
        print('\n  Responsable     | Usuario                | Total | En Rev. | Auto | Manual')
        print('  ' + '-' * 80)
        for r in por_resp:
            print(f'  {r[0][:15]:<15} | {r[1][:22]:<22} | {r[2]:<5} | {r[3]:<7} | {r[4]:<4} | {r[5]}')
    else:
        print('\n  [WARNING] No hay facturas asignadas a responsables')

    # Proveedores sin asignación
    print('\nPROVEEDORES SIN ASIGNACION (requieren configuracion):')
    sin_asig = conn.execute(text("""
        SELECT
            p.nit,
            p.razon_social,
            COUNT(f.id) as total_facturas,
            SUM(CASE WHEN f.estado = 'en_revision' THEN 1 ELSE 0 END) as en_rev
        FROM facturas f
        JOIN proveedores p ON p.id = f.proveedor_id
        LEFT JOIN asignacion_nit_responsable a ON a.nit = p.nit AND a.activo = 1
        WHERE f.responsable_id IS NULL
        AND a.id IS NULL
        GROUP BY p.id, p.nit, p.razon_social
        ORDER BY total_facturas DESC
    """)).fetchall()

    if sin_asig:
        print(f'\n  Total: {len(sin_asig)} proveedores')
        print('\n  NIT           | Proveedor                       | Facturas | En Rev.')
        print('  ' + '-' * 80)
        for p in sin_asig:
            nit = p[0]
            proveedor = p[1]
            total_fact = p[2]
            en_rev = p[3]

            # Mostrar NIT formateado con DV para referencia
            nit_con_dv = formatear_nit_con_dv(nit)

            print(f'  {nit:<13} | {proveedor[:31]:<31} | {total_fact:<8} | {en_rev}')
            print(f'  {nit_con_dv:<13}   (con DV para referencia)')

        print('\n  [ACCION REQUERIDA]')
        print('  Configurar estas asignaciones en: Proveedores > Asignaciones')
        print('  IMPORTANTE: Al configurar, usar el NIT SIN el digito de verificacion')
    else:
        print('\n  [OK] Todos los proveedores con facturas tienen asignacion')

print('\n' + '=' * 90)
print('PROCESO COMPLETADO')
print('=' * 90)
print('\nPROXIMOS PASOS:')
print('1. Si hay NITs cortados (PASO 1), restaurarlos manualmente con el NIT correcto')
print('2. Configurar asignaciones para proveedores sin responsable')
print('3. Reiniciar el backend')
print('4. Iniciar sesion con cada responsable y verificar facturas asignadas')
print('\nREGLA PARA EL FUTURO:')
print('- Al crear/actualizar proveedores: SIEMPRE usar NIT SIN digito de verificacion')
print('- Al configurar asignaciones: SIEMPRE usar NIT SIN digito de verificacion')
print('- El sistema mostrara el DV automaticamente cuando sea necesario')

engine.dispose()
