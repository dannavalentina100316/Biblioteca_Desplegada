from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional

class AutorBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    nacionalidad: Optional[str] = Field(None, max_length=60)
    anio_naci: Optional[int] = Field(None, ge=1000, le=2026)

    @field_validator('nombre')
    def limpiar_nombre(cls, v: str) -> str:
        return " ".join(v.strip().split()).title()

class AutorCreate(AutorBase):
    pass

class AutorUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    nacionalidad: Optional[str] = Field(None, max_length=60)
    anio_naci: Optional[int] = Field(None, ge=1000, le=2026)

    @field_validator('nombre')
    def limpiar_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return " ".join(v.strip().split()).title()
        return v

class AutorResponse(AutorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)