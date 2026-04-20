# Endpoints SLA y Classifier

Referencia completa de endpoints relacionados a asignación automática y clasificación.

## Base URL

```
http://localhost:8000/api
```

---

## SLA — Perfiles de Técnicos

### GET /technician-profiles/

Lista todos los perfiles de técnico del departamento.

**Permiso:** `IsAreaAdmin`

**Query params:**
- `department`: filtrar por departamento (opcional)

**Response 200:**
```json
[
  {
    "id": 1,
    "user_id": 42,
    "department": 1,
    "department_name": "TI",
    "active": true,
    "created_at": "2026-04-20T10:30:00Z"
  }
]
```

---

### POST /technician-profiles/

Crea un nuevo perfil de técnico.

**Permiso:** `IsAreaAdmin`

**Body:**
```json
{
  "user_id": 42,
  "department": 1,
  "active": true
}
```

**Response 201:**
```json
{
  "id": 1,
  "user_id": 42,
  "department": 1,
  "department_name": "TI",
  "active": true,
  "created_at": "2026-04-20T10:30:00Z"
}
```

---

### GET /technician-profiles/{id}/

Obtiene un perfil de técnico específico.

**Permiso:** `IsAreaAdmin`

**Response 200:**
```json
{
  "id": 1,
  "user_id": 42,
  "department": 1,
  "department_name": "TI",
  "active": true,
  "created_at": "2026-04-20T10:30:00Z"
}
```

---

### PUT /technician-profiles/{id}/

Actualiza un perfil de técnico.

**Permiso:** `IsAreaAdmin`

**Body:**
```json
{
  "user_id": 42,
  "department": 1,
  "active": false
}
```

**Response 200:**
```json
{
  "id": 1,
  "user_id": 42,
  "department": 1,
  "department_name": "TI",
  "active": false,
  "created_at": "2026-04-20T10:30:00Z"
}
```

---

### DELETE /technician-profiles/{id}/

Elimina un perfil de técnico.

**Permiso:** `IsAreaAdmin`

**Response 204:** (sin contenido)

---

## SLA — Configuración

### GET /sla-config/

Lista todas las configuraciones SLA (por departamento y global).

**Permiso:** `IsAreaAdmin`

**Response 200:**
```json
[
  {
    "id": 1,
    "department": 1,
    "department_name": "TI",
    "max_load": 3,
    "resolution_time": 72,
    "resolution_unit": "business_hours",
    "score_overdue": 1000,
    "score_company": 100,
    "score_area": 50,
    "score_individual": 10,
    "score_critical": 40,
    "score_high": 30,
    "score_medium": 20,
    "score_low": 10
  },
  {
    "id": 2,
    "department": null,
    "department_name": "Global",
    "max_load": 3,
    "resolution_time": 72,
    "resolution_unit": "business_hours",
    ...
  }
]
```

---

### POST /sla-config/

Crea una nueva configuración SLA (departamental o global).

**Permiso:** `IsAreaAdmin`

**Body:**
```json
{
  "department": 1,
  "max_load": 5,
  "resolution_time": 24,
  "resolution_unit": "calendar_hours",
  "score_overdue": 1000,
  "score_company": 100,
  "score_area": 50,
  "score_individual": 10,
  "score_critical": 40,
  "score_high": 30,
  "score_medium": 20,
  "score_low": 10
}
```

`department` puede ser `null` para crear config global.

**Response 201:**
```json
{
  "id": 1,
  "department": 1,
  "department_name": "TI",
  "max_load": 5,
  "resolution_time": 24,
  "resolution_unit": "calendar_hours",
  ...
}
```

---

### GET /sla-config/{id}/

Obtiene una configuración SLA específica.

**Permiso:** `IsAreaAdmin`

**Response 200:**
```json
{
  "id": 1,
  "department": 1,
  "department_name": "TI",
  "max_load": 5,
  "resolution_time": 24,
  "resolution_unit": "calendar_hours",
  ...
}
```

---

### PUT /sla-config/{id}/

Actualiza una configuración SLA.

**Permiso:** `IsAreaAdmin`

**Body:** (todos los campos opcionales)
```json
{
  "max_load": 3,
  "resolution_time": 72,
  "resolution_unit": "business_hours"
}
```

**Response 200:**
```json
{
  "id": 1,
  ...
}
```

---

## SLA — Cola de Servicios

### GET /service-queue/

Lista todos los tickets encolados (en espera de asignación).

**Permiso:** `IsAreaAdmin`

**Query params:**
- `department`: filtrar por departamento (opcional)

**Response 200:**
```json
[
  {
    "id": 1,
    "folio": "HD-000001",
    "priority": "critical",
    "impact": "company",
    "department": "TI",
    "due_date": "2026-04-25T10:00:00Z",
    "urgency_score": 1170,
    "queued_at": "2026-04-20T10:30:00Z"
  }
]
```

---

## Classifier — Clasificación

### POST /classify/

Clasifica un texto y devuelve los servicios más probables.

