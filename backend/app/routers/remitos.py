from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import defer, selectinload
from sqlmodel import select

from app.core.config import settings
from app.deps import CurrentUser, SessionDep, require_roles
from app.enums import EstadoRemito, Rol, TipoRemito
from app.models import Camion, DocumentoRemito, HistorialRemito, Remito, RemitoItem, Usuario
from app.schemas import (
    AsignarDeposito,
    DocumentoPublic,
    EgresoCreate,
    HistorialPublic,
    MarcarEspera,
    Page,
    RemitoEntradaCreate,
    RemitoPublic,
    RemitoSalidaCreate,
    ValidacionResolver,
)
from app.services import remitos as svc

router = APIRouter(prefix="/remitos", tags=["Remitos"])

Guardia = Annotated[Usuario, Depends(require_roles(Rol.guardia))]
Calidad = Annotated[Usuario, Depends(require_roles(Rol.calidad))]
DepInsumos = Annotated[Usuario, Depends(require_roles(Rol.deposito_insumos))]
DepExpedicion = Annotated[Usuario, Depends(require_roles(Rol.deposito_expedicion))]


# ----------------------------------------------------------------- consulta
@router.get("", response_model=Page[RemitoPublic])
def listar_remitos(
    _: CurrentUser,
    session: SessionDep,
    tipo: TipoRemito | None = None,
    estado_general: EstadoRemito | None = None,
    patente: str | None = None,
    numero_remito: str | None = None,
    deposito_id: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    """Listado con filtros y paginado. Es la fuente única que consultan las tres áreas."""
    filtros = []
    if tipo:
        filtros.append(Remito.tipo == tipo.value)
    if estado_general:
        filtros.append(Remito.estado_general == estado_general.value)
    if numero_remito:
        filtros.append(Remito.numero_remito.ilike(f"%{numero_remito}%"))
    if deposito_id:
        filtros.append(Remito.deposito_id == deposito_id)
    if desde:
        filtros.append(Remito.fecha >= desde)
    if hasta:
        filtros.append(Remito.fecha <= hasta)
    if patente:
        filtros.append(
            Remito.camion_id.in_(
                select(Camion.id).where(Camion.patente.ilike(f"%{patente.upper().replace(' ', '')}%"))
            )
        )
    total = session.exec(select(func.count()).select_from(Remito).where(*filtros)).one()
    items = session.exec(
        select(Remito)
        .where(*filtros)
        .options(
            selectinload(Remito.items).selectinload(RemitoItem.producto),
            selectinload(Remito.validaciones),
            selectinload(Remito.camion),
            selectinload(Remito.chofer),
        )
        .order_by(Remito.fecha.desc(), Remito.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return Page[RemitoPublic](
        total=int(total), items=[RemitoPublic.model_validate(r) for r in items]
    )


@router.get("/{remito_id}", response_model=RemitoPublic)
def obtener_remito(remito_id: int, _: CurrentUser, session: SessionDep):
    return svc.cargar_remito(session, remito_id)


@router.get("/{remito_id}/historial", response_model=list[HistorialPublic])
def historial_remito(remito_id: int, _: CurrentUser, session: SessionDep):
    """Bitácora auditable: quién hizo qué y cuándo con este remito."""
    svc.cargar_remito(session, remito_id)
    return session.exec(
        select(HistorialRemito)
        .where(HistorialRemito.remito_id == remito_id)
        .order_by(HistorialRemito.id)
    ).all()


# ------------------------------------------------------- flujo de entrada
@router.post("/entrada", response_model=RemitoPublic, status_code=201)
def registrar_entrada(data: RemitoEntradaCreate, session: SessionDep, user: Guardia):
    """La Guardia registra la llegada del camión y su documentación."""
    return svc.registrar_entrada(session, data, user)


@router.post("/{remito_id}/validacion", response_model=RemitoPublic)
def resolver_validacion(
    remito_id: int, data: ValidacionResolver, session: SessionDep, user: Calidad
):
    """Calidad aprueba o rechaza la mercadería."""
    return svc.resolver_validacion(session, remito_id, data, user)


@router.post("/{remito_id}/asignar-deposito", response_model=RemitoPublic)
def asignar_deposito(
    remito_id: int, data: AsignarDeposito, session: SessionDep, user: DepInsumos
):
    """Depósito de Insumos confirma que hay lugar y asigna el destino."""
    return svc.asignar_deposito(session, remito_id, data.deposito_id, user)


@router.post("/{remito_id}/marcar-espera", response_model=RemitoPublic)
def marcar_espera(
    remito_id: int, data: MarcarEspera, session: SessionDep, user: DepInsumos
):
    """No hay lugar: el camión queda esperando afuera."""
    return svc.marcar_espera(session, remito_id, data.deposito_id, data.detalle, user)


@router.post("/{remito_id}/autorizar-ingreso", response_model=RemitoPublic)
def autorizar_ingreso(remito_id: int, session: SessionDep, user: Guardia):
    """La Guardia deja pasar al camión (solo si está listo para ingresar)."""
    return svc.autorizar_ingreso(session, remito_id, user)


@router.post("/{remito_id}/confirmar-descarga", response_model=RemitoPublic)
def confirmar_descarga(remito_id: int, session: SessionDep, user: DepInsumos):
    """Depósito confirma la descarga: acá se genera el stock."""
    return svc.confirmar_descarga(session, remito_id, user)


# ------------------------------------------------------------ flujo de salida
@router.post("/salida", response_model=RemitoPublic, status_code=201)
def crear_salida(data: RemitoSalidaCreate, session: SessionDep, user: DepExpedicion):
    """Expedición arma el remito de salida (numerado) con su precinto."""
    return svc.crear_salida(session, data, user)


@router.post("/{remito_id}/egreso", response_model=RemitoPublic)
def registrar_egreso(
    remito_id: int, data: EgresoCreate, session: SessionDep, user: Guardia
):
    """La Guardia compara el precinto del camión con el del remito y deja salir."""
    return svc.registrar_egreso(session, remito_id, data.numero_precinto, user)


# ---------------------------------------------------------------- documentos
TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


@router.post("/{remito_id}/documentos", response_model=DocumentoPublic, status_code=201)
async def subir_documento(
    remito_id: int,
    session: SessionDep,
    user: Guardia,
    archivo: Annotated[UploadFile, File(description="Foto o PDF de la documentación")],
    descripcion: Annotated[str | None, Form(max_length=200)] = None,
):
    """La Guardia sube la foto o el PDF de la documentación del camión."""
    svc.cargar_remito(session, remito_id)
    if archivo.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(415, "Formato no permitido (usar JPG, PNG, WEBP o PDF)")
    limite = settings.max_upload_mb * 1024 * 1024
    contenido = await archivo.read(limite + 1)
    if len(contenido) > limite:
        raise HTTPException(413, f"El archivo supera el máximo de {settings.max_upload_mb} MB")
    if not contenido:
        raise HTTPException(422, "El archivo está vacío")
    doc = DocumentoRemito(
        remito_id=remito_id,
        nombre_archivo=(archivo.filename or "documento")[:200],
        content_type=archivo.content_type,
        tamano=len(contenido),
        descripcion=descripcion,
        subido_por=user.id,
        contenido=contenido,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


@router.get("/{remito_id}/documentos", response_model=list[DocumentoPublic])
def listar_documentos(remito_id: int, _: CurrentUser, session: SessionDep):
    """Lista los documentos de un remito, sin traer el contenido pesado."""
    svc.cargar_remito(session, remito_id)
    return session.exec(
        select(DocumentoRemito)
        .where(DocumentoRemito.remito_id == remito_id)
        .options(defer(DocumentoRemito.contenido))
        .order_by(DocumentoRemito.id)
    ).all()


@router.get("/{remito_id}/documentos/{documento_id}/archivo")
def descargar_documento(
    remito_id: int, documento_id: int, _: CurrentUser, session: SessionDep
):
    """Devuelve el archivo en sí (la foto o el PDF) para verlo en pantalla."""
    doc = session.get(DocumentoRemito, documento_id)
    if doc is None or doc.remito_id != remito_id:
        raise HTTPException(404, "Documento no encontrado")
    return Response(
        content=doc.contenido,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'inline; filename="{doc.nombre_archivo}"'},
    )