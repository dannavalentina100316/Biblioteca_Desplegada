from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Prestamo(Base):
    __tablename__ = "prestamos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    libro_id: Mapped[int] = mapped_column(
        ForeignKey("libros.id"), nullable=False
    )
    socio_id: Mapped[int] = mapped_column(
        ForeignKey("socios.id"), nullable=False
    )
    fecha_prestamo: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_limite: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_devolucion: Mapped[date | None] = mapped_column(Date, nullable=True)
    multa: Mapped[float | None] = mapped_column(
        Float, default=0.0, nullable=True
    )
    multa_pagada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    registrado_por_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    libro: Mapped["Libro"] = relationship("Libro", back_populates="prestamos")
    socio: Mapped["Socio"] = relationship("Socio", back_populates="prestamos")
    registrado_por: Mapped["Usuario | None"] = relationship(
        "Usuario", back_populates="prestamos_registrados"
    )
