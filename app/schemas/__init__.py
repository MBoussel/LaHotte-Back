"""Schémas de validation Pydantic"""
from app.schemas.cadeau import CadeauBase, CadeauCreate, CadeauUpdate, CadeauResponse
from app.schemas.user import UserBase, UserCreate, UserUpdate, UserResponse, Token, TokenData
from app.schemas.famille import FamilleBase, FamilleCreate, FamilleUpdate, FamilleResponse, FamilleWithMembres, MembreSimple
from app.schemas.invitation import InvitationCreate, InvitationResponse
from app.schemas.contribution import ContributionCreate, ContributionResponse, ContributionWithUser
__all__ = [
    "CadeauBase", "CadeauCreate", "CadeauUpdate", "CadeauResponse",
    "UserBase", "UserCreate", "UserUpdate", "UserResponse", "Token", "TokenData",
    "FamilleBase", "FamilleCreate", "FamilleUpdate", "FamilleResponse", "FamilleWithMembres", "MembreSimple",
     "InvitationCreate", "InvitationResponse",
     "ContributionCreate", "ContributionResponse", "ContributionWithUser"
]