# Diagramas de Arquitectura — Help Desk API

## 1. ESTRUCTURA DE APPS

```
┌─────────────────────────────────────────────────────────────────┐
│                     Django REST Framework                        │
│                                                                  │
│   /api/auth/        /api/departments/    /api/helpdesks/        │
│   /api/services/    /api/service-        /api/helpdesks/{id}/   │
│                     categories/          attachments/comments/   │
└────┬────────────────────┬───────────────────────┬───────────────┘
     │                    │                        │
     ▼                    ▼                        ▼
┌──────────────┐  ┌───────────────────┐  ┌──────────────────────┐
│ authentication│  │   apps/catalog/   │  │  apps/helpdesks/     │
│               │  │                   │  │                      │
│ JWTUser       │  │ Department        │  │ HelpDesk             │
│ (en memoria)  │  │ ServiceCategory   │  │ HDAttachment         │
│               │  │ Service           │  │ HDComment            │
│ authentication│  │                   │  │                      │
│ _urls.py      │  │ IsAreaAdmin       │  │ IsTechnicianOrAdmin   │
└───────────────┘  │ IsSuperAdmin      │  │                      │
                   └───────────────────┘  └──────────────────────┘
                            │                        │
                            └────────────┬───────────┘
                                         ▼
                              ┌──────────────────────┐
                              │      config/          │
                              │                      │
                              │ settings.py          │
                              │ urls.py              │
                              │ exceptions.py        │
                              └──────────────────────┘
```

---

## 2. MODELOS Y RELACIONES

```
┌─────────────────────────────────────────────────────────────────┐
│                        app: catalog                              │
│                                                                  │
│  ┌─────────────────┐                                            │
│  │   Department    │                                            │
│  │─────────────────│                                            │
│  │ id              │                                            │
│  │ nombre          │                                            │
│  │ descripcion     │                                            │
│  │ activo          │                                            │
│  │ created_at      │                                            │
│  └────────┬────────┘                                            │
│           │ FK (PROTECT)                                        │
│           ▼                                                      │
│  ┌─────────────────────┐                                        │
│  │   ServiceCategory   │                                        │
│  │─────────────────────│                                        │
│  │ id                  │                                        │
│  │ nombre              │                                        │
│  │ department ─────────┘                                        │
│  │ activo              │                                        │
│  └──────────┬──────────┘                                        │
│             │ FK (PROTECT)                                      │
│             ▼                                                    │
│  ┌─────────────────────────┐                                    │
│  │        Service          │                                    │
│  │─────────────────────────│                                    │
│  │ id                      │                                    │
│  │ nombre                  │                                    │
│  │ descripcion             │                                    │
│  │ category ───────────────┘                                    │
│  │ tiempo_estimado_default  │                                   │
│  │ activo                  │                                    │
│  │ created_at              │                                    │
│  └────────────┬────────────┘                                    │
└───────────────│─────────────────────────────────────────────────┘
                │ FK (PROTECT)
                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        app: helpdesks                            │
│                                                                  │
│  ┌─────────────────────────────────────┐                        │
│  │              HelpDesk               │                        │
│  │─────────────────────────────────────│                        │
│  │ id                                  │                        │
│  │ folio            [autogenerado]     │                        │
│  │ solicitante_id   [IntegerField]     │ ← referencia externa   │
│  │ responsable_id   [IntegerField]     │ ← referencia externa   │
│  │ service ────────────────────────────┘                        │
│  │ origen           [choices]          │                        │
│  │ prioridad        [choices]          │                        │
│  │ estado           [choices]          │                        │
│  │ descripcion_problema                │                        │
│  │ descripcion_solucion [null hasta resolver]                   │
│  │ fecha_asignacion [auto en /assign/] │                        │
│  │ fecha_compromiso [opcional]         │                        │
│  │ fecha_efectividad [auto en /resolve/]                        │
│  │ tiempo_estimado  [hereda del servicio]                       │
│  │ created_at                          │                        │
│  │ updated_at                          │                        │
│  └──────────────┬──────────────────────┘                        │
│                 │ FK (CASCADE)                                   │
│         ┌───────┴────────┐                                       │
│         ▼                ▼                                       │
│  ┌──────────────┐ ┌──────────────┐                             │
│  │ HDAttachment │ │  HDComment   │                             │
│  │──────────────│ │──────────────│                             │
│  │ id           │ │ id           │                             │
│  │ help_desk ───┘ │ help_desk ───┘                             │
│  │ tipo           │ autor_id     │ ← referencia externa        │
│  │ nombre         │ contenido    │                             │
│  │ valor          │ es_interno   │                             │
│  │ created_at     │ created_at   │                             │
│  └──────────────┘ └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. MAQUINA DE ESTADOS

```
                     ┌─────────┐
                     │ abierto │
                     └────┬────┘
                          │ PATCH /status/
                          ▼
                   ┌─────────────┐
              ┌───►│ en_progreso │◄──┐
              │    └──────┬──────┘   │
              │           │          │
    PATCH /status/        │   PATCH /status/
    "en_progreso"         │   "en_espera"
              │           ▼          │
              │    ┌─────────────┐   │
              └────│  en_espera  │───┘
                   └──────┬──────┘
                          │ PATCH /status/
                          │ "resuelto"
                          │ (requiere descripcion_solucion)
                          ▼
                    ┌──────────┐
                    │ resuelto │
                    └────┬─────┘
                         │ PATCH /status/
                         │ "cerrado"
                         ▼
                    ┌────────┐
                    │cerrado │  ← estado terminal
                    └────────┘
