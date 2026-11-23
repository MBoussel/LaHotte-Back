"""Profils de bénéficiaires sans compte utilisateur."""
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

beneficiaire_responsables = Table(
    "beneficiaire_responsables",
    Base.metadata,
    Column("beneficiaire_id", Integer, ForeignKey("beneficiaires.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

class Beneficiaire(Base):
    __tablename__ = "beneficiaires"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    famille_id: Mapped[int] = mapped_column(ForeignKey("familles.id", ondelete="CASCADE"), nullable=False, index=True)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(insert_default=func.now())

    responsables: Mapped[List["User"]] = relationship(secondary=beneficiaire_responsables)
    cadeaux: Mapped[List["Cadeau"]] = relationship(back_populates="beneficiaire_profil")
