from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from backend.api.deps import SessionDep
from backend.schemas.user import UserCreate, UserResponse
from backend.schemas.token import Token
from backend.services import auth_service
from backend.core import security

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: SessionDep) -> Any:
    user = auth_service.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="O servidor já tem um usuário com esse email.",
        )
    user = auth_service.get_user_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=400,
            detail="Nome de usuário indisponível.",
        )
    user = auth_service.create_user(db, user_in=user_in)
    return {"message": "Usuário registrado com sucesso", "user_id": user.id}

@router.post("/login", response_model=Token)
def login(db: SessionDep, form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    # Tenta buscar pelo username
    user = auth_service.get_user_by_username(db, username=form_data.username)
    # Se não encontrar, tenta buscar pelo email (o form_data.username pode conter o email)
    if not user:
        user = auth_service.get_user_by_email(db, email=form_data.username)
        
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Nome de usuário ou senha incorretos")
    
    access_token = security.create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": security.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }
