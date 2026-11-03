from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    CuentaBloqueada,
    Conflicto,
    NoAutenticado,
    NoEncontrado,
    Prohibido,
)
from app.core.security import (
    crear_token,
    hashear_password,
    leer_token,
    normalizar_utc,
    verificar_password,
    verificar_password_inexistente,
)
from app.models.refresh_token import RefreshToken
from app.models.socio import Socio
from app.models.usuario import RolUsuario, Usuario
from app.schemas.auth import CambioPassword, UsuarioRegistro


def registrar_usuario(db: Session, datos: UsuarioRegistro) -> Usuario:
    email = str(datos.email).lower()
    existente = db.query(Usuario).filter(func.lower(Usuario.email) == email).first()
    socio_existente = db.query(Socio).filter(func.lower(Socio.email) == email).first()
    if existente or socio_existente:
        raise Conflicto("El correo electrónico ya está registrado")

    socio = Socio(
        nombre=datos.nombre,
        email=email,
        telefono=datos.telefono,
        activo=True,
        fecha_alta=datetime.now(timezone.utc).date(),
    )
    try:
        db.add(socio)
        db.flush()
        usuario = Usuario(
            email=email,
            nombre=datos.nombre,
            password_hash=hashear_password(datos.password),
            rol=RolUsuario.socio,
            socio_id=socio.id,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario
    except IntegrityError as exc:
        db.rollback()
        raise Conflicto("El correo electrónico ya está registrado") from exc
    except Exception:
        db.rollback()
        raise


def iniciar_sesion(db: Session, email: str, password: str) -> dict:
    email_normalizado = email.strip().lower()
    usuario = (
        db.query(Usuario)
        .filter(func.lower(Usuario.email) == email_normalizado)
        .first()
    )
    if usuario is None:
        verificar_password_inexistente(password)
        raise NoAutenticado("Credenciales inválidas")

    ahora = datetime.now(timezone.utc)
    if usuario.bloqueado_hasta and normalizar_utc(usuario.bloqueado_hasta) > ahora:
        raise CuentaBloqueada()

    if not verificar_password(password, usuario.password_hash):
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= 5:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=15)
            db.commit()
            raise CuentaBloqueada()
        db.commit()
        raise NoAutenticado("Credenciales inválidas")

    if not usuario.activo:
        raise Prohibido("Usuario inactivo")

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    settings = get_settings()
    access_token, _, _ = crear_token(
        usuario,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token, jti, expira_en = crear_token(
        usuario,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(
        RefreshToken(
            jti=jti,
            usuario_id=usuario.id,
            expira_en=expira_en,
        )
    )
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


def renovar_tokens(db: Session, token: str) -> dict:
    payload = leer_token(token, "refresh")
    try:
        user_id = int(payload["sub"])
        jti = str(payload["jti"])
    except (KeyError, TypeError, ValueError) as exc:
        raise NoAutenticado("Token inválido o vencido") from exc

    registro = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if registro is None:
        raise NoAutenticado("Refresh token inválido o revocado")
    if registro.revocado:
        db.query(RefreshToken).filter(
            RefreshToken.usuario_id == registro.usuario_id
        ).update({RefreshToken.revocado: True}, synchronize_session=False)
        db.commit()
        raise NoAutenticado("Refresh token reutilizado; sesión revocada")

    ahora = datetime.now(timezone.utc)
    if normalizar_utc(registro.expira_en) <= ahora:
        registro.revocado = True
        db.commit()
        raise NoAutenticado("Refresh token vencido")

    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    if usuario is None:
        raise NoAutenticado("Token inválido o vencido")
    if not usuario.activo:
        raise Prohibido("Usuario inactivo")
    if registro.usuario_id != usuario.id:
        raise NoAutenticado("Refresh token inválido")

    registro.revocado = True
    settings = get_settings()
    access_token, _, _ = crear_token(
        usuario,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh_token, nuevo_jti, expira_en = crear_token(
        usuario,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(
        RefreshToken(
            jti=nuevo_jti,
            usuario_id=usuario.id,
            expira_en=expira_en,
        )
    )
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


def cerrar_sesion(db: Session, usuario: Usuario, token: str) -> None:
    payload = leer_token(token, "refresh")
    if str(payload.get("sub")) != str(usuario.id):
        raise NoAutenticado("El refresh token no pertenece al usuario")
    registro = (
        db.query(RefreshToken)
        .filter(RefreshToken.jti == payload.get("jti"))
        .first()
    )
    if registro is None:
        raise NoAutenticado("Refresh token inválido o revocado")
    registro.revocado = True
    db.commit()


def cambiar_password(
    db: Session,
    usuario: Usuario,
    datos: CambioPassword,
) -> None:
    if not verificar_password(datos.password_actual, usuario.password_hash):
        raise NoAutenticado("La contraseña actual es incorrecta")
    usuario.password_hash = hashear_password(datos.password_nueva)
    db.query(RefreshToken).filter(
        RefreshToken.usuario_id == usuario.id
    ).update({RefreshToken.revocado: True}, synchronize_session=False)
    db.commit()


def usuario_por_id(db: Session, usuario_id: int) -> Usuario:
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario is None:
        raise NoEncontrado("Usuario no encontrado")
    return usuario
