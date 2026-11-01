from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.db import get_session
from app.core.security import decode_access_token
from app.enums import Rol
from app.models import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep) -> Usuario:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o vencido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_error
    user = session.get(Usuario, user_id)
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def require_roles(*roles: Rol):
    """Dependencia que exige que el usuario tenga alguno de los roles indicados."""
    permitidos = {r.value for r in roles}

    def checker(user: CurrentUser) -> Usuario:
        if user.rol not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu rol ({user.rol}) no tiene permiso para esta acción",
            )
        return user

    return checker