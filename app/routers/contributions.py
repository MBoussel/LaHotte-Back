"""Routes API pour les contributions"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.contribution import Contribution
from app.models.cadeau import Cadeau
from app.models.user import User
from app.schemas.contribution import ContributionCreate, ContributionResponse, ContributionWithUser
from app.core.security import get_current_active_user

router = APIRouter(
    prefix="/contributions",
    tags=["Contributions"]
)


@router.post("/cadeaux/{cadeau_id}", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
def contribuer_cadeau(
    cadeau_id: int,
    contribution: ContributionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Contribuer à un cadeau.
    """
    # Vérifier que le cadeau existe
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeau non trouvé"
        )
    
    # Vérifier que je ne contribue pas à mon propre cadeau
    if cadeau.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas contribuer à votre propre cadeau"
        )
    
    # Vérifier que je suis membre d'au moins une famille où se trouve le cadeau
    is_member = any(current_user in famille.membres for famille in cadeau.familles)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous devez être membre de la famille"
        )
    
    # Créer la contribution
    db_contribution = Contribution(
        cadeau_id=cadeau_id,
        user_id=current_user.id,
        montant=contribution.montant,
        message=contribution.message,
        is_anonymous=contribution.is_anonymous
    )
    
    db.add(db_contribution)
    db.commit()
    db.refresh(db_contribution)
    
    return db_contribution


@router.get("/cadeaux/{cadeau_id}", response_model=None)
def lister_contributions_cadeau(
    cadeau_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lister toutes les contributions d'un cadeau.
    Le propriétaire du cadeau NE PEUT PAS voir les contributions.
    """
    # Vérifier que le cadeau existe
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeau non trouvé"
        )
    
    # Vérifier que je ne suis PAS le propriétaire
    if cadeau.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas voir les contributions de votre propre cadeau"
        )
    
    # Vérifier que je suis membre d'au moins une famille
    is_member = any(current_user in famille.membres for famille in cadeau.familles)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous devez être membre de la famille"
        )
    
    # Récupérer les contributions
    contributions = db.query(Contribution).filter(Contribution.cadeau_id == cadeau_id).all()
    
    # Formater les contributions
    result = []
    for contrib in contributions:
        user = db.query(User).filter(User.id == contrib.user_id).first()
        result.append({
            "id": contrib.id,
            "montant": contrib.montant,
            "message": contrib.message,
            "is_anonymous": contrib.is_anonymous,
            "created_at": contrib.created_at,
            "contributeur": None if contrib.is_anonymous else (user.username if user else "Inconnu")
        })
    
    return result


@router.get("/mes-contributions", response_model=List[ContributionResponse])
def mes_contributions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lister toutes mes contributions.
    """
    contributions = db.query(Contribution).filter(
        Contribution.user_id == current_user.id
    ).all()
    
    return contributions


@router.delete("/{contribution_id}", response_model=None,status_code=status.HTTP_204_NO_CONTENT)
def supprimer_contribution(
    contribution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Supprimer une de mes contributions.
    """
    contribution = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    
    if not contribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contribution non trouvée"
        )
    
    # Vérifier que c'est ma contribution
    if contribution.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez supprimer que vos propres contributions"
        )
    
    db.delete(contribution)
    db.commit()
    
    return None