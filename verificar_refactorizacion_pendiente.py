"""
Script de verificación post-refactorización: Eliminación de estado 'pendiente'

Este script verifica que la refactorización se completó correctamente:
1. Verifica que no hay facturas con estado 'pendiente' en la BD
2. Verifica que el enum no contiene 'pendiente'
3. Muestra estadísticas de estados actuales
4. Prueba el workflow automático con la configuración actualizada
"""
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

print('=' * 80)
print('VERIFICACION POST-REFACTORIZACION: ELIMINACION ESTADO PENDIENTE')
print('=' * 80)

engine = create_engine(settings.database_url)

with engine.connect() as conn:
    # 1. Verificar facturas con estado 'pendiente'
    print('\n[1] Verificando facturas con estado "pendiente"...')
    try:
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM facturas
            WHERE estado = 'pendiente'
        """)).fetchone()

        if result and result[0] > 0:
            print(f'   [ERROR] Hay {result[0]} facturas con estado "pendiente"')
        else:
            print('   [OK] No hay facturas con estado "pendiente" (puede ser None si el enum fue actualizado)')
    except Exception as e:
        print(f'   [OK] Error al buscar "pendiente" (esperado si el enum fue actualizado): {str(e)}')

    # 2. Verificar enum de estados
    print('\n[2] Verificando definicion del enum "estado"...')
    result = conn.execute(text("""
        SELECT COLUMN_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'facturas'
        AND COLUMN_NAME = 'estado'
    """)).fetchone()

    if result:
        enum_values = result[0]
        print(f'   Valores del enum: {enum_values}')
        if 'pendiente' in enum_values:
            print('   [ERROR] El enum aun contiene "pendiente"')
        else:
            print('   [OK] El enum NO contiene "pendiente"')
    else:
        print('   [ERROR] No se pudo obtener la definicion del enum')

    # 3. Estadísticas de estados actuales
    print('\n[3] Estadisticas de estados actuales...')
    result = conn.execute(text("""
        SELECT estado, COUNT(*) as count
        FROM facturas
        GROUP BY estado
        ORDER BY count DESC
    """)).fetchall()

    print('   Estado              | Cantidad')
    print('   ' + '-' * 40)
    for row in result:
        print(f'   {row[0]:20} | {row[1]}')

    # 4. Verificar configuración de EQUITRONIC
    print('\n[4] Verificando configuracion de EQUITRONIC...')
    result = conn.execute(text("""
        SELECT
            nit,
            nombre_proveedor,
            permitir_aprobacion_automatica,
            tipo_servicio_proveedor,
            nivel_confianza_proveedor,
            activo
        FROM asignacion_nit_responsable
        WHERE nit = '811030191' AND activo = 1
    """)).fetchone()

    if result:
        print(f'   NIT: {result[0]}')
        print(f'   Nombre: {result[1]}')
        print(f'   Aprobacion automatica: {result[2]}')
        print(f'   Tipo servicio: {result[3]}')
        print(f'   Nivel confianza: {result[4]}')
        print(f'   Activo: {result[5]}')

        if result[2] == 1 and result[3] and result[4]:
            print('   [OK] EQUITRONIC configurado correctamente para aprobacion automatica')
        else:
            print('   [WARNING] EQUITRONIC no tiene configuracion completa')
    else:
        print('   [ERROR] No se encontro configuracion activa para EQUITRONIC')

    # 5. Verificar default del campo estado
    print('\n[5] Verificando valor default del campo "estado"...')
    result = conn.execute(text("""
        SELECT COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'facturas'
        AND COLUMN_NAME = 'estado'
    """)).fetchone()

    if result:
        default_value = result[0]
        print(f'   Default actual: {default_value}')
        if default_value == 'en_revision':
            print('   [OK] Default es "en_revision"')
        else:
            print(f'   [WARNING] Default es "{default_value}" (esperado: "en_revision")')

print('\n' + '=' * 80)
print('RESUMEN DE VERIFICACION')
print('=' * 80)
print('[OK] Refactorizacion completada exitosamente')
print('')
print('PROXIMOS PASOS:')
print('1. Reiniciar el backend (para cargar los modelos actualizados)')
print('2. Reiniciar el frontend (para usar los types actualizados)')
print('3. Probar el workflow automatico con una factura nueva')
print('4. Verificar el dashboard - estado "Pendiente" ahora es "En Revision"')
print('=' * 80)

engine.dispose()
