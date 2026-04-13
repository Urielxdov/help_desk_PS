# Help Desk MVP — Especificación Técnica

---

## Objetivo

Construir el módulo de Help Desk (HDs) desde cero: catálogo de departamentos, categorías y servicios, creación y gestión de HDs con adjuntos y comentarios, expuesto como API RESTful con rutas protegidas por rol.

---

## Stack

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.11 |
| Framework | Django 4.2 |
| API REST | Django REST Framework (DRF) |
| Autenticación | djangorestframework-simplejwt |
| Base de datos | SQL Server |
| ORM | Django ORM + mssql-django |
| Filtros | django-filter |
| CORS | django-cors-headers |

---

## Restricciones

- Seguir convenciones `snake_case` en todo el proyecto.
- Separar la lógica en apps Django por dominio (`catalog`, `helpdesks`).
- IDs enteros autoincrementales.
- El sistema de usuarios es externo; el JWT incluye `user_id` y `role`.
- La autenticación se valida vía token JWT en cada request.
- No exponer rutas administrativas sin el permiso correspondiente.

---

## Estructura de carpetas

```
helpdesk/
  config/
    settings.py
    urls.py
    wsgi.py
  apps/
    catalog/
      models.py         # Department, ServiceCategory, Service
      serializers.py
      views.py
      urls.py
      permissions.py
    helpdesks/
      models.py         # HelpDesk, HDAttachment, HDComment
      serializers.py
      views.py
      urls.py
      permissions.py
  manage.py
  requirements.txt
```

---

## Archivos clave

```
config/settings.py
config/urls.py

apps/catalog/models.py
apps/catalog/serializers.py
apps/catalog/views.py
apps/catalog/urls.py
apps/catalog/permissions.py

apps/helpdesks/models.py
apps/helpdesks/serializers.py
apps/helpdesks/views.py
apps/helpdesks/urls.py
apps/helpdesks/permissions.py
```

---

## Dependencias

```txt
# requirements.txt
Django==4.2
djangorestframework
djangorestframework-simplejwt
mssql-django
django-filter
django-cors-headers
```

---

## Modelo de base de datos

### `catalog_department`
| Campo | Tipo Django | Notas |
|---|---|---|
| `id` | AutoField PK | Autoincremental |
| `nombre` | CharField(100) | |
| `descripcion` | TextField | |
| `activo` | BooleanField | Default True |
| `created_at` | DateTimeField | auto_now_add |

### `catalog_servicecategory`
| Campo | Tipo Django | Notas |
|---|---|---|
| `id` | AutoField PK | |
| `nombre` | CharField(100) | Ej: Hardware, Software |
| `department` | ForeignKey | → Department |
| `activo` | BooleanField | Default True |

### `catalog_service`
| Campo | Tipo Django | Notas |
|---|---|---|
| `id` | AutoField PK | |
| `nombre` | CharField(100) | |
| `descripcion` | TextField | |
| `category` | ForeignKey | → ServiceCategory |
| `tiempo_estimado_default` | IntegerField | En horas |
| `activo` | BooleanField | Default True |
| `created_at` | DateTimeField | auto_now_add |

### `helpdesks_helpdesk`
| Campo | Tipo Django | Notas |
|---|---|---|
| `id` | AutoField PK | |
| `folio` | CharField(20) | HD-2024-0001, autogenerado |
| `solicitante_id` | IntegerField | Del sistema externo (JWT) |
| `responsable_id` | IntegerField | Técnico asignado, nullable |
| `service` | ForeignKey | → Service |
| `origen` | CharField choices | `error` \| `solicitud` \| `consulta` \| `mantenimiento` |
| `prioridad` | CharField choices | `baja` \| `media` \| `alta` \| `critica` |
| `estado` | CharField choices | `abierto` \| `en_progreso` \| `en_espera` \| `resuelto` \| `cerrado` |
| `descripcion_problema` | TextField | |
| `descripcion_solucion` | TextField | Null hasta resolver |
| `fecha_asignacion` | DateTimeField | Null, se llena al asignar |
| `fecha_compromiso` | DateTimeField | Null, la define el admin |
| `fecha_efectividad` | DateTimeField | Null, se llena al resolver |
| `tiempo_estimado` | IntegerField | Heredado del servicio, ajustable |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto_now |

### `helpdesks_hdattachment`
| Campo | Tipo Django | Notas |
|---|---|---|
| `id` | AutoField PK | |
| `help_desk` | ForeignKey | → HelpDesk |
| `tipo` | CharField choices | `archivo` \| `url` |
| `nombre` | CharField(200) | Nombre descriptivo |
| `valor` | TextField | Ruta o URL |
| `created_at` | DateTimeField | auto_now_add |

### `helpdesks_hdcomment`
| Campo | Tipo Django | Notas |
|---|---|---|
| `id` | AutoField PK | |
| `help_desk` | ForeignKey | → HelpDesk |
| `autor_id` | IntegerField | Del sistema externo |
| `contenido` | TextField | |
| `es_interno` | BooleanField | True = solo visible para TI |
| `created_at` | DateTimeField | auto_now_add |

---

## Roles y permisos

