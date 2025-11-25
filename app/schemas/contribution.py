"""Schémas Pydantic pour les contributions"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ContributionCreate(BaseModel):
    """Schéma pour créer une contribution"""
    montant: float = Field(..., gt=0, description="Montant de la contribution")
    message: Optional[str] = Field("", max_length=500, description="Message optionnel")
    is_anonymous: bool = Field(False, description="Contribution anonyme")


class ContributionResponse(BaseModel):
    """Schéma pour la réponse"""
    id: int
    cadeau_id: int
    user_id: int
    montant: float
    message: str
    is_anonymous: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ContributionWithUser(BaseModel):
    """Schéma de contribution avec info utilisateur"""
    id: int
    montant: float
    message: str
    is_anonymous: bool
    created_at: datetime
    contributeur: Optional[str] = None  # Nom de l'utilisateur (ou None si anonyme)
    
    class Config:
        from_attributes = True