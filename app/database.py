"""Configuration de la base de données"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# Créer l'engine avec pool_pre_ping pour PostgreSQL
if settings.DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Vérifie que la connexion est valide
        pool_size=10,
        max_overflow=20
    )
else:
    # SQLite pour le dev
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy"""
    pass


def get_db():
    """
    Dependency pour obtenir une session de base de données.
    Yield la session et la ferme automatiquement après utilisation.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()