# Help Desk — Estructura del proyecto Django DDD

## Visión general

Monorepo Django organizado por dominios (DDD ligero). Un solo proyecto, dominios aislados que se comunican únicamente por eventos. Multi-tenant con `django-tenants` usando schema de PostgreSQL por organización.

**Regla de dependencia entre dominios:**
- `tenants` no depende de nadie
- `users` depende de `tenants`
- `tickets` depende de `users`
- `assignments` depende de `tickets` y `users`
- Comunicación entre dominios: solo por eventos (`shared/events.py`)
- Nunca importar modelos de un dominio en otro directamente

---

## Árbol de carpetas

```
helpdesk/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
│
├── shared/
│   ├── models.py
│   ├── permissions.py
│   ├── exceptions.py
│   ├── middleware.py
│   ├── events.py
│   ├── responses.py
│   ├── pagination.py
│   ├── utils.py
│   └── mixins.py
│
├── domains/
│   ├── tenants/
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── repository.py
│   │   ├── urls.py
│   │   ├── api/
│   │   │   ├── views.py
│   │   │   └── serializers.py
│   │   └── tests/
│   │       ├── test_models.py
│   │       ├── test_services.py
│   │       └── test_api.py
│   │
│   ├── users/
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── repository.py
│   │   ├── urls.py
│   │   ├── api/
│   │   │   ├── views.py
│   │   │   └── serializers.py
│   │   └── tests/
│   │       ├── test_models.py
│   │       ├── test_services.py
│   │       └── test_api.py
│   │
│   ├── tickets/
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── repository.py
│   │   ├── events.py
│   │   ├── urls.py
│   │   ├── api/
│   │   │   ├── views.py
│   │   │   └── serializers.py
│   │   └── tests/
│   │       ├── test_models.py
│   │       ├── test_services.py
│   │       └── test_api.py
│   │
│   └── assignments/
│       ├── models.py
│       ├── services.py
│       ├── repository.py
│       ├── urls.py
│       ├── api/
│       │   ├── views.py
│       │   └── serializers.py
│       └── tests/
│           ├── test_models.py
│           ├── test_services.py
│           └── test_api.py
│
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Capa `shared/` — detalle de responsabilidades

La regla de oro: algo va en `shared` **solo si lo usan 2 o más dominios** y no pertenece a ninguno en particular.

### `shared/models.py` — modelos abstractos base

| Clase | Hereda de | Agrega |
|---|---|---|
| `BaseModel` | `models.Model` | `id` (UUID), `created_at`, `updated_at` |
| `SoftDeleteModel` | `BaseModel` | `is_active`, `deleted_at`, método `soft_delete()` |
| `TenantAwareModel` | `SoftDeleteModel` | Base para modelos dentro del schema de tenant |
| `AuditModel` | `TenantAwareModel` | `created_by`, `updated_by` (FK a `users.User`) |

Todos son `abstract = True`. Nunca se migran directamente.

### `shared/permissions.py` — permisos por rol

| Clase | Condición |
|---|---|
| `IsTenantMember` | Usuario autenticado y request tiene tenant |
| `IsTenantAdmin` | `role == 'admin'` |
| `IsHDManager` | `role in ('admin', 'hd_manager')` |
| `IsAgent` | `role in ('admin', 'hd_manager', 'agent')` |

### `shared/exceptions.py` — errores de dominio

| Clase | HTTP | Uso |
|---|---|---|
| `DomainException` | 400 | Base para todos los errores de negocio |
| `NotFoundError` | 404 | Recurso no encontrado |
| `ForbiddenError` | 403 | Sin permisos suficientes |
| `ConflictError` | 409 | Conflicto con estado actual |
| `ValidationError` | 422 | Datos inválidos de dominio |

Registrar en `settings.py`:
```python
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'shared.exceptions.custom_exception_handler'
}
```

### `shared/middleware.py` — resolución de tenant

Inyecta `request.tenant` en cada request. Resuelve el tenant por:
- **Subdominio:** `empresa.tuapp.com`
- **Header HTTP:** `X-Tenant-ID`

### `shared/events.py` — contrato de eventos entre dominios

`DomainEvent` es la clase base con `event_type`, `payload`, `tenant_id`, `occurred_at`, `event_id`.

`publish_event(event)` despacha hoy vía Django signal. En Fase 2 se reemplaza por Celery o un message broker sin tocar ningún dominio.

### `shared/responses.py` — formato de respuesta unificado

```
Éxito:  { "data": {...}, "message": "OK" }
Error:  { "error": "...", "code": "NotFoundError" }
```

### `shared/mixins.py` — mixins para ViewSets

| Mixin | Qué hace |
|---|---|
| `TenantFilterMixin` | Filtra automáticamente el QuerySet por `request.tenant` |
| `AuditMixin` | Asigna `created_by` / `updated_by` desde `request.user` |

### `shared/pagination.py`

`TenantPageNumberPagination` — paginación estándar con `page_size` configurable por tenant.

---

## Dominios — responsabilidad de cada archivo

### Patrón uniforme en todos los dominios

```
models.py       → solo definición de entidades y relaciones
repository.py   → solo acceso a datos (queries, filtros)
services.py     → lógica de negocio, usa el repository
events.py       → definición de eventos propios del dominio (si aplica)
api/views.py    → solo HTTP: valida, delega al service, responde
api/serializers.py → serialización/deserialización de datos
urls.py         → rutas del dominio
tests/          → pruebas por capa
```

### `domains/tenants/`

**Modelos:** `Tenant`, `TenantDomain`, `TenantConfig`

**Responsabilidad:** registro y configuración de organizaciones. Vive en el schema **público** de PostgreSQL.

**Endpoints:**
```
POST   /api/v1/tenants/              crear organización
GET    /api/v1/tenants/{id}/         detalle
PATCH  /api/v1/tenants/{id}/         actualizar configuración
GET    /api/v1/tenants/{id}/stats/   métricas generales
```

---

### `domains/users/`

**Modelos:** `User`, `Role`, `Position`, `Department`

**Responsabilidad:** gestión de usuarios, roles y estructura organizacional dentro de cada tenant. Vive en el schema **por tenant**.

**Endpoints:**
```
POST   /api/v1/auth/login/
POST   /api/v1/auth/refresh/
POST   /api/v1/auth/logout/