```

**Nota:** El endpoint `/resolve/` es un shortcut que hace la transicion a `resuelto` y ademas guarda `descripcion_solucion` y `fecha_efectividad` atomicamente. La transicion via `/status/` con valor `resuelto` requiere que el estado actual sea `en_progreso` o `en_espera` (segun `VALID_TRANSITIONS`).

---

## 4. ANATOMIA DE UN VIEWSET

```
┌───────────────────────────────────────────────────────────────┐
│                    HelpDeskViewSet                             │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ get_queryset()          ← filtra por rol del JWT        │ │
│  │   user       → filter(solicitante_id=user_id)          │ │
│  │   technician → filter(responsable_id=user_id)          │ │
│  │   admin+     → HelpDesk.objects.all()                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │ list() → GET /      │  │ create() → POST /            │  │
│  │ retrieve() → GET /{id} │ HelpDeskCreateSerializer     │  │
│  │ HelpDeskSerializer  │  │ perform_create():            │  │
│  │                     │  │   solicitante_id = user_id   │  │
│  └─────────────────────┘  └──────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ @action status/ → PATCH                                  ││
│  │   Valida VALID_TRANSITIONS[actual].includes(nuevo)       ││
│  └──────────────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────────┐│
│  │ @action assign/ → PATCH  (IsAreaAdmin)                   ││
│  │   HelpDeskAssignSerializer                               ││
│  │   responsable_id + fecha_asignacion=now()                ││
│  └──────────────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────────┐│
│  │ @action resolve/ → PATCH  (IsTechnicianOrAdmin)          ││
│  │   Valida estado in [en_progreso, en_espera]              ││
│  │   Guarda descripcion_solucion + fecha_efectividad=now()  ││
│  └──────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────┘
```

---

## 5. SERIALIZERS POR OPERACION

```
┌─────────────────────────────────────────────────────────────────┐
│                     helpdesks/serializers.py                     │
│                                                                  │
│  ┌─────────────────────────┐                                    │
│  │   HelpDeskSerializer    │  ← GET (lectura)                   │
│  │─────────────────────────│                                    │
│  │ id, folio (read-only)   │                                    │
│  │ solicitante_id (ro)     │                                    │
│  │ responsable_id (ro)     │                                    │
│  │ service + service_nombre│ ← nested CharField                 │
│  │ origen, prioridad       │                                    │
│  │ estado (ro)             │                                    │
│  │ descripcion_problema    │                                    │
│  │ descripcion_solucion    │                                    │
│  │ fechas (ro)             │                                    │
│  │ tiempo_estimado         │                                    │
│  │ attachments[] (nested)  │ ← HDAttachmentSerializer many=True │
│  │ created_at, updated_at  │                                    │
│  └─────────────────────────┘                                    │
│                                                                  │
│  ┌─────────────────────────────┐                                │
│  │  HelpDeskCreateSerializer   │  ← POST (escritura)            │
│  │─────────────────────────────│                                │
│  │ service                     │                                │
│  │ origen                      │                                │
│  │ prioridad                   │                                │
│  │ descripcion_problema        │                                │
│  │ tiempo_estimado (opcional)  │ ← si no viene, hereda del svc  │
│  └─────────────────────────────┘                                │
│                                                                  │
│  ┌─────────────────────────────┐                                │
│  │  HelpDeskAssignSerializer   │  ← PATCH /assign/ (validacion) │
│  │─────────────────────────────│                                │
│  │ responsable_id (requerido)  │                                │
│  │ fecha_compromiso (opcional) │                                │
│  └─────────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. FLUJO DE AUTENTICACION

