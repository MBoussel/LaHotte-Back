"""Gestion de la sécurité et de l'authentification"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

# Configuration
SECRET_KEY = "votre-super-cle-secrete-a-changer-en-production-min-32-chars"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Contexte pour hasher les mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 pour récupérer le token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifier un mot de passe contre son hash.
    
    Args:
        plain_password: Le mot de passe en clair
        hashed_password: Le hash stocké en DB
        
    Returns:
        True si le mot de passe correspond
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hasher un mot de passe avec bcrypt (limité à 72 octets).
    
    Args:
        password: Le mot de passe en clair
        
    Returns:
        Le hash du mot de passe
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Créer un token JWT.
    
    Args:
        data: Les données à encoder dans le token (généralement {"sub": email})
        expires_delta: Durée de validité du token
        
    Returns:
        Le token JWT encodé
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Récupérer l'utilisateur connecté depuis le token JWT.
    
    Args:
        token: Le token JWT
        db: Session de base de données
        
    Returns:
        L'utilisateur connecté
        
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur n'existe pas
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Décoder le token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Récupérer l'utilisateur
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Vérifier que l'utilisateur est actif.
    
    Args:
        current_user: L'utilisateur connecté
        
    Returns:
        L'utilisateur si actif
        
    Raises:
        HTTPException: Si l'utilisateur est inactif
    """
    if not bool(current_user.is_active):
        raise HTTPException(status_code=400, detail="Utilisateur inactif")
    return current_user