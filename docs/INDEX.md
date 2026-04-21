# Documentación Help Desk API

Guía completa del backend Help Desk con asignación automática y clasificación inteligente.

## Documentos

### 1. [readme.md](./readme.md)
Arquitectura general del proyecto, principios clave, estructura de apps, autenticación y flujos principales.
- Principios arquitectónicos
- Estructura del proyecto
- Apps de dominio (catalog, helpdesks, sla, classifier)
- Autenticación JWT
- Permisos por rol
- Flujos de datos básicos
- Reglas de negocio

**Para:** Entender la arquitectura global y cómo encajan los componentes.

---

### 2. [SLA_and_Classifier.md](./SLA_and_Classifier.md)
Documentación detallada de los módulos SLA y Classifier.
- Flujo de auto-asignación de tickets
- Cálculo de due_date según configuración
- Urgency scoring y ranking de cola
- Horario hábil (08:30-18:00 Lun-Vie)
- Clasificación automática de servicios
- Ajuste de pesos basado en feedback
- Entrenamiento automático
- Ejemplos de uso

**Para:** Entender cómo funcionan la auto-asignación y el aprendizaje del clasificador.

---

### 3. [Endpoints_SLA_Classifier.md](./Endpoints_SLA_Classifier.md)
Referencia completa de endpoints SLA y Classifier.
- GET/POST /technician-profiles/
- GET/POST /sla-config/
- GET /service-queue/
- POST /classify/
- POST /classify/feedback/
- GET /classify/stats/
- POST /classify/train/
- GET/POST /service-keywords/
- GET /choices/

**Para:** Integrar los endpoints desde el frontend.

---

### 4. [API_Reference.md](./API_Reference.md)
Referencia general de endpoints de catalog y helpdesks.
- Autenticación
- Departamentos, Categorías, Servicios
- Tickets (crear, listar, cambiar estado)
- Asignación manual de técnicos
- Resolución de tickets
- Comentarios y adjuntos

**Para:** Operaciones básicas de tickets y catálogo.

---

### 5. [Architecture.md](./Architecture.md)
Documentación arquitectónica detallada del sistema anterior.

---

## Guía Rápida

### Setup

```bash
# Instalar dependencias
pip install -r requirements.txt

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Servidor de desarrollo
python manage.py runserver

# Docker (recomendado)
docker compose up
```

---

### Configuración Inicial

#### 1. Crear un departamento
```bash
POST /api/departments/
{
  "name": "TI",
  "description": "Soporte técnico",
  "active": true
}
```

#### 2. Crear categoría de servicios
```bash
POST /api/service-categories/
{
  "name": "Accesos",
  "department": 1,
  "active": true
}
```

#### 3. Crear servicio
```bash
POST /api/services/
{
  "name": "Reset de contraseña",
  "description": "Resetear contraseña de usuario",
  "category": 1,
  "estimated_hours": 1,
  "impact": "individual",
  "client_close": true,
  "active": true
}
```

#### 4. Crear SLAConfig para el departamento
```bash
POST /api/sla-config/
{
  "department": 1,
  "max_load": 3,
  "resolution_time": 24,
  "resolution_unit": "business_hours",
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

#### 5. Crear técnicos
```bash
POST /api/technician-profiles/
{
  "user_id": 42,
  "department": 1,
  "active": true
}
```

#### 6. Agregar keywords para clasificación
```bash
POST /api/service-keywords/
{
  "service": 1,
  "keyword": "contraseña",
  "weight": 3
}

