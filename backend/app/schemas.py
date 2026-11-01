"""Esquemas de entrada/salida de la API (patrón Create / Update / Public)."""
from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from app.enums import (
    EstadoTurno,
    EstadoValidacion,
    Rol,
    TipoDeposito,
    TipoMovimiento,
)

T = TypeVar("T")


class Page(SQLModel, Generic[T]):
    total: int
    items: list[T]


# ---------------------------------------------------------------- Auth / usuarios
class UsuarioCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=150)
    password: str = Field(min_length=8, max_length=72)
    rol: Rol

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or v.startswith("@") or v.endswith("@"):
            raise ValueError("Email inválido")
        return v


class UsuarioUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=72)
    rol: Rol | None = None


class UsuarioPublic(SQLModel):
    id: int
    nombre: str
    email: str
    rol: Rol


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioPublic


class CambioPassword(SQLModel):
    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=72)


# ---------------------------------------------------------------- Catálogos
class ProveedorCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=150)
    cuit: str = Field(min_length=8, max_length=20)


class ProveedorUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    cuit: str | None = Field(default=None, min_length=8, max_length=20)


class ProveedorPublic(ProveedorCreate):
    id: int


class ProductoCreate(SQLModel):
    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=2, max_length=150)
    tipo: str | None = Field(default=None, max_length=50)
    requiere_prueba_fisica: bool = False

    @field_validator("codigo")
    @classmethod
    def _codigo(cls, v: str) -> str:
        return v.strip().upper()


class ProductoUpdate(SQLModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    tipo: str | None = Field(default=None, max_length=50)
    requiere_prueba_fisica: bool | None = None


class ProductoPublic(ProductoCreate):
    id: int


class DepositoCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=100)
    tipo: TipoDeposito
    lugar_disponible: bool = True


class DepositoUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    tipo: TipoDeposito | None = None


class DepositoLugar(SQLModel):
    lugar_disponible: bool


class DepositoPublic(DepositoCreate):
    id: int


class ChoferCreate(SQLModel):
    nombre: str = Field(min_length=2, max_length=150)
    dni: str = Field(min_length=6, max_length=20)
    telefono: str | None = Field(default=None, max_length=30)

    @field_validator("dni")
    @classmethod
    def _dni(cls, v: str) -> str:
        return v.replace(".", "").replace(" ", "").strip()


class ChoferUpdate(SQLModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    telefono: str | None = Field(default=None, max_length=30)


class ChoferPublic(ChoferCreate):
    id: int


class CamionCreate(SQLModel):
    patente: str = Field(min_length=5, max_length=15)

    @field_validator("patente")
    @classmethod
    def _patente(cls, v: str) -> str:
        return v.replace(" ", "").replace("-", "").strip().upper()


class CamionPublic(CamionCreate):
    id: int


# ---------------------------------------------------------------- Turnos
class TurnoCreate(SQLModel):
    fecha_estimada: date
    producto_id: int
    proveedor_id: int | None = None


class TurnoUpdate(SQLModel):
    fecha_estimada: date | None = None
    producto_id: int | None = None
    proveedor_id: int | None = None


class TurnoPublic(SQLModel):
    id: int
    fecha_estimada: date
    producto_id: int
    proveedor_id: int | None
    creado_por: int
    estado: EstadoTurno
    creado_en: datetime
    producto: ProductoPublic | None = None
    proveedor: ProveedorPublic | None = None


# ---------------------------------------------------------------- Remitos
class ItemEntradaCreate(SQLModel):
    producto_id: int
    cantidad: int = Field(gt=0)
    unidad: str = Field(min_length=1, max_length=20)
    numero_lote: str = Field(min_length=1, max_length=50)


class RemitoEntradaCreate(SQLModel):
    turno_id: int | None = None
    numero_remito: str = Field(min_length=1, max_length=50)
    patente: str = Field(min_length=5, max_length=15)
    chofer_dni: str = Field(min_length=6, max_length=20)
    chofer_nombre: str = Field(min_length=2, max_length=150)
    chofer_telefono: str | None = Field(default=None, max_length=30)
    items: list[ItemEntradaCreate] = Field(min_length=1)

    @field_validator("patente")
    @classmethod
    def _patente(cls, v: str) -> str:
        return v.replace(" ", "").replace("-", "").strip().upper()

    @field_validator("chofer_dni")
    @classmethod
    def _dni(cls, v: str) -> str:
        return v.replace(".", "").replace(" ", "").strip()


class ItemSalidaCreate(SQLModel):
    producto_id: int
    cantidad: int = Field(gt=0)
    unidad: str = Field(default="cajas", min_length=1, max_length=20)


class RemitoSalidaCreate(SQLModel):
    numero_remito: str | None = Field(default=None, max_length=50)
    numero_precinto: str = Field(min_length=1, max_length=50)
    deposito_id: int
    patente: str = Field(min_length=5, max_length=15)
    chofer_dni: str = Field(min_length=6, max_length=20)
    chofer_nombre: str = Field(min_length=2, max_length=150)
    chofer_telefono: str | None = Field(default=None, max_length=30)
    items: list[ItemSalidaCreate] = Field(min_length=1)

    @field_validator("patente")
    @classmethod
    def _patente(cls, v: str) -> str:
        return v.replace(" ", "").replace("-", "").strip().upper()

    @field_validator("chofer_dni")
    @classmethod
    def _dni(cls, v: str) -> str:
        return v.replace(".", "").replace(" ", "").strip()


class RemitoItemPublic(SQLModel):
    id: int
    producto_id: int
    cantidad: int
    unidad: str
    numero_lote: str | None
    producto: ProductoPublic | None = None


class ValidacionPublic(SQLModel):
    id: int
    usuario_id: int | None
    estado: EstadoValidacion
    motivo_rechazo: str | None
    resultado_prueba_fisica: str | None
    fecha_inicio: datetime
    fecha_resolucion: datetime | None


class RemitoPublic(SQLModel):
    id: int
    turno_id: int | None
    tipo: str
    numero_remito: str
    fecha: datetime
    numero_precinto: str | None
    deposito_id: int | None
    estado_general: str
    ingresado_en: datetime | None
    descargado_en: datetime | None
    egresado_en: datetime | None
    camion: CamionPublic | None = None
    chofer: ChoferPublic | None = None
    items: list[RemitoItemPublic] = []
    validaciones: list[ValidacionPublic] = []


class ValidacionResolver(SQLModel):
    estado: EstadoValidacion
    motivo_rechazo: str | None = None
    resultado_prueba_fisica: str | None = None

    @field_validator("estado")
    @classmethod
    def _no_pendiente(cls, v: EstadoValidacion) -> EstadoValidacion:
        if v == EstadoValidacion.pendiente:
            raise ValueError("Se debe resolver como 'aprobado' o 'rechazado'")
        return v

    @field_validator("resultado_prueba_fisica")
    @classmethod
    def _prueba(cls, v: str | None) -> str | None:
        if v is not None and v not in ("aprobado", "rechazado"):
            raise ValueError("resultado_prueba_fisica debe ser 'aprobado' o 'rechazado'")
        return v


class AsignarDeposito(SQLModel):
    deposito_id: int


class MarcarEspera(SQLModel):
    deposito_id: int | None = None
    detalle: str | None = Field(default=None, max_length=300)


class EgresoCreate(SQLModel):
    numero_precinto: str = Field(min_length=1, max_length=50)


class DocumentoPublic(SQLModel):
    id: int
    remito_id: int
    nombre_archivo: str
    content_type: str
    tamano: int
    descripcion: str | None
    subido_por: int | None
    creado_en: datetime


class HistorialPublic(SQLModel):
    id: int
    remito_id: int
    usuario_id: int | None
    estado_anterior: str | None
    estado_nuevo: str
    detalle: str | None
    creado_en: datetime


# ---------------------------------------------------------------- Stock
class MovimientoCreate(SQLModel):
    producto_id: int
    deposito_id: int
    tipo: TipoMovimiento
    cantidad: int = Field(gt=0)
    motivo: str = Field(min_length=3, max_length=200)


class MovimientoPublic(SQLModel):
    id: int
    remito_id: int | None
    producto_id: int
    deposito_id: int
    tipo: TipoMovimiento
    cantidad: int
    fecha: datetime
    usuario_id: int | None
    motivo: str | None


class StockItem(SQLModel):
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    deposito_id: int
    deposito_nombre: str
    cantidad: int