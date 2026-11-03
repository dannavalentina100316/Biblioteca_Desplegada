from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from datetime import date

from app.models.libro import Libro
from app.models.autor import Autor
from app.models.categoria import Categoria, libro_categoria
from app.models.socio import Socio
from app.models.prestamo import Prestamo

def get_libros_mas_prestados(
    db: Session, limite: int = 5, skip: int = 0
):
    consulta = db.query(
        Libro.titulo.label("titulo_libro"),
        Autor.nombre.label("nombre_autor"),
        func.count(Prestamo.id).label("total_prestamos")
    ).join(Libro.autor)\
     .join(Prestamo, Prestamo.libro_id == Libro.id)\
     .group_by(Libro.id, Autor.id)
    total = consulta.order_by(None).count()
    resultados = consulta.order_by(desc("total_prestamos"))\
     .offset(skip).limit(limite).all()
     
    return {
        "items": [
          {
            "titulo_libro": r.titulo_libro,
            "nombre_autor": r.nombre_autor,
            "total_prestamos": r.total_prestamos
          } for r in resultados
        ],
        "total": total,
        "skip": skip,
        "limit": limite,
    }

def get_reporte_categorias(db: Session, skip: int = 0, limit: int = 10):
    total_libros = func.count(libro_categoria.c.libro_id).label("total_libros")
    consulta = db.query(
        Categoria.nombre.label("nombre_categoria"),
        total_libros
    ).outerjoin(libro_categoria, libro_categoria.c.categoria_id == Categoria.id)\
     .group_by(Categoria.id, Categoria.nombre)
    total = consulta.order_by(None).count()
    resultados = consulta.offset(skip).limit(limit).all()
     
    return {
        "items": [
          {
            "nombre_categoria": r.nombre_categoria,
            "total_libros": r.total_libros
          } for r in resultados
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

def get_prestamos_vencidos(db: Session, skip: int = 0, limit: int = 10):
    hoy = date.today()
    # Días de retraso se calcula en SQL con func.julianday o la diferencia de fechas de PostgreSQL
    consulta = db.query(
        Prestamo.id.label("prestamo_id"),
        Libro.titulo.label("titulo_libro"),
        Socio.nombre.label("nombre_socio"),
        Socio.email.label("email_socio"),
        Prestamo.fecha_limite,
        (hoy - Prestamo.fecha_limite).label("dias_retraso")
    ).join(Libro, Prestamo.libro_id == Libro.id)\
     .join(Socio, Prestamo.socio_id == Socio.id)\
     .filter(Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite < hoy)
    total = consulta.order_by(None).count()
    resultados = consulta.offset(skip).limit(limit).all()
     
    return {
        "items": [
          {
            "prestamo_id": r.prestamo_id,
            "titulo_libro": r.titulo_libro,
            "nombre_socio": r.nombre_socio,
            "email_socio": r.email_socio,
            "fecha_limite": str(r.fecha_limite),
            "dias_retraso": r.dias_retraso.days if hasattr(r.dias_retraso, 'days') else int(r.dias_retraso)
          } for r in resultados
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

def get_socios_con_multas(db: Session, skip: int = 0, limit: int = 10):
    consulta = db.query(
        Socio.nombre.label("nombre_socio"),
        Socio.email.label("email_socio"),
        func.sum(Prestamo.multa).label("total_multas"),
        func.count(Prestamo.id).label("prestamos_con_multa")
    ).join(Prestamo, Prestamo.socio_id == Socio.id)\
     .filter(Prestamo.multa > 0, Prestamo.multa_pagada.is_(False))\
     .group_by(Socio.id, Socio.nombre, Socio.email)\
     .having(func.sum(Prestamo.multa) > 0)
    total = consulta.order_by(None).count()
    resultados = consulta.offset(skip).limit(limit).all()
     
    return {
        "items": [
          {
            "nombre_socio": r.nombre_socio,
            "email_socio": r.email_socio,
            "total_multas": float(r.total_multas or 0),
            "prestamos_con_multa": r.prestamos_con_multa
          } for r in resultados
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

def get_reporte_autores(db: Session, skip: int = 0, limit: int = 10):
    consulta = db.query(
        Autor.nombre.label("nombre_autor"),
        func.count(Libro.id).label("total_libros"),
        func.coalesce(func.sum(Libro.ejemplares), 0).label("total_ejemplares"),
        func.count(Prestamo.id).label("total_prestamos")
    ).outerjoin(Libro, Libro.autor_id == Autor.id)\
     .outerjoin(Prestamo, Prestamo.libro_id == Libro.id)\
     .group_by(Autor.id, Autor.nombre)
    total = consulta.order_by(None).count()
    resultados = consulta.offset(skip).limit(limit).all()
     
    return {
        "items": [
          {
            "nombre_autor": r.nombre_autor,
            "total_libros": r.total_libros,
            "total_ejemplares": int(r.total_ejemplares),
            "total_prestamos": r.total_prestamos
          } for r in resultados
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

def get_resumen_general(db: Session):
    hoy = date.today()
    total_libros = db.query(func.count(Libro.id)).scalar() or 0
    total_ejemplares = db.query(func.sum(Libro.ejemplares)).scalar() or 0
    total_prestados = db.query(func.count(Prestamo.id)).filter(Prestamo.fecha_devolucion.is_(None)).scalar() or 0
    total_socios_activos = db.query(func.count(Socio.id)).filter(Socio.activo == True).scalar() or 0
    total_vencidos = db.query(func.count(Prestamo.id)).filter(Prestamo.fecha_devolucion.is_(None), Prestamo.fecha_limite < hoy).scalar() or 0
    total_multas = db.query(func.sum(Prestamo.multa)).filter(
        Prestamo.multa_pagada.is_(True)
    ).scalar() or 0.0

    return {
        "total_libros": total_libros,
        "total_ejemplares": int(total_ejemplares),
        "total_prestados": total_prestados,
        "total_socios_activos": total_socios_activos,
        "total_vencidos": total_vencidos,
        "total_multas_recaudadas": float(total_multas)
    }