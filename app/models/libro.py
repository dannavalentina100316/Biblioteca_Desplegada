from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.categoria import libro_categoria


class Libro(Base):
    __tablename__ = "libros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    isbn: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    anio_publicacion: Mapped[int] = mapped_column(Integer, nullable=False)
    ejemplares: Mapped[int | None] = mapped_column(
        Integer, default=1, nullable=True
    )
    autor_id: Mapped[int] = mapped_column(
        ForeignKey("autores.id"), nullable=False
    )

    autor: Mapped["Autor"] = relationship("Autor", back_populates="libros")
    categorias: Mapped[list["Categoria"]] = relationship(
        "Categoria",
        secondary=libro_categoria,
        back_populates="libros",
    )
    prestamos: Mapped[list["Prestamo"]] = relationship(
        "Prestamo", back_populates="libro"
    )
