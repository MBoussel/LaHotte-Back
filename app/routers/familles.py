"""Routes API pour les familles"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import secrets

from app.database import get_db
from app.models.famille import Famille
from app.models.user import User
from app.models.invitation import Invitation
from app.schemas.famille import FamilleCreate, FamilleUpdate, FamilleResponse, FamilleWithMembres
from app.schemas.invitation import InvitationCreate, InvitationResponse
from app.core.security import get_current_active_user
from app.core.email import send_invitation_email
from app.models.demande_adhesion import DemandeAdhesion
from app.schemas.demande_adhesion import DemandeAdhesionCreate, DemandeAdhesionResponse


router = APIRouter(
    prefix="/familles",
    tags=["Familles"]
)

@router.get("/search", response_model=List[FamilleResponse])
def rechercher_familles_publiques(
    query: str = "",
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Rechercher des familles publiques.
    """
    familles = db.query(Famille).filter(
        Famille.is_public == True,
        Famille.nom.ilike(f"%{query}%")
    ).offset(skip).limit(limit).all()
    
    return familles


@router.post("/{famille_id}/demander-adhesion", status_code=status.HTTP_201_CREATED)
def demander_adhesion(
    famille_id: int,
    demande: DemandeAdhesionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Demander à rejoindre une famille publique.
    """
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    
    if not famille:
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    
    if not famille.is_public:
        raise HTTPException(status_code=400, detail="Cette famille n'est pas publique")
    
    # Vérifier si déjà membre
    if current_user in famille.membres:
        raise HTTPException(status_code=400, detail="Vous êtes déjà membre")
    
    # Vérifier si demande existe déjà
    existing = db.query(DemandeAdhesion).filter(
        DemandeAdhesion.famille_id == famille_id,
        DemandeAdhesion.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Demande déjà envoyée")
    
    # Créer la demande
    db_demande = DemandeAdhesion(
        famille_id=famille_id,
        user_id=current_user.id,
        message=demande.message
    )
    
    db.add(db_demande)
    db.commit()
    
    return {"message": "Demande envoyée au créateur de la famille"}


@router.get("/{famille_id}/demandes", response_model=List[DemandeAdhesionResponse])
def lister_demandes_adhesion(
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lister les demandes d'adhésion (créateur seulement).
    """
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    
    if not famille:
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    
    if famille.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Seul le créateur peut voir les demandes")
    
    demandes = db.query(DemandeAdhesion).filter(
        DemandeAdhesion.famille_id == famille_id
    ).all()
    
    # Ajouter les infos utilisateur
    result = []
    for demande in demandes:
        user = db.query(User).filter(User.id == demande.user_id).first()
        result.append({
            "id": demande.id,
            "famille_id": demande.famille_id,
            "user_id": demande.user_id,
            "message": demande.message,
            "created_at": demande.created_at,
            "user_username": user.username if user else None,
            "user_email": user.email if user else None
        })
    
    return result


@router.post("/demandes/{demande_id}/accepter")
def accepter_demande(
    demande_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Accepter une demande d'adhésion.
    """
    demande = db.query(DemandeAdhesion).filter(DemandeAdhesion.id == demande_id).first()
    
    if not demande:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    
    famille = db.query(Famille).filter(Famille.id == demande.famille_id).first()
    if not famille or famille.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Seul le créateur peut accepter")
    
    # Ajouter l'utilisateur à la famille
    user = db.query(User).filter(User.id == demande.user_id).first()
    if user and user not in famille.membres:
        famille.membres.append(user)
    
    # Supprimer la demande
    db.delete(demande)
    db.commit()
    
    return {"message": "Demande acceptée"}


@router.delete("/demandes/{demande_id}")
def refuser_demande(
    demande_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Refuser une demande d'adhésion.
    """
    demande = db.query(DemandeAdhesion).filter(DemandeAdhesion.id == demande_id).first()
    
    if not demande:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    
    famille = db.query(Famille).filter(Famille.id == demande.famille_id).first()
    if not famille or famille.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Seul le créateur peut refuser")
    
    db.delete(demande)
    db.commit()
    
    return {"message": "Demande refusée"}

@router.post("/", response_model=FamilleResponse, status_code=status.HTTP_201_CREATED)
def creer_famille(
    famille: FamilleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Créer une nouvelle famille.
    Le créateur est automatiquement ajouté comme membre.
    """
    db_famille = Famille(
        nom=famille.nom,
        description=famille.description,
        creator_id=current_user.id
    )
    
    # Ajouter le créateur comme membre
    db_famille.membres.append(current_user)
    
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
):
    """
    Récupérer toutes MES familles (celles dont je suis membre).
    """
    # Recharger l'utilisateur pour avoir les relations
    db.refresh(current_user)
    
    return current_user.familles[skip:skip + limit]


@router.get("/{famille_id}", response_model=FamilleWithMembres)
def obtenir_famille(
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupérer une famille spécifique.
    Accessible seulement si je suis membre de cette famille.
    """
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    
    if not famille:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Famille avec l'ID {famille_id} non trouvée"
        )
    
    # Vérifier que je suis membre de cette famille
    if current_user not in famille.membres:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas membre de cette famille"
        )
    
    return famille


@router.put("/{famille_id}", response_model=FamilleResponse)
def modifier_famille(
    famille_id: int,
    famille_update: FamilleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Modifier une famille (seulement le créateur peut le faire)."""

    db_famille = db.query(Famille).filter(Famille.id == famille_id).first()
    
    if not db_famille:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Famille avec l'ID {famille_id} non trouvée"
        )
    
    # Vérifier que je suis le créateur
    if db_famille.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le créateur peut modifier la famille"
        )
    
    # Mettre à jour
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
):
    """
    Supprimer une famille (seulement le créateur peut le faire).
    """
    db_famille = db.query(Famille).filter(Famille.id == famille_id).first()
    
    if not db_famille:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Famille avec l'ID {famille_id} non trouvée"
        )
    
    # Vérifier que je suis le créateur
    if db_famille.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le créateur peut supprimer la famille"
        )
    
    db.delete(db_famille)
    db.commit()
    
    return None


@router.post("/{famille_id}/membres/{user_id}", status_code=status.HTTP_200_OK)
def ajouter_membre(
    famille_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Ajouter un membre à la famille (seulement le créateur).
    """
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    
    if not famille:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Famille non trouvée"
        )
    
    # Vérifier que je suis le créateur
    if famille.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le créateur peut ajouter des membres"
        )
    
    # Trouver l'utilisateur à ajouter
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Vérifier qu'il n'est pas déjà membre
    if user in famille.membres:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet utilisateur est déjà membre de la famille"
        )
    
    # Ajouter le membre
    famille.membres.append(user)
    db.commit()
    
    return {"message": f"Utilisateur {user.username} ajouté à la famille"}


