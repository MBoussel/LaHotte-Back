"""Modèle SQLAlchemy 2.0 pour les contributions"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Numeric, ForeignKey, Boolean, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.cadeau import Cadeau


class Contribution(Base):
    """
    Table des contributions aux cadeaux.
    
    Attributs:
        id: Identifiant unique
        cadeau_id: ID du cadeau
        user_id: ID de l'utilisateur qui contribue
        montant: Montant de la contribution
        message: Message optionnel
        is_anonymous: Si la contribution est anonyme
        created_at: Date de la contribution
    """
    __tablename__ = "contributions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cadeau_id: Mapped[int] = mapped_column(ForeignKey("cadeaux.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    montant: Mapped[float] = mapped_column(Numeric(10, 2))
    message: Mapped[Optional[str]] = mapped_column(Text, default="")
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())
    
    # Relations
    cadeau: Mapped["Cadeau"] = relationship(back_populates="contributions")
    user: Mapped["User"] = relationship(back_populates="contributions")
    
    def __repr__(self) -> str:
        return f"<Contribution(id={self.id}, cadeau_id={self.cadeau_id}, montant={self.montant})>"
