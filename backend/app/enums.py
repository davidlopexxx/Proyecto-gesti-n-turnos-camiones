from enum import Enum


class Rol(str, Enum):
    guardia = "guardia"
    calidad = "calidad"
    deposito_insumos = "deposito_insumos"
    analista_insumos = "analista_insumos"
    deposito_expedicion = "deposito_expedicion"


class TipoDeposito(str, Enum):
    insumos = "insumos"
    expedicion = "expedicion"


class EstadoTurno(str, Enum):
    pendiente = "pendiente"
    confirmado = "confirmado"
    cancelado = "cancelado"


class TipoRemito(str, Enum):
    entrada = "entrada"
    salida = "salida"


class EstadoRemito(str, Enum):
    # Remitos de entrada
    en_estudio_calidad = "en_estudio_calidad"
    aprobado_calidad = "aprobado_calidad"
    esperando_lugar = "esperando_lugar"
    listo_para_ingreso = "listo_para_ingreso"
    rechazado = "rechazado"
    ingresado = "ingresado"
    descargado = "descargado"
    # Remitos de salida
    preparado = "preparado"
    egresado = "egresado"


class EstadoValidacion(str, Enum):
    pendiente = "pendiente"
    aprobado = "aprobado"
    rechazado = "rechazado"


class ResultadoPrueba(str, Enum):
    aprobado = "aprobado"
    rechazado = "rechazado"


class TipoMovimiento(str, Enum):
    entrada = "entrada"
    salida = "salida"