@echo off
echo 🚀 Activando entorno virtual AFE Backend...
call venv\Scripts\activate.bat
echo  Entorno virtual activado. Ahora puedes ejecutar:
echo   - alembic current
echo   - uvicorn app.main:app --reload --port 8000
echo   - pytest tests/
cmd /k