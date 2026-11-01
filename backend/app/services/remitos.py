"""Reglas de negocio del ciclo de vida de un remito.

Patrón de diseño: State (table-driven). Las transiciones permitidas entre estados
están en una tabla (TRANSICIONES) y todo cambio de estado pasa por `cambiar_estado`,
que además deja registro en la bitácora (historial_remito). Así ningún endpoint puede
saltearse un paso.
"""
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.enums import (
    EstadoRemito as E,
)
from app.enums import (
    EstadoTurno,
    EstadoValidacion,
    ResultadoPrueba,
    TipoDeposito,
    TipoMovimiento,
    TipoRemito,
)
from app.models import (
    Camion,
    Chofer,
    Deposito,
    HistorialRemito,
    Producto,
    Remito,
    RemitoItem,
    Turno,
    Usuario,
    ValidacionCalidad,
    utcnow,
)
from app.schemas import (
    RemitoEntradaCreate,
    RemitoSalidaCreate,
    ValidacionResolver,
)
from app.services import stock as stock_svc

TRANSICIONES: dict[E, set[E]] = {
    E.en_estudio_calidad: {E.aprobado_calidad, E.rechazado},
    E.aprobado_calidad: {E.listo_para_ingreso, E.esperando_lugar},
    E.esperando_lugar: {E.listo_para_ingreso},
    E.listo_para_ingreso: {E.ingresado},
    E.ingresado: {E.descargado},
    E.preparado: {E.egresado},
}


# ------------------------------------------------------------------ helpers
def _norm_precinto(valor: str) -> str:
    return valor.strip().upper().replace(" ", "")


def cargar_remito(session: Session, remito_id: int, tipo: TipoRemito | None = None) -> Remito:
    remito = session.exec(
        select(Remito)
        .where(Remito.id == remito_id)
        .options(
            selectinload(Remito.items).selectinload(RemitoItem.producto),
            selectinload(Remito.validaciones),
            selectinload(Remito.camion),
            selectinload(Remito.chofer),
        )
    ).first()
    if remito is None:
        raise HTTPException(404, f"Remito {remito_id} no encontrado")
    if tipo is not None and remito.tipo != tipo.value:
        raise HTTPException(409, f"El remito {remito_id} es de {remito.tipo}, no de {tipo.value}")
    return remito


def registrar_evento(
    session: Session, remito: Remito, usuario: Usuario | None, detalle: str, estado_nuevo: str | None = None
) -> None:
    """Deja una línea en la bitácora. Si no se pasa estado_nuevo, el estado no cambia."""
    session.add(
        HistorialRemito(
            remito_id=remito.id,
            usuario_id=usuario.id if usuario else None,
            estado_anterior=remito.estado_general,
            estado_nuevo=estado_nuevo or remito.estado_general,
            detalle=detalle,
        )
    )


def cambiar_estado(
    session: Session, remito: Remito, nuevo: E, usuario: Usuario | None, detalle: str | None = None
) -> None:
    actual = E(remito.estado_general)
    if nuevo not in TRANSICIONES.get(actual, set()):
        raise HTTPException(
            409,
            f"Transición no permitida: el remito está '{actual.value}' y no puede pasar a '{nuevo.value}'",
        )
    registrar_evento(session, remito, usuario, detalle or "", nuevo.value)
    remito.estado_general = nuevo.value
    session.add(remito)


def _exigir_estado(remito: Remito, *permitidos: E) -> None:
    if remito.estado_general not in {p.value for p in permitidos}:
        lista = ", ".join(p.value for p in permitidos)
        raise HTTPException(
            409, f"El remito está '{remito.estado_general}'; esta acción requiere: {lista}"
        )


def validacion_vigente(remito: Remito) -> ValidacionCalidad | None:
    if not remito.validaciones:
        return None
    return max(remito.validaciones, key=lambda v: v.id)


def _exigir_calidad_aprobada(remito: Remito) -> None:
    """Regla central del proyecto: sin aprobación real de Calidad no se avanza."""
    v = validacion_vigente(remito)
    if v is None or v.estado != EstadoValidacion.aprobado.value:
        raise HTTPException(409, "Calidad no aprobó este remito: no se puede continuar")


def _obtener_o_crear_camion_chofer(
    session: Session, patente: str, dni: str, nombre: str, telefono: str | None
) -> tuple[Camion, Chofer]:
    camion = session.exec(select(Camion).where(Camion.patente == patente)).first()
    if camion is None:
        camion = Camion(patente=patente)
        session.add(camion)
    chofer = session.exec(select(Chofer).where(Chofer.dni == dni)).first()
    if chofer is None:
        chofer = Chofer(nombre=nombre, dni=dni, telefono=telefono)
        session.add(chofer)
    elif telefono and chofer.telefono != telefono:
        chofer.telefono = telefono
        session.add(chofer)
    session.flush()
    return camion, chofer


