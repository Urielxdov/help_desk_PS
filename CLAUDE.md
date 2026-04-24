# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Instalar dependencias
pip install -r requirements.txt

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Servidor de desarrollo
python manage.py runserver

# Tests
pytest
pytest apps/helpdesks/tests/
pytest apps/helpdesks/tests/test_views.py::TestHelpDeskCreate

# Linting
ruff check .
ruff format .

# Docker (levanta PostgreSQL + web)
docker compose up
docker compose up db          # solo la base de datos
docker compose exec web python manage.py migrate
```

`DJANGO_SETTINGS_MODULE=config.settings` — único archivo de settings (no hay development/production separados, todo via `.env`).

## Autenticación

El sistema de usuarios es **externo**. El JWT llega en el header `Authorization: Bearer <token>` y se decodifica sin validar firma (`authentication.JWTAuthentication`). El payload debe contener `user_id` (int, nullable) y `role` (str, nullable).

**Endpoint de desarrollo** — `POST /api/auth/token/` acepta `{"user_id": 1, "role": "technician"}` y devuelve un JWT firmado con `SECRET_KEY`. Solo para pruebas locales; en producción el JWT lo genera el sistema externo.

**Roles válidos:** `user`, `technician`, `area_admin`, `super_admin`

### Atributos de rol en JWTUser

| Atributo | Descripción | Usado en |
|---|---|---|
| `real_role` | Rol original del JWT, nunca cambia | Clases de permiso (`IsAreaAdmin`, `IsSuperAdmin`, `IsTechnicianOrAdmin`) y checks de acceso inline en vistas |
| `active_role` | Override temporal; `None` si no hay override activo | Respuesta de `/api/auth/me/` y `/api/auth/switch-role/` |
| `role` | Rol efectivo: `active_role` si está activo, si no `real_role` | Filtrado de datos en `get_queryset` y visibilidad de comentarios |

### Override de rol (view-as)

Permite a usuarios con rol superior simular la vista de un rol menor **sin perder acceso a los endpoints**. El override viaja en el campo `active_role` del JWT.

**Flujo:**
1. Cliente tiene JWT externo con `role: "super_admin"`.
2. Llama `POST /api/auth/switch-role/` con `{"active_role": "technician"}`.
3. Recibe un JWT nuevo (firmado por este servicio) con `{role: "super_admin", active_role: "technician"}`.
4. Con ese JWT, las respuestas se filtran como las vería un `technician`; los permisos de endpoint siguen siendo de `super_admin`.
5. Para revertir: llama `POST /api/auth/switch-role/` con `{"active_role": null}` o vuelve a usar el JWT original.

**Regla de jerarquía:** `active_role` debe ser estrictamente menor al `role` real. Un token con `active_role >= role` es ignorado silenciosamente por `JWTAuthentication`.

## Arquitectura

```
config/          — settings.py, urls.py, wsgi.py, exceptions.py
apps/
  catalog/       — Department → ServiceCategory → Service
  helpdesks/     — HelpDesk, HDAttachment, HDComment
authentication.py       — JWTAuthentication + JWTUser + ROLE_LEVEL
authentication_urls.py  — POST /api/auth/token/ · POST /api/auth/switch-role/ · GET /api/auth/me/
```

### Dependencias entre apps
```
catalog    → sin dependencias internas
helpdesks  → catalog (FK a Service)
```

## Modelos clave

### HelpDesk (`apps/helpdesks/models.py`)
- **Folio:** `HD-000001` — autogenerado en `save()` a partir del PK; nunca se reinicia.
- **Estado:** `abierto → en_progreso → en_espera → resuelto → cerrado`. Transiciones validadas en la vista contra `VALID_TRANSITIONS`.
- `solicitante_id` / `responsable_id` — enteros del sistema externo, nullables.
- `tiempo_estimado` se hereda de `service.tiempo_estimado_default` si no se provee al crear.

### HDAttachment — storage intercambiable
`apps/helpdesks/storage.py` define la interfaz `FileStorage`. La implementación activa es `LocalFileStorage` (usa `default_storage` de Django). Para migrar a S3/Azure: crear nueva clase, cambiar `get_storage()`.

### Almacenamiento de archivos — rutas persistentes
El sistema soporta dos configuraciones via `.env`:

**Para Docker (recomendado):**
```env
ENVIRONMENT=docker
MEDIA_ROOT_DOCKER=/app/media
```
Los archivos se guardan en el volumen `media_data` definido en `docker-compose.yml`.

**Para servidor físico:**
```env
ENVIRONMENT=local
MEDIA_ROOT_LOCAL=/var/data/calidadpro/media
```
Asegúrate de que la carpeta existe y tiene permisos de escritura:
```bash
sudo mkdir -p /var/data/calidadpro/media
sudo chown -R www-data:www-data /var/data/calidadpro/media
```

## Endpoints

| Método | Ruta | Permiso |
|---|---|---|
| POST | `/api/auth/token/` | Público |
| POST | `/api/auth/switch-role/` | auth |
| GET | `/api/auth/me/` | auth |
| GET/POST | `/api/departments/` | GET: auth / POST: super_admin |
| GET | `/api/departments/{id}/categories/` | auth |
| POST/PUT | `/api/service-categories/` | area_admin |
| GET | `/api/service-categories/{id}/services/` | auth |
| POST/PUT | `/api/services/` | area_admin |
| PATCH | `/api/services/{id}/toggle/` | area_admin |
| GET/POST | `/api/helpdesks/` | auth |
| GET | `/api/helpdesks/{id}/` | auth |
| PATCH | `/api/helpdesks/{id}/status/` | technician+ |
| PATCH | `/api/helpdesks/{id}/assign/` | area_admin+ |
| PATCH | `/api/helpdesks/{id}/resolve/` | technician+ |
| POST | `/api/helpdesks/{id}/attachments/` | auth |
| DELETE | `/api/helpdesks/{id}/attachments/{aid}/` | auth |
| GET/POST | `/api/helpdesks/{id}/comments/` | auth |

**Filtrado de visibilidad en `/api/helpdesks/`:**
- `user` → solo sus HDs (`solicitante_id`)
- `technician` → solo los asignados a él (`responsable_id`)
- `area_admin` / `super_admin` → todos

**Comentarios internos:** `es_interno=True` no los ve el rol `user`.

## Respuestas de error

Formato uniforme via `config/exceptions.py`:
```json
{"error": "descripción", "code": "NombreExcepción"}
```
