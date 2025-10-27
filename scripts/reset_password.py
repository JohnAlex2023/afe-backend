"""
Script para resetear la contraseña de un responsable.
Uso: python scripts/reset_password.py <usuario_o_email> <nueva_password>
"""
import sys
from passlib.context import CryptContext
from app.db.session import SessionLocal
from app.models.responsable import Responsable

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

try:
    # Obtener argumentos
    usuario_input = sys.argv[1] if len(sys.argv) > 1 else "alexander.taimal"
    nueva_password = sys.argv[2] if len(sys.argv) > 2 else "12345678"

    # Buscar responsable por usuario o email
    responsable = db.query(Responsable).filter(
        (Responsable.usuario == usuario_input) | (Responsable.email == usuario_input)
    ).first()

    if not responsable:
        print(f" Responsable '{usuario_input}' no encontrado")
    else:
        # Generar nuevo hash
        nuevo_hash = pwd_context.hash(nueva_password)

        print(f"Responsable encontrado: {responsable.nombre}")
        print(f"Hash anterior: {responsable.hashed_password[:50]}...")
        print(f"Hash nuevo:    {nuevo_hash[:50]}...")

        # Actualizar
        responsable.hashed_password = nuevo_hash
        db.commit()

        # Verificar
        es_valida = pwd_context.verify(nueva_password, responsable.hashed_password)
        print(f"\n  Contraseña actualizada exitosamente!")
        print(f"   Verificación: {'  VÁLIDA' if es_valida else ' INVÁLIDA'}")
        print(f"\n🔑 Credenciales:")
        print(f"   Usuario: {responsable.usuario}")
        print(f"   Contraseña: {nueva_password}")

except Exception as e:
    print(f" Error: {e}")
    db.rollback()
finally:
    db.close()
