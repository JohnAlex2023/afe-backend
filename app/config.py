# app/config.py


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
	database_url: str

	class Config:
		env_file = ".env"

settings = Settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()

