"""Modèle SQLAlchemy 2.0 pour les invitations"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.famille import Famille


class Invitation(Base):
    """
    Table des invitations à rejoindre une famille.
    
    Attributs:
        id: Identifiant unique
        famille_id: ID de la famille
        email: Email de la personne invitée
        token: Token unique pour accepter l'invitation
        accepted: Si l'invitation a été acceptée
        created_at: Date de création
    """
    __tablename__ = "invitations"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    famille_id: Mapped[int] = mapped_column(ForeignKey("familles.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), index=True)
    token: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    
    # Relation
    famille: Mapped["Famille"] = relationship(back_populates="invitations")
    
    def __repr__(self) -> str:
        return f"<Invitation(id={self.id}, email='{self.email}', famille_id={self.famille_id})>"