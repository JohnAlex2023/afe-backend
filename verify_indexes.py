from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.database_url)

with engine.connect() as conn:
    result = conn.execute(text("SHOW INDEX FROM facturas WHERE Key_name LIKE 'idx_facturas%'"))

    print("\n" + "="*90)
    print("INDICES CREADOS EN TABLA FACTURAS")
    print("="*90)
    print(f"{'Index Name':<45} | {'Column':<20} | {'Seq':<5}")
    print("-"*90)

    for row in result:
        print(f"{row[2]:<45} | {row[4]:<20} | {row[3]:<5}")

    print("="*90)
