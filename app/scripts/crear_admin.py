import getpass
import re
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func

from app.core.database import SessionLocal
from app.core.security import hashear_password
from app.models.usuario import RolUsuario, Usuario


def main() -> None:
    email_input = input("Correo del administrador: ").strip()
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email_input)).lower()
    except ValidationError:
        print("El correo electrónico no es válido.", file=sys.stderr)
        raise SystemExit(1)
    nombre = input("Nombre del administrador: ").strip()
    password = getpass.getpass("Contraseña: ")
    confirmacion = getpass.getpass("Confirmar contraseña: ")

    if password != confirmacion:
        print("Las contraseñas no coinciden.", file=sys.stderr)
        raise SystemExit(1)
    if (
        not 8 <= len(password) <= 64
        or not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"\d", password)
    ):
        print(
            "La contraseña debe tener entre 8 y 64 caracteres e incluir "
            "mayúscula, minúscula y número.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not 3 <= len(nombre) <= 100:
        print("El nombre debe tener entre 3 y 100 caracteres.", file=sys.stderr)
        raise SystemExit(1)

    db = SessionLocal()
    try:
        existing = db.query(Usuario).filter(
            func.lower(Usuario.email) == email
        ).first()
        if existing:
            print("Ya existe un usuario con ese correo; no se realizaron cambios.")
            return
        usuario = Usuario(
            email=email,
            nombre=" ".join(nombre.split()).title(),
            password_hash=hashear_password(password),
            rol=RolUsuario.admin,
        )
        db.add(usuario)
        db.commit()
        print(f"Administrador creado: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
