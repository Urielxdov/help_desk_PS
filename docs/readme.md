# Arquitectura Backend — Help Desk API

Organizacion del proyecto **por app de dominio**, donde cada feature agrupa modelos, serializers, vistas y permisos en una sola carpeta. Equivalente al enfoque de `apps` en Django + DRF por dominio de negocio.

## Tabla de Contenidos

- [Principios Clave](#principios-clave)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Apps de Dominio](#apps-de-dominio)
- [Autenticacion](#autenticacion)
- [Permisos por Rol](#permisos-por-rol)
- [Flujo de Datos](#flujo-de-datos)
- [Reglas de Negocio](#reglas-de-negocio)

---

## Principios Clave

### 1. **App por dominio**
Cada app agrupa todo lo relacionado a un concepto de negocio. `catalog` no importa nada de `helpdesks`. Cada app tiene sus propios modelos, serializers, vistas, URLs y permisos.

### 2. **Usuarios externos al sistema**
No existe un modelo `User` local. El JWT incluye `user_id` y `role`. Las referencias a usuarios en la DB son `IntegerField` (`requester_id`, `assignee_id`, `author_id`), no FKs.

### 3. **Estado como maquina de estados**
Las transiciones de estado de un ticket estan definidas explicitamente en `VALID_TRANSITIONS`. El backend las valida en cada cambio — ningun estado invalido puede entrar a la DB.

### 4. **Soft-delete en catalogo, CASCADE en tickets**
Las entidades del catalogo (Department, ServiceCategory, Service) usan `active=False` para desactivarse — nunca se eliminan fisicamente para preservar la integridad historica de los tickets. Los adjuntos y comentarios de un ticket se eliminan en cascada si el ticket se borra.

### 5. **Serializers separados por operacion**
`HelpDeskSerializer` es de solo lectura (GET). `HelpDeskCreateSerializer` es de escritura (POST). Esto evita que campos calculados o protegidos se expongan en inputs.

### 6. **SLA Configurable por Departamento**
Cada departamento define su propia política de asignación: carga máxima por técnico, tiempo máximo de resolución (en horas hábiles, horas calendario o días), y pesos de urgencia para scoring automático de la cola.

### 7. **Clasificación Automática de Servicios**
El sistema aprende de los problemas históricos — extrae keywords por servicio y sugiere automáticamente el servicio más probable cuando el usuario describe su problema.

---

## Estructura del Proyecto

```
help_desk_PS/
├── config/
│   ├── settings.py            # Configuracion centralizada
│   ├── urls.py                # URLs raiz — prefijo /api/
│   ├── celery.py              # Celery worker config
│   ├── business_hours.py      # Utilidades para cálculos en horas hábiles
│   ├── wsgi.py
│   └── exceptions.py          # Manejador de errores unificado
│
├── apps/
│   ├── catalog/               # Dominio: Departamentos, Categorias, Servicios
│   │   ├── models.py          # Department, ServiceCategory, Service
│   │   ├── serializers.py     # Un serializer por modelo
│   │   ├── views.py           # ViewSets con mixins minimos
│   │   ├── urls.py            # DefaultRouter
│   │   └── permissions.py     # IsAreaAdmin, IsSuperAdmin
│   │
│   ├── helpdesks/             # Dominio: Tickets, Adjuntos, Comentarios
│   │   ├── models.py          # HelpDesk, HDAttachment, HDComment + choices
│   │   ├── serializers.py     # HelpDeskSerializer, HelpDeskCreateSerializer, etc
│   │   ├── views.py           # HelpDeskViewSet, HDAttachmentViewSet, HDCommentViewSet
│   │   ├── urls.py            # Router + rutas manuales para adjuntos y comentarios
│   │   ├── permissions.py     # IsTechnicianOrAdmin
│   │   └── storage.py         # Abstraccion de almacenamiento de archivos
│   │
│   ├── sla/                   # Dominio: Asignación automática y Queue
│   │   ├── models.py          # TechnicianProfile, SLAConfig, ServiceQueue
│   │   ├── serializers.py     # Serializers para SLA y cola
│   │   ├── services.py        # Lógica de asignación y scoring de urgencia
│   │   ├── views.py           # ViewSets read-only para monitoreo
│   │   ├── urls.py            # Router
│   │   ├── tasks.py           # Celery tasks para auto-asignación
│   │   ├── signals.py         # Handlers de post_save para disparar Celery
│   │   └── permissions.py     # IsAreaAdmin
│   │
│   └── classifier/            # Dominio: Clasificación automática de servicios
│       ├── models.py          # ServiceKeyword, ClassificationFeedback
│       ├── serializers.py     # Serializers para keywords y feedback
│       ├── services.py        # Lógica de clasificación por keywords
│       ├── training.py        # Ajuste automático de pesos basado en feedback
│       ├── views.py           # ViewSets para keywords, classify, feedback, stats
│       ├── urls.py            # Router
│       ├── tasks.py           # Celery task para entrenamiento
│       └── permissions.py     # IsAreaAdmin
│
├── authentication.py          # JWTAuthentication + JWTUser (sin DB)
├── authentication_urls.py     # POST /api/auth/token/
├── manage.py
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── docs/
    ├── readme.md              # Este archivo
    ├── Architecture.md        # Flujos detallados
    └── API_Reference.md       # Referencia de endpoints
```

---

## Apps de Dominio

### catalog/

Gestiona la jerarquia de servicios: `Department → ServiceCategory → Service`.

```
catalog/
├── models.py       ← Department, ServiceCategory, Service (con impact por service)
├── serializers.py  ← Validacion de activo en FKs
├── views.py        ← DepartmentViewSet (CRUD), ServiceCategoryViewSet, ServiceViewSet
├── urls.py         ← DefaultRouter
└── permissions.py  ← IsAreaAdmin, IsSuperAdmin
```

**Jerarquia:**
```
Department
    └── ServiceCategory (FK → Department, PROTECT)
            └── Service (FK → ServiceCategory, PROTECT)
                └── impact: 'individual' | 'area' | 'company'
                └── estimated_hours: horas estimadas para resolver
```

**Regla clave**: `on_delete=PROTECT` en todas las FKs del catalogo. No se puede eliminar un departamento si tiene categorias, ni una categoria si tiene servicios. Esto preserva la integridad de los tickets historicos que referencian un servicio.

### helpdesks/

Gestiona el ciclo de vida completo de un ticket.

```
helpdesks/
├── models.py       ← HelpDesk, HDAttachment, HDComment + VALID_TRANSITIONS
├── serializers.py  ← Serializers separados por operacion (lectura vs escritura)
├── views.py        ← ViewSets con logica de rol en get_queryset()
├── urls.py         ← Router + rutas manuales para recursos anidados
├── permissions.py  ← IsTechnicianOrAdmin
└── storage.py      ← Abstraccion para almacenamiento local / S3
```

**Maquina de estados:**
```
open → in_progress → on_hold → in_progress  (puede ir y volver)
                  → resolved → closed
on_hold          → resolved
```

**Visibilidad por rol (get_queryset):**

| Rol | Filtra por |
|---|---|
| `user` | `requester_id = request.user.user_id` |
| `technician` | `assignee_id = request.user.user_id` |
| `area_admin` | Sin filtro — ve todos |
| `super_admin` | Sin filtro — ve todos |

**Nuevos campos:**
- `impact`: 'individual' | 'area' | 'company' — heredado de `service.impact` al crear
- `due_date`: fecha de compromiso — calculada automáticamente según `SLAConfig` del departamento

### sla/

Asignación automática de tickets a técnicos + cola priorizada.

```
sla/
├── models.py       ← TechnicianProfile, SLAConfig, ServiceQueue
├── services.py     ← try_assign(), enqueue(), process_queue(), compute_urgency_score()
├── views.py        ← ViewSets read-only para monitoreo
├── urls.py         ← Router
├── tasks.py        ← Celery tasks: auto_assign_helpdesk, process_department_queue, process_all_queues
├── signals.py      ← post_save handlers para disparar Celery
└── permissions.py  ← IsAreaAdmin
```

**Modelos:**
- `TechnicianProfile`: vincula `user_id` externo con departamento y activo/inactivo
- `SLAConfig`: políticas por departamento (max_load, resolution_time, resolution_unit, pesos de urgencia)
- `ServiceQueue`: tickets encolados en espera de técnico disponible

**Flujo de asignación:**
```
1. Ticket creado → signal dispara auto_assign_helpdesk
2. Si hay técnico disponible → asigna + calcula due_date
3. Si todos en max_load → encola en ServiceQueue con urgency_score
4. Cuando técnico resuelve/cierra → signal dispara process_department_queue
5. Desencola siguiente ticket de mayor urgency_score
```

**Cálculo de urgency_score:**
```
score = score_overdue (1000 si vencido) 
      + score_company/area/individual (según impact)
      + score_critical/high/medium/low (según priority)
```

**Horario hábil:**
- Asignaciones solo entre 08:30-18:00 Lun-Vie
- Fuera de horario los tickets quedan en cola
- Celery Beat a las 08:30 cada día hábil desencola acumulados

### classifier/

Clasificación automática de servicios basada en keywords + aprendizaje de feedback.

```
classifier/
├── models.py       ← ServiceKeyword, ClassificationFeedback
├── services.py     ← classify() — busca keywords y devuelve top 3 servicios
├── training.py     ← run_training() — ajusta pesos basado en feedback
├── views.py        ← classify_view, feedback_view, ServiceKeywordViewSet, stats_view, train_view
├── urls.py         ← Router
├── tasks.py        ← Celery task para entrenamiento automático
└── permissions.py  ← IsAreaAdmin
```

**Modelos:**
- `ServiceKeyword`: palabra clave → servicio con weight (prioridad)
- `ClassificationFeedback`: registro de si el usuario aceptó o cambió la sugerencia

**Flujo de clasificación:**
```
1. Usuario entra texto → POST /api/classify/
2. Sistema busca keywords en el texto
3. Suma pesos por servicio
4. Devuelve top 3 servicios con score
5. Usuario acepta o rechaza → POST /api/classify/feedback/
6. Celery entrena: 
   - Si aceptó → sube weight de keywords correctos
   - Si rechazó → baja weight de incorrectos + extrae palabras nuevas
```

**Entrenamiento automático:**
- Corre diario a las 2am vía Celery Beat
- Procesa todos los feedbacks pendientes (donde `trained=False`)
- Ajusta pesos y marca como entrenados

---

## Autenticacion

Sin sesion, sin modelos de usuario locales. Cada request trae un JWT en el header.

```
Authorization: Bearer <token>
```

**JWTAuthentication** (authentication.py):
- Lee el header `Authorization: Bearer`
- Decodifica el JWT sin verificar firma (`verify_signature=False`) — el sistema de usuarios externo es el emisor confiable
- Construye un objeto `JWTUser(user_id, role)` en memoria — no hace consulta a DB
- Retorna `None` si no hay header (permite endpoints publicos)
- Lanza `AuthenticationFailed` si el token existe pero es invalido

**JWTUser** (en memoria, no es modelo DB):
```python
user.user_id  # int | None
user.role     # str | None  →  user | technician | area_admin | super_admin
user.is_authenticated  # siempre True si llego aqui
```

**Endpoint de desarrollo:**
```
POST /api/auth/token/
{"user_id": 1, "role": "technician"}
```
Devuelve JWT firmado con `SECRET_KEY` — solo para testing local.

---

## Permisos por Rol

| Permiso | Clase | Roles permitidos |
|---|---|---|
| `IsAuthenticated` | DRF builtin | Cualquier rol con JWT valido |
| `IsTechnicianOrAdmin` | helpdesks/permissions | technician, area_admin, super_admin |
| `IsAreaAdmin` | catalog/permissions | area_admin, super_admin |
| `IsSuperAdmin` | catalog/permissions | super_admin |

**Matriz de acceso por endpoint:**

| Endpoint | user | technician | area_admin | super_admin |
|---|:---:|:---:|:---:|:---:|
| GET /helpdesks/ | Solo suyos | Solo asignados | Todos | Todos |
| POST /helpdesks/ | Si | No | Si | Si |
| PATCH /helpdesks/{id}/status/ | No | Si | Si | Si |
| PATCH /helpdesks/{id}/assign/ | No | No | Si | Si |
| PATCH /helpdesks/{id}/resolve/ | No | Si | Si | Si |
| GET/POST /comments/ | Si | Si | Si | Si |
| POST/DELETE /attachments/ | Si | Si | Si | Si |
| POST/PUT /departments/ | No | No | No | Si |
| POST/PUT /service-categories/ | No | No | Si | Si |
| POST/PUT /services/ | No | No | Si | Si |
| PATCH /services/{id}/toggle/ | No | No | Si | Si |
| GET/POST /technician-profiles/ | No | No | Si | Si |
| GET/POST /sla-config/ | No | No | Si | Si |
| GET /service-queue/ | No | No | Si | Si |
| POST /classify/ | Si | Si | Si | Si |
| POST /classify/feedback/ | Si | Si | Si | Si |
| GET/POST /service-keywords/ | No | No | Si | Si |
| POST /classify/train/ | No | No | Si | Si |
| GET /classify/stats/ | No | No | Si | Si |
| GET /choices/ | Si | Si | Si | Si |

---

## Flujo de Datos

### Crear un ticket

```
POST /api/helpdesks/
    │
    │ Body: { service, origin, priority, problem_description, estimated_hours? }
    │
    ├─► HelpDeskCreateSerializer.validate()
    │   ├─► Si no trae estimated_hours → hereda service.estimated_hours
    │   └─► impact = service.impact (auto)
    │
    ├─► HelpDeskViewSet.create()
    │   └─► requester_id = request.user.user_id
    │       status = 'open' (default)
    │       folio = auto-generado en HelpDesk.save()
    │
    ├─► Django signal: post_save(HelpDesk, created=True)
    │   └─► Celery task: auto_assign_helpdesk(hd_id)
    │       ├─► if is_business_hours() and técnico_disponible:
    │       │   - assignee_id = técnico_menos_cargado
    │       │   - due_date = calculate_due_date(...) según SLAConfig
    │       │   - save()
    │       └─► else: enqueue(hd) en ServiceQueue
    │
    └─► Response 201 con HelpDeskSerializer
```

### Clasificar servicio (antes de crear ticket)

```
POST /api/classify/
    │
    │ Body: { "text": "mi impresora no funciona" }
    │
    ├─► classify(text) en services.py
    │   ├─► Busca cada ServiceKeyword en el texto (case-insensitive)
    │   ├─► Suma pesos por servicio
    │   └─► Retorna top 3 servicios con score ≥ MIN_SCORE
    │
    └─► Response: {
            "suggestions": [
                {
                    "service_id": 3,
                    "service_name": "Soporte Hardware",
                    "category_id": 2,
                    "category_name": "Equipos",
                    "department_id": 1,
                    "department_name": "TI",
                    "score": 7
                },
                ...
            ]
        }
```

### Guardar feedback de clasificación

```
POST /api/classify/feedback/
    │
    │ Body: {
    │     "problem_description": "mi impresora...",
    │     "suggested_service": 3,           # null si no hubo sugerencia
    │     "chosen_service": 5,              # lo que el usuario eligió
    │     "accepted": false                 # true si aceptó la sugerencia
    │ }
    │
    ├─► ClassificationFeedbackSerializer.validate()
    │
    └─► Response 201
```

### Entrenar el clasificador

```
POST /api/classify/train/
    │
    │ (Sin body — dispara manualmente)
    │
    ├─► train_classifier.delay() (Celery)
    │   └─► run_training()
    │       ├─► Para cada feedback con trained=False:
    │       │   ├─► Si accepted=True: sube weight de keywords correctos
    │       │   └─► Si accepted=False:
    │       │       - Baja weight de keywords incorrectos (o borra si weight < MIN_WEIGHT)
    │       │       - Extrae palabras nuevas del texto
    │       │       - Crea ServiceKeyword nuevos con weight=1
    │       └─► feedback.trained = True
    │
    └─► Response: {"detail": "Entrenamiento encolado."}
```

### Asignar técnico manualmente

```
PATCH /api/helpdesks/{id}/assign/
    │
    │ Body: { "assignee_id": 42, "due_date": "ISO8601"?, "impact": "area"? }
    │
    ├─► Permiso: IsAreaAdmin
    │
    ├─► HelpDeskAssignSerializer.validate()
    │
    └─► hd.assignee_id = assignee_id
        hd.assigned_at = timezone.now()
        hd.due_date = due_date OR calculate_due_date(...) según SLAConfig
        hd.impact = impact (si se manda)
        → save() → Response 200
```

### Resolver ticket

```
PATCH /api/helpdesks/{id}/resolve/
    │
    │ Body: { "solution_description": "..." }
    │
    ├─► Permiso: IsTechnicianOrAdmin
    │
    ├─► Valida: status in ['in_progress', 'on_hold', 'resolved']
    │   Valida: solution_description no vacia
    │
    ├─► hd.status = 'resolved'
    │   hd.solution_description = solution_description
    │   hd.resolved_at = timezone.now()
    │   → save()
    │
    ├─► Django signal: post_save(HelpDesk)
    │   └─► Celery task: process_department_queue(department_id)
    │       └─► Desencola siguiente ticket y lo asigna si hay disponibilidad
    │
    └─► Response 200
```

---

## Reglas de Negocio

### Tickets

1. **Folio** — se genera automaticamente en `HelpDesk.save()` con formato `HD-XXXXXX` basado en el PK. No se puede modificar via API (read-only).

2. **estimated_hours** — se hereda de `service.estimated_hours` al crear si no se especifica en el body.

3. **impact** — se hereda de `service.impact` al crear. El area_admin puede sobreescribir en `/assign/`.

4. **assigned_at** — se registra con `timezone.now()` automaticamente en el endpoint `/assign/`. No se puede enviar desde el cliente.

5. **due_date** — se calcula automaticamente según `SLAConfig` del departamento:
   - business_hours: `assigned_at + accumulated_hours + resolution_time` (en horas hábiles)
   - calendar_hours: `assigned_at + resolution_time` (en horas calendario)
   - calendar_days: `assigned_at + resolution_time` (en días calendario)

6. **resolved_at** — se registra con `timezone.now()` automaticamente al resolver. No se puede enviar desde el cliente.

7. **solution_description** — es obligatoria para marcar un ticket como resuelto.

8. **Comentarios internos** — `is_internal=True` los hace invisibles para el rol `user`. El filtro se aplica en `HDCommentViewSet.get_queryset()`.

9. **Adjuntos tipo archivo** — el servidor valida tamaño maximo (10 MB). El archivo se guarda via `storage.py`.

### SLA

10. **Horario hábil** — 08:30-18:00 Lun-Vie. Fuera de horario, tickets van a la cola automáticamente.

11. **max_load** — límite de tickets activos (open/in_progress/on_hold) por técnico.

12. **resolution_time + resolution_unit** — tiempo máximo de resolución configurable por departamento en horas hábiles, horas calendario o días.

13. **urgency_score** — se calcula per ticket encolado. Tickets vencidos (due_date < ahora) ganan +1000 puntos automáticamente.

14. **Desencola** — intenta asignar el siguiente cuando se libera un slot.

### Clasificador

15. **ServiceKeyword** — palabra clave con weight (1-10). El sistema sugiere servicios si el texto contiene el keyword.

16. **MIN_SCORE** — threshold minimo (default=1). Por debajo, no hay sugerencia.

17. **TOP_N** — máximo de sugerencias devueltas (default=3).

18. **Entrenamiento automático** — corre a las 2am diariamente. Ajusta pesos basado en feedback de usuarios.

### Catalogo

19. **Soft-delete** — servicios, categorias y departamentos usan `active=False` para desactivarse. No hay DELETE fisico.

20. **PROTECT en FKs** — no se puede eliminar un departamento si tiene categorias o servicios.
