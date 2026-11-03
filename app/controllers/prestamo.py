from sqlalchemy.orm import Session, selectinload
from typing import Optional
from datetime import date, timedelta

from app.models.prestamo import Prestamo
from app.models.libro import Libro
from app.models.socio import Socio
from app.schemas.prestamo import PrestamoCreate, DevolucionCreate
from app.core.exceptions import NoEncontrado, Conflicto, ReglaNegocio
from app.controllers.libro import enriq_libro


def get_prestamos(
    db: Session,
    skip: int,
    limit: int,
    estado: Optional[str] = None,
    socio_id: Optional[int] = None,
    libro_id: Optional[int] = None,
):
    query = db.query(Prestamo).options(
        selectinload(Prestamo.libro).selectinload(Libro.autor),
        selectinload(Prestamo.libro).selectinload(Libro.categorias),
        selectinload(Prestamo.socio)
    )

    if socio_id:
        query = query.filter(Prestamo.socio_id == socio_id)

    if libro_id:
        query = query.filter(Prestamo.libro_id == libro_id)

    if estado == "activo":
        query = query.filter(
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_limite >= date.today()
        )
    elif estado == "vencido":
        query = query.filter(
            Prestamo.fecha_devolucion.is_(None),
            Prestamo.fecha_limite < date.today()
        )
    elif estado == "devuelto":
        query = query.filter(
            Prestamo.fecha_devolucion.is_not(None)
        )

    total = query.order_by(None).count()
    prestamos = query.offset(skip).limit(limit).all()
    for p in prestamos:
        if p.libro:
            enriq_libro(db, p.libro)
    return {
        "items": prestamos,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


def get_prestamo_by_id(
    db: Session, prestamo_id: int, socio_id: int | None = None
):
    query = db.query(Prestamo).options(
        selectinload(Prestamo.libro).selectinload(Libro.autor),
        selectinload(Prestamo.libro).selectinload(Libro.categorias),
        selectinload(Prestamo.socio)
    ).filter(Prestamo.id == prestamo_id)
    if socio_id is not None:
        query = query.filter(Prestamo.socio_id == socio_id)
    prestamo = query.first()

    if not prestamo:
        raise NoEncontrado("Préstamo no encontrado")

    if prestamo.libro:
        enriq_libro(db, prestamo.libro)

    return prestamo


def create_prestamo(
    db: Session,
    p_in: PrestamoCreate,
    registrado_por_id: int | None = None,
):
    # R1: El socio existe
    socio = db.query(Socio).filter(
        Socio.id == p_in.socio_id
    ).first()

    if not socio:
        raise NoEncontrado("El socio especificado no existe")

    # R2: El libro existe
    libro = db.query(Libro).filter(
        Libro.id == p_in.libro_id
    ).first()

    if not libro:
        raise NoEncontrado("El libro especificado no existe")

    # R3: El socio está activo
    if not socio.activo:
        raise ReglaNegocio("El socio no está activo")

    multas_pendientes = db.query(Prestamo).filter(
        Prestamo.socio_id == p_in.socio_id,
        Prestamo.multa > 0,
        Prestamo.multa_pagada.is_(False),
    ).count()
    if multas_pendientes:
        raise ReglaNegocio("El socio tiene multas pendientes")

    # Fecha del préstamo
    f_prestamo = (
        p_in.fecha_prestamo
        if p_in.fecha_prestamo
        else date.today()
    )

    if f_prestamo > date.today():
        raise ReglaNegocio(
            "La fecha de préstamo no puede ser futura"
        )

    # R4: El socio no tiene préstamos vencidos
    vencidos = db.query(Prestamo).filter(
        Prestamo.socio_id == p_in.socio_id,
        Prestamo.fecha_devolucion.is_(None),
        Prestamo.fecha_limite < date.today()
    ).count()

    if vencidos > 0:
        raise ReglaNegocio(
            "El socio tiene préstamos vencidos"
        )

    # R5: El socio tiene menos de 3 préstamos sin devolver
    activos_socio = db.query(Prestamo).filter(
        Prestamo.socio_id == p_in.socio_id,
        Prestamo.fecha_devolucion.is_(None)
    ).count()

    if activos_socio >= 3:
        raise ReglaNegocio("Máximo de 3 préstamos")

    # R6: El socio no tiene ese mismo libro sin devolver
    mismo_libro = db.query(Prestamo).filter(
        Prestamo.socio_id == p_in.socio_id,
        Prestamo.libro_id == p_in.libro_id,
        Prestamo.fecha_devolucion.is_(None)
    ).first()

    if mismo_libro:
        raise Conflicto(
            "El socio ya tiene este libro sin devolver"
        )

    # R7: El libro tiene ejemplares disponibles
    prestados_activos_libro = db.query(Prestamo).filter(
        Prestamo.libro_id == p_in.libro_id,
        Prestamo.fecha_devolucion.is_(None)
    ).count()

    disponibles = libro.ejemplares - prestados_activos_libro

    if disponibles <= 0:
        raise ReglaNegocio("No hay ejemplares disponibles")

    # R8: La fecha límite se calcula según los días solicitados
    dias = p_in.dias if p_in.dias else 14
    f_limite = f_prestamo + timedelta(days=dias)

    nuevo_prestamo = Prestamo(
        libro_id=p_in.libro_id,
        socio_id=p_in.socio_id,
        fecha_prestamo=f_prestamo,
        fecha_limite=f_limite,
        multa=0.0,
        multa_pagada=True,
        registrado_por_id=registrado_por_id,
    )

    db.add(nuevo_prestamo)
    db.commit()
    db.refresh(nuevo_prestamo)

    # Cargar relaciones antes de retornar
    db.refresh(nuevo_prestamo)
    if nuevo_prestamo.libro:
        enriq_libro(db, nuevo_prestamo.libro)

    return nuevo_prestamo


def registrar_devolucion(
    db: Session,
    prestamo_id: int,
    dev_in: DevolucionCreate
):
    prestamo = db.query(Prestamo).filter(
        Prestamo.id == prestamo_id
    ).first()

    if not prestamo:
        raise NoEncontrado("Préstamo no encontrado")

    # R9: El préstamo no fue devuelto antes
    if prestamo.fecha_devolucion is not None:
        raise Conflicto(
            "El préstamo ya fue devuelto anteriormente"
        )

    f_dev = (
        dev_in.fecha_devolucion
        if dev_in.fecha_devolucion
        else date.today()
    )

    if f_dev < prestamo.fecha_prestamo:
        raise ReglaNegocio(
            "La fecha de devolución no puede ser anterior "
            "a la fecha de préstamo"
        )

    prestamo.fecha_devolucion = f_dev

    # R10: Multa de 0,50 por cada día de retraso
    if f_dev > prestamo.fecha_limite:
        dias_retraso = (
            f_dev - prestamo.fecha_limite
        ).days
        prestamo.multa = float(dias_retraso * 0.50)
    else:
        prestamo.multa = 0.0
    prestamo.multa_pagada = prestamo.multa == 0

    db.commit()
    db.refresh(prestamo)

    if prestamo.libro:
        enriq_libro(db, prestamo.libro)

    return prestamo


def pagar_multa(db: Session, prestamo_id: int):
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    if prestamo is None:
        raise NoEncontrado("Préstamo no encontrado")
    if prestamo.multa <= 0 or prestamo.multa_pagada:
        raise Conflicto("El préstamo no tiene una multa pendiente")
    prestamo.multa_pagada = True
    db.commit()
    db.refresh(prestamo)
    if prestamo.libro:
        enriq_libro(db, prestamo.libro)
    return prestamo