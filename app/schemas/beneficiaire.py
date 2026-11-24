"""Schémas API pour les profils bénéficiaires sans compte."""
from pydantic import BaseModel, Field, field_validator
from typing import List

class BeneficiaireCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    responsable_ids: List[int] = Field(default_factory=list)

    @field_validator('nom', mode='before')
    @classmethod
    def capitaliser_nom(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value[:1].upper() + value[1:] if value else value
        return value

class ResponsablesUpdate(BaseModel):
    responsable_ids: List[int] = Field(..., min_length=1)

