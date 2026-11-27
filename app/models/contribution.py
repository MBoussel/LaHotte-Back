"""Modèle SQLAlchemy 2.0 pour les contributions."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Numeric, ForeignKey, Boolean, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.cadeau import Cadeau
    from app.models.beneficiaire import Beneficiaire
    from app.models.famille import Famille


class Contribution(Base):
    """Une contribution à la cagnotte d'une personne.

    cadeau_id est conservé à titre d'origine/historique lorsqu'une contribution
    est initiée depuis une fiche cadeau. Les nouvelles contributions globales
    n'ont pas de cadeau associé.
    """
    __tablename__ = "contributions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    famille_id: Mapped[int] = mapped_column(ForeignKey("familles.id", ondelete="CASCADE"), nullable=False, index=True)
    cadeau_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cadeaux.id", ondelete="SET NULL"), nullable=True
    )
    beneficiaire_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    beneficiaire_profil_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("beneficiaires.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    montant: Mapped[float] = mapped_column(Numeric(10, 2))
    message: Mapped[Optional[str]] = mapped_column(Text, default="")
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())

    famille: Mapped["Famille"] = relationship()
    cadeau: Mapped[Optional["Cadeau"]] = relationship(back_populates="contributions")
    user: Mapped["User"] = relationship(back_populates="contributions", foreign_keys=[user_id])
    beneficiaire_user: Mapped[Optional["User"]] = relationship(foreign_keys=[beneficiaire_user_id])
    beneficiaire_profil: Mapped[Optional["Beneficiaire"]] = relationship()

    def __repr__(self) -> str:
        return (
            f"<Contribution(id={self.id}, beneficiaire_user_id={self.beneficiaire_user_id}, "
            f"beneficiaire_profil_id={self.beneficiaire_profil_id}, montant={self.montant})>"
        )
