"""Gestion des profils bénéficiaires sans compte."""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.famille import Famille
from app.models.beneficiaire import Beneficiaire
from app.schemas.beneficiaire import BeneficiaireCreate, ResponsablesUpdate
from app.core.profile_storage import upload_profile_photo

router = APIRouter(prefix="/beneficiaires", tags=["Bénéficiaires"])

def _serialize(profil: Beneficiaire):
    return {
        "id": profil.id,
        "famille_id": profil.famille_id,
        "nom": profil.nom,
        "avatar_url": profil.avatar_url,
        "created_by_id": profil.created_by_id,
        "responsables": [{"id": u.id, "username": u.username} for u in profil.responsables],
    }

@router.get("/famille/{famille_id}")
def lister_profils(
    famille_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    if not famille:
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    if current_user not in famille.membres:
        raise HTTPException(status_code=403, detail="Vous devez être membre de cette famille")
    profils = (
        db.query(Beneficiaire)
        .options(joinedload(Beneficiaire.responsables))
        .filter(Beneficiaire.famille_id == famille_id)
        .order_by(Beneficiaire.nom)
        .all()
    )
    return [_serialize(p) for p in profils]

@router.post("/famille/{famille_id}", status_code=status.HTTP_201_CREATED)
def creer_profil(
    famille_id: int,
    data: BeneficiaireCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    famille = db.query(Famille).filter(Famille.id == famille_id).first()
    if not famille:
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    if current_user not in famille.membres:
        raise HTTPException(status_code=403, detail="Vous devez être membre de cette famille")

    nom = data.nom.strip()
    if not nom:
        raise HTTPException(status_code=422, detail="Le prénom est obligatoire")

    ids = set(data.responsable_ids or [])
    ids.add(current_user.id)
    membres = {m.id: m for m in famille.membres}
    if any(user_id not in membres for user_id in ids):
        raise HTTPException(status_code=400, detail="Tous les responsables doivent être membres de la famille")

    profil = Beneficiaire(
        famille_id=famille_id,
        nom=nom,
        created_by_id=current_user.id,
        responsables=[membres[user_id] for user_id in ids],
    )
    db.add(profil)
    db.commit()
    db.refresh(profil)
    return _serialize(profil)

@router.put("/{beneficiaire_id}/responsables")
def modifier_responsables(
    beneficiaire_id: int,
    data: ResponsablesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profil = db.query(Beneficiaire).options(
        joinedload(Beneficiaire.responsables)
    ).filter(Beneficiaire.id == beneficiaire_id).first()
    if not profil:
        raise HTTPException(status_code=404, detail="Bénéficiaire non trouvé")

    if current_user not in profil.responsables:
        raise HTTPException(status_code=403, detail="Seul un responsable peut gérer ce profil")

    famille = db.query(Famille).filter(Famille.id == profil.famille_id).first()
    if not famille or current_user not in famille.membres:
        raise HTTPException(status_code=403, detail="Vous devez être membre de cette famille")
    membres = {m.id: m for m in famille.membres}
    ids = set(data.responsable_ids)
    if profil.created_by_id in membres:
        ids.add(profil.created_by_id)
    if any(user_id not in membres for user_id in ids):
        raise HTTPException(status_code=400, detail="Tous les responsables doivent être membres de la famille")

    profil.responsables = [membres[user_id] for user_id in ids]
    db.commit()
    db.refresh(profil)
    return _serialize(profil)

@router.post("/{beneficiaire_id}/avatar")
async def televerser_photo(
    beneficiaire_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Seul un responsable du bénéficiaire peut modifier sa photo."""
    profil = (
        db.query(Beneficiaire)
        .options(joinedload(Beneficiaire.responsables))
        .filter(Beneficiaire.id == beneficiaire_id)
        .first()
    )
    if not profil:
        raise HTTPException(status_code=404, detail="Bénéficiaire non trouvé")
    if current_user not in profil.responsables:
        raise HTTPException(status_code=403, detail="Seul un responsable peut modifier ce profil")

    famille = db.query(Famille).filter(Famille.id == profil.famille_id).first()
    if not famille or current_user not in famille.membres:
        raise HTTPException(status_code=403, detail="Vous devez être membre de cette famille")

    profil.avatar_url = await upload_profile_photo(file, f"beneficiaires/{profil.id}")
    db.commit()
    db.refresh(profil)
    return {"message": "Photo du bénéficiaire mise à jour", "avatar_url": profil.avatar_url}
