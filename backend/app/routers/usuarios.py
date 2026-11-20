from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select

from app.core.security import hash_password
from app.deps import SessionDep, require_roles
from app.enums import Rol
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioPublic, UsuarioUpdate

# El Analista de Insumos (Administración/Compras) administra las cuentas.
router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    dependencies=[Depends(require_roles(Rol.analista_insumos))],
)


@router.post("", response_model=UsuarioPublic, status_code=201)
def crear_usuario(data: UsuarioCreate, session: SessionDep):
    if session.exec(select(Usuario).where(Usuario.email == data.email)).first():
        raise HTTPException(409, "Ya existe un usuario con ese email")
    user = Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        rol=data.rol.value,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("", response_model=list[UsuarioPublic])
def listar_usuarios(
    session: SessionDep,
    rol: Rol | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    stmt = select(Usuario).order_by(Usuario.nombre).offset(skip).limit(limit)
    if rol:
        stmt = stmt.where(Usuario.rol == rol.value)
    return session.exec(stmt).all()


@router.get("/{usuario_id}", response_model=UsuarioPublic)
def obtener_usuario(usuario_id: int, session: SessionDep):
    user = session.get(Usuario, usuario_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    return user


@router.patch("/{usuario_id}", response_model=UsuarioPublic)
def actualizar_usuario(usuario_id: int, data: UsuarioUpdate, session: SessionDep):
    user = session.get(Usuario, usuario_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    cambios = data.model_dump(exclude_unset=True)
    if "password" in cambios:
        user.password_hash = hash_password(cambios.pop("password"))
    if "rol" in cambios:
        user.rol = cambios.pop("rol").value
    for campo, valor in cambios.items():
        setattr(user, campo, valor)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user