"""Wrapper para ejecutar importación sin problemas de encoding."""
import sys
import os

# Forzar encoding UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Importar y ejecutar
from app.scripts.importar_historial_excel import main

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
