"""Routes API pour les cadeaux"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.models.cadeau import Cadeau
from app.models.user import User
from app.models.famille import Famille
from app.schemas.cadeau import CadeauCreate, CadeauUpdate, CadeauResponse
from app.core.security import get_current_active_user

router = APIRouter(
    prefix="/cadeaux",
    tags=["Cadeaux"]
)


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
    
    # Créer le cadeau
    db_cadeau = Cadeau(
        titre=cadeau.titre,
        prix=cadeau.prix,
        description=cadeau.description or "",
        photo_url=cadeau.photo_url or "",
        lien_achat=cadeau.lien_achat or "",
        owner_id=current_user.id,
    )
    
    # Ajouter aux familles
    db_cadeau.familles = familles
    
    db.add(db_cadeau)
    db.commit()
    db.refresh(db_cadeau)
    
    # Retourner avec les IDs des familles
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
        "famille_ids": [f.id for f in db_cadeau.familles]
    }


@router.get("/", response_model=List[CadeauResponse])
def lister_cadeaux(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Récupérer la liste de tous les cadeaux."""
    cadeaux = db.query(Cadeau).offset(skip).limit(limit).all()
    return cadeaux


@router.get("/me", response_model=List[CadeauResponse])
def lister_mes_cadeaux(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer MES cadeaux (ceux que j'ai créés)."""
    cadeaux = db.query(Cadeau).filter(
        Cadeau.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    return cadeaux


@router.get("/{cadeau_id}", response_model=CadeauResponse)
def obtenir_cadeau(
    cadeau_id: int,
    db: Session = Depends(get_db)
):
    """Récupérer un cadeau spécifique par son ID."""
    cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    
    if not cadeau:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cadeau avec l'ID {cadeau_id} non trouvé"
        )
    
    return cadeau


@router.put("/{cadeau_id}", response_model=CadeauResponse)
def modifier_cadeau(
    cadeau_id: int,
    cadeau_update: CadeauUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Modifier un cadeau existant."""
    db_cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    
    if not db_cadeau:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cadeau avec l'ID {cadeau_id} non trouvé"
        )
    
    # Vérifier que c'est bien MON cadeau
    if db_cadeau.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez modifier que vos propres cadeaux"
        )
    
    # Mettre à jour seulement les champs fournis
    update_data = cadeau_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_cadeau, field, value)
    
    db.commit()
    db.refresh(db_cadeau)
    
    return db_cadeau


@router.delete("/{cadeau_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_cadeau(
    cadeau_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Supprimer un cadeau."""
    db_cadeau = db.query(Cadeau).filter(Cadeau.id == cadeau_id).first()
    
    if not db_cadeau:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cadeau avec l'ID {cadeau_id} non trouvé"
        )
    
    # Vérifier que c'est bien MON cadeau
    if db_cadeau.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez supprimer que vos propres cadeaux"
        )
    
    db.delete(db_cadeau)
    db.commit()


@router.post("/{cadeau_id}/mark-purchased", response_model=CadeauResponse)
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
    
    # Vérifier que je ne suis pas le propriétaire
    if cadeau.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas marquer votre propre cadeau comme acheté"
        )
    
    # Vérifier que je suis membre d'au moins une famille où se trouve le cadeau
    is_member = any(current_user in famille.membres for famille in cadeau.familles)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous devez être membre de la famille"
        )
    
    # Marquer comme acheté
    cadeau.is_purchased = True
    cadeau.purchased_by_id = current_user.id
    
    db.commit()
    db.refresh(cadeau)
    
    return cadeau


@router.post("/{cadeau_id}/unmark-purchased", response_model=CadeauResponse)
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
    
    # Vérifier que c'est moi qui l'ai marqué comme acheté
    if cadeau.purchased_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul celui qui a marqué le cadeau comme acheté peut annuler"
        )
    
    # Annuler
    cadeau.is_purchased = False
    cadeau.purchased_by_id = None
    
    db.commit()
    db.refresh(cadeau)
    
    return cadeau

@router.get("/famille/{famille_id}")
def lister_cadeaux_famille(
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Récupérer tous les cadeaux d'une famille."""
    from app.models.famille import Famille
    
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
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
            "purchased_by_id": cadeau.purchased_by_id
        })
    
    return result
