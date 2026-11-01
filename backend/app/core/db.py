from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


def make_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = make_engine(settings.sqlalchemy_url)


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por request."""
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    """Crea las tablas que falten."""
    import app.models  # noqa: F401

    SQLModel.metadata.create_all(engine)