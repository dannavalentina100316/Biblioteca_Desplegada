from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine
from app.routes.common import ERROR_RESPONSES

router = APIRouter(
    prefix="/health",
    tags=["Salud"],
    responses={
        **ERROR_RESPONSES,
        503: {"description": "Base de datos no disponible"},
    },
)


@router.get("", summary="Verificar disponibilidad de la API y la base de datos")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Base de datos no disponible",
        ) from exc
    return {"status": "ok", "database": "ok"}
