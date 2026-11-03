from sqlalchemy.orm import Session
from app.models.categoria import Categoria
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate
from app.core.exceptions import NoEncontrado, Conflicto

def get_categorias(db: Session, skip: int, limit: int):
    query = db.query(Categoria)
    total = query.count()
    return {
        "items": query.offset(skip).limit(limit).all(),
        "total": total,
        "skip": skip,
        "limit": limit,
    }

def get_categoria_by_id(db: Session, categoria_id: int):
    cat = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not cat:
        raise NoEncontrado("Categoría no encontrada")
    return cat

def create_categoria(db: Session, cat_in: CategoriaCreate):
    existente = db.query(Categoria).filter(Categoria.nombre == cat_in.nombre).first()
    if existente:
        raise Conflicto("La categoría ya existe")
    
    nueva_cat = Categoria(**cat_in.model_dump())
    db.add(nueva_cat)
    db.commit()
    db.refresh(nueva_cat)
    return nueva_cat

def update_categoria(db: Session, categoria_id: int, cat_in: CategoriaUpdate):
    cat = get_categoria_by_id(db, categoria_id)
    datos = cat_in.model_dump(exclude_unset=True)
    
    if "nombre" in datos:
        existente = db.query(Categoria).filter(Categoria.nombre == datos["nombre"], Categoria.id != categoria_id).first()
        if existente:
            raise Conflicto("Ya existe otra categoría con ese nombre")

    for key, value in datos.items():
        setattr(cat, key, value)
    
    db.commit()
    db.refresh(cat)
    return cat

def delete_categoria(db: Session, categoria_id: int):
    cat = get_categoria_by_id(db, categoria_id)
    # SQLAlchemy limpia automáticamente la tabla intermedia gracias a la relación secondary
    db.delete(cat)
    db.commit()
    return None