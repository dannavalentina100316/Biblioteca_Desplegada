from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers import prestamo as prestamo_controller
from app.core.dependencies import CurrentUser, get_db, paginacion, requiere_rol
from app.core.exceptions import NoEncontrado
from app.models.usuario import RolUsuario
from app.routes.common import ERROR_RESPONSES
from app.schemas.pagina import Pagina
from app.schemas.prestamo import (
    DevolucionCreate,
    PrestamoCreate,
    PrestamoResponse,
)

STAFF = (RolUsuario.admin, RolUsuario.bibliotecario)
router = APIRouter(
    prefix="/prestamos",
    tags=["Préstamos"],
    responses=ERROR_RESPONSES,
)


@router.get(
    "",
    response_model=Pagina[PrestamoResponse],
    summary="Listar préstamos permitidos para el usuario",
)
def listar_prestamos(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
    estado: str | None = None,
    socio_id: int | None = None,
    libro_id: int | None = None,
):
    if usuario.rol == RolUsuario.socio:
        if usuario.socio_id is None:
            raise NoEncontrado("Perfil de socio no encontrado")
        socio_id = usuario.socio_id
    return prestamo_controller.get_prestamos(
        db, pag["skip"], pag["limit"], estado, socio_id, libro_id
    )


@router.get(
    "/{prestamo_id}",
    response_model=PrestamoResponse,
    summary="Consultar un préstamo propio o autorizado",
)
def obtener_prestamo(
    prestamo_id: int,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    socio_id = None
    if usuario.rol == RolUsuario.socio:
        if usuario.socio_id is None:
            raise NoEncontrado("Perfil de socio no encontrado")
        socio_id = usuario.socio_id
    return prestamo_controller.get_prestamo_by_id(
        db, prestamo_id, socio_id
    )


@router.post(
    "",
    response_model=PrestamoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un préstamo",
    dependencies=[requiere_rol(*STAFF)],
)
def crear_prestamo(
    prestamo: PrestamoCreate,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    return prestamo_controller.create_prestamo(
        db, prestamo, registrado_por_id=usuario.id
    )


@router.post(
    "/{prestamo_id}/devolucion",
    response_model=PrestamoResponse,
    summary="Registrar la devolución de un préstamo",
    dependencies=[requiere_rol(*STAFF)],
)
def devolver_prestamo(
    prestamo_id: int,
    devolucion: DevolucionCreate,
    db: Annotated[Session, Depends(get_db)],
):
    return prestamo_controller.registrar_devolucion(
        db, prestamo_id, devolucion
    )


@router.post(
    "/{prestamo_id}/pago-multa",
    response_model=PrestamoResponse,
    summary="Registrar el pago de una multa",
    dependencies=[requiere_rol(*STAFF)],
    responses={409: {"description": "Multa ausente o ya pagada"}},
)
def pagar_multa(
    prestamo_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return prestamo_controller.pagar_multa(db, prestamo_id)
