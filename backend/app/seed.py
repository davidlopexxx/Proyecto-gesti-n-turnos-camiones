"""Datos de demostración. Uso:  python -m app.seed   (es idempotente: no duplica registros)."""
from datetime import date, timedelta

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import create_db_and_tables, engine
from app.core.security import hash_password
from app.enums import Rol
from app.models import Deposito, Producto, Proveedor, Remito, Turno, Usuario
from app.schemas import (
    ItemEntradaCreate,
    ItemSalidaCreate,
    RemitoEntradaCreate,
    RemitoSalidaCreate,
    ValidacionResolver,
)
from app.services import remitos as svc
from app.services import stock as stock_svc

USUARIOS = [
    ("Analista de Insumos", "analista@fabrica.com", Rol.analista_insumos),
    ("Guardia Portería", "guardia@fabrica.com", Rol.guardia),
    ("Laboratorio Calidad", "calidad@fabrica.com", Rol.calidad),
    ("Depósito de Insumos", "insumos@fabrica.com", Rol.deposito_insumos),
    ("Depósito de Expedición", "expedicion@fabrica.com", Rol.deposito_expedicion),
]

PROVEEDORES = [
    ("Azucarera del Norte S.A.", "30-11111111-1"),
    ("Lácteos del Sur S.R.L.", "30-22222222-2"),
    ("Cacao y Derivados S.A.", "30-33333333-3"),
    ("Envases Plásticos Cuyo", "30-44444444-4"),
]

# codigo, nombre, tipo, requiere_prueba_fisica
PRODUCTOS = [
    ("AZU-001", "Azúcar refinada (bolsa 50 kg)", "insumo", True),
    ("LEC-001", "Leche en polvo entera (bolsa 25 kg)", "insumo", True),
    ("CAC-001", "Cacao en polvo (bolsa 25 kg)", "insumo", False),
    ("GLU-001", "Jarabe de glucosa (tambor 200 kg)", "insumo", False),
    ("ENV-001", "Film de envoltorio caramelos (bobina)", "insumo", False),
    ("PT-CAR-001", "Caramelos masticables x 24 (caja)", "terminado", False),
    ("PT-CHO-001", "Chocolatines x 12 (caja)", "terminado", False),
]

DEPOSITOS = [
    ("Depósito de Insumos A", "insumos"),
    ("Depósito de Insumos B", "insumos"),
    ("Expedición Central", "expedicion"),
]


def _get(session: Session, modelo, **filtro):
    stmt = select(modelo)
    for k, v in filtro.items():
        stmt = stmt.where(getattr(modelo, k) == v)
    return session.exec(stmt).first()


def seed_base(session: Session, password: str | None = None) -> dict[str, Usuario]:
    password = password or settings.seed_password
    usuarios: dict[str, Usuario] = {}
    for nombre, email, rol in USUARIOS:
        u = _get(session, Usuario, email=email)
        if u is None:
            u = Usuario(nombre=nombre, email=email, password_hash=hash_password(password), rol=rol.value)
            session.add(u)
        usuarios[rol.value] = u
    for nombre, cuit in PROVEEDORES:
        if _get(session, Proveedor, cuit=cuit) is None:
            session.add(Proveedor(nombre=nombre, cuit=cuit))
    for codigo, nombre, tipo, prueba in PRODUCTOS:
        if _get(session, Producto, codigo=codigo) is None:
            session.add(Producto(codigo=codigo, nombre=nombre, tipo=tipo, requiere_prueba_fisica=prueba))
    for nombre, tipo in DEPOSITOS:
        if _get(session, Deposito, nombre=nombre) is None:
            session.add(Deposito(nombre=nombre, tipo=tipo, lugar_disponible=True))
    session.commit()
    for u in usuarios.values():
        session.refresh(u)
    return usuarios




