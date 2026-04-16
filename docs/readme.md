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
No existe un modelo `User` local. El JWT incluye `user_id` y `role`. Las referencias a usuarios en la DB son `IntegerField` (`solicitante_id`, `responsable_id`, `autor_id`), no FKs.

### 3. **Estado como maquina de estados**
Las transiciones de estado de un ticket estan definidas explicitamente en `VALID_TRANSITIONS`. El backend las valida en cada cambio — ningun estado invalido puede entrar a la DB.

### 4. **Soft-delete en catalogo, CASCADE en tickets**
Las entidades del catalogo (Department, ServiceCategory, Service) usan `activo=False` para desactivarse — nunca se eliminan fisicamente para preservar la integridad historica de los tickets. Los adjuntos y comentarios de un ticket se eliminan en cascada si el ticket se borra.

### 5. **Serializers separados por operacion**
`HelpDeskSerializer` es de solo lectura (GET). `HelpDeskCreateSerializer` es de escritura (POST). Esto evita que campos calculados o protegidos se expongan en inputs.

---

## Estructura del Proyecto

```
help_desk_PS/
├── config/
│   ├── settings.py            # Configuracion centralizada
│   ├── urls.py                # URLs raiz — prefijo /api/
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
│   └── helpdesks/             # Dominio: Tickets, Adjuntos, Comentarios
│       ├── models.py          # HelpDesk, HDAttachment, HDComment + choices
│       ├── serializers.py     # HelpDeskSerializer, HelpDeskCreateSerializer,
│       │                      # HelpDeskAssignSerializer, HDAttachmentSerializer,
│       │                      # HDCommentSerializer
│       ├── views.py           # HelpDeskViewSet, HDAttachmentViewSet, HDCommentViewSet
│       ├── urls.py            # Router + rutas manuales para adjuntos y comentarios
│       ├── permissions.py     # IsTechnicianOrAdmin
│       └── storage.py         # Abstraccion de almacenamiento de archivos
│
├── authentication.py          # JWTAuthentication + JWTUser (sin DB)
├── authentication_urls.py     # POST /api/auth/token/
├── manage.py
├── requirements.txt
├── docker-compose.yml
└── Dockerfile
```

---

## Apps de Dominio

### catalog/

Gestiona la jerarquia de servicios: `Department → ServiceCategory → Service`.

```
catalog/
├── models.py       ← Department, ServiceCategory, Service
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
abierto → en_progreso → en_espera → en_progreso  (puede ir y volver)
                     → resuelto  → cerrado
en_espera            → resuelto
```

**Visibilidad por rol (get_queryset):**

| Rol | Filtra por |
|---|---|
| `user` | `solicitante_id = request.user.user_id` |
| `technician` | `responsable_id = request.user.user_id` |
| `area_admin` | Sin filtro — ve todos |
| `super_admin` | Sin filtro — ve todos |

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

---

## Flujo de Datos

### Crear un ticket

```
POST /api/helpdesks/
    │
    │ Body: { service, origen, prioridad, descripcion_problema }
    │
    ├─► HelpDeskCreateSerializer.validate()
    │   └─► Si no trae tiempo_estimado → hereda service.tiempo_estimado_default
    │
    ├─► HelpDeskViewSet.perform_create()
    │   └─► solicitante_id = request.user.user_id
    │       estado = 'abierto' (default del modelo)
    │       folio = auto-generado en HelpDesk.save()
    │
    └─► Response 201 con HelpDeskSerializer (lectura completa)
```

### Cambiar estado

```
PATCH /api/helpdesks/{id}/status/
    │
    │ Body: { "estado": "en_progreso" }
    │
    ├─► Permiso: IsTechnicianOrAdmin
    │
    ├─► Valida transicion:
    │   VALID_TRANSITIONS[hd.estado].includes(nuevo_estado)
    │   Si invalida → 400 ValidationError
    │
    └─► hd.estado = nuevo_estado → save()
        Response 200 con HelpDeskSerializer
```

### Asignar tecnico

```
PATCH /api/helpdesks/{id}/assign/
    │
    │ Body: { "responsable_id": 42, "fecha_compromiso": "ISO8601" }
    │
    ├─► Permiso: IsAreaAdmin
    │
    ├─► HelpDeskAssignSerializer.validate() → responsable_id int requerido
    │
    └─► hd.responsable_id = responsable_id
        hd.fecha_asignacion = timezone.now()  ← automatico
        hd.fecha_compromiso = fecha_compromiso (opcional)
        → save() → Response 200
```

### Resolver ticket

```
PATCH /api/helpdesks/{id}/resolve/
    │
    │ Body: { "descripcion_solucion": "..." }
    │
    ├─► Permiso: IsTechnicianOrAdmin
    │
    ├─► Valida: estado in ['en_progreso', 'en_espera']
    │   Valida: descripcion_solucion no vacia
    │
    └─► hd.estado = 'resuelto'
        hd.descripcion_solucion = descripcion_solucion
        hd.fecha_efectividad = timezone.now()  ← automatico
        → save() → Response 200
```

---

## Reglas de Negocio

1. **Folio** — se genera automaticamente en `HelpDesk.save()` con formato `HD-XXXXXX` basado en el PK. No se puede modificar via API (read-only en el serializer).

2. **tiempo_estimado** — se hereda de `service.tiempo_estimado_default` al crear si no se especifica en el body.

3. **fecha_asignacion** — se registra con `timezone.now()` automaticamente en el endpoint `/assign/`. No se puede enviar desde el cliente.

4. **fecha_efectividad** — se registra con `timezone.now()` automaticamente al resolver. No se puede enviar desde el cliente.

5. **descripcion_solucion** — es obligatoria para marcar un ticket como resuelto. El endpoint `/resolve/` la requiere no vacia.

6. **Comentarios internos** — `es_interno=True` los hace invisibles para el rol `user`. El filtro se aplica en `HDCommentViewSet.get_queryset()`, no en el serializer.

7. **Adjuntos tipo archivo** — el servidor valida tamaño maximo (10 MB). El archivo se guarda via `storage.py` — intercambiable entre almacenamiento local y S3 sin cambiar las vistas.

8. **Soft-delete en catalogo** — desactivar un servicio usa `PATCH /services/{id}/toggle/` que invierte el flag `activo`. No hay endpoint DELETE para catalogo.
