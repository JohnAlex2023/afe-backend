# AFE Backend

Proyecto FastAPI para gestión de facturas (AFE). Estructura modular y profesional.

Quickstart:
1. Copia `.env.example` → `.env` y rellena.
2. Instala dependencias: `pip install -r requirements.txt`
3. Levanta MySQL (o usa docker-compose).
4. Genera y aplica migraciones con Alembic o usa `create_all` en desarrollo:
   - `alembic revision --autogenerate -m "init"`
   - `alembic upgrade head`
5. Ejecuta el servidor:
   - `uvicorn app.main:app --reload --port 8000`

Docs disponibles en `/docs`.
