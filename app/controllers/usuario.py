from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import Conflicto, NoEncontrado, ReglaNegocio
from app.core.security import hashear_password
from app.models.refresh_token import RefreshToken
from app.models.usuario import RolUsuario, Usuario
from app.schemas.usuario import UsuarioCrear


def listar_usuarios(
    db: Session,
    skip: int,
    limit: int,
    rol: RolUsuario | None = None,
    activo: bool | None = None,
) -> dict:
    consulta = db.query(Usuario)
    if rol is not None:
        consulta = consulta.filter(Usuario.rol == rol)
    if activo is not None:
        consulta = consulta.filter(Usuario.activo == activo)
    total = consulta.order_by(None).count()
    return {
        "items": consulta.order_by(Usuario.id).offset(skip).limit(limit).all(),
        "total": total,
        "skip": skip,
        "limit": limit,
    }


def crear_usuario(db: Session, datos: UsuarioCrear) -> Usuario:
    if datos.rol == RolUsuario.socio:
        raise ReglaNegocio("Los usuarios socio se crean mediante el registro público")
    email = str(datos.email).lower()
    if db.query(Usuario).filter(func.lower(Usuario.email) == email).first():
        raise Conflicto("El correo electrónico ya está registrado")
    usuario = Usuario(
        email=email,
        nombre=datos.nombre,
        password_hash=hashear_password(datos.password),
        rol=datos.rol,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def _revocar_refresh(db: Session, usuario_id: int) -> None:
    db.query(RefreshToken).filter(
        RefreshToken.usuario_id == usuario_id
    ).update({RefreshToken.revocado: True}, synchronize_session=False)


def actualizar_rol(
    db: Session,
    usuario_id: int,
    nuevo_rol: RolUsuario,
    actor: Usuario,
) -> Usuario:
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario is None:
        raise NoEncontrado("Usuario no encontrado")
    if nuevo_rol == RolUsuario.socio and usuario.socio_id is None:
        raise ReglaNegocio("El usuario no tiene un socio vinculado")
    if usuario.id == actor.id and usuario.rol != nuevo_rol:
        raise ReglaNegocio("No puede cambiar su propio rol")
    if (
        usuario.activo
        and usuario.rol == RolUsuario.admin
        and nuevo_rol != RolUsuario.admin
    ):
        admins_activos = db.query(Usuario).filter(
            Usuario.rol == RolUsuario.admin,
            Usuario.activo.is_(True),
        ).count()
        if admins_activos <= 1:
            raise ReglaNegocio("Debe existir al menos un administrador activo")
    usuario.rol = nuevo_rol
    _revocar_refresh(db, usuario.id)
    db.commit()
    db.refresh(usuario)
    return usuario


def actualizar_estado(
    db: Session,
    usuario_id: int,
    activo: bool,
    actor: Usuario,
) -> Usuario:
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario is None:
        raise NoEncontrado("Usuario no encontrado")
    if usuario.id == actor.id and not activo:
        raise ReglaNegocio("No puede desactivar su propia cuenta")
    if (
        usuario.activo
        and usuario.rol == RolUsuario.admin
        and not activo
    ):
        admins_activos = db.query(Usuario).filter(
            Usuario.rol == RolUsuario.admin,
            Usuario.activo.is_(True),
        ).count()
        if admins_activos <= 1:
            raise ReglaNegocio("Debe existir al menos un administrador activo")
    usuario.activo = activo
    _revocar_refresh(db, usuario.id)
    db.commit()
    db.refresh(usuario)
    return usuario
