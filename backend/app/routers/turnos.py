from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.deps import CurrentUser, SessionDep, require_roles
from app.enums import EstadoTurno, Rol
from app.models import Producto, Proveedor, Remito, Turno, Usuario
from app.schemas import TurnoCreate, TurnoPublic, TurnoUpdate

router = APIRouter(prefix="/turnos", tags=["Turnos"])

PUEDE_GESTIONAR = Depends(require_roles(Rol.analista_insumos, Rol.guardia))


def _validar_refs(session, producto_id, proveedor_id):
    if producto_id is not None and session.get(Producto, producto_id) is None:
        raise HTTPException(404, f"Producto {producto_id} no encontrado")
    if proveedor_id is not None and session.get(Proveedor, proveedor_id) is None:
        raise HTTPException(404, f"Proveedor {proveedor_id} no encontrado")


def _cargar(session, turno_id: int) -> Turno:
    turno = session.exec(
        select(Turno)
        .where(Turno.id == turno_id)
        .options(selectinload(Turno.producto), selectinload(Turno.proveedor))
    ).first()
    if turno is None:
        raise HTTPException(404, "Turno no encontrado")
    return turno


@router.post("", response_model=TurnoPublic, status_code=201)
def crear_turno(data: TurnoCreate, session: SessionDep, user: Annotated[Usuario, PUEDE_GESTIONAR]):
    """El Analista coordina la entrega con el proveedor; la Guardia lo carga si el camión llega sin turno."""
    _validar_refs(session, data.producto_id, data.proveedor_id)
    turno = Turno(**data.model_dump(), creado_por=user.id)
    session.add(turno)
    session.commit()
    return _cargar(session, turno.id)


@router.get("", response_model=list[TurnoPublic])
def listar_turnos(
    _: CurrentUser,
    session: SessionDep,
    estado: EstadoTurno | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    proveedor_id: int | None = None,
    producto_id: int | None = None,
    sin_remito: bool = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    stmt = (
        select(Turno)
        .options(selectinload(Turno.producto), selectinload(Turno.proveedor))
        .order_by(Turno.fecha_estimada, Turno.id)
        .offset(skip)
        .limit(limit)
    )
    if estado:
        stmt = stmt.where(Turno.estado == estado.value)
    if desde:
        stmt = stmt.where(Turno.fecha_estimada >= desde)
    if hasta:
        stmt = stmt.where(Turno.fecha_estimada <= hasta)
    if proveedor_id:
        stmt = stmt.where(Turno.proveedor_id == proveedor_id)
    if producto_id:
        stmt = stmt.where(Turno.producto_id == producto_id)
    if sin_remito:
        stmt = stmt.where(Turno.id.not_in(select(Remito.turno_id).where(Remito.turno_id.is_not(None))))
    return session.exec(stmt).all()


@router.get("/{turno_id}", response_model=TurnoPublic)
def obtener_turno(turno_id: int, _: CurrentUser, session: SessionDep):
    return _cargar(session, turno_id)


@router.patch("/{turno_id}", response_model=TurnoPublic, dependencies=[PUEDE_GESTIONAR])
def actualizar_turno(turno_id: int, data: TurnoUpdate, session: SessionDep):
    turno = _cargar(session, turno_id)
    if turno.estado != EstadoTurno.pendiente.value:
        raise HTTPException(409, "Solo se pueden modificar turnos pendientes")
    cambios = data.model_dump(exclude_unset=True)
    _validar_refs(session, cambios.get("producto_id"), cambios.get("proveedor_id"))
    turno.sqlmodel_update(cambios)
    session.add(turno)
    session.commit()
    return _cargar(session, turno_id)


@router.post("/{turno_id}/cancelar", response_model=TurnoPublic, dependencies=[PUEDE_GESTIONAR])
def cancelar_turno(turno_id: int, session: SessionDep):
    turno = _cargar(session, turno_id)
    if turno.estado == EstadoTurno.cancelado.value:
        raise HTTPException(409, "El turno ya está cancelado")
    if turno.estado == EstadoTurno.confirmado.value:
        raise HTTPException(409, "El camión ya llegó (turno confirmado): no se puede cancelar")
    turno.estado = EstadoTurno.cancelado.value
    session.add(turno)
    session.commit()
    return _cargar(session, turno_id)