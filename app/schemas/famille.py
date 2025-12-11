"""Schémas Pydantic pour les familles"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FamilleBase(BaseModel):
    """Schéma de base pour une famille"""
    nom: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field("", max_length=1000)
    is_public: bool = Field(False, description="Si la famille est visible dans la recherche")


class FamilleCreate(FamilleBase):
    """Schéma pour créer une famille"""
    pass


class FamilleUpdate(BaseModel):
    """Schéma pour modifier une famille"""
    nom: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class MembreSimple(BaseModel):
    """Infos simplifiées d'un membre"""
    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class FamilleResponse(FamilleBase):
    """Schéma pour la réponse"""
    id: int
    creator_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class FamilleWithMembres(FamilleResponse):
    """Schéma de famille avec la liste des membres"""
    membres: List[MembreSimple] = []
    
    model_config = {
        "from_attributes" : True
        }