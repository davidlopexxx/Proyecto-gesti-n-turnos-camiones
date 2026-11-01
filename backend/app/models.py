"""Modelos de tabla (SQLModel). Reflejan database/schema.sql."""
from datetime import UTC, date, datetime

from sqlalchemy import Column, DateTime, LargeBinary, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

TS = DateTime(timezone=True)


def utcnow() -> datetime:
    return datetime.now(UTC)


class Usuario(SQLModel, table=True):
    __tablename__ = "usuarios"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100)
    email: str = Field(max_length=150, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    rol: str = Field(max_length=50)


class Proveedor(SQLModel, table=True):
    __tablename__ = "proveedores"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150)
    cuit: str = Field(max_length=20, unique=True)


class Producto(SQLModel, table=True):
    __tablename__ = "productos"

    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=30, unique=True)
    nombre: str = Field(max_length=150)
    tipo: str | None = Field(default=None, max_length=50)
    requiere_prueba_fisica: bool = Field(default=False)


class Deposito(SQLModel, table=True):
    __tablename__ = "depositos"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=100)
    tipo: str = Field(max_length=30)
    lugar_disponible: bool = Field(default=True)


class Chofer(SQLModel, table=True):
    __tablename__ = "choferes"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150)
    dni: str = Field(max_length=20, unique=True, index=True)
    telefono: str | None = Field(default=None, max_length=30)


class Camion(SQLModel, table=True):
    __tablename__ = "camiones"

    id: int | None = Field(default=None, primary_key=True)
    patente: str = Field(max_length=15, unique=True, index=True)


class Turno(SQLModel, table=True):
    __tablename__ = "turnos"

    id: int | None = Field(default=None, primary_key=True)
    fecha_estimada: date
    producto_id: int = Field(foreign_key="productos.id")
    proveedor_id: int | None = Field(default=None, foreign_key="proveedores.id")
    creado_por: int = Field(foreign_key="usuarios.id")
    estado: str = Field(default="pendiente", max_length=20)
    creado_en: datetime = Field(default_factory=utcnow, sa_type=TS)

    producto: Producto | None = Relationship()
    proveedor: Proveedor | None = Relationship()


class Remito(SQLModel, table=True):
    __tablename__ = "remitos"

    id: int | None = Field(default=None, primary_key=True)
    turno_id: int | None = Field(default=None, foreign_key="turnos.id")
    camion_id: int = Field(foreign_key="camiones.id")
    chofer_id: int = Field(foreign_key="choferes.id")
    tipo: str = Field(max_length=20)
    numero_remito: str = Field(max_length=50)
    fecha: datetime = Field(default_factory=utcnow, sa_type=TS)
    numero_precinto: str | None = Field(default=None, max_length=50)
    deposito_id: int | None = Field(default=None, foreign_key="depositos.id")
    estado_general: str = Field(default="en_estudio_calidad", max_length=30, index=True)
    ingresado_en: datetime | None = Field(default=None, sa_type=TS)
    descargado_en: datetime | None = Field(default=None, sa_type=TS)
    egresado_en: datetime | None = Field(default=None, sa_type=TS)

    camion: Camion | None = Relationship()
    chofer: Chofer | None = Relationship()
    items: list["RemitoItem"] = Relationship(back_populates="remito")
    validaciones: list["ValidacionCalidad"] = Relationship(back_populates="remito")


class RemitoItem(SQLModel, table=True):
    __tablename__ = "remito_items"
    __table_args__ = (UniqueConstraint("producto_id", "numero_lote"),)

    id: int | None = Field(default=None, primary_key=True)
    remito_id: int = Field(foreign_key="remitos.id")
    producto_id: int = Field(foreign_key="productos.id")
    cantidad: int
    unidad: str = Field(max_length=20)
    numero_lote: str | None = Field(default=None, max_length=50)

    remito: Remito | None = Relationship(back_populates="items")
    producto: Producto | None = Relationship()


class ValidacionCalidad(SQLModel, table=True):
    __tablename__ = "validaciones_calidad"

    id: int | None = Field(default=None, primary_key=True)
    remito_id: int = Field(foreign_key="remitos.id")
    usuario_id: int | None = Field(default=None, foreign_key="usuarios.id")
    estado: str = Field(default="pendiente", max_length=20)
    motivo_rechazo: str | None = None
    resultado_prueba_fisica: str | None = Field(default=None, max_length=20)
    fecha_inicio: datetime = Field(default_factory=utcnow, sa_type=TS)
    fecha_resolucion: datetime | None = Field(default=None, sa_type=TS)

    remito: Remito | None = Relationship(back_populates="validaciones")


class MovimientoStock(SQLModel, table=True):
    __tablename__ = "movimientos_stock"

    id: int | None = Field(default=None, primary_key=True)
    remito_id: int | None = Field(default=None, foreign_key="remitos.id")
    producto_id: int = Field(foreign_key="productos.id")
    deposito_id: int = Field(foreign_key="depositos.id")
    tipo: str = Field(max_length=20)
    cantidad: int
    fecha: datetime = Field(default_factory=utcnow, sa_type=TS)
    usuario_id: int | None = Field(default=None, foreign_key="usuarios.id")
    motivo: str | None = Field(default=None, max_length=200)


class DocumentoRemito(SQLModel, table=True):
    """Fotos / PDFs de la documentación del camión (los toma la Guardia)."""

    __tablename__ = "documentos_remito"

    id: int | None = Field(default=None, primary_key=True)
    remito_id: int = Field(foreign_key="remitos.id", index=True)
    nombre_archivo: str = Field(max_length=200)
    content_type: str = Field(max_length=100)
    tamano: int
    descripcion: str | None = Field(default=None, max_length=200)
    subido_por: int | None = Field(default=None, foreign_key="usuarios.id")
    creado_en: datetime = Field(default_factory=utcnow, sa_type=TS)
    contenido: bytes = Field(sa_column=Column(LargeBinary, nullable=False))


class HistorialRemito(SQLModel, table=True):
    """Bitácora auditable: quién cambió el estado de un remito y cuándo."""

    __tablename__ = "historial_remito"

    id: int | None = Field(default=None, primary_key=True)
    remito_id: int = Field(foreign_key="remitos.id", index=True)
    usuario_id: int | None = Field(default=None, foreign_key="usuarios.id")
    estado_anterior: str | None = Field(default=None, max_length=30)
    estado_nuevo: str = Field(max_length=30)
    detalle: str | None = None
    creado_en: datetime = Field(default_factory=utcnow, sa_type=TS)