from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    sal = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), sal).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, rol: str) -> str:
    vence = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    contenido = {"sub": subject, "rol": rol, "exp": vence}
    return jwt.encode(contenido, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Devuelve el contenido o lanza jwt.PyJWTError si es inválido o venció."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])