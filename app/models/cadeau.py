"""Modèle SQLAlchemy 2.0 pour les cadeaux"""
from typing import Optional, TYPE_CHECKING, List
from sqlalchemy import String, Float, Numeric, ForeignKey, Text, Boolean, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.famille import Famille
    from app.models.contribution import Contribution

# Table d'association pour la relation many-to-many entre Cadeau et Famille
cadeau_familles = Table(
    "cadeau_familles",
    Base.metadata,
    Column("cadeau_id", Integer, ForeignKey("cadeaux.id", ondelete="CASCADE"), primary_key=True),
    Column("famille_id", Integer, ForeignKey("familles.id", ondelete="CASCADE"), primary_key=True)
)

# Table d'association pour les bénéficiaires du cadeau
cadeau_beneficiaires = Table(
    "cadeau_beneficiaires",
    Base.metadata,
    Column("cadeau_id", Integer, ForeignKey("cadeaux.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)


class Cadeau(Base):
    """
    Table des cadeaux dans la base de données.
    
    Un cadeau appartient à un créateur (owner) ET peut avoir plusieurs bénéficiaires.
    """
    __tablename__ = "cadeaux"
    
    # Colonnes
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    titre: Mapped[str] = mapped_column(String(200))
    prix: Mapped[float] = mapped_column(Numeric(10, 2))
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    photo_url: Mapped[Optional[str]] = mapped_column(Text, default="")
    lien_achat: Mapped[Optional[str]] = mapped_column(Text, default="")
    is_purchased: Mapped[bool] = mapped_column(Boolean, default=False)
    purchased_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Foreign keys
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    
    # Relations
    owner: Mapped["User"] = relationship(back_populates="cadeaux", foreign_keys=[owner_id])
    familles: Mapped[List["Famille"]] = relationship(
        secondary=cadeau_familles,
        back_populates="cadeaux"
    )
    beneficiaires: Mapped[List["User"]] = relationship(
        secondary=cadeau_beneficiaires,
        backref="cadeaux_recus"
    )
    contributions: Mapped[List["Contribution"]] = relationship(
        back_populates="cadeau",
        cascade="all, delete-orphan"
    )
    purchased_by: Mapped[Optional["User"]] = relationship(foreign_keys=[purchased_by_id])
    
    def __repr__(self) -> str:
        return f"<Cadeau(id={self.id}, titre='{self.titre}', owner_id={self.owner_id})>"
