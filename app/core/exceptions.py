from fastapi import HTTPException, status

class ErrorAplicacion(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class NoEncontrado(ErrorAplicacion):
    def __init__(self, detail: str = "El recurso no existe"):
        super().__init__(status_code=404, detail=detail)

class Conflicto(ErrorAplicacion):
    def __init__(self, detail: str = "Conflicto con los datos existentes"):
        super().__init__(status_code=409, detail=detail)

class ReglaNegocio(ErrorAplicacion):
    def __init__(self, detail: str = "Una regla de la biblioteca no se cumple"):
        super().__init__(status_code=422, detail=detail)

class NoAutenticado(ErrorAplicacion):
    def __init__(self, detail: str = "No autenticado"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class Prohibido(ErrorAplicacion):
    def __init__(self, detail: str = "No tiene permisos para esta acción"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class CuentaBloqueada(ErrorAplicacion):
    def __init__(self, detail: str = "Cuenta bloqueada temporalmente"):
        super().__init__(status_code=423, detail=detail)