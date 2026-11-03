from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.controllers import auth as auth_controller
from app.core.dependencies import CurrentUser, get_db
from app.core.limiter import limiter
from app.models.usuario import Usuario
from app.routes.common import ERROR_RESPONSES
from app.schemas.auth import (
    CambioPassword,
    RefreshTokenEntrada,
    TokenRespuesta,
    UsuarioRegistro,
    UsuarioRespuesta,
)

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"],
    responses=ERROR_RESPONSES,
)


@router.post(
    "/registro",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un socio",
    responses={409: {"description": "Correo ya registrado"}},
)
@limiter.limit("5/minute")
def registrar(
    request: Request,
    datos: UsuarioRegistro,
    db: Annotated[Session, Depends(get_db)],
):
    return auth_controller.registrar_usuario(db, datos)


@router.post(
    "/login",
    response_model=TokenRespuesta,
    summary="Iniciar sesión",
    responses={423: {"description": "Cuenta bloqueada"}},
)
@limiter.limit("10/minute")
def login(
    request: Request,
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    return auth_controller.iniciar_sesion(
        db, formulario.username, formulario.password
    )


@router.post(
    "/refresh",
    response_model=TokenRespuesta,
    summary="Rotar los tokens de acceso",
)
def refresh(
    datos: RefreshTokenEntrada,
    db: Annotated[Session, Depends(get_db)],
):
    return auth_controller.renovar_tokens(db, datos.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión y revocar el refresh token",
)
def logout(
    datos: RefreshTokenEntrada,
    db: Annotated[Session, Depends(get_db)],
    usuario: CurrentUser,
) -> Response:
    auth_controller.cerrar_sesion(db, usuario, datos.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UsuarioRespuesta,
    summary="Consultar el usuario autenticado",
)
def me(usuario: CurrentUser):
    return usuario


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar la contraseña y revocar sesiones",
)
def actualizar_password(
    datos: CambioPassword,
    db: Annotated[Session, Depends(get_db)],
    usuario: CurrentUser,
) -> Response:
    auth_controller.cambiar_password(db, usuario, datos)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
