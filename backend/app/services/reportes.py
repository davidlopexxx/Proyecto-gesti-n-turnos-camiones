"""Indicadores para el panel y los reportes (Analista de Insumos / Administración)."""
from collections import Counter
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.enums import EstadoRemito as E
from app.enums import EstadoValidacion, TipoRemito
from app.models import Producto, Proveedor, Remito, RemitoItem, Turno, ValidacionCalidad

ESTADOS_ESPERANDO = [
    E.en_estudio_calidad.value,
    E.aprobado_calidad.value,
    E.esperando_lugar.value,
    E.listo_para_ingreso.value,
]


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _minutos(a: datetime | None, b: datetime | None) -> float | None:
    a, b = _aware(a), _aware(b)
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 60


def _promedio(valores: list[float | None]) -> float | None:
    vs = [v for v in valores if v is not None]
    return round(sum(vs) / len(vs), 1) if vs else None


def _filtrar_fecha(remitos: list[Remito], desde: datetime | None, hasta: datetime | None) -> list[Remito]:
    d, h = _aware(desde), _aware(hasta)
    return [r for r in remitos if (d is None or _aware(r.fecha) >= d) and (h is None or _aware(r.fecha) <= h)]


def resumen(session: Session, desde: datetime | None = None, hasta: datetime | None = None) -> dict:
    remitos = _filtrar_fecha(list(session.exec(select(Remito)).all()), desde, hasta)
    entradas = [r for r in remitos if r.tipo == TipoRemito.entrada.value]
    salidas = [r for r in remitos if r.tipo == TipoRemito.salida.value]
    ids_entrada = {r.id for r in entradas}

    validaciones = [
        v
        for v in session.exec(select(ValidacionCalidad)).all()
        if v.remito_id in ids_entrada and v.fecha_resolucion is not None
    ]
    tiempos_calidad = [_minutos(v.fecha_inicio, v.fecha_resolucion) for v in validaciones]

    # Rechazos por proveedor (vía turno). Los remitos sin turno van a "Sin turno / sin proveedor".
    turnos = {t.id: t for t in session.exec(select(Turno)).all()}
    proveedores = {p.id: p.nombre for p in session.exec(select(Proveedor)).all()}
    rechazos_por_proveedor: Counter = Counter()
    motivos: Counter = Counter()
    rechazadas = [v for v in validaciones if v.estado == EstadoValidacion.rechazado.value]
    remito_por_id = {r.id: r for r in entradas}
    for v in rechazadas:
        r = remito_por_id[v.remito_id]
        turno = turnos.get(r.turno_id) if r.turno_id else None
        nombre = proveedores.get(turno.proveedor_id) if turno and turno.proveedor_id else None
        rechazos_por_proveedor[nombre or "Sin turno / sin proveedor"] += 1
        motivos[(v.motivo_rechazo or "").strip().lower() or "sin motivo"] += 1

    total_resueltas = len(validaciones)
    return {
        "remitos_por_estado": dict(Counter(r.estado_general for r in remitos)),
        "total_entradas": len(entradas),
        "total_salidas": len(salidas),
        "camiones_esperando": sum(1 for r in entradas if r.estado_general in ESTADOS_ESPERANDO),
        "camiones_sin_lugar": sum(1 for r in entradas if r.estado_general == E.esperando_lugar.value),
        "tiempo_promedio_calidad_min": _promedio(tiempos_calidad),
        "tiempo_promedio_llegada_a_ingreso_min": _promedio([_minutos(r.fecha, r.ingresado_en) for r in entradas]),
        "tiempo_promedio_ingreso_a_descarga_min": _promedio(
            [_minutos(r.ingresado_en, r.descargado_en) for r in entradas]
        ),
        "validaciones_resueltas": total_resueltas,
        "tasa_rechazo_pct": round(100 * len(rechazadas) / total_resueltas, 1) if total_resueltas else None,
        "rechazos_por_proveedor": dict(rechazos_por_proveedor),
        "motivos_rechazo": dict(motivos),
    }


def conciliacion(session: Session, desde: datetime | None = None, hasta: datetime | None = None) -> list[dict]:
    """Para Administración/Compras: unidades recibidas (descargadas) vs. despachadas (egresadas) por producto."""
    remitos = _filtrar_fecha(list(session.exec(select(Remito)).all()), desde, hasta)
    por_id = {r.id: r for r in remitos}
    productos = {p.id: p for p in session.exec(select(Producto)).all()}
    recibido: Counter = Counter()
    despachado: Counter = Counter()
    for it in session.exec(select(RemitoItem)).all():
        r = por_id.get(it.remito_id)
        if r is None:
            continue
        if r.tipo == TipoRemito.entrada.value and r.estado_general == E.descargado.value:
            recibido[it.producto_id] += it.cantidad
        elif r.tipo == TipoRemito.salida.value and r.estado_general == E.egresado.value:
            despachado[it.producto_id] += it.cantidad
    filas = []
    for pid in sorted(set(recibido) | set(despachado)):
        p = productos[pid]
        filas.append(
            {
                "producto_id": pid,
                "producto_codigo": p.codigo,
                "producto_nombre": p.nombre,
                "recibido": recibido[pid],
                "despachado": despachado[pid],
                "diferencia": recibido[pid] - despachado[pid],
            }
        )
    return filas