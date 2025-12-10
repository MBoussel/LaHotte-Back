"""Modèle SQLAlchemy 2.0 pour les utilisateurs"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from sqlalchemy import String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.cadeau import Cadeau
    from app.models.famille import Famille
from app.models.contribution import Contribution

class User(Base):
    """
    Table des utilisateurs dans la base de données.
    """
    __tablename__ = "users"
    
    # Colonnes
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(100), default="")
    last_name: Mapped[Optional[str]] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    
    # Relations
    cadeaux: Mapped[List["Cadeau"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="Cadeau.owner_id"
    )
    contributions: Mapped[List["Contribution"]] = relationship(
    back_populates="user",
    cascade="all, delete-orphan"
)

    
    # Familles créées par l'utilisateur
    familles_creees: Mapped[List["Famille"]] = relationship(
        back_populates="creator",
        cascade="all, delete-orphan",
        foreign_keys="Famille.creator_id"
    )
    
    # Familles dont l'utilisateur est membre
    familles: Mapped[List["Famille"]] = relationship(
        secondary="famille_membres",
        back_populates="membres"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"