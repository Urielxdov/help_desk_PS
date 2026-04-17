# SLA — Diseño de la app

## Posición en la arquitectura

```
catalog   → sin dependencias internas
helpdesks → catalog
sla       → helpdesks + catalog
```

`sla` conoce a `helpdesks` y `catalog` pero ninguna de las dos sabe de `sla`.
Esto evita dependencias circulares y mantiene el dominio de tickets limpio.

---

## Modelos

### TechnicianProfile
```
user_id     IntegerField (unique) — ID del sistema externo
department  FK → catalog.Department
active      BooleanField (default=True)
created_at  DateTimeField (auto)
```
Relaciona un usuario externo con un departamento. Gestionado por `area_admin` y `super_admin`.

---

### SLAConfig
```
department       FK → catalog.Department (null=True, unique=True)
max_load         PositiveIntegerField (default=3)

# Pesos de urgencia
score_overdue    IntegerField (default=1000)
score_company    IntegerField (default=100)
score_area       IntegerField (default=50)
score_individual IntegerField (default=10)
score_critical   IntegerField (default=40)
score_high       IntegerField (default=30)
score_medium     IntegerField (default=20)
score_low        IntegerField (default=10)
```

- `department=null` = configuración global (fallback).
- Si existe config por departamento, tiene precedencia sobre la global.
- `max_load` = máximo de HDs activos simultáneos por técnico.
- Gestionado por `area_admin` (solo su departamento) y `super_admin` (global + cualquier depto).

---

### ServiceQueue
```
help_desk      OneToOneField → helpdesks.HelpDesk
queued_at      DateTimeField (auto_now_add)
urgency_score  IntegerField
```
Un HD solo puede estar en cola una vez (OneToOne lo garantiza).

---

### Campo nuevo en HelpDesk (app helpdesks)
```
impact  CharField (individual | area | company, default='individual')
```
Define el impacto de negocio del ticket. Lo establece el `area_admin` al crear o asignar.

---

## Cálculo de urgency_score

Los pesos se leen del `SLAConfig` del departamento (fallback al global).

```
score = 0

if due_date and now > due_date:
    score += config.score_overdue

match impact:
    'company'    → score += config.score_company
    'area'       → score += config.score_area
    'individual' → score += config.score_individual

match priority:
    'critical' → score += config.score_critical
    'high'     → score += config.score_high
    'medium'   → score += config.score_medium
    'low'      → score += config.score_low
```

Vencido siempre gana cualquier combinación de impacto + prioridad.
Dentro del mismo rango: impacto > prioridad.
Tiebreak final: `queued_at` más antiguo.

---

## Flujo de auto-asignación

```
HD creado (post_save signal, created=True)
    │
    ▼
Celery task: auto_assign(hd_id)
    │
    ▼
Obtener departamento: hd.service.category.department
    │
    ▼
Obtener SLAConfig del departamento (fallback a global)
    │
    ▼
Filtrar TechnicianProfile activos del departamento
    │
    ▼
Para cada técnico:
    carga_count = HDs activos (open | in_progress | on_hold) donde assignee_id = user_id
    carga_horas = sum(estimated_hours) de esos HDs
    │
    ├── Hay técnicos con carga_count < max_load
    │       │
    │       ▼
    │   Elegir el de menor carga_horas (más fiel a la carga real)
    │       │
    │       ▼
    │   hd.assignee_id = tecnico.user_id
    │   hd.assigned_at = now()
    │   hd.status permanece 'open'
    │   (el técnico cambia a in_progress cuando inicia el trabajo)
    │
    └── Todos saturados (carga_count >= max_load)
            │
            ▼
        Calcular urgency_score
        Crear ServiceQueue(help_desk=hd, urgency_score=score)
        HD queda sin assignee_id
```

> Criterio de elegibilidad: `count < max_load`.
> Criterio de selección entre elegibles: menor suma de `estimated_hours` activas.

---

## Flujo de desencolar

```
HD resuelto o cerrado (al final de resolve() y close() en helpdesks/views.py)
    │
    ▼
Celery task: process_queue(department_id)
    │
    ▼
¿Hay HDs en cola para este departamento?
    │
    ├── No → termina
    │
    └── Sí
            │
            ▼
        Recalcular urgency_score de todos los HDs en cola del depto
        (algunos pueden haber vencido desde que se encolaron)
            │
            ▼
        Tomar el de mayor urgency_score
        Tiebreak: queued_at más antiguo
            │
            ▼
        Reiniciar auto_assign(hd_id)
        Si se asigna → eliminar de ServiceQueue
        Si sigue saturado → dejar en cola con score actualizado
```

---

## Tarea periódica (Celery Beat)

Frecuencia: cada 15 minutos.

1. Recorrer todos los HDs en `ServiceQueue`
2. Recalcular `urgency_score` (detecta tickets que se volvieron vencidos)
3. Intentar `process_queue` para departamentos con cola no vacía

Garantiza que un HD vencido suba al tope aunque nadie haya resuelto un ticket recientemente.

---

## Endpoints

| Método | Ruta | Permiso |
|---|---|---|
| GET/POST | `/api/technician-profiles/` | area_admin+ |
| GET/PUT/DELETE | `/api/technician-profiles/{id}/` | area_admin+ |
| GET/POST | `/api/sla-config/` | area_admin+ |
| GET/PUT | `/api/sla-config/{id}/` | area_admin+ |
| GET | `/api/service-queue/` | area_admin+ |

---

## Casos edge

| Caso | Comportamiento |
|---|---|
| Departamento sin técnicos | Va a cola, espera hasta que se agregue un técnico |
| Se agrega/activa técnico en depto | `post_save` en TechnicianProfile dispara `process_queue` |
| Técnico desactivado con HDs activos | Sus HDs quedan asignados (reasignación automática fuera de scope v1) |
| HD sin `due_date` | No puede vencer, score máximo sin overdue |
| `SLAConfig` inexistente | Usa defaults hardcodeados como último fallback |
| Dos HDs mismo score | Gana el de `queued_at` más antiguo (FIFO) |
| `impact` no definido al crear | Default `individual`, area_admin puede cambiar al asignar |
| `SLAConfig` modificado | El nuevo límite aplica a partir del siguiente intento de asignación |

---

## Infraestructura requerida

- **Celery** — worker de tareas asíncronas
- **Redis** — broker de mensajes para Celery (también sirve de backend de resultados)
- **Celery Beat** — scheduler para la tarea periódica de recálculo