POST /api/service-keywords/
{
  "service": 1,
  "keyword": "usuario bloqueado",
  "weight": 2
}
```

---

### Flujo de Usuario

#### Usuario (requester)

1. **Obtener opciones de servicios**
   ```bash
   GET /api/departments/
   GET /api/departments/{id}/categories/
   GET /api/departments/{id}/categories/{cid}/services/
   ```

2. **Clasificar problema (opcional)**
   ```bash
   POST /api/classify/
   {"text": "mi contraseña no funciona"}
   ```
   Recibe sugerencias con departamento, categoría y servicio.

3. **Crear ticket**
   ```bash
   POST /api/helpdesks/
   {
     "service": 1,
     "origin": "error",
     "priority": "high",
     "problem_description": "mi contraseña no funciona"
   }
   ```

4. **Guardar feedback si clasificó**
   ```bash
   POST /api/classify/feedback/
   {
     "problem_description": "mi contraseña...",
     "suggested_service": 1,
     "chosen_service": 1,
     "accepted": true
   }
   ```

5. **Ver ticket**
   ```bash
   GET /api/helpdesks/{id}/
   GET /api/helpdesks/{id}/comments/
   ```

6. **Cerrar ticket (si el servicio lo permite)**
   ```bash
   PATCH /api/helpdesks/{id}/close/
   ```

---

#### Técnico (technician)

1. **Ver mis tickets asignados**
   ```bash
   GET /api/helpdesks/
   ```

2. **Empezar a trabajar**
   ```bash
   PATCH /api/helpdesks/{id}/status/
   {"status": "in_progress"}
   ```

3. **Pedir ayuda o esperar (opcional)**
   ```bash
   PATCH /api/helpdesks/{id}/status/
   {"status": "on_hold"}
   ```

4. **Resolver**
   ```bash
   PATCH /api/helpdesks/{id}/resolve/
   {"solution_description": "Reseté tu contraseña..."}
   ```
   Automáticamente se desencola el siguiente ticket si hay.

5. **Agregar comentarios**
   ```bash
   POST /api/helpdesks/{id}/comments/
   {"content": "Contactado al requester", "is_internal": false}
   ```

---

#### Administrador de Área (area_admin)

1. **Configurar SLA del departamento**
   ```bash
   POST /api/sla-config/
   GET /api/sla-config/
   PUT /api/sla-config/{id}/
   ```

2. **Gestionar técnicos**
   ```bash
   POST /api/technician-profiles/
   GET /api/technician-profiles/
   PUT /api/technician-profiles/{id}/
   ```

3. **Ver cola de espera**
   ```bash
   GET /api/service-queue/
   ```

4. **Asignar manualmente**
   ```bash
   PATCH /api/helpdesks/{id}/assign/
   {
     "assignee_id": 42,
     "due_date": "2026-04-25T18:00:00Z",
     "impact": "company"
   }
   ```

5. **Gestionar keywords del clasificador**
   ```bash
   GET /api/service-keywords/
   POST /api/service-keywords/
   DELETE /api/service-keywords/{id}/
   ```

6. **Ver estadísticas del clasificador**
   ```bash
   GET /api/classify/stats/
   POST /api/classify/train/
   ```

---

## Variables de Entorno

```
# Django
DJANGO_SETTINGS_MODULE=config.settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Base de datos
DB_NAME=helpdesk_dev
DB_USER=helpdesk
DB_PASSWORD=helpdesk
DB_HOST=db
DB_PORT=5432

# Redis / Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_TASK_ALWAYS_EAGER=False

# Archivos adjuntos
MEDIA_ROOT=/app/media
```

---

## Troubleshooting

### Los tickets no se auto-asignan
- Verificar que sea horario hábil (08:30-18:00 Lun-Vie)
- Verificar que hay técnicos activos en el departamento
- Verificar que max_load < cantidad de tickets
- Ver logs de Celery: `docker logs help_desk_PS-worker-1`

### El clasificador no sugiere nada
- Crear keywords: `POST /api/service-keywords/`
- Verificar que el texto contenga los keywords (case-insensitive)
- Ver estadísticas: `GET /api/classify/stats/`

### Feedback no se entrenan
- El entrenamiento corre a las 2:00 AM diariamente
- Disparar manualmente: `POST /api/classify/train/`
- Verificar pending_training en stats

### Cambios en SLAConfig no aplican inmediatamente
- Los tickets creados DESPUÉS del cambio usan la nueva config
- Los tickets existentes mantienen su due_date original

---

## Glosario

- **Folio:** Número único de ticket (HD-000001)
- **Impact:** Alcance del problema (individual, area, company)
- **Priority:** Urgencia (low, medium, high, critical)
- **Status:** Estado del ticket (open, in_progress, on_hold, resolved, closed)
- **Origin:** Tipo de solicitud (error, request, inquiry, maintenance)
- **Max Load:** Máximo de tickets simultáneos por técnico
- **Resolution Time:** Tiempo máximo para resolver
- **Urgency Score:** Puntaje para ordenar la cola
- **Business Hours:** 08:30-18:00 Lun-Vie
- **Keyword:** Palabra clave para clasificación automática
- **Weight:** Importancia de un keyword (1-10)

---

## Contacto y Soporte

Para reportar bugs o sugerencias, abrir un issue en el repositorio.
