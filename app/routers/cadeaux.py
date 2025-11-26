"""Routes pour la gestion des cadeaux"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.cadeau import Cadeau
from app.models.famille import Famille
from app.schemas.cadeau import CadeauCreate, CadeauUpdate, CadeauResponse
from app.core.security import get_current_active_user

router = APIRouter(prefix="/cadeaux", tags=["cadeaux"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def creer_cadeau(
    cadeau: CadeauCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Créer un nouveau cadeau et l'ajouter à plusieurs familles."""
    # Vérifier que toutes les familles existent et que je suis membre
    familles = []
    for famille_id in cadeau.famille_ids:
        famille = db.query(Famille).filter(Famille.id == famille_id).first()
        if not famille:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Famille {famille_id} non trouvée"
            )
        if current_user not in famille.membres:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Vous devez être membre de la famille {famille.nom}"
            )
        familles.append(famille)
    
    # Vérifier les bénéficiaires
    beneficiaires = []
    if cadeau.beneficiaire_ids:
        for benef_id in cadeau.beneficiaire_ids:
            user = db.query(User).filter(User.id == benef_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Utilisateur {benef_id} non trouvé"
                )
            # Vérifier que le bénéficiaire est membre d'au moins une des familles
            is_member = any(user in fam.membres for fam in familles)
            if not is_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{user.username} doit être membre d'au moins une des familles"
                )
            beneficiaires.append(user)
    
    # Créer le cadeau
    db_cadeau = Cadeau(
        titre=cadeau.titre,
        prix=cadeau.prix,
        description=cadeau.description or "",
        photo_url=cadeau.photo_url or "",
        lien_achat=cadeau.lien_achat or "",
        owner_id=current_user.id,
    )
    
    # Ajouter aux familles et bénéficiaires
    db_cadeau.familles = familles
    db_cadeau.beneficiaires = beneficiaires
    
    db.add(db_cadeau)
    db.commit()
    db.refresh(db_cadeau)
    
    return {
        "id": db_cadeau.id,
        "titre": db_cadeau.titre,
        "prix": db_cadeau.prix,
        "description": db_cadeau.description,
        "photo_url": db_cadeau.photo_url,
        "lien_achat": db_cadeau.lien_achat,
        "owner_id": db_cadeau.owner_id,
        "is_purchased": db_cadeau.is_purchased,
        "purchased_by_id": db_cadeau.purchased_by_id,
        "beneficiaires": [{"id": b.id, "username": b.username} for b in db_cadeau.beneficiaires]
    }


@router.get("/")
def lister_tous_cadeaux(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer tous les cadeaux (visible uniquement aux admins ou pour debug)."""
    cadeaux = db.query(Cadeau).offset(skip).limit(limit).all()
    return cadeaux


@router.get("/me")
def lister_mes_cadeaux(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer tous mes cadeaux."""
    cadeaux = db.query(Cadeau).filter(Cadeau.owner_id == current_user.id).all()
    
    result = []
    for cadeau in cadeaux:
        result.append({
            "id": cadeau.id,
            "titre": cadeau.titre,
            "prix": cadeau.prix,
            "description": cadeau.description,
            "photo_url": cadeau.photo_url,
            "lien_achat": cadeau.lien_achat,
            "owner_id": cadeau.owner_id,
            "is_purchased": cadeau.is_purchased,
            "purchased_by_id": cadeau.purchased_by_id,
            "beneficiaires": [{"id": b.id, "username": b.username} for b in cadeau.beneficiaires]
        })
    
    return result


@router.get("/{cadeau_id}")
def recuperer_cadeau(
    cadeau_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer un cadeau spécifique."""
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeau non trouvé"
        )
    
    # Vérifier que je suis membre d'au moins une famille qui contient ce cadeau
    is_member = any(current_user in famille.membres for famille in cadeau.familles)
    if not is_member and cadeau.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas accès à ce cadeau"
        )
    
    return {
        "id": cadeau.id,
        "titre": cadeau.titre,
        "prix": cadeau.prix,
        "description": cadeau.description,
        "photo_url": cadeau.photo_url,
        "lien_achat": cadeau.lien_achat,
        "owner_id": cadeau.owner_id,
        "is_purchased": cadeau.is_purchased,
        "purchased_by_id": cadeau.purchased_by_id,
        "beneficiaires": [{"id": b.id, "username": b.username} for b in cadeau.beneficiaires]
    }


@router.put("/{cadeau_id}")
def modifier_cadeau(
    cadeau_id: int,
    cadeau_update: CadeauUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Modifier un cadeau (seulement le propriétaire)."""
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeau non trouvé"
        )
    
    if cadeau.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas le propriétaire de ce cadeau"
        )
    
    # Mettre à jour les champs
    if cadeau_update.titre is not None:
        cadeau.titre = cadeau_update.titre
    if cadeau_update.prix is not None:
        cadeau.prix = cadeau_update.prix
    if cadeau_update.description is not None:
        cadeau.description = cadeau_update.description
    if cadeau_update.photo_url is not None:
        cadeau.photo_url = cadeau_update.photo_url
    if cadeau_update.lien_achat is not None:
        cadeau.lien_achat = cadeau_update.lien_achat
    
    # Mettre à jour les bénéficiaires si fournis
    if cadeau_update.beneficiaire_ids is not None:
        beneficiaires = []
        for benef_id in cadeau_update.beneficiaire_ids:
            user = db.query(User).filter(User.id == benef_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Utilisateur {benef_id} non trouvé"
                )
            # Vérifier que le bénéficiaire est membre d'au moins une des familles
            is_member = any(user in fam.membres for fam in cadeau.familles)
            if not is_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{user.username} doit être membre d'au moins une des familles"
                )
            beneficiaires.append(user)
        cadeau.beneficiaires = beneficiaires
    
    db.commit()
    db.refresh(cadeau)
    
    return {
        "id": cadeau.id,
        "titre": cadeau.titre,
        "prix": cadeau.prix,
        "description": cadeau.description,
        "photo_url": cadeau.photo_url,
        "lien_achat": cadeau.lien_achat,
        "owner_id": cadeau.owner_id,
        "is_purchased": cadeau.is_purchased,
        "purchased_by_id": cadeau.purchased_by_id,
        "beneficiaires": [{"id": b.id, "username": b.username} for b in cadeau.beneficiaires]
    }


