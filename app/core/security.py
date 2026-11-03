from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.exceptions import NoAutenticado
from app.models.usuario import Usuario


password_hasher = PasswordHash.recommended()
_dummy_password_hash = password_hasher.hash("not-a-real-user-password")


def hashear_password(password: str) -> str:
    return password_hasher.hash(password)


def verificar_password(password: str, hash_guardado: str) -> bool:
    return password_hasher.verify(password, hash_guardado)


def verificar_password_inexistente(password: str) -> None:
    password_hasher.verify(password, _dummy_password_hash)


def crear_token(
    usuario: Usuario, tipo: str, duracion: timedelta
) -> tuple[str, str, datetime]:
    ahora = datetime.now(timezone.utc)
    jti = str(uuid4())
    expira_en = ahora + duracion
    payload = {
        "sub": str(usuario.id),
        "rol": usuario.rol.value,
        "type": tipo,
        "iat": ahora,
        "exp": expira_en,
        "jti": jti,
    }
    token = jwt.encode(
        payload,
        get_settings().secret_key,
        algorithm=get_settings().algorithm,
    )
    return token, jti, expira_en


def leer_token(token: str, tipo_esperado: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except jwt.InvalidTokenError as exc:
        raise NoAutenticado("Token inválido o vencido") from exc
    if payload.get("type") != tipo_esperado:
        raise NoAutenticado("Tipo de token inválido")
    return payload


def normalizar_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