def seed_demo(session: Session, usuarios: dict[str, Usuario]) -> None:
    """Crea turnos y remitos en distintos estados para poder mostrar el sistema funcionando."""
    if session.exec(select(Remito.id)).first():
        return  # ya hay movimiento: no se pisa
    g, c = usuarios["guardia"], usuarios["calidad"]
    di, de = usuarios["deposito_insumos"], usuarios["deposito_expedicion"]
    an = usuarios["analista_insumos"]
    azu, lec, cac, glu, env, car, cho = (
        _get(session, Producto, codigo=cod).id
        for cod in ("AZU-001", "LEC-001", "CAC-001", "GLU-001", "ENV-001", "PT-CAR-001", "PT-CHO-001")
    )
    prov = {p.cuit: p.id for p in session.exec(select(Proveedor)).all()}
    dep_a = _get(session, Deposito, nombre="Depósito de Insumos A")
    dep_b = _get(session, Deposito, nombre="Depósito de Insumos B")
    dep_x = _get(session, Deposito, nombre="Expedición Central")

    hoy = date.today()
    # Turnos futuros (todavía no llegaron)
    for i, (producto, cuit) in enumerate(
        [(azu, "30-11111111-1"), (lec, "30-22222222-2"), (cac, "30-33333333-3")], 1
    ):
        session.add(
            Turno(
                fecha_estimada=hoy + timedelta(days=i),
                producto_id=producto,
                proveedor_id=prov[cuit],
                creado_por=an.id,
            )
        )
    # Turno que llega hoy (se vincula al remito 1)
    t_hoy = Turno(
        fecha_estimada=hoy, producto_id=azu, proveedor_id=prov["30-11111111-1"], creado_por=an.id
    )
    session.add(t_hoy)
    session.commit()
    session.refresh(t_hoy)

    def entrada(turno_id, numero, patente, dni, nombre, items):
        return svc.registrar_entrada(
            session,
            RemitoEntradaCreate(
                turno_id=turno_id,
                numero_remito=numero,
                patente=patente,
                chofer_dni=dni,
                chofer_nombre=nombre,
                items=[ItemEntradaCreate(**i) for i in items],
            ),
            g,
        )

    # 1) Descargado completo (genera stock en Insumos A)
    r1 = entrada(
        t_hoy.id, "0001-00004521", "AB123CD", "30111222", "Carlos Gómez",
        [{"producto_id": azu, "cantidad": 400, "unidad": "bolsas", "numero_lote": "AZ-2610-01"}],
    )
    svc.resolver_validacion(
        session, r1.id, ValidacionResolver(estado="aprobado", resultado_prueba_fisica="aprobado"), c
    )
    svc.asignar_deposito(session, r1.id, dep_a.id, di)
    svc.autorizar_ingreso(session, r1.id, g)
    svc.confirmar_descarga(session, r1.id, di)

    # 2) En estudio de Calidad (camión esperando afuera)
    entrada(
        None, "0003-00001188", "AC456EF", "28444555", "Marcelo Ríos",
        [{"producto_id": lec, "cantidad": 200, "unidad": "bolsas", "numero_lote": "LE-2610-07"}],
    )

    # 3) Rechazado por Calidad
    r3 = entrada(
        None, "0002-00000931", "AD789GH", "32777888", "Julián Paz",
        [{"producto_id": glu, "cantidad": 10, "unidad": "tambores", "numero_lote": "GL-2610-03"}],
    )
    svc.resolver_validacion(
        session,
        r3.id,
        ValidacionResolver(estado="rechazado", motivo_rechazo="Certificado de análisis vencido"),
        c,
    )

    # 4) Aprobado pero sin lugar (espera afuera)
    r4 = entrada(
        None, "0001-00007788", "AE321IJ", "25999000", "Hugo Medina",
        [{"producto_id": cac, "cantidad": 120, "unidad": "bolsas", "numero_lote": "CA-2610-02"}],
    )
    svc.resolver_validacion(session, r4.id, ValidacionResolver(estado="aprobado"), c)
    dep_b.lugar_disponible = False
    session.add(dep_b)
    session.commit()
    svc.marcar_espera(session, r4.id, dep_b.id, "Depósito B completo hasta mañana", di)

    # 5) Listo para ingresar (la Guardia solo tiene que abrir)
    r5 = entrada(
        None, "0004-00000345", "AF654KL", "27000111", "Sergio Luna",
        [{"producto_id": env, "cantidad": 30, "unidad": "bobinas", "numero_lote": "EN-2610-11"}],
    )
    svc.resolver_validacion(session, r5.id, ValidacionResolver(estado="aprobado"), c)
    svc.asignar_deposito(session, r5.id, dep_a.id, di)

    # Producción que llega a Expedición + un remito de salida despachado y otro preparado
    stock_svc.registrar_movimiento(
        session, producto_id=car, deposito_id=dep_x.id, tipo="entrada", cantidad=1500,
        usuario_id=de.id, motivo="Producción lote 2610 auditado por Calidad",
    )
    stock_svc.registrar_movimiento(
        session, producto_id=cho, deposito_id=dep_x.id, tipo="entrada", cantidad=800,
        usuario_id=de.id, motivo="Producción lote 2610 auditado por Calidad",
    )
    session.commit()
    s1 = svc.crear_salida(
        session,
        RemitoSalidaCreate(
            numero_precinto="PR-100234",
            deposito_id=dep_x.id,
            patente="AG111MN",
            chofer_dni="26333444",
            chofer_nombre="Raúl Ibarra",
            items=[ItemSalidaCreate(producto_id=car, cantidad=500, unidad="cajas")],
        ),
        de,
    )
    svc.registrar_egreso(session, s1.id, "PR-100234", g)
    svc.crear_salida(
        session,
        RemitoSalidaCreate(
            numero_precinto="PR-100235",
            deposito_id=dep_x.id,
            patente="AH222OP",
            chofer_dni="29888777",
            chofer_nombre="Diego Vera",
            items=[ItemSalidaCreate(producto_id=cho, cantidad=300, unidad="cajas")],
        ),
        de,
    )


def main() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        usuarios = seed_base(session)
        seed_demo(session, usuarios)
    print("Seed completo. Usuarios (contraseña = SEED_PASSWORD):")
    for _, email, rol in USUARIOS:
        print(f"  {email:28s} {rol.value}")


if __name__ == "__main__":
    main()