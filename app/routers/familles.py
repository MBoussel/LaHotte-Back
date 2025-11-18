"""Routes API pour les familles"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.famille import Famille
from app.models.user import User
from app.schemas.famille import FamilleCreate, FamilleUpdate, FamilleResponse, FamilleWithMembres
from app.core.security import get_current_active_user

router = APIRouter(
    prefix="/familles",
    tags=["Familles"]
)


@router.post("/", response_model=FamilleResponse, status_code=status.HTTP_201_CREATED)
def creer_famille(
    famille: FamilleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Famille:
    """
    Créer une nouvelle famille.
    Le créateur est automatiquement ajouté comme membre.
    """
    db_famille = Famille(
        nom=famille.nom,
        description=famille.description,
        creator_id=current_user.id
    )

    db_famille.membres.append(current_user)  # Ajouter le créateur comme membre

    db.add(db_famille)
    db.commit()
    db.refresh(db_famille)

    return db_famille


@router.get("/", response_model=List[FamilleWithMembres])
def lister_mes_familles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[Famille]:
    """
    Récupérer toutes MES familles (celles dont je suis membre).
    """
    user: User | None = db.query(User).filter(User.id == current_user.id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")

    return user.familles[skip:skip + limit]


@router.get("/{famille_id}", response_model=FamilleWithMembres)
def obtenir_famille(
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Famille:
    """
    Récupérer une famille spécifique.
    Accessible seulement si je suis membre de cette famille.
    """
    famille: Famille | None = db.query(Famille).filter(Famille.id == famille_id).first()
    if famille is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Famille avec l'ID {famille_id} non trouvée")

    if current_user not in famille.membres:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'êtes pas membre de cette famille")

    return famille


@router.put("/{famille_id}", response_model=FamilleResponse)
def modifier_famille(
    famille_id: int,
    famille_update: FamilleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Famille:
    """
    Modifier une famille (seulement le créateur peut le faire).
    """
    db_famille: Famille | None = db.query(Famille).filter(Famille.id == famille_id).first()
    if db_famille is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Famille avec l'ID {famille_id} non trouvée")

    if db_famille.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul le créateur peut modifier la famille")

    update_data = famille_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_famille, field, value)

    db.commit()
    db.refresh(db_famille)

    return db_famille


@router.delete("/{famille_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_famille(
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    Supprimer une famille (seulement le créateur peut le faire).
    """
    db_famille: Famille | None = db.query(Famille).filter(Famille.id == famille_id).first()
    if db_famille is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Famille avec l'ID {famille_id} non trouvée")

    if db_famille.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul le créateur peut supprimer la famille")

    db.delete(db_famille)
    db.commit()
    return None


@router.post("/{famille_id}/membres/{user_id}", status_code=status.HTTP_200_OK)
def ajouter_membre(
    famille_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Ajouter un membre à la famille (seulement le créateur).
    """
    famille: Famille | None = db.query(Famille).filter(Famille.id == famille_id).first()
    if famille is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Famille non trouvée")

    if famille.creator_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seul le créateur peut ajouter des membres")

    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")

    if user in famille.membres:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cet utilisateur est déjà membre de la famille")

    famille.membres.append(user)
    db.commit()

    return {"message": f"Utilisateur {user.username} ajouté à la famille"}


@router.delete("/{famille_id}/membres/{user_id}", status_code=status.HTTP_200_OK)
def retirer_membre(
    famille_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Retirer un membre de la famille.
    Le créateur peut retirer n'importe qui.
    Un membre peut se retirer lui-même.
    """
    famille: Famille | None = db.query(Famille).filter(Famille.id == famille_id).first()
    if famille is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Famille non trouvée")

    is_creator = famille.creator_id == current_user.id
    is_self = user_id == current_user.id

    if not (is_creator or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez retirer que vous-même, sauf si vous êtes le créateur"
        )

    if user_id == famille.creator_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le créateur ne peut pas quitter la famille")

    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")

    if user not in famille.membres:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cet utilisateur n'est pas membre de la famille")

    famille.membres.remove(user)
    db.commit()

    return {"message": f"Utilisateur {user.username} retiré de la famille"}
