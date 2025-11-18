"""Modèle SQLAlchemy 2.0 pour les cadeaux"""
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.famille import Famille


class Cadeau(Base):
    """
    Table des cadeaux dans la base de données.
    
    Un cadeau appartient à un utilisateur ET à une famille.
    """
    __tablename__ = "cadeaux"
    
    # Colonnes
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    titre: Mapped[str] = mapped_column(String(200))
    prix: Mapped[float] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(String(1000), default="")
    
    # Foreign keys
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    famille_id: Mapped[int] = mapped_column(ForeignKey("familles.id", ondelete="CASCADE"))
    
    # Relations
    owner: Mapped["User"] = relationship(back_populates="cadeaux", foreign_keys=[owner_id])
    famille: Mapped["Famille"] = relationship(back_populates="cadeaux")
    
    def __repr__(self) -> str:
        return f"<Cadeau(id={self.id}, titre='{self.titre}', owner_id={self.owner_id}, famille_id={self.famille_id})>"