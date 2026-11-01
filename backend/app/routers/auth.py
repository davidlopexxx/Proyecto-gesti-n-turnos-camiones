from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from app.core.security import create_access_token, hash_password, verify_password
from app.deps import CurrentUser, SessionDep
from app.models import Usuario
from app.schemas import CambioPassword, Token, UsuarioPublic

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    """OAuth2 Password Flow: `username` es el email."""
    user = session.exec(select(Usuario).where(Usuario.email == form.username.strip().lower())).first()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token(str(user.id), user.rol),
        usuario=UsuarioPublic.model_validate(user),
    )


@router.get("/me", response_model=UsuarioPublic)
def me(user: CurrentUser):
    return user


@router.post("/cambiar-password", status_code=204)
def cambiar_password(data: CambioPassword, user: CurrentUser, session: SessionDep):
    if not verify_password(data.password_actual, user.password_hash):
        raise HTTPException(400, "La contraseña actual no es correcta")
    user.password_hash = hash_password(data.password_nueva)
    session.add(user)
    session.commit()