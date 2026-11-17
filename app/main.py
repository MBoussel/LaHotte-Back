"""
API Liste de Noël 🎄
Application FastAPI pour gérer des listes de cadeaux
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.database import engine, Base
from app.routers import cadeaux, auth, familles, contributions

# Créer les tables dans la base de données
Base.metadata.create_all(bind=engine)

# Créer l'application FastAPI
app = FastAPI(
    title="API Liste de Noël 🎄",
    description="Une API pour gérer les listes de cadeaux de Noël en famille",
    version="1.0.0"
)

# Protection CSRF : les requêtes qui modifient des données et utilisent le
# cookie de session doivent provenir d'une origine frontend explicitement autorisée.
TRUSTED_FRONTEND_ORIGINS = {
    origin.rstrip("/")
    for origin in (
        settings.FRONTEND_URL,
        "https://deploy-preview-11--lahotte.netlify.app",
    )
    if origin
}

@app.middleware("http")
async def protect_cookie_authenticated_writes(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.cookies.get("access_token"):
        origin = request.headers.get("origin")
        if not origin or origin.rstrip("/") not in TRUSTED_FRONTEND_ORIGINS:
            return JSONResponse(
                status_code=403,
                content={"detail": "Origine de la requête non autorisée"},
            )
    return await call_next(request)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "https://deploy-preview-11--lahotte.netlify.app"],  # Site public + aperçu de la PR famille
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