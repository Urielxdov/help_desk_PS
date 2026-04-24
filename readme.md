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
POST   /api/auth/token/                              # Obtener JWT (desarrollo)
```

### Catálogo

```
GET    /api/departments/                             # auth
POST   /api/departments/                             # super_admin
GET    /api/departments/{id}/categories/             # auth
POST   /api/service-categories/                      # area_admin
PUT    /api/service-categories/{id}/                 # area_admin
GET    /api/service-categories/{id}/services/        # auth
POST   /api/services/                                # area_admin
PUT    /api/services/{id}/                           # area_admin
PATCH  /api/services/{id}/toggle/                    # area_admin
```

### Help Desks

Filtros disponibles: `?status=`, `?priority=`, `?service=`, `?assignee_id=`, `?department=`

```
GET    /api/helpdesks/                               # Lista según rol
GET    /api/helpdesks/{id}/                          # Detalle
POST   /api/helpdesks/                               # Crear HD
PATCH  /api/helpdesks/{id}/status/                   # Cambiar estado (technician+)
PATCH  /api/helpdesks/{id}/assign/                   # Asignar técnico (area_admin+)
PATCH  /api/helpdesks/{id}/resolve/                  # Resolver (technician+)
PATCH  /api/helpdesks/{id}/close/                    # Cerrar (requester / area_admin+)
POST   /api/helpdesks/{id}/attachments/              # Subir adjunto
DELETE /api/helpdesks/{id}/attachments/{aid}/        # Eliminar adjunto
GET    /api/helpdesks/{id}/comments/                 # Ver comentarios
POST   /api/helpdesks/{id}/comments/                 # Añadir comentario
```

### Incidentes (area_admin+)

Agrupan múltiples tickets del mismo servicio bajo un ticket maestro de seguimiento.
Al resolver el maestro, todos los hijos se cierran automáticamente.

```
GET    /api/helpdesks/incidents/                     # Lista de incidentes activos
POST   /api/helpdesks/incidents/                     # Crear incidente
GET    /api/helpdesks/incidents/{id}/                # Detalle + tickets vinculados
POST   /api/helpdesks/incidents/{id}/link/           # Vincular tickets al incidente
```

**Body crear incidente:**
```json
{
  "service": 3,
  "origin": "error",
  "priority": "high",
  "problem_description": "Caída del servidor de producción",
  "due_date": "2026-04-25T18:00:00Z",
  "ticket_ids": [41, 43, 47]
}
```

### Monitoreo de incidentes (area_admin+)

Detecta servicios con acumulación anormal de tickets activos sin incidente asignado.

```
GET    /api/helpdesks/monitor/                       # Vista global
GET    /api/helpdesks/monitor/?department=2          # Filtrado por departamento
GET    /api/helpdesks/monitor/?threshold=3           # Override puntual del umbral
```

El threshold por defecto se resuelve en este orden:
1. `?threshold=N` en la query string
2. `SLAConfig.incident_threshold` del departamento
3. `SLAConfig.incident_threshold` global
4. `settings.INCIDENT_CANDIDATE_THRESHOLD` (default: 5)

### SLA (area_admin+)

```
GET    /api/sla/technicians/                         # Perfiles de técnicos
POST   /api/sla/technicians/                         # Crear perfil
PUT    /api/sla/technicians/{id}/                    # Actualizar perfil
DELETE /api/sla/technicians/{id}/                    # Eliminar perfil
GET    /api/sla/configs/                             # Configuraciones SLA
POST   /api/sla/configs/                             # Crear config (dept o global)
PUT    /api/sla/configs/{id}/                        # Actualizar config
GET    /api/sla/queue/                               # Cola de asignación pendiente
```

**Campos clave de SLAConfig:** `max_load`, `resolution_time`, `resolution_unit`,
`score_overdue`, `score_company`, `score_area`, `score_individual`,
`score_critical`, `score_high`, `score_medium`, `score_low`, `incident_threshold`

### Clasificador

```
POST   /api/classify/                                # Sugerir servicio a partir de texto
POST   /api/classify/feedback/                       # Registrar feedback del usuario
GET    /api/classify/stats/                          # Estadísticas (area_admin+)
POST   /api/classify/train/                          # Forzar entrenamiento (area_admin+)
GET    /api/service-keywords/                        # Listar keywords (area_admin+)
POST   /api/service-keywords/                        # Añadir keyword (area_admin+)
DELETE /api/service-keywords/{id}/                   # Eliminar keyword (area_admin+)
GET    /api/user-feedback-profiles/                  # Perfiles de confianza (area_admin+)
PATCH  /api/user-feedback-profiles/{id}/             # Ajustar trust_score / flagged (area_admin+)
```

---

## Pantallas

### Usuario final

| Pantalla | Ruta sugerida | Descripción |
|---|---|---|
| Crear HD | `/helpdesks/new` | Clasificador sugiere servicio · selector depto → categoría → servicio · formulario |
| Mis HDs | `/helpdesks` | Tabla con folio, servicio, estado, fecha · filtros por estado |
| Detalle HD | `/helpdesks/{id}` | Info + hilo de comentarios + adjuntos · banner si ticket vinculado a incidente |

### Técnico

| Pantalla | Ruta sugerida | Descripción |
|---|---|---|
| Mi cola | `/queue` | HDs asignados ordenados por urgencia · cambio rápido de estado |
| Detalle HD | `/queue/{id}` | Igual que usuario + notas internas + resolver |

### Admin de área

| Pantalla | Ruta sugerida | Descripción |
|---|---|---|
| Panel del área | `/area/helpdesks` | Todos los HDs del depto · asignación de técnico · filtro por departamento |
| Monitoreo | `/area/monitor` | Servicios con acumulación anormal · botón crear incidente pre-llenado |
| Incidentes | `/area/incidents` | Lista de incidentes activos · detalle con tickets vinculados |
| Configuración SLA | `/area/sla` | Editar `max_load`, `resolution_time`, `incident_threshold` y pesos de urgencia |
| Gestión de servicios | `/area/services` | CRUD de categorías y servicios |

### Super admin

| Pantalla | Ruta sugerida | Descripción |
|---|---|---|
| Departamentos | `/admin/departments` | CRUD de departamentos |
| Configuración global SLA | `/admin/sla` | Config SLA que aplica a todos los departamentos sin config propia |

---

## Alcances futuros

### Panel de confianza de usuarios del clasificador

El endpoint `GET /api/user-feedback-profiles/` ya existe y está protegido por `area_admin`/`super_admin`. Devuelve `user_id`, `trust_score`, `flagged`, `feedback_count` y `rate_limited_count` por usuario.

**Pendiente:** definir la pantalla frontend correspondiente. El bloqueador actual es que el perfil solo almacena `user_id` (entero del sistema externo) y no hay un contrato definido para obtener nombre/email del usuario a partir de ese ID. Una vez que ese contrato exista, hay dos opciones de implementación:

- **Opción A:** guardar `user_name`/`user_email` en `UserFeedbackProfile` al crear el perfil (si el JWT los incluye).
- **Opción B:** el frontend enriquece la lista llamando al sistema externo de usuarios con cada `user_id`.

La pantalla sugerida es una tabla ordenada por riesgo descendente (`flagged` primero, luego `trust_score` asc, luego `rate_limited_count` desc) con acción de PATCH para ajustar `trust_score` y activar/desactivar `flagged`.

---

## Criterio de terminado

- [ ] Proyecto corriendo con `python manage.py runserver`.
- [ ] Migraciones generadas y aplicadas sobre SQL Server.
- [ ] JWT funcional: login devuelve token, rutas protegidas lo validan.
- [ ] Tests mínimos por app (modelos y endpoints principales).
- [ ] Explicación corta de cambios por cada tarea implementada.