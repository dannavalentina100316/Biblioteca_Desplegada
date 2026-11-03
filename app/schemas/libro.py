from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from app.schemas.autor import AutorResponse
from app.schemas.categoria import CategoriaResponse

class LibroBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=150)
    isbn: str = Field(..., pattern=r"^\d{13}$", description="Debe ser exactamente de 13 dígitos")
    anio_publicacion: int = Field(..., ge=1450, le=2026)
    ejemplares: int = Field(..., ge=1, le=50)
    autor_id: int

    @field_validator('titulo')
    def limpiar_titulo(cls, v: str) -> str:
        return " ".join(v.strip().split()).title()

class LibroCreate(LibroBase):
    categoria_ids: List[int] = Field(..., min_length=1, max_length=5)

    @field_validator('categoria_ids')
    def validar_categorias_unicas(cls, v: List[int]) -> List[int]:
        if len(v) != len(set(v)):
            raise ValueError("No se permiten categorías repetidas")
        return v

class LibroUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=150)
    isbn: Optional[str] = Field(None, pattern=r"^\d{13}$")
    anio_publicacion: Optional[int] = Field(None, ge=1450, le=2026)
    ejemplares: Optional[int] = Field(None, ge=1, le=50)
    autor_id: Optional[int] = None
    categoria_ids: Optional[List[int]] = Field(None, min_length=1, max_length=5)

    @field_validator('titulo')
    def limpiar_titulo(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return " ".join(v.strip().split()).title()
        return v

    @field_validator('categoria_ids')
    def validar_categorias_unicas(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None and len(v) != len(set(v)):
            raise ValueError("No se permiten categorías repetidas")
        return v

class LibroResponse(LibroBase):
    id: int
    disponibles: int
    autor: AutorResponse
    categorias: List[CategoriaResponse] = []

    model_config = ConfigDict(from_attributes=True)