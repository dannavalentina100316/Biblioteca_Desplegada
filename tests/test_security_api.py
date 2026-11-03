from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.core.security import hashear_password, verificar_password
from app.core.config import Settings
from app.core.limiter import limiter
from app.models.usuario import RolUsuario, Usuario
from app.routes import health as health_route
from app.routes import libros as libros_route
from app.scripts import crear_admin


PASSWORD = "Biblioteca123"


def register(client, email, nombre):
    return client.post(
        "/api/v1/auth/registro",
        json={
            "email": email,
            "nombre": nombre,
            "telefono": "3001234567",
            "password": PASSWORD,
            "confirmar_password": PASSWORD,
        },
    )


def admin_login(client, db):
    admin = Usuario(
        email="admin@biblioteca.com",
        nombre="Admin Biblioteca",
        password_hash=hashear_password(PASSWORD),
        rol=RolUsuario.admin,
    )
    db.add(admin)
    db.commit()
    return client.post(
        "/api/v1/auth/login",
        data={"username": admin.email, "password": PASSWORD},
    ).json()["access_token"]


def create_librarian(client, admin_token):
    response = client.post(
        "/api/v1/usuarios",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "biblio@biblioteca.com",
            "nombre": "Bibliotecario",
            "password": PASSWORD,
            "rol": "bibliotecario",
        },
    )
    assert response.status_code == 201
    return client.post(
        "/api/v1/auth/login",
        data={"username": "biblio@biblioteca.com", "password": PASSWORD},
    ).json()["access_token"]


def create_book(client, librarian_token, isbn="9781234567890"):
    headers = {"Authorization": f"Bearer {librarian_token}"}
    author = client.post(
        "/api/v1/autores",
        headers=headers,
        json={"nombre": "Autora de Prueba", "nacionalidad": "Colombia"},
    ).json()
    category = client.post(
        "/api/v1/categorias",
        headers=headers,
        json={"nombre": "Pruebas"},
    ).json()
    response = client.post(
        "/api/v1/libros",
        headers=headers,
        json={
            "titulo": "Libro de Prueba",
            "isbn": isbn,
            "anio_publicacion": 2020,
            "ejemplares": 3,
            "autor_id": author["id"],
            "categoria_ids": [category["id"]],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health_catalog_and_request_id(client):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "database": "ok"}
    assert health.headers["x-request-id"]

    catalog = client.get("/api/v1/libros")
    assert catalog.status_code == 200
    assert catalog.json() == {
        "items": [],
        "total": 0,
        "skip": 0,
        "limit": 10,
    }


def test_registration_validation_hash_and_response(client, db):
    weak_password = client.post(
        "/api/v1/auth/registro",
        json={
            "email": "weak@example.com",
            "nombre": "Socio de Prueba",
            "password": "abcdefgh",
            "confirmar_password": "abcdefgh",
        },
    )
    assert weak_password.status_code == 422

    mismatched = client.post(
        "/api/v1/auth/registro",
        json={
            "email": "mismatch@example.com",
            "nombre": "Socio de Prueba",
            "password": PASSWORD,
            "confirmar_password": "Another123",
        },
    )
    assert mismatched.status_code == 422

    created = register(client, "ana@example.com", "ana torres")
    assert created.status_code == 201
    assert created.json()["rol"] == "socio"
    assert created.json()["socio_id"]
    assert "password_hash" not in created.json()

    user = db.query(Usuario).filter_by(email="ana@example.com").one()
    assert user.password_hash != PASSWORD
    assert verificar_password(PASSWORD, user.password_hash)
    duplicate = register(client, "ANA@EXAMPLE.COM", "Ana Torres")
    assert duplicate.status_code == 409


def test_login_tokens_401_header_and_refresh_rotation(client):
    assert register(client, "ana@example.com", "Ana Torres").status_code == 201
    unauthorized = client.get("/api/v1/auth/me")
    assert unauthorized.status_code == 401
    assert unauthorized.headers["www-authenticate"] == "Bearer"

    invalid_password = client.post(
        "/api/v1/auth/login",
        data={"username": "ana@example.com", "password": "WrongPass123"},
    )
    missing_user = client.post(
        "/api/v1/auth/login",
        data={"username": "missing@example.com", "password": "WrongPass123"},
    )
    assert invalid_password.status_code == missing_user.status_code == 401
    assert invalid_password.json() == missing_user.json()

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "ana@example.com", "password": PASSWORD},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 900
    assert "password_hash" not in client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    ).json()

    refresh_as_access = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert refresh_as_access.status_code == 401

    rotated = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert rotated.status_code == 200
    replay = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert replay.status_code == 401
    revoked = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated.json()["refresh_token"]},
    )
    assert revoked.status_code == 401


