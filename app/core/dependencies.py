from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy import select
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import NoAutenticado, Prohibido
from app.core.security import leer_token
from app.models.usuario import RolUsuario, Usuario

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def paginacion(
    skip: int = Query(0, ge=0, description="Registros a saltar"),
    limit: int = Query(10, ge=1, le=100, description="Límite de registros por página")
):
    return {"skip": skip, "limit": limit}


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> Usuario:
    if token is None:
        raise NoAutenticado("No se proporcionó un token")
    payload = leer_token(token, "access")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise NoAutenticado("Token inválido o vencido") from exc
    usuario = db.scalar(select(Usuario).where(Usuario.id == user_id))
    if usuario is None:
        raise NoAutenticado("Token inválido o vencido")
    if not usuario.activo:
        raise Prohibido("Usuario inactivo")
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def requiere_rol(*roles: RolUsuario):
    def verificar(usuario: CurrentUser) -> Usuario:
        if usuario.rol not in roles:
            raise Prohibido()
        return usuario

    return Depends(verificar)
