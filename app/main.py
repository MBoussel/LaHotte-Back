"""
API Liste de Noël 🎄
Application FastAPI pour gérer des listes de cadeaux
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import cadeaux, auth, familles

# Créer les tables dans la base de données
Base.metadata.create_all(bind=engine)

# Créer l'application FastAPI
app = FastAPI(
    title="API Liste de Noël 🎄",
    description="Une API pour gérer les listes de cadeaux de Noël en famille",
    version="1.0.0"
)

# Configuration CORS (pour permettre les requêtes depuis un frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routes
app.include_router(cadeaux.router)
app.include_router(auth.router)
app.include_router(familles.router) 


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
            "familles": "/familles" 
        }
    }


@app.get("/health", tags=["Root"])
def health_check():
    """
    Vérifier que l'API fonctionne.
    """
    return {"status": "healthy"}