def _productos_por_id(session: Session, ids: list[int]) -> dict[int, Producto]:
    encontrados = {p.id: p for p in session.exec(select(Producto).where(Producto.id.in_(set(ids)))).all()}
    faltan = set(ids) - set(encontrados)
    if faltan:
        raise HTTPException(404, f"Producto(s) inexistente(s): {sorted(faltan)}")
    return encontrados


# ------------------------------------------------------------------ ENTRADA
def registrar_entrada(session: Session, data: RemitoEntradaCreate, usuario: Usuario) -> Remito:
    """La Guardia registra la llegada de un camión con su documentación."""
    turno = None
    if data.turno_id is not None:
        turno = session.get(Turno, data.turno_id)
        if turno is None:
            raise HTTPException(404, f"Turno {data.turno_id} no encontrado")
        if turno.estado == EstadoTurno.cancelado.value:
            raise HTTPException(409, "El turno está cancelado")
        ya_usado = session.exec(select(Remito.id).where(Remito.turno_id == turno.id)).first()
        if ya_usado:
            raise HTTPException(409, "Ese turno ya tiene un remito asociado")

    _productos_por_id(session, [i.producto_id for i in data.items])

    # Trazabilidad por lote: (producto, lote) no puede repetirse
    vistos: set[tuple[int, str]] = set()
    for it in data.items:
        clave = (it.producto_id, it.numero_lote)
        if clave in vistos:
            raise HTTPException(422, f"Lote repetido dentro del remito: {it.numero_lote}")
        vistos.add(clave)
        existente = session.exec(
            select(RemitoItem.id).where(
                RemitoItem.producto_id == it.producto_id, RemitoItem.numero_lote == it.numero_lote
            )
        ).first()
        if existente:
            raise HTTPException(
                409, f"El lote {it.numero_lote} de ese producto ya fue ingresado en otro remito"
            )

    camion, chofer = _obtener_o_crear_camion_chofer(
        session, data.patente, data.chofer_dni, data.chofer_nombre, data.chofer_telefono
    )

    remito = Remito(
        turno_id=data.turno_id,
        camion_id=camion.id,
        chofer_id=chofer.id,
        tipo=TipoRemito.entrada.value,
        numero_remito=data.numero_remito,
        estado_general=E.en_estudio_calidad.value,
    )
    session.add(remito)
    session.flush()

    for it in data.items:
        session.add(
            RemitoItem(
                remito_id=remito.id,
                producto_id=it.producto_id,
                cantidad=it.cantidad,
                unidad=it.unidad,
                numero_lote=it.numero_lote,
            )
        )
    session.add(ValidacionCalidad(remito_id=remito.id))
    session.add(
        HistorialRemito(
            remito_id=remito.id,
            usuario_id=usuario.id,
            estado_anterior=None,
            estado_nuevo=E.en_estudio_calidad.value,
            detalle="Camión registrado en portería; documentación enviada a Calidad",
        )
    )
    if turno is not None:
        turno.estado = EstadoTurno.confirmado.value
        session.add(turno)
    session.commit()
    return cargar_remito(session, remito.id)


def resolver_validacion(
    session: Session, remito_id: int, data: ValidacionResolver, usuario: Usuario
) -> Remito:
    """Calidad aprueba o rechaza. Si hay productos con prueba física, el resultado es obligatorio."""
    remito = cargar_remito(session, remito_id, TipoRemito.entrada)
    _exigir_estado(remito, E.en_estudio_calidad)
    validacion = validacion_vigente(remito)
    if validacion is None or validacion.estado != EstadoValidacion.pendiente.value:
        raise HTTPException(409, "No hay una validación pendiente para este remito")

    requiere_prueba = any(it.producto and it.producto.requiere_prueba_fisica for it in remito.items)
    resultado = data.resultado_prueba_fisica if requiere_prueba else None

    if requiere_prueba and resultado is None:
        raise HTTPException(
            422, "Este remito incluye productos con prueba física (azúcar / leche en polvo): informá el resultado"
        )

    if data.estado == EstadoValidacion.rechazado:
        if not data.motivo_rechazo or len(data.motivo_rechazo.strip()) < 3:
            raise HTTPException(422, "Para rechazar es obligatorio indicar el motivo")
        nuevo = E.rechazado
        detalle = f"Rechazado por Calidad: {data.motivo_rechazo.strip()}"
    else:
        if resultado == ResultadoPrueba.rechazado.value:
            raise HTTPException(
                422, "No se puede aprobar un remito cuya prueba física fue rechazada: rechazalo con su motivo"
            )
        nuevo = E.aprobado_calidad
        detalle = "Aprobado por Calidad" + (" (prueba física OK)" if requiere_prueba else "")

    validacion.estado = data.estado.value
    validacion.usuario_id = usuario.id
    validacion.motivo_rechazo = data.motivo_rechazo.strip() if data.motivo_rechazo else None
    validacion.resultado_prueba_fisica = resultado
    validacion.fecha_resolucion = utcnow()
    session.add(validacion)
    cambiar_estado(session, remito, nuevo, usuario, detalle)
    session.commit()
    return cargar_remito(session, remito_id)




