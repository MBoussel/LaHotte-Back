"""Schémas Pydantic pour les invitations"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class InvitationCreate(BaseModel):
    """Schéma pour créer une invitation"""
    email: EmailStr


class InvitationResponse(BaseModel):
    """Schéma pour la réponse"""
    id: int
    famille_id: int
    email: str
    token: str
    accepted: bool
    created_at: datetime
    famille_nom: Optional[str] = None  # Nom de la famille
    
    class Config:
        from_attributes = True