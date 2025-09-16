
from sqlalchemy.orm import Session
from app.models.role import Role
from app.models.responsable import Responsable
from app.core.security import hash_password
from app.utils.logger import logger

def create_default_roles_and_admin(db: Session):
	# crear roles si no existen
	if not db.query(Role).filter(Role.nombre == "admin").first():
		db.add(Role(nombre="admin"))
	if not db.query(Role).filter(Role.nombre == "responsable").first():
		db.add(Role(nombre="responsable"))
	db.commit()

	# crear admin responsable si no existe
	admin = db.query(Responsable).filter(Responsable.usuario == "admin").first()
	if not admin:
		admin = Responsable(
			usuario="admin",
			nombre="Administrador",
			email="admin@example.com",
			hashed_password=hash_password("Admin123!"),
			activo=True
		)
		db.add(admin)
		db.commit()
		db.refresh(admin)
		logger.info("Admin created: %s", admin.usuario)