def asignar_deposito(session: Session, remito_id: int, deposito_id: int, usuario: Usuario) -> Remito:
    """Depósito de Insumos confirma lugar y asigna destino. Solo si Calidad ya aprobó."""
    remito = cargar_remito(session, remito_id, TipoRemito.entrada)
    _exigir_estado(remito, E.aprobado_calidad, E.esperando_lugar)
    _exigir_calidad_aprobada(remito)
    deposito = session.get(Deposito, deposito_id)
    if deposito is None:
        raise HTTPException(404, f"Depósito {deposito_id} no encontrado")
    if deposito.tipo != TipoDeposito.insumos.value:
        raise HTTPException(422, "Los insumos solo pueden asignarse a un depósito de insumos")
    if not deposito.lugar_disponible:
        raise HTTPException(
            409, f"El depósito '{deposito.nombre}' no tiene lugar disponible: marcá el camión en espera"
        )
    remito.deposito_id = deposito.id
    cambiar_estado(
        session, remito, E.listo_para_ingreso, usuario, f"Lugar asignado en '{deposito.nombre}'"
    )
    session.commit()
    return cargar_remito(session, remito_id)


def marcar_espera(
    session: Session, remito_id: int, deposito_id: int | None, detalle: str | None, usuario: Usuario
) -> Remito:
    """No hay lugar: el camión espera afuera hasta que se libere."""
    remito = cargar_remito(session, remito_id, TipoRemito.entrada)
    _exigir_estado(remito, E.aprobado_calidad)
    _exigir_calidad_aprobada(remito)
    texto = "Sin lugar disponible: el camión espera afuera"
    if deposito_id is not None:
        dep = session.get(Deposito, deposito_id)
        if dep is None:
            raise HTTPException(404, f"Depósito {deposito_id} no encontrado")
        texto += f" (destino previsto: '{dep.nombre}')"
    if detalle:
        texto += f" — {detalle}"
    cambiar_estado(session, remito, E.esperando_lugar, usuario, texto)
    session.commit()
    return cargar_remito(session, remito_id)


def autorizar_ingreso(session: Session, remito_id: int, usuario: Usuario) -> Remito:
    """La Guardia deja pasar al camión: solo posible si está `listo_para_ingreso`."""
    remito = cargar_remito(session, remito_id, TipoRemito.entrada)
    _exigir_estado(remito, E.listo_para_ingreso)
    _exigir_calidad_aprobada(remito)
    if remito.deposito_id is None:
        raise HTTPException(409, "El remito no tiene depósito asignado")
    remito.ingresado_en = utcnow()
    cambiar_estado(session, remito, E.ingresado, usuario, "Ingreso físico autorizado por Guardia")
    session.commit()
    return cargar_remito(session, remito_id)


def confirmar_descarga(session: Session, remito_id: int, usuario: Usuario) -> Remito:
    """Depósito confirma la descarga: se genera el stock (movimiento de entrada por ítem)."""
    remito = cargar_remito(session, remito_id, TipoRemito.entrada)
    _exigir_estado(remito, E.ingresado)
    _exigir_calidad_aprobada(remito)
    for it in remito.items:
        stock_svc.registrar_movimiento(
            session,
            producto_id=it.producto_id,
            deposito_id=remito.deposito_id,
            tipo=TipoMovimiento.entrada.value,
            cantidad=it.cantidad,
            usuario_id=usuario.id,
            remito_id=remito.id,
            motivo=f"Descarga remito {remito.numero_remito} lote {it.numero_lote}",
        )
    remito.descargado_en = utcnow()
    cambiar_estado(session, remito, E.descargado, usuario, "Descarga confirmada; stock actualizado")
    session.commit()
    return cargar_remito(session, remito_id)




