"""Configuration de la base de données avec SQLAlchemy 2.0"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# URL de la base de données SQLite
DATABASE_URL = "sqlite:///./cadeaux.db"

# Créer le moteur SQLAlchemy
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False  # Mettre à True pour voir les requêtes SQL
)

# Créer la session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles"""
    pass


def get_db():
    """
    Générateur de session de base de données.
    À utiliser avec Depends() dans FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()