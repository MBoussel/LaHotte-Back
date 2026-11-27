"""Routes API pour les contributions aux cagnottes des bénéficiaires."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.models.contribution import Contribution
from app.models.cadeau import Cadeau
from app.models.beneficiaire import Beneficiaire
from app.models.famille import Famille
from app.models.user import User
from app.schemas.contribution import ContributionCreate, ContributionResponse
from app.core.security import get_current_active_user

router = APIRouter(prefix="/contributions", tags=["Contributions"])


def _famille_accessible(famille: Famille, current_user: User) -> None:
    if current_user not in famille.membres:
        raise HTTPException(status_code=403, detail="Vous devez être membre de la famille")


def _peut_voir_contributions(famille: Famille, current_user: User, beneficiaire_user_id: int | None) -> bool:
    is_santa = famille.pere_noel_id == current_user.id
    is_creator = famille.creator_id == current_user.id
    return (
        (is_santa and beneficiaire_user_id != famille.pere_noel_id)
        or (is_creator and famille.pere_noel_id is not None and beneficiaire_user_id == famille.pere_noel_id)
    )


def _creer_contribution(
    db: Session,
    current_user: User,
    contribution: ContributionCreate,
    *,
    famille: Famille,
    beneficiaire_user_id: int | None = None,
    beneficiaire_profil_id: int | None = None,
    cadeau_id: int | None = None,
):
    _famille_accessible(famille, current_user)
    if beneficiaire_user_id is not None and beneficiaire_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas contribuer à votre propre cagnotte")
    if beneficiaire_profil_id is not None:
        profil = db.query(Beneficiaire).filter(
            Beneficiaire.id == beneficiaire_profil_id,
            Beneficiaire.famille_id == famille.id,
        ).first()
        if not profil:
            raise HTTPException(status_code=404, detail="Bénéficiaire introuvable")
    elif beneficiaire_user_id is not None:
        target = db.query(User).filter(User.id == beneficiaire_user_id).first()
        if not target or target not in famille.membres:
            raise HTTPException(status_code=404, detail="Bénéficiaire introuvable dans cette famille")
    else:
        raise HTTPException(status_code=400, detail="Bénéficiaire manquant")

    row = Contribution(
        famille_id=famille.id,
        cadeau_id=cadeau_id,
        beneficiaire_user_id=beneficiaire_user_id,
        beneficiaire_profil_id=beneficiaire_profil_id,
        user_id=current_user.id,
        montant=contribution.montant,
        message="",
        is_anonymous=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _lister_cagnotte(
    db: Session,
    current_user: User,
    famille: Famille,
    *,
    beneficiaire_user_id: int | None = None,
    beneficiaire_profil_id: int | None = None,
) -> List[Dict[str, Any]]:
    _famille_accessible(famille, current_user)
    if not _peut_voir_contributions(famille, current_user, beneficiaire_user_id):
        raise HTTPException(status_code=403, detail="Vous n'avez pas accès aux détails de cette cagnotte")
    query = db.query(Contribution).filter(Contribution.famille_id == famille.id)
    if beneficiaire_profil_id is not None:
        query = query.filter(Contribution.beneficiaire_profil_id == beneficiaire_profil_id)
    else:
        query = query.filter(Contribution.beneficiaire_user_id == beneficiaire_user_id)
    result = []
    for row in query.order_by(Contribution.created_at.desc()).all():
        contributor = db.query(User).filter(User.id == row.user_id).first()
        result.append({
            "id": row.id,
            "montant": float(row.montant),
            "message": row.message or "",
            "created_at": row.created_at,
            "contributeur": contributor.username if contributor else "Inconnu",
        })
    return result


@router.post("/personnes/utilisateurs/{user_id}", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
def contribuer_cagnotte_utilisateur(
    user_id: int,
    contribution: ContributionCreate,
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    if not famille:
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    return _creer_contribution(db, current_user, contribution, famille=famille, beneficiaire_user_id=user_id)


@router.post("/personnes/profils/{profil_id}", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
def contribuer_cagnotte_profil(
    profil_id: int,
    contribution: ContributionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profil = db.query(Beneficiaire).filter(Beneficiaire.id == profil_id).first()
    if not profil:
        raise HTTPException(status_code=404, detail="Bénéficiaire non trouvé")
    famille = db.query(Famille).filter(Famille.id == profil.famille_id).first()
    return _creer_contribution(db, current_user, contribution, famille=famille, beneficiaire_profil_id=profil_id)


@router.get("/personnes/utilisateurs/{user_id}", response_model=List[Dict[str, Any]])
def lister_cagnotte_utilisateur(
    user_id: int,
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    if not famille:
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    return _lister_cagnotte(db, current_user, famille, beneficiaire_user_id=user_id)


@router.get("/personnes/profils/{profil_id}", response_model=List[Dict[str, Any]])
def lister_cagnotte_profil(
    profil_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profil = db.query(Beneficiaire).filter(Beneficiaire.id == profil_id).first()
    if not profil:
        raise HTTPException(status_code=404, detail="Bénéficiaire non trouvé")
    famille = db.query(Famille).filter(Famille.id == profil.famille_id).first()
    return _lister_cagnotte(db, current_user, famille, beneficiaire_profil_id=profil_id)


@router.post("/cadeaux/{cadeau_id}", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
def contribuer_cadeau(
    cadeau_id: int,
    contribution: ContributionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(status_code=404, detail="Cadeau non trouvé")
    if len(cadeau.familles) != 1:
        raise HTTPException(status_code=400, detail="Ce cadeau doit être associé à une seule famille")
    famille = cadeau.familles[0]
    _famille_accessible(famille, current_user)

    if cadeau.beneficiaire_profil_id is not None:
        return _creer_contribution(
            db, current_user, contribution, famille=famille,
            beneficiaire_profil_id=cadeau.beneficiaire_profil_id, cadeau_id=cadeau.id,
        )
    if len(cadeau.beneficiaires) > 1:
        raise HTTPException(status_code=409, detail="Ce cadeau a plusieurs bénéficiaires. Corrigez son destinataire avant toute contribution.")
    recipient_id = cadeau.beneficiaires[0].id if cadeau.beneficiaires else cadeau.owner_id
    return _creer_contribution(
        db, current_user, contribution, famille=famille,
        beneficiaire_user_id=recipient_id, cadeau_id=cadeau.id,
    )


@router.get("/cadeaux/{cadeau_id}", response_model=List[Dict[str, Any]])
def lister_contributions_cadeau(
    cadeau_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(status_code=404, detail="Cadeau non trouvé")
    if len(cadeau.familles) != 1:
        raise HTTPException(status_code=400, detail="Ce cadeau doit être associé à une seule famille")
    famille = cadeau.familles[0]
    _famille_accessible(famille, current_user)
    if cadeau.beneficiaire_profil_id is not None:
        return _lister_cagnotte(db, current_user, famille, beneficiaire_profil_id=cadeau.beneficiaire_profil_id)
    recipient_id = cadeau.beneficiaires[0].id if cadeau.beneficiaires else cadeau.owner_id
    return _lister_cagnotte(db, current_user, famille, beneficiaire_user_id=recipient_id)


@router.get("/statistics")
def statistiques_contributions(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    from sqlalchemy import func
    total = db.query(func.sum(Contribution.montant)).filter(Contribution.user_id == current_user.id).scalar() or 0
    count = db.query(func.count(Contribution.id)).filter(Contribution.user_id == current_user.id).scalar() or 0
    return {"total_contribue": float(total), "nombre_contributions": count}


@router.get("/mes-contributions", response_model=List[ContributionResponse])
def mes_contributions(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return db.query(Contribution).filter(Contribution.user_id == current_user.id).all()


@router.delete("/{contribution_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_contribution(contribution_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    row = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Contribution non trouvée")
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres contributions")
    db.delete(row)
    db.commit()


@router.put("/{contribution_id}", response_model=ContributionResponse)
def modifier_contribution(
    contribution_id: int,
    montant: float = None,
    message: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.query(Contribution).filter(Contribution.id == contribution_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Contribution non trouvée")
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres contributions")
    if montant is not None:
        if montant < 0.01:
            raise HTTPException(status_code=422, detail="Le montant doit être positif")
        row.montant = montant
    if message is not None:
        row.message = message
    db.commit()
    db.refresh(row)
    return row
