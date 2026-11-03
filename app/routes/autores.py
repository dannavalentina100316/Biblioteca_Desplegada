from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers import autor as autor_controller
from app.controllers import libro as libro_controller
from app.core.dependencies import get_db, paginacion, requiere_rol
from app.models.usuario import RolUsuario
from app.routes.common import ERROR_RESPONSES
from app.schemas.autor import AutorCreate, AutorResponse, AutorUpdate
from app.schemas.libro import LibroResponse
from app.schemas.pagina import Pagina

router = APIRouter(
    prefix="/autores",
    tags=["Autores"],
    responses=ERROR_RESPONSES,
)


@router.get(
    "",
    response_model=Pagina[AutorResponse],
    summary="Listar autores",
)
def listar_autores(
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
    nacionalidad: str | None = None,
):
    return autor_controller.get_autores(
        db, pag["skip"], pag["limit"], nacionalidad
    )


@router.get(
    "/{autor_id}",
    response_model=AutorResponse,
    summary="Consultar un autor",
)
def obtener_autor(
    autor_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return autor_controller.get_autor_by_id(db, autor_id)


@router.post(
    "",
    response_model=AutorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un autor",
    dependencies=[requiere_rol(RolUsuario.admin, RolUsuario.bibliotecario)],
)
def crear_autor(
    autor: AutorCreate,
    db: Annotated[Session, Depends(get_db)],
):
    return autor_controller.create_autor(db, autor)


@router.patch(
    "/{autor_id}",
    response_model=AutorResponse,
    summary="Actualizar un autor",
    dependencies=[requiere_rol(RolUsuario.admin, RolUsuario.bibliotecario)],
)
def actualizar_autor(
    autor_id: int,
    autor: AutorUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    return autor_controller.update_autor(db, autor_id, autor)


@router.delete(
    "/{autor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un autor",
    dependencies=[requiere_rol(RolUsuario.admin)],
)
def eliminar_autor(
    autor_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return autor_controller.delete_autor(db, autor_id)


@router.get(
    "/{autor_id}/libros",
    response_model=Pagina[LibroResponse],
    summary="Listar libros de un autor",
)
def listar_libros_de_autor(
    autor_id: int,
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
):
    return libro_controller.get_libros_by_autor(
        db, autor_id, pag["skip"], pag["limit"]
    )
