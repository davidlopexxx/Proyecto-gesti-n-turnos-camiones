from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.db import create_db_and_tables
from app.routers import auth, catalogos, remitos, turnos, usuarios


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Gestión de Turnos, Acceso y Remitos de Camiones",
    description=(
        "API REST del Trabajo Final Integrador (UTN - TUP a distancia). "
        "Un único estado del remito, consultable por Guardia, Calidad y Depósito, "
        "con registro auditable."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, exc: IntegrityError):
    # Valores duplicados (patente, DNI, CUIT, código, email...) o referencias inexistentes.
    return JSONResponse(
        status_code=409,
        content={"detail": "Ya existe un registro con esos datos o hay una referencia inválida"},
    )


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(catalogos.proveedores)
app.include_router(catalogos.productos)
app.include_router(catalogos.depositos)
app.include_router(catalogos.choferes)
app.include_router(catalogos.camiones)
app.include_router(turnos.router)
app.include_router(remitos.router)


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}