GET    /api/v1/users/
POST   /api/v1/users/
GET    /api/v1/users/{id}/
PATCH  /api/v1/users/{id}/
DELETE /api/v1/users/{id}/          soft delete
GET    /api/v1/users/{id}/workload/ carga actual del agente

GET    /api/v1/departments/
POST   /api/v1/departments/
PATCH  /api/v1/departments/{id}/
GET    /api/v1/departments/{id}/agents/
```

---

### `domains/tickets/`

**Modelos:** `Ticket`, `TicketStatus`, `TicketHistory`, `Comment`, `Attachment`

**Responsabilidad:** ciclo de vida completo de un ticket. Es el dominio central del sistema.

**Eventos que publica:**
- `ticket.created`
- `ticket.status_changed`
- `ticket.deadline_set`
- `ticket.closed`

**Endpoints:**
```
GET    /api/v1/tickets/                    listar (filtros: status, dept, agente, fecha)
POST   /api/v1/tickets/                    crear ticket
GET    /api/v1/tickets/{id}/
PATCH  /api/v1/tickets/{id}/
DELETE /api/v1/tickets/{id}/               solo admin

POST   /api/v1/tickets/{id}/comments/
GET    /api/v1/tickets/{id}/comments/
POST   /api/v1/tickets/{id}/attachments/

