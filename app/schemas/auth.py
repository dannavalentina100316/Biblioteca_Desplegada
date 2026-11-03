import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.usuario import RolUsuario


class UsuarioRegistro(BaseModel):
    email: EmailStr = Field(max_length=100)
    nombre: str = Field(min_length=3, max_length=100)
    telefono: str | None = Field(default=None, pattern=r"^[0-9\s\+]{7,15}$")
    password: str = Field(min_length=8, max_length=64)
    confirmar_password: str = Field(min_length=8, max_length=64)

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
    def validar_complejidad(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("La contraseña debe incluir una mayúscula")
        if not re.search(r"[a-z]", value):
            raise ValueError("La contraseña debe incluir una minúscula")
        if not re.search(r"\d", value):
            raise ValueError("La contraseña debe incluir un número")
        return value

    @model_validator(mode="after")
    def passwords_coinciden(self):
        if self.password != self.confirmar_password:
            raise ValueError("Las contraseñas no coinciden")
        return self


class UsuarioRespuesta(BaseModel):
    id: int
    email: EmailStr
    nombre: str
    rol: RolUsuario
    activo: bool
    socio_id: int | None
    creado_en: datetime

    model_config = {"from_attributes": True}


class TokenRespuesta(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenEntrada(BaseModel):
    refresh_token: str


class CambioPassword(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=64)

    @field_validator("password_nueva")
    @classmethod
    def validar_complejidad(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("La contraseña debe incluir una mayúscula")
        if not re.search(r"[a-z]", value):
            raise ValueError("La contraseña debe incluir una minúscula")
        if not re.search(r"\d", value):
            raise ValueError("La contraseña debe incluir un número")
        return value
