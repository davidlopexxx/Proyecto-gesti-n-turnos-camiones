"""ABM de catálogos: proveedores, productos, depósitos, choferes y camiones."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select

from app.deps import CurrentUser, SessionDep, require_roles
from app.enums import Rol
from app.models import Camion, Chofer, Deposito, Producto, Proveedor
from app.schemas import (
    CamionCreate,
    CamionPublic,
    ChoferCreate,
    ChoferPublic,
    ChoferUpdate,
    DepositoCreate,
    DepositoLugar,
    DepositoPublic,
    DepositoUpdate,
    ProductoCreate,
    ProductoPublic,
    ProductoUpdate,
    ProveedorCreate,
    ProveedorPublic,
    ProveedorUpdate,
)

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=200)]

solo_analista = Depends(require_roles(Rol.analista_insumos))
analista_o_guardia = Depends(require_roles(Rol.analista_insumos, Rol.guardia))


def _get_or_404(session, modelo, id_: int, nombre: str):
    obj = session.get(modelo, id_)
    if obj is None:
        raise HTTPException(404, f"{nombre} no encontrado")
    return obj


def _guardar(session, obj):
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# ----------------------------------------------------------------- proveedores
proveedores = APIRouter(prefix="/proveedores", tags=["Proveedores"])


@proveedores.post("", response_model=ProveedorPublic, status_code=201, dependencies=[solo_analista])
def crear_proveedor(data: ProveedorCreate, session: SessionDep):
    return _guardar(session, Proveedor(**data.model_dump()))


@proveedores.get("", response_model=list[ProveedorPublic])
def listar_proveedores(
    _: CurrentUser, session: SessionDep, q: str | None = None, skip: Skip = 0, limit: Limit = 50
):
    stmt = select(Proveedor).order_by(Proveedor.nombre).offset(skip).limit(limit)
    if q:
        stmt = stmt.where(Proveedor.nombre.ilike(f"%{q}%") | Proveedor.cuit.ilike(f"%{q}%"))
    return session.exec(stmt).all()


@proveedores.get("/{id_}", response_model=ProveedorPublic)
def obtener_proveedor(id_: int, _: CurrentUser, session: SessionDep):
    return _get_or_404(session, Proveedor, id_, "Proveedor")


@proveedores.patch("/{id_}", response_model=ProveedorPublic, dependencies=[solo_analista])
def actualizar_proveedor(id_: int, data: ProveedorUpdate, session: SessionDep):
    obj = _get_or_404(session, Proveedor, id_, "Proveedor")
    obj.sqlmodel_update(data.model_dump(exclude_unset=True))
    return _guardar(session, obj)


# ------------------------------------------------------------------- productos
productos = APIRouter(prefix="/productos", tags=["Productos"])


@productos.post("", response_model=ProductoPublic, status_code=201, dependencies=[solo_analista])
def crear_producto(data: ProductoCreate, session: SessionDep):
    return _guardar(session, Producto(**data.model_dump()))


@productos.get("", response_model=list[ProductoPublic])
def listar_productos(
    _: CurrentUser,
    session: SessionDep,
    q: str | None = None,
    requiere_prueba_fisica: bool | None = None,
    skip: Skip = 0,
    limit: Limit = 100,
):
    stmt = select(Producto).order_by(Producto.codigo).offset(skip).limit(limit)
    if q:
        stmt = stmt.where(Producto.nombre.ilike(f"%{q}%") | Producto.codigo.ilike(f"%{q}%"))
    if requiere_prueba_fisica is not None:
        stmt = stmt.where(Producto.requiere_prueba_fisica == requiere_prueba_fisica)
    return session.exec(stmt).all()


@productos.get("/{id_}", response_model=ProductoPublic)
def obtener_producto(id_: int, _: CurrentUser, session: SessionDep):
    return _get_or_404(session, Producto, id_, "Producto")


@productos.patch("/{id_}", response_model=ProductoPublic, dependencies=[solo_analista])
def actualizar_producto(id_: int, data: ProductoUpdate, session: SessionDep):
    obj = _get_or_404(session, Producto, id_, "Producto")
    cambios = data.model_dump(exclude_unset=True)
    if "codigo" in cambios and cambios["codigo"]:
        cambios["codigo"] = cambios["codigo"].strip().upper()
    obj.sqlmodel_update(cambios)
    return _guardar(session, obj)




# ------------------------------------------------------------------- depósitos
depositos = APIRouter(prefix="/depositos", tags=["Depósitos"])


@depositos.post("", response_model=DepositoPublic, status_code=201, dependencies=[solo_analista])
def crear_deposito(data: DepositoCreate, session: SessionDep):
    return _guardar(session, Deposito(**data.model_dump(mode="json")))


@depositos.get("", response_model=list[DepositoPublic])
def listar_depositos(
    _: CurrentUser, session: SessionDep, tipo: str | None = None, solo_con_lugar: bool = False
):
    stmt = select(Deposito).order_by(Deposito.nombre)
    if tipo:
        stmt = stmt.where(Deposito.tipo == tipo)
    if solo_con_lugar:
        stmt = stmt.where(Deposito.lugar_disponible.is_(True))
    return session.exec(stmt).all()


@depositos.get("/{id_}", response_model=DepositoPublic)
def obtener_deposito(id_: int, _: CurrentUser, session: SessionDep):
    return _get_or_404(session, Deposito, id_, "Depósito")


@depositos.patch("/{id_}", response_model=DepositoPublic, dependencies=[solo_analista])
def actualizar_deposito(id_: int, data: DepositoUpdate, session: SessionDep):
    obj = _get_or_404(session, Deposito, id_, "Depósito")
    obj.sqlmodel_update(data.model_dump(exclude_unset=True, mode="json"))
    return _guardar(session, obj)


@depositos.put("/{id_}/lugar", response_model=DepositoPublic)
def cambiar_lugar_disponible(
    id_: int,
    data: DepositoLugar,
    session: SessionDep,
    user=Depends(require_roles(Rol.deposito_insumos, Rol.deposito_expedicion, Rol.analista_insumos)),
):
    """Cada depósito informa si tiene lugar: es lo que habilita (o frena) la entrada de camiones."""
    obj = _get_or_404(session, Deposito, id_, "Depósito")
    if user.rol == Rol.deposito_insumos.value and obj.tipo != "insumos":
        raise HTTPException(403, "Solo podés modificar depósitos de insumos")
    if user.rol == Rol.deposito_expedicion.value and obj.tipo != "expedicion":
        raise HTTPException(403, "Solo podés modificar depósitos de expedición")
    obj.lugar_disponible = data.lugar_disponible
    return _guardar(session, obj)


# --------------------------------------------------------------------- choferes
choferes = APIRouter(prefix="/choferes", tags=["Choferes"])


@choferes.post("", response_model=ChoferPublic, status_code=201, dependencies=[analista_o_guardia])
def crear_chofer(data: ChoferCreate, session: SessionDep):
    return _guardar(session, Chofer(**data.model_dump()))


@choferes.get("", response_model=list[ChoferPublic])
def listar_choferes(
    _: CurrentUser, session: SessionDep, q: str | None = None, skip: Skip = 0, limit: Limit = 50
):
    stmt = select(Chofer).order_by(Chofer.nombre).offset(skip).limit(limit)
    if q:
        stmt = stmt.where(Chofer.nombre.ilike(f"%{q}%") | Chofer.dni.ilike(f"%{q}%"))
    return session.exec(stmt).all()


@choferes.get("/dni/{dni}", response_model=ChoferPublic)
def buscar_chofer_por_dni(dni: str, _: CurrentUser, session: SessionDep):
    """Permite a la Guardia autocompletar los datos de un chofer recurrente."""
    obj = session.exec(select(Chofer).where(Chofer.dni == dni.replace(".", "").strip())).first()
    if obj is None:
        raise HTTPException(404, "Chofer no encontrado")
    return obj


@choferes.patch("/{id_}", response_model=ChoferPublic, dependencies=[analista_o_guardia])
def actualizar_chofer(id_: int, data: ChoferUpdate, session: SessionDep):
    obj = _get_or_404(session, Chofer, id_, "Chofer")
    obj.sqlmodel_update(data.model_dump(exclude_unset=True))
    return _guardar(session, obj)


# --------------------------------------------------------------------- camiones
camiones = APIRouter(prefix="/camiones", tags=["Camiones"])


@camiones.post("", response_model=CamionPublic, status_code=201, dependencies=[analista_o_guardia])
def crear_camion(data: CamionCreate, session: SessionDep):
    return _guardar(session, Camion(**data.model_dump()))


@camiones.get("", response_model=list[CamionPublic])
def listar_camiones(
    _: CurrentUser, session: SessionDep, q: str | None = None, skip: Skip = 0, limit: Limit = 50
):
    stmt = select(Camion).order_by(Camion.patente).offset(skip).limit(limit)
    if q:
        stmt = stmt.where(Camion.patente.ilike(f"%{q.upper().replace(' ', '')}%"))
    return session.exec(stmt).all()