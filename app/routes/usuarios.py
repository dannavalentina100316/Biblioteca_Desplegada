from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers import usuario as usuario_controller
from app.core.dependencies import CurrentUser, get_db, paginacion, requiere_rol
from app.models.usuario import RolUsuario
from app.routes.common import ERROR_RESPONSES
from app.schemas.pagina import Pagina
from app.schemas.auth import UsuarioRespuesta
from app.schemas.usuario import (
    UsuarioActivoActualizar,
    UsuarioCrear,
    UsuarioRolActualizar,
)

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"],
    responses=ERROR_RESPONSES,
    dependencies=[requiere_rol(RolUsuario.admin)],
)


@router.get(
    "",
    response_model=Pagina[UsuarioRespuesta],
    summary="Listar usuarios",
)
def listar(
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
    rol: RolUsuario | None = None,
    activo: bool | None = None,
):
    return usuario_controller.listar_usuarios(
        db, pag["skip"], pag["limit"], rol, activo
    )


@router.post(
    "",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un bibliotecario o administrador",
)
def crear(
    datos: UsuarioCrear,
    db: Annotated[Session, Depends(get_db)],
):
    return usuario_controller.crear_usuario(db, datos)


@router.patch(
    "/{usuario_id}/rol",
    response_model=UsuarioRespuesta,
    summary="Cambiar el rol de un usuario",
)
def cambiar_rol(
    usuario_id: int,
    datos: UsuarioRolActualizar,
    db: Annotated[Session, Depends(get_db)],
    actor: CurrentUser,
):
    return usuario_controller.actualizar_rol(db, usuario_id, datos.rol, actor)


@router.patch(
    "/{usuario_id}/activo",
    response_model=UsuarioRespuesta,
    summary="Activar o desactivar un usuario",
)
def cambiar_estado(
    usuario_id: int,
    datos: UsuarioActivoActualizar,
    db: Annotated[Session, Depends(get_db)],
    actor: CurrentUser,
):
    return usuario_controller.actualizar_estado(
        db, usuario_id, datos.activo, actor
    )