# ------------------------------------------------------------------ SALIDA
def _siguiente_numero_salida(session: Session) -> str:
    cantidad = session.exec(
        select(func.count()).select_from(Remito).where(Remito.tipo == TipoRemito.salida.value)
    ).one()
    return f"S-{int(cantidad) + 1:06d}"


def crear_salida(session: Session, data: RemitoSalidaCreate, usuario: Usuario) -> Remito:
    """Expedición arma el remito de salida (productos ya aprobados) y coloca el precinto."""
    deposito = session.get(Deposito, data.deposito_id)
    if deposito is None:
        raise HTTPException(404, f"Depósito {data.deposito_id} no encontrado")
    if deposito.tipo != TipoDeposito.expedicion.value:
        raise HTTPException(422, "Los remitos de salida salen de un depósito de expedición")
    _productos_por_id(session, [i.producto_id for i in data.items])

    # Se valida stock agregado por producto (puede haber dos ítems del mismo producto)
    pedido: dict[int, int] = {}
    for it in data.items:
        pedido[it.producto_id] = pedido.get(it.producto_id, 0) + it.cantidad
    for producto_id, cantidad in pedido.items():
        disponible = stock_svc.stock_actual(session, producto_id, deposito.id)
        if disponible < cantidad:
            raise HTTPException(
                409,
                f"Stock insuficiente en '{deposito.nombre}' (producto {producto_id}): "
                f"disponible {disponible}, pedido {cantidad}",
            )

    numero = data.numero_remito or _siguiente_numero_salida(session)
    if session.exec(
        select(Remito.id).where(Remito.tipo == TipoRemito.salida.value, Remito.numero_remito == numero)
    ).first():
        raise HTTPException(409, f"Ya existe un remito de salida con el número {numero}")
    precinto = _norm_precinto(data.numero_precinto)
    if session.exec(
        select(Remito.id).where(
            Remito.tipo == TipoRemito.salida.value, Remito.numero_precinto == precinto
        )
    ).first():
        raise HTTPException(409, f"El precinto {precinto} ya fue usado en otro remito")

    camion, chofer = _obtener_o_crear_camion_chofer(
        session, data.patente, data.chofer_dni, data.chofer_nombre, data.chofer_telefono
    )
    remito = Remito(
        camion_id=camion.id,
        chofer_id=chofer.id,
        tipo=TipoRemito.salida.value,
        numero_remito=numero,
        numero_precinto=precinto,
        deposito_id=deposito.id,
        estado_general=E.preparado.value,
    )
    session.add(remito)
    session.flush()
    for it in data.items:
        session.add(
            RemitoItem(remito_id=remito.id, producto_id=it.producto_id, cantidad=it.cantidad, unidad=it.unidad)
        )
    session.add(
        HistorialRemito(
            remito_id=remito.id,
            usuario_id=usuario.id,
            estado_anterior=None,
            estado_nuevo=E.preparado.value,
            detalle=f"Remito de salida generado; precinto {precinto} colocado",
        )
    )
    session.commit()
    return cargar_remito(session, remito.id)


def registrar_egreso(session: Session, remito_id: int, precinto_leido: str, usuario: Usuario) -> Remito:
    """La Guardia verifica que el precinto físico coincida con el remito antes de dejar salir."""
    remito = cargar_remito(session, remito_id, TipoRemito.salida)
    _exigir_estado(remito, E.preparado)
    esperado = _norm_precinto(remito.numero_precinto or "")
    leido = _norm_precinto(precinto_leido)
    if leido != esperado:
        # El intento fallido también queda registrado (auditoría) antes de rechazar.
        registrar_evento(
            session,
            remito,
            usuario,
            f"EGRESO BLOQUEADO: precinto leído '{leido}' no coincide con el del remito '{esperado}'",
        )
        session.commit()
        raise HTTPException(409, "El precinto no coincide con el del remito: el camión no puede salir")

    for it in remito.items:
        stock_svc.registrar_movimiento(
            session,
            producto_id=it.producto_id,
            deposito_id=remito.deposito_id,
            tipo=TipoMovimiento.salida.value,
            cantidad=it.cantidad,
            usuario_id=usuario.id,
            remito_id=remito.id,
            motivo=f"Egreso remito {remito.numero_remito}",
        )
    remito.egresado_en = utcnow()
    cambiar_estado(session, remito, E.egresado, usuario, "Precinto verificado; camión egresó")
    session.commit()
    return cargar_remito(session, remito_id)