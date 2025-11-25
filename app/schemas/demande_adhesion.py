"""Schémas Pydantic pour les demandes d'adhésion"""
from pydantic import BaseModel
from datetime import datetime


class DemandeAdhesionCreate(BaseModel):
    """Schéma pour créer une demande"""
    message: str = ""


class DemandeAdhesionResponse(BaseModel):
    """Schéma pour la réponse"""
    id: int
    famille_id: int
    user_id: int
    message: str
    created_at: datetime
    user_username: str | None = None
    user_email: str | None = None
    
    class Config:
        from_attributes = True