@router.delete("/{cadeau_id}")
def supprimer_cadeau(
    cadeau_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Supprimer un cadeau (seulement le propriétaire)."""
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeau non trouvé"
        )
    
    if cadeau.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas le propriétaire de ce cadeau"
        )
    
    db.delete(cadeau)
    db.commit()
    
    return {"message": "Cadeau supprimé avec succès"}


@router.post("/{cadeau_id}/mark-purchased")
def marquer_achete(
    cadeau_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Marquer un cadeau comme acheté."""
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
            detail="Vous ne pouvez pas acheter votre propre cadeau"
        )
    
    # Vérifier que je suis membre d'une famille qui contient ce cadeau
    is_member = any(current_user in famille.membres for famille in cadeau.familles)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous devez être membre d'une famille pour acheter ce cadeau"
        )
    
    if cadeau.is_purchased:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce cadeau a déjà été acheté"
        )
    
    cadeau.is_purchased = True
    cadeau.purchased_by_id = current_user.id
    
    db.commit()
    db.refresh(cadeau)
    
    return {
        "id": cadeau.id,
        "titre": cadeau.titre,
        "prix": cadeau.prix,
        "description": cadeau.description,
        "photo_url": cadeau.photo_url,
        "lien_achat": cadeau.lien_achat,
        "owner_id": cadeau.owner_id,
        "is_purchased": cadeau.is_purchased,
        "purchased_by_id": cadeau.purchased_by_id,
        "beneficiaires": [{"id": b.id, "username": b.username} for b in cadeau.beneficiaires]
    }


@router.post("/{cadeau_id}/unmark-purchased")
def demarquer_achete(
    cadeau_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Annuler le marquage "acheté" d'un cadeau."""
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    if not cadeau:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cadeau non trouvé"
        )
    
    # Seul celui qui a marqué le cadeau peut le démarquer
    if cadeau.purchased_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas marqué ce cadeau comme acheté"
        )
    
    cadeau.is_purchased = False
    cadeau.purchased_by_id = None
    
    db.commit()
    db.refresh(cadeau)
    
    return {
        "id": cadeau.id,
        "titre": cadeau.titre,
        "prix": cadeau.prix,
        "description": cadeau.description,
        "photo_url": cadeau.photo_url,
        "lien_achat": cadeau.lien_achat,
        "owner_id": cadeau.owner_id,
        "is_purchased": cadeau.is_purchased,
        "purchased_by_id": cadeau.purchased_by_id,
        "beneficiaires": [{"id": b.id, "username": b.username} for b in cadeau.beneficiaires]
    }


@router.get("/famille/{famille_id}")
def lister_cadeaux_famille(
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer tous les cadeaux d'une famille."""
    from sqlalchemy.orm import joinedload
    
    famille = db.query(Famille).options(
        joinedload(Famille.cadeaux).joinedload(Cadeau.beneficiaires)
    ).filter(Famille.id == famille_id).first()
    
    if not famille:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Famille non trouvée"
        )
    
    if current_user not in famille.membres:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous devez être membre de cette famille"
        )
    
    result = []
    for cadeau in famille.cadeaux:
        result.append({
            "id": cadeau.id,
            "titre": cadeau.titre,
            "prix": cadeau.prix,
            "description": cadeau.description,
            "photo_url": cadeau.photo_url,
            "lien_achat": cadeau.lien_achat,
            "owner_id": cadeau.owner_id,
            "is_purchased": cadeau.is_purchased,
            "purchased_by_id": cadeau.purchased_by_id,
            "beneficiaires": [{"id": b.id, "username": b.username} for b in cadeau.beneficiaires]
        })
    
    return result


@router.get("/beneficiaire/me")
def lister_cadeaux_beneficiaire(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer tous les cadeaux dont je suis bénéficiaire."""
    cadeaux = db.query(Cadeau).join(
        Cadeau.beneficiaires
    ).filter(
        User.id == current_user.id
    ).all()
    
    result = []
    for cadeau in cadeaux:
        result.append({
            "id": cadeau.id,
            "titre": cadeau.titre,
            "prix": cadeau.prix,
            "description": cadeau.description,
            "photo_url": cadeau.photo_url,
            "lien_achat": cadeau.lien_achat,
            "owner_id": cadeau.owner_id,
            "is_purchased": cadeau.is_purchased,
            "purchased_by_id": cadeau.purchased_by_id,
            "beneficiaires": [{"id": b.id, "username": b.username} for b in cadeau.beneficiaires]
        })
    
    return result
