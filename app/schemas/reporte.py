from pydantic import BaseModel
from typing import Optional

class ReporteLibroMasPrestado(BaseModel):
    titulo_libro: str
    nombre_autor: str
    total_prestamos: int

class ReporteCategoria(BaseModel):
    nombre_categoria: str
    total_libros: int

class ReportePrestamoVencido(BaseModel):
    prestamo_id: int
    titulo_libro: str
    nombre_socio: str
    email_socio: str
    fecha_limite: str
    dias_retraso: int

class ReporteSocioMulta(BaseModel):
    nombre_socio: str
    email_socio: str
    total_multas: float
    prestamos_con_multa: int

class ReporteAutor(BaseModel):
    nombre_autor: str
    total_libros: int
    total_ejemplares: int
    total_prestamos: int

class ReporteResumen(BaseModel):
    total_libros: int
    total_ejemplares: int
    total_prestados: int
    total_socios_activos: int
    total_vencidos: int
    total_multas_recaudadas: float