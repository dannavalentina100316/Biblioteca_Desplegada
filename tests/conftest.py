import os
import tempfile
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

_database_file = Path(tempfile.gettempdir()) / f"biblioteca-{uuid.uuid4().hex}.db"
_database_url = f"sqlite+pysqlite:///{_database_file.as_posix()}"
os.environ.update(
    {
        "DATABASE_URL": _database_url,
        "TEST_DATABASE_URL": _database_url,
        "SECRET_KEY": "test-key-not-for-production-at-least-32-characters",
        "ENVIRONMENT": "test",
        "CORS_ORIGINS": '["http://localhost:5173"]',
    }
)

from app.core.database import SessionLocal, engine
from app.core.limiter import limiter
from app.main import app
from app.models.prestamo import Prestamo
from app.models.refresh_token import RefreshToken
from app.models.socio import Socio
from app.models.usuario import Usuario
from app.models.libro import Libro
from app.models.categoria import Categoria
from app.models.autor import Autor


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    yield
    command.downgrade(config, "base")
    engine.dispose()
    _database_file.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def clean_tables(migrated_database):
    with SessionLocal() as db:
        db.query(RefreshToken).delete()
        db.query(Prestamo).delete()
        db.execute(text("DELETE FROM libro_categoria"))
        db.query(Libro).delete()
        db.query(Usuario).delete()
        db.query(Socio).delete()
        db.query(Categoria).delete()
        db.query(Autor).delete()
        db.commit()
    limiter.reset()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
