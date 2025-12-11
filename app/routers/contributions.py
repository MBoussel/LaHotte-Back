"""Routes API pour les contributions"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

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
    """Contribuer à un cadeau."""
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadeau non trouvé")
    
    if cadeau.owner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vous ne pouvez pas contribuer à votre propre cadeau")
    
    is_member = any(current_user in famille.membres for famille in cadeau.familles)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous devez être membre de la famille")
    
    # Vérifier que le montant ne dépasse pas le reste
    from sqlalchemy import func
    total_contribue = db.query(func.sum(Contribution.montant)).filter(
        Contribution.cadeau_id == cadeau_id
    ).scalar() or 0.0
    
    reste = float(cadeau.prix) - float(total_contribue)
    
    if contribution.montant > reste + 0.01:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le montant ne peut pas dépasser le reste à financer ({reste:.2f} €)"
        )

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


@router.get("/cadeaux/{cadeau_id}", response_model=List[Dict[str, Any]])
def lister_contributions_cadeau(
    cadeau_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lister toutes les contributions d'un cadeau."""
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadeau non trouvé")
    
    if cadeau.owner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez pas voir les contributions de votre propre cadeau")
    
    is_member = any(current_user in famille.membres for famille in cadeau.familles)
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous devez être membre de la famille")
    
    contributions = db.query(Contribution).filter(Contribution.cadeau_id == cadeau_id).all()
    
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


@router.get("/statistics")
def statistiques_contributions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer les statistiques de mes contributions."""
    from sqlalchemy import func
    
    total = db.query(func.sum(Contribution.montant)).filter(
        Contribution.user_id == current_user.id
    ).scalar() or 0.0
    
    count = db.query(func.count(Contribution.id)).filter(
        Contribution.user_id == current_user.id
    ).scalar() or 0
    
    return {
        "total_contribue": float(total),
        "nombre_contributions": count
    }


@router.get("/mes-contributions", response_model=List[ContributionResponse])
def mes_contributions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lister toutes mes contributions."""
    contributions = db.query(Contribution).filter(
        Contribution.user_id == current_user.id
    ).all()
    
    return contributions


@router.delete("/{contribution_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_contribution(
    contribution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Supprimer une de mes contributions."""
    contribution = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    
    if not contribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution non trouvée")
    
    if contribution.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres contributions")
    
    db.delete(contribution)
    db.commit()


@router.put("/{contribution_id}", response_model=ContributionResponse)
def modifier_contribution(
    contribution_id: int,
    montant: float = None,
    message: str = None,
    is_anonymous: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Modifier une de mes contributions."""
    contribution = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    
    if not contribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contribution non trouvée"
        )
    
    if contribution.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez modifier que vos propres contributions"
        )
    
    # Mettre à jour les champs
    if montant is not None:
        contribution.montant = montant
    if message is not None:
        contribution.message = message
    if is_anonymous is not None:
        contribution.is_anonymous = is_anonymous
    
    db.commit()
    db.refresh(contribution)
    
    return contribution
