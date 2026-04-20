# SLA y Clasificador Automático

Documentación detallada de los módulos `sla/` y `classifier/`.

## Tabla de Contenidos

- [SLA — Auto-asignación](#sla--auto-asignación)
- [Classifier — Clasificación de Servicios](#classifier--clasificación-de-servicios)
- [Configuración por Departamento](#configuración-por-departamento)
- [Celery Tasks y Schedule](#celery-tasks-y-schedule)
- [Ejemplos de Uso](#ejemplos-de-uso)

---

## SLA — Auto-asignación

El módulo SLA automatiza la asignación de tickets a técnicos respetando:
1. **Disponibilidad**: máximo de tickets simultáneos por técnico
2. **Horario hábil**: solo asigna dentro de 08:30-18:00 Lun-Vie
3. **Urgencia**: cola priorizada por fecha de vencimiento, impacto y prioridad
4. **Carga actual**: considera horas acumuladas en tickets activos

---

### Flujo de Asignación Automática

```
1. Ticket creado (POST /api/helpdesks/)
    ↓
2. Signal: post_save(HelpDesk, created=True)
    ↓
3. Celery task: auto_assign_helpdesk(hd_id)
    ├─ if NOT is_business_hours():
    │   └─ enqueue(hd) — va a la cola
    │
    └─ if is_business_hours():
        ├─ Obtiene SLAConfig del departamento
        ├─ Filtra técnicos activos en ese departamento
        ├─ Para cada técnico: cuenta tickets activos
        ├─ Si alguno tiene active_count < max_load:
        │   ├─ Elige al de menor carga acumulada (estimated_hours)
        │   ├─ assign → due_date calculado automáticamente
        │   └─ save()
        └─ Si todos en max_load:
            └─ enqueue(hd) con urgency_score calculado
```

---

### Cálculo de Due Date

Según la configuración de `resolution_time` y `resolution_unit` en `SLAConfig`:

#### business_hours (horas hábiles)
```
due_date = add_business_hours(assigned_at, accumulated_hours + resolution_time)
```
Ejemplo: técnico con 20 horas acumuladas, resolution_time=72
- Due date = assigned_at + (20 + 72) horas hábiles
- Si se asigna a las 17:00 lunes:
  - 1 hora restante lunes (17:00 → 18:00)
  - Faltan 91 horas
  - Lunes-viernes = 9.5 hrs/día × 9 días = 85.5 hrs
  - Sobran 5.5 hrs el viernes siguiente
  - Due date = viernes 14:00

#### calendar_hours (horas calendario)
```
due_date = assigned_at + timedelta(hours=resolution_time)
```
Simple suma de horas, sin considerar horario hábil.

#### calendar_days (días calendario)
```
due_date = assigned_at + timedelta(days=resolution_time)
```
Suma de días naturales (incluye fines de semana).

---

### Cálculo de Urgency Score

Cuando un ticket entra a la cola:

```
score = 0

if due_date < now:
    score += score_overdue  (default 1000)

match impact:
    'company'     → score += score_company (default 100)
    'area'        → score += score_area (default 50)
    'individual'  → score += score_individual (default 10)

match priority:
    'critical'    → score += score_critical (default 40)
    'high'        → score += score_high (default 30)
    'medium'      → score += score_medium (default 20)
    'low'         → score += score_low (default 10)
```

**Ranking de cola:**
```
ORDER BY -urgency_score, queued_at
```
Vencidos primero, empate por FIFO.

---

### Desencola Automática

Cuando un ticket se resuelve o cierra:

```
1. Signal: post_save(HelpDesk, status='resolved' or 'closed')
    ↓
2. Celery task: process_department_queue(department_id)
    ├─ Recalcula urgency_score de TODOS los tickets en la cola
    │  (algunos pueden haberse vencido)
    ├─ Ordena por -urgency_score, queued_at
    └─ Intenta asignar cada uno:
        └─ if try_assign(ticket):
            └─ delete queue_entry
        else:
            └─ break (todos siguen saturados)
```

---

### Horario Hábil

Definido en `config/business_hours.py`:
```
BUSINESS_START = time(8, 30)
BUSINESS_END = time(18, 0)
BUSINESS_HOURS_PER_DAY = 9.5  # 08:30 a 18:00 = 9.5 horas
```

**Validaciones:**
- `is_business_hours()` → checks if lunes-viernes y 08:30 ≤ ahora < 18:00
- `add_business_hours(start, hours)` → suma horas solo en días hábiles
- `next_business_start(dt)` → siguiente 08:30 hábil desde dt

---

## Classifier — Clasificación de Servicios

El módulo Classifier aprende qué servicios corresponden a qué problemas, basándose en histórico de keywords y feedback del usuario.

---

### Flujo de Clasificación

```
1. Usuario escribe su problema
    ↓
2. POST /api/classify/ { "text": "..." }
    ↓
3. classify(text) en services.py
    ├─ Obtiene todos los ServiceKeyword activos
    ├─ Por cada keyword:
    │   if keyword in text.lower():
    │       score[service] += weight
    ├─ Filtra score ≥ MIN_SCORE (default 1)
    ├─ Ordena por -score
    └─ Devuelve top TOP_N (default 3) con details
    ↓
4. Response con sugerencias:
    {
        "suggestions": [
            {
                "service_id": 3,
                "service_name": "...",
                "category_id": 2,
                "category_name": "...",
                "department_id": 1,
                "department_name": "...",
                "score": 7
            }
        ]
    }
    ↓
5a. Usuario acepta → crea ticket con ese servicio
    ↓
5b. Usuario rechaza → navega el catálogo y elige otro
    ↓
6. POST /api/classify/feedback/ { 
       "suggested_service": 3,
       "chosen_service": (3 o 5),
       "accepted": (true o false)
    }
```

---

### Ajuste Automático de Pesos (Entrenamiento)

El sistema aprende de la retroalimentación:

#### Si el usuario ACEPTA la sugerencia
```
Para cada keyword en ServiceKeyword que matcheó el texto:
    weight = min(weight + WEIGHT_INCREMENT, MAX_WEIGHT)  # default +1, max 10
    save()
```

#### Si el usuario RECHAZA la sugerencia
```
Para cada keyword del servicio SUGERIDO que matcheó:
    if weight - WEIGHT_DECREMENT < MIN_WEIGHT:
        delete()  # eliminar keyword débil
    else:
        weight -= WEIGHT_DECREMENT  # bajar weight
        save()

Extrae palabras nuevas del texto (>3 caracteres, sin stopwords):
    para cada palabra nueva no ya presente en el servicio ELEGIDO:
        create ServiceKeyword(service=chosen, keyword=palabra, weight=1)
```

#### Si NO hubo sugerencia (score=0)
```
El usuario elige manualmente → extrae palabras nuevas para ese servicio
Esto es APRENDIZAJE PROGRESIVO — el sistema aprende casos sin matches
```

---

### Entrenamiento Automático

**Schedule:** Celery Beat a las 2:00 AM diariamente

```python
'train-classifier': {
    'task': 'apps.classifier.tasks.train_classifier',
    'schedule': crontab(hour=2, minute=0),
}
```

**Proceso:**
```
1. Busca todos ClassificationFeedback con trained=False
2. Para cada uno: _adjust_weights(feedback)
3. feedback.trained = True
4. save()
```

También se puede disparar manualmente:
```
POST /api/classify/train/  (area_admin)
→ { "detail": "Entrenamiento encolado." }
```

---

### Stopwords

Palabras ignoradas al extraer candidatos (en `training.py`):

```python
STOPWORDS = {
    'de', 'la', 'el', 'en', 'y', 'a', 'que', 'es', 'se', 'no', 'un', 'una',
    'los', 'las', 'del', 'al', 'lo', 'por', 'con', 'para', 'su', 'me', 'mi',
    'te', 'le', 'nos', 'les', 'pero', 'si', 'ya', 'hay', 'fue', 'ser',
    'como', 'más', 'este', 'esta', 'esto', 'porque', 'cuando', 'muy', 'sin',
    'sobre', 'entre', 'has', 'the', 'and', 'or', 'not', 'can',
}
```

Solo se crean keywords con palabras > 3 caracteres fuera de esta lista.

---

## Configuración por Departamento

### SLAConfig

```
POST /api/sla-config/
{
    "department": 1,              # null = global config
    "max_load": 3,                # máx. tickets por técnico
    "resolution_time": 72,        # tiempo máximo
    "resolution_unit": "business_hours",  # o "calendar_hours", "calendar_days"
    "score_overdue": 1000,        # vencido
    "score_company": 100,         # impacto empresa
    "score_area": 50,             # impacto área
    "score_individual": 10,       # impacto individual
    "score_critical": 40,         # prioridad crítica
    "score_high": 30,
    "score_medium": 20,
    "score_low": 10
}
```

**Fallback:**
1. Primero busca SLAConfig para ese departamento específico
2. Si no existe, busca SLAConfig global (department=null)
3. Si tampoco existe, usa defaults hardcodeados en `_DEFAULT_CONFIG`

---

### Service Keywords

```
POST /api/service-keywords/
{
    "service": 3,          # ID del servicio
    "keyword": "impresora",
    "weight": 2
}
```

Weight rango: 1-10 (default 1)

Se guarda en minúsculas automáticamente.

Búsqueda es **case-insensitive substring match**:
```
if "impresora" in "mi IMPRESORA no funciona".lower():  # match!
```

---

## Celery Tasks y Schedule

### Auto-asignación (reactiva)

```python
auto_assign_helpdesk(hd_id)  # se dispara en post_save(HelpDesk, created=True)
```

### Desencola (reactiva)

```python
process_department_queue(department_id)  # se dispara en post_save(HelpDesk) cuando status cambia a 'resolved' o 'closed'
```

### Recalcula urgency scores (periódica)

```python
'recalculate-queue-scores': {
    'task': 'apps.sla.tasks.recalculate_queue_scores',
    'schedule': 900,  # cada 15 minutos
}
```
Recalcula puntajes de TODOS los tickets encolados en TODOS los departamentos.
Sirve para que tickets que se vencen suban automáticamente sin esperar a que alguien resuelva un ticket.

### Procesa cola al inicio del día hábil (periódica)

```python
'process-queue-business-start': {
    'task': 'apps.sla.tasks.process_all_queues',
    'schedule': crontab(hour=8, minute=30, day_of_week='1-5'),  # Lun-Vie 08:30
}
```
Desencola todos los tickets que quedaron esperando desde el viernes o fin de semana.

### Entrena el clasificador (periódica)

```python
'train-classifier': {
    'task': 'apps.classifier.tasks.train_classifier',
    'schedule': crontab(hour=2, minute=0),  # Diario a las 2:00 AM
}
```

---

## Ejemplos de Uso

### 1. Crear SLAConfig para TI (72 horas hábiles)

```bash
curl -X POST http://localhost:8000/api/sla-config/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "department": 1,
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
  }'
```

### 2. Crear técnico

```bash
curl -X POST http://localhost:8000/api/technician-profiles/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "department": 1,
    "active": true
  }'
```

### 3. Agregar keywords para un servicio

```bash
curl -X POST http://localhost:8000/api/service-keywords/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "service": 3,
    "keyword": "contraseña",
    "weight": 3
  }'

curl -X POST http://localhost:8000/api/service-keywords/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "service": 3,
    "keyword": "usuario bloqueado",
    "weight": 2
  }'
```

### 4. Clasificar un problema

```bash
curl -X POST http://localhost:8000/api/classify/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "No puedo entrar al sistema, mi contraseña no funciona"
  }'
```

Respuesta:
```json
{
  "suggestions": [
    {
      "service_id": 3,
      "service_name": "Reset de contraseña",
      "category_id": 2,
      "category_name": "Accesos",
      "department_id": 1,
      "department_name": "TI",
      "score": 5
    }
  ]
}
```

### 5. Crear ticket aceptando la sugerencia

```bash
curl -X POST http://localhost:8000/api/helpdesks/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "service": 3,
    "origin": "error",
    "priority": "high",
    "problem_description": "No puedo entrar al sistema, mi contraseña no funciona"
  }'
```

### 6. Guardar feedback

```bash
curl -X POST http://localhost:8000/api/classify/feedback/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_description": "No puedo entrar...",
    "suggested_service": 3,
    "chosen_service": 3,
    "accepted": true
  }'
```

### 7. Ver estadísticas del clasificador

```bash
curl -X GET http://localhost:8000/api/classify/stats/ \
  -H "Authorization: Bearer <token>"
```

Respuesta:
```json
{
  "total_feedback": 150,
  "accepted": 120,
  "rejected": 30,
  "acceptance_rate": 80.0,
  "pending_training": 5
}
```

### 8. Disparar entrenamiento manual

```bash
curl -X POST http://localhost:8000/api/classify/train/ \
  -H "Authorization: Bearer <token>"
```

---

## Troubleshooting

**Problema:** Tickets creados a las 19:00 no se asignan.
**Solución:** Está fuera de horario hábil (08:30-18:00). Van a la cola automáticamente. Al día siguiente a las 08:30, Celery Beat los desencola.

**Problema:** El clasificador nunca sugiere servicios.
**Solución:** No hay keywords registrados. Crea keywords vía `/api/service-keywords/` o ejecuta script de TF-IDF sobre tickets históricos.

**Problema:** Feedback guardados pero no reentrenados.
**Solución:** El entrenamiento corre a las 2:00 AM. O dispara manualmente con `POST /api/classify/train/`.

**Problema:** Todos los técnicos tienen max_load tickets.
**Solución:** Nuevos tickets entran a la cola. Se desencolan cuando alguno se resuelve.
