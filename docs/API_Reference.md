# Referencia de la API — Help Desk

Base URL: `http://localhost:8080/api` (configurada en `NEXT_PUBLIC_API_URL` del frontend)

Todas las rutas requieren el header:
```
Authorization: Bearer <jwt_token>
```
Excepto `POST /auth/token/`.

---

## Autenticacion

### POST /auth/token/

Genera un JWT de acceso.

**Permiso:** Publico (`AllowAny`)

**Body:**
```json
{
  "user_id": 5,
  "role": "technician"
}
```

**Roles validos:** `user` | `technician` | `area_admin` | `super_admin`

**Response 200:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5..."
}
```

---

## Departamentos

### GET /departments/

Lista todos los departamentos activos.

**Permiso:** `IsAuthenticated`

**Response 200:**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "nombre": "Infraestructura",
      "descripcion": "Servidores, redes y hardware",
      "activo": true,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### POST /departments/

Crea un nuevo departamento.

**Permiso:** `IsSuperAdmin`

**Body:**
```json
{
  "nombre": "Desarrollo",
  "descripcion": "Equipo de software",
  "activo": true
}
```

**Response 201:** Objeto `Department`

### GET /departments/{id}/

Detalle de un departamento.

**Permiso:** `IsAuthenticated`

### PUT /departments/{id}/

Actualiza un departamento.

**Permiso:** `IsSuperAdmin`

### PATCH /departments/{id}/

Actualiza parcialmente un departamento (p.ej. solo `activo`).

**Permiso:** `IsSuperAdmin`

### GET /departments/{id}/categories/

Lista las categorias activas de un departamento.

**Permiso:** `IsAuthenticated`

**Response 200:** Array de `ServiceCategory`
```json
[
  {
    "id": 1,
    "nombre": "Hardware",
    "department": 1,
    "department_nombre": "Infraestructura",
    "activo": true
  }
]
```

### GET /departments/{id}/services/

Lista todos los servicios activos de un departamento (de todas sus categorias).

**Permiso:** `IsAuthenticated`

**Response 200:** Array de `Service`

---

## Categorias de Servicio

### POST /service-categories/

Crea una nueva categoria.

**Permiso:** `IsAreaAdmin`

**Body:**
```json
{
  "nombre": "Conectividad",
  "department": 1
}
```

**Validaciones:**
- El departamento referenciado debe estar activo

**Response 201:** Objeto `ServiceCategory`

### GET /service-categories/{id}/

Detalle de una categoria.

**Permiso:** `IsAreaAdmin`

### PUT /service-categories/{id}/

Actualiza una categoria.

**Permiso:** `IsAreaAdmin`

**Body:**
```json
{
  "nombre": "Conectividad y Redes",
  "department": 1
}
```

### PATCH /service-categories/{id}/

Actualizacion parcial de una categoria.

**Permiso:** `IsAreaAdmin`

### GET /service-categories/{id}/services/

Lista los servicios activos de una categoria.

**Permiso:** `IsAuthenticated`

**Response 200:** Array de `Service`

---

## Servicios

### POST /services/

Crea un nuevo servicio.

**Permiso:** `IsAreaAdmin`

**Body:**
```json
{
  "nombre": "Cambio de teclado",
  "descripcion": "Reemplazo de teclado fisico",
  "category": 1,
  "tiempo_estimado_default": 2
}
```

**Validaciones:**
- La categoria referenciada debe estar activa

**Response 201:** Objeto `Service`

### GET /services/{id}/

Detalle de un servicio.

**Permiso:** `IsAreaAdmin`

### PUT /services/{id}/

Actualiza un servicio.

**Permiso:** `IsAreaAdmin`

### PATCH /services/{id}/

Actualizacion parcial de un servicio.

**Permiso:** `IsAreaAdmin`

### PATCH /services/{id}/toggle/

Activa o desactiva un servicio (invierte el flag `activo`).

**Permiso:** `IsAreaAdmin`

**Body:** Vacio `{}`

**Response 200:** Objeto `Service` con el nuevo estado de `activo`

**Nota:** Este es el unico mecanismo de eliminacion para servicios — sin DELETE fisico.

---

## Help Desks (Tickets)

### GET /helpdesks/

Lista tickets segun el rol del usuario autenticado.

**Permiso:** `IsAuthenticated`

**Visibilidad por rol:**

| Rol | Ve |
|---|---|
| `user` | Solo sus propios tickets (`solicitante_id`) |
| `technician` | Solo los tickets asignados a el (`responsable_id`) |
| `area_admin` | Todos los tickets |
| `super_admin` | Todos los tickets |

**Query params (filtros):**
- `estado` — `abierto` | `en_progreso` | `en_espera` | `resuelto` | `cerrado`
- `prioridad` — `baja` | `media` | `alta` | `critica`
- `service` — ID del servicio
- `responsable_id` — ID del tecnico asignado

**Ejemplo:** `GET /helpdesks/?estado=abierto&prioridad=alta`

**Response 200:**
```json
{
  "count": 12,
  "next": "http://localhost:8080/api/helpdesks/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "folio": "HD-000001",
      "solicitante_id": 5,
      "responsable_id": null,
      "service": 3,
      "service_nombre": "Cambio de teclado",
      "origen": "solicitud",
      "prioridad": "media",
      "estado": "abierto",
      "descripcion_problema": "Mi teclado no funciona",
      "descripcion_solucion": null,
      "fecha_asignacion": null,
      "fecha_compromiso": null,
      "fecha_efectividad": null,
      "tiempo_estimado": 2,
      "attachments": [],
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### POST /helpdesks/

Crea un nuevo ticket.

**Permiso:** `IsAuthenticated`

**Body:**
```json
{
  "service": 3,
  "origen": "solicitud",
  "prioridad": "media",
  "descripcion_problema": "Mi teclado no funciona desde hoy"
}
```

**Campos opcionales:**
- `tiempo_estimado` — si se omite, se hereda de `service.tiempo_estimado_default`

**Campos calculados automaticamente (no enviar):**
- `solicitante_id` — tomado de `request.user.user_id`
- `estado` — fijado en `abierto`
- `folio` — generado automaticamente (`HD-XXXXXX`)

**Response 201:** Objeto `HelpDesk` completo

**Errores comunes:**
```json
{ "error": "Este campo es requerido.", "code": "ValidationError" }
```

### GET /helpdesks/{id}/

Detalle de un ticket.

**Permiso:** `IsAuthenticated` (con visibilidad por rol igual que en list)

**Response 200:** Objeto `HelpDesk` completo con `attachments` anidados

### PATCH /helpdesks/{id}/status/

Cambia el estado de un ticket.

**Permiso:** `IsTechnicianOrAdmin`

**Body:**
```json
{
  "estado": "en_progreso"
}
```

**Transiciones validas:**

| Estado actual | Puede cambiar a |
|---|---|
| `abierto` | `en_progreso` |
| `en_progreso` | `en_espera`, `resuelto` |
| `en_espera` | `en_progreso`, `resuelto` |
| `resuelto` | `cerrado` |
| `cerrado` | — (estado terminal) |

**Response 200:** Objeto `HelpDesk` actualizado

**Error de transicion invalida (400):**
```json
{
  "error": "Transicion invalida: abierto → cerrado",
  "code": "ValidationError"
}
```

### PATCH /helpdesks/{id}/assign/

Asigna un tecnico al ticket.

**Permiso:** `IsAreaAdmin`

**Body:**
```json
{
  "responsable_id": 42,
  "fecha_compromiso": "2024-02-01T17:00:00Z"
}
```

**Campos opcionales:**
- `fecha_compromiso` — si se omite, no se modifica

**Campos calculados automaticamente:**
- `fecha_asignacion` — se establece a `timezone.now()`

**Response 200:** Objeto `HelpDesk` actualizado

### PATCH /helpdesks/{id}/resolve/

Resuelve un ticket. Requiere que el estado sea `en_progreso` o `en_espera`.

**Permiso:** `IsTechnicianOrAdmin`

**Body:**
```json
{
  "descripcion_solucion": "Se reemplazo el teclado por uno nuevo. Quedo funcionando correctamente."
}
```

**Campos calculados automaticamente:**
- `estado` — cambia a `resuelto`
- `fecha_efectividad` — se establece a `timezone.now()`

**Response 200:** Objeto `HelpDesk` actualizado

**Errores (400):**
```json
{ "error": "descripcion_solucion no puede estar vacia.", "code": "ValidationError" }
{ "error": "El ticket debe estar en progreso o en espera para resolver.", "code": "ValidationError" }
```

---

## Adjuntos

### POST /helpdesks/{helpdesk_pk}/attachments/

Agrega un adjunto al ticket. Soporta dos modalidades.

**Permiso:** `IsAuthenticated`

#### Modalidad archivo (multipart/form-data)
```
tipo=archivo
nombre=Foto del teclado
archivo=<file binary>
```
- Tamano maximo: **10 MB**
- El archivo se guarda en el almacenamiento configurado (`storage.py`)

#### Modalidad URL (application/json)
```json
{
  "tipo": "url",
  "nombre": "Video del problema",
  "valor": "https://drive.google.com/file/..."
}
```

**Response 201:**
```json
{
  "id": 7,
  "tipo": "archivo",
  "nombre": "Foto del teclado",
  "valor": "/media/helpdesks/1/foto_teclado.jpg",
  "created_at": "2024-01-15T11:00:00Z"
}
```

### DELETE /helpdesks/{helpdesk_pk}/attachments/{pk}/

Elimina un adjunto.

**Permiso:** `IsAuthenticated`

- Si `tipo=archivo`: elimina el archivo fisico del almacenamiento
- Si `tipo=url`: solo elimina el registro en DB

**Response 204:** Sin contenido

---

## Comentarios

### GET /helpdesks/{helpdesk_pk}/comments/

Lista los comentarios de un ticket.

**Permiso:** `IsAuthenticated`

**Visibilidad:**
- `user` — no ve comentarios con `es_interno=True`
- `technician`, `area_admin`, `super_admin` — ven todos

**Sin paginacion** — devuelve todos los comentarios ordenados por `created_at` ASC.

**Response 200:**
```json
[
  {
    "id": 1,
    "autor_id": 5,
    "contenido": "Buenos dias, el teclado dejo de funcionar de repente.",
    "es_interno": false,
    "created_at": "2024-01-15T10:05:00Z"
  },
  {
    "id": 2,
    "autor_id": 42,
    "contenido": "Nota interna: el usuario tiene historial de problemas con este equipo.",
    "es_interno": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### POST /helpdesks/{helpdesk_pk}/comments/

Agrega un comentario al ticket.

**Permiso:** `IsAuthenticated`

**Body:**
```json
{
  "contenido": "El equipo lleva 3 anos en uso.",
  "es_interno": false
}
```

**Campos calculados automaticamente:**
- `autor_id` — tomado de `request.user.user_id`

**Response 201:**
```json
{
  "id": 3,
  "autor_id": 5,
  "contenido": "El equipo lleva 3 anos en uso.",
  "es_interno": false,
  "created_at": "2024-01-15T10:45:00Z"
}
```

---

## Codigos de Error Comunes

| Status | Significado | Cuando ocurre |
|---|---|---|
| 400 | Bad Request | Validacion fallida, transicion invalida, campo faltante |
| 401 | Unauthorized | Sin token, token invalido o expirado |
| 403 | Forbidden | Rol sin permiso para la accion |
| 404 | Not Found | Recurso no existe o no visible para el rol |
| 413 | Payload Too Large | Archivo mayor a 10 MB |
| 500 | Internal Server Error | Error no manejado en el servidor |

**Formato unificado de error:**
```json
{
  "error": "Descripcion legible del error",
  "code": "NombreDeExcepcion"
}
```
