from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Socio(Base):
    __tablename__ = "socios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    activo: Mapped[bool | None] = mapped_column(
        Boolean, default=True, nullable=True
    )
    fecha_alta: Mapped[date | None] = mapped_column(Date, nullable=True)

    prestamos: Mapped[list["Prestamo"]] = relationship(
        "Prestamo", back_populates="socio"
    )
    usuario: Mapped["Usuario | None"] = relationship(
        "Usuario", back_populates="socio", uselist=False
    )
