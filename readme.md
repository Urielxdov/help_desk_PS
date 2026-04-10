# Help Desk — Arquitectura y Plan de Ejecución

> Sistema de gestión de tickets con captura de datos orientada a la automatización futura.

---

## Visión general

Proyecto Django organizado por dominios (DDD ligero). El objetivo de la Fase 1 es operar el ciclo de vida completo de un ticket con la mínima complejidad posible, mientras se acumulan datos de calidad para entrenar flujos automáticos en fases posteriores.

**Decisiones de alcance:**
- Sin multi-tenancy en Fase 1. Un solo tenant configurado en `settings.py`
- Sin asignación automática. La asignación es manual por parte del HD Manager
- Sin integración con LLM externo en Fase 1. El clasificador de tickets se prepara como estructura, pero opera con reglas simples basadas en palabras clave
- El dominio `analytics` captura datos desde el primer ticket de `help_desk`, listos para entrenar un modelo real en Fase 2

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
│   └── mixins.py
│
├── domains/
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
│   ├── help_desk/
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── repository.py
│   │   ├── classifier.py        ← reglas simples hoy, LLM en Fase 2
│   │   ├── events.py
│   │   ├── urls.py
│   │   ├── api/
│   │   │   ├── views.py
│   │   │   └── serializers.py
│   │   └── tests/
│   │       ├── test_models.py
│   │       ├── test_services.py
│   │       ├── test_classifier.py
│   │       └── test_api.py
│   │
│   └── analytics/
│       ├── models.py
│       ├── services.py
│       ├── repository.py
│       ├── urls.py
│       ├── api/
│       │   ├── views.py
│       │   └── serializers.py
│       └── tests/
│           ├── test_models.py
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

## Capa `shared/` — responsabilidades

Regla: algo va en `shared` **solo si lo usan 2 o más dominios**.

### `shared/models.py` — modelos abstractos base

| Clase | Hereda de | Agrega |
|---|---|---|
| `BaseModel` | `models.Model` | `id` (UUID), `created_at`, `updated_at` |
| `SoftDeleteModel` | `BaseModel` | `is_active`, `deleted_at`, `soft_delete()` |
| `AuditModel` | `SoftDeleteModel` | `created_by`, `updated_by` (FK a `users.User`) |

Todos son `abstract = True`.

### `shared/permissions.py`

| Clase | Condición |
|---|---|
| `IsAuthenticated` | Usuario autenticado |
| `IsAdmin` | `role == 'admin'` |
| `IsHDManager` | `role in ('admin', 'hd_manager')` |
| `IsAgent` | `role in ('admin', 'hd_manager', 'agent')` |

### `shared/exceptions.py`

| Clase | HTTP | Uso |
|---|---|---|
| `DomainException` | 400 | Base para errores de negocio |
| `NotFoundError` | 404 | Recurso no encontrado |
| `ForbiddenError` | 403 | Sin permisos |
| `ConflictError` | 409 | Conflicto de estado |
| `ValidationError` | 422 | Datos inválidos |

### `shared/events.py`

`DomainEvent` con `event_type`, `payload`, `occurred_at`, `event_id`. Despacha hoy vía Django signals. En Fase 2 se reemplaza por Celery sin tocar los dominios.

### `shared/responses.py`

```
Éxito:  { "data": {...}, "message": "OK" }
Error:  { "error": "...", "code": "NotFoundError" }
```

---

## Dominios

### Patrón uniforme

```
models.py           → definición de entidades
repository.py       → acceso a datos
services.py         → lógica de negocio
api/views.py        → HTTP: valida, delega al service, responde
api/serializers.py  → serialización
urls.py             → rutas
tests/              → pruebas por capa
```

---

### `domains/users/`

**Modelos:** `User` con campo `role` (admin, hd_manager, agent)

**Responsabilidad:** autenticación y gestión básica de usuarios. Sin departamentos ni posiciones en Fase 1.

**Endpoints:**
```
POST   /api/v1/auth/login/
POST   /api/v1/auth/refresh/
POST   /api/v1/auth/logout/

GET    /api/v1/users/
POST   /api/v1/users/
GET    /api/v1/users/{id}/
PATCH  /api/v1/users/{id}/
DELETE /api/v1/users/{id}/      soft delete
```

---

### `domains/help_desk/`

**Modelos:** `HelpDeskTicket`, `HelpDeskStatus`, `HelpDeskHistory`, `Comment`, `Attachment`

**Responsabilidad:** ciclo de vida completo del ticket. Es el dominio central.

**`classifier.py`** — módulo independiente dentro del dominio:

```python
# Fase 1: reglas basadas en palabras clave
# Fase 2: se reemplaza el método classify() con llamada a LLM
# La interfaz no cambia, solo la implementación interna

class HelpDeskClassifier:
    def classify(self, subject: str, description: str) -> ClassificationResult:
        # Devuelve: category, priority, confidence
        ...
```

