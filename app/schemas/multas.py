from pydantic import BaseModel

from app.schemas.pagina import Pagina
from app.schemas.prestamo import PrestamoResponse


class MultasSocioRespuesta(BaseModel):
    items: list[PrestamoResponse]
    total: int
    skip: int
    limit: int
    total_multa: float