@router.delete("/{famille_id}/membres/{user_id}", status_code=status.HTTP_200_OK)
def retirer_membre(
    famille_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retirer un membre de la famille.
    Le créateur peut retirer n'importe qui.
    Un membre peut se retirer lui-même.
    """
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    
    if not famille:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Famille non trouvée"
        )
    
    # Vérifier les permissions
    is_creator = famille.creator_id == current_user.id
    is_self = user_id == current_user.id
    
    if not (is_creator or is_self):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez retirer que vous-même, sauf si vous êtes le créateur"
        )
    
    # Ne pas permettre au créateur de se retirer
    if user_id == famille.creator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le créateur ne peut pas quitter la famille"
        )
    
    # Trouver l'utilisateur
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Vérifier qu'il est membre
    if user not in famille.membres:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet utilisateur n'est pas membre de la famille"
        )
    
    # Retirer le membre
    famille.membres.remove(user)
    db.commit()
    
    return {"message": f"Utilisateur {user.username} retiré de la famille"}


# ========== ROUTES D'INVITATION ==========

from app.core.email import send_invitation_email

@router.post("/{famille_id}/invitations", response_model=InvitationResponse)
def creer_invitation(
    famille_id: int,
    invitation: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Créer une invitation et envoyer un email."""
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    
    if not famille:
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    
    if famille.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Seul le créateur peut inviter")
    
    user = db.query(User).filter(User.email == invitation.email).first()
    if user and user in famille.membres:
        raise HTTPException(status_code=400, detail="Cet utilisateur est déjà membre")
    
    existing = db.query(Invitation).filter(
        Invitation.famille_id == famille_id,
        Invitation.email == invitation.email,
        Invitation.accepted == False
    ).first()
    
    if existing:
        # Renvoyer l'email
        send_invitation_email(invitation.email, famille.nom, existing.token)
        return existing
    
    # Créer l'invitation
    token = secrets.token_urlsafe(32)
    db_invitation = Invitation(
        famille_id=famille_id,
        email=invitation.email,
        token=token
    )
    
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    
    # Envoyer l'email
    send_invitation_email(invitation.email, famille.nom, token)
    
    return db_invitation


@router.get("/invitations/pending", response_model=List[InvitationResponse])
def mes_invitations_en_attente(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Récupérer mes invitations en attente avec le nom de la famille.
    """
    invitations = db.query(Invitation).filter(
        Invitation.email == current_user.email,
        Invitation.accepted == False
    ).all()
    
    # Ajouter le nom de la famille à chaque invitation
    result = []
    for invitation in invitations:
        famille = db.query(Famille).filter(Famille.id == invitation.famille_id).first()
        inv_dict = {
            "id": invitation.id,
            "famille_id": invitation.famille_id,
            "email": invitation.email,
            "token": invitation.token,
            "accepted": invitation.accepted,
            "created_at": invitation.created_at,
            "famille_nom": famille.nom if famille else "Famille inconnue"
        }
        result.append(inv_dict)
    
    return result


@router.post("/invitations/{token}/accept")
def accepter_invitation(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Accepter une invitation.
    """
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation non trouvée"
        )
    
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette invitation ne vous est pas destinée"
        )
    
    if invitation.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation déjà acceptée"
        )
    
    # Ajouter à la famille
    famille = db.query(Famille).filter(Famille.id == invitation.famille_id).first()
    if not famille:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Famille non trouvée"
        )
    
    if current_user not in famille.membres:
        famille.membres.append(current_user)
    
    invitation.accepted = True
    db.commit()
    
    return {"message": f"Vous avez rejoint la famille {famille.nom}"}


@router.get("/{famille_id}/invitations", response_model=List[InvitationResponse])
def lister_invitations_famille(
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Lister toutes les invitations d'une famille (pour le créateur).
    """
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    
    if not famille:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Famille non trouvée"
        )
    
    if famille.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le créateur peut voir les invitations"
        )
    
    return famille.invitations