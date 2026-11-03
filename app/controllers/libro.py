from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, desc
from typing import Optional, List
from enum import Enum

from app.models.libro import Libro
from app.models.autor import Autor
from app.models.categoria import Categoria
from app.models.prestamo import Prestamo
from app.schemas.libro import LibroCreate, LibroUpdate
from app.core.exceptions import NoEncontrado, Conflicto, ReglaNegocio

class OrdenLibro(str, Enum):
    titulo = "titulo"
    anio = "anio"
    anio_desc = "-anio"

def calcular_disponibles(db: Session, libro: Libro) -> int:
    # Cuenta los préstamos sin devolver (fecha_devolucion es None)
    prestados = db.query(Prestamo).filter(
        Prestamo.libro_id == libro.id,
        Prestamo.fecha_devolucion.is_(None)
    ).count()
    return libro.ejemplares - prestados

def enriq_libro(db: Session, libro: Libro) -> dict:
    # Transforma el modelo a diccionario o añade el atributo calculable para el schema Response
    setattr(libro, "disponibles", calcular_disponibles(db, libro))
    return libro

def get_libros(
    db: Session,
    skip: int,
    limit: int,
    buscar: Optional[str] = None,
    autor: Optional[str] = None,
    categoria_id: Optional[int] = None,
    desde: Optional[int] = None,
    hasta: Optional[int] = None,
    orden: Optional[OrdenLibro] = None
):
    consulta = db.query(Libro).options(
        selectinload(Libro.autor),
        selectinload(Libro.categorias)
    )

    if buscar:
        consulta = consulta.filter(Libro.titulo.ilike(f"%{buscar}%"))
    if autor:
        consulta = consulta.join(Libro.autor).filter(Autor.nombre.ilike(f"%{autor}%"))
    if categoria_id:
        consulta = consulta.join(Libro.categorias).filter(Categoria.id == categoria_id)
    if desde:
        consulta = consulta.filter(Libro.anio_publicacion >= desde)
    if hasta:
        consulta = consulta.filter(Libro.anio_publicacion <= hasta)

    if orden:
        if orden == OrdenLibro.titulo:
            consulta = consulta.order_by(Libro.titulo)
        elif orden == OrdenLibro.anio:
            consulta = consulta.order_by(Libro.anio_publicacion)
        elif orden == OrdenLibro.anio_desc:
            consulta = consulta.order_by(desc(Libro.anio_publicacion))

    total = consulta.order_by(None).distinct().count()
    libros = consulta.offset(skip).limit(limit).all()
    return {
        "items": [enriq_libro(db, l) for l in libros],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

def get_libro_by_id(db: Session, libro_id: int):
    libro = db.query(Libro).options(
        selectinload(Libro.autor),
        selectinload(Libro.categorias)
    ).filter(Libro.id == libro_id).first()

    if not libro:
        raise NoEncontrado("Libro no encontrado")
    return enriq_libro(db, libro)

def create_libro(db: Session, libro_in: LibroCreate):
    # Validar ISBN único (409)
    isbn_existente = db.query(Libro).filter(Libro.isbn == libro_in.isbn).first()
    if isbn_existente:
        raise Conflicto("El ISBN ya existe")

    # Validar que el autor exista (404)
    autor_obj = db.query(Autor).filter(Autor.id == libro_in.autor_id).first()
    if not autor_obj:
        raise NoEncontrado("El autor especificado no existe")

    # Validar que todas las categorías existan (404)
    categorias_obj = db.query(Categoria).filter(Categoria.id.in_(libro_in.categoria_ids)).all()
    if len(categorias_obj) != len(libro_in.categoria_ids):
        raise NoEncontrado("Una o más categorías especificadas no existen")

    datos_libro = libro_in.model_dump(exclude={"categoria_ids"})
    nuevo_libro = Libro(**datos_libro)
    nuevo_libro.categorias = categorias_obj

    db.add(nuevo_libro)
    db.commit()
    db.refresh(nuevo_libro)
    return enriq_libro(db, nuevo_libro)

def update_libro(db: Session, libro_id: int, libro_in: LibroUpdate):
    libro = db.query(Libro).filter(Libro.id == libro_id).first()
    if not libro:
        raise NoEncontrado("Libro no encontrado")

    datos = libro_in.model_dump(exclude_unset=True)

    if "isbn" in datos:
        isbn_ex = db.query(Libro).filter(Libro.isbn == datos["isbn"], Libro.id != libro_id).first()
        if isbn_ex:
            raise Conflicto("Ya existe otro libro con ese ISBN")

    if "autor_id" in datos:
        autor_obj = db.query(Autor).filter(Autor.id == datos["autor_id"]).first()
        if not autor_obj:
            raise NoEncontrado("El autor especificado no existe")

    if "categoria_ids" in datos:
        cats = db.query(Categoria).filter(Categoria.id.in_(datos["categoria_ids"])).all()
        if len(cats) != len(datos["categoria_ids"]):
            raise NoEncontrado("Una o más categorías no existen")
        libro.categorias = cats
        del datos["categoria_ids"]

    if "ejemplares" in datos:
        prestados_activos = db.query(Prestamo).filter(
            Prestamo.libro_id == libro_id,
            Prestamo.fecha_devolucion.is_(None)
        ).count()
        if datos["ejemplares"] < prestados_activos:
            raise ReglaNegocio("No se pueden reducir los ejemplares por debajo de los préstamos activos")

    for key, value in datos.items():
        setattr(libro, key, value)

    db.commit()
    db.refresh(libro)
    return enriq_libro(db, libro)

def delete_libro(db: Session, libro_id: int):
    libro = db.query(Libro).filter(Libro.id == libro_id).first()
    if not libro:
        raise NoEncontrado("Libro no encontrado")

    prestados_activos = db.query(Prestamo).filter(
        Prestamo.libro_id == libro_id,
        Prestamo.fecha_devolucion.is_(None)
    ).count()

    if prestados_activos > 0:
        raise Conflicto("No se puede eliminar el libro porque tiene préstamos sin devolver")

    db.delete(libro)
    db.commit()
    return None

def get_libros_by_autor(db: Session, autor_id: int, skip: int, limit: int):
    autor = db.query(Autor).filter(Autor.id == autor_id).first()
    if not autor:
        raise NoEncontrado("Autor no encontrado")

    query = db.query(Libro).options(
        selectinload(Libro.autor),
        selectinload(Libro.categorias)
    ).filter(Libro.autor_id == autor_id)
    total = query.count()
    libros = query.offset(skip).limit(limit).all()

    return {
        "items": [enriq_libro(db, l) for l in libros],
        "total": total,
        "skip": skip,
        "limit": limit,
    }