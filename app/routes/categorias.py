from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers import categoria as categoria_controller
from app.core.dependencies import get_db, paginacion, requiere_rol
from app.models.usuario import RolUsuario
from app.routes.common import ERROR_RESPONSES
from app.schemas.categoria import (
    CategoriaCreate,
    CategoriaResponse,
    CategoriaUpdate,
)
from app.schemas.pagina import Pagina

router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"],
    responses=ERROR_RESPONSES,
)


@router.get(
    "",
    response_model=Pagina[CategoriaResponse],
    summary="Listar categorías",
)
def listar_categorias(
    db: Annotated[Session, Depends(get_db)],
    pag: Annotated[dict, Depends(paginacion)],
):
    return categoria_controller.get_categorias(
        db, pag["skip"], pag["limit"]
    )


@router.post(
    "",
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una categoría",
    dependencies=[requiere_rol(RolUsuario.admin, RolUsuario.bibliotecario)],
)
def crear_categoria(
    categoria: CategoriaCreate,
    db: Annotated[Session, Depends(get_db)],
):
    return categoria_controller.create_categoria(db, categoria)


@router.patch(
    "/{categoria_id}",
    response_model=CategoriaResponse,
    summary="Actualizar una categoría",
    dependencies=[requiere_rol(RolUsuario.admin, RolUsuario.bibliotecario)],
)
def actualizar_categoria(
    categoria_id: int,
    categoria: CategoriaUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    return categoria_controller.update_categoria(db, categoria_id, categoria)


@router.delete(
    "/{categoria_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una categoría",
    dependencies=[requiere_rol(RolUsuario.admin)],
)
def eliminar_categoria(
    categoria_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return categoria_controller.delete_categoria(db, categoria_id)
