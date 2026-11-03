from pydantic import BaseModel, ConfigDict, Field


class SocioActualizarPropio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    telefono: str | None = Field(default=None, pattern=r"^[0-9\s\+]{7,15}$")