def test_role_ownership_and_staff_attribution(client, db):
    admin_token = admin_login(client, db)
    librarian_token = create_librarian(client, admin_token)
    ana = register(client, "ana@example.com", "Ana Torres").json()
    luis = register(client, "luis@example.com", "Luis Perez").json()
    book = create_book(client, librarian_token)
    staff_headers = {"Authorization": f"Bearer {librarian_token}"}

    loan_a = client.post(
        "/api/v1/prestamos",
        headers=staff_headers,
        json={"libro_id": book["id"], "socio_id": ana["socio_id"], "dias": 14},
    )
    loan_b = client.post(
        "/api/v1/prestamos",
        headers=staff_headers,
        json={"libro_id": book["id"], "socio_id": luis["socio_id"], "dias": 14},
    )
    assert loan_a.status_code == loan_b.status_code == 201
    assert loan_a.json()["registrado_por_id"]

    ana_token = client.post(
        "/api/v1/auth/login",
        data={"username": "ana@example.com", "password": PASSWORD},
    ).json()["access_token"]
    ana_headers = {"Authorization": f"Bearer {ana_token}"}
    own = client.get("/api/v1/prestamos?socio_id=999", headers=ana_headers)
    assert own.status_code == 200
    assert own.json()["total"] == 1
    assert own.json()["items"][0]["socio_id"] == ana["socio_id"]
    foreign = client.get(
        f"/api/v1/prestamos/{loan_b.json()['id']}",
        headers=ana_headers,
    )
    assert foreign.status_code == 404

    forbidden_write = client.post(
        "/api/v1/libros",
        headers=ana_headers,
        json={},
    )
    assert forbidden_write.status_code == 403
    forbidden_delete = client.delete(
        f"/api/v1/libros/{book['id']}",
        headers=staff_headers,
    )
    assert forbidden_delete.status_code == 403
    forbidden_profile = client.patch(
        "/api/v1/socios/me",
        headers=ana_headers,
        json={"activo": False},
    )
    assert forbidden_profile.status_code == 422


def test_lockout_admin_guard_and_disabled_user(client, db):
    admin_token = admin_login(client, db)
    assert register(client, "luis@example.com", "Luis Perez").status_code == 201

    for attempt in range(5):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "luis@example.com", "password": "WrongPass123"},
        )
    assert response.status_code == 423
    correct_password = client.post(
        "/api/v1/auth/login",
        data={"username": "luis@example.com", "password": PASSWORD},
    )
    assert correct_password.status_code == 423

    self_role_change = client.patch(
        "/api/v1/usuarios/1/rol",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"rol": "socio"},
    )
    assert self_role_change.status_code == 422

    luis_id = client.get(
        "/api/v1/usuarios?activo=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    ).json()["items"][1]["id"]
    luis_login = client.post(
        "/api/v1/auth/login",
        data={"username": "luis@example.com", "password": PASSWORD},
    )
    assert luis_login.status_code == 423

    db.query(Usuario).filter(Usuario.email == "luis@example.com").update(
        {Usuario.intentos_fallidos: 0, Usuario.bloqueado_hasta: None}
    )
    db.commit()
    luis_login = client.post(
        "/api/v1/auth/login",
        data={"username": "luis@example.com", "password": PASSWORD},
    )
    assert luis_login.status_code == 200
    response = client.patch(
        f"/api/v1/usuarios/{luis_id}/activo",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"activo": False},
    )
    assert response.status_code == 200
    inactive = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {luis_login.json()['access_token']}"
        },
    )
    assert inactive.status_code == 403
    assert inactive.json()["detail"] == "Usuario inactivo"


def test_unpaid_fine_blocks_new_loan_until_paid(client, db):
    admin_token = admin_login(client, db)
    librarian_token = create_librarian(client, admin_token)
    ana = register(client, "ana@example.com", "Ana Torres").json()
    book = create_book(client, librarian_token)
    headers = {"Authorization": f"Bearer {librarian_token}"}
    old_date = date.today() - timedelta(days=20)

    loan = client.post(
        "/api/v1/prestamos",
        headers=headers,
        json={
            "libro_id": book["id"],
            "socio_id": ana["socio_id"],
            "fecha_prestamo": old_date.isoformat(),
            "dias": 7,
        },
    )
    assert loan.status_code == 201
    returned = client.post(
        f"/api/v1/prestamos/{loan.json()['id']}/devolucion",
        headers=headers,
        json={"fecha_devolucion": date.today().isoformat()},
    )
    assert returned.status_code == 200
    assert returned.json()["multa"] == 6.5
    assert returned.json()["multa_pagada"] is False

    blocked = client.post(
        "/api/v1/prestamos",
        headers=headers,
        json={"libro_id": book["id"], "socio_id": ana["socio_id"]},
    )
    assert blocked.status_code == 422
    assert blocked.json()["detail"] == "El socio tiene multas pendientes"

    paid = client.post(
        f"/api/v1/prestamos/{loan.json()['id']}/pago-multa",
        headers=headers,
    )
    assert paid.status_code == 200
    assert paid.json()["multa_pagada"] is True
    duplicate_payment = client.post(
        f"/api/v1/prestamos/{loan.json()['id']}/pago-multa",
        headers=headers,
    )
    assert duplicate_payment.status_code == 409

    new_loan = client.post(
        "/api/v1/prestamos",
        headers=headers,
        json={"libro_id": book["id"], "socio_id": ana["socio_id"]},
    )
    assert new_loan.status_code == 201


def test_password_change_revokes_refresh_and_catalog_total(client):
    assert register(client, "ana@example.com", "Ana Torres").status_code == 201
    tokens = client.post(
        "/api/v1/auth/login",
        data={"username": "ana@example.com", "password": PASSWORD},
    ).json()
    changed = client.patch(
        "/api/v1/auth/me/password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"password_actual": PASSWORD, "password_nueva": "ChangedPass123"},
    )
    assert changed.status_code == 204
    assert client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    ).status_code == 401
    assert client.get("/api/v1/libros?skip=1&limit=5").json()["total"] == 0


def test_login_rate_limit_and_logout(client):
    responses = [
        client.post(
            "/api/v1/auth/login",
            data={
                "username": "not-found@example.com",
                "password": "WrongPass123",
            },
        )
        for _ in range(11)
    ]
    assert [response.status_code for response in responses[:10]] == [401] * 10
    assert responses[10].status_code == 429

    limiter.reset()
    assert register(client, "ana@example.com", "Ana Torres").status_code == 201
    tokens = client.post(
        "/api/v1/auth/login",
        data={"username": "ana@example.com", "password": PASSWORD},
    ).json()
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout.status_code == 204
    assert client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    ).status_code == 401


