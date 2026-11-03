from __future__ import annotations

from enum import Enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RolUsuario(str, Enum):
    admin = "admin"
    bibliotecario = "bibliotecario"
    socio = "socio"


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (UniqueConstraint("socio_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True, index=True
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        SqlEnum(RolUsuario, name="rolusuario"),
        nullable=False,
        default=RolUsuario.socio,
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    intentos_fallidos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    socio_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("socios.id", ondelete="CASCADE"),
        nullable=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    socio: Mapped["Socio | None"] = relationship(
        "Socio", back_populates="usuario"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    prestamos_registrados: Mapped[list["Prestamo"]] = relationship(
        "Prestamo", back_populates="registrado_por"
    )
