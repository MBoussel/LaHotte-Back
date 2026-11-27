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


def _peut_voir_contributions(
    famille: Famille,
    current_user: User,
    beneficiaire_user_id: int | None,
    beneficiaire_profil: Beneficiaire | None = None,
) -> bool:
    """Le Père/Mère Noël voit les autres cagnottes ; le créateur voit uniquement la sienne."""
    is_santa = famille.pere_noel_id == current_user.id
    is_creator = famille.creator_id == current_user.id
    profil_est_santa = (
        beneficiaire_profil is not None
        and any(responsable.id == famille.pere_noel_id for responsable in beneficiaire_profil.responsables)
    )
    beneficiaire_est_santa = beneficiaire_user_id == famille.pere_noel_id or profil_est_santa
    return (
        (is_santa and not beneficiaire_est_santa)
        or (is_creator and famille.pere_noel_id is not None and beneficiaire_est_santa)
    )


def _beneficiaire_visible_pour_membre(
    famille: Famille,
    current_user: User,
    beneficiaire_user_id: int | None,
    beneficiaire_profil: Beneficiaire | None = None,
) -> bool:
    """Tout membre peut contribuer à la cagnotte d'un autre membre, jamais à la sienne.

    Les rôles Père/Mère Noël et créateur ne limitent pas les contributions.
    L'appartenance à la famille est vérifiée séparément.
    """
    if beneficiaire_user_id == current_user.id:
        return False
    if beneficiaire_profil is not None and any(
        responsable.id == current_user.id
        for responsable in beneficiaire_profil.responsables
    ):
        return False
    return True


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
    profil = None
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

    if not _beneficiaire_visible_pour_membre(
        famille, current_user, beneficiaire_user_id, profil
    ):
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez pas contribuer à cette cagnotte"
        )

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
    beneficiaire_profil: Beneficiaire | None = None,
) -> List[Dict[str, Any]]:
    _famille_accessible(famille, current_user)
    if not _peut_voir_contributions(famille, current_user, beneficiaire_user_id, beneficiaire_profil):
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
    return _lister_cagnotte(db, current_user, famille, beneficiaire_profil_id=profil_id, beneficiaire_profil=profil)


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
        return _lister_cagnotte(db, current_user, famille, beneficiaire_profil_id=cadeau.beneficiaire_profil_id, beneficiaire_profil=cadeau.beneficiaire_profil)
    recipient_id = cadeau.beneficiaires[0].id if cadeau.beneficiaires else cadeau.owner_id
    return _lister_cagnotte(db, current_user, famille, beneficiaire_user_id=recipient_id)


@router.get("/familles/{famille_id}/recap-contributeurs")
def recap_totaux_contributeurs(
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Totaux donnés par contributeur, réservés au Père/Mère Noël."""
    from sqlalchemy import or_

    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    if not famille:
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    _famille_accessible(famille, current_user)

    # Ne pas exposer ces totaux au créateur ni aux autres membres.
    if famille.pere_noel_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès réservé au Père/Mère Noël")

    profils = db.query(Beneficiaire).filter(
        Beneficiaire.famille_id == famille.id
    ).all()
    user_ids = [m.id for m in famille.membres if m.id != famille.pere_noel_id]
    profil_ids = [
        profil.id for profil in profils
        if all(responsable.id != famille.pere_noel_id for responsable in profil.responsables)
    ]

    conditions = []
    if user_ids:
        conditions.append(Contribution.beneficiaire_user_id.in_(user_ids))
    if profil_ids:
        conditions.append(Contribution.beneficiaire_profil_id.in_(profil_ids))

    rows = (
        db.query(Contribution)
        .filter(
            Contribution.famille_id == famille.id,
            or_(*conditions) if conditions else False,
        )
        .all()
    )

    totaux = {}
    for row in rows:
        contributor = db.query(User).filter(User.id == row.user_id).first()
        key = row.user_id
        if key not in totaux:
            totaux[key] = {
                "contributeur_id": key,
                "contributeur": contributor.username if contributor else "Compte supprimé",
                "total_donne": 0.0,
                "nb_contributions": 0,
            }
        totaux[key]["total_donne"] += float(row.montant)
        totaux[key]["nb_contributions"] += 1

    resultats = sorted(
        totaux.values(),
        key=lambda item: (-item["total_donne"], item["contributeur"].lower()),
    )
    return {"contributions_par_contributeur": resultats}


@router.get("/statistics")
def statistiques_contributions(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    from sqlalchemy import func
    total = db.query(func.sum(Contribution.montant)).filter(Contribution.user_id == current_user.id).scalar() or 0
    count = db.query(func.count(Contribution.id)).filter(Contribution.user_id == current_user.id).scalar() or 0
    return {"total_contribue": float(total), "nombre_contributions": count}


@router.get("/mes-contributions", response_model=List[ContributionResponse])
def mes_contributions(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    rows = db.query(Contribution).filter(
        Contribution.user_id == current_user.id
    ).order_by(Contribution.created_at.desc()).all()

    result = []
    for row in rows:
        if row.beneficiaire_user_id is not None:
            beneficiaire_nom = row.beneficiaire_user.username if row.beneficiaire_user else None
        elif row.beneficiaire_profil_id is not None:
            beneficiaire_nom = row.beneficiaire_profil.nom if row.beneficiaire_profil else None
        else:
            beneficiaire_nom = None

        result.append({
            "id": row.id,
            "cadeau_id": row.cadeau_id,
            "beneficiaire_user_id": row.beneficiaire_user_id,
            "beneficiaire_profil_id": row.beneficiaire_profil_id,
            "beneficiaire_nom": beneficiaire_nom,
            "user_id": row.user_id,
            "montant": row.montant,
            "message": row.message or "",
            "created_at": row.created_at,
        })
    return result


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
