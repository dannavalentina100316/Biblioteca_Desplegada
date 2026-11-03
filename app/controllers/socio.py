from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.socio import Socio
from app.models.prestamo import Prestamo
from app.schemas.socio import SocioCreate, SocioUpdate
from app.core.exceptions import NoEncontrado, Conflicto

def get_socios(db: Session, skip: int, limit: int, activo: Optional[bool] = None):
    query = db.query(Socio)
    if activo is not None:
        query = query.filter(Socio.activo == activo)
    total = query.count()
    return {
        "items": query.offset(skip).limit(limit).all(),
        "total": total,
        "skip": skip,
        "limit": limit,
    }

def get_socio_by_id(db: Session, socio_id: int):
    socio = db.query(Socio).filter(Socio.id == socio_id).first()
    if not socio:
        raise NoEncontrado("Socio no encontrado")
    return socio

def create_socio(db: Session, socio_in: SocioCreate):
    existente = db.query(Socio).filter(Socio.email == socio_in.email).first()
    if existente:
        raise Conflicto("El correo electrónico ya está registrado")

    nuevo_socio = Socio(**socio_in.model_dump())
    db.add(nuevo_socio)
    db.commit()
    db.refresh(nuevo_socio)
    return nuevo_socio

def update_socio(db: Session, socio_id: int, socio_in: SocioUpdate):
    socio = get_socio_by_id(db, socio_id)
    datos = socio_in.model_dump(exclude_unset=True)

    if "email" in datos:
        email_ex = db.query(Socio).filter(Socio.email == datos["email"], Socio.id != socio_id).first()
        if email_ex:
            raise Conflicto("El correo electrónico ya pertenece a otro socio")

    for key, value in datos.items():
        setattr(socio, key, value)

    db.commit()
    db.refresh(socio)
    return socio

def delete_socio(db: Session, socio_id: int):
    socio = get_socio_by_id(db, socio_id)
    
    # Verificar préstamos activos (sin devolver) usando la entidad Prestamo
    prestados_activos = db.query(Prestamo).filter(
        Prestamo.socio_id == socio_id,
        Prestamo.fecha_devolucion.is_(None)
    ).count()

    if prestados_activos > 0:
        raise Conflicto("No se puede eliminar ni desactivar el socio porque tiene préstamos sin devolver")

    # Verificar si tiene historial de préstamos (aunque estén devueltos)
    prestamos_totales = db.query(Prestamo).filter(Prestamo.socio_id == socio_id).count()

    if prestamos_totales > 0:
        # Borrado lógico: se desactiva
        socio.activo = False
        db.commit()
        return {"mensaje": "El socio tiene historial de préstamos, se ha marcado como inactivo"}
    else:
        # Si no tiene ningún préstamo, se elimina físicamente
        db.delete(socio)
        db.commit()
        return None

def get_prestamos_by_socio(db: Session, socio_id: int, estado: Optional[str], skip: int, limit: int):
    socio = get_socio_by_id(db, socio_id)
    from datetime import date
    
    query = db.query(Prestamo).filter(Prestamo.socio_id == socio_id)
    
    if estado == "activo":
        query = query.filter(Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite >= date.today())
    elif estado == "vencido":
        query = query.filter(Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite < date.today())
    elif estado == "devuelto":
        query = query.filter(Prestamo.fecha_devolucion.is_not(None))

    total = query.count()
    return {
        "items": query.offset(skip).limit(limit).all(),
        "total": total,
        "skip": skip,
        "limit": limit,
    }