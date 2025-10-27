# app/db/init_db.py
from sqlalchemy.orm import Session
from app.models.role import Role
from app.models.responsable import Responsable
from app.core.security import hash_password
from app.utils.logger import logger


def create_default_roles_and_admin(db: Session):
    # === Crear roles si no existen ===
    roles = {"admin", "responsable"}
    for role_name in roles:
        if not db.query(Role).filter(Role.nombre == role_name).first():
            db.add(Role(nombre=role_name))
            logger.info("Rol creado: %s", role_name)
    db.commit()

    # === Crear usuario admin si no existe ===
    admin = db.query(Responsable).filter(Responsable.usuario == "alex.taimal").first()
    if not admin:
        # buscar el rol admin
        admin_role = db.query(Role).filter(Role.nombre == "admin").first()

        admin = Responsable(
            usuario="",
            nombre="John Alex",
            email="jhontaimal@gmail.com",
            hashed_password=hash_password("87654321"),
            activo=True,
            role_id=admin_role.id if admin_role else None,
            must_change_password=True  # <-- mejora para seguridad
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        logger.info("Admin creado: %s", admin.usuario)
    else:
        logger.info("Admin ya existe: %s", admin.usuario)
