"""Routes d'authentification"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Créer un nouveau compte utilisateur.
    
    Args:
        user: Données du nouvel utilisateur
        db: Session de base de données
        
    Returns:
        L'utilisateur créé
        
    Raises:
        HTTPException: Si l'email ou le username existe déjà
    """
    # Vérifier si l'email existe déjà
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé"
        )
    
    # Vérifier si le username existe déjà
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà pris"
        )
    
    # Créer l'utilisateur
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Se connecter et obtenir un token d'accès.
    
    Args:
        form_data: Formulaire de connexion (username = email, password)
        db: Session de base de données
        
    Returns:
        Token JWT d'accès
        
    Raises:
        HTTPException: Si les identifiants sont incorrects
    """
    # Trouver l'utilisateur par email
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Vérifier le mot de passe
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Créer le token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtenir les informations de l'utilisateur connecté.
    
    Args:
        current_user: L'utilisateur authentifié
        
    Returns:
        Les informations de l'utilisateur
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(
    user_update: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Modifier les informations de l'utilisateur connecté.
    
    Args:
        user_update: Nouvelles données
        current_user: L'utilisateur authentifié
        db: Session de base de données
        
    Returns:
        L'utilisateur mis à jour
    """
    # Mettre à jour les champs
    if user_update.first_name:
        current_user.first_name = user_update.first_name
    if user_update.last_name:
        current_user.last_name = user_update.last_name
    
    db.commit()
    db.refresh(current_user)
    
    return current_user