Al crear un ticket, el clasificador sugiere categoría y prioridad. El agente acepta o corrige. La corrección se persiste en `analytics.HelpDeskSnapshot` como dato de entrenamiento.

**Eventos que publica:**
- `help_desk.ticket_created`
- `help_desk.status_changed`
- `help_desk.deadline_set`
- `help_desk.ticket_closed`

**Estados del ticket:**
```
OPEN → IN_PROGRESS → PENDING_USER → RESOLVED → CLOSED
                  ↘ ESCALATED ↗
```

**Endpoints:**
```
GET    /api/v1/help-desk/
POST   /api/v1/help-desk/
GET    /api/v1/help-desk/{id}/
PATCH  /api/v1/help-desk/{id}/
DELETE /api/v1/help-desk/{id}/               solo admin

POST   /api/v1/help-desk/{id}/comments/
GET    /api/v1/help-desk/{id}/comments/
POST   /api/v1/help-desk/{id}/attachments/

PATCH  /api/v1/help-desk/{id}/status/
PATCH  /api/v1/help-desk/{id}/deadline/      solo HD Manager
PATCH  /api/v1/help-desk/{id}/assign/        asignación manual
GET    /api/v1/help-desk/{id}/history/
```

---

### `domains/analytics/`

**Modelos:** `HelpDeskSnapshot`

**Responsabilidad:** capturar el estado completo de un ticket en cada evento relevante. Solo escribe, nunca modifica datos operativos. Es la fuente de verdad para entrenamiento futuro.

```python
class HelpDeskSnapshot(BaseModel):
    ticket_id            = UUIDField()
    event_type           = CharField()   # created, status_changed, commented, resolved
    time_in_state        = DurationField()
    agent_id             = UUIDField(null=True)
    priority             = CharField()
    category             = CharField()
    comment_count        = IntegerField()
    resolution_time      = DurationField(null=True)
    was_escalated        = BooleanField()

    # Datos del clasificador — clave para el entrenamiento
    suggested_category   = CharField(null=True)
    suggested_priority   = CharField(null=True)
    accepted_category    = CharField(null=True)    # lo que eligió el agente
    accepted_priority    = CharField(null=True)
    suggestion_accepted  = BooleanField(null=True)
    classifier_confidence = FloatField(null=True)

    snapshot_data        = JSONField()             # estado completo serializado
```

**Endpoints:**
```
GET    /api/v1/analytics/snapshots/     HD Manager
GET    /api/v1/analytics/export/        HD Manager — CSV/JSON para entrenamiento
```

---

## Endpoints — resumen completo

| Método | Endpoint | Permiso mínimo |
|---|---|---|
| POST | `/auth/login/` | Público |
| POST | `/auth/refresh/` | Público |
| POST | `/auth/logout/` | Autenticado |
| GET/POST | `/users/` | Admin |
| GET/PATCH/DELETE | `/users/{id}/` | Admin |
| GET/POST | `/help-desk/` | Agent |
| GET/PATCH | `/help-desk/{id}/` | Agent |
| PATCH | `/help-desk/{id}/status/` | Agent |
| PATCH | `/help-desk/{id}/assign/` | HDManager |
| PATCH | `/help-desk/{id}/deadline/` | HDManager |
| POST | `/help-desk/{id}/comments/` | Agent |
| POST | `/help-desk/{id}/attachments/` | Agent |
| GET | `/help-desk/{id}/history/` | Agent |
| GET | `/analytics/snapshots/` | HDManager |
| GET | `/analytics/export/` | HDManager |

---

## Base de datos

```
users_user
help_desk_ticket
help_desk_status
help_desk_history
help_desk_comment
help_desk_attachment
analytics_help_desk_snapshot
```

---

## Dependencias (`requirements/base.txt`)

```
django>=4.2
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
psycopg2-binary>=2.9
django-filter>=23.0
gunicorn>=21.0
redis>=5.0
celery>=5.3          # preparado para Fase 2, no se usa aún
```

---

## Plan de ejecución — Fase 1 MVP

El plan está dividido en 4 semanas. Cada semana produce algo funcional y testeable.

---

### Semana 1 — Fundación

**Objetivo:** proyecto corriendo, base de datos conectada, un endpoint respondiendo.

**Tareas:**

1. Inicializar proyecto Django con estructura de carpetas definitiva
2. Configurar `settings/base.py`, `development.py`, `production.py`
3. Configurar PostgreSQL con Docker Compose
4. Implementar `shared/models.py` — modelos abstractos base
5. Implementar `shared/exceptions.py` y registrar el `custom_exception_handler`
6. Implementar `shared/responses.py`
7. Implementar `shared/permissions.py`
8. Implementar `shared/events.py` — estructura base con Django signals
9. Crear dominio `users/`: modelo `User`, serializers, auth con SimpleJWT
10. Endpoints de auth: `login`, `refresh`, `logout`
11. Endpoints CRUD de usuarios con permisos por rol
12. Tests de `users/`: modelos, servicios, API

