"""
API Liste de Noël 🎄
Application FastAPI pour gérer des listes de cadeaux
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import engine, Base
from sqlalchemy import text
from app.routers import cadeaux, auth, familles, contributions

# Créer les tables dans la base de données
Base.metadata.create_all(bind=engine)
with engine.begin() as connection:
    connection.execute(text('ALTER TABLE familles ADD COLUMN IF NOT EXISTS pere_noel_id INTEGER REFERENCES users(id) ON DELETE SET NULL'))

# Créer l'application FastAPI
app = FastAPI(
    title="API Liste de Noël 🎄",
    description="Une API pour gérer les listes de cadeaux de Noël en famille",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],  # Depuis .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routes
app.include_router(cadeaux.router)
app.include_router(auth.router)
app.include_router(familles.router) 
app.include_router(contributions.router)


@app.get("/", tags=["Root"])
def root():
    """
    Page d'accueil de l'API.
    """
    return {
        "message": "Bienvenue sur l'API Liste de Noël ! 🎄",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "cadeaux": "/cadeaux",
            "auth": "/auth",
            "familles": "/familles",
            "contributions": "/contributions"
        }
    }


@app.get("/health", tags=["Root"])
def health_check():
    """
    Vérifier que l'API fonctionne.
    """
    return {"status": "healthy"}