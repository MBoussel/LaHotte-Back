"""Routes API pour les cadeaux"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.cadeau import Cadeau
from app.models.user import User
from app.schemas.cadeau import CadeauCreate, CadeauUpdate, CadeauResponse
from app.core.security import get_current_active_user

router = APIRouter(
    prefix="/cadeaux",
    tags=["Cadeaux"]
)


@router.post("/", response_model=CadeauResponse, status_code=status.HTTP_201_CREATED)
def creer_cadeau(
    cadeau: CadeauCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Créer un nouveau cadeau dans une famille.
    """
    from app.models.famille import Famille
    
    # Vérifier que la famille existe
    famille = db.query(Famille).filter(Famille.id == cadeau.famille_id).first()
    if not famille:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Famille non trouvée"
        )
    
    # Vérifier que je suis membre de cette famille
    if current_user not in famille.membres:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous devez être membre de la famille pour y ajouter un cadeau"
        )
    
    db_cadeau = Cadeau(
        titre=cadeau.titre,
        prix=cadeau.prix,
        description=cadeau.description,
        owner_id=current_user.id,
        famille_id=cadeau.famille_id
    )
    
    db.add(db_cadeau)
    db.commit()
    db.refresh(db_cadeau)
    
    return db_cadeau


@router.get("/", response_model=List[CadeauResponse])
def lister_cadeaux(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Récupérer la liste de tous les cadeaux (pas besoin d'être connecté).
    """
    cadeaux = db.query(Cadeau).offset(skip).limit(limit).all()
    return cadeaux


@router.get("/me", response_model=List[CadeauResponse])
def lister_mes_cadeaux(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupérer MES cadeaux (ceux que j'ai créés).
    """
    cadeaux = db.query(Cadeau).filter(
        Cadeau.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    return cadeaux


@router.get("/{cadeau_id}", response_model=CadeauResponse)
def obtenir_cadeau(
    cadeau_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer un cadeau spécifique par son ID.
    """
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
    """
    Modifier un cadeau (seulement si c'est MON cadeau).
    """
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
    
    # Mettre à jour
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
    """
    Supprimer un cadeau (seulement si c'est MON cadeau).
    """
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
    
    return None