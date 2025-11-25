"""Modèle SQLAlchemy 2.0 pour les familles"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from sqlalchemy import String, ForeignKey, Table, Column, Integer, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.cadeau import Cadeau
    from app.models.invitation import Invitation

# Table d'association pour la relation many-to-many entre User et Famille
famille_membres = Table(
    "famille_membres",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("famille_id", Integer, ForeignKey("familles.id", ondelete="CASCADE"), primary_key=True)
)


class Famille(Base):
    """
    Table des familles dans la base de données.
    
    Attributs:
        id: Identifiant unique de la famille
        nom: Nom de la famille
        description: Description optionnelle
        creator_id: ID du créateur de la famille
        created_at: Date de création
        creator: Relation vers le créateur
        membres: Liste des membres de la famille
        cadeaux: Liste des cadeaux de la famille
        invitations: Liste des invitations envoyées
    """
    __tablename__ = "familles"
    
    # Colonnes
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nom: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(String(1000), default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    
    # Relations
    creator: Mapped["User"] = relationship(back_populates="familles_creees", foreign_keys=[creator_id])
    membres: Mapped[List["User"]] = relationship(
        secondary=famille_membres,
        back_populates="familles"
    )
    cadeaux: Mapped[List["Cadeau"]] = relationship(
    secondary="cadeau_familles",
    back_populates="familles"
)
    invitations: Mapped[List["Invitation"]] = relationship(
        back_populates="famille",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Famille(id={self.id}, nom='{self.nom}')>"