**Entregable de la semana:** autenticación funcionando, usuarios CRUD, tests en verde.

---

### Semana 2 — Dominio help_desk

**Objetivo:** crear y gestionar tickets con su ciclo de vida completo.

**Tareas:**

1. Modelos: `HelpDeskTicket`, `HelpDeskStatus`, `HelpDeskHistory`
2. Implementar `help_desk/repository.py` — queries con filtros por status, agente, fecha
3. Implementar `help_desk/services.py` — crear ticket, cambiar estado, validar transiciones
4. Implementar la máquina de estados con validación de transiciones permitidas
5. Endpoint `POST /help-desk/` — crear ticket
6. Endpoints de listado con filtros (`django-filter`)
7. Endpoint `PATCH /help-desk/{id}/status/` con historial automático en `HelpDeskHistory`
8. Endpoint `PATCH /help-desk/{id}/assign/` — asignación manual
9. Endpoint `PATCH /help-desk/{id}/deadline/` — solo HD Manager
10. Modelos `Comment` y `Attachment`
11. Endpoints de comentarios y adjuntos
12. Endpoint `GET /help-desk/{id}/history/`
13. Tests de `help_desk/`: modelos, servicios (especialmente transiciones de estado), API

**Entregable de la semana:** flujo completo de un ticket desde creación hasta cierre, testeado.

---

### Semana 3 — Clasificador y Analytics

**Objetivo:** captura de datos desde el primer ticket real.

**Tareas:**

1. Implementar `help_desk/classifier.py` con `HelpDeskClassifier` basado en palabras clave
   - Categorías iniciales configurables en `settings.py`
   - Devuelve `suggested_category`, `suggested_priority`, `confidence`
2. Integrar el clasificador en `POST /help-desk/` — sugerencia antes de guardar
3. El serializer de creación expone la sugerencia al cliente
4. El agente puede aceptar o corregir en la misma llamada
5. Tests de `test_classifier.py` — casos por categoría
6. Modelo `analytics/HelpDeskSnapshot`
7. `analytics/services.py` — `create_snapshot(ticket, event_type)`
8. Conectar `create_snapshot` a los eventos de `help_desk/events.py` vía Django signals
9. Validar que cada cambio de estado genera un snapshot
10. Endpoint `GET /analytics/snapshots/` con filtros básicos
11. Endpoint `GET /analytics/export/` — responde CSV o JSON según query param `?format=csv`
12. Tests de analytics: creación de snapshots, integridad de datos, export

**Entregable de la semana:** cada ticket crea snapshots automáticamente. El export muestra datos listos para analizar.

---

### Semana 4 — Estabilización y cierre de MVP

**Objetivo:** sistema confiable, documentado y desplegable.

**Tareas:**

1. Revisar cobertura de tests — mínimo 80% en dominios `help_desk` y `analytics`
2. Revisar que ningún dominio importa modelos de otro directamente
3. Configurar paginación en todos los listados (`shared/pagination.py`)
4. Agregar `django-filter` en `help_desk` con filtros: status, agente asignado, fecha de creación, prioridad
5. Configurar `settings/production.py` — variables de entorno, ALLOWED_HOSTS, CORS
6. Dockerfile y `docker-compose.yml` funcionales para producción
7. Documentar variables de entorno en `.env.example`
8. Smoke test manual del flujo completo: crear usuario → crear ticket → clasificar → cambiar estado → exportar analytics
9. Revisar y limpiar respuestas de error — que todos usen el formato de `shared/responses.py`
10. Agregar logging básico en `services.py` de tickets y analytics

**Entregable de la semana:** MVP desplegable con datos de entrenamiento acumulándose desde el día uno.

---

## Qué queda fuera de Fase 1 (backlog)

| Funcionalidad | Fase |
|---|---|
| Multi-tenancy con `django-tenants` | 2 |
| Clasificación con LLM externo | 2 |
| Asignación automática por menor carga | 2 |
| Notificaciones por email | 2 |
| Dashboard de métricas en tiempo real | 3 |
| Portal de usuario final (autoservicio) | 3 |
| Entrenamiento del modelo propio de clasificación | 3 |

---

## Reglas de dependencia entre dominios

```
shared      → no depende de nadie
users       → depende de shared
help_desk   → depende de users (solo por FK, nunca importa lógica)
analytics   → escucha eventos de help_desk (nunca importa modelos de help_desk)
```

Comunicación entre dominios: únicamente por eventos en `shared/events.py`. Nunca importar modelos de un dominio en otro directamente.

---

*Fase 1 MVP — Help Desk con captura de datos para automatización*