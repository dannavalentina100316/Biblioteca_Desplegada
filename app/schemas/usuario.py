import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.usuario import RolUsuario


class UsuarioCrear(BaseModel):
    email: EmailStr = Field(max_length=150)
    nombre: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=64)
    rol: RolUsuario

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("nombre")
    @classmethod
    def normalizar_nombre(cls, value: str) -> str:
        return " ".join(value.strip().split()).title()

    @field_validator("password")
    @classmethod
    def validar_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(r"\d", value):
            raise ValueError("La contraseña debe incluir mayúscula, minúscula y número")
        return value


class UsuarioRolActualizar(BaseModel):
    rol: RolUsuario


class UsuarioActivoActualizar(BaseModel):
    activo: bool
