from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers import reporte as reporte_controller
from app.core.dependencies import get_db, requiere_rol
from app.models.usuario import RolUsuario
from app.routes.common import ERROR_RESPONSES
from app.schemas.pagina import Pagina
from app.schemas.reporte import (
    ReporteAutor,
    ReporteCategoria,
    ReporteLibroMasPrestado,
    ReportePrestamoVencido,
    ReporteResumen,
    ReporteSocioMulta,
)

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"],
    responses=ERROR_RESPONSES,
    dependencies=[
        requiere_rol(RolUsuario.admin, RolUsuario.bibliotecario)
    ],
)


@router.get(
    "/libros-mas-prestados",
    response_model=Pagina[ReporteLibroMasPrestado],
    summary="Consultar los libros más prestados",
)
def libros_mas_prestados(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limite: int = Query(5, ge=1, le=100),
):
    return reporte_controller.get_libros_mas_prestados(db, limite, skip)


@router.get(
    "/categorias",
    response_model=Pagina[ReporteCategoria],
    summary="Consultar libros por categoría",
)
def reporte_categorias(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return reporte_controller.get_reporte_categorias(db, skip, limit)


@router.get(
    "/prestamos-vencidos",
    response_model=Pagina[ReportePrestamoVencido],
    summary="Consultar préstamos vencidos",
)
def prestamos_vencidos(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return reporte_controller.get_prestamos_vencidos(db, skip, limit)


@router.get(
    "/socios-con-multas",
    response_model=Pagina[ReporteSocioMulta],
    summary="Consultar socios con multas",
)
def socios_con_multas(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return reporte_controller.get_socios_con_multas(db, skip, limit)


@router.get(
    "/autores",
    response_model=Pagina[ReporteAutor],
    summary="Consultar estadísticas por autor",
)
def reporte_autores(
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return reporte_controller.get_reporte_autores(db, skip, limit)


@router.get(
    "/resumen",
    response_model=ReporteResumen,
    summary="Consultar el resumen general de la biblioteca",
)
def resumen_general(db: Annotated[Session, Depends(get_db)]):
    return reporte_controller.get_resumen_general(db)