```
Client
  │
  │  POST /api/auth/token/
  │  { user_id: 5, role: "technician" }
  │
  ▼
TokenView (AllowAny)
  │
  │  Genera JWT con { user_id, role } como claims
  │  Firma con SECRET_KEY
  │
  ▼
{ access: "eyJ..." }
  │
  │  Requests siguientes:
  │  Authorization: Bearer eyJ...
  │
  ▼
JWTAuthentication.authenticate()
  │
  ├─► No hay header → retorna None (DRF pasa al siguiente backend)
  ├─► Header invalido → AuthenticationFailed 401
  │
  └─► Decodifica JWT (sin verificar firma — confia en el emisor externo)
      Construye JWTUser(user_id=5, role="technician")
      No hace consulta a DB
      │
      ▼
  request.user = JWTUser  ← disponible en toda la vista
```

---

## 7. MANEJO DE ERRORES

Todas las excepciones pasan por `config/exceptions.py` y se normalizan al mismo formato:

```json
{
  "error": "Mensaje legible por el cliente",
  "code": "NombreDeExcepcion"
}
```

**Casos manejados:**

| Excepcion | Status | Ejemplo de error |
|---|---|---|
| `ValidationError` del serializer | 400 | "servicio: Este campo es requerido." |
| `ValidationError` de la vista | 400 | "Transicion invalida: abierto → cerrado" |
| `AuthenticationFailed` | 401 | "Token invalido o expirado." |
| `PermissionDenied` | 403 | "No tienes permiso para realizar esta accion." |
| `NotFound` | 404 | "No encontrado." |
| Excepcion no manejada | 500 | "Error interno del servidor." |

---

## 8. MODELO DE BASE DE DATOS (DBML)

```dbml
// Compatible con dbdiagram.io

Table Department {
  id          int         [pk, increment]
  nombre      varchar(100)[not null]
  descripcion text
  activo      bool        [default: true]
  created_at  timestamp   [default: `now()`]

  Note: "catalog_department — soft-delete via activo"
}

Table ServiceCategory {
  id            int         [pk, increment]
  department_id int         [ref: > Department.id, not null]
  nombre        varchar(100)[not null]
  activo        bool        [default: true]

  Note: "catalog_servicecategory — FK PROTECT"
}

Table Service {
  id                      int         [pk, increment]
  category_id             int         [ref: > ServiceCategory.id, not null]
  nombre                  varchar(100)[not null]
  descripcion             text
  tiempo_estimado_default int         [not null, note: "Horas"]
  activo                  bool        [default: true]
  created_at              timestamp   [default: `now()`]

  Note: "catalog_service — FK PROTECT"
}

Table HelpDesk {
  id                    int         [pk, increment]
  folio                 varchar(20) [unique, not null, note: "HD-XXXXXX autogenerado"]
  solicitante_id        int         [note: "Nullable — user_id del JWT, sin FK"]
  responsable_id        int         [note: "Nullable — user_id del JWT, sin FK"]
  service_id            int         [ref: > Service.id, not null]
  origen                varchar(20) [not null, note: "error|solicitud|consulta|mantenimiento"]
  prioridad             varchar(10) [not null, note: "baja|media|alta|critica"]
  estado                varchar(15) [not null, default: "abierto"]
  descripcion_problema  text        [not null]
  descripcion_solucion  text        [note: "Null hasta /resolve/"]
  fecha_asignacion      timestamp   [note: "Auto en /assign/"]
  fecha_compromiso      timestamp   [note: "Opcional, solo area_admin"]
  fecha_efectividad     timestamp   [note: "Auto en /resolve/"]
  tiempo_estimado       int         [not null, note: "Horas — hereda de service"]
  created_at            timestamp   [default: `now()`]
  updated_at            timestamp

  Note: "helpdesks_helpdesk — ordering: -created_at"
}

Table HDAttachment {
  id          int         [pk, increment]
  helpdesk_id int         [ref: > HelpDesk.id, not null]
  tipo        varchar(10) [not null, note: "archivo|url"]
  nombre      varchar(200)[not null]
  valor       text        [not null, note: "Ruta del archivo o URL externa"]
  created_at  timestamp   [default: `now()`]

  Note: "helpdesks_hdattachment — FK CASCADE"
}

Table HDComment {
  id          int       [pk, increment]
  helpdesk_id int       [ref: > HelpDesk.id, not null]
  autor_id    int       [note: "Nullable — user_id del JWT, sin FK"]
  contenido   text      [not null]
  es_interno  bool      [default: false, note: "Oculto para role=user"]
  created_at  timestamp [default: `now()`]

  Note: "helpdesks_hdcomment — FK CASCADE — ordering: created_at"
}
```
