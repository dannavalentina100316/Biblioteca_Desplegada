from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers import libro as libro_controller
from app.controllers.libro import OrdenLibro
from app.core.dependencies import get_db, paginacion, requiere_rol
from app.models.usuario import RolUsuario
from app.routes.common import ERROR_RESPONSES
from app.schemas.libro import LibroCreate, LibroResponse, LibroUpdate
from app.schemas.pagina import Pagina

router = APIRouter(
    prefix="/libros",
    tags=["Libros"],
    responses=ERROR_RESPONSES,
)


@router.get(
    "",
    response_model=Pagina[LibroResponse],
    summary="Buscar y listar libros",
)
def listar_libros(
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
    buscar: str | None = None,
    autor: str | None = None,
    categoria_id: int | None = None,
    desde: int | None = None,
    hasta: int | None = None,
    orden: OrdenLibro | None = None,
):
    return libro_controller.get_libros(
        db,
        pag["skip"],
        pag["limit"],
        buscar,
        autor,
        categoria_id,
        desde,
        hasta,
        orden,
    )


@router.get(
    "/autores/{autor_id}/libros",
    response_model=Pagina[LibroResponse],
    summary="Listar libros de un autor",
)
def listar_libros_por_autor(
    autor_id: int,
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
):
    return libro_controller.get_libros_by_autor(
        db, autor_id, pag["skip"], pag["limit"]
    )


@router.get(
    "/{libro_id}",
    response_model=LibroResponse,
    summary="Consultar un libro",
)
def obtener_libro(
    libro_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return libro_controller.get_libro_by_id(db, libro_id)


@router.post(
    "",
    response_model=LibroResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un libro",
    dependencies=[requiere_rol(RolUsuario.admin, RolUsuario.bibliotecario)],
)
def crear_libro(
    libro: LibroCreate,
    db: Annotated[Session, Depends(get_db)],
):
    return libro_controller.create_libro(db, libro)


@router.patch(
    "/{libro_id}",
    response_model=LibroResponse,
    summary="Actualizar un libro",
    dependencies=[requiere_rol(RolUsuario.admin, RolUsuario.bibliotecario)],
)
def actualizar_libro(
    libro_id: int,
    libro: LibroUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    return libro_controller.update_libro(db, libro_id, libro)


@router.delete(
    "/{libro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un libro",
    dependencies=[requiere_rol(RolUsuario.admin)],
)
def eliminar_libro(
    libro_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return libro_controller.delete_libro(db, libro_id)
