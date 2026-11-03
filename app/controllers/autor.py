from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from typing import Optional
from app.models.autor import Autor
from app.schemas.autor import AutorCreate, AutorUpdate
from app.core.exceptions import NoEncontrado, Conflicto

def get_autores(db: Session, skip: int, limit: int, nacionalidad: Optional[str] = None):
    query = db.query(Autor)
    if nacionalidad:
        query = query.filter(Autor.nacionalidad.ilike(f"%{nacionalidad}%"))
    total = query.order_by(None).count()
    return {
        "items": query.offset(skip).limit(limit).all(),
        "total": total,
        "skip": skip,
        "limit": limit,
    }

def get_autor_by_id(db: Session, autor_id: int):
    autor = db.query(Autor).filter(Autor.id == autor_id).first()
    if not autor:
        raise NoEncontrado("Autor no encontrado")
    return autor

def create_autor(db: Session, autor_in: AutorCreate):
    existente = db.query(Autor).filter(Autor.nombre == autor_in.nombre).first()
    if existente:
        raise Conflicto("El autor ya existe")
    
    nuevo_autor = Autor(**autor_in.model_dump())
    db.add(nuevo_autor)
    db.commit()
    db.refresh(nuevo_autor)
    return nuevo_autor

def update_autor(db: Session, autor_id: int, autor_in: AutorUpdate):
    autor = get_autor_by_id(db, autor_id)
    datos = autor_in.model_dump(exclude_unset=True)
    
    if "nombre" in datos:
        existente = db.query(Autor).filter(Autor.nombre == datos["nombre"], Autor.id != autor_id).first()
        if existente:
            raise Conflicto("Ya existe otro autor con ese nombre")

    for key, value in datos.items():
        setattr(autor, key, value)
    
    db.commit()
    db.refresh(autor)
    return autor

def delete_autor(db: Session, autor_id: int):
    autor = get_autor_by_id(db, autor_id)
    if autor.libros:
        raise Conflicto("No se puede eliminar el autor porque tiene libros asociados")
    
    db.delete(autor)
    db.commit()
    return None