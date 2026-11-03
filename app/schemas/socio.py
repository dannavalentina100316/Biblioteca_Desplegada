from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator
from typing import Optional
from datetime import datetime

class SocioBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    telefono: Optional[str] = Field(None, pattern=r"^[0-9\s\+]{7,15}$")
    activo: Optional[bool] = True

    @field_validator('nombre')
    def limpiar_nombre(cls, v: str) -> str:
        return " ".join(v.strip().split()).title()

    @field_validator('email')
    def email_minusculas(cls, v: str) -> str:
        return v.strip().lower()

class SocioCreate(SocioBase):
    pass

class SocioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = Field(None, pattern=r"^[0-9\s\+]{7,15}$")
    activo: Optional[bool] = None

    @field_validator('nombre')
    def limpiar_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return " ".join(v.strip().split()).title()
        return v

    @field_validator('email')
    def email_minusculas(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip().lower()
        return v

class SocioResponse(SocioBase):
    id: int
    fecha_alta: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)