"""Schémas Pydantic pour la validation des cadeaux"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List


class CadeauBase(BaseModel):
    """Schéma de base pour un cadeau"""
    titre: str = Field(..., min_length=1, max_length=200)
    prix: float = Field(..., gt=0)
    description: Optional[str] = Field("", max_length=5000)
    photo_url: Optional[str] = Field("", max_length=500)
    lien_achat: Optional[str] = Field("", max_length=500)
    is_favorite: bool = False

    @field_validator('titre', mode='before')
    @classmethod
    def capitaliser_titre(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value[:1].upper() + value[1:] if value else value
        return value


class CadeauCreate(CadeauBase):
    """Schéma pour créer un cadeau"""
    famille_ids: List[int] = Field(..., min_length=1, max_length=1, description="ID de l’unique famille du cadeau")
    beneficiaire_ids: List[int] = Field(default=[], max_length=1, description="Un seul bénéficiaire utilisateur (optionnel)")
    beneficiaire_profil_id: Optional[int] = Field(None, description="Profil sans compte destinataire du cadeau")


class CadeauUpdate(BaseModel):
    """Schéma pour modifier un cadeau"""
    titre: Optional[str] = Field(None, min_length=1, max_length=200)
    prix: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=5000)
    photo_url: Optional[str] = Field(None, max_length=500)
    lien_achat: Optional[str] = Field(None, max_length=500)
    beneficiaire_ids: Optional[List[int]] = Field(None, max_length=1, description="Un seul bénéficiaire utilisateur")
    is_favorite: Optional[bool] = None

    @field_validator('titre', mode='before')
    @classmethod
    def capitaliser_titre(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value[:1].upper() + value[1:] if value else value
        return value


class BeneficiaireSimple(BaseModel):
    """Infos simplifiées d'un bénéficiaire"""
    id: int
    username: str
    
    class Config:
        from_attributes = True


class CadeauResponse(CadeauBase):
    """Schéma pour la réponse"""
    id: int
    owner_id: int
    beneficiaires: List[BeneficiaireSimple] = []
    
    class Config:
        from_attributes = True


class CadeauWithVisibility(CadeauResponse):
    """Schéma avec infos de visibilité des contributions"""
    can_see_contributions: bool
    total_contributions: Optional[float] = None
    nb_contributions: Optional[int] = None
