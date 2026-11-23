"""Schémas API pour les profils bénéficiaires sans compte."""
from pydantic import BaseModel, Field
from typing import List

class BeneficiaireCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    responsable_ids: List[int] = Field(default_factory=list)

class ResponsablesUpdate(BaseModel):
    responsable_ids: List[int] = Field(..., min_length=1)