| Rol | Valor en JWT | Acceso |
|---|---|---|
| `usuario` | `user` | Crear HDs, ver los suyos, comentar |
| `tecnico` | `technician` | Ver HDs asignados, cambiar estado, comentar |
| `admin_area` | `area_admin` | Ver todos los HDs de su depto, asignar, gestionar servicios |
| `super_admin` | `super_admin` | Todo lo anterior + gestión de departamentos |

### Permisos custom (DRF)

```python
# apps/catalog/permissions.py
class IsAreaAdmin(BasePermission): ...
class IsSuperAdmin(BasePermission): ...

# apps/helpdesks/permissions.py
class IsTechnicianOrAdmin(BasePermission): ...
class IsOwnerOrAdmin(BasePermission): ...
```

---

## Reglas de negocio

- El folio se genera automáticamente con formato `HD-YYYY-XXXX`.
- Al crear un HD, `tiempo_estimado` se hereda del servicio si no se especifica.
- `fecha_asignacion` se registra automáticamente al asignar un responsable.
- `fecha_efectividad` se registra automáticamente al cambiar estado a `resuelto`.
- `descripcion_solucion` es **obligatoria** para marcar como resuelto.
- Los comentarios con `es_interno = True` no son visibles para el solicitante.
- Un adjunto solo puede ser de tipo `archivo` o `url`.
- Los estados siguen el flujo:

```
abierto → en_progreso → en_espera → resuelto → cerrado
```

---

## Flujo de creación de un HD

```
1. Usuario selecciona Departamento
        ↓
2. Aparecen categorías del depto (Hardware, Software...)
        ↓
3. Selecciona categoría → aparecen servicios con descripción
        ↓
4. Selecciona servicio → se hereda tiempo_estimado
        ↓
5. Llena: origen, descripción del problema
6. Adjunta archivos o URLs (opcional)
        ↓
7. HD creado en estado: abierto
        ↓
8. Admin del área asigna responsable → define fecha_compromiso
        ↓
9. Técnico atiende → cambia estado → agrega comentarios
        ↓
10. Técnico resuelve → llena descripcion_solucion + fecha_efectividad
        ↓
11. Admin o sistema cierra el HD
```

---

## Endpoints

### Autenticación

```
POST   /api/auth/token/             # Obtener JWT
POST   /api/auth/token/refresh/     # Refrescar JWT
```

### Catálogo — lectura (cualquier usuario autenticado)

```
GET    /api/departments/
GET    /api/departments/{id}/categories/
GET    /api/categories/{id}/services/
```

### Catálogo — administración (area_admin / super_admin)

```
POST   /api/departments/                      # super_admin
PUT    /api/departments/{id}/                 # super_admin

POST   /api/service-categories/               # area_admin
PUT    /api/service-categories/{id}/          # area_admin

POST   /api/services/                         # area_admin
PUT    /api/services/{id}/                    # area_admin
PATCH  /api/services/{id}/toggle/             # area_admin
```

### Help Desks

```
GET    /api/helpdesks/                        # Lista según rol
GET    /api/helpdesks/{id}/                   # Detalle
POST   /api/helpdesks/                        # Crear HD (usuario)
PATCH  /api/helpdesks/{id}/status/            # Cambiar estado (tecnico)
PATCH  /api/helpdesks/{id}/assign/            # Asignar técnico (area_admin)
PATCH  /api/helpdesks/{id}/resolve/           # Resolver HD (tecnico)
```

### Adjuntos

```
POST   /api/helpdesks/{id}/attachments/
DELETE /api/helpdesks/{id}/attachments/{attachment_id}/
```

### Comentarios

```
GET    /api/helpdesks/{id}/comments/
POST   /api/helpdesks/{id}/comments/
```

---

## Pantallas

### Usuario final

| Pantalla | Ruta | Descripción |
|---|---|---|
| Crear HD | `/helpdesks/new` | Selector depto → categoría → servicio, formulario |
| Mis HDs | `/helpdesks` | Tabla con folio, servicio, estado, fecha |
| Detalle HD | `/helpdesks/{id}` | Info + hilo de comentarios + adjuntos |

### Técnico

| Pantalla | Ruta | Descripción |
|---|---|---|
| Mi cola | `/queue` | HDs asignados, filtros por estado, cambio rápido de estado |
| Detalle HD | `/queue/{id}` | Igual que usuario + notas internas + resolver |

### Admin de área

| Pantalla | Ruta | Descripción |
|---|---|---|
| Panel del área | `/area/helpdesks` | Todos los HDs del depto, asignación de técnico |
| Gestión de servicios | `/area/services` | CRUD de categorías y servicios |

### Super admin

| Pantalla | Ruta | Descripción |
|---|---|---|
| Departamentos | `/admin/departments` | CRUD de departamentos |

---

## Criterio de terminado

- [ ] Proyecto corriendo con `python manage.py runserver`.
- [ ] Migraciones generadas y aplicadas sobre SQL Server.
- [ ] JWT funcional: login devuelve token, rutas protegidas lo validan.
- [ ] Tests mínimos por app (modelos y endpoints principales).
- [ ] Explicación corta de cambios por cada tarea implementada.