PATCH  /api/v1/tickets/{id}/status/        cambio de estado (workflow)
PATCH  /api/v1/tickets/{id}/deadline/      solo HD Manager
GET    /api/v1/tickets/{id}/history/       historial de cambios
```

**Estados del ticket:**
```
OPEN → IN_PROGRESS → PENDING_USER → RESOLVED → CLOSED
                  ↘ ESCALATED ↗
```

---

### `domains/assignments/`

**Modelos:** `Assignment`, `WorkloadSnapshot`

**Responsabilidad:** asignación automática por menor carga y balance entre agentes. Escucha eventos de `tickets`.

**Lógica de balance:**
```python
# Selecciona el agente con menos tickets abiertos en el departamento
agent = Agent.objects
    .filter(department=dept, is_active=True)
    .annotate(open_tickets=Count('assignments', filter=Q(status='open')))
    .order_by('open_tickets')
    .first()
```

**Endpoints:**
```
POST   /api/v1/assignments/auto/          asignación automática al crear ticket
POST   /api/v1/assignments/manual/        asignación manual por HD Manager
PATCH  /api/v1/assignments/{id}/reassign/ reasignar ticket
GET    /api/v1/assignments/workload/      dashboard de carga por agente y departamento
```

---

## Base de datos — schema por tenant

### Schema `public` (compartido entre todas las organizaciones)

```
tenants_tenant
tenants_domain
tenants_config
```

### Schema `{tenant_slug}` (aislado por organización)

```
users_user
users_role
users_position
users_department
tickets_ticket
tickets_ticketstatus
tickets_tickethistory
tickets_comment
tickets_attachment
assignments_assignment
assignments_workloadsnapshot
```

---

## Endpoints — resumen completo `/api/v1/`

| Método | Endpoint | Dominio | Permiso mínimo |
|---|---|---|---|
| POST | `/auth/login/` | users | Público |
| POST | `/auth/refresh/` | users | Público |
| GET/POST | `/tenants/` | tenants | SuperAdmin |
| GET/PATCH | `/tenants/{id}/` | tenants | TenantAdmin |
| GET/POST | `/users/` | users | TenantAdmin |
| GET/PATCH/DELETE | `/users/{id}/` | users | TenantAdmin |
| GET | `/users/{id}/workload/` | users | HDManager |
| GET/POST | `/departments/` | users | TenantAdmin |
| GET | `/departments/{id}/agents/` | users | HDManager |
| GET/POST | `/tickets/` | tickets | Agent |
| GET/PATCH | `/tickets/{id}/` | tickets | Agent |
| PATCH | `/tickets/{id}/status/` | tickets | Agent |
| PATCH | `/tickets/{id}/deadline/` | tickets | HDManager |
| GET | `/tickets/{id}/history/` | tickets | Agent |
| POST | `/tickets/{id}/comments/` | tickets | Agent |
| POST | `/tickets/{id}/attachments/` | tickets | Agent |
| POST | `/assignments/auto/` | assignments | Sistema (signal) |
| POST | `/assignments/manual/` | assignments | HDManager |
| PATCH | `/assignments/{id}/reassign/` | assignments | HDManager |
| GET | `/assignments/workload/` | assignments | HDManager |

---

## Lo que NO va en `shared/`

| Qué | Dónde va |
|---|---|
| Lógica de balance de carga | `assignments/services.py` |
| Modelo `Ticket` | `tickets/models.py` |
| Serializers de usuario | `users/api/serializers.py` |
| Tareas Celery de un dominio | En ese dominio |
| Cualquier cosa que use solo un dominio | En ese dominio |

> Si en la semana 6 sigues agregando cosas a `shared/`, hay un problema en la separación de dominios.

---

## Dependencias principales (`requirements/base.txt`)

```
django>=4.2
djangorestframework>=3.15
django-tenants>=3.5
djangorestframework-simplejwt>=5.3
celery>=5.3
redis>=5.0
psycopg2-binary>=2.9
django-filter>=23.0
gunicorn>=21.0
```

---

*Generado como referencia de arquitectura — Fase 1 MVP Help Desk*
