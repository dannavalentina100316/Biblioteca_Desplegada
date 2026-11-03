from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Autor(Base):
    __tablename__ = "autores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    nacionalidad: Mapped[str | None] = mapped_column(String(60), nullable=True)
    anio_naci: Mapped[int | None] = mapped_column(Integer, nullable=True)

    libros: Mapped[list["Libro"]] = relationship("Libro", back_populates="autor")
