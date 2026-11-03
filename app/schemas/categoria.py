from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional

class CategoriaBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=200)

    @field_validator('nombre')
    def limpiar_y_minusculas(cls, v: str) -> str:
        return " ".join(v.strip().split()).lower()

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=3, max_length=50)
    descripcion: Optional[str] = Field(None, max_length=200)

    @field_validator('nombre')
    def limpiar_y_minusculas(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return " ".join(v.strip().split()).lower()
        return v

class CategoriaResponse(CategoriaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)