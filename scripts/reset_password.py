"""
Script para resetear la contraseña de un usuario.
"""
from passlib.context import CryptContext
from app.core.database import SessionLocal
from app.models.usuario import Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

try:
    # Buscar usuario
    usuario = db.query(Usuario).filter(Usuario.usuario == "alex.taimal").first()

    if not usuario:
        print("❌ Usuario alex.taimal no encontrado")
    else:
        # Generar nuevo hash con la contraseña 'zentria2025'
        nueva_password = "zentria2025"
        nuevo_hash = pwd_context.hash(nueva_password)

        print(f"Usuario encontrado: {usuario.nombre}")
        print(f"Hash anterior: {usuario.password_hash[:50]}...")
        print(f"Hash nuevo:    {nuevo_hash[:50]}...")

        # Actualizar
        usuario.password_hash = nuevo_hash
        db.commit()

        # Verificar
        es_valida = pwd_context.verify(nueva_password, usuario.password_hash)
        print(f"\n✅ Contraseña actualizada exitosamente!")
        print(f"   Verificación: {'✅ VÁLIDA' if es_valida else '❌ INVÁLIDA'}")
        print(f"\n🔑 Credenciales:")
        print(f"   Usuario: alex.taimal")
        print(f"   Contraseña: zentria2025")

except Exception as e:
    print(f"❌ Error: {e}")
    db.rollback()
finally:
    db.close()
