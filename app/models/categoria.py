from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

libro_categoria = Table(
    "libro_categoria",
    Base.metadata,
    Column("libro_id", Integer, ForeignKey("libros.id"), primary_key=True),
    Column("categoria_id", Integer, ForeignKey("categorias.id"), primary_key=True),
)


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(200), nullable=True)

    libros: Mapped[list["Libro"]] = relationship(
        "Libro",
        secondary=libro_categoria,
        back_populates="categorias",
    )
