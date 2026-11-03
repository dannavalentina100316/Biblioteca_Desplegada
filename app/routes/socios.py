from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.controllers import socio as socio_controller
from app.controllers import prestamo as prestamo_controller
from app.controllers.libro import enriq_libro
from app.core.dependencies import (
    CurrentUser,
    get_db,
    paginacion,
    requiere_rol,
)
from app.core.exceptions import NoEncontrado
from app.models.prestamo import Prestamo
from app.models.usuario import RolUsuario
from app.routes.common import ERROR_RESPONSES
from app.schemas.multas import MultasSocioRespuesta
from app.schemas.pagina import Pagina
from app.schemas.prestamo import PrestamoResponse
from app.schemas.socio import SocioCreate, SocioResponse, SocioUpdate
from app.schemas.socio_propio import SocioActualizarPropio

STAFF = (RolUsuario.admin, RolUsuario.bibliotecario)
router = APIRouter(
    prefix="/socios",
    tags=["Socios"],
    responses=ERROR_RESPONSES,
)


def _socio_propio_id(usuario: CurrentUser) -> int:
    if usuario.socio_id is None:
        raise NoEncontrado("Perfil de socio no encontrado")
    return usuario.socio_id


@router.get(
    "/me",
    response_model=SocioResponse,
    summary="Consultar el perfil propio",
    dependencies=[requiere_rol(RolUsuario.socio)],
)
def obtener_perfil(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    return socio_controller.get_socio_by_id(db, _socio_propio_id(usuario))


@router.patch(
    "/me",
    response_model=SocioResponse,
    summary="Actualizar nombre y teléfono propios",
    dependencies=[requiere_rol(RolUsuario.socio)],
)
def actualizar_perfil(
    datos: SocioActualizarPropio,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    socio_id = _socio_propio_id(usuario)
    actualizacion = SocioUpdate(**datos.model_dump(exclude_unset=True))
    return socio_controller.update_socio(db, socio_id, actualizacion)


@router.get(
    "/me/prestamos",
    response_model=Pagina[PrestamoResponse],
    summary="Listar préstamos propios",
    dependencies=[requiere_rol(RolUsuario.socio)],
)
def listar_prestamos_propios(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
    estado: str | None = None,
):
    return socio_controller.get_prestamos_by_socio(
        db, _socio_propio_id(usuario), estado, pag["skip"], pag["limit"]
    )


@router.get(
    "/me/multas",
    response_model=MultasSocioRespuesta,
    summary="Consultar multas pendientes propias",
    dependencies=[requiere_rol(RolUsuario.socio)],
)
def listar_multas_propias(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
):
    query = db.query(Prestamo).filter(
        Prestamo.socio_id == _socio_propio_id(usuario),
        Prestamo.multa > 0,
        Prestamo.multa_pagada.is_(False),
    )
    total = query.count()
    total_multa = db.query(func.coalesce(func.sum(Prestamo.multa), 0.0)).filter(
        Prestamo.socio_id == usuario.socio_id,
        Prestamo.multa > 0,
        Prestamo.multa_pagada.is_(False),
    ).scalar()
    items = query.order_by(Prestamo.id).offset(pag["skip"]).limit(pag["limit"]).all()
    for prestamo in items:
        if prestamo.libro:
            enriq_libro(db, prestamo.libro)
    return {
        "items": items,
        "total": total,
        "skip": pag["skip"],
        "limit": pag["limit"],
        "total_multa": float(total_multa or 0),
    }


@router.get(
    "",
    response_model=Pagina[SocioResponse],
    summary="Listar socios",
    dependencies=[requiere_rol(*STAFF)],
)
def listar_socios(
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
    activo: bool | None = None,
):
    return socio_controller.get_socios(
        db, pag["skip"], pag["limit"], activo
    )


@router.post(
    "",
    response_model=SocioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un socio",
    dependencies=[requiere_rol(*STAFF)],
)
def crear_socio(
    socio: SocioCreate,
    db: Annotated[Session, Depends(get_db)],
):
    return socio_controller.create_socio(db, socio)


@router.get(
    "/{socio_id}",
    response_model=SocioResponse,
    summary="Consultar un socio",
    dependencies=[requiere_rol(*STAFF)],
)
def obtener_socio(
    socio_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return socio_controller.get_socio_by_id(db, socio_id)


@router.patch(
    "/{socio_id}",
    response_model=SocioResponse,
    summary="Actualizar un socio",
    dependencies=[requiere_rol(*STAFF)],
)
def actualizar_socio(
    socio_id: int,
    socio: SocioUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    return socio_controller.update_socio(db, socio_id, socio)


@router.delete(
    "/{socio_id}",
    summary="Eliminar o desactivar un socio",
    dependencies=[requiere_rol(RolUsuario.admin)],
)
def eliminar_socio(
    socio_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    resultado = socio_controller.delete_socio(db, socio_id)
    if resultado is None:
        return {"mensaje": "Socio eliminado exitosamente"}
    return resultado


@router.get(
    "/{socio_id}/prestamos",
    response_model=Pagina[PrestamoResponse],
    summary="Listar préstamos de un socio",
    dependencies=[requiere_rol(*STAFF)],
)
def listar_prestamos_socio(
    socio_id: int,
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
    estado: str | None = None,
):
    return socio_controller.get_prestamos_by_socio(
        db, socio_id, estado, pag["skip"], pag["limit"]
    )
