"""Modèle SQLAlchemy 2.0 pour les demandes d'adhésion"""
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.famille import Famille


class DemandeAdhesion(Base):
    """
    Table des demandes pour rejoindre une famille publique.
    
    Attributs:
        id: Identifiant unique
        famille_id: ID de la famille
        user_id: ID de l'utilisateur qui demande
        message: Message optionnel
        created_at: Date de la demande
    """
    __tablename__ = "demandes_adhesion"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    famille_id: Mapped[int] = mapped_column(ForeignKey("familles.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    
    # Relations
    famille: Mapped["Famille"] = relationship()
    user: Mapped["User"] = relationship()
    
    def __repr__(self) -> str:
        return f"<DemandeAdhesion(id={self.id}, user_id={self.user_id}, famille_id={self.famille_id})>"