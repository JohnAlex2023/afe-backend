"""
Script para verificar usuarios existentes.
"""
from app.core.database import SessionLocal
from app.models.usuario import Usuario
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

try:
    usuarios = db.query(Usuario).all()

    if not usuarios:
        print("❌ No hay usuarios en la base de datos")
    else:
        print(f"\n✅ Usuarios encontrados: {len(usuarios)}\n")
        for u in usuarios:
            print(f"ID: {u.id}")
            print(f"Nombre: {u.nombre}")
            print(f"Usuario: {u.usuario}")
            print(f"Email: {u.email}")
            print(f"Rol: {u.rol}")
            print(f"Activo: {u.activo}")
            print(f"Hash de contraseña: {u.password_hash[:50]}...")
            print("-" * 50)

        # Probar verificación de contraseña
        print("\n🔐 Probando contraseña 'zentria2025' para alex.taimal:")
        alex = db.query(Usuario).filter(Usuario.usuario == "alex.taimal").first()
        if alex:
            es_valida = pwd_context.verify("zentria2025", alex.password_hash)
            print(f"   Resultado: {'✅ VÁLIDA' if es_valida else '❌ INVÁLIDA'}")
        else:
            print("   ❌ Usuario alex.taimal no encontrado")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    db.close()
