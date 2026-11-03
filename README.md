# API segura de biblioteca

API REST modular con FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, contraseñas Argon2 y JWT.

## Requisitos

- Python 3.12 o superior
- Docker y Docker Compose

## Instalación local (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Edite `.env`: defina `POSTGRES_PASSWORD`, una `DATABASE_URL` que use esa contraseña
y genere `SECRET_KEY` sin guardarla en el repositorio:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Inicie PostgreSQL y aplique las migraciones:

```powershell
docker compose up -d db
alembic upgrade head
```

La aplicación nunca crea tablas al arrancar. Para iniciar la API:

```powershell
fastapi dev app/main.py
```

La documentación está en `/docs` (solo fuera de producción), la comprobación de
salud en `/api/v1/health` y todas las rutas de negocio tienen el prefijo `/api/v1`.

## Administrador inicial

Después de aplicar las migraciones, cree el primer administrador de forma
interactiva. El script solicita la contraseña con `getpass`; no la imprime ni la
guarda en el código:

```powershell
python -m app.scripts.crear_admin
```

El endpoint público de registro solo puede crear usuarios con rol `socio`.
Administradores pueden crear bibliotecarios y otros administradores desde
`POST /api/v1/usuarios`.

## Migraciones

Las migraciones versionadas están en `alembic/versions`. Cada cambio de esquema
debe tener su migración, revisarse antes de aplicarse y contar con un `downgrade`.

```powershell
alembic history
alembic current
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
alembic downgrade -1
alembic downgrade base
```

Las cinco migraciones incluidas crean el esquema inicial, añaden el estado de
pago de multas, usuarios, refresh tokens y auditoría de los préstamos. En un
entorno de desarrollo nuevo, ejecute `alembic upgrade head` antes de iniciar la API.

## Pruebas

```powershell
pytest --cov=app --cov-report=term-missing
```

Las pruebas usan `TEST_DATABASE_URL`; el valor de ejemplo apunta a SQLite y no
usa la base PostgreSQL de desarrollo.

## Roles y permisos

| Rol | Permisos |
|---|---|
| Anónimo | Registro, login, salud y consulta del catálogo |
| Socio | Perfil, préstamos y multas propios; catálogo |
| Bibliotecario | Catálogo, socios, préstamos, devoluciones, multas y reportes |
| Admin | Permisos del bibliotecario, borrados y gestión de usuarios/roles |

Un socio nunca puede consultar préstamos de otro socio. Los refresh tokens se
almacenan por identificador, rotan al renovarse y se revocan al cerrar sesión,
cambiar contraseña, cambiar rol o desactivar una cuenta.

## Conceptos de seguridad

- **Autenticación y autorización:** la autenticación confirma quién inició
  sesión. La autorización decide qué acciones permite su rol o propiedad. Un
  `401` significa que falta una credencial válida; un `403`, que el usuario
  autenticado no tiene permiso.
- **Hash de contraseñas:** Argon2 es deliberadamente costoso para dificultar
  ataques de diccionario. Incluye una sal aleatoria en el hash almacenado.
  MD5, SHA-1 y SHA-256 son demasiado rápidos para proteger contraseñas.
- **JWT:** contiene encabezado, claims y firma, codificados en Base64URL. Está
  firmado, no cifrado: no se deben incluir secretos en sus claims. `exp` limita
  su vigencia.
- **Access y refresh tokens:** el access token dura minutos para reducir el
  impacto de una filtración. El refresh token dura más tiempo, se almacena por
  `jti` y se rota en cada renovación; reutilizar uno revocado invalida las
  sesiones de refresh del usuario.
- **OAuth2 Password Flow de FastAPI:** `OAuth2PasswordRequestForm` recibe
  usuario/correo y contraseña como formulario; `OAuth2PasswordBearer` extrae
  el token Bearer y publica el flujo de autorización en OpenAPI.
- **Alembic:** `upgrade` aplica cambios y `downgrade` los revierte. La
  autogeneración compara metadatos y esquema, pero no deduce cambios de datos ni
  siempre reconoce renombres o reglas de negocio; cada revisión requiere
  inspección manual.
- **Rate limiting:** restringir intentos por IP dificulta ataques automatizados
  de fuerza bruta contra login y registro.
- **CORS:** es una política del navegador para solicitudes desde otros orígenes.
  La API permite los orígenes configurados en `CORS_ORIGINS`; producción no
  admite el comodín `*`.

## Endpoints principales

| Ruta | Anónimo | Socio | Bibliotecario | Admin |
|---|---:|---:|---:|---:|
| `POST /api/v1/auth/registro`, `/login`, `/refresh` | Sí | Sí | Sí | Sí |
| `GET /api/v1/health`, catálogo `GET /libros`, `/autores`, `/categorias` | Sí | Sí | Sí | Sí |
| `POST` / `PATCH` catálogo | No | No | Sí | Sí |
| `DELETE` catálogo | No | No | No | Sí |
| `/api/v1/auth/me`, `/logout`, `/me/password` | No | Sí | Sí | Sí |
| `/api/v1/socios/me*` | No | Propio | No | No |
| `GET` / `POST /api/v1/socios`, `GET` / `PATCH /socios/{id}` | No | No | Sí | Sí |
| `DELETE /api/v1/socios/{id}` | No | No | No | Sí |
| `GET /api/v1/prestamos*` | No | Propio | Sí | Sí |
| Crear/devolver/pagar préstamos | No | No | Sí | Sí |
| `GET /api/v1/reportes/*` | No | No | Sí | Sí |
| `/api/v1/usuarios*` | No | No | No | Sí |

Las respuestas de colecciones incluyen `items`, `total`, `skip` y `limit`.
Los errores 401 envían `WWW-Authenticate: Bearer`. El middleware agrega
`X-Request-ID` y registra método, ruta, código HTTP y duración sin guardar
contraseñas ni tokens.

## Entrega

Antes de publicar, completar los nombres de los integrantes y el nombre del
aprendiz en el repositorio. Los commits por fase y por migración se realizan en
el repositorio Git de entrega del equipo.

**Integrantes:** completar con nombres y apellidos del equipo.
