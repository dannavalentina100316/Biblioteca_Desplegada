import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.core.config import get_settings
from app.core.exceptions import ErrorAplicacion
from app.core.limiter import limiter
from app.routes.auth import router as auth_router
from app.routes.autores import router as autores_router
from app.routes.categorias import router as categorias_router
from app.routes.health import router as health_router
from app.routes.libros import router as libros_router
from app.routes.prestamos import router as prestamos_router
from app.routes.reportes import router as reportes_router
from app.routes.socios import router as socios_router
from app.routes.usuarios import router as usuarios_router
from app.models.autor import Autor
from app.models.categoria import Categoria
from app.models.libro import Libro
from app.models.prestamo import Prestamo
from app.models.refresh_token import RefreshToken
from app.models.socio import Socio
from app.models.usuario import Usuario

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
settings = get_settings()
logger = logging.getLogger("biblioteca.api")

app = FastAPI(
    title="API Segura de Biblioteca",
    version="3.0.0",
    description="API de biblioteca con autenticación, roles y migraciones Alembic.",
    docs_url=None if settings.environment == "prod" else "/docs",
    redoc_url=None if settings.environment == "prod" else "/redoc",
    openapi_url=None if settings.environment == "prod" else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def agregar_request_id(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    inicio = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duracion_ms = (perf_counter() - inicio) * 1000
        logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            status_code,
            duracion_ms,
        )


@app.exception_handler(ErrorAplicacion)
async def manejar_error_aplicacion(
    request: Request,
    exc: ErrorAplicacion,
):
    headers = {}
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    headers["X-Request-ID"] = getattr(request.state, "request_id", str(uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )


@app.exception_handler(Exception)
async def manejar_error_interno(
    request: Request,
    exc: Exception,
):
    logger.exception("Error interno de la solicitud %s", request.url.path)
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
        headers={"X-Request-ID": request_id},
    )


for router in (
    auth_router,
    autores_router,
    categorias_router,
    libros_router,
    socios_router,
    prestamos_router,
    reportes_router,
    usuarios_router,
    health_router,
):
    app.include_router(router, prefix="/api/v1")
