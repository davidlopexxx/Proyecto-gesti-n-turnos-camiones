"""Lógica de stock: el saldo se calcula a partir de movimientos_stock (entradas - salidas)."""
from fastapi import HTTPException
from sqlalchemy import case, func
from sqlmodel import Session, select

from app.enums import TipoMovimiento
from app.models import Deposito, MovimientoStock, Producto, utcnow


def _signed_qty():
    return case(
        (MovimientoStock.tipo == TipoMovimiento.entrada.value, MovimientoStock.cantidad),
        else_=-MovimientoStock.cantidad,
    )


def stock_actual(session: Session, producto_id: int, deposito_id: int) -> int:
    total = session.exec(
        select(func.coalesce(func.sum(_signed_qty()), 0)).where(
            MovimientoStock.producto_id == producto_id,
            MovimientoStock.deposito_id == deposito_id,
        )
    ).one()
    return int(total)


def listar_stock(
    session: Session, producto_id: int | None = None, deposito_id: int | None = None
) -> list[dict]:
    stmt = (
        select(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            Deposito.id,
            Deposito.nombre,
            func.sum(_signed_qty()),
        )
        .join(Producto, Producto.id == MovimientoStock.producto_id)
        .join(Deposito, Deposito.id == MovimientoStock.deposito_id)
        .group_by(Producto.id, Producto.codigo, Producto.nombre, Deposito.id, Deposito.nombre)
        .order_by(Deposito.nombre, Producto.codigo)
    )
    if producto_id:
        stmt = stmt.where(MovimientoStock.producto_id == producto_id)
    if deposito_id:
        stmt = stmt.where(MovimientoStock.deposito_id == deposito_id)
    return [
        {
            "producto_id": r[0],
            "producto_codigo": r[1],
            "producto_nombre": r[2],
            "deposito_id": r[3],
            "deposito_nombre": r[4],
            "cantidad": int(r[5] or 0),
        }
        for r in session.exec(stmt).all()
    ]


def registrar_movimiento(
    session: Session,
    *,
    producto_id: int,
    deposito_id: int,
    tipo: str,
    cantidad: int,
    usuario_id: int | None,
    remito_id: int | None = None,
    motivo: str | None = None,
) -> MovimientoStock:
    """Agrega un movimiento. No hace commit (lo hace quien llama, para que sea atómico)."""
    if cantidad <= 0:
        raise HTTPException(422, "La cantidad debe ser mayor a cero")
    if tipo == TipoMovimiento.salida.value:
        disponible = stock_actual(session, producto_id, deposito_id)
        if disponible < cantidad:
            producto = session.get(Producto, producto_id)
            raise HTTPException(
                409,
                f"Stock insuficiente de {producto.codigo if producto else producto_id}: "
                f"disponible {disponible}, pedido {cantidad}",
            )
    mov = MovimientoStock(
        remito_id=remito_id,
        producto_id=producto_id,
        deposito_id=deposito_id,
        tipo=tipo,
        cantidad=cantidad,
        usuario_id=usuario_id,
        motivo=motivo,
        fecha=utcnow(),
    )
    session.add(mov)
    session.flush()
    return mov