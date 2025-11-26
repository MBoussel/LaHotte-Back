"""Schémas Pydantic pour la validation des cadeaux"""
from pydantic import BaseModel, Field
from typing import Optional, List


class CadeauBase(BaseModel):
    """Schéma de base pour un cadeau"""
    titre: str = Field(..., min_length=1, max_length=200)
    prix: float = Field(..., gt=0)
    description: Optional[str] = Field("", max_length=5000)
    photo_url: Optional[str] = Field("", max_length=500)
    lien_achat: Optional[str] = Field("", max_length=500)


class CadeauCreate(CadeauBase):
    """Schéma pour créer un cadeau"""
    famille_ids: List[int] = Field(..., description="IDs des familles où ajouter le cadeau")


class CadeauUpdate(BaseModel):
    """Schéma pour modifier un cadeau"""
    titre: Optional[str] = Field(None, min_length=1, max_length=200)
    prix: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=5000)
    photo_url: Optional[str] = Field(None, max_length=500)
    lien_achat: Optional[str] = Field(None, max_length=500)


class CadeauResponse(CadeauBase):
    """Schéma pour la réponse"""
    id: int
    owner_id: int
    is_purchased: bool
    purchased_by_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class CadeauWithVisibility(CadeauResponse):
    """Schéma avec infos de visibilité des contributions"""
    can_see_contributions: bool
    total_contributions: Optional[float] = None
    nb_contributions: Optional[int] = None