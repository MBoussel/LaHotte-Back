"""Schémas Pydantic pour les utilisateurs"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Schéma de base pour un utilisateur"""
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    username: str = Field(..., min_length=3, max_length=50, description="Nom d'utilisateur")
    first_name: Optional[str] = Field("", max_length=100)
    last_name: Optional[str] = Field("", max_length=100)


class UserCreate(UserBase):
    """Schéma pour créer un utilisateur"""
    password: str = Field(..., min_length=6, description="Mot de passe (min 6 caractères)")


class UserUpdate(BaseModel):
    """Schéma pour modifier un utilisateur"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


class UserResponse(UserBase):
    """Schéma pour la réponse (sans le mot de passe !)"""
    id: int
    is_active: bool
    is_admin: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True
        from_attributes = True


class Token(BaseModel):
    """Schéma pour le token JWT"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Données contenues dans le token"""
    email: Optional[str] = None
# Ajoute is_admin à UserResponse (trouve la classe et ajoute le champ)