def test_profile_reports_and_admin_user_management(client, db):
    admin_token = admin_login(client, db)
    librarian_token = create_librarian(client, admin_token)
    ana = register(client, "ana@example.com", "Ana Torres").json()
    ana_token = client.post(
        "/api/v1/auth/login",
        data={"username": "ana@example.com", "password": PASSWORD},
    ).json()["access_token"]
    ana_headers = {"Authorization": f"Bearer {ana_token}"}

    profile = client.get("/api/v1/socios/me", headers=ana_headers)
    assert profile.status_code == 200
    assert profile.json()["id"] == ana["socio_id"]
    updated = client.patch(
        "/api/v1/socios/me",
        headers=ana_headers,
        json={"nombre": "Ana Torres Actualizada"},
    )
    assert updated.status_code == 200
    assert updated.json()["nombre"] == "Ana Torres Actualizada"
    fines = client.get("/api/v1/socios/me/multas", headers=ana_headers)
    assert fines.json()["total_multa"] == 0

    forbidden_report = client.get(
        "/api/v1/reportes/resumen", headers=ana_headers
    )
    assert forbidden_report.status_code == 403
    report = client.get(
        "/api/v1/reportes/resumen",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert report.status_code == 200
    for path in (
        "/api/v1/reportes/libros-mas-prestados",
        "/api/v1/reportes/categorias",
        "/api/v1/reportes/prestamos-vencidos",
        "/api/v1/reportes/socios-con-multas",
        "/api/v1/reportes/autores",
    ):
        listing = client.get(
            path,
            headers={"Authorization": f"Bearer {librarian_token}"},
        )
        assert listing.status_code == 200
        assert listing.json()["total"] == 0

    created_admin = client.post(
        "/api/v1/usuarios",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "admin2@biblioteca.com",
            "nombre": "Segundo Admin",
            "password": PASSWORD,
            "rol": "admin",
        },
    )
    assert created_admin.status_code == 201
    second_login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin2@biblioteca.com", "password": PASSWORD},
    ).json()
    orphan_socio_role = client.patch(
        f"/api/v1/usuarios/{created_admin.json()['id']}/rol",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"rol": "socio"},
    )
    assert orphan_socio_role.status_code == 422
    role_change = client.patch(
        f"/api/v1/usuarios/{created_admin.json()['id']}/rol",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"rol": "bibliotecario"},
    )
    assert role_change.status_code == 200
    assert client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_login["refresh_token"]},
    ).status_code == 401


def test_production_cors_must_not_allow_wildcard():
    with pytest.raises(ValueError):
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            secret_key="test-key-not-for-production-at-least-32-characters",
            environment="prod",
            cors_origins=["*"],
        )


def test_registration_rate_limit(client):
    results = [
        register(client, f"rate{index}@example.com", f"Socio {index}")
        for index in range(6)
    ]
    assert [response.status_code for response in results[:5]] == [201] * 5
    assert results[5].status_code == 429


def test_health_and_internal_errors_are_sanitized(monkeypatch):
    def database_unavailable():
        raise OperationalError("SELECT 1", {}, RuntimeError("private db detail"))

    monkeypatch.setattr(
        health_route,
        "engine",
        type("UnavailableEngine", (), {"connect": staticmethod(database_unavailable)})(),
    )
    client = TestClient(app, raise_server_exceptions=False)
    unavailable = client.get("/api/v1/health")
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"] == "Base de datos no disponible"

    def fail_catalog(*args, **kwargs):
        raise RuntimeError("private application detail")

    monkeypatch.setattr(libros_route.libro_controller, "get_libros", fail_catalog)
    internal_error = client.get("/api/v1/libros")
    assert internal_error.status_code == 500
    assert internal_error.json() == {
        "detail": "Error interno del servidor"
    }
    assert "private" not in internal_error.text
    assert internal_error.headers["x-request-id"]


def test_admin_creation_script_hashes_password_and_is_idempotent(
    monkeypatch, db
):
    answers = iter(["root@example.com", "Root Admin"])
    passwords = iter(["RootPass123", "RootPass123"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(
        crear_admin.getpass, "getpass", lambda _prompt: next(passwords)
    )
    crear_admin.main()
    user = db.query(Usuario).filter_by(email="root@example.com").one()
    assert user.rol == RolUsuario.admin
    assert user.password_hash != "RootPass123"

    answers = iter(["root@example.com", "Ignored Name"])
    passwords = iter(["RootPass123", "RootPass123"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(
        crear_admin.getpass, "getpass", lambda _prompt: next(passwords)
    )
    crear_admin.main()
    assert db.query(Usuario).filter_by(email="root@example.com").count() == 1
