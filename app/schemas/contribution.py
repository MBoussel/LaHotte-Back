"""Schémas Pydantic pour les contributions."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ContributionCreate(BaseModel):
    montant: float = Field(..., ge=0.01, description="Montant de la contribution")


class ContributionResponse(BaseModel):
    id: int
    cadeau_id: Optional[int] = None
    beneficiaire_user_id: Optional[int] = None
    beneficiaire_profil_id: Optional[int] = None
    beneficiaire_nom: Optional[str] = None
    user_id: int
    montant: float
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContributionWithUser(BaseModel):
    id: int
    montant: float
    message: str
    created_at: datetime
    contributeur: Optional[str] = None

    class Config:
        from_attributes = True
