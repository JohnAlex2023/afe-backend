#!/usr/bin/env python3
"""
Script de verificación de sincronización de migraciones Alembic
Úsalo después de sincronizar para confirmar que todo está correcto
"""
import subprocess
import sys
import pymysql
from dotenv import load_dotenv
import os

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}[OK] {text}{RESET}")

def print_error(text):
    print(f"{RED}[ERROR] {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}[WARN] {text}{RESET}")

def print_info(text):
    print(f"{BLUE}[INFO] {text}{RESET}")

def run_command(cmd):
    """Ejecuta un comando y retorna su salida"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def check_git_status():
    """Verifica estado de Git"""
    print_header("1. VERIFICACIÓN DE GIT")

    success, stdout, stderr = run_command("git log --oneline -1")
    if success:
        print_success(f"Último commit: {stdout}")
    else:
        print_error("No se pudo obtener información de Git")
        return False

    success, stdout, stderr = run_command("git status --short")
    if success:
        if stdout:
            print_warning("Hay cambios sin commitear:")
            print(stdout)
        else:
            print_success("Working directory limpio")

    return True

def check_alembic_history():
    """Verifica historial de Alembic"""
    print_header("2. VERIFICACIÓN DE MIGRACIONES")

    success, stdout, stderr = run_command("alembic history")
    if not success:
        print_error("Error al obtener historial de Alembic")
        print(stderr)
        return False

    lines = stdout.split('\n')
    if not lines:
        print_error("No se encontraron migraciones")
        return False

    # Verificar que esté la migración esperada
    if "7bad075511e9" in stdout:
        print_success("Migración 7bad075511e9 encontrada")
    else:
        print_error("Migración 7bad075511e9 NO encontrada")
        return False

    if "05b5bdfbca40" in stdout:
        print_success("Migración 05b5bdfbca40 encontrada")
    else:
        print_error("Migración 05b5bdfbca40 NO encontrada")
        return False

    # Contar migraciones
    migration_count = len([l for l in lines if '->' in l])
    print_info(f"Total de migraciones: {migration_count}")

    return True

def check_alembic_current():
    """Verifica versión actual de Alembic"""
    print_header("3. VERIFICACIÓN DE VERSIÓN ACTUAL")

    success, stdout, stderr = run_command("alembic current")
    if not success:
        print_error("Error al obtener versión actual")
        print(stderr)
        return False

    if "7bad075511e9" in stdout and "(head)" in stdout:
        print_success("Base de datos en versión correcta: 7bad075511e9 (head)")
        return True
    else:
        print_error(f"Versión incorrecta. Versión actual: {stdout}")
        print_warning("Ejecuta el script de actualización en MIGRACIONES_SYNC_GUIDE.md")
        return False

def check_database_version():
    """Verifica versión directamente en la base de datos"""
    print_header("4. VERIFICACIÓN DIRECTA EN BASE DE DATOS")

    try:
        load_dotenv()

        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='root',
            database='bd_afe',
            charset='utf8mb4'
        )

        with connection.cursor() as cursor:
            cursor.execute("SELECT version_num FROM alembic_version")
            result = cursor.fetchone()

            if result:
                version = result[0]
                if version == "7bad075511e9":
                    print_success(f"Versión en BD: {version} ✓")
                    return True
                else:
                    print_error(f"Versión en BD: {version} (esperada: 7bad075511e9)")
                    return False
            else:
                print_error("No se encontró versión en alembic_version")
                return False

    except pymysql.Error as e:
        print_error(f"Error de conexión a BD: {e}")
        print_info("Verifica las credenciales en .env")
        return False
    finally:
        if 'connection' in locals():
            connection.close()

def check_migration_files():
    """Verifica que existan los archivos de migración correctos"""
    print_header("5. VERIFICACIÓN DE ARCHIVOS DE MIGRACIÓN")

    import os

    migrations_path = "alembic/versions"

    if not os.path.exists(migrations_path):
        print_error(f"Directorio {migrations_path} no existe")
        return False

    files = os.listdir(migrations_path)
    py_files = [f for f in files if f.endswith('.py') and not f.startswith('__')]

    print_info(f"Total de archivos de migración: {len(py_files)}")

    # Verificar archivos específicos
    expected_files = [
        "05b5bdfbca40_extend_version_algoritmo_length.py",
        "7bad075511e9_add_automation_tables.py"
    ]

    all_found = True
    for expected_file in expected_files:
        if expected_file in files:
            print_success(f"Archivo encontrado: {expected_file}")
        else:
            print_error(f"Archivo NO encontrado: {expected_file}")
            all_found = False

    # Verificar que NO existan los archivos viejos
    old_files = [
        "fix_version_algoritmo_length.py",
        "add_automation_tables.py"
    ]

    for old_file in old_files:
        if old_file in files:
            print_error(f"Archivo VIEJO encontrado (debe eliminarse): {old_file}")
            all_found = False
        else:
            print_success(f"Archivo viejo eliminado correctamente: {old_file}")

    return all_found

def main():
    """Función principal"""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{'  VERIFICACIÓN DE SINCRONIZACIÓN DE MIGRACIONES':^60}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    results = []

    # Ejecutar verificaciones
    results.append(("Git Status", check_git_status()))
    results.append(("Historial de Migraciones", check_alembic_history()))
    results.append(("Versión Actual (Alembic)", check_alembic_current()))
    results.append(("Versión en Base de Datos", check_database_version()))
    results.append(("Archivos de Migración", check_migration_files()))

    # Resumen final
    print_header("RESUMEN DE VERIFICACIÓN")

    all_passed = True
    for name, passed in results:
        if passed:
            print_success(f"{name}: OK")
        else:
            print_error(f"{name}: FALLO")
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print(f"{GREEN}{BOLD}[SUCCESS] SINCRONIZACION COMPLETA Y CORRECTA{RESET}")
        print(f"{GREEN}Ambos equipos estan sincronizados correctamente{RESET}")
        return 0
    else:
        print(f"{RED}{BOLD}[FAILED] SINCRONIZACION INCOMPLETA{RESET}")
        print(f"{YELLOW}Revisa los errores y consulta MIGRACIONES_SYNC_GUIDE.md{RESET}")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Verificacion interrumpida por el usuario{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Error inesperado: {e}{RESET}")
        sys.exit(1)
