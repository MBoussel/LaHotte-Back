"""Schémas Pydantic pour la validation des cadeaux"""
from pydantic import BaseModel, Field
from typing import Optional


class CadeauBase(BaseModel):
    """Schéma de base pour un cadeau"""
    titre: str = Field(..., min_length=1, max_length=200)
    prix: float = Field(..., gt=0)
    description: Optional[str] = Field("", max_length=1000)


class CadeauCreate(CadeauBase):
    """Schéma pour créer un cadeau"""
    famille_id: int = Field(..., description="ID de la famille")


class CadeauUpdate(BaseModel):
    """Schéma pour modifier un cadeau"""
    titre: Optional[str] = Field(None, min_length=1, max_length=200)
    prix: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=1000)


class CadeauResponse(CadeauBase):
    """Schéma pour la réponse"""
    id: int
    owner_id: int
    famille_id: int
    
    class Config:
        from_attributes = True