**Permiso:** `IsAuthenticated`

**Body:**
```json
{
  "text": "mi impresora no funciona"
}
```

**Response 200:**
```json
{
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
    {
      "service_id": 5,
      "service_name": "Mantenimiento",
      "category_id": 3,
      "category_name": "Preventivo",
      "department_id": 1,
      "department_name": "TI",
      "score": 2
    }
  ]
}
```

Si no hay coincidencias con `score >= MIN_SCORE`:
```json
{
  "suggestions": []
}
```

---

### POST /classify/feedback/

Guarda la retroalimentación del usuario sobre la clasificación.

**Permiso:** `IsAuthenticated`

**Body:**
```json
{
  "problem_description": "mi impresora no funciona",
  "suggested_service": 3,
  "chosen_service": 3,
  "accepted": true
}
```

- `suggested_service`: ID del servicio sugerido por el sistema (puede ser `null` si no hubo sugerencia)
- `chosen_service`: ID del servicio que el usuario eligió finalmente
- `accepted`: `true` si el usuario aceptó la sugerencia, `false` si la cambió

**Response 201:**
```json
{
  "id": 1,
  "problem_description": "mi impresora no funciona",
  "suggested_service": 3,
  "chosen_service": 3,
  "accepted": true,
  "created_at": "2026-04-20T10:30:00Z"
}
```

**Validaciones:**
- Si `accepted=true`, `suggested_service` no puede ser `null`
- Si `chosen_service == suggested_service`, `accepted` debe ser `true`

---

### GET /classify/stats/

Obtiene estadísticas de clasificación y entrenamiento.

**Permiso:** `IsAreaAdmin`

**Response 200:**
```json
{
  "total_feedback": 150,
  "accepted": 120,
  "rejected": 30,
  "acceptance_rate": 80.0,
  "pending_training": 5
}
```

---

### POST /classify/train/

Dispara el entrenamiento manual del clasificador.

**Permiso:** `IsAreaAdmin`

**Body:** (vacío)

**Response 200:**
```json
{
  "detail": "Entrenamiento encolado."
}
```

El entrenamiento corre asincronamente en Celery. Ver `pending_training` en `/classify/stats/` para saber si hay trabajo pendiente.

---

## Classifier — Keywords

### GET /service-keywords/

Lista todos los keywords registrados.

**Permiso:** `IsAreaAdmin`

**Query params:**
- `service`: filtrar por servicio (opcional)

**Response 200:**
```json
[
  {
    "id": 1,
    "service": 3,
    "service_name": "Reset de contraseña",
    "keyword": "contraseña",
    "weight": 3,
    "created_at": "2026-04-20T10:00:00Z"
  },
  {
    "id": 2,
    "service": 3,
    "service_name": "Reset de contraseña",
    "keyword": "usuario bloqueado",
    "weight": 2,
    "created_at": "2026-04-20T10:05:00Z"
  }
]
```

---

### POST /service-keywords/

Crea un nuevo keyword para un servicio.

**Permiso:** `IsAreaAdmin`

**Body:**
```json
{
  "service": 3,
  "keyword": "contraseña olvidada",
  "weight": 2
}
```

**Response 201:**
```json
{
  "id": 3,
  "service": 3,
  "service_name": "Reset de contraseña",
  "keyword": "contraseña olvidada",
  "weight": 2,
  "created_at": "2026-04-20T10:30:00Z"
}
```

**Notas:**
- El keyword se guarda en minúsculas automáticamente
- `weight` rango: 1-10 (default 1)
- Unique constraint: un keyword no puede estar 2 veces para el mismo servicio

---

### DELETE /service-keywords/{id}/

Elimina un keyword.

**Permiso:** `IsAreaAdmin`

**Response 204:** (sin contenido)

---

## Utilidad — Choices

### GET /choices/

Devuelve los valores posibles para dropdowns de tickets.

**Permiso:** `IsAuthenticated`

**Response 200:**
```json
{
  "impact": [
    "individual",
    "area",
    "company"
  ],
  "priority": [
    "low",
    "medium",
    "high",
    "critical"
  ],
  "origin": [
    "error",
    "request",
    "inquiry",
    "maintenance"
  ],
  "status": [
    "open",
    "in_progress",
    "on_hold",
    "resolved",
    "closed"
  ]
}
```

---

## Errores Comunes

### 400 — Bad Request
```json
{
  "error": "Validation error",
  "code": "ValidationError"
}
```
Revisar el body según la documentación del endpoint.

### 401 — Unauthorized
```json
{
  "error": "Invalid or missing token",
  "code": "AuthenticationFailed"
}
```
Verificar header `Authorization: Bearer <token>`.

### 403 — Forbidden
```json
{
  "error": "Permission denied",
  "code": "PermissionDenied"
}
```
El rol del usuario no tiene acceso a este endpoint.

### 404 — Not Found
```json
{
  "error": "Not found",
  "code": "NotFound"
}
```
El recurso no existe o